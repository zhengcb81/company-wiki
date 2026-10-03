"""English business milestones survive TXT parsing without broad finance recall."""

from __future__ import annotations

import hashlib

import pytest

from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_VERSION,
    NarrativeParseResult,
    _make_unit,
    parse_transcript_text,
    select_narrative_evidence,
    verify_transcript_evidence_spans,
)
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


BUSINESS = (
    "We entered two new markets and signed pilot agreements with three customers.",
    "We entered two new markets during the quarter.",
    "We signed pilot agreements with three customers.",
    "Our new logistics business began commercial operations in October.",
    "We opened a sales office in Germany to expand our overseas distribution network.",
    "We expanded our distribution network into three overseas markets.",
    "Our distribution business completed its first commercial deployment with a regional retailer.",
    "Three customers completed pilot deployments of our new platform.",
    "We secured multi-year supply agreements with two industrial customers.",
)
NON_BUSINESS = (
    "The board entered the annual meeting and signed the minutes for shareholders.",
    "We signed this meeting policy to improve international investor relations.",
    "This presentation includes forward-looking statements about entering new markets and signing pilot agreements with customers.",
    "We may enter new markets, but actual results could differ materially due to risks and uncertainties.",
    "Actual results may differ materially as we expand into new markets and sign pilot agreements.",
    "These forward-looking statements describe planned new markets and expected pilot agreements.",
    "Forward-looking statements assume we entered two new markets and signed pilot agreements; actual results may differ materially.",
    "Market growth was 12% and profit increased 9% this quarter.",
    "We delivered earnings growth and expanded operating margins during the quarter.",
    "Revenue from international customers increased by 20% while net profit grew 15%.",
    "Growth in overseas markets lifted earnings per share from $1.20 to $1.40.",
    "We entered gains in the accounts and signed financial statement approval documents.",
)


def _select(text):
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    source_id = source_id_for_sha256(digest)
    parsed = parse_transcript_text(
        text, source_id=source_id, source_sha256=digest, language="en"
    )
    package = select_narrative_evidence(
        parsed,
        title="ACME_2026_Q3_earnings_call.txt",
        existing_kind="investor_call_transcript",
    )
    return parsed, package, source_id, digest


@pytest.mark.parametrize("sentence", BUSINESS)
def test_actual_english_business_milestone_is_selected_with_unchanged_text_and_locator(
    tmp_path, sentence
):
    text = f"Full Conference Call Transcript\nCEO: {sentence}\n"
    path = tmp_path / "business.txt"
    path.write_text(text, encoding="utf-8")
    parsed, package, source_id, digest = _select(path.read_text(encoding="utf-8"))
    assert package.candidate_count >= 1
    assert package.evidence_spans
    span = next(span for span in package.evidence_spans if span.raw_text == sentence)
    assert span.structured_value["source_role"] == "management"
    assert "specific_business_event" in span.structured_value["selection_reasons"]
    assert span.coordinates.paragraph_index == 1
    assert span.coordinates.char_start == 0
    assert span.coordinates.char_end == len(sentence)
    assert span.parser_version == NARRATIVE_PARSER_VERSION == "0.1.0"
    assert parsed.coverage_complete
    verified, failed = verify_transcript_evidence_spans(
        text,
        source_id=source_id,
        source_sha256=digest,
        evidence_spans=package.evidence_spans,
    )
    assert verified == tuple(item.span_id for item in package.evidence_spans)
    assert failed == ()


@pytest.mark.parametrize("sentence", NON_BUSINESS)
def test_governance_safe_harbor_and_financial_growth_do_not_become_business_candidates(
    sentence,
):
    _, package, _, _ = _select(f"Full Conference Call Transcript\nCEO: {sentence}\n")
    assert package.coverage_complete
    assert package.candidate_count == 0
    assert package.evidence_spans == ()


def test_english_financial_table_remains_dropped_and_business_milestone_stays_selectable():
    text = BUSINESS[0]
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    source_id = source_id_for_sha256(digest)
    rows = [
        _make_unit(
            source_id=source_id,
            parser_version=NARRATIVE_PARSER_VERSION,
            coordinates=EvidenceCoordinates(
                page_number=1, table_index=0, row_index=index
            ),
            raw_text=label + " | 120.0 | 100.0",
            unit_kind="pdf_table_row",
            source_role="company_filing",
            language="en",
            metadata={
                "row_cells": (label, "120.0", "100.0"),
                "table_headers": ("Income statement", "2026", "2025"),
            },
        )
        for index, label in enumerate(("Revenue", "Net profit", "Earnings per share"))
    ]
    business = _make_unit(
        source_id=source_id,
        parser_version=NARRATIVE_PARSER_VERSION,
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=1),
        raw_text=text,
        unit_kind="pdf_text_block",
        source_role="company_filing",
        language="en",
        metadata={},
    )
    parsed = NarrativeParseResult(
        source_id=source_id,
        source_sha256=digest,
        language="en",
        units=tuple(rows) + (business,),
        page_count=1,
        pages_read=1,
    )
    package = select_narrative_evidence(
        parsed, title="ACME annual report.pdf", existing_kind="annual_report"
    )
    assert package.dropped_financial_count == 3
    assert len(package.evidence_spans) == 1
    assert package.evidence_spans[0].raw_text == text
    assert package.evidence_spans[0].coordinates.page_number == 1


def test_recall_semantics_are_versioned_without_changing_source_parser():
    assert NARRATIVE_SELECTOR_VERSION == "0.2.0"
    assert NARRATIVE_PARSER_VERSION == "0.1.0"
