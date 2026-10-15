"""PDF replay must use the source-owned language, including native ranges."""

from dataclasses import replace
from hashlib import sha256

import pytest

from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_replay import (
    NarrativeReplayError,
    replay_narrative_evidence,
)
from company_wiki.source_catalog.narrative_evidence import (
    parse_pdf_bytes,
    verify_pdf_evidence_spans,
    verify_pdf_evidence_spans_bytes,
)
from company_wiki.source_catalog.narrative_native_ranges import native_range_unit
from company_wiki.source_catalog.narrative_replay import verify_replayed_pdf_spans
from company_wiki.source_contract import EvidenceSpan, source_id_for_sha256


@pytest.fixture(scope="module")
def pdf_materials():
    """One synthetic original; each declared parse language is deliberate."""
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    try:
        page = document.new_page()
        page.insert_text(
            (60, 80),
            "The reactor completed customer qualification.",
            fontsize=12,
        )
        page.insert_text(
            (60, 110),
            "Commercial deliveries are planned for next quarter.",
            fontsize=12,
        )
        data = document.tobytes()
    finally:
        document.close()
    digest = sha256(data).hexdigest()
    source = source_id_for_sha256(digest)
    materials = {}
    for language in ("zh", "en", "mixed"):
        parsed = parse_pdf_bytes(
            data,
            source_id=source,
            source_sha256=digest,
            language=language,
            selector_version="0.9.0",
        )
        assert len(parsed.units) == 2, "fixture must contain two exact native sentences"
        native = native_range_unit(parsed.units)
        assert native is not None, "fixture must exercise a verifiable native range"
        span = native.to_evidence_span(
            topics=("business_progress",), selection_reasons=("reading_plan",)
        )
        selected = NarrativeSelectResult.from_dict(
            {
                "schema_version": "narrative-select-result/2.0",
                "source_ref": {
                    "schema_version": "2.0",
                    "document_id": "doc-synthetic-language-replay",
                    "source_id": source,
                    "content_sha256": digest,
                    "byte_size": len(data),
                    "mime_type": "application/pdf",
                },
                "expected_read_policy_sha256": digest,
                "source_metadata": {
                    "source_class": "filing",
                    "title": "Synthetic phased production update",
                    "document_kind": "annual_report",
                    "language": language,
                },
                "parser": {"name": "selective_pdf_parser", "version": "0.1.1"},
                "selector": {
                    "name": "selective_narrative_selector",
                    "version": "0.9.0",
                },
                "selection": {
                    "status": "partial",
                    "coverage_complete": True,
                    "source_units": 2,
                    "candidate_count": 1,
                    "selected_count": 1,
                    "omitted_candidate_count": 0,
                    "dropped_financial_count": 0,
                    "pages_total": 1,
                    "pages_read": 1,
                    "lines_total": 0,
                    "tables_total": 0,
                    "tables_scanned": 0,
                },
                "evidence_spans": [span.to_dict()],
                "prompt_review": {
                    "status": "not_reviewed",
                    "source_sha256": None,
                    "evidence_sha256": None,
                    "policy_hash": None,
                    "reviewed_at": None,
                },
                "transcript_lineage": None,
                "transcript_byte_bindings": [],
                "summary_scope": "selected_evidence_only",
            }
        )
        materials[language] = (data, selected, parsed)
    return materials


@pytest.mark.parametrize("language", ["zh", "en", "mixed"])
def test_native_fixture_matches_its_actual_parsed_language(pdf_materials, language):
    _, selected, parsed = pdf_materials[language]
    span = selected.evidence_spans[0]
    assert span.structured_value["language"] == language
    assert verify_replayed_pdf_spans(selected.evidence_spans, parsed.units) == (
        (span.span_id,),
        (),
    )


@pytest.mark.parametrize("language", ["zh", "en", "mixed"])
def test_pdf_replay_uses_selected_source_language(pdf_materials, language):
    data, selected, _ = pdf_materials[language]
    assert replay_narrative_evidence(data, selected) == 1


@pytest.mark.parametrize("language", ["en", "mixed"])
def test_pdf_bytes_replay_accepts_explicit_source_language(pdf_materials, language):
    data, selected, _ = pdf_materials[language]
    span = selected.evidence_spans[0]
    assert verify_pdf_evidence_spans_bytes(
        data,
        source_id=selected.source_ref.source_id,
        source_sha256=selected.source_ref.content_sha256,
        evidence_spans=selected.evidence_spans,
        language=language,
    ) == ((span.span_id,), ())


