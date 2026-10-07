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
from .download_budget import AcquisitionBudget
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "acquisition": self.acquisition.to_dict(),
            "resolution": self.resolution.to_dict(),
            "attempt": self.attempt.to_dict() if self.attempt else None,
            "canonical_import": (
                self.canonical_import.to_dict() if self.canonical_import else None
            ),
        }


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
            self.journal.record(
                request_id=request.request_id,
                outcome="failed",
                reason=failure_reason,
                error_type=type(exc).__name__,
                error=str(exc),
                content_sha256=(acquisition.receipt.content_sha256
                                if acquisition is not None and acquisition.receipt is not None else None),
            )
            raise

    def _stage_with_retry(self, request, selected, *, budget=None):
        from .adapter_process import AdapterProcessError

        for attempt in range(3):
            try:
                return self.coordinator.stage_selected(request, selected, budget=budget)
            except AdapterProcessError as exc:
                if not exc.retryable or attempt == 2:
                    raise
                self.coordinator.cleanup_target(request, selected.candidate)
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
            )
        if acquisition.status is AcquisitionStatus.MISSING:
            attempt = record_attempt("missing")
            return SourceEnsureResult(
                schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
                status=SourceEnsureStatus.MISSING,
                acquisition=acquisition,
                resolution=acquisition.resolution,
                attempt=attempt,
            )
        if acquisition.status is AcquisitionStatus.AMBIGUOUS:
            attempt = record_attempt("ambiguous")
            return SourceEnsureResult(
                schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
                status=SourceEnsureStatus.AMBIGUOUS,
                acquisition=acquisition,
                resolution=acquisition.resolution,
                attempt=attempt,
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
            )
        if candidate is None or acquisition.receipt is None:
            raise RuntimeError("staged acquisition is missing candidate or receipt")
        if budget is not None:
            budget.ensure_open()
        imported = self.writer.import_staged(request, candidate, acquisition.receipt, budget=budget)
        if budget is not None:
            budget.ensure_open()
        final = SourceResolver(self.coordinator.catalog).resolve(
            self.coordinator.target_request(request, candidate))
        final = replace(final, request_id=request.request_id)
        if final.status not in {ResolutionStatus.REUSED_EXACT, ResolutionStatus.REUSED_EQUIVALENT}:
            raise RuntimeError("final source resolution did not reuse the requested source")
        if not any(h.content_sha256 == imported.content_sha256 for h in final.matches):
            raise RuntimeError("final source resolution did not match imported bytes")
        if imported.status is CanonicalImportStatus.IMPORTED_NEW:
            status = SourceEnsureStatus.IMPORTED
            outcome = "downloaded_new"
        else:
            status = SourceEnsureStatus.DEDUPLICATED
            outcome = "deduplicated_after_download"
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
        )



__all__ = [
    "SOURCE_ENSURE_SCHEMA_VERSION",
    "SourceAcquisitionService",
    "SourceEnsureResult",
    "SourceEnsureStatus",
]
