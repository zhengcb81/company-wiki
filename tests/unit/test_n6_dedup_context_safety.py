"""MAIN adversarial cases: identical text does not prove identical context."""

import pytest

from company_wiki.source_catalog.n6_budget_dedup import deduplicate_candidates
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_budget import BudgetItem, select_budget_items
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def candidate(page, *, text="We expect to launch next year.", role="management",
              language="en", digest="a", metadata=None):
    unit = _make_unit(
        source_id=source_id_for_sha256(digest * 64), parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=0),
        raw_text=text, unit_kind="pdf_text_block", source_role=role,
        language=language, metadata=metadata or {},
    )
    return EvidenceCandidate(unit, ("business_progress",), ("specific_business_event",), 6)


@pytest.mark.parametrize("left_options,right_options", [
    ({}, {"digest": "b"}),
    ({}, {"language": "zh"}),
    ({"metadata": {"qa_group_id": "product-a"}}, {"metadata": {"qa_group_id": "product-b"}}),
    ({"metadata": {"qa_parent_id": "q1"}}, {"metadata": {"qa_parent_id": "q2"}}),
    ({"metadata": {"speaker": "CEO"}}, {"metadata": {"speaker": "CFO"}}),
    ({"metadata": {"section": "qa"}}, {"metadata": {"section": "prepared_remarks"}}),
    ({"metadata": {"table_headers": ["2025"]}}, {"metadata": {"table_headers": ["2024"]}}),
])
def test_same_text_in_distinct_contexts_keeps_both(left_options, right_options):
    left, right = candidate(1, **left_options), candidate(2, **right_options)
    result = deduplicate_candidates((left, right), {})
    assert {item.unit.unit_id for item in result.candidates} == {left.unit.unit_id, right.unit.unit_id}
    assert not result.drops


@pytest.mark.parametrize("right_options", [
    {"role": "unknown"}, {"role": "company_filing"}, {"digest": "b"},
    {"language": "zh"}, {"metadata": {"qa_parent_id": "other-question"}},
])
def test_summary_group_cannot_mix_contexts(right_options):
    left, right = candidate(1), candidate(2, text="Another business statement.", **right_options)
    groups = {left.unit.unit_id: "input", right.unit.unit_id: "input"}
    result = deduplicate_candidates((left, right), groups)
    assert len(result.candidates) == 2
    assert len(set(result.group_ids.values())) == 2


def test_reversed_event_sequence_is_not_the_same_event():
    a, b = candidate(1, text="First phase."), candidate(2, text="Second phase.")
    c, d = candidate(3, text="Second phase."), candidate(4, text="First phase.")
    groups = {a.unit.unit_id: "a", b.unit.unit_id: "a", c.unit.unit_id: "b", d.unit.unit_id: "b"}
    result = deduplicate_candidates((a, b, c, d), groups)
    assert len(result.candidates) == 4
    assert not result.drops


def test_generated_group_id_cannot_alias_an_existing_input_group():
    a, b = candidate(1), candidate(2, text="Question?", role="investor_question")
    c = candidate(3, text="Unrelated event.")
    groups = {a.unit.unit_id: "input", b.unit.unit_id: "input", c.unit.unit_id: "input:statement"}
    result = deduplicate_candidates((a, b, c), groups)
    assert len(set(result.group_ids.values())) == 3


def test_ungrouped_budget_item_cannot_alias_an_event_group():
    def item(identifier, group, score):
        return BudgetItem(identifier, group, ("page", 1), "loc:v1/page:1/paragraph:0",
                          (1, 0), ("specific_business_event",), score, False, identifier)
    items = (item("x", None, 0), item("y", "item:x", 100), item("z", None, 90))
    selected = select_budget_items(items, limit=2)
    assert {entry.item_id for entry in selected} == {"y", "z"}
