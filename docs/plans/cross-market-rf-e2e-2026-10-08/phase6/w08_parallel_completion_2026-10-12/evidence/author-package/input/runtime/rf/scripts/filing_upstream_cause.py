"""Decode the versioned FF failure diagnostic; no research or retry decision."""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

SCHEMA_VERSION = "filing-upstream-cause/1"
KEYS = frozenset({"schema_version", "operation", "code", "provider_started", "usage_complete", "retry_scope"})
OPERATIONS = frozenset({"identify", "ensure", "resolve", "close-gap", "query", "local_prepare"})
STAGES = OPERATIONS | {"source_query", "source_operation", "ambiguous", "not_found", "upstream_error",
                       "source_reader", "source_record", "narrative_reader"}
RETRY_SCOPES = frozenset({"none", "catalog_contention", "caller_decision"})
# Versioned public vocabulary, not runtime imports of a provider's private files.
CODES = frozenset({
    "catalog_locked", "catalog_busy", "db_timeout", "worker_paused", "legacy_evidence_archived", "fatal",
    "maintenance_operation_retired", "producer_start_failed", "producer_deadline_exceeded",
    "producer_output_exceeded", "producer_transport_failure", "unknown",
    "adapter_process_failed", "adapter_timeout", "adapter_output_limit", "adapter_response_invalid",
    "adapter_not_bounded", "upstream_unavailable", "network_failed", "budget_exceeded", "provider_failed",
    "provider_not_configured", "invalid_request", "invalid_budget", "invalid_candidate", "missing_scratch",
    "invalid_scratch", "unsupported_language", "unsupported_sec_form", "unsupported_hk_period",
    "identity_mismatch", "invalid_provider_metadata", "primary_missing", "fiscal_period_unresolved",
    "missing_response", "staging_conflict", "sdk_asset_mismatch", "deadline_exceeded",
    "byte_budget_exceeded", "cost_budget_exceeded", "unsupported_content_encoding", "incomplete_response",
    "acquisition_budget_exceeded", "acquisition_validation_failed", "canonical_import_failed",
    "local_metadata_gap", "no_registered_local_source", "no_local_match", "source_not_found", "invalid_producer_schema",
})
ACQUISITION_CODES = CODES - {"catalog_locked", "catalog_busy", "db_timeout", "worker_paused", "legacy_evidence_archived", "fatal",
    "maintenance_operation_retired", "producer_start_failed", "producer_deadline_exceeded", "producer_output_exceeded",
    "producer_transport_failure", "unknown", "local_metadata_gap", "no_registered_local_source", "no_local_match",
    "source_not_found", "invalid_producer_schema"}
FAILURE_STATUSES = frozenset({"fatal", "upstream_error", "not_found", "gap", "source_blocked", "ambiguous", "identity_error",
                            "request_error", "config_error", "catalog_locked", "catalog_busy", "db_timeout", "worker_paused"})
SAFE_REASONS = CODES | {"provider_unavailable", "metadata_only_gap_plan", "not_published", "reader_unavailable"}
SOURCE_FAILURE_REASONS = frozenset({
    "invalid_read_policy_pin", "catalog_unavailable", "candidate_budget_exceeded", "document_not_indexed",
    "source_not_active", "document_source_mismatch", "source_version_not_indexed", "expected_version_mismatch",
    "source_ref_changed", "unsupported_version", "unsupported_purpose", "no_indexed_location",
    "root_admission_denied", "verification_invariant_broken", "no_verified_location", "reader_unavailable",
    "source_availability_unknown", "source_identity_mismatch", "source_period_mismatch",
    "document_kind_mismatch", "fiscal_year_mismatch", "fiscal_period_mismatch", "source_bytes_mismatch",
    "source_candidate_invalid", "source_clock_invalid_date", "source_availability_invalid",
    "source_availability_version_mismatch", "source_publication_after_asof", "source_availability_after_asof",
    "source_clock_conflict",
    "primary_issuer_conflict", "primary_scope_conflict", "primary_identity_unresolved",
    "fiscal_period_unresolved",
})