@pytest.mark.parametrize("language", ["en", "mixed"])
def test_pdf_path_replay_accepts_explicit_source_language(pdf_materials, language, tmp_path):
    data, selected, _ = pdf_materials[language]
    path = tmp_path / "synthetic.pdf"
    path.write_bytes(data)
    digest_before = sha256(path.read_bytes()).hexdigest()
    mtime_before = path.stat().st_mtime_ns
    span = selected.evidence_spans[0]
    assert verify_pdf_evidence_spans(
        path,
        source_id=selected.source_ref.source_id,
        source_sha256=selected.source_ref.content_sha256,
        evidence_spans=selected.evidence_spans,
        language=language,
    ) == ((span.span_id,), ())
    assert sha256(path.read_bytes()).hexdigest() == digest_before
    assert path.stat().st_mtime_ns == mtime_before


def test_pdf_default_zh_remains_compatible(pdf_materials, tmp_path):
    data, selected, _ = pdf_materials["zh"]
    path = tmp_path / "legacy-default.pdf"
    path.write_bytes(data)
    expected = ((selected.evidence_spans[0].span_id,), ())
    arguments = {
        "source_id": selected.source_ref.source_id,
        "source_sha256": selected.source_ref.content_sha256,
        "evidence_spans": selected.evidence_spans,
    }
    assert verify_pdf_evidence_spans_bytes(data, **arguments) == expected
    assert verify_pdf_evidence_spans(path, **arguments) == expected


@pytest.mark.parametrize("wrong_language", ["zh", "mixed"])
def test_native_range_language_mismatch_is_still_rejected(pdf_materials, wrong_language):
    data, selected, _ = pdf_materials["en"]
    _, _, wrong_parsed = pdf_materials[wrong_language]
    span = selected.evidence_spans[0]
    assert verify_replayed_pdf_spans(selected.evidence_spans, wrong_parsed.units) == (
        (),
        (span.span_id,),
    )
    mismatched = replace(
        selected,
        source_metadata=replace(selected.source_metadata, language=wrong_language),
    )
    with pytest.raises(NarrativeReplayError):
        replay_narrative_evidence(data, mismatched)


@pytest.mark.parametrize("mutation", ["same_size", "different_size"])
def test_replay_rejects_changed_original_before_parsing(pdf_materials, mutation):
    data, selected, _ = pdf_materials["en"]
    changed = bytes([data[0] ^ 1]) + data[1:] if mutation == "same_size" else data + b"x"
    with pytest.raises(NarrativeReplayError, match="original bytes differ"):
        replay_narrative_evidence(changed, selected)


def test_replay_rejects_different_source_before_parsing(pdf_materials):
    data, selected, _ = pdf_materials["zh"]
    with pytest.raises(ValueError, match="source_id does not match"):
        verify_pdf_evidence_spans_bytes(
            data,
            source_id=source_id_for_sha256("f" * 64),
            source_sha256=selected.source_ref.content_sha256,
            evidence_spans=selected.evidence_spans,
        )


@pytest.mark.parametrize("parser_field", ["parser_name", "parser_version"])
def test_replay_rejects_wrong_native_parser_before_parsing(pdf_materials, parser_field):
    data, selected, _ = pdf_materials["zh"]
    value = selected.evidence_spans[0].to_dict()
    # Rebuild all derived IDs so the negative case is a valid EvidenceSpan,
    # rather than a malformed DTO that fails before reaching replay planning.
    value[parser_field] = "wrong-native-parser" if parser_field == "parser_name" else "9.9.9"
    span = EvidenceSpan.create(
        source_id=value["source_id"],
        coordinates=selected.evidence_spans[0].coordinates,
        raw_text=value["raw_text"],
        structured_value=value["structured_value"],
        parser_name=value["parser_name"],
        parser_version=value["parser_version"],
        parse_status=value["parse_status"],
        quality_flags=value["quality_flags"],
    )
    with pytest.raises(ValueError, match="unverified native range parser version"):
        verify_pdf_evidence_spans_bytes(
            data,
            source_id=selected.source_ref.source_id,
            source_sha256=selected.source_ref.content_sha256,
            evidence_spans=(span,),
        )
