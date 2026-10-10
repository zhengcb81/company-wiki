"""End-to-end query-first ensure service over adapters, writer, and journal."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Callable

from .acquisition import (
    AcquisitionCoordinator,
    AcquisitionResult,
    AcquisitionStatus,
    acquisition_target_sha256,
)
from .download_budget import AcquisitionBudget, AcquisitionBudgetExceeded
from .acquisition_journal import AcquisitionAttempt, AcquisitionJournal
from .canonical_writer import (
    CanonicalImportResult,
    CanonicalImportStatus,
    CanonicalSourceWriter,
)
from .resolver import ResolutionResult, ResolutionStatus, SourceRequest, SourceResolver
from .lock import _acquisition_mutex


SOURCE_ENSURE_SCHEMA_VERSION = "1.0"


class SourceEnsureStatus(str, Enum):
    REUSED = "reused"
    IMPORTED = "imported"
    DEDUPLICATED = "deduplicated"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    GAP = "gap"  # WU-4.2: metadata-only plan returned, nothing downloaded


@dataclass(frozen=True)
class SourceEnsureResult:
    schema_version: str
    status: SourceEnsureStatus
    acquisition: AcquisitionResult
    resolution: ResolutionResult
    attempt: AcquisitionAttempt | None
    canonical_import: CanonicalImportResult | None = None
    # M3-USAGE: observed operation usage sibling; absent when no budget ran.
    acquisition_observation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "acquisition": self.acquisition.to_dict(),
            "resolution": self.resolution.to_dict(),
            "attempt": self.attempt.to_dict() if self.attempt else None,
            "canonical_import": (
                self.canonical_import.to_dict() if self.canonical_import else None
            ),
        }
        if self.acquisition.acquisition_failure is not None:
            result["acquisition_failure"] = self.acquisition.acquisition_failure
        if self.acquisition_observation is not None:
            result["acquisition_observation"] = self.acquisition_observation
        return result


def _observation_outcome(status: SourceEnsureStatus, *, candidate, gap_plan) -> str:
    if status is SourceEnsureStatus.REUSED:
        return "reused_after_discovery" if candidate is not None else "reused_before_download"
    if status is SourceEnsureStatus.IMPORTED:
        return "downloaded_new"
    if status is SourceEnsureStatus.DEDUPLICATED:
        return "deduplicated_after_download"
    if status is SourceEnsureStatus.MISSING:
        return "missing"
    if status is SourceEnsureStatus.AMBIGUOUS:
        return "ambiguous"
    if gap_plan is not None and getattr(gap_plan, "provider_unavailable", False):
        return "gap_plan_provider_unavailable"
    return "gap_plan"


def _observed(budget, *, status: SourceEnsureStatus, candidate, gap_plan) -> dict[str, Any] | None:
    from .acquisition_observation import observation_from_budget
    if budget is None:
        return None
    return observation_from_budget(
        budget, outcome=_observation_outcome(status, candidate=candidate, gap_plan=gap_plan),
    )


class SourceAcquisitionService:
    """Resolve first, stage only when required, then commit through the sole writer."""

    def __init__(
        self,
        *,
        coordinator: AcquisitionCoordinator,
        writer: CanonicalSourceWriter,
        journal: AcquisitionJournal,
    ):
        if not isinstance(coordinator, AcquisitionCoordinator):
            raise TypeError("coordinator must be AcquisitionCoordinator")
        if not isinstance(writer, CanonicalSourceWriter):
            raise TypeError("writer must be CanonicalSourceWriter")
        if not isinstance(journal, AcquisitionJournal):
            raise TypeError("journal must be AcquisitionJournal")
        self.coordinator = coordinator
        self.writer = writer
        self.journal = journal

    def ensure(
        self,
        request: SourceRequest,
        *,
        budget: AcquisitionBudget | None = None,
        candidate_scope: Callable[[Any], bool] | None = None,
    ) -> SourceEnsureResult:
        return self._ensure(request, budget=budget, candidate_scope=candidate_scope)

    def _ensure(self, request, *, budget=None, candidate_scope=None) -> SourceEnsureResult:
        """One selection and target transaction; legacy scope is data, not approval."""
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        if budget is not None and not isinstance(budget, AcquisitionBudget):
            raise TypeError("budget must be AcquisitionBudget")
        if candidate_scope is not None and not callable(candidate_scope):
            raise TypeError("candidate_scope must be callable")
        acquisition = None
        failure_reason = "adapter_or_staging_failed"
        try:
            acquisition = self.coordinator.select(request, budget=budget, candidate_scope=candidate_scope)
            if acquisition.status is AcquisitionStatus.SELECTED:
                assert acquisition.candidate is not None
                lock_dir = self.coordinator.catalog.config.catalog_dir / "ensure_locks"
                lock_dir.mkdir(parents=True, exist_ok=True)
                lock_path = lock_dir / (acquisition_target_sha256(request, acquisition.candidate) + ".lock")
                timeout = 10.0 if budget is None else budget.remaining_seconds
                if budget is not None:
                    budget.ensure_open()
                with _acquisition_mutex(lock_path, timeout_seconds=timeout):
                    if budget is not None:
                        budget.ensure_open()
                    try:
                        self.coordinator.cleanup_target(request, acquisition.candidate)
                        staged = self._stage_with_retry(request, acquisition, budget=budget)
                        acquisition = staged
                        failure_reason = "canonical_import_failed"
                        result = self._finish(request, staged, budget=budget,
                            cleanup=lambda: self.coordinator.cleanup_target(request, staged.candidate))
                    except Exception as exc:
                        try:
                            self.coordinator.cleanup_target(request, acquisition.candidate)
                        except Exception as cleanup_error:
                            add_note = getattr(exc, "add_note", None)
                            if callable(add_note):
                                add_note(f"staging cleanup failed: {cleanup_error}")
                        raise
                    return result
            return self._finish(request, acquisition, budget=budget)
        except Exception as exc:
            from .acquisition_failure import attach_acquisition_failure
            attach_acquisition_failure(exc, budget=budget, code="acquisition_validation_failed")
            try:
                self.journal.record(
                    request_id=request.request_id,
                    outcome="failed",
                    reason=failure_reason,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    content_sha256=(acquisition.receipt.content_sha256
                                    if acquisition is not None and acquisition.receipt is not None else None),
                )
            except Exception as journal_error:
                exc.add_note(f"acquisition journal failed: {type(journal_error).__name__}")
            raise

    def _stage_with_retry(self, request, selected, *, budget=None):
        from .adapter_process import AdapterProcessError

        for attempt in range(3):
            try:
                return self.coordinator.stage_selected(request, selected, budget=budget)
            except AdapterProcessError as exc:
                if not exc.retryable or attempt == 2:
                    raise
                try:
                    self.coordinator.cleanup_target(request, selected.candidate)
                except Exception as cleanup_error:
                    exc.add_note(f"staging cleanup failed: {type(cleanup_error).__name__}")
                    raise exc
                if budget is not None:
                    budget.ensure_open()
        raise AssertionError("bounded staging loop did not return or raise")

    def _finish(self, request, acquisition, *, budget=None,
                cleanup: Callable[[], None] | None = None) -> SourceEnsureResult:
        candidate = acquisition.candidate
        common = {
            "request_id": request.request_id,
            "adapter_name": acquisition.adapter_name,
            "candidate_id": candidate.candidate_id if candidate else None,
            "provider": candidate.provider if candidate else None,
            "provider_document_id": (
                candidate.provider_document_id if candidate else None
            ),
            "source_url": candidate.source_url if candidate else None,
            "reason": acquisition.reason,
        }

        def record_attempt(outcome, **values):
            if cleanup is not None:
                cleanup()
            return self.journal.record(outcome=outcome, **common, **values)

        if acquisition.status is AcquisitionStatus.REUSED:
            outcome = (
                "reused_after_discovery"
                if acquisition.candidate is not None
                else "reused_before_download"
            )
            attempt = record_attempt(outcome)
            return SourceEnsureResult(
                schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
                status=SourceEnsureStatus.REUSED,
                acquisition=acquisition,
                resolution=acquisition.resolution,
                attempt=attempt,
                acquisition_observation=_observed(budget, status=SourceEnsureStatus.REUSED,
                    candidate=acquisition.candidate, gap_plan=None),
            )
        if acquisition.status is AcquisitionStatus.MISSING:
            attempt = record_attempt("missing")
            return SourceEnsureResult(
                schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
                status=SourceEnsureStatus.MISSING,
                acquisition=acquisition,
                resolution=acquisition.resolution,
                attempt=attempt,
                acquisition_observation=_observed(budget, status=SourceEnsureStatus.MISSING,
                    candidate=acquisition.candidate, gap_plan=None),
            )
        if acquisition.status is AcquisitionStatus.AMBIGUOUS:
            attempt = record_attempt("ambiguous")
            return SourceEnsureResult(
                schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
                status=SourceEnsureStatus.AMBIGUOUS,
                acquisition=acquisition,
                resolution=acquisition.resolution,
                attempt=attempt,
                acquisition_observation=_observed(budget, status=SourceEnsureStatus.AMBIGUOUS,
                    candidate=acquisition.candidate, gap_plan=None),
            )
        if acquisition.status is AcquisitionStatus.GAP:
            # Metadata diagnostic only; a plan hash does not grant permission.
            plan = acquisition.gap_plan
            attempt = record_attempt(
                (
                    "gap_plan_provider_unavailable"
                    if plan is not None and plan.provider_unavailable
                    else "gap_plan"
                ),
            )
            return SourceEnsureResult(
                schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
                status=SourceEnsureStatus.GAP,
                acquisition=acquisition,
                resolution=acquisition.resolution,
                attempt=attempt,
                acquisition_observation=_observed(budget, status=SourceEnsureStatus.GAP,
                    candidate=acquisition.candidate, gap_plan=plan),
            )
        if candidate is None or acquisition.receipt is None:
            raise RuntimeError("staged acquisition is missing candidate or receipt")
        if budget is not None:
            budget.ensure_open()
        try:
            imported = self.writer.import_staged(request, candidate, acquisition.receipt, budget=budget)
        except AcquisitionBudgetExceeded:
            raise
        except Exception as exc:
            # The code is assigned at the actual writer responsibility boundary,
            # not inferred from every subsequent completion/journal failure.
            exc.error_code = "canonical_import_failed"
            raise
        if budget is not None:
            budget.ensure_open()
        final = SourceResolver(self.coordinator.catalog).resolve(
            self.coordinator.target_request(request, candidate))
        final = replace(final, request_id=request.request_id)
        # The writer has returned the registered exact version. This query
        # describes its applicability to the requested history; it is not a
        # second storage acceptance gate. Multiple provider revisions can be
        # narrowed to the exact bytes this transaction actually committed.
        committed = tuple(h for h in final.matches
                          if h.content_sha256 == imported.source_ref.content_sha256)
        if final.status is ResolutionStatus.AMBIGUOUS and len(committed) == 1:
            final = replace(final, status=ResolutionStatus.REUSED_EXACT,
                            reason="one_existing_source_matches_provider_identity",
                            matches=committed, download_required=False)
        if imported.status is CanonicalImportStatus.IMPORTED_NEW:
            status = SourceEnsureStatus.IMPORTED
            outcome = "downloaded_new"
        else:
            status = SourceEnsureStatus.DEDUPLICATED
            outcome = "deduplicated_after_download"
        if final.status is ResolutionStatus.AMBIGUOUS:
            status = SourceEnsureStatus.AMBIGUOUS
        elif final.status not in {ResolutionStatus.REUSED_EXACT, ResolutionStatus.REUSED_EQUIVALENT}:
            status = SourceEnsureStatus.MISSING
        attempt = record_attempt(
            outcome,
            content_sha256=imported.content_sha256,
            canonical_path=imported.canonical_path,
        )
        return SourceEnsureResult(
            schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
            status=status,
            acquisition=acquisition,
            resolution=final,
            attempt=attempt,
            canonical_import=imported,
            acquisition_observation=_observed(budget, status=status,
                candidate=acquisition.candidate, gap_plan=None),
        )



__all__ = [
    "SOURCE_ENSURE_SCHEMA_VERSION",
    "SourceAcquisitionService",
    "SourceEnsureResult",
    "SourceEnsureStatus",
]
