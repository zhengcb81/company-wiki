"""Printed turns in PDF transcripts retain source-exact evidence and scope."""

from hashlib import sha256

import pytest

from company_wiki.resource_budget import new_document_work_budget
from company_wiki.source_catalog.narrative_pdf_reading import PdfReading, PdfReadingRequest
from company_wiki.source_catalog.narrative_selector_binding import bind_narrative_selector
from company_wiki.source_catalog.reading_recipe import business_algorithm_hashes
from company_wiki.source_contract import EvidenceSpan, source_id_for_sha256


_BUSINESS = "We launched a new product and expanded overseas capacity for customers."


def _select_pdf(*blocks: str, kind: str = "investor_call_transcript"):
    pymupdf = pytest.importorskip("pymupdf")
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=760)
        for index, block in enumerate(blocks):
            page.insert_text((50, 60 + index * 60), block)
        data = pdf.tobytes()
    digest = sha256(data).hexdigest()
    request = PdfReadingRequest(
        source_id_for_sha256(digest), digest, "en", document_kind=kind,
    )
    reader = PdfReading()
    parsed, package = reader.select(
        data, request, selector=bind_narrative_selector(selector_version="0.9.0"),
        work_budget=new_document_work_budget(), checkpoint=lambda: None,
    )
    return reader, data, request, parsed, package


@pytest.mark.parametrize("label", ["CEO", "CFO", "Jane Doe, Chief Executive Officer"])
def test_pdf_transcript_selects_printed_turn_without_rewriting_original(label):
    original = f"{label}: {_BUSINESS}"
    reader, data, request, parsed, package = _select_pdf(original)
    assert len(parsed.units) == 1 and parsed.units[0].raw_text == original
    assert len(package.evidence_spans) == 1
    span = package.evidence_spans[0]
    assert span.raw_text == original
    assert span.coordinates == parsed.units[0].coordinates
    assert span.structured_value["source_role"] == parsed.units[0].source_role
    assert span.structured_value["printed_turn"]["role"] == "management"
    assert reader.replay(
        data, source_id=request.source_id, source_sha256=request.source_sha256,
        evidence_spans=(span,), language="en",
    ) == ((span.span_id,), ())


def test_pdf_transcript_keeps_analyst_assertions_out_of_management_support():
    management = f"CFO: {_BUSINESS}"
    _, _, _, _, package = _select_pdf(
        "Earnings Call Transcript",
        "Analyst: We launched a new product for our subscribers.",
        "Analyst: Are you planning to expand overseas capacity?",
        management,
    )
    assert [span.raw_text for span in package.evidence_spans] == [management]
    assert package.evidence_spans[0].structured_value["printed_turn"]["role"] == "management"


@pytest.mark.parametrize("body, expected_reason", [
    ("We have not launched a new product for overseas customers.", "operating_restriction"),
    ("We plan to launch a new product for overseas customers if certification is granted.", "operating_plan"),
])
def test_pdf_transcript_retains_negation_and_plan_language(body, expected_reason):
    original = f"CEO: {body}"
    _, _, _, _, package = _select_pdf(original)
    assert [span.raw_text for span in package.evidence_spans] == [original]
    assert expected_reason in package.evidence_spans[0].structured_value["selection_reasons"]
    assert all("operating_milestone" not in span.structured_value["selection_reasons"]
               for span in package.evidence_spans)


def test_ordinary_pdf_keeps_its_normal_prose_path():
    _, _, _, _, package = _select_pdf(_BUSINESS, kind="annual_report")
    assert [span.raw_text for span in package.evidence_spans] == [_BUSINESS]
    assert "printed_turn" not in package.evidence_spans[0].structured_value


def test_pdf_replay_refuses_changed_printed_turn_metadata():
    reader, data, request, _, package = _select_pdf(f"CFO: {_BUSINESS}")
    span = package.evidence_spans[0]
    altered = EvidenceSpan.create(
        source_id=span.source_id, coordinates=span.coordinates, raw_text=span.raw_text,
        structured_value={
            **span.structured_value,
            "printed_turn": {**span.structured_value["printed_turn"], "role": "analyst"},
        },
        parser_name=span.parser_name, parser_version=span.parser_version,
        parse_status=span.parse_status, quality_flags=span.quality_flags,
    )
    assert reader.replay(
        data, source_id=request.source_id, source_sha256=request.source_sha256,
        evidence_spans=(altered,), language="en",
    ) == ((), (altered.span_id,))


def test_pdf_transcript_does_not_donate_mixed_speaker_block_as_one_assertion():
    _, _, _, parsed, package = _select_pdf(
        f"CFO: {_BUSINESS}\nAnalyst: We launched our research coverage last week."
    )
    assert len(parsed.units) == 1  # The physical parser retains this as one block.
    assert not package.evidence_spans


@pytest.mark.parametrize("label", [
    "Analyst:",
    "John Doe, Analyst: First, let me discuss our view.",
    "Q: Can you elaborate?",
    "A: This answer is not identified with a printed speaker.",
])
def test_pdf_detached_analyst_body_stays_context_until_a_new_turn(label):
    management = "CFO: We expanded overseas capacity and opened a new facility for customers."
    _, _, _, _, package = _select_pdf(label, _BUSINESS, management)
    assert [span.raw_text for span in package.evidence_spans] == [management]


def test_pdf_detached_management_body_replays_its_printed_label():
    reader, data, request, parsed, package = _select_pdf("CFO:", _BUSINESS)
    label, body = parsed.units
    span, = package.evidence_spans
    assert span.raw_text == _BUSINESS and span.coordinates == body.coordinates
    assert span.structured_value["printed_turn"]["label_locator"] == label.coordinates.locator()
    assert span.structured_value["printed_turn"]["role"] == "management"
    assert reader.replay(
        data, source_id=request.source_id, source_sha256=request.source_sha256,
        evidence_spans=(span,), language="en",
    ) == ((span.span_id,), ())


@pytest.mark.parametrize("heading", ["Forward-Looking Statements", "Safe Harbor Statement", "Disclaimer"])
def test_pdf_disclosure_heading_ends_attribution_until_next_speaker(heading):
    opening = "We launched a new product for customers."
    next_turn = "CEO: We began testing expanded production with customers."
    _, _, _, _, package = _select_pdf("CFO:", opening, heading, _BUSINESS, next_turn)
    assert [span.raw_text for span in package.evidence_spans] == [opening, next_turn]


@pytest.mark.parametrize("other_turn", [
    "Analyst: We launched coverage last week.",
    "Jane Doe, Analyst: We launched coverage last week.",
    "Q: Did you expand capacity?",
])
def test_pdf_same_physical_line_can_contain_two_printed_turns(other_turn):
    _, _, _, parsed, package = _select_pdf(f"CFO: {_BUSINESS} {other_turn}")
    assert len(parsed.units) == 1
    assert not package.evidence_spans


def test_pdf_inline_word_is_not_an_observed_speaker_change():
    text = f"CFO: {_BUSINESS} The label says Analyst: name."
    _, _, _, _, package = _select_pdf(text)
    assert [span.raw_text for span in package.evidence_spans] == [text]


def test_pdf_recipe_tracks_printed_turn_grammar_in_its_owner():
    key = "company_wiki.document_model.turns"
    assert key in business_algorithm_hashes(pdf_frontend=True)
    assert key not in business_algorithm_hashes(pdf_frontend=False)
