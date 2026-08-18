"""FC-801: CloseGap transaction — the fixed close-gap step sequence.

A ``CloseGapTransaction`` executes the authorized download of a gap plan
as ONE contract with journaled state:

1. policy binding check (DL-03): the RuntimePolicySnapshot hash must match
   the binding — a download authorized under a different policy is never
   reusable (fetch=0);
2. gap revalidation (DL-03): rediscover provider metadata (metadata only,
   nothing fetched) and rebuild the current GapPlan; if the plan still has
   missing items but its hash differs from the binding, the authorization
   is stale (fetch=0); if the gap is already closed (no missing), the
   transaction completes as reused (fetch=0);
3. authorize + fetch staging (DL-02): the coordinator stages only what the
   receipt allows (accessions/caps/expiry); any authorization failure is
   rejected with the precise reason and fetch=0;
4. validate (DL-07): receipt bytes/hash/magic must match — invalid staging
   is never committed; the staging directory is cleaned up (auditable) and
   the catalog is unchanged;
5. canonical commit (DL-09): ``import_staged`` is idempotent by
   content_sha256 — a re-run after interruption deduplicates;
6. re-resolve: the final resolver pass returns the FC-704 envelope so the
   caller sees the real outcome (journal-reconciled).

Partial failure (LT-10) never reports ``completed``: the journal records
``failed`` with the txn id and the reason; re-running the same binding is
safe.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .acquisition import AcquisitionStatus
from .acquisition_journal import AcquisitionJournal
from .authorization import build_download_authorization
from .canonical_writer import CanonicalSourceWriter
from .resolver import (
    SourceRequest,
    SourceResolver,
    build_resolution_envelope,
)
from .runtime_policy import RuntimePolicyError, load_runtime_policy


CLOSE_GAP_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class CloseGapBinding:
    """FC-801: the input binding of one authorized close-gap download."""

    request_id: str
    gap_plan_hash: str
    policy_hash: str
    provider: str
    allowed_accessions: tuple[str, ...]
    max_items: int
    max_bytes: int
    expires_at: str

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "txn_id": self.txn_id,
            "status": self.status,
            "reason": self.reason,
            "fetch_events": self.fetch_events,
            "outcome": self.outcome,
            "resolution": self.resolution,
            "envelope": self.envelope,
        }


def _txn_id(binding: CloseGapBinding) -> str:
    payload = json.dumps(binding.to_dict(), sort_keys=True, ensure_ascii=False)
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


def _is_retryable_staging_error(exc: Exception) -> bool:
    """FC-804 OPS-02: a staging error is retryable when the adapter said so
    (AdapterProcessError.retryable) or the plan reported the provider
    unavailable.  Everything else fails immediately."""
    from .adapter_process import AdapterProcessError

    if isinstance(exc, AdapterProcessError):
        return bool(exc.retryable)
    if isinstance(exc, RuntimeError) and str(exc).startswith(
        ("provider unavailable", "download not authorized")
    ):
        return False
    return False


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _actionable_candidates(gap_plan: Any) -> tuple[Any, ...]:
    """Return the exact remote candidates an authorized close-gap may fetch.

    A same-period amendment is a real freshness gap even when a local filing
    already exists, so ``newer_revision`` is actionable alongside ``missing``.
    The plan hash binds this ordered set; the acquisition coordinator still
    validates provider, accession, caps, and expiry before it fetches bytes.
    """
    return tuple(gap_plan.missing) + tuple(gap_plan.newer_revision)


class CloseGapTransaction:
    """FC-801: execute one authorized close-gap download, journaled."""

    def __init__(
        self,
        *,
        catalog: Any,
        coordinator: Any,
        writer: CanonicalSourceWriter,
        journal: AcquisitionJournal,
    ) -> None:
        self.catalog = catalog
        self.coordinator = coordinator
        self.writer = writer
        self.journal = journal
        # ZR-203: close-gap is a WRITE flow — the writer initializer may
        # create the catalog before the read-only resolver reads it.
        _ = getattr(self.catalog, "store", None)

    def execute(
        self,
        binding: CloseGapBinding,
        request: SourceRequest,
    ) -> CloseGapResult:
        if not isinstance(binding, CloseGapBinding):
            raise TypeError("binding must be a CloseGapBinding")
        if not isinstance(request, SourceRequest):
            raise TypeError("request must be a SourceRequest")
        txn = _txn_id(binding)

        def _fail(
            reason: str, *, error: str | None = None, error_type: str | None = None
        ) -> CloseGapResult:
            self.journal.record(
                request_id=binding.request_id,
                outcome="failed",
                reason=reason,
                error_type=error_type,
                error=error,
            )
            return CloseGapResult(
                schema_version=CLOSE_GAP_SCHEMA_VERSION,
                txn_id=txn,
                status="failed",
                reason=reason,
                fetch_events=0,
                outcome=None,
                resolution=None,
                envelope=None,
            )

        def _reject(reason: str) -> CloseGapResult:
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

        # Step 1: policy binding (DL-03) — fail closed without a snapshot.
        try:
            snapshot = load_runtime_policy(
                self.catalog.config.catalog_dir / "runtime_policy.json"
            )
        except RuntimePolicyError:
            return _reject("no_runtime_policy")
        if snapshot.get("policy_hash") != binding.policy_hash:
            return _reject("stale_policy_hash")

        # Step 2: gap revalidation (DL-03) — metadata only, nothing fetched.
        rediscovered = self.coordinator.resolve_or_stage(
            SourceRequest(
                entity=request.entity,
                market=request.market,
                security_id=request.security_id,
                document_kind=request.document_kind,
                form_type=request.form_type,
                fiscal_year=request.fiscal_year,
                fiscal_period=request.fiscal_period,
                language=request.language,
                provider=request.provider,
                provider_document_id=request.provider_document_id,
                as_of_date=request.as_of_date,
                mode="latest_as_of",
            )
        )
        if rediscovered.status is not AcquisitionStatus.GAP:
            return _reject(f"gap_revalidated_status:{rediscovered.status.value}")
        current_plan = rediscovered.gap_plan
        actionable = _actionable_candidates(current_plan)
        if not actionable:
            # The gap is already closed (local is latest): complete as
            # reused with zero fetches — idempotent recovery (DL-09).
            return self._complete_reused(
                request, txn, binding, reason="gap_already_closed"
            )
        if current_plan.gap_hash != binding.gap_plan_hash:
            return _reject("stale_gap_hash")

        # Step 3: authorize + fetch staging (DL-02).
        # The staging request is built per exact actionable candidate: an
        # exact request without its fiscal_year would re-resolve an older
        # local document as reused and never stage a missing period or a
        # same-period newer revision.
        missing_candidate = actionable[0]
        missing_year = getattr(missing_candidate, "fiscal_year", None)
        missing_pdoc = getattr(missing_candidate, "provider_document_id", None)
        authorization = build_download_authorization(
            request_id=binding.request_id,
            gap_plan_hash=binding.gap_plan_hash,
            policy_hash=binding.policy_hash,
            provider=binding.provider,
            allowed_accessions=binding.allowed_accessions,
            max_items=binding.max_items,
            max_bytes=binding.max_bytes,
            expires_at=binding.expires_at,
        )
        staged_request = SourceRequest(
            entity=request.entity,
            market=request.market,
            security_id=request.security_id,
            document_kind=request.document_kind,
            form_type=request.form_type
            or getattr(missing_candidate, "form_type", None),
            fiscal_year=missing_year or request.fiscal_year,
            fiscal_period=request.fiscal_period,
            language=request.language,
            provider=getattr(missing_candidate, "provider", None) or request.provider,
            provider_document_id=missing_pdoc or request.provider_document_id,
            as_of_date=request.as_of_date,
            mode="exact",
            allow_download=True,
        )
        # Step 3 (FC-804 DL-08): single-flight — the fetch+commit phase is
        # serialized per transaction across processes.  INSIDE the lock the
        # gap is re-checked: the first caller may have just closed it, in
        # which case this caller completes as reused with fetch=0 (at most
        # one provider fetch + one canonical commit for the same request).
        from .lock import CatalogOperationLockedError, _acquisition_mutex

        lock_dir = self.catalog.config.catalog_dir / "close_gap_locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_path = lock_dir / (txn.rsplit(":", 1)[-1] + ".lock")
        lock_timeout = self._lock_timeout_seconds()
        try:
            with _acquisition_mutex(lock_path, timeout_seconds=lock_timeout):
                return self._fetch_and_commit(
                    request,
                    staged_request,
                    authorization,
                    txn,
                    binding,
                    missing_candidate,
                )
        except CatalogOperationLockedError as exc:
            return _fail(
                f"close_gap_lock_timeout: {exc}",
                error_type="CatalogOperationLockedError",
            )

    def _lock_timeout_seconds(self) -> float:
        """Lock wait bound: the adapter timeout plus a small grace."""
        timeout = getattr(self.coordinator, "timeout_seconds", None)
        if isinstance(timeout, (int, float)) and timeout > 0:
            return float(timeout) + 30.0
        return 600.0

    def _fetch_and_commit(
        self,
        request,
        staged_request,
        authorization,
        txn: str,
        binding,
        missing_candidate,
    ) -> CloseGapResult:
        def _fail(reason, *, error=None, error_type=None):
            self.journal.record(
                request_id=binding.request_id,
                outcome="failed",
                reason=reason,
                error_type=error_type,
                error=error,
            )
            return CloseGapResult(
                schema_version=CLOSE_GAP_SCHEMA_VERSION,
                txn_id=txn,
                status="failed",
                reason=reason,
                fetch_events=0,
                outcome=None,
                resolution=None,
                envelope=None,
            )

        # Re-check the gap INSIDE the lock (FC-804 DL-08): the first caller
        # may have closed it while we waited.
        rediscovered = self.coordinator.resolve_or_stage(
            SourceRequest(
                entity=request.entity,
                market=request.market,
                security_id=request.security_id,
                document_kind=request.document_kind,
                form_type=request.form_type,
                fiscal_year=request.fiscal_year,
                fiscal_period=request.fiscal_period,
                language=request.language,
                provider=request.provider,
                provider_document_id=request.provider_document_id,
                as_of_date=request.as_of_date,
                mode="latest_as_of",
            )
        )
        if rediscovered.status is AcquisitionStatus.GAP:
            current = rediscovered.gap_plan
            if not _actionable_candidates(current):
                # single-flight win: the other caller downloaded it
                return self._complete_reused(
                    request, txn, binding, reason="gap_closed_by_concurrent"
                )
            if current.gap_hash != binding.gap_plan_hash:
                return _reject_result(txn, "stale_gap_hash")

        # FC-804 OPS-02: bounded retry for retryable staging failures.
        attempts = 0
        backoff = 1.0
        while True:
            attempts += 1
            try:
                staged = self.coordinator.resolve_or_stage(
                    staged_request, authorization=authorization
                )
                break
            except Exception as exc:
                if str(exc).startswith("download not authorized"):
                    # DL-02: authorization failures are REJECTIONS.
                    return _reject_result(txn, str(exc))
                retryable = _is_retryable_staging_error(exc)
                if attempts >= 3 or not retryable:
                    # DL-07 / LT-10: never committed, staging cleaned.  The
                    # staging dir is named by the STAGING request's id.
                    self._cleanup_staging(staged_request.request_id)
                    return _fail(str(exc), error_type=type(exc).__name__)
                import time

                time.sleep(backoff)
                backoff *= 2.0

        if staged.status is AcquisitionStatus.REUSED:
            return self._complete_reused(
                request, txn, binding, reason="reused_after_discovery"
            )
        if staged.status is not AcquisitionStatus.STAGED:
            return _reject_result(txn, f"stage_status:{staged.status.value}")

        # Step 4: canonical commit (DL-09 — idempotent by content hash).
        try:
            imported = self.writer.import_staged(
                request, staged.candidate, staged.receipt
            )
        except Exception as exc:
            return _fail(
                f"canonical_import_failed: {type(exc).__name__}: {exc}",
                error_type=type(exc).__name__,
            )
        outcome = (
            "downloaded_new"
            if imported.status.value == "imported_new"
            else "deduplicated_after_download"
        )
        self.journal.record(
            request_id=binding.request_id,
            outcome=outcome,
            adapter_name=staged.adapter_name,
            candidate_id=staged.candidate.candidate_id,
            provider=staged.candidate.provider,
            provider_document_id=staged.candidate.provider_document_id,
            source_url=staged.candidate.source_url,
            content_sha256=staged.receipt.content_sha256,
            reason=staged.reason,
        )
        return self._finalize(request, txn, outcome, fetch_events=1)

    # -- helpers ---------------------------------------------------------------

    def _complete_reused(self, request, txn, binding, *, reason: str):
        self.journal.record(
            request_id=binding.request_id,
            outcome="reused_before_download",
            reason=reason,
        )
        return self._finalize(request, txn, "reused_before_download", fetch_events=0)

    def _finalize(self, request, txn, outcome: str, *, fetch_events: int):
        """Step 5: re-resolve and attach the FC-704 envelope (+ FC-902 bundle).

        LT-10: ``completed`` is only claimed when the document actually
        resolves — a re-resolve that misses means the close did NOT happen.
        """
        from .resolver import ResolutionStatus

        resolution = SourceResolver(self.catalog).resolve(request)
        if resolution.status not in (
            ResolutionStatus.REUSED_EXACT,
            ResolutionStatus.REUSED_EQUIVALENT,
        ):
            return CloseGapResult(
                schema_version=CLOSE_GAP_SCHEMA_VERSION,
                txn_id=txn,
                status="failed",
                reason=f"re_resolve_did_not_reuse:{resolution.status.value}",
                fetch_events=fetch_events,
                outcome=None,
                resolution=resolution.to_dict(),
                envelope=None,
            )
        envelope = build_resolution_envelope(
            resolution,
            journal=self.journal,
            bundle=self.catalog.bundle_for_resolution(resolution),
            store=self.catalog.store,
            project_root=self.catalog.config.project_root,
        )
        return CloseGapResult(
            schema_version=CLOSE_GAP_SCHEMA_VERSION,
            txn_id=txn,
            status="completed",
            reason=(
                "gap_closed_downloaded"
                if fetch_events
                else "gap_already_closed_or_reused"
            ),
            fetch_events=fetch_events,
            outcome=outcome,
            resolution=resolution.to_dict(),
            envelope=envelope.to_dict(),
        )

    def _cleanup_staging(self, request_id: str) -> None:
        """Auditable staging cleanup (DL-07): remove the request's staging
        directory so invalid bytes never linger."""
        staging_root = self.coordinator.staging_root
        request_dir = staging_root / request_id.rsplit(":", 1)[-1]
        if request_dir.is_dir():
            shutil.rmtree(request_dir, ignore_errors=True)
