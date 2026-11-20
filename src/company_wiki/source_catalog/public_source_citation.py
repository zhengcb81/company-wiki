"""Exact-original citation replay independent of summary artifacts."""

from __future__ import annotations

from typing import Any

from ..source_contract.source_version import SourceReadError, SourceRef
from ..wire_json import canonical_json_hash
from .native_source_citation import read_native_citation

REQUEST_SCHEMA = "company-wiki-source-citation-request/1"
RESPONSE_SCHEMA = "company-wiki-source-citation/1"
_LOCATOR_FIELDS = {"kind", "value", "page_kind", "excerpt"}


def _quote(value: Any) -> str | None:
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ValueError("citation excerpt must be nonempty text")
    return value


def resolve_source_citation(catalog, request: dict[str, Any]) -> dict[str, Any]:
    if (not isinstance(request, dict) or set(request) != {"schema_version", "source_ref", "evidence"}
            or request["schema_version"] != REQUEST_SCHEMA):
        raise ValueError("invalid source citation request")
    ref = SourceRef.from_dict(request["source_ref"])
    evidence = request["evidence"]
    if not isinstance(evidence, dict) or set(evidence) - {"quote", "locator"}:
        raise ValueError("invalid source citation selector")
    quote = _quote(evidence.get("quote"))
    locator = evidence.get("locator")
    if locator is not None:
        if (not isinstance(locator, dict) or set(locator) != _LOCATOR_FIELDS
                or locator["kind"] not in ("page", "paragraph", "table")
                or not isinstance(locator["value"], str) or not locator["value"]
                or locator["page_kind"] not in (None, "physical")):
            raise ValueError("invalid native citation locator")
        _quote(locator["excerpt"])
    if quote is None and locator is None:
        raise ValueError("an excerpt or native locator is required")
    try:
        citation = read_native_citation(catalog, ref, quote=quote, locator=locator)
        response = {"schema_version": RESPONSE_SCHEMA, "state": "available",
                    "reason_codes": ["exact_original_verified"], **citation}
    except SourceReadError as exc:
        response = {"schema_version": RESPONSE_SCHEMA, "state": exc.status,
                    "reason_codes": [exc.reason], "source_ref": None,
                    "document_version_id": None, "current_byte_verification": None,
                    "evidence_validation": None}
    response["receipt_sha256"] = canonical_json_hash(response)
    return response
