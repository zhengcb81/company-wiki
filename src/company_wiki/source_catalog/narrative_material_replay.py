"""Shared original-byte locator replay for publication and transport."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
from typing import TYPE_CHECKING, Protocol

from .narrative_evidence import (
    verify_transcript_evidence_spans,
)
from .transcript_text_extract import (
    TranscriptTextLine,
    extract_transcript_material,
)
from company_wiki.source_contract import EvidenceSpan
from company_wiki.source_contract.selection_annotations import READING_ANNOTATION_FIELDS
from company_wiki.source_contract.source_version import SourceRefMismatchError, VerifiedContent
from .narrative_normalization import NarrativeNormalization
from .narrative_pdf_reading import PdfReading

from .narrative_contracts import (
    NarrativeBundle,
    NarrativeSelectResult,
    TranscriptByteBinding,
)
from .narrative_formats import NORMALIZED_MIME_TYPES, parser_component

if TYPE_CHECKING:
    from .narrative_official_json import VerifiedProjectionView


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
        language: str = "zh",
    ) -> tuple[tuple[str, ...], tuple[str, ...]]: ...


def _require_full_replay(
    spans: Sequence[EvidenceSpan],
    verified: Sequence[str],
    failed: Sequence[str],
) -> None:
    expected = {span.span_id for span in spans}
    if failed or set(verified) != expected or len(verified) != len(expected):
        raise NarrativeReplayError("not every selected locator replayed exactly")


def _verify_transcript_bindings(
    lines: Sequence[TranscriptTextLine],
    selected: NarrativeSelectResult | NarrativeBundle,
) -> None:
    spans = {span.span_id: span for span in selected.evidence_spans}
    binding_ids = [binding.evidence_id for binding in selected.transcript_byte_bindings]
    if len(binding_ids) != len(spans) or set(binding_ids) != set(spans):
        raise NarrativeReplayError(
            "transcript byte binding count differs from evidence"
        )
    for binding in selected.transcript_byte_bindings:
        _verify_transcript_binding(lines, spans[binding.evidence_id], binding)


def _verify_transcript_binding(
    lines: Sequence[TranscriptTextLine],
    span: EvidenceSpan,
    binding: TranscriptByteBinding,
) -> None:
    bound_lines = tuple(
        line
        for line in lines
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
        raise NarrativeReplayError(
            "transcript byte binding differs from original bytes"
        )


def _replay_transcript(
    data: bytes,
    selected: NarrativeSelectResult | NarrativeBundle,
) -> None:
    material = extract_transcript_material(
        data, mime_type=selected.source_ref.mime_type
    )
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


def _replay_normalized(original: bytes | VerifiedContent, selected, normalization=None):
    """Dispatch recorded parser identity and replay all selected media once."""
    source = selected.source_ref
    version = (
        selected.parser.version
        if isinstance(selected, NarrativeSelectResult)
        else selected.versions.parser
    )
    name = selected.parser.name if isinstance(selected, NarrativeSelectResult) else None
    port = normalization or NarrativeNormalization()
    expected_name, _ = parser_component(
        source.mime_type, normalization=port, parser_version=version
    )
    if name is not None and name != expected_name:
        raise NarrativeReplayError("unsupported normalization parser")
    if any(span.parser_version != version for span in selected.evidence_spans):
        raise NarrativeReplayError("selected span parser differs from bound generation")
    options = {
        "mime_type": source.mime_type,
        "evidence_spans": selected.evidence_spans,
        "parser_version": version,
        "language": selected.source_metadata.language,
    }
    if isinstance(original, VerifiedContent):
        replay_verified = getattr(port, "replay_verified", None)
        if callable(replay_verified):
            replay_verified(original, **options)
            return
        original = original.data
    port.replay(original, source_id=source.source_id, source_sha256=source.content_sha256, **options)


def replay_narrative_evidence(
    data: bytes,
    selected: NarrativeSelectResult | NarrativeBundle,
    *,
    pdf_replayer: PdfEvidenceReplayer | None = None,
    normalization: NarrativeNormalization | None = None,
    pdf_reading: PdfReading | None = None,
) -> int:
    """Verify standalone bytes and replay all selected locators."""
    source = selected.source_ref
    if (
        not isinstance(data, bytes)
        or len(data) != source.byte_size
        or hashlib.sha256(data).hexdigest() != source.content_sha256
    ):
        raise NarrativeReplayError("original bytes differ from source reference")
    return _replay_original(data, selected, pdf_replayer=pdf_replayer,
                            normalization=normalization, pdf_reading=pdf_reading)


def replay_verified_narrative_evidence(
    content: VerifiedContent,
    selected: NarrativeSelectResult | NarrativeBundle,
    *,
    normalization: NarrativeNormalization | None = None,
    pdf_reading: PdfReading | None = None,
) -> int:
    """Replay one source-owner observation against this exact selected version."""
    source = selected.source_ref
    if (
        not isinstance(content, VerifiedContent)
        or content.document_id != source.document_id
        or content.source_id != source.source_id
        or content.content_sha256 != source.content_sha256
        or content.byte_size != source.byte_size
        or not isinstance(content.data, bytes)
        or len(content.data) != content.byte_size
    ):
        raise NarrativeReplayError("verified source differs from selected source reference")
    try:
        verified = VerifiedContent.verified_observation(content)
    except SourceRefMismatchError as exc:
        raise NarrativeReplayError("verified source differs from selected source reference") from exc
    return _replay_original(verified, selected, normalization=normalization, pdf_reading=pdf_reading)


def _replay_original(
    original: bytes | VerifiedContent,
    selected: NarrativeSelectResult | NarrativeBundle,
    *,
    pdf_replayer: PdfEvidenceReplayer | None = None,
    normalization: NarrativeNormalization | None = None,
    pdf_reading: PdfReading | None = None,
) -> int:
    source = selected.source_ref
    data = original.data if isinstance(original, VerifiedContent) else original
    try:
        if selected.source_metadata.source_class == "filing":
            if source.mime_type in NORMALIZED_MIME_TYPES:
                _replay_normalized(original, selected, normalization)
                return len(selected.evidence_spans)
            if pdf_replayer is not None and pdf_reading is not None:
                raise ValueError("provide one complete PDF reading implementation")
            reading = pdf_reading or PdfReading(replayer=pdf_replayer)
            if isinstance(original, VerifiedContent):
                verified, failed = reading.replay_verified(
                    original, evidence_spans=selected.evidence_spans, language=selected.source_metadata.language,
                )
            else:
                verified, failed = reading.replay(
                    data, source_id=source.source_id, source_sha256=source.content_sha256,
                    evidence_spans=selected.evidence_spans, language=selected.source_metadata.language,
                )
            _require_full_replay(selected.evidence_spans, verified, failed)
        else:
            _replay_transcript(data, selected)
    except (RuntimeError, ValueError) as exc:
        raise NarrativeReplayError("selected evidence could not be replayed") from exc
    return len(selected.evidence_spans)


_SELECTION_ANNOTATIONS = frozenset(
    {
        "topics",
        "selection_reasons",
        "selection_group_id",
        *READING_ANNOTATION_FIELDS,
        "unit_kind",
        "text_sha256",
    }
)


def _projection_span_identity(span: EvidenceSpan) -> dict:
    value = span.to_dict()
    # These hashes necessarily change when selector annotations are added.
    value.pop("span_id")
    value.pop("output_sha256")
    metadata = value["structured_value"]
    if (
        "text_sha256" in metadata
        and metadata["text_sha256"]
        != hashlib.sha256((span.raw_text or "").encode()).hexdigest()
    ):
        raise NarrativeReplayError("selected text hash differs from original field")
    if "unit_kind" in metadata and metadata["unit_kind"] != "official_json_field":
        raise NarrativeReplayError("selected unit kind differs from original field")
    for key in _SELECTION_ANNOTATIONS:
        metadata.pop(key, None)
    return value


def replay_verified_projection(
    view: VerifiedProjectionView,
    selected: NarrativeSelectResult | NarrativeBundle,
) -> int:
    """Replay selected locators against one already source-verified export.

    The source port owns byte/issuer/as-of verification. This layer checks that
    selection changed only selector annotations, never source text or lineage;
    it neither reopens parents nor pretends the real anchor is the projection.
    """
    if view.subject != selected.subject or selected.subject.kind != "official_json":
        raise NarrativeReplayError("verified projection differs from selected subject")
    if isinstance(selected, (NarrativeSelectResult, NarrativeBundle)):
        if selected.source_metadata.language != (view.language or "unknown"):
            raise NarrativeReplayError(
                "selected language differs from verified native fields"
            )
        if isinstance(selected, NarrativeSelectResult):
            parser_version = selected.parser.version
            if any(
                span.parser_name != selected.parser.name for span in view.evidence_spans
            ):
                raise NarrativeReplayError(
                    "selected parser differs from verified native fields"
                )
        else:
            parser_version = selected.versions.parser
        if any(span.parser_version != parser_version for span in view.evidence_spans):
            raise NarrativeReplayError(
                "selected parser generation differs from verified native fields"
            )
    originals = {
        (
            span.source_id,
            span.structured_value.get("pointer"),
        ): _projection_span_identity(span)
        for span in view.evidence_spans
    }
    seen = set()
    for span in selected.evidence_spans:
        key = (span.source_id, span.structured_value.get("pointer"))
        if key in seen or originals.get(key) != _projection_span_identity(span):
            raise NarrativeReplayError(
                "selected field differs from verified projection"
            )
        seen.add(key)
    return len(selected.evidence_spans)


__all__ = [
    "NarrativeReplayError",
    "PdfEvidenceReplayer",
    "replay_narrative_evidence",
    "replay_verified_narrative_evidence",
    "replay_verified_projection",
]
