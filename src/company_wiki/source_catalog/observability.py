"""WU-1305: versioned reason taxonomy + privacy-safe metrics collector.

Every rejection/reuse/download/recompute carries a *registered* reason code
(snake_case, versioned by REASON_TAXONOMY_VERSION).  The collector aggregates
by root/route/adapter/version/role without ever recording company names,
document ids, or absolute paths — those are redacted by default (REDACT).

Telemetry export being off must not affect core behavior: the collector is
pure in-memory, append-only, and thread-safe; nothing raises when the
exporter is absent.
"""

from __future__ import annotations

import math
import re
import threading
from dataclasses import dataclass, field
from typing import Any

REASON_TAXONOMY_VERSION = "1.1"

# Canonical reason taxonomy (additive; codes are never removed, only
# deprecated) — kept in sync with admission/reuse/resolver/artifact codes.
REASONS: dict[str, str] = {
    # scan / admission
    "admitted": "candidate facts pass the profile gate",
    "identity_missing": "no canonical_entity_id or security_id",
    "kind_missing": "no document_kind",
    "period_missing": "no fiscal_year or period_end",
    "hash_missing": "no content_sha256",
    "content_hash_mismatch": "observed bytes differ from recorded hash",
    "status_not_active": "source_status != active",
    "policy_denied": "root policy does not authorize reuse",
    "non_filing_kind": "document kind is not a filing profile",
    "focus_policy_invalid_relative_path": "path traversal or absolute path",
    "focus_policy_no_allowed_category_evidence": "no allowed category evidence",
    # reuse / latest / gap
    "download_suppressed": "reuse policy suppressed the download",
    "download_authorized": "gap plan authorized a download",
    "downloaded": "download executed once",
    "gap_not_required": "no gap to close for this period",
    "gap_authorization_expired": "download auth window expired",
    # resolver
    "exact_hit": "exact identity match resolved",
    "latest_selected": "latest-as-of handle selected",
    "ambiguous_issuer": "token shared by multiple issuers",
    "entity_gate_rejected": "entity anchoring failed",
    # artifacts
    "artifact_selected": "valid artifact reused",
    "artifact_rejected": "artifact failed validation (reason in detail)",
    "recomputed": "artifact recompute planned",
    "stale_bundle": "snapshot mismatch invalidates the bundle",
    # migration / bridge
    "legacy_bridge_hit": "legacy acquisition/dayu_meta container read",
    "shadow_diff": "v2 shadow read differed from legacy bridge",
    "migration_remaining": "sources still pending migration",
    "verified_v2_assertion": "verified v2 assertion read (legacy-visible)",
    # FC-1301 additions (1.1) — every emitted reason literal must be
    # registered; the audit gate below fails closed on unregistered codes.
    # adapters / acquisition
    "adapter_discovery_returned_multiple_candidates": "adapter saw >1 candidate",
    "adapter_discovery_returned_no_candidate": "adapter saw no candidates",
    "adapter_or_staging_failed": "adapter fetch or staging failed",
    "existing_catalog_source_reused_before_adapter": "catalog hit before adapter",
    "existing_catalog_source_reused_after_discovery": "catalog hit after discovery",
    "missing_source_downloaded_to_staging_pending_canonical_import": "staged download awaiting canonical import",
    "canonical_copy": "canonical writer copied bytes",
    "canonical_import_failed": "canonical import failed",
    "identity_conflict_no_download": "identity conflict suppresses download",
    "explicit_security_id_conflicts_with_verified_identity": "explicit id conflicts with verified identity",
    "download_required_but_not_allowed": "gap exists but download is not allowed",
    "only_sources_published_after_as_of_date": "all candidates publish after as-of",
    "no_existing_source_satisfies_request": "no catalog source satisfies the request",
    "reused_after_discovery": "catalog hit after provider discovery",
    # artifact binding gate
    "artifact_schema_unsupported": "artifact schema version unknown",
    "artifact_status_not_completed": "artifact status is not completed",
    "artifact_source_binding_mismatch": "artifact source does not match lineage",
    "artifact_hash_malformed": "artifact hash is not lowercase hex",
    "artifact_hash_mismatch": "artifact hash differs from bytes",
    "artifact_file_missing": "artifact file is missing on disk",
    "artifact_generator_unregistered": "generator not in GENERATOR_REGISTRY",
    "artifact_created_at_malformed": "created_at is not ISO-8601 Z",
    "artifact_created_at_future": "created_at is in the future",
    "artifact_path_outside_allowed_root": "artifact path outside allowed roots",
    "artifact_role_unknown": "artifact role not in KNOWN_ARTIFACT_ROLES",
    "artifact_source_sha_mismatch": "artifact source sha differs from source",
    "artifact_source_as_of_future": "artifact source as-of is in the future",
    "artifact_superseded_by_newer": "a newer artifact exists for the role",
    # worker / control plane
    "unhandled_exception": "worker cycle hit an unhandled exception",
    "cycle_failed": "worker cycle failed",
    "productive_cycle": "worker cycle made progress",
    "already_running": "operation already running",
    "control_request": "control-plane request processed",
    "persistent_pause": "worker paused persistently",
    "semantic_review_only": "semantic review path only",
    "clean_exit": "process exited cleanly",
    "no_output": "no output produced",
    # latest / gap
    "gap_already_closed": "gap closed by an earlier transaction",
    "gap_closed_by_concurrent": "gap closed by a concurrent transaction",
    # documents / scanning
    "document_not_in_catalog": "document missing from catalog",
    "source_not_in_catalog": "source missing from catalog",
    "no_original_location": "document has no original_primary location",
    "empty_text": "source text is empty",
    "unsupported_document": "document kind unsupported",
    "cannot_parse_yaml": "yaml payload cannot be parsed",
    "unexpected_path_pattern": "path pattern outside expectations",
    "focus_policy_orphan_sidecar": "sidecar without its primary file",
    # llm pipeline
    "llm_deferred": "llm summary deferred",
    "llm_global_failure": "llm pipeline failed globally",
    "fiscal_year": "fiscal-year filter applied",
}

