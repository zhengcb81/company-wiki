"""Legacy close-gap results over the unified, bounded acquisition service.

Old bindings only narrow provider/accession scope and byte limits. Download
intent, shared resource accounting, target locks and real source verification
belong to the same service used by ensure; policy hashes and TTLs are history.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any

from .acquisition import AcquisitionStatus
from .acquisition_journal import AcquisitionJournal
from .download_budget import AcquisitionBudget
from .canonical_writer import CanonicalSourceWriter
from .resolver import SourceRequest, build_resolution_envelope


CLOSE_GAP_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class CloseGapBinding:
    """Legacy request scope; digest/expiry fields are diagnostic compatibility."""

    request_id: str
    gap_plan_hash: str
    policy_hash: str
    provider: str
    allowed_accessions: tuple[str, ...]
    max_items: int
    max_bytes: int
    expires_at: str

    def __post_init__(self):
        if (not isinstance(self.provider, str) or not self.provider
                or self.provider != self.provider.strip()):
            raise ValueError("provider must be non-empty trimmed text")
        object.__setattr__(self, "provider", self.provider.lower())
        if not isinstance(self.allowed_accessions, tuple) or any(
            not isinstance(item, str) or not item or item != item.strip()
            for item in self.allowed_accessions
        ):
            raise ValueError("allowed_accessions must contain trimmed accession strings")
        for field in ("max_items", "max_bytes"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "gap_plan_hash": self.gap_plan_hash,
            "policy_hash": self.policy_hash,
            "provider": self.provider,
            "allowed_accessions": list(self.allowed_accessions),
            "max_items": self.max_items,
            "max_bytes": self.max_bytes,
            "expires_at": self.expires_at,
        }

    def restrict(self, budget: AcquisitionBudget):
        """Narrow an existing budget/selection; this is not a permission check."""
        if self.max_items < 1 or self.max_bytes <= 0:
            raise ValueError("request scope allows no items or bytes")
        budget.max_response_bytes = min(budget.max_response_bytes, self.max_bytes)
        if budget.response_bytes_used > budget.max_response_bytes:
            from .download_budget import AcquisitionBudgetExceeded
            raise AcquisitionBudgetExceeded("request byte scope already exceeded")
        budget.ensure_open()
        return lambda candidate: (
            candidate.provider == self.provider
            and candidate.provider_document_id in self.allowed_accessions
        )


@dataclass(frozen=True)
class CloseGapResult:
    schema_version: str
    txn_id: str
    status: str  # completed | rejected | failed
    reason: str
    fetch_events: int
    outcome: str | None
    resolution: dict[str, Any] | None
    envelope: dict[str, Any] | None
    acquisition_failure: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "txn_id": self.txn_id,
            "status": self.status,
            "reason": self.reason,
            "fetch_events": self.fetch_events,
            "outcome": self.outcome,
            "resolution": self.resolution,
            "envelope": self.envelope,
        }
        if self.acquisition_failure is not None:
            result["acquisition_failure"] = self.acquisition_failure
        return result


def _txn_id(binding: CloseGapBinding) -> str:
    payload = json.dumps({"request_id": binding.request_id, "provider": binding.provider,
                          "accessions": sorted(binding.allowed_accessions)}, sort_keys=True, ensure_ascii=False)
    return (
        "urn:company-wiki:close-gap:sha256:"
        + hashlib.sha256(payload.encode("utf-8")).hexdigest()
    )


def _reject_result(txn: str, reason: str) -> CloseGapResult:
    return CloseGapResult(
        schema_version=CLOSE_GAP_SCHEMA_VERSION,
        txn_id=txn,
        status="rejected",
        reason=reason,
        fetch_events=0,
        outcome=None,
        resolution=None,
        envelope=None,
    )


class CloseGapTransaction:
    """Legacy result wrapper around the one acquisition transaction service.

    Executing close-gap is an explicit fetch-if-missing operation. An optional
    old binding narrows target scope/caps; hashes and expiry are diagnostics.
    """

    def __init__(self, *, catalog: Any, coordinator: Any,
                 writer: CanonicalSourceWriter, journal: AcquisitionJournal) -> None:
        self.catalog, self.coordinator = catalog, coordinator
        self.writer, self.journal = writer, journal

    def execute(self, binding: CloseGapBinding | None, request: SourceRequest, *,
                budget: AcquisitionBudget | None = None) -> CloseGapResult:
        from .acquisition_service import SourceAcquisitionService, SourceEnsureStatus
        from .resolver import ResolutionStatus

        if binding is not None and not isinstance(binding, CloseGapBinding):
            raise TypeError("binding must be CloseGapBinding or None")
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be SourceRequest")
        if budget is not None and not isinstance(budget, AcquisitionBudget):
            raise TypeError("budget must be AcquisitionBudget")
        request = replace(request, allow_download=True)
        txn = ("urn:company-wiki:close-gap:sha256:" + request.request_id.rsplit(":", 1)[-1]
               if binding is None else _txn_id(binding))
        if binding is None and budget is None:
            return _reject_result(txn, "acquisition_budget_required")
        scope = None
        if binding is not None:
            if binding.max_items < 1 or binding.max_bytes <= 0:
                return _reject_result(txn, "request_scope_allows_no_items_or_bytes")
            if budget is None:
                budget = AcquisitionBudget.from_limits(max_response_bytes=binding.max_bytes,
                    max_seconds=30, max_cost_usd="0")
            scope = binding.restrict(budget)
        service = SourceAcquisitionService(coordinator=self.coordinator,
                                           writer=self.writer, journal=self.journal)
        try:
            ensured = service.ensure(request, budget=budget, candidate_scope=scope)
        except Exception as exc:
            from .acquisition_failure import published_acquisition_failure
            return CloseGapResult(CLOSE_GAP_SCHEMA_VERSION, txn, "failed",
                f"acquisition_failed:{type(exc).__name__}:{exc}", 0, None, None, None,
                acquisition_failure=published_acquisition_failure(exc))
        completed = ensured.status in {SourceEnsureStatus.REUSED, SourceEnsureStatus.IMPORTED,
                                       SourceEnsureStatus.DEDUPLICATED}
        if not completed or ensured.resolution.status not in {
            ResolutionStatus.REUSED_EXACT, ResolutionStatus.REUSED_EQUIVALENT,
        }:
            return CloseGapResult(CLOSE_GAP_SCHEMA_VERSION, txn, "rejected",
                ensured.acquisition.reason or "no_unique_current_target", 0, None,
                ensured.resolution.to_dict(), None,
                acquisition_failure=ensured.acquisition.acquisition_failure)
        fetch_events = int(ensured.acquisition.status is AcquisitionStatus.STAGED)
        envelope = build_resolution_envelope(ensured.resolution, journal=self.journal,
            bundle=self.catalog.bundle_for_resolution(ensured.resolution),
            store=self.catalog.store, project_root=self.catalog.config.project_root)
        return CloseGapResult(CLOSE_GAP_SCHEMA_VERSION, txn, "completed",
            "gap_closed_downloaded" if fetch_events else "gap_already_closed_or_reused",
            fetch_events, ensured.attempt.outcome if ensured.attempt else None,
            ensured.resolution.to_dict(), envelope.to_dict())
