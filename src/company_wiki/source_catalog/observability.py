"""WU-1305: versioned reason taxonomy + privacy-safe metrics collector.

Every rejection/reuse/download/recompute carries a *registered* reason code
(snake_case, versioned by REASON_TAXONOMY_VERSION).  The collector aggregates
by root/route/adapter/version/role without ever recording company names,
document ids, or absolute paths — those are redacted by default (REDACT).

Telemetry export being off must not affect core behavior: the collector is
pure in-memory, append-only, and thread-safe; nothing raises when the
exporter is absent.

ZR-101 (stage taxonomy 2.0): on top of the flat v1.1 reason codes, every
registered reason is attributed to at least one of eight cross-repo stages
(identity, resolution, freshness, acquisition, safety, artifact, semantic,
consumer).  Stage events are validated fail closed: unknown codes/stages are
never silently recorded, and an N-1 consumer that only knows
reason-taxonomy-1.1 rejects a stage-taxonomy-2.0 event with a problems list
instead of crashing.
"""

from __future__ import annotations

import math
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
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
    # ZR-502 homepage identity — verdict evidence codes
    "no_first_page_text": "no first-page text was extracted",
    "no_declared_identity_on_cover": "cover contradicts declared identity",
    "no_strong_cover_framing": "page is not recognizably a cover",
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


# ---------------------------------------------------------------------------
# ZR-101: cross-repo stage taxonomy 2.0 (additive over the flat v1.1 codes).
# Every v1.1 reason code is attributed to >=1 of the eight canonical stages;
# nothing in REASONS is renamed or removed, so an N-1 consumer that only
# knows reason-taxonomy-1.1 keeps working and rejects 2.0 events gracefully.
# ---------------------------------------------------------------------------
STAGE_TAXONOMY_VERSION = "2.0"
STAGE_TAXONOMY_SCHEMA = "stage-taxonomy-2.0"


class CrossRepoStage(str, Enum):
    """The eight cross-repo pipeline stages, in canonical order.

    Members are named by their canonical snake_case stage name and carry
    that same snake_case string as their value (str, Enum) — e.g.
    ``CrossRepoStage.identity.value == "identity"``.
    """

    identity = "identity"
    resolution = "resolution"
    freshness = "freshness"
    acquisition = "acquisition"
    safety = "safety"
    artifact = "artifact"
    semantic = "semantic"
    consumer = "consumer"


_REGISTERED_STAGES = frozenset(stage.value for stage in CrossRepoStage)

