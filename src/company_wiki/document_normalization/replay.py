"""Exact version-bound locator replay for normalized narrative units."""

from __future__ import annotations

import hashlib

from company_wiki.source_catalog.narrative_document import NarrativeUnit

from .html_parser import parse_html
from .limits import NormalizationLimits
from .pptx_parser import parse_pptx
from .text import normalize_text
from .units import (
    FORMAT_HTML,
    PARSER_NAME,
    PARSER_VERSION,
    verify_unit_identity,
)

__all__ = ["replay_unit"]


def _parse_for_replay(
    original: bytes,
    *,
    source_sha256: str,
    unit: NarrativeUnit,
    limits: NormalizationLimits,
):
    if not isinstance(original, bytes):
        raise TypeError("original must be bytes")
    if hashlib.sha256(original).hexdigest() != source_sha256:
        raise ValueError("source bytes do not match source_sha256")
    verify_unit_identity(unit, format_name=str(unit.metadata.get("format", "")))
    if unit.parser_name != PARSER_NAME:
        raise ValueError(f"unknown parser_name: {unit.parser_name!r}")
    if unit.parser_version != PARSER_VERSION:
        raise ValueError(f"unsupported parser_version: {unit.parser_version!r}")
    format_name = unit.metadata.get("format")
    if format_name == FORMAT_HTML:
        return parse_html(
            original,
            source_id=unit.source_id,
            source_sha256=source_sha256,
            mime_type="text/html",
            limits=limits,
        )
    return parse_pptx(
        original,
        source_id=unit.source_id,
        source_sha256=source_sha256,
        mime_type=(
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        ),
        limits=limits,
    )


def replay_unit(
    original: bytes,
    *,
    source_sha256: str,
    unit: NarrativeUnit,
    limits: NormalizationLimits,
) -> str:
    """Re-derive one unit's text from the actual original bytes.

    Refuses (raises :class:`company_wiki.document_normalization.errors.ReplayError`
    semantics via ValueError) when the bytes' SHA, the parser version, the
    locator, or the claimed text do not reproduce.  Never returns stored
    ``unit.raw_text`` as though it were a replay.
    """
    document = _parse_for_replay(
        original, source_sha256=source_sha256, unit=unit, limits=limits
    )
    expected_locator = unit.metadata.get("source_locator")
    matches = [
        candidate
        for candidate in document.units
        if candidate.metadata.get("source_locator") == expected_locator
    ]
    if not matches:
        raise ValueError(f"locator {expected_locator!r} not found in source")
    verified = [
        candidate
        for candidate in matches
        if candidate.raw_text == unit.raw_text
        and candidate.unit_id == unit.unit_id
    ]
    if not verified:
        found = matches[0].raw_text
        if normalize_text(found) != normalize_text(unit.raw_text):
            raise ValueError(
                "replayed text differs from the claimed unit text at the "
                "same locator"
            )
        raise ValueError(
            "locator replays different unit identity; parser binding changed"
        )
    return verified[0].raw_text
