"""Source replay preserves parser quality while allowing conservative diagnostics."""
from dataclasses import replace
import hashlib

import pytest

from company_wiki.document_normalization import normalize_document, NormalizationLimits
from company_wiki.document_normalization.errors import ReplayError
from company_wiki.document_normalization.replay import verify_parsed_evidence_spans, replay_evidence_spans, replay_unit
from company_wiki.source_contract import EvidenceSpan, source_id_for_sha256


def example():
    data = b"<html><body><p>Annual subscriptions are billed per user.</p></body></html>"
    sha = hashlib.sha256(data).hexdigest()
    source_id = source_id_for_sha256(sha)
    doc = normalize_document(data, source_id=source_id, source_sha256=sha, mime_type="text/html")
    unit = doc.units[0]
    span = unit.to_evidence_span(topics=("core_business",), selection_reasons=("business_progress",))
    return data, sha, source_id, unit, span


def canonical_change(span, **changes):
    fields = {key: getattr(span, key) for key in (
        "source_id", "coordinates", "raw_text", "structured_value", "parser_name",
        "parser_version", "parse_status", "quality_flags")}
    # A self-consistent forged output must still fail against the real source.
    return EvidenceSpan.create(**{**fields, **changes})


@pytest.mark.parametrize("warning", ["table_structure_ambiguous", "layout_ambiguous", "parser_warning"])
def test_extra_diagnostic_warning_keeps_initial_and_original_replay(warning):
    data, sha, source_id, unit, span = example()
    selected = replace(span, quality_flags=tuple(dict.fromkeys((*span.quality_flags, warning))))
    assert verify_parsed_evidence_spans((unit,), source_id=source_id, evidence_spans=(selected,)) == 1
    assert replay_evidence_spans(data, source_id=source_id, source_sha256=sha,
        mime_type="text/html", evidence_spans=(selected,), limits=NormalizationLimits()) == 1
    assert selected.quality_flags == (*span.quality_flags, warning)
    assert unit.quality_flags == span.quality_flags
    assert replay_unit(data, source_sha256=sha, unit=unit, limits=NormalizationLimits()) == unit.raw_text


def test_parser_quality_cannot_be_removed_by_downstream_selection():
    _data, _sha, source_id, unit, span = example()
    parsed = replace(unit, quality_flags=("low_ocr_confidence",))
    with pytest.raises(ReplayError):
        verify_parsed_evidence_spans((parsed,), source_id=source_id, evidence_spans=(span,))


@pytest.mark.parametrize("field,value", [("raw_text", "Invented facts"), ("parser_version", "9.9.9")])
def test_additional_warning_does_not_hide_material_tampering(field, value):
    _data, _sha, source_id, unit, span = example()
    altered = canonical_change(span, quality_flags=("table_structure_ambiguous",), **{field: value})
    with pytest.raises(ReplayError):
        verify_parsed_evidence_spans((unit,), source_id=source_id, evidence_spans=(altered,))


def test_extra_diagnostic_is_not_a_forged_ocr_locator_or_parser_proof():
    _data, _sha, source_id, unit, span = example()
    metadata = {**span.structured_value, "source_locator": "cwp-pptx-image-ocr/1|forged"}
    altered = canonical_change(span, quality_flags=("ocr_used",), structured_value=metadata)
    with pytest.raises(ReplayError):
        verify_parsed_evidence_spans((unit,), source_id=source_id, evidence_spans=(altered,))


def test_unknown_quality_cannot_be_smuggled_as_a_verification_signal():
    _data, _sha, _source_id, _unit, span = example()
    with pytest.raises(ValueError, match="quality_flags"):
        replace(span, quality_flags=("verified_source",))
