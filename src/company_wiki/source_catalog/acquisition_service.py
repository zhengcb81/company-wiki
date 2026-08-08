"""End-to-end query-first ensure service over adapters, writer, and journal."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .acquisition import (
    AcquisitionCoordinator,
    AcquisitionResult,
    AcquisitionStatus,
)
from .acquisition_journal import AcquisitionAttempt, AcquisitionJournal
from .canonical_writer import (
    CanonicalImportResult,
    CanonicalImportStatus,
    CanonicalSourceWriter,
)
from .resolver import ResolutionResult, SourceRequest


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
    attempt: AcquisitionAttempt
    canonical_import: CanonicalImportResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "acquisition": self.acquisition.to_dict(),
            "resolution": self.resolution.to_dict(),
            "attempt": self.attempt.to_dict(),
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

    def ensure(self, request: SourceRequest) -> SourceEnsureResult:
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        try:
            acquisition = self.coordinator.resolve_or_stage(request)
        except Exception as exc:
            self.journal.record(
                request_id=request.request_id,
                outcome="failed",
                reason="adapter_or_staging_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

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
        if acquisition.status is AcquisitionStatus.REUSED:
            outcome = (
                "reused_after_discovery"
                if acquisition.candidate is not None
                else "reused_before_download"
            )
            attempt = self.journal.record(outcome=outcome, **common)
            return SourceEnsureResult(
                schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
                status=SourceEnsureStatus.REUSED,
                acquisition=acquisition,
                resolution=acquisition.resolution,
                attempt=attempt,
            )
        if acquisition.status is AcquisitionStatus.MISSING:
            attempt = self.journal.record(outcome="missing", **common)
            return SourceEnsureResult(
                schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
                status=SourceEnsureStatus.MISSING,
                acquisition=acquisition,
                resolution=acquisition.resolution,
                attempt=attempt,
            )
        if acquisition.status is AcquisitionStatus.AMBIGUOUS:
            attempt = self.journal.record(outcome="ambiguous", **common)
            return SourceEnsureResult(
                schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
                status=SourceEnsureStatus.AMBIGUOUS,
                acquisition=acquisition,
                resolution=acquisition.resolution,
                attempt=attempt,
            )
        if acquisition.status is AcquisitionStatus.GAP:
            # WU-4.2: metadata-only plan surfaced to the caller; nothing was
            # downloaded and nothing was written. The plan hash is the basis
            # for any later authorized fetch (WU-4.3).
            plan = acquisition.gap_plan
            attempt = self.journal.record(
                outcome=(
                    "gap_plan_provider_unavailable"
                    if plan is not None and plan.provider_unavailable
                    else "gap_plan"
                ),
                **common,
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
        try:
            imported = self.writer.import_staged(
                request,
                candidate,
                acquisition.receipt,
            )
        except Exception as exc:
            self.journal.record(
                outcome="failed",
                content_sha256=acquisition.receipt.content_sha256,
                reason="canonical_import_failed",
                error_type=type(exc).__name__,
                error=str(exc),
                **{key: value for key, value in common.items() if key != "reason"},
            )
            raise
        if imported.status is CanonicalImportStatus.IMPORTED_NEW:
            status = SourceEnsureStatus.IMPORTED
            outcome = "downloaded_new"
        else:
            status = SourceEnsureStatus.DEDUPLICATED
            outcome = "deduplicated_after_download"
        attempt = self.journal.record(
            outcome=outcome,
            content_sha256=imported.content_sha256,
            canonical_path=imported.canonical_path,
            **common,
        )
        return SourceEnsureResult(
            schema_version=SOURCE_ENSURE_SCHEMA_VERSION,
            status=status,
            acquisition=acquisition,
            resolution=imported.resolution,
            attempt=attempt,
            canonical_import=imported,
        )


__all__ = [
    "SOURCE_ENSURE_SCHEMA_VERSION",
    "SourceAcquisitionService",
    "SourceEnsureResult",
    "SourceEnsureStatus",
]
