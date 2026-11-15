"""Pure pathless projection over a validated source operation input."""

from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any, cast, Protocol

from .operation_contract import (
    OPERATION_REASONS,
    SourceOperationInput,
    SourceOperationProjectionError,
)
from .resolver import CANDIDATE_EXCLUSION_REASONS
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

# FF-1 B4: the pathless candidate whitelist (contract text 2026-11-15 — the
# consumer lane implements the SAME text; do not deviate).  Exactly these
# keys, at most five items, only for status ambiguous / not_found.
_CANDIDATE_ITEM_FIELDS = (
    "document_id", "title", "document_kind", "provider", "provider_document_id",
    "form_type", "fiscal_year", "fiscal_period", "language", "content_sha256",
    "byte_size", "publication_status", "exclusion_reason",
)
_CANDIDATE_MAX_ITEMS = 5
_CANDIDATE_PUBLICATION_STATUSES = frozenset({"known", "unknown", "future"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


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


def _candidate_text(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise SourceOperationProjectionError(f"candidate {key} must be text or null")
    return value


def _candidate_title(item: dict[str, Any]) -> str:
    """Title is trimmed non-empty text (F-R3).

    ``documents.title`` is free text and may carry padding; the FF consumer's
    ``_validated_operation_candidates`` (filing-fetch
    ``scripts/fetch_filing.py``) rejects any candidate value with
    ``value != value.strip()`` fail-closed, so the PRODUCER trims the
    projection output here (documents data itself is untouched) — the same
    normalization provider/form_type already get at their sources.  A
    whitespace-only title has no consumer-valid representation and fails
    closed rather than emitting a payload the consumer must refuse.
    """
    value = item.get("title")
    if not isinstance(value, str):
        raise SourceOperationProjectionError("candidate title must be text")
    trimmed = value.strip()
    if not trimmed:
        raise SourceOperationProjectionError("candidate title must be non-empty text")
    return trimmed


def _project_candidate(
    item: dict[str, Any], *, exclusion_reason: str | None = None,
) -> dict[str, Any]:
    """One candidate projected onto the whitelist — nothing else survives."""
    document_id = item.get("document_id")
    if not isinstance(document_id, str) or not document_id:
        raise SourceOperationProjectionError("candidate document_id must be text")
    digest = item.get("content_sha256") or item.get("snapshot_sha256")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceOperationProjectionError(
            "candidate content_sha256 must be a 64-hex sha256"
        )
    byte_size = item.get("byte_size")
    if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size < 0:
        raise SourceOperationProjectionError(
            "candidate byte_size must be a non-negative integer"
        )
    publication_status = item.get("publication_status")
    if publication_status is None:
        publication_status = "known" if item.get("published_date") else "unknown"
    if publication_status not in _CANDIDATE_PUBLICATION_STATUSES:
        raise SourceOperationProjectionError(
            "candidate publication_status is outside the closed set"
        )
    reason = exclusion_reason or item.get("exclusion_reason")
    if reason not in CANDIDATE_EXCLUSION_REASONS:
        raise SourceOperationProjectionError(
            "candidate exclusion_reason is outside the closed set"
        )
    fiscal_year = item.get("fiscal_year")
    if fiscal_year is not None and (
        isinstance(fiscal_year, bool) or not isinstance(fiscal_year, int)
    ):
        raise SourceOperationProjectionError(
            "candidate fiscal_year must be an integer or null"
        )
    return {
        "document_id": document_id,
        "title": _candidate_title(item),
        "document_kind": _candidate_text(item, "document_kind"),
        "provider": _candidate_text(item, "provider"),
        "provider_document_id": _candidate_text(item, "provider_document_id"),
        "form_type": _candidate_text(item, "form_type"),
        "fiscal_year": fiscal_year,
        "fiscal_period": _candidate_text(item, "fiscal_period"),
        "language": _candidate_text(item, "language"),
        "content_sha256": digest,
        "byte_size": byte_size,
        "publication_status": publication_status,
        "exclusion_reason": reason,
    }


def _operation_candidates(operation_input: SourceOperationInput) -> list[dict[str, Any]]:
    """Candidates for an ambiguous / not_found payload, capped at five.

    Several matching sources ARE the candidate set (each excluded because the
    request is ambiguous between them); otherwise the resolver's excluded
    candidates are republished with their own per-candidate reason.
    Existing producer order is preserved; the cap truncates.
    """
    if len(operation_input.matches) > 1:
        projected = [
            _project_candidate(match, exclusion_reason="multiple_candidates")
            for match in operation_input.matches
        ]
    else:
        projected = [_project_candidate(item) for item in operation_input.candidates]
    return projected[:_CANDIDATE_MAX_ITEMS]


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
    if operation_input.local_preparation is not None:
        return operation_input.local_preparation["status"], None, None
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
    result: dict[str, Any] = {
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
    if status in {"ambiguous", "not_found"}:
        # FF-1 B4: additive optional fields — never on completed/gap payloads.
        candidates = _operation_candidates(operation_input)
        if candidates:
            result["candidates"] = candidates
        if operation_input.reason in OPERATION_REASONS:
            result["reason"] = operation_input.reason
    if operation_input.local_preparation is not None:
        result["local_preparation"] = operation_input.local_preparation
    if _contains_physical_field(result):
        raise SourceOperationProjectionError(
            "operation result contains a physical field"
        )
    return result


__all__ = ["OPERATION_SCHEMA_VERSION", "VersionReader", "project_source_operation"]
