"""Narrative-unit construction bound to versioned source locators.

Unit identity binds source id, source SHA-256, parser name/version, format,
the versioned ``source_locator``, the normalized text SHA-256, unit kind, and
source role.  The binding is computed with canonical JSON, so unit ids are
stable across processes regardless of ``PYTHONHASHSEED``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any

from company_wiki.source_catalog.narrative_document import NarrativeUnit
from company_wiki.source_contract.evidence_span import EvidenceCoordinates

from .text import normalize_text

PARSER_NAME = "cwp_document_normalization"
PARSER_VERSION = "1.0.0"
NORMALIZATION_SCHEMA = "cwp-document-normalization/1"
UNIT_ID_PREFIX = "urn:company-wiki:narrative-unit:sha256:"
SOURCE_ROLE = "company_filing"

FORMAT_HTML = "html"
FORMAT_PPTX = "pptx"

HTML_LOCATOR_SCHEMA = "cwp-html-dom/1"
PPTX_LOCATOR_SCHEMA = "cwp-pptx-shape/1"


def canonical_identity_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def unit_text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_unit_id(
    *,
    source_id: str,
    source_sha256: str,
    format_name: str,
    source_locator: str,
    text_sha256: str,
    unit_kind: str,
    source_role: str,
) -> str:
    identity = {
        "format": format_name,
        "parser_name": PARSER_NAME,
        "parser_version": PARSER_VERSION,
        "source_id": source_id,
        "source_locator": source_locator,
        "source_role": source_role,
        "source_sha256": source_sha256,
        "text_sha256": text_sha256,
        "unit_kind": unit_kind,
    }
    return UNIT_ID_PREFIX + hashlib.sha256(
        canonical_identity_json(identity).encode("utf-8")
    ).hexdigest()


def build_unit(
    *,
    source_id: str,
    source_sha256: str,
    format_name: str,
    coordinates: EvidenceCoordinates,
    raw_text: str,
    unit_kind: str,
    source_locator: str,
    transform: str,
    extra_metadata: Mapping[str, Any] | None = None,
    quality_flags: Sequence[str] = (),
) -> NarrativeUnit:
    """Create one NarrativeUnit whose id binds every replay-relevant fact."""
    normalized = normalize_text(raw_text)
    if not normalized:
        raise ValueError("cannot build a narrative unit from blank text")
    if normalized != raw_text:
        raise ValueError("unit text must already be normalized before building")
    metadata: dict[str, Any] = {
        "normalization_schema": NORMALIZATION_SCHEMA,
        "format": format_name,
        "source_sha256": source_sha256,
        "source_locator": source_locator,
        "transform": transform,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    unit_id = compute_unit_id(
        source_id=source_id,
        source_sha256=source_sha256,
        format_name=format_name,
        source_locator=source_locator,
        text_sha256=unit_text_sha256(normalized),
        unit_kind=unit_kind,
        source_role=SOURCE_ROLE,
    )
    return NarrativeUnit(
        unit_id=unit_id,
        source_id=source_id,
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        coordinates=coordinates,
        raw_text=normalized,
        unit_kind=unit_kind,
        source_role=SOURCE_ROLE,
        language="und",
        quality_flags=tuple(quality_flags),
        metadata=metadata,
    )


def verify_unit_identity(unit: NarrativeUnit, *, format_name: str) -> None:
    """Recompute the identity binding; refuse any mismatch (tamper detection).

    The claimed unit_id must equal the id recomputed from the unit's own
    fields and metadata, so a forged locator, version, or text cannot replay.
    """
    metadata = unit.metadata
    expected_locator = metadata.get("source_locator")
    if not isinstance(expected_locator, str) or not expected_locator:
        raise ValueError("unit metadata lacks a source_locator")
    expected_id = compute_unit_id(
        source_id=unit.source_id,
        source_sha256=str(metadata.get("source_sha256", "")),
        format_name=str(metadata.get("format", "")),
        source_locator=expected_locator,
        text_sha256=unit.text_sha256,
        unit_kind=unit.unit_kind,
        source_role=unit.source_role,
    )
    if unit.unit_id != expected_id:
        raise ValueError(
            "unit_id does not bind its claimed locator, text, or metadata"
        )
    if metadata.get("format") != format_name:
        raise ValueError("unit format does not match the parsed document")


__all__ = [
    "FORMAT_HTML",
    "FORMAT_PPTX",
    "HTML_LOCATOR_SCHEMA",
    "NORMALIZATION_SCHEMA",
    "PARSER_NAME",
    "PARSER_VERSION",
    "PPTX_LOCATOR_SCHEMA",
    "SOURCE_ROLE",
    "UNIT_ID_PREFIX",
    "build_unit",
    "canonical_identity_json",
    "compute_unit_id",
    "unit_text_sha256",
    "verify_unit_identity",
]