# Attribution rules (documented for cross-repo consistency — revenue-forecast
# and filing-fetch consume this map in later cards):
#   identity    — entity/security identity + admission profile gates
#   resolution  — matching/disambiguation of issuer/handle/source
#   freshness   — as-of date, period, gap analysis, timeliness
#   acquisition — download/fetch/staging/canonical copy of bytes
#   safety      — prompt-safety vocabulary (none registered yet; reserved)
#   artifact    — artifact schema/hash/binding/status + path-policy checks
#   semantic    — content/meaning-level decisions
#   consumer    — downstream consumption: recompute, migration, legacy bridge
STAGES_BY_REASON: dict[str, tuple[str, ...]] = {
    # identity
    "admitted": ("identity",),
    "identity_missing": ("identity",),
    "kind_missing": ("identity",),
    "entity_gate_rejected": ("identity",),
    "identity_conflict_no_download": ("identity",),
    "explicit_security_id_conflicts_with_verified_identity": ("identity",),
    # resolution
    "exact_hit": ("resolution",),
    "latest_selected": ("resolution",),
    "ambiguous_issuer": ("resolution",),
    "existing_catalog_source_reused_before_adapter": ("resolution",),
    "existing_catalog_source_reused_after_discovery": ("resolution",),
    "reused_after_discovery": ("resolution",),
    # freshness
    "period_missing": ("freshness",),
    "gap_not_required": ("freshness",),
    "gap_authorization_expired": ("freshness",),
    "only_sources_published_after_as_of_date": ("freshness",),
    "no_existing_source_satisfies_request": ("freshness",),
    "gap_already_closed": ("freshness",),
    "gap_closed_by_concurrent": ("freshness",),
    "fiscal_year": ("freshness",),
    # acquisition
    "download_suppressed": ("acquisition",),
    "download_authorized": ("acquisition",),
    "downloaded": ("acquisition",),
    "adapter_discovery_returned_multiple_candidates": ("acquisition",),
    "adapter_discovery_returned_no_candidate": ("acquisition",),
    "adapter_or_staging_failed": ("acquisition",),
    "missing_source_downloaded_to_staging_pending_canonical_import": ("acquisition",),
    "canonical_copy": ("acquisition",),
    "canonical_import_failed": ("acquisition",),
    "download_required_but_not_allowed": ("acquisition",),
    "no_original_location": ("acquisition",),
    # safety — no registered codes yet (stage reserved for prompt-safety)
    # artifact
    "hash_missing": ("artifact",),
    "content_hash_mismatch": ("artifact",),
    "focus_policy_invalid_relative_path": ("artifact",),
    "artifact_selected": ("artifact",),
    "artifact_rejected": ("artifact",),
    "stale_bundle": ("artifact",),
    "artifact_schema_unsupported": ("artifact",),
    "artifact_status_not_completed": ("artifact",),
    "artifact_source_binding_mismatch": ("artifact",),
    "artifact_hash_malformed": ("artifact",),
    "artifact_hash_mismatch": ("artifact",),
    "artifact_file_missing": ("artifact",),
    "artifact_generator_unregistered": ("artifact",),
    "artifact_created_at_malformed": ("artifact",),
    "artifact_created_at_future": ("artifact",),
    "artifact_path_outside_allowed_root": ("artifact",),
    "artifact_role_unknown": ("artifact",),
    "artifact_source_sha_mismatch": ("artifact",),
    "artifact_source_as_of_future": ("artifact",),
    "artifact_superseded_by_newer": ("artifact",),
    "unexpected_path_pattern": ("artifact",),
    "focus_policy_orphan_sidecar": ("artifact",),
    # semantic
    "non_filing_kind": ("semantic",),
    "focus_policy_no_allowed_category_evidence": ("semantic",),
    "semantic_review_only": ("semantic",),
    "empty_text": ("semantic",),
    "unsupported_document": ("semantic",),
    "cannot_parse_yaml": ("semantic",),
    "llm_deferred": ("semantic",),
    "llm_global_failure": ("semantic",),
    # ZR-502 homepage identity — content-level verdict evidence
    "no_first_page_text": ("semantic",),
    "no_declared_identity_on_cover": ("semantic",),
    "no_strong_cover_framing": ("semantic",),
    # consumer
    "status_not_active": ("consumer",),
    "policy_denied": ("consumer",),
    "recomputed": ("consumer",),
    "legacy_bridge_hit": ("consumer",),
    "shadow_diff": ("consumer",),
    "migration_remaining": ("consumer",),
    "verified_v2_assertion": ("consumer",),
    "unhandled_exception": ("consumer",),
    "cycle_failed": ("consumer",),
    "productive_cycle": ("consumer",),
    "already_running": ("consumer",),
    "control_request": ("consumer",),
    "persistent_pause": ("consumer",),
    "clean_exit": ("consumer",),
    "no_output": ("consumer",),
    "document_not_in_catalog": ("consumer",),
    "source_not_in_catalog": ("consumer",),
}


def stage_sequence() -> tuple[CrossRepoStage, ...]:
    """Canonical cross-repo stage order (taxonomy 2.0)."""
    return tuple(CrossRepoStage)


def is_registered_stage(stage: str) -> bool:
    """True when *stage* is one of the eight canonical stage names."""
    return stage in _REGISTERED_STAGES


def stages_for_reason(code: str) -> tuple[str, ...]:
    """Attributed stages for a registered reason code (canonical order).

    Fail closed: unknown codes raise ValueError instead of being silently
    attributed.
    """
    if code not in REASONS:
        raise ValueError(f"unknown reason code: {code!r}")
    return STAGES_BY_REASON[code]


