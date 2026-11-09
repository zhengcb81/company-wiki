"""Map native and OCR PDF page snapshots to canonical evidence coordinates.

OCR input uses ``cwp-ocr-page-text/1``. Accepted lines must cover the page
text in non-overlapping ranges, apart from separating whitespace. Physical
page numbers are retained even when a page has no accepted text.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from operator import attrgetter
from typing import Any
import unicodedata

from ..canonical_ingest import ParserResult
from ..document_normalization.ocr_page_text import (
    DEFER_AMBIGUOUS_ORDER,
    DEFER_LIMIT,
    DEFER_LOW_CONFIDENCE,
    P1_PAGE_TEXT_SCHEMA,
    P1_PAGE_TEXT_VERSION,
)
from ..source_contract import (
    EvidenceCoordinates,
    ImmutableStatus,
    ParseStatus,
    QualityFlag,
    SourceManifest,
)
from ._pdf_values import LOW_PAGE_QUALITY_THRESHOLD, require_ratio
from .pdf_page_aware import PageAwarePDFResult

PDF_OCR_PAGE_ADAPTER_ID = "pdf-ocr-page-adapter/1"
PDF_OCR_PAGE_PARSER_NAME = "pdf_ocr_page_adapter"
PDF_OCR_PAGE_PARSER_VERSION = P1_PAGE_TEXT_VERSION

_OCR_PAGE_FIELDS = frozenset({"page_number", "ocr"})
_TEXT_PAGE_FIELDS = frozenset({"page_number", "text", "quality_score"})
_FLAGS_BY_DEFER_REASON = {
    DEFER_LOW_CONFIDENCE: QualityFlag.LOW_OCR_CONFIDENCE,
    DEFER_AMBIGUOUS_ORDER: QualityFlag.LAYOUT_AMBIGUOUS,
    DEFER_LIMIT: QualityFlag.TRUNCATED,
}


class OCRPageAdapterError(ValueError):
    """Raised when OCR/text page input cannot be mapped truthfully."""


@dataclass(frozen=True)
class _LocatedText:
    text: str
    start: int
    end: int
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class _Page:
    number: int
    text: str
    locations: tuple[_LocatedText, ...]
    flags: tuple[QualityFlag, ...] = ()
    has_deferred_text: bool = False


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a sequence")
    return value


def _require_nfc_lf(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise OCRPageAdapterError(f"{field_name} must be text")
    if "\r" in value:
        raise OCRPageAdapterError(f"{field_name} must use LF line endings")
    if unicodedata.normalize("NFC", value) != value:
        raise OCRPageAdapterError(f"{field_name} must use Unicode NFC")
    return value


def _coerce_manifest(manifest: Any) -> SourceManifest:
    if isinstance(manifest, SourceManifest):
        return manifest
    if isinstance(manifest, Mapping):
        return SourceManifest.from_dict(dict(manifest))
    raise TypeError("manifest must be a SourceManifest or a source manifest mapping")


def _validate_manifest(manifest: SourceManifest) -> None:
    if manifest.mime_type != "application/pdf":
        raise OCRPageAdapterError("manifest mime_type must be application/pdf")
    if manifest.immutable_status is not ImmutableStatus.VERIFIED:
        raise OCRPageAdapterError("manifest must have verified immutable status")


def _ocr_page(number: int, ocr: Any) -> _Page:
    if not isinstance(ocr, Mapping):
        raise OCRPageAdapterError("ocr page must be a mapping")
    if ocr.get("schema_version") != P1_PAGE_TEXT_SCHEMA:
        raise OCRPageAdapterError(f"ocr schema_version must be {P1_PAGE_TEXT_SCHEMA}")
    text = _require_nfc_lf(ocr.get("text"), "ocr text")
    lines = ocr.get("lines")
    if not isinstance(lines, Sequence) or isinstance(lines, (str, bytes, bytearray)):
        raise OCRPageAdapterError("ocr lines must be an array")

    locations: list[_LocatedText] = []
    defer_reasons: set[str] = set()
    has_deferred_text = False
    for index, entry in enumerate(lines):
        if not isinstance(entry, Mapping):
            raise OCRPageAdapterError("each ocr line must be a mapping")
        accepted = entry.get("accepted")
        if not isinstance(accepted, bool):
            raise OCRPageAdapterError("ocr line accepted must be boolean")
        start = entry.get("char_start")
        end = entry.get("char_end")
        if not accepted:
            if start is not None or end is not None:
                raise OCRPageAdapterError("deferred ocr line must have null char_start and char_end")
            has_deferred_text = True
            reasons = entry.get("defer_reasons")
            if isinstance(reasons, Sequence) and not isinstance(reasons, (str, bytes, bytearray)):
                defer_reasons.update(reason for reason in reasons if isinstance(reason, str))
            continue
        line_text = _require_nfc_lf(entry.get("text"), "ocr line text")
        if isinstance(start, bool) or not isinstance(start, int):
            raise OCRPageAdapterError("accepted ocr line char_start must be an int")
        if isinstance(end, bool) or not isinstance(end, int):
            raise OCRPageAdapterError("accepted ocr line char_end must be an int")
        if not 0 <= start < end <= len(text):
            raise OCRPageAdapterError("accepted ocr line char range is outside the page text")
        if text[start:end] != line_text:
            raise OCRPageAdapterError("accepted ocr line text must match its char range in the page text")
        locations.append(_LocatedText(
            line_text,
            start,
            end,
            {
                "kind": "ocr_line",
                "page_number": number,
                "line_index": entry.get("line_index", index),
                "column_id": entry.get("column_id"),
            },
        ))

    if bool(locations) != bool(text):
        raise OCRPageAdapterError("ocr text must be non-empty exactly when it has accepted lines")
    # The producer's line array follows source indexes. Ranges carry reading order.
    locations.sort(key=attrgetter("start"))
    cursor = 0
    for location in locations:
        if location.start < cursor:
            raise OCRPageAdapterError("accepted ocr line char ranges overlap")
        if text[cursor:location.start].strip():
            raise OCRPageAdapterError("ocr page contains unbound text between line ranges")
        cursor = location.end
    if text[cursor:].strip():
        raise OCRPageAdapterError("ocr page contains unbound text after the last line range")

    flags = (QualityFlag.OCR_USED,) + tuple(
        flag for reason, flag in _FLAGS_BY_DEFER_REASON.items() if reason in defer_reasons
    )
    return _Page(number, text, tuple(locations), flags, has_deferred_text)


def _text_page(number: int, value: Mapping[str, Any]) -> _Page:
    text = _require_nfc_lf(value["text"], "page text").strip(" \t\n")
    quality = float(require_ratio(value["quality_score"], "quality_score", error=OCRPageAdapterError))
    flags = (QualityFlag.PARSER_WARNING,) if quality < LOW_PAGE_QUALITY_THRESHOLD else ()
    locations: tuple[_LocatedText, ...] = ()
    if text:
        locations = (_LocatedText(
            text, 0, len(text), {"kind": "text_page", "page_number": number, "quality_score": quality},
        ),)
    return _Page(number, text, locations, flags)


def _prepare_page(value: Any) -> _Page:
    if not isinstance(value, Mapping):
        raise TypeError("each page must be a mapping")
    keys = set(value)
    if keys != _OCR_PAGE_FIELDS and keys != _TEXT_PAGE_FIELDS:
        raise OCRPageAdapterError(
            "page fields must match {page_number, ocr} or {page_number, text, quality_score}"
        )
    number = value["page_number"]
    if isinstance(number, bool) or not isinstance(number, int):
        raise OCRPageAdapterError("page_number must be an integer")
    if number < 1:
        raise OCRPageAdapterError("page_number must be >= 1")
    if keys == _OCR_PAGE_FIELDS:
        return _ocr_page(number, value["ocr"])
    return _text_page(number, value)


def adapt_ocr_pages(
    manifest: SourceManifest | Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
) -> PageAwarePDFResult:
    """Map OCR and plain text into canonical results without changing the inputs."""
    source = _coerce_manifest(manifest)
    _validate_manifest(source)
    page_values = _require_sequence(pages, "pages")
    if not page_values:
        raise OCRPageAdapterError("pages must not be empty")

    prepared = tuple(_prepare_page(value) for value in page_values)
    numbers = [page.number for page in prepared]
    if len(set(numbers)) != len(numbers):
        raise OCRPageAdapterError("page_number must not repeat")
    order_flags = (
        (QualityFlag.LOCATOR_UNSTABLE,) if numbers != list(range(1, len(numbers) + 1)) else ()
    )
    document_partial = any(not page.locations for page in prepared)
    normalized_parts: list[str] = []
    cursor = 0
    results: list[ParserResult] = []

    for page in prepared:
        flags = page.flags + order_flags
        if not page.locations:
            results.append(ParserResult(
                source_id=source.source_id,
                coordinates=EvidenceCoordinates(page_number=page.number),
                raw_text=None,
                structured_value=None,
                parser_name=PDF_OCR_PAGE_PARSER_NAME,
                parser_version=PDF_OCR_PAGE_PARSER_VERSION,
                parse_status=ParseStatus.FAILED,
                quality_flags=flags + (QualityFlag.EMPTY_OUTPUT,),
            ))
            continue

        if normalized_parts:
            cursor += 2
        page_start = cursor
        normalized_parts.append(page.text)
        cursor += len(page.text)
        partial = (
            document_partial or page.has_deferred_text
            or any(flag is not QualityFlag.OCR_USED for flag in flags)
        )
        if partial and not flags:
            flags = (QualityFlag.PARSER_WARNING,)
        status = ParseStatus.PARTIAL if partial else ParseStatus.PARSED
        for location in page.locations:
            results.append(ParserResult(
                source_id=source.source_id,
                coordinates=EvidenceCoordinates(
                    page_number=page.number,
                    char_start=page_start + location.start,
                    char_end=page_start + location.end,
                ),
                raw_text=location.text,
                structured_value=location.metadata,
                parser_name=PDF_OCR_PAGE_PARSER_NAME,
                parser_version=PDF_OCR_PAGE_PARSER_VERSION,
                parse_status=status,
                quality_flags=flags,
            ))

    return PageAwarePDFResult(
        normalized_text="\n\n".join(normalized_parts),
        parser_results=tuple(results),
        page_count=len(prepared),
    )


__all__ = [
    "OCRPageAdapterError",
    "PDF_OCR_PAGE_ADAPTER_ID",
    "PDF_OCR_PAGE_PARSER_NAME",
    "PDF_OCR_PAGE_PARSER_VERSION",
    "adapt_ocr_pages",
]