def validated_source_failure_reason(value: Any) -> str | None:
    return value if isinstance(value, str) and value in SOURCE_FAILURE_REASONS else None


def _candidate_token(value: Any, *, maximum: int = 256) -> bool:
    return isinstance(value, str) and len(value) <= maximum and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._-]*", value) is not None


def _candidate_name(value: Any) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= 256 and value == value.strip()
            and not any(ord(char) < 32 for char in value)
            and not any(marker in value for marker in ("://", "?", "=", "\\")))


def _candidate_reference(value: Any) -> dict[str, Any] | None:
    """Project a logical reference only; opening bytes remains CWP's job."""
    fields = {"schema_version", "document_id", "source_id", "content_sha256", "byte_size", "mime_type"}
    if not isinstance(value, dict) or set(value) != fields or value["schema_version"] != "2.0":
        return None
    sha = value["content_sha256"]
    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{64}", sha) is None:
        return None
    if type(value["byte_size"]) is not int or value["byte_size"] < 0:
        return None
    # Format support belongs to CWP's parser/reader. This consumer only
    # projects a bounded MIME token; it must not maintain a second capability list.
    if (not isinstance(value["mime_type"], str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}", value["mime_type"]) is None):
        return None
    for key, kind in (("document_id", "document"), ("source_id", "source")):
        identifier = value[key]
        if not _candidate_token(identifier):
            return None
        if identifier.startswith("urn:company-wiki:") and identifier != f"urn:company-wiki:{kind}:sha256:{sha}":
            return None
    return dict(value)


def validated_failure_candidates(value: Any) -> list[dict[str, Any]] | None:
    """A failure may expose identity/SourceRef DTOs, never arbitrary bodies.

    Historical identity candidates need only the four disambiguation fields.
    Unrecognized wrapper fields, provider URLs and nested diagnostic objects
    are not part of that public projection. This is not identity resolution.
    """
    if not isinstance(value, list):
        return None
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        candidate = {}
        if (_candidate_name(item.get("canonical_name")) and isinstance(item.get("market"), str) and item["market"] in {"CN", "HK", "US"}
                and _candidate_token(item.get("ticker"), maximum=32)
                and _candidate_token(item.get("exchange"), maximum=32)):
            candidate.update({key: item[key] for key in ("ticker", "canonical_name", "market", "exchange")})
            for key in ("security_id", "entity_id"):
                if _candidate_token(item.get(key)):
                    candidate[key] = item[key]
        reference = _candidate_reference(item.get("source_ref"))
        if reference is not None:
            candidate["source_ref"] = reference
        if candidate:
            result.append(candidate)
    return result or None


def validated_cause(value: Any) -> dict[str, Any] | None:
    """Retain only a safe six-field wire object, preserving bool/null exactly."""
    if not isinstance(value, dict) or set(value) != KEYS:
        return None
    if any(not isinstance(value[field], str) for field in ("schema_version", "operation", "code", "retry_scope")):
        return None
    if value["schema_version"] != SCHEMA_VERSION or value["operation"] not in OPERATIONS:
        return None
    if value["code"] not in CODES or value["retry_scope"] not in RETRY_SCOPES:
        return None
    if any(value[field] is not None and type(value[field]) is not bool for field in ("provider_started", "usage_complete")):
        return None
    return dict(value)


REQUEST_DIAGNOSTIC_SCHEMA = "filing-request-diagnostic/1"
REQUEST_DIAGNOSTIC_PATHS = {
    "exact_requires_fiscal_year": frozenset({"fiscal_year"}),
    "latest_forbids_fiscal_year": frozenset({"fiscal_year"}),
    "latest_reuse_requires_acquisition_limits": frozenset({"acquisition_limits"}),
    "acquisition_limits_invalid": frozenset({"acquisition_limits", "acquisition_limits.max_bytes",
        "acquisition_limits.timeout_seconds", "acquisition_limits.max_cost_usd"}),
}


def validated_request_diagnostic(value: Any) -> dict[str, Any] | None:
    """An optional closed sibling; the original six-field cause is unchanged."""
    if not isinstance(value, dict) or set(value) != {"schema_version", "reason", "field_path"}:
        return None
    if value["schema_version"] != REQUEST_DIAGNOSTIC_SCHEMA or not isinstance(value["reason"], str):
        return None
    paths = REQUEST_DIAGNOSTIC_PATHS.get(value["reason"])
    if paths is None or not isinstance(value["field_path"], str) or value["field_path"] not in paths:
        return None
    return dict(value)


def failure_detail(payload: dict[str, Any]) -> dict[str, Any]:
    """A v2 filing's failure is independent of its transcript companion."""
    child = payload.get("filing")
    return child if payload.get("schema_version") == "2.0" and isinstance(child, dict) else payload


def validated_acquisition_failure(value: Any) -> dict[str, Any] | None:
    """Pure validation of existing CWP operation accounting, without settlement."""
    keys = {"schema_version", "code", "retryable", "provider_started", "usage_complete", "acquisition_usage", "usage_scope"}
    if not isinstance(value, dict) or set(value) != keys:
        return None
    if value.get("schema_version") != "acquisition-failure/1" or value.get("usage_scope") != "operation":
        return None
    if not isinstance(value["code"], str) or value["code"] not in ACQUISITION_CODES:
        return None
    if any(value[field] is not None and type(value[field]) is not bool for field in ("retryable", "provider_started", "usage_complete")):
        return None
    usage = value["acquisition_usage"]
    if usage is not None:
        if not isinstance(usage, dict) or set(usage) != {"schema_version", "response_bytes", "cost_usd"}:
            return None
        if usage["schema_version"] != "1.0" or type(usage["response_bytes"]) is not int or usage["response_bytes"] < 0 or not isinstance(usage["cost_usd"], str):
            return None
        try:
            amount = Decimal(usage["cost_usd"])
        except InvalidOperation:
            return None
        if not amount.is_finite() or amount < 0:
            return None
    return {**value, "acquisition_usage": dict(usage) if usage is not None else None}


# M3-USAGE: observed-usage sibling. Pure validation of the producer's
# operation observation; no recomputation, no fee inference, no MIME or
# identity re-verification — values pass through or the object is dropped.
ACQUISITION_OBSERVATION_SCHEMA = "acquisition-observation/1"
OBSERVATION_OUTCOMES = frozenset({
    "downloaded_new", "deduplicated_after_download",
    "reused_before_download", "reused_after_discovery",
    "missing", "ambiguous", "gap_plan", "gap_plan_provider_unavailable",
    "failed",
})
_OBSERVATION_KEYS = frozenset({
    "schema_version", "usage_scope", "outcome", "provider_started",
    "usage_complete", "wire_body_bytes", "wire_usage_complete",
    "entity_body_bytes", "http_exchanges", "http_exchanges_complete",
    "cost_usd", "http_observation",
})
_HTTP_OBSERVATION_KEYS = frozenset({
    "status_code", "mime_type", "content_encoding", "wire_content_length",
})


def validated_acquisition_observation(value: Any) -> dict[str, Any] | None:
    """Copy the operation observation iff it matches the closed contract."""
    if not isinstance(value, dict) or set(value) != _OBSERVATION_KEYS:
        return None
    if (value["schema_version"] != ACQUISITION_OBSERVATION_SCHEMA
            or value["usage_scope"] != "operation"):
        return None
    outcome = value.get("outcome")
    if not isinstance(outcome, str) or outcome not in OBSERVATION_OUTCOMES:
        return None
    result: dict[str, Any] = {
        "schema_version": ACQUISITION_OBSERVATION_SCHEMA,
        "usage_scope": "operation",
        "outcome": outcome,
    }
    for key in ("provider_started", "usage_complete", "wire_usage_complete",
                "http_exchanges_complete"):
        flag = value.get(key)
        if flag is not None and type(flag) is not bool:
            return None
        result[key] = flag
    for key in ("wire_body_bytes", "entity_body_bytes"):
        count = value.get(key)
        if type(count) is not int or count < 0:
            return None
        result[key] = count
    exchanges = value.get("http_exchanges")
    if type(exchanges) is not int or exchanges < 0:
        return None
    result["http_exchanges"] = exchanges
    cost = value.get("cost_usd")
    if cost is not None:
        if not isinstance(cost, str):
            return None
        try:
            amount = Decimal(cost)
        except (InvalidOperation, ValueError):
            return None
        if not amount.is_finite() or amount < 0:
            return None
    result["cost_usd"] = cost
    http_observation = value.get("http_observation")
    if http_observation is not None:
        if (not isinstance(http_observation, dict)
                or set(http_observation) != _HTTP_OBSERVATION_KEYS):
            return None
        status = http_observation.get("status_code")
        if type(status) is not int or status < 0:
            return None
        checked: dict[str, Any] = {"status_code": status}
        for key in ("mime_type", "content_encoding"):
            text = http_observation.get(key)
            if not isinstance(text, str) or not text or len(text) > 128:
                return None
            checked[key] = text
        length = http_observation.get("wire_content_length")
        if length is not None and (type(length) is not int or length < 0):
            return None
        checked["wire_content_length"] = length
        http_observation = checked
    result["http_observation"] = http_observation
    return result


def failure_observation(payload: Any) -> dict[str, Any]:
    """Only allowlisted observed facts cross both RF subprocess boundaries."""
    if not isinstance(payload, dict):
        return {}
    detail = failure_detail(payload)
    result: dict[str, Any] = {}
    cause = validated_cause(detail.get("upstream_cause"))
    diagnostic = validated_request_diagnostic(detail.get("request_diagnostic"))
    receipt = validated_acquisition_failure(detail.get("acquisition_failure"))
    # M3-USAGE: the operation observation is an envelope-level account (like
    # calls/downloads); the detail fallback keeps older flat shapes readable.
    observation = validated_acquisition_observation(payload.get("acquisition_observation"))
    if observation is None:
        observation = validated_acquisition_observation(detail.get("acquisition_observation"))
    if cause is not None:
        result["upstream_cause"] = cause
    if diagnostic is not None:
        result["request_diagnostic"] = diagnostic
    if receipt is not None:
        result["acquisition_failure"] = receipt
    if observation is not None:
        result["acquisition_observation"] = observation
    reason = validated_source_failure_reason(detail.get("source_failure_reason"))
    if reason is not None:
        result["source_failure_reason"] = reason
    stage = detail.get("stage")
    if isinstance(stage, str) and stage in STAGES:
        result["stage"] = stage
    for key in ("attempts", "calls", "downloads"):
        value = detail.get(key) if key == "attempts" else payload.get(key)
        if type(value) is int and value >= 0:
            result[key] = value
    return result


def safe_failure_message(payload: Any, *, prefix: str) -> str:
    """A fixed message plus finite real subtype; raw errors/URLs stay private."""
    if not isinstance(payload, dict):
        return prefix + ": invalid upstream error document"
    detail = failure_detail(payload)
    status = detail.get("error_code") or detail.get("status") or payload.get("status")
    status = status if isinstance(status, str) and status in FAILURE_STATUSES else "unknown"
    cause = validated_cause(detail.get("upstream_cause"))
    reason = cause["code"] if cause is not None else detail.get("reason")
    reason = reason if isinstance(reason, str) and reason in SAFE_REASONS else "unspecified"
    return f"{prefix}: status={status}: {reason}"


def extract_cause(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    return validated_cause(failure_detail(payload).get("upstream_cause"))


def parse_error_document(text: str) -> dict[str, Any] | None:
    """Decode a small stderr JSON error once; legacy text remains legacy text."""
    if len(text) > 65536:
        return None
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None
