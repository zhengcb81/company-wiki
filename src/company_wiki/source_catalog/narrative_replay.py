"""Version-bound locator replay primitives for selected narrative evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
from pathlib import Path

from company_wiki.source_contract import EvidenceSpan

from .narrative_document import NarrativeUnit
from .narrative_pdf_qa import QA_FRAGMENT_VERSIONS
from .narrative_native_ranges import (
    NATIVE_RANGE_BASE_VERSIONS, NATIVE_RANGE_PARSER_NAME, verify_native_range_span,
)


RoundtripKey = tuple[str, str, str, str]


@dataclass(frozen=True)
class PdfReplayPlan:
    parser_version: str
    table_pages: tuple[int, ...]
    native_ranges: bool = False


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


def _validate_source_bytes_binding(
    data: bytes,
    source_id: str,
    source_sha256: str,
    evidence_spans: Sequence[EvidenceSpan],
) -> None:
    if not isinstance(data, bytes):
        raise TypeError("PDF data must be bytes")
    if hashlib.sha256(data).hexdigest() != source_sha256:
        raise ValueError("PDF changed before evidence locator round-trip")
    if any(span.source_id != source_id for span in evidence_spans):
        raise ValueError("evidence source_id does not match the requested PDF")


def _narrative_metadata(span: EvidenceSpan) -> Mapping:
    if not isinstance(span.structured_value, Mapping):
        raise ValueError("PDF evidence requires a narrative binding")
    return span.structured_value


def _has_native_range(span: EvidenceSpan) -> bool:
    return span.parser_name == NATIVE_RANGE_PARSER_NAME or (
        isinstance(span.structured_value, Mapping)
        and span.structured_value.get("unit_kind") == "pdf_native_range")


def _parser_version(
    evidence_spans: Sequence[EvidenceSpan], default_parser_version: str
) -> str:
    versions = set()
    for span in evidence_spans:
        metadata = _narrative_metadata(span)
        native = _has_native_range(span)
        if native:
            binding = metadata.get("native_range", {})
            if (span.parser_name != NATIVE_RANGE_PARSER_NAME
                or span.parser_version not in NATIVE_RANGE_BASE_VERSIONS
                or metadata.get("unit_kind") != "pdf_native_range"
                or not isinstance(binding, Mapping)
                or binding.get("base_parser_version") != NATIVE_RANGE_BASE_VERSIONS[span.parser_version]):
                raise ValueError("unverified native range parser version")
            versions.add(NATIVE_RANGE_BASE_VERSIONS[span.parser_version])
        else:
            versions.add(span.parser_version)
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
        native_ranges=any(_has_native_range(span) for span in evidence_spans),
    )


def prepare_pdf_replay_bytes(
    data: bytes,
    *,
    source_id: str,
    source_sha256: str,
    evidence_spans: Sequence[EvidenceSpan],
    default_parser_version: str,
) -> PdfReplayPlan:
    """Validate immutable in-memory bytes and derive their replay plan."""
    _validate_source_bytes_binding(data, source_id, source_sha256, evidence_spans)
    return PdfReplayPlan(
        parser_version=_parser_version(evidence_spans, default_parser_version),
        table_pages=_table_pages(evidence_spans),
        native_ranges=any(_has_native_range(span) for span in evidence_spans),
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
    metadata = _narrative_metadata(span)
    return _roundtrip_key(
        locator=span.coordinates.locator(),
        raw_text=span.raw_text or "",
        role=str(metadata.get("source_role", "unknown")),
        unit_kind=str(metadata.get("unit_kind", "")),
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
    if QA_FRAGMENT_VERSIONS.intersection({unit.parser_version, span.parser_version}):
        if unit.parser_name != span.parser_name or unit.parser_version != span.parser_version:
            return False
        if any(unit.metadata.get(key) != expected.get(key) for key in (
            "cell_fragment_sha256", "qa_group_id", "qa_question_number", "qa_state",
        )):
            return False
    return bool(
        unit.metadata.get("cell_sha256") == expected.get("cell_sha256")
        and unit.metadata.get("cell_fragment_start")
        == expected.get("cell_fragment_start")
        and unit.metadata.get("cell_fragment_end")
        == expected.get("cell_fragment_end")
    )


def _span_matches(span: EvidenceSpan, matches: Sequence[NarrativeUnit]) -> bool:
    matches = tuple(unit for unit in matches
                    if (unit.source_id, unit.parser_name, unit.parser_version)
                    == (span.source_id, span.parser_name, span.parser_version)
                    # Consumers may add conservative diagnostics, but cannot
                    # erase a quality limitation observed by the source owner.
                    and set(unit.quality_flags).issubset(span.quality_flags))
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
    native_available = ({unit.unit_id: unit for unit in replay_units}
                        if any(_has_native_range(span) for span in evidence_spans) else {})
    verified: list[str] = []
    failed: list[str] = []
    for span in evidence_spans:
        if not isinstance(span.structured_value, Mapping):
            failed.append(span.span_id)
            continue
        if _has_native_range(span):
            target = verified if verify_native_range_span(span, native_available) else failed
            target.append(span.span_id)
            continue
        matches = available.get(span_roundtrip_key(span), ())
        target = verified if _span_matches(span, matches) else failed
        target.append(span.span_id)
    return tuple(verified), tuple(failed)


__all__ = [
    "PdfReplayPlan",
    "prepare_pdf_replay",
    "prepare_pdf_replay_bytes",
    "span_roundtrip_key",
    "unit_roundtrip_key",
    "verify_replayed_pdf_spans",
]