def _utc_now_iso() -> str:
    """Current UTC instant as ISO-8601 with a trailing ``Z``."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@dataclass
class StageEvent:
    """One stage-attributed cross-repo event (stage-taxonomy-2.0).

    ``detail`` is sanitized on validation: path-like patterns are redacted
    to ``REDACT`` (never rejected).  ``emitted_at_utc`` defaults to the
    current UTC instant.
    """

    schema_version: str = STAGE_TAXONOMY_SCHEMA
    stage: str = ""
    reason: str = ""
    detail: str | None = None
    emitted_at_utc: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stage": self.stage,
            "reason": self.reason,
            "detail": self.detail,
            "emitted_at_utc": self.emitted_at_utc,
        }


def _redact_detail(detail: Any) -> Any:
    """Replace path-like patterns in *detail* with REDACT (never raises)."""
    if not isinstance(detail, str):
        return detail
    return _PATH_PATTERN.sub(REDACT, detail)


def _is_iso8601_utc(value: Any) -> bool:
    """True for ISO-8601 timestamps carrying an explicit UTC offset."""
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _schema_problems(schema_version: Any) -> list[str]:
    if schema_version == STAGE_TAXONOMY_SCHEMA:
        return []
    return [f"schema_version must be {STAGE_TAXONOMY_SCHEMA!r}, got {schema_version!r}"]


def _stage_problems(stage: Any) -> list[str]:
    if is_registered_stage(stage):
        return []
    return [f"unknown stage: {stage!r}"]


def _reason_stage_problems(reason: Any, stage: Any) -> list[str]:
    if reason not in REASONS:
        return [f"unknown reason: {reason!r}"]
    if is_registered_stage(stage) and stage not in STAGES_BY_REASON[reason]:
        return [f"reason {reason!r} not attributed to stage {stage!r}"]
    return []


def _emitted_at_problems(value: Any) -> list[str]:
    if _is_iso8601_utc(value):
        return []
    return [f"emitted_at_utc is not ISO-8601: {value!r}"]


def validate_stage_event(event: dict | StageEvent) -> list[str]:
    """Validate a stage event; returns problems (empty list == valid).

    Fail closed: wrong/missing schema_version, unknown stage, unknown
    reason, a reason not attributed to the declared stage, and non-ISO-8601
    emitted_at_utc are reported as problems.  Path-like ``detail`` is
    redacted in place (stored as ``REDACT``) instead of rejected.  Never
    raises on invalid input.
    """
    problems: list[str] = []
    if isinstance(event, StageEvent):
        schema_version = event.schema_version
        stage = event.stage
        reason = event.reason
        detail = event.detail
        emitted_at_utc = event.emitted_at_utc
        event.detail = _redact_detail(detail)
    elif isinstance(event, dict):
        schema_version = event.get("schema_version")
        stage = event.get("stage")
        reason = event.get("reason")
        detail = event.get("detail")
        emitted_at_utc = event.get("emitted_at_utc")
        event["detail"] = _redact_detail(detail)
    else:
        return ["event must be a dict or StageEvent"]
    problems.extend(_schema_problems(schema_version))
    problems.extend(_stage_problems(stage))
    problems.extend(_reason_stage_problems(reason, stage))
    problems.extend(_emitted_at_problems(emitted_at_utc))
    return problems


@dataclass
class Metric:
    """One observable event.  Free-form fields are redacted on export."""

    dimension: str  # root_id | route | adapter_id | role | reason
    key: str  # e.g. a root_id | an adapter_id
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

    def record_stage_event(self, event: StageEvent) -> bool:
        """Record a stage-attributed event; refused when validation fails.

        Fail closed: an invalid event (see ``validate_stage_event``) is
        refused (False) and never stored.  Valid events append their dict
        form — with path-like detail already redacted — to the report's raw
        log.  The v1.1 ``record_reason`` contract is unaffected.
        """
        if validate_stage_event(event):
            return False
        with self._lock:
            self._report.raw.append(event.to_dict())
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
