"""Pure pathless projection over a validated source operation input."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, cast, Protocol

from .operation_contract import (
    SourceOperationInput,
    SourceOperationProjectionError,
)
from .source_reader import SourceRef


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


class VersionReader(Protocol):
    """Read-side port required by the operation projector."""

    def query_ref(
        self, document_id: str, source_id: str, sha256: str,
    ) -> SourceRef: ...

    def describe_candidate(self, ref: SourceRef) -> dict[str, object]: ...


def _gap_projection(gap: dict[str, Any] | None) -> dict[str, Any] | None:
    if gap is None:
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


def _identity(match: dict[str, Any]) -> tuple[str, str, str]:
    values = (
        match.get("document_id"),
        match.get("source_id"),
        match.get("snapshot_sha256") or match.get("content_sha256"),
    )
    if not all(isinstance(item, str) and item for item in values):
        raise SourceOperationProjectionError("resolved source identity is incomplete")
    return cast(tuple[str, str, str], values)


def _resolved_source(
    operation_input: SourceOperationInput,
    reader: VersionReader,
) -> tuple[SourceRef, dict[str, object]] | None:
    if len(operation_input.matches) != 1:
        return None
    match = operation_input.matches[0]
    document_id, source_id, digest = _identity(match)
    ref = reader.query_ref(document_id, source_id, digest)
    if "byte_size" in match and match["byte_size"] != ref.byte_size:
        raise SourceOperationProjectionError("resolved source version changed")
    if "mime_type" in match and match["mime_type"] != ref.mime_type:
        raise SourceOperationProjectionError("resolved source version changed")
    candidate = reader.describe_candidate(ref)
    if _contains_physical_field(candidate):
        raise SourceOperationProjectionError("candidate contains a physical field")
    return ref, candidate


def _status_and_source(
    operation_input: SourceOperationInput,
    reader: VersionReader,
) -> tuple[str, SourceRef | None, dict[str, object] | None]:
    if operation_input.producer_status == "gap":
        return "gap", None, None
    resolved = _resolved_source(operation_input, reader)
    if resolved is not None:
        return "completed", resolved[0], resolved[1]
    if (
        operation_input.producer_status == "ambiguous"
        or operation_input.resolution_status == "ambiguous"
    ):
        return "ambiguous", None, None
    if (
        operation_input.producer_status in {"missing", "not_found"}
        or operation_input.resolution_status == "missing"
    ):
        return "not_found", None, None
    return "unavailable", None, None


def project_source_operation(
    operation_input: SourceOperationInput,
    *,
    reader: VersionReader,
) -> dict[str, Any]:
    """Return the stable consumer DTO without any physical storage field."""
    if not isinstance(operation_input, SourceOperationInput):
        raise TypeError("operation_input must be SourceOperationInput")
    status, ref, candidate = _status_and_source(operation_input, reader)
    result = {
        "operation_schema_version": OPERATION_SCHEMA_VERSION,
        "operation": operation_input.operation,
        "status": status,
        "request_id": operation_input.request_id,
        "outcome": operation_input.outcome,
        "download_events": operation_input.download_events,
        "policy_hash": operation_input.policy_hash,
        "source_ref": asdict(ref) if ref is not None else None,
        "candidate": candidate,
        "gap_plan": _gap_projection(operation_input.gap_plan) if status == "gap" else None,
    }
    if _contains_physical_field(result):
        raise SourceOperationProjectionError(
            "operation result contains a physical field"
        )
    return result


__all__ = ["OPERATION_SCHEMA_VERSION", "VersionReader", "project_source_operation"]
