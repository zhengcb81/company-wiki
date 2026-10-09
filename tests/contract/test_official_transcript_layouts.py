"""W05 natural issuer call layouts retain speaker, QA and exact byte lineage."""

from __future__ import annotations
import hashlib
import pytest
from company_wiki.source_catalog.transcript_text_extract import (
    extract_transcript_material,
)
from company_wiki.source_catalog.narrative_evidence import (
    parse_transcript_text,
    select_narrative_evidence,
    verify_transcript_evidence_spans,
)


def parse(html):
    original = html.encode("utf-8")
    m = extract_transcript_material(original, mime_type="text/html")
    m.verify(original)
    d = parse_transcript_text(
        m.text_utf8, source_id=m.original_source_id, source_sha256=m.original_sha256
    )
    return original, m, d


def test_actual_issuer_natural_heading_colon_speakers_end_and_qa():
    original, m, d = parse(
        "<html><head><title>Acme Fiscal Year Fourth Quarter Earnings Conference Call</title></head><body><nav>Transcript</nav><h2>Transcript</h2><p>Acme FY Fourth Quarter Earnings Conference Call</p><p>JANE DOE:</p><p>We launched a new product and expanded overseas capacity.</p><p>JANE DOE: We will now move over to Q&amp;A.</p><p>ANALYST NAME:</p><p>When will the new product complete customer validation?</p><p>JANE DOE:</p><p>Customer validation is planned next year, not completed.</p><p>END</p><footer><p>We launched a new retail website.</p></footer></body></html>"
    )
    assert not d.errors and d.coverage_complete
    assert all("retail website" not in u.raw_text for u in d.units)
    assert any(u.source_role == "analyst" for u in d.units)
    assert any(
        u.source_role == "management" and u.metadata["section"] == "qa" for u in d.units
    )
    p = select_narrative_evidence(
        d, title="Acme earnings call", existing_kind="investor_call_transcript"
    )
    assert p.evidence_spans and any(
        "not completed" in s.raw_text for s in p.evidence_spans
    )
    verified, failed = verify_transcript_evidence_spans(
        m.text_utf8,
        source_id=m.original_source_id,
        source_sha256=m.original_sha256,
        evidence_spans=p.evidence_spans,
    )
    assert len(verified) == len(p.evidence_spans) and not failed
    assert hashlib.sha256(original).hexdigest() == m.original_sha256
    for u in d.units:
        assert all(
            0 <= x.source_byte_start < x.source_byte_end <= len(original)
            for x in m.lines[u.metadata["line_start"] - 1 : u.metadata["line_end"]]
        )


def test_second_layout_titled_speaker_labels_and_question_and_answer_heading():
    _, _, d = parse(
        "<html><body><h1>Q2 2026 Earnings Call Transcript</h1><p>Jane Doe -- Chief Executive Officer</p><p>We expanded production capacity overseas for a new product.</p><h2>Question and Answer Session</h2><p>Alex Smith -- Research Analyst</p><p>Is the new product entering customer trials?</p><p>Jane Doe -- Chief Executive Officer</p><p>Trials remain planned and have not commenced.</p><p>This concludes today’s conference call. You may disconnect.</p><p>Unrelated footer business expansion.</p></body></html>"
    )
    assert not d.errors
    assert any(
        u.source_role == "analyst" and u.metadata["section"] == "qa" for u in d.units
    )
    assert all("Unrelated footer" not in u.raw_text for u in d.units)
    q = next(u for u in d.units if u.source_role == "analyst")
    a = next(u for u in d.units if "not commenced" in u.raw_text)
    assert q.metadata["qa_group_id"] == a.metadata["qa_group_id"]


