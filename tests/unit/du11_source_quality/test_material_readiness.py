"""Source observations, rather than model prose, determine usable support."""
from copy import deepcopy
from hashlib import sha256

import pymupdf as fitz
import pytest

from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model_extractive import compile_extractive_plan
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
from company_wiki.source_catalog.narrative_reading import select_reading_evidence
from company_wiki.source_contract import source_id_for_sha256
from unit.document_understanding_selection.test_reading_native_continuity import native, run
from unit.test_narrative_extractive_runtime import selected


def test_singleton_native_material_is_unassessed_not_a_fabricated_closed_window():
    result = run([native("Our platform received customer orders but remains subject to", 0)])
    # Completeness describes bounded physical analysis, not semantic closure.
    # The source-readiness owner must assess dangling qualifiers separately.
    assert result["complete"]
    assert result["semantic_status"] == "not_evaluated"
    assert result["standalone_unit_count"] == 1
    assert not result["windows"]


def test_observed_mid_block_prefix_without_its_predecessor_is_not_a_closed_statement():
    result = run([native("omers received the new platform.", 0, start=38)])
    assert not result["complete"]
    assert result["deferred_unit_ids"] == ["source-a:0"]


def test_closed_native_singleton_is_still_available_to_the_source_reader():
    result = run([native("Our customers received the new platform.", 0)])
    assert result["complete"]
    assert not result["deferred_unit_ids"]


def test_source_table_ambiguity_is_not_promoted_to_a_canonical_summary_card():
    wire = selected(2).to_dict()
    wire["evidence_spans"][0]["quality_flags"] = ["table_structure_ambiguous"]
    source = NarrativeSelectResult.from_dict(wire)
    before = deepcopy(source.to_dict())
    plan = compile_extractive_plan(source)
    assert [row["claim_id"] for row in plan.draft["claims"]] == ["t2-source"]
    first = plan.execution["tasks"][0]
    assert first["source_disposition"] == "unsupported"
    assert first["reason"] == "source_table_unresolved"
    assert source.to_dict() == before  # Queryable originals and evidence remain.


@pytest.mark.parametrize("kind,expected", [("operating_table", "unsupported"),
                                           ("paragraph_event", "admitted")])
def test_table_header_ambiguity_is_used_by_its_table_not_unrelated_prose(kind, expected):
    wire = selected(2).to_dict()
    first, second = (span['span_id'] for span in wire['evidence_spans'])
    wire['evidence_spans'][0]['quality_flags'] = ['table_structure_ambiguous']
    wire['reading_context'].update(schema_version='du-production-reading/2', groups=[{
        'group_id': 'observed-table', 'kind': kind, 'section_role': 'operating_metrics',
        'evidence_ids': [first, second], 'citation_views': [{
            'support_evidence_ids': [second], 'context_evidence_ids': [first]}]}])
    plan = compile_extractive_plan(NarrativeSelectResult.from_dict(wire))
    assert plan.execution['tasks'][0]['source_disposition'] == expected


def test_production_keeps_heading_as_context_and_carries_source_priority():
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((60, 90), "Item 1. Business", fontsize=18)
        page.insert_text((60, 140), "We launched a new software platform for enterprise customers.", fontsize=12)
        data = document.tobytes()
    digest = sha256(data).hexdigest()
    parsed = parse_pdf_bytes(data, source_id=source_id_for_sha256(digest), source_sha256=digest,
                             language="en", selector_version="0.9.0")
    package = select_reading_evidence(parsed, title="Annual Report", existing_kind="annual_report")
    assert package.evidence_spans
    spans = {span.span_id: span for span in package.evidence_spans}
    body = [span for span in spans.values() if "launched" in span.raw_text]
    assert body
    for span in body:
        assert type(span.structured_value["reading_priority"]) is int
        assert span.structured_value["reading_value_band"] == "meaningful_fact"
        assert span.structured_value["reading_score"] > 0
    for group in package.reading_context["groups"]:
        for view in group["citation_views"]:
            assert all("Item 1. Business" not in spans[sid].raw_text
                       for sid in view["support_evidence_ids"])