_PATH_PATTERN = re.compile(r"[A-Za-z]:[\\/][^;,\s]+|[\\/][^;,\s]*[\\/][^;,\s]+")

REDACT = "<redacted>"


def validate_reason(code: str) -> bool:
    """Fail closed: only registered codes may be recorded."""
    return code in REASONS


@dataclass
class Metric:
    """One observable event.  Free-form fields are redacted on export."""

    dimension: str          # root_id | route | adapter_id | role | reason
    key: str                # e.g. a root_id | an adapter_id
    count: int = 1


@dataclass
class ObservabilityReport:
    schema_version: str = f"reason-taxonomy-{REASON_TAXONOMY_VERSION}"
    metrics: list[Metric] = field(default_factory=list)
    latency_p50: float | None = None
    latency_p95: float | None = None
    latency_p99: float | None = None
    db_busy: int = 0
    db_timeout: int = 0
    subprocess_failures: int = 0
    legacy_bridge_hits: int = 0
    shadow_diffs: int = 0
    migration_remaining: int = 0
    raw: list[dict] = field(default_factory=list)

    def aggregate(self, dimension: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for metric in self.metrics:
            if metric.dimension == dimension:
                out[metric.key] = out.get(metric.key, 0) + metric.count
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "metrics": [m.__dict__ for m in self.metrics],
            "aggregated": {
                dim: self.aggregate(dim)
                for dim in ("root_id", "route", "adapter_id", "role", "reason")
            },
            "latency_p50": self.latency_p50,
            "latency_p95": self.latency_p95,
            "latency_p99": self.latency_p99,
            "db_busy": self.db_busy,
            "db_timeout": self.db_timeout,
            "subprocess_failures": self.subprocess_failures,
            "legacy_bridge_hits": self.legacy_bridge_hits,
            "shadow_diffs": self.shadow_diffs,
            "migration_remaining": self.migration_remaining,
        }


class MetricsCollector:
    """Thread-safe append-only collector.  Never raises; exporter optional."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._report = ObservabilityReport()

    def record(self, dimension: str, key: str, *, redact: bool = True) -> None:
        if redact:
            key = _PATH_PATTERN.sub(REDACT, str(key))
        with self._lock:
            self._report.metrics.append(Metric(dimension=dimension, key=key))

    def record_reason(self, code: str) -> bool:
        """Record a reason code; unknown codes are refused (fail closed)."""
        if not validate_reason(code):
            return False
        with self._lock:
            self._report.metrics.append(Metric(dimension="reason", key=code))
            if code == "legacy_bridge_hit":
                self._report.legacy_bridge_hits += 1
            elif code == "shadow_diff":
                self._report.shadow_diffs += 1
            elif code == "migration_remaining":
                self._report.migration_remaining += 1
        return True

    def record_latency(self, samples: list[float]) -> None:
        if not samples:
            return
        ordered = sorted(samples)
        n = len(ordered)
        # nearest-rank percentiles: index = ceil(q * n) - 1
        def pct(q: float) -> float:
            return ordered[math.ceil(q * n) - 1]

        with self._lock:
            self._report.latency_p50 = pct(0.50)
            self._report.latency_p95 = pct(0.95)
            self._report.latency_p99 = pct(0.99)

    def record_db(self, *, busy: int = 0, timeout: int = 0) -> None:
        with self._lock:
            self._report.db_busy += busy
            self._report.db_timeout += timeout

    def record_subprocess_failure(self) -> None:
        with self._lock:
            self._report.subprocess_failures += 1

    def snapshot(self) -> ObservabilityReport:
        with self._lock:
            return self._report

    def reset(self) -> None:
        with self._lock:
            self._report = ObservabilityReport()