@pytest.mark.parametrize(
    "body",
    [
        "<title>Transcript</title><nav>Transcript</nav><p>Our products expand overseas.</p>",
        "<h1>Earnings Call Transcript</h1><p>Contact: Investor Relations</p><p>Download: PDF</p>",
        "<h2>Transcript</h2><p>Revenue: Our new products grew strongly.</p>",
    ],
)
def test_navigation_or_metrics_without_true_speaker_body_are_rejected(body):
    _, _, d = parse("<html><body>" + body + "</body></html>")
    assert d.errors and not d.units


def test_ambiguous_empty_heading_body_is_not_success():
    _, _, d = parse("<h1>Full Conference Call Transcript</h1><p>Download document</p>")
    assert d.errors and not d.units


def test_call_page_title_cannot_promote_trace_id_or_navigation_to_a_speaker():
    _, _, d = parse(
        "<html><head><title>Acme Fourth Quarter Earnings Conference Call</title></head><body><p>This is the Trace Id: abc</p><p>Our products and services</p><nav>Cloud products</nav><h2>Transcript</h2><p>Acme Fourth Quarter Earnings Conference Call</p><p>JANE DOE:</p><p>We launched a new product overseas and expanded production.</p><p>ALEX SMITH:</p><p>Has customer certification actually completed?</p><p>END</p></body></html>"
    )
    assert d.units and min(u.metadata["line_start"] for u in d.units) >= 6
    assert all(
        "Trace" not in str(u.metadata.get("speaker"))
        and "products and services" not in u.raw_text
        for u in d.units
    )


def test_natural_heading_incomplete_call_retains_named_coverage_failure():
    _, _, d = parse(
        "<h1>Acme Q2 Earnings Call Transcript</h1><p>Jane Doe -- CEO</p><p>We launched new products and expanded overseas supply.</p><p>Alex Smith -- Analyst</p><p>Has customer certification completed?</p>"
    )
    assert (
        d.units and d.errors == ("transcript_end_missing",) and not d.coverage_complete
    )


def test_legacy_version_replays_original_heading_layout_and_new_identity_is_separate():
    from company_wiki.automation.narrative_formats import parser_component

    original, m, _ = parse(
        "<h1>Full Conference Call Transcript</h1><p>CEO: We launched a new product and expanded overseas capacity.</p>"
    )
    old = parse_transcript_text(
        m.text_utf8,
        source_id=m.original_source_id,
        source_sha256=m.original_sha256,
        parser_version="0.1.1",
    )
    new = parse_transcript_text(
        m.text_utf8, source_id=m.original_source_id, source_sha256=m.original_sha256
    )
    assert old.units[0].raw_text == new.units[0].raw_text
    assert old.units[0].unit_id != new.units[0].unit_id
    old_spans = select_narrative_evidence(
        old, title="earnings call", existing_kind="investor_call_transcript"
    ).evidence_spans
    verified, failed = verify_transcript_evidence_spans(
        m.text_utf8,
        source_id=m.original_source_id,
        source_sha256=m.original_sha256,
        evidence_spans=old_spans,
    )
    assert len(verified) == len(old_spans) and not failed
    assert parser_component("text/html", "transcript") == (
        "selective_narrative_parser",
        "0.2.0",
    )
    assert parser_component("text/html", "transcript", parser_version="0.1.1") == (
        "selective_narrative_parser",
        "0.1.1",
    )
    assert parser_component("application/pdf") == (
        "selective_narrative_parser",
        "0.1.1",
    )


def test_closing_courtesy_before_operator_direction_remains_last_actual_speaker():
    _, _, d = parse(
        "<h2>Transcript</h2><p>Acme Q2 Earnings Call</p><p>JANE DOE:</p><p>We launched new products and expanded overseas capacity.</p><p>AMY ROE:</p><p>Thank you.</p><p>(Operator Direction.)</p><p>END</p><footer>More businesses</footer>"
    )
    assert any(
        u.raw_text.startswith("Thank you.") and u.metadata["speaker"] == "AMY ROE"
        for u in d.units
    )
    assert all(u.metadata["speaker"] != "Thank you." for u in d.units)
