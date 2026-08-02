"""Pure adapter for the audited aggregate output of legacy PDF extract v3."""

from __future__ import annotations

from collections.abc import Mapping
import math
import re
from typing import Any
import unicodedata

from ..canonical_ingest import ParserResult
from ..source_contract import (
    EvidenceCoordinates,
    ImmutableStatus,
    ParseStatus,
    QualityFlag,
    SourceManifest,
)


PDF_EXTRACT_V3_PARSER_NAME = "legacy_pdf_extract_v3"

_EXPECTED_FIELDS = frozenset(
    {
        "text",
        "pages_read",
        "total_pages",
        "total_chars",
        "quality_score",
        "is_scanned",
        "scan_confidence",
        "error",
    }
)
_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n+")
_TABLE_MARKER_RE = re.compile(r"\[TABLE [1-9]\d*\]")
_LOW_QUALITY_THRESHOLD = 0.30


class PDFExtractV3AdapterError(ValueError):
    """Raised when legacy aggregate output cannot be mapped truthfully."""


def _require_integer(value: Any, field_name: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PDFExtractV3AdapterError(f"{field_name} must be an integer")
    if value < minimum:
        raise PDFExtractV3AdapterError(f"{field_name} must be >= {minimum}")
    return value


def _require_ratio(value: Any, field_name: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise PDFExtractV3AdapterError(f"{field_name} must be numeric")
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise PDFExtractV3AdapterError(f"{field_name} must be finite in [0, 1]")
    return value


def _paragraph_ranges(text: str) -> tuple[tuple[int, int, str], ...]:
    ranges: list[tuple[int, int, str]] = []
    cursor = 0
    segments: list[tuple[int, int]] = []
    for separator in _BLANK_LINE_RE.finditer(text):
        segments.append((cursor, separator.start()))
        cursor = separator.end()
    segments.append((cursor, len(text)))

    for start, end in segments:
        segment = text[start:end]
        left_trimmed = segment.lstrip(" \t\n")
        if not left_trimmed:
            continue
        adjusted_start = start + len(segment) - len(left_trimmed)
        value = left_trimmed.rstrip(" \t\n")
        adjusted_end = adjusted_start + len(value)
        ranges.append((adjusted_start, adjusted_end, value))
    return tuple(ranges)


def _validate_input(
    *,
    manifest: SourceManifest,
    extraction: Mapping[str, Any],
) -> tuple[str, int, int, float | int, float | int]:
    if not isinstance(manifest, SourceManifest):
        raise TypeError("manifest must be SourceManifest")
    if manifest.mime_type != "application/pdf":
        raise PDFExtractV3AdapterError("manifest mime_type must be application/pdf")
    if manifest.immutable_status is not ImmutableStatus.VERIFIED:
        raise PDFExtractV3AdapterError("manifest must have verified immutable status")
    if not isinstance(extraction, Mapping):
        raise TypeError("extraction must be a mapping")
    if set(extraction) != _EXPECTED_FIELDS:
        raise PDFExtractV3AdapterError(
            "legacy extraction fields must exactly match pdf_extract_v3 output"
        )

    text = extraction["text"]
    if not isinstance(text, str):
        raise PDFExtractV3AdapterError("text must be a string")
    if "\r" in text:
        raise PDFExtractV3AdapterError("text must use LF line endings")
    if unicodedata.normalize("NFC", text) != text:
        raise PDFExtractV3AdapterError("text must use Unicode NFC")

    is_scanned = extraction["is_scanned"]
    if not isinstance(is_scanned, bool):
        raise PDFExtractV3AdapterError("is_scanned must be boolean")
    scan_confidence = _require_ratio(
        extraction["scan_confidence"],
        "scan_confidence",
    )
    if not is_scanned and scan_confidence != 0.0:
        raise PDFExtractV3AdapterError(
            "scan_confidence must be zero when is_scanned is false"
        )

    error = extraction["error"]
    if error is not None:
        raise PDFExtractV3AdapterError(f"legacy extraction error: {error}")
    if is_scanned:
        raise PDFExtractV3AdapterError(
            "scanned PDF output requires a separate audited OCR parser"
        )
    if not text.strip():
        raise PDFExtractV3AdapterError("legacy extraction text is empty")

    pages_read = _require_integer(
        extraction["pages_read"],
        "pages_read",
        minimum=1,
    )
    total_pages = _require_integer(
        extraction["total_pages"],
        "total_pages",
        minimum=1,
    )
    if total_pages < pages_read:
        raise PDFExtractV3AdapterError("total_pages must be >= pages_read")
    total_chars = _require_integer(
        extraction["total_chars"],
        "total_chars",
        minimum=1,
    )
    if total_chars != len(text):
        raise PDFExtractV3AdapterError("total_chars must exactly match text length")
    quality_score = _require_ratio(
        extraction["quality_score"],
        "quality_score",
    )
    return text, pages_read, total_pages, quality_score, scan_confidence


def adapt_pdf_extract_v3(
    *,
    manifest: SourceManifest,
    extraction: Mapping[str, Any],
    parser_version: str,
) -> tuple[ParserResult, ...]:
    """Map one strict aggregate v3 result into normalized paragraph results."""

    text, pages_read, total_pages, quality_score, scan_confidence = _validate_input(
        manifest=manifest,
        extraction=extraction,
    )
    paragraphs = _paragraph_ranges(text)
    if not paragraphs:
        raise PDFExtractV3AdapterError("legacy extraction text is empty")

    metadata = {
        "adapter": "pdf_extract_v3_aggregate",
        "physical_page_locator_available": False,
        "quality_score": quality_score,
        "scan_confidence": scan_confidence,
        "pages_read": pages_read,
        "total_pages": total_pages,
    }
    base_flags: list[QualityFlag] = []
    if pages_read < total_pages:
        base_flags.append(QualityFlag.TRUNCATED)
    if quality_score < _LOW_QUALITY_THRESHOLD:
        base_flags.append(QualityFlag.PARSER_WARNING)

    results: list[ParserResult] = []
    for paragraph_index, (char_start, char_end, raw_text) in enumerate(paragraphs):
        quality_flags = list(base_flags)
        if _TABLE_MARKER_RE.search(raw_text):
            quality_flags.append(QualityFlag.TABLE_STRUCTURE_AMBIGUOUS)
        parse_status = (
            ParseStatus.PARTIAL if quality_flags else ParseStatus.PARSED
        )
        results.append(
            ParserResult(
                source_id=manifest.source_id,
                coordinates=EvidenceCoordinates(
                    paragraph_index=paragraph_index,
                    char_start=char_start,
                    char_end=char_end,
                ),
                raw_text=raw_text,
                structured_value=metadata,
                parser_name=PDF_EXTRACT_V3_PARSER_NAME,
                parser_version=parser_version,
                parse_status=parse_status,
                quality_flags=quality_flags,
            )
        )
    return tuple(results)


__all__ = [
    "PDF_EXTRACT_V3_PARSER_NAME",
    "PDFExtractV3AdapterError",
    "adapt_pdf_extract_v3",
]
