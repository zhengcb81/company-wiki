"""Pathless, versioned results for acquisition-capable source operations."""

from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any

from .source_reader import SourceRef, SourceVersionReader


OPERATION_SCHEMA_VERSION = "1.0"

_GAP_FIELDS = frozenset({
    "schema_version", "request_id", "as_of_date", "document_kind",
    "entity", "market", "fiscal_year", "fiscal_period", "form_type",
    "gap_hash", "not_published", "provider_unavailable",
})
_GAP_ITEM_FIELDS = frozenset({
    "provider", "provider_document_id", "accession", "source_url",
    "published_date", "filing_date", "form_type", "fiscal_year",
    "fiscal_period", "period_end", "reason",
})
_PHYSICAL_FIELD_PARTS = ("path", "location", "root", "bundle")


class SourceOperationProjectionError(ValueError):
    """An acquisition result cannot be represented by the pathless contract."""


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _gap_projection(value: object) -> dict[str, Any] | None:
    gap = _mapping(value)
    if not gap:
        return None
    projected = {key: gap[key] for key in _GAP_FIELDS if key in gap}
    for group in ("missing", "newer_revision", "future"):
        entries = gap.get(group)
        if not isinstance(entries, list):
            continue
        projected[group] = [
            {key: item[key] for key in _GAP_ITEM_FIELDS if key in item}
            for item in entries
            if isinstance(item, dict)
        ]
    return projected


def _contains_physical_field(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            any(part in str(key).lower() for part in _PHYSICAL_FIELD_PARTS)
            or _contains_physical_field(child)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_physical_field(child) for child in value)
    return False


def _result_and_resolution(
    payload: dict[str, Any], operation: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = _mapping(payload.get("source_ensure")) if operation == "ensure" else {}
    if not result:
        result = _mapping(payload.get("close_gap")) if operation == "close-gap" else {}
    if not result:
        result = payload
    resolution = _mapping(result.get("resolution"))
    if not resolution and operation == "close-gap":
        resolution = _mapping(payload.get("resolution"))
    envelope = _mapping(result.get("envelope"))
    if not envelope:
        envelope = _mapping(resolution.get("resolution_envelope"))
    # This is the public acquisition result DTO, not the legacy metadata_json
    # identity container. Keep the input field explicit to avoid overloading
    # that legacy name at the source-operation boundary.
    acquisition = _mapping(result.get("acquisition_result"))
    return result, resolution, {**envelope, "_acquisition": acquisition}


def _download_events(result: dict[str, Any], envelope: dict[str, Any]) -> int:
    value = envelope.get("download_events")
    if value is None:
        value = result.get("fetch_events")
    if value is None:
        value = result.get("download_events", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SourceOperationProjectionError("invalid download event count")
    return value


def project_operation_result(
    payload: dict[str, Any],
    *,
    operation: str,
    reader: SourceVersionReader,
) -> dict[str, Any]:
    """Project ensure/close-gap output without exposing storage locations.

    latest_as_of intentionally reaches this acquisition-capable operation,
    not the pure DB-only local query. The catalog reader then binds the exact
    resolved version and returns only its pathless reference and metadata.
    """
    if operation not in {"ensure", "close-gap"}:
        raise ValueError("operation must be ensure or close-gap")
    if not isinstance(payload, dict):
        raise TypeError("payload and reader have invalid types")

    result, resolution, envelope = _result_and_resolution(payload, operation)
    acquisition = envelope.pop("_acquisition", {})
    gap = _gap_projection(acquisition.get("gap_plan") or result.get("gap_plan"))
    attempt = _mapping(result.get("attempt"))
    outcome = (
        envelope.get("outcome")
        or result.get("outcome")
        or attempt.get("outcome")
    )
    downloads = _download_events(result, envelope)
    request_id = (
        result.get("request_id")
        or resolution.get("request_id")
        or (gap or {}).get("request_id")
        or payload.get("request_id")
    )
    matches = resolution.get("matches")
    if gap is not None or result.get("status") == "gap":
        status = "gap"
        ref = candidate = None
    elif isinstance(matches, list) and len(matches) == 1 and isinstance(matches[0], dict):
        match = matches[0]
        document_id = match.get("document_id")
        source_id = match.get("source_id")
        digest = match.get("snapshot_sha256") or match.get("content_sha256")
        if not all(isinstance(item, str) and item for item in (document_id, source_id, digest)):
            raise SourceOperationProjectionError("resolved source identity is incomplete")
        ref = reader.query_ref(document_id, source_id, digest)
        if (
            ("byte_size" in match and match["byte_size"] != ref.byte_size)
            or ("mime_type" in match and match["mime_type"] != ref.mime_type)
        ):
            raise SourceOperationProjectionError("resolved source version changed")
        candidate = reader.describe_candidate(ref)
        status = "completed"
        request_id = request_id or resolution.get("request_id")
    elif result.get("status") == "ambiguous" or resolution.get("status") == "ambiguous":
        status = "ambiguous"
        ref = candidate = None
    elif result.get("status") in {"missing", "not_found"} or resolution.get("status") == "missing":
        status = "not_found"
        ref = candidate = None
    else:
        status = "unavailable"
        ref = candidate = None

    if candidate is not None and _contains_physical_field(candidate):
        raise SourceOperationProjectionError("candidate contains a physical field")
    policy_hash = envelope.get("policy_hash")
    if policy_hash is not None and (
        not isinstance(policy_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", policy_hash)
    ):
        raise SourceOperationProjectionError("invalid policy hash")

    projected = {
        "operation_schema_version": OPERATION_SCHEMA_VERSION,
        "operation": operation,
        "status": status,
        "request_id": request_id,
        "outcome": outcome,
        "download_events": downloads,
        "policy_hash": policy_hash,
        "source_ref": asdict(ref) if isinstance(ref, SourceRef) else None,
        "candidate": candidate,
        "gap_plan": gap if status == "gap" else None,
    }
    if _contains_physical_field(projected):
        raise SourceOperationProjectionError("operation result contains a physical field")
    return projected
