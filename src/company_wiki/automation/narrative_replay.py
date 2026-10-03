"""Shared original-byte locator replay for publication and transport."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
from typing import Protocol

from company_wiki.source_catalog.narrative_evidence import (
    verify_pdf_evidence_spans_bytes,
    verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.transcript_text_extract import (
    TranscriptTextLine,
    extract_transcript_material,
)
from company_wiki.source_contract import EvidenceSpan

from .narrative_contracts import NarrativeBundle, NarrativeSelectResult, TranscriptByteBinding


class NarrativeReplayError(ValueError):
    """Selected evidence cannot be grounded in the bound original bytes."""


class PdfEvidenceReplayer(Protocol):
    def __call__(
        self,
        data: bytes,
        *,
        source_id: str,
        source_sha256: str,
        evidence_spans: Sequence[EvidenceSpan],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]: ...


def _require_full_replay(
    spans: Sequence[EvidenceSpan], verified: Sequence[str], failed: Sequence[str],
) -> None:
    expected = {span.span_id for span in spans}
    if failed or set(verified) != expected or len(verified) != len(expected):
        raise NarrativeReplayError("not every selected locator replayed exactly")


def _verify_transcript_bindings(
    lines: Sequence[TranscriptTextLine], selected: NarrativeSelectResult | NarrativeBundle,
) -> None:
    spans = {span.span_id: span for span in selected.evidence_spans}
    binding_ids = [binding.evidence_id for binding in selected.transcript_byte_bindings]
    if len(binding_ids) != len(spans) or set(binding_ids) != set(spans):
        raise NarrativeReplayError("transcript byte binding count differs from evidence")
    for binding in selected.transcript_byte_bindings:
        _verify_transcript_binding(lines, spans[binding.evidence_id], binding)


def _verify_transcript_binding(
    lines: Sequence[TranscriptTextLine], span: EvidenceSpan, binding: TranscriptByteBinding,
) -> None:
    bound_lines = tuple(
        line for line in lines
        if binding.material_line_start <= line.line_number <= binding.material_line_end
    )
    actual = tuple(
        (line.source_byte_start, line.source_byte_end) for line in bound_lines
    )
    if (
        span.structured_value.get("line_start") != binding.material_line_start
        or span.structured_value.get("line_end") != binding.material_line_end
        or actual != binding.source_byte_ranges
    ):
        raise NarrativeReplayError("transcript byte binding differs from original bytes")


def _replay_transcript(
    data: bytes, selected: NarrativeSelectResult | NarrativeBundle,
) -> None:
    material = extract_transcript_material(data, mime_type=selected.source_ref.mime_type)
    material.verify(data)
    if (
        selected.transcript_lineage is None
        or material.lineage_dict() != selected.transcript_lineage.to_dict()
    ):
        raise NarrativeReplayError("transcript material lineage differs from selection")
    _verify_transcript_bindings(material.lines, selected)
    verified, failed = verify_transcript_evidence_spans(
        material.text_utf8,
        source_id=selected.source_ref.source_id,
        source_sha256=selected.source_ref.content_sha256,
        evidence_spans=selected.evidence_spans,
        language=selected.source_metadata.language,
    )
    _require_full_replay(selected.evidence_spans, verified, failed)


def replay_narrative_evidence(
    data: bytes,
    selected: NarrativeSelectResult | NarrativeBundle,
    *,
    pdf_replayer: PdfEvidenceReplayer | None = None,
) -> int:
    """Replay all selected locators; quality diagnostics remain unchanged."""
    source = selected.source_ref
    if len(data) != source.byte_size or hashlib.sha256(data).hexdigest() != source.content_sha256:
        raise NarrativeReplayError("original bytes differ from source reference")
    try:
        if selected.source_metadata.source_class == "filing":
            replayer = pdf_replayer or verify_pdf_evidence_spans_bytes
            verified, failed = replayer(
                data, source_id=source.source_id,
                source_sha256=source.content_sha256,
                evidence_spans=selected.evidence_spans,
            )
            _require_full_replay(selected.evidence_spans, verified, failed)
        else:
            _replay_transcript(data, selected)
    except (RuntimeError, ValueError) as exc:
        raise NarrativeReplayError("selected evidence could not be replayed") from exc
    return len(selected.evidence_spans)
