"""Canonical PDF adapter for OCR page text (P1-OCR-TEXT card section 5.2).

Pure adapter: maps either an OCR page (a ``cwp-ocr-page-text/1`` document from
:func:`~company_wiki.document_normalization.ocr_page_text.order_page_lines`) or a
plain pre-extracted text page onto the existing
:class:`~company_wiki.source_contract.evidence_span.ParserResult` /
:class:`~company_wiki.source_contract.evidence_span.EvidenceCoordinates`
contract that ``pdf_page_aware`` already publishes.

Page shapes accepted (mixing is allowed):

- ``{page_number: int, ocr: <cwp-ocr-page-text/1 dict>}``
- ``{page_number: int, text: str, quality_score: float}``

Contract enforced by the card section 5.2 failure semantics (all ``ValueError``):
manifest/pages mismatch, duplicate or ``<= 0`` page numbers, and an ``ocr``
block whose ``schema_version`` is not ``cwp-ocr-page-text/1``.  OCR lines are
bound to that page's ``text`` through their own ``char_start/char_end``, offset
into the concatenated ``normalized_text`` exactly the way ``pdf_page_aware``
offsets paragraph spans.

``parse_status`` mirrors the card's three cases: every page contributes
accepted body -> ``parsed``; a page mixes accepted and deferred lines ->
``partial``; a page yields no accepted body -> ``failed`` (never an empty string
pretending to be success).

Quality flags use only existing ``QualityFlag`` values: ``ocr_used`` for any OCR
page, ``low_ocr_confidence`` for a deferred ``low_confidence`` line,
``layout_ambiguous`` for ``ambiguous_order``, ``truncated`` for ``limit``,
``locator_unstable`` when page numbers are not exactly ``1..N`` in order, and
``parser_warning`` for a plain-text page whose ``quality_score`` is below the
existing 0.30 threshold (reused from ``pdf_page_aware``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import unicodedata
from typing import Any

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
from .pdf_page_aware import PageAwarePDFResult

# Identity of this adapter (reported in handoff interface_versions).
PDF_OCR_PAGE_ADAPTER_ID = "pdf-ocr-page-adapter/1"
PDF_OCR_PAGE_PARSER_NAME = "pdf_ocr_page_adapter"
PDF_OCR_PAGE_PARSER_VERSION = P1_PAGE_TEXT_VERSION

# Reused from pdf_page_aware so quality thresholds stay single-sourced.
_LOW_QUALITY_THRESHOLD = 0.30

_OCR_PAGE_FIELDS = frozenset({"page_number", "ocr"})
_TEXT_PAGE_FIELDS = frozenset({"page_number", "text", "quality_score"})


class OCRPageAdapterError(ValueError):
    """Raised when OCR/text page input cannot be mapped truthfully."""


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


def _require_ratio(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OCRPageAdapterError(f"{field_name} must be numeric")
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise OCRPageAdapterError(f"{field_name} must be finite in [0, 1]")
    return float(value)


def _coerce_manifest(manifest: Any) -> SourceManifest:
    """Accept a SourceManifest or its Mapping form; reject anything else."""
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


def _validate_ocr_block(ocr: Any) -> tuple[str, list[dict[str, Any]]]:
    """Validate one ``cwp-ocr-page-text/1`` block; return (text, lines)."""
    if not isinstance(ocr, Mapping):
        raise OCRPageAdapterError("ocr page must be a mapping")
    if ocr.get("schema_version") != P1_PAGE_TEXT_SCHEMA:
        raise OCRPageAdapterError(
            f"ocr schema_version must be {P1_PAGE_TEXT_SCHEMA}"
        )
    page_text = _require_nfc_lf(ocr.get("text"), "ocr text")
    raw_lines = ocr.get("lines")
    if not isinstance(raw_lines, Sequence) or isinstance(
        raw_lines, (str, bytes, bytearray)
    ):
        raise OCRPageAdapterError("ocr lines must be an array")

    lines: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_lines):
        if not isinstance(entry, Mapping):
            raise OCRPageAdapterError("each ocr line must be a mapping")
        accepted = entry.get("accepted")
        if not isinstance(accepted, bool):
            raise OCRPageAdapterError("ocr line accepted must be boolean")
        line_text = _require_nfc_lf(entry.get("text"), "ocr line text")
        defer_reasons = entry.get("defer_reasons")
        if not isinstance(defer_reasons, Sequence) or isinstance(
            defer_reasons, (str, bytes, bytearray)
        ):
            raise OCRPageAdapterError("ocr line defer_reasons must be an array")
        char_start = entry.get("char_start")
        char_end = entry.get("char_end")
        if accepted:
            if isinstance(char_start, bool) or not isinstance(char_start, int):
                raise OCRPageAdapterError("accepted ocr line char_start must be an int")
            if isinstance(char_end, bool) or not isinstance(char_end, int):
                raise OCRPageAdapterError("accepted ocr line char_end must be an int")
            if char_start < 0 or char_end <= char_start:
                raise OCRPageAdapterError(
                    "accepted ocr line char range must satisfy 0 <= start < end"
                )
            if page_text[char_start:char_end] != line_text:
                raise OCRPageAdapterError(
                    "accepted ocr line text must match its char range in the page text"
                )
        elif char_start is not None or char_end is not None:
            raise OCRPageAdapterError(
                "deferred ocr line must have null char_start and char_end"
            )
        lines.append(
            {
                "line_index": entry.get("line_index", index),
                "text": line_text,
                "accepted": accepted,
                "defer_reasons": list(defer_reasons),
                "char_start": char_start,
                "char_end": char_end,
                "column_id": entry.get("column_id"),
            }
        )

    has_accepted = any(line["accepted"] for line in lines)
    if has_accepted != bool(page_text):
        raise OCRPageAdapterError(
            "ocr text must be non-empty exactly when it has accepted lines"
        )
    return page_text, lines


def adapt_ocr_pages(
    manifest: Mapping[str, Any],
    pages: Sequence[Mapping[str, Any]],
) -> PageAwarePDFResult:
    """Map OCR/text pages into canonical page-aware parser results.

    The input ``manifest`` and ``pages`` are read only and never mutated.
    """
    source = _coerce_manifest(manifest)
    _validate_manifest(source)

    page_values = _require_sequence(pages, "pages")
    if not page_values:
        raise OCRPageAdapterError("pages must not be empty")

    numbers: list[int] = []
    kinds: list[str] = []
    for value in page_values:
        if not isinstance(value, Mapping):
            raise TypeError("each page must be a mapping")
        keys = set(value)
        if keys == _OCR_PAGE_FIELDS:
            kinds.append("ocr")
        elif keys == _TEXT_PAGE_FIELDS:
            kinds.append("text")
        else:
            raise OCRPageAdapterError(
                "page fields must match {page_number, ocr} or "
                "{page_number, text, quality_score}"
            )
        page_number = value["page_number"]
        if isinstance(page_number, bool) or not isinstance(page_number, int):
            raise OCRPageAdapterError("page_number must be an integer")
        if page_number < 1:
            raise OCRPageAdapterError("page_number must be >= 1")
        numbers.append(page_number)
    if len(set(numbers)) != len(numbers):
        raise OCRPageAdapterError("page_number must not repeat")
    locator_unstable = numbers != list(range(1, len(numbers) + 1))

    normalized_parts: list[str] = []
    cursor = 0
    results: list[ParserResult] = []

    for value, page_number, kind in zip(page_values, numbers, kinds):
        if kind == "ocr":
            page_text, lines = _validate_ocr_block(value["ocr"])
            page_flags = [QualityFlag.OCR_USED]
            defer_reasons = {
                reason for line in lines for reason in line["defer_reasons"]
            }
            if DEFER_LOW_CONFIDENCE in defer_reasons:
                page_flags.append(QualityFlag.LOW_OCR_CONFIDENCE)
            if DEFER_AMBIGUOUS_ORDER in defer_reasons:
                page_flags.append(QualityFlag.LAYOUT_AMBIGUOUS)
            if DEFER_LIMIT in defer_reasons:
                page_flags.append(QualityFlag.TRUNCATED)
            if locator_unstable:
                page_flags.append(QualityFlag.LOCATOR_UNSTABLE)

            accepted = [line for line in lines if line["accepted"]]
            if page_text:
                if normalized_parts:
                    cursor += 2
                page_start = cursor
                normalized_parts.append(page_text)
                cursor += len(page_text)
            else:
                page_start = 0

            if accepted:
                status = ParseStatus.PARTIAL if defer_reasons else ParseStatus.PARSED
                for line in accepted:
                    local_start = int(line["char_start"])
                    local_end = int(line["char_end"])
                    results.append(
                        ParserResult(
                            source_id=source.source_id,
                            coordinates=EvidenceCoordinates(
                                page_number=page_number,
                                char_start=page_start + local_start,
                                char_end=page_start + local_end,
                            ),
                            raw_text=line["text"],
                            structured_value={
                                "kind": "ocr_line",
                                "page_number": page_number,
                                "line_index": line["line_index"],
                                "column_id": line["column_id"],
                            },
                            parser_name=PDF_OCR_PAGE_PARSER_NAME,
                            parser_version=PDF_OCR_PAGE_PARSER_VERSION,
                            parse_status=status,
                            quality_flags=page_flags,
                        )
                    )
            else:
                results.append(
                    ParserResult(
                        source_id=source.source_id,
                        coordinates=EvidenceCoordinates(page_number=page_number),
                        raw_text=None,
                        structured_value=None,
                        parser_name=PDF_OCR_PAGE_PARSER_NAME,
                        parser_version=PDF_OCR_PAGE_PARSER_VERSION,
                        parse_status=ParseStatus.FAILED,
                        quality_flags=page_flags + [QualityFlag.EMPTY_OUTPUT],
                    )
                )
            continue

        # --- plain text page --------------------------------------------
        text = _require_nfc_lf(value["text"], "page text").strip(" \t\n")
        quality_score = _require_ratio(value["quality_score"], "quality_score")
        flags: list[QualityFlag] = []
        if quality_score < _LOW_QUALITY_THRESHOLD:
            flags.append(QualityFlag.PARSER_WARNING)
        if locator_unstable:
            flags.append(QualityFlag.LOCATOR_UNSTABLE)

        if text:
            if normalized_parts:
                cursor += 2
            page_start = cursor
            normalized_parts.append(text)
            cursor += len(text)
            results.append(
                ParserResult(
                    source_id=source.source_id,
                    coordinates=EvidenceCoordinates(
                        page_number=page_number,
                        char_start=page_start,
                        char_end=page_start + len(text),
                    ),
                    raw_text=text,
                    structured_value={
                        "kind": "text_page",
                        "page_number": page_number,
                        "quality_score": quality_score,
                    },
                    parser_name=PDF_OCR_PAGE_PARSER_NAME,
                    parser_version=PDF_OCR_PAGE_PARSER_VERSION,
                    parse_status=(
                        ParseStatus.PARTIAL if flags else ParseStatus.PARSED
                    ),
                    quality_flags=flags,
                )
            )
        else:
            results.append(
                ParserResult(
                    source_id=source.source_id,
                    coordinates=EvidenceCoordinates(page_number=page_number),
                    raw_text=None,
                    structured_value=None,
                    parser_name=PDF_OCR_PAGE_PARSER_NAME,
                    parser_version=PDF_OCR_PAGE_PARSER_VERSION,
                    parse_status=ParseStatus.FAILED,
                    quality_flags=flags + [QualityFlag.EMPTY_OUTPUT],
                )
            )

    return PageAwarePDFResult(
        normalized_text="\n\n".join(normalized_parts),
        parser_results=tuple(results),
        page_count=len(page_values),
    )


__all__ = [
    "OCRPageAdapterError",
    "PDF_OCR_PAGE_ADAPTER_ID",
    "PDF_OCR_PAGE_PARSER_NAME",
    "PDF_OCR_PAGE_PARSER_VERSION",
    "adapt_ocr_pages",
]
