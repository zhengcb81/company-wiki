"""Version-bound locator replay primitives for selected narrative evidence."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
from pathlib import Path

from company_wiki.source_contract import EvidenceSpan

from .narrative_document import NarrativeUnit


RoundtripKey = tuple[str, str, str, str]


@dataclass(frozen=True)
class PdfReplayPlan:
    parser_version: str
    table_pages: tuple[int, ...]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_source_binding(
    path: Path,
    source_id: str,
    source_sha256: str,
    evidence_spans: Sequence[EvidenceSpan],
) -> None:
    if _file_sha256(path) != source_sha256:
        raise ValueError("PDF changed before evidence locator round-trip")
    if any(span.source_id != source_id for span in evidence_spans):
        raise ValueError("evidence source_id does not match the requested PDF")


def _parser_version(
    evidence_spans: Sequence[EvidenceSpan], default_parser_version: str
) -> str:
    versions = {span.parser_version for span in evidence_spans}
    if len(versions) > 1:
        raise ValueError("round-trip verification requires one parser version")
    return next(iter(versions), default_parser_version)


def _table_pages(evidence_spans: Sequence[EvidenceSpan]) -> tuple[int, ...]:
    pages: set[int] = set()
    for span in evidence_spans:
        page = span.coordinates.page_number
        if span.coordinates.table_index is not None and page is not None:
            pages.add(page)
    return tuple(sorted(pages))


def prepare_pdf_replay(
    path: Path,
    *,
    source_id: str,
    source_sha256: str,
    evidence_spans: Sequence[EvidenceSpan],
    default_parser_version: str,
) -> PdfReplayPlan:
    """Validate immutable inputs and derive the minimal deterministic replay plan."""
    _validate_source_binding(path, source_id, source_sha256, evidence_spans)
    return PdfReplayPlan(
        parser_version=_parser_version(evidence_spans, default_parser_version),
        table_pages=_table_pages(evidence_spans),
    )


def _roundtrip_key(
    *, locator: str, raw_text: str, role: str, unit_kind: str
) -> RoundtripKey:
    return (
        locator,
        hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        role,
        unit_kind,
    )


def unit_roundtrip_key(unit: NarrativeUnit) -> RoundtripKey:
    return _roundtrip_key(
        locator=unit.coordinates.locator(),
        raw_text=unit.raw_text,
        role=unit.source_role,
        unit_kind=unit.unit_kind,
    )


def span_roundtrip_key(span: EvidenceSpan) -> RoundtripKey:
    return _roundtrip_key(
        locator=span.coordinates.locator(),
        raw_text=span.raw_text or "",
        role=str(span.structured_value.get("source_role", "unknown")),
        unit_kind=str(span.structured_value.get("unit_kind", "")),
    )


def _available_units(
    units: Sequence[NarrativeUnit],
) -> dict[RoundtripKey, list[NarrativeUnit]]:
    available: dict[RoundtripKey, list[NarrativeUnit]] = {}
    for unit in units:
        available.setdefault(unit_roundtrip_key(unit), []).append(unit)
    return available


def _qa_fragment_matches(unit: NarrativeUnit, span: EvidenceSpan) -> bool:
    expected = span.structured_value
    return bool(
        unit.metadata.get("cell_sha256") == expected.get("cell_sha256")
        and unit.metadata.get("cell_fragment_start")
        == expected.get("cell_fragment_start")
        and unit.metadata.get("cell_fragment_end")
        == expected.get("cell_fragment_end")
    )


def _span_matches(span: EvidenceSpan, matches: Sequence[NarrativeUnit]) -> bool:
    if not matches:
        return False
    if span.structured_value.get("unit_kind") != "pdf_table_qa_fragment":
        return True
    return any(_qa_fragment_matches(unit, span) for unit in matches)


def verify_replayed_pdf_spans(
    evidence_spans: Sequence[EvidenceSpan], replay_units: Sequence[NarrativeUnit]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Match selected spans against units reconstructed by the pinned parser."""
    available = _available_units(replay_units)
    verified: list[str] = []
    failed: list[str] = []
    for span in evidence_spans:
        matches = available.get(span_roundtrip_key(span), ())
        target = verified if _span_matches(span, matches) else failed
        target.append(span.span_id)
    return tuple(verified), tuple(failed)


__all__ = [
    "PdfReplayPlan",
    "prepare_pdf_replay",
    "span_roundtrip_key",
    "unit_roundtrip_key",
    "verify_replayed_pdf_spans",
]
