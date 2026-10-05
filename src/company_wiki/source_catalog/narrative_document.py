"""Stable in-memory document and selected-evidence structures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import hashlib
from types import MappingProxyType
from typing import Any, Literal
import unicodedata

from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan, ParseStatus


@dataclass(frozen=True)
class NarrativeUnit:
    """One transient source block with a replayable locator."""

    unit_id: str
    source_id: str
    parser_name: str
    parser_version: str
    coordinates: EvidenceCoordinates
    raw_text: str
    unit_kind: str
    source_role: str
    language: str
    quality_flags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.raw_text or self.raw_text != self.raw_text.strip():
            raise ValueError("narrative unit text must be non-empty and trimmed")
        if unicodedata.normalize("NFC", self.raw_text) != self.raw_text:
            raise ValueError("narrative unit text must use NFC")
        if not self.unit_id.startswith("urn:company-wiki:narrative-unit:sha256:"):
            raise ValueError("unit_id must be a canonical narrative-unit SHA-256")
        if not isinstance(self.coordinates, EvidenceCoordinates):
            raise TypeError("coordinates must be EvidenceCoordinates")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()

    def to_evidence_span(
        self,
        *,
        topics: Sequence[str],
        selection_reasons: Sequence[str],
        selection_group_id: str | None = None,
    ) -> EvidenceSpan:
        structured = dict(self.metadata)
        structured.update(
            {
                "language": self.language,
                "selection_reasons": list(selection_reasons),
                "source_role": self.source_role,
                "text_sha256": self.text_sha256,
                "topics": list(topics),
                "unit_kind": self.unit_kind,
            }
        )
        if selection_group_id is not None:
            structured["selection_group_id"] = selection_group_id
        return EvidenceSpan.create(
            source_id=self.source_id,
            coordinates=self.coordinates,
            raw_text=self.raw_text,
            structured_value=structured,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            parse_status=ParseStatus.PARSED,
            quality_flags=self.quality_flags,
        )


@dataclass(frozen=True)
class DocumentStructure:
    """Format-neutral parsed structure plus explicit coverage state."""

    source_id: str
    source_sha256: str
    language: str
    units: tuple[NarrativeUnit, ...]
    page_count: int = 0
    pages_read: int = 0
    opaque_pages: tuple[int, ...] = ()
    table_scan_pages: tuple[int, ...] = ()
    deferred_table_pages: tuple[int, ...] = ()
    line_count: int = 0
    errors: tuple[str, ...] = ()

    @property
    def coverage_complete(self) -> bool:
        if self.errors or self.opaque_pages or self.deferred_table_pages:
            return False
        if self.page_count:
            return self.pages_read == self.page_count
        return self.line_count > 0


NarrativeParseResult = DocumentStructure


@dataclass(frozen=True)
class NarrativeEvidencePackage:
    source_id: str
    source_sha256: str
    document_kind: str
    status: Literal[
        "selected", "partial", "skipped_no_narrative", "needs_review", "blocked"
    ]
    evidence_spans: tuple[EvidenceSpan, ...]
    selection_limit: int
    candidate_count: int
    dropped_financial_count: int
    source_units: int
    omitted_candidate_count: int
    coverage_complete: bool

    @property
    def selected_text_bytes(self) -> int:
        return sum(
            len((span.raw_text or "").encode("utf-8"))
            for span in self.evidence_spans
        )

    def summary_input(self) -> dict[str, Any]:
        """Return selected evidence only; the full document is never included."""
        return selected_summary_input(
            source_id=self.source_id, source_sha256=self.source_sha256,
            document_kind=self.document_kind, evidence_spans=self.evidence_spans,
        )


def selected_summary_input(
    *, source_id: str, source_sha256: str, document_kind: str,
    evidence_spans: tuple[EvidenceSpan, ...],
) -> dict[str, Any]:
    """Group selected spans in memory for summary input or original-text search."""
    return {
        "schema_version": "narrative-summary-input/0.2.0",
        "source_id": source_id, "source_sha256": source_sha256,
        "document_kind": document_kind, "summary_scope": "selected_evidence_only",
        "evidence": [
            _summary_group(group_id, members)
            for group_id, members in _group_spans(evidence_spans).items()
        ],
    }


def _group_spans(
    spans: tuple[EvidenceSpan, ...],
) -> dict[str, list[EvidenceSpan]]:
    grouped: dict[str, list[EvidenceSpan]] = {}
    for span in spans:
        group_id = span.structured_value.get("selection_group_id")
        key = str(group_id) if group_id is not None else span.span_id
        grouped.setdefault(key, []).append(span)
    return grouped


def _span_order(span: EvidenceSpan) -> tuple[int, int, int, int, int]:
    coordinates = span.coordinates
    return (
        _zero(coordinates.page_number),
        _zero(coordinates.paragraph_index),
        _zero(coordinates.table_index),
        _zero(coordinates.row_index),
        _zero(coordinates.column_index),
    )


def _zero(value: int | None) -> int:
    return 0 if value is None else value


def _summary_group(group_id: str, members: list[EvidenceSpan]) -> dict[str, Any]:
    members.sort(key=_span_order)
    member_ids = [span.span_id for span in members]
    language = str(members[0].structured_value.get("language", "zh"))
    separator = " " if language.startswith("en") else ""
    raw_text = separator.join(span.raw_text or "" for span in members)
    row: dict[str, Any] = {
        "evidence_ids": member_ids,
        "locators": [span.locator for span in members],
        "source_role": members[0].structured_value.get("source_role", "unknown"),
        "topics": _span_values(members, "topics"),
        "selection_reasons": _span_values(members, "selection_reasons"),
        "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        "raw_text": raw_text,
        "quality_flags": sorted({flag for span in members for flag in span.quality_flags}),
        "parser_name": members[0].parser_name,
        "parser_version": members[0].parser_version,
    }
    _add_single_or_group_fields(row, group_id, members)
    return row


def _span_values(members: list[EvidenceSpan], key: str) -> list[str]:
    return sorted(
        {
            str(value)
            for span in members
            for value in span.structured_value.get(key, ())
        }
    )


def _add_single_or_group_fields(
    row: dict[str, Any], group_id: str, members: list[EvidenceSpan]
) -> None:
    if len(members) == 1:
        row["evidence_id"] = members[0].span_id
        row["locator"] = members[0].locator
        return
    row["context_group_id"] = group_id
    row["context_member_count"] = len(members)


__all__ = [
    "DocumentStructure",
    "NarrativeEvidencePackage",
    "NarrativeParseResult",
    "NarrativeUnit",
    "selected_summary_input",
]
