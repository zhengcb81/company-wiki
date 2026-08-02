"""Pure canonical adapter for page-aware PDF text and table snapshots."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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


PAGE_AWARE_PDF_PARSER_NAME = "pdf_page_aware_core"

_PAGE_FIELDS = frozenset(
    {
        "page_number",
        "text",
        "tables",
        "quality_score",
        "ocr_used",
        "ocr_confidence",
        "layout_ambiguous",
        "encoding_repaired",
        "error",
    }
)
_TABLE_FIELDS = frozenset({"markdown", "rows", "cols", "data"})
_PARAGRAPH_BREAK_RE = re.compile(r"\n[ \t]*\n+")
_LOW_QUALITY_THRESHOLD = 0.30
_LOW_OCR_CONFIDENCE_THRESHOLD = 0.80


class PageAwarePDFAdapterError(ValueError):
    """Raised when page-aware parser input cannot be mapped truthfully."""


@dataclass(frozen=True)
class PageAwarePDFResult:
    """One immutable normalized stream and its canonical parser results."""

    normalized_text: str
    parser_results: tuple[ParserResult, ...]
    page_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.normalized_text, str):
            raise TypeError("normalized_text must be text")
        if not isinstance(self.parser_results, tuple) or not all(
            isinstance(item, ParserResult) for item in self.parser_results
        ):
            raise TypeError("parser_results must be a tuple of ParserResult values")
        if isinstance(self.page_count, bool) or not isinstance(self.page_count, int):
            raise TypeError("page_count must be an integer")
        if self.page_count < 1:
            raise PageAwarePDFAdapterError("page_count must be >= 1")


@dataclass(frozen=True)
class _Page:
    page_number: int
    text: str
    tables: tuple[Mapping[str, Any], ...]
    quality_score: float | int
    ocr_used: bool
    ocr_confidence: float | int | None
    layout_ambiguous: bool
    encoding_repaired: bool
    error: str | None


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a sequence")
    return value


def _require_integer(value: Any, field_name: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PageAwarePDFAdapterError(f"{field_name} must be an integer")
    if value < minimum:
        raise PageAwarePDFAdapterError(f"{field_name} must be >= {minimum}")
    return value


def _require_ratio(value: Any, field_name: str) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise PageAwarePDFAdapterError(f"{field_name} must be numeric")
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise PageAwarePDFAdapterError(f"{field_name} must be finite in [0, 1]")
    return value


def _require_nfc_lf(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if "\r" in value:
        raise PageAwarePDFAdapterError(f"{field_name} must use LF line endings")
    if unicodedata.normalize("NFC", value) != value:
        raise PageAwarePDFAdapterError(f"{field_name} must use Unicode NFC")
    return value


def _validate_manifest(manifest: SourceManifest) -> None:
    if not isinstance(manifest, SourceManifest):
        raise TypeError("manifest must be SourceManifest")
    if manifest.mime_type != "application/pdf":
        raise PageAwarePDFAdapterError("manifest mime_type must be application/pdf")
    if manifest.immutable_status is not ImmutableStatus.VERIFIED:
        raise PageAwarePDFAdapterError("manifest must have verified immutable status")


def _validate_page(value: Any, *, expected_page_number: int) -> _Page:
    if not isinstance(value, Mapping):
        raise TypeError("each page must be a mapping")
    if set(value) != _PAGE_FIELDS:
        raise PageAwarePDFAdapterError(
            "page fields must exactly match the page-aware input contract"
        )
    page_number = _require_integer(value["page_number"], "page_number", minimum=1)
    if page_number != expected_page_number:
        raise PageAwarePDFAdapterError(
            f"page_number must be contiguous from 1; expected {expected_page_number}"
        )
    text = _require_nfc_lf(value["text"], "text").strip(" \t\n")
    tables = tuple(_require_sequence(value["tables"], "tables"))
    quality_score = _require_ratio(value["quality_score"], "quality_score")
    ocr_used = value["ocr_used"]
    if not isinstance(ocr_used, bool):
        raise TypeError("ocr_used must be boolean")
    ocr_confidence = value["ocr_confidence"]
    if ocr_used:
        if ocr_confidence is None:
            raise PageAwarePDFAdapterError(
                "ocr_confidence is required when ocr_used is true"
            )
        ocr_confidence = _require_ratio(ocr_confidence, "ocr_confidence")
    elif ocr_confidence is not None:
        raise PageAwarePDFAdapterError(
            "ocr_confidence must be null when ocr_used is false"
        )
    layout_ambiguous = value["layout_ambiguous"]
    if not isinstance(layout_ambiguous, bool):
        raise TypeError("layout_ambiguous must be boolean")
    encoding_repaired = value["encoding_repaired"]
    if not isinstance(encoding_repaired, bool):
        raise TypeError("encoding_repaired must be boolean")
    error = value["error"]
    if error is not None:
        if not isinstance(error, str) or not error.strip():
            raise PageAwarePDFAdapterError("error must be non-empty text or null")
        if text or tables:
            raise PageAwarePDFAdapterError(
                "an error page must not also publish text or tables"
            )
    return _Page(
        page_number=page_number,
        text=text,
        tables=tables,
        quality_score=quality_score,
        ocr_used=ocr_used,
        ocr_confidence=ocr_confidence,
        layout_ambiguous=layout_ambiguous,
        encoding_repaired=encoding_repaired,
        error=error,
    )


def _paragraph_ranges(text: str) -> tuple[tuple[int, int, str], ...]:
    segments: list[tuple[int, int]] = []
    cursor = 0
    for separator in _PARAGRAPH_BREAK_RE.finditer(text):
        segments.append((cursor, separator.start()))
        cursor = separator.end()
    segments.append((cursor, len(text)))
    ranges: list[tuple[int, int, str]] = []
    for start, end in segments:
        segment = text[start:end]
        left = segment.lstrip(" \t\n")
        if not left:
            continue
        adjusted_start = start + len(segment) - len(left)
        raw_text = left.rstrip(" \t\n")
        ranges.append((adjusted_start, adjusted_start + len(raw_text), raw_text))
    return tuple(ranges)


def _page_flags(page: _Page) -> tuple[QualityFlag, ...]:
    flags: list[QualityFlag] = []
    if page.ocr_used:
        flags.append(QualityFlag.OCR_USED)
        if page.ocr_confidence is not None and (
            page.ocr_confidence < _LOW_OCR_CONFIDENCE_THRESHOLD
        ):
            flags.append(QualityFlag.LOW_OCR_CONFIDENCE)
    if page.layout_ambiguous:
        flags.append(QualityFlag.LAYOUT_AMBIGUOUS)
    if page.encoding_repaired:
        flags.append(QualityFlag.ENCODING_REPAIRED)
    if page.quality_score < _LOW_QUALITY_THRESHOLD:
        flags.append(QualityFlag.PARSER_WARNING)
    return tuple(flags)


def _status_for_output(flags: Sequence[QualityFlag]) -> ParseStatus:
    degrading = {item for item in flags if item is not QualityFlag.OCR_USED}
    return ParseStatus.PARTIAL if degrading else ParseStatus.PARSED


def _page_metadata(page: _Page, *, kind: str) -> dict[str, Any]:
    return {
        "encoding_repaired": page.encoding_repaired,
        "kind": kind,
        "layout_ambiguous": page.layout_ambiguous,
        "ocr_confidence": page.ocr_confidence,
        "ocr_used": page.ocr_used,
        "page_number": page.page_number,
        "quality_score": page.quality_score,
    }


def _cell_value(value: Any) -> tuple[str | None, Any]:
    if value is None:
        return None, None
    if isinstance(value, str):
        text = _require_nfc_lf(value, "table cell")
        return text, text
    if isinstance(value, bool):
        return ("true" if value else "false"), value
    if isinstance(value, int):
        return str(value), value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PageAwarePDFAdapterError("table cell numbers must be finite")
        return str(value), value
    raise PageAwarePDFAdapterError("table cells must be JSON scalar values")


def _table_results(
    *,
    manifest: SourceManifest,
    page: _Page,
    parser_version: str,
    flags: tuple[QualityFlag, ...],
) -> tuple[ParserResult, ...]:
    results: list[ParserResult] = []
    for table_index, table in enumerate(page.tables):
        if not isinstance(table, Mapping):
            raise TypeError("each table must be a mapping")
        if set(table) != _TABLE_FIELDS:
            raise PageAwarePDFAdapterError(
                "table fields must exactly match pdf_extract_v3 table output"
            )
        _require_nfc_lf(table["markdown"], "table markdown")
        rows = _require_integer(table["rows"], "rows", minimum=1)
        cols = _require_integer(table["cols"], "cols", minimum=1)
        data = _require_sequence(table["data"], "table data")
        if len(data) != rows:
            raise PageAwarePDFAdapterError("rows must exactly match table data")
        for row_index, row in enumerate(data):
            values = _require_sequence(row, "table row")
            if len(values) != cols:
                raise PageAwarePDFAdapterError("table data must be rectangular")
            for column_index, raw_value in enumerate(values):
                raw_text, normalized_value = _cell_value(raw_value)
                structured_value = {
                    "column_index": column_index,
                    "kind": "table_cell",
                    "page_number": page.page_number,
                    "raw_value": normalized_value,
                    "row_index": row_index,
                    "table_index": table_index,
                    "value": raw_text,
                }
                results.append(
                    ParserResult(
                        source_id=manifest.source_id,
                        coordinates=EvidenceCoordinates(
                            page_number=page.page_number,
                            table_index=table_index,
                            row_index=row_index,
                            column_index=column_index,
                        ),
                        raw_text=raw_text,
                        structured_value=structured_value,
                        parser_name=PAGE_AWARE_PDF_PARSER_NAME,
                        parser_version=parser_version,
                        parse_status=_status_for_output(flags),
                        quality_flags=flags,
                    )
                )
    return tuple(results)


def adapt_pdf_pages(
    *,
    manifest: SourceManifest,
    pages: Sequence[Mapping[str, Any]],
    parser_version: str,
) -> PageAwarePDFResult:
    """Map strict physical-page snapshots into canonical parser results."""

    _validate_manifest(manifest)
    page_values = _require_sequence(pages, "pages")
    if not page_values:
        raise PageAwarePDFAdapterError("pages must not be empty")
    validated = tuple(
        _validate_page(value, expected_page_number=index)
        for index, value in enumerate(page_values, start=1)
    )

    normalized_parts: list[str] = []
    results: list[ParserResult] = []
    normalized_cursor = 0
    for page in validated:
        if page.error is not None:
            results.append(
                ParserResult(
                    source_id=manifest.source_id,
                    coordinates=EvidenceCoordinates(page_number=page.page_number),
                    raw_text=None,
                    structured_value=None,
                    parser_name=PAGE_AWARE_PDF_PARSER_NAME,
                    parser_version=parser_version,
                    parse_status=ParseStatus.FAILED,
                    quality_flags=(QualityFlag.PARSER_ERROR,),
                )
            )
            continue

        flags = _page_flags(page)
        if page.text:
            if normalized_parts:
                normalized_cursor += 2
            page_start = normalized_cursor
            normalized_parts.append(page.text)
            normalized_cursor += len(page.text)
            for paragraph_index, (start, end, raw_text) in enumerate(
                _paragraph_ranges(page.text)
            ):
                results.append(
                    ParserResult(
                        source_id=manifest.source_id,
                        coordinates=EvidenceCoordinates(
                            page_number=page.page_number,
                            paragraph_index=paragraph_index,
                            char_start=page_start + start,
                            char_end=page_start + end,
                        ),
                        raw_text=raw_text,
                        structured_value=_page_metadata(page, kind="paragraph"),
                        parser_name=PAGE_AWARE_PDF_PARSER_NAME,
                        parser_version=parser_version,
                        parse_status=_status_for_output(flags),
                        quality_flags=flags,
                    )
                )

        table_results = _table_results(
            manifest=manifest,
            page=page,
            parser_version=parser_version,
            flags=flags,
        )
        results.extend(table_results)
        if not page.text and not table_results:
            results.append(
                ParserResult(
                    source_id=manifest.source_id,
                    coordinates=EvidenceCoordinates(page_number=page.page_number),
                    raw_text=None,
                    structured_value=None,
                    parser_name=PAGE_AWARE_PDF_PARSER_NAME,
                    parser_version=parser_version,
                    parse_status=ParseStatus.FAILED,
                    quality_flags=(QualityFlag.EMPTY_OUTPUT,),
                )
            )

    return PageAwarePDFResult(
        normalized_text="\n\n".join(normalized_parts),
        parser_results=tuple(results),
        page_count=len(validated),
    )


__all__ = [
    "PAGE_AWARE_PDF_PARSER_NAME",
    "PageAwarePDFAdapterError",
    "PageAwarePDFResult",
    "adapt_pdf_pages",
]
