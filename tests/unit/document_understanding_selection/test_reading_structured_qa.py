"""Source-owned Q&A roles and record boundaries survive the shared engine.

The native JSON fields have no added Q:/A: prefixes. Record association is
provided by the source adapter, not inferred from keyword similarity or order.
"""

from __future__ import annotations

from copy import deepcopy
import pytest

from company_wiki.document_understanding.observation_adapter import build_observation
from company_wiki.document_understanding.structure import build_structure
from company_wiki.source_catalog import narrative_evidence as selector
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


SOURCE_ID = source_id_for_sha256("a" * 64)
OTHER_SOURCE_ID = source_id_for_sha256("b" * 64)
QUESTION = "新产品客户验证和海外订单交付进展如何？"
ANSWER = "公司新产品完成客户验证，第四季度开始批量交付，海外订单持续增长。"


def _unit(text, role, index, *, group="record-1", source_id=SOURCE_ID, original_role=None):
    metadata = {"source_locator": f"native-json:/records/{index}/field"}
    if group is not None:
        metadata.update(qa_group_id=group, official_record_group_id=group)
    if original_role is not None:
        metadata["original_role"] = original_role
    return selector._make_unit(
        source_id=source_id,
        parser_version="0.1.0",
        coordinates=EvidenceCoordinates(paragraph_index=index),
        raw_text=text,
        unit_kind="official_json_field",
        source_role=role,
        language="zh",
        metadata=metadata,
    )


def _observe(*units):
    return build_observation(
        units, source_id=SOURCE_ID, source_sha256="a" * 64,
        title="投资者关系问答", declared_kind="investor_relations",
        mime_type="application/json", language="zh",
    )


def _exchanges(*units):
    result = build_structure(_observe(*units))
    return [item for item in result["semantic_units"] if item["kind"] == "qa_exchange"]


def _select(*units):
    parsed = DocumentStructure(
        SOURCE_ID, "a" * 64, "zh", tuple(units), mime_type="application/json"
    )
    return selector.select_narrative_evidence(
        parsed, title="投资者关系问答", existing_kind="investor_relations",
        max_selected=32, selector_version="0.9.0",
    )


def test_native_roles_without_parser_qa_state_project_speaker_and_record():
    q = _unit(QUESTION, "investor_question", 0)
    a = _unit(ANSWER, "management", 1)
    emitted = _observe(q, a)["units"]
    assert [unit["hints"].get("speaker") for unit in emitted] == ["investor", "management"]
    assert emitted[0]["hints"].get("turn_id")
    assert emitted[0]["hints"]["turn_id"] == emitted[1]["hints"]["turn_id"]


@pytest.mark.parametrize("answer_first", [False, True])
def test_source_record_association_pairs_native_fields_in_either_order(answer_first):
    q = _unit(QUESTION, "investor_question", 0)
    a = _unit(ANSWER, "management", 1)
    units = (a, q) if answer_first else (q, a)
    exchanges = _exchanges(*units)
    assert len(exchanges) == 1
    exchange = exchanges[0]
    assert exchange["completeness"] == "complete"
    assert exchange["member_unit_ids"] == [unit.unit_id for unit in units]
    assert exchange["anchor_unit_ids"] == [a.unit_id]
    assert exchange["required_context_unit_ids"] == [q.unit_id]


def test_shared_production_selection_retains_question_context_and_true_source_refs():
    q = _unit(QUESTION, "investor_question", 0)
    a = _unit(ANSWER, "management", 1)
    package = _select(a, q)
    assert {span.raw_text for span in package.evidence_spans} == {QUESTION, ANSWER}
    assert {span.structured_value["source_role"] for span in package.evidence_spans} == {
        "investor_question", "management"
    }
    assert {span.source_id for span in package.evidence_spans} == {SOURCE_ID}
    groups = package.reading_context["groups"]
    assert len(groups) == 1
    assert set(groups[0]["evidence_ids"]) == {span.span_id for span in package.evidence_spans}


@pytest.mark.parametrize("separate_parent", [False, True])
def test_unfinished_question_cannot_borrow_an_answer_from_another_record_or_parent(separate_parent):
    q = _unit("新产品是否已交付，", "investor_question", 0, group="record-1")
    a = _unit(
        ANSWER, "management", 1,
        group="record-1" if separate_parent else "record-2",
        source_id=OTHER_SOURCE_ID if separate_parent else SOURCE_ID,
    )
    exchanges = _exchanges(q, a)
    assert len(exchanges) == 2
    assert all(exchange["completeness"] == "partial" for exchange in exchanges)
    assert not any(set(exchange["member_unit_ids"]) == {q.unit_id, a.unit_id} for exchange in exchanges)
    assert {diagnostic["code"] for exchange in exchanges for diagnostic in exchange["diagnostics"]} >= {
        "ANSWER_MISSING", "ANSWER_WITHOUT_QUESTION"
    }


def test_actual_management_denial_is_not_reclassified_by_rhetorical_question_words():
    q = _unit("公司是否已经批量交付新产品？", "investor_question", 0)
    a = _unit("是否已经批量交付？目前尚未量产，公司仍在客户验证阶段。", "management", 1)
    exchanges = _exchanges(q, a)
    assert len(exchanges) == 1
    assert exchanges[0]["completeness"] == "complete"
    assert exchanges[0]["anchor_unit_ids"] == [a.unit_id]
    assert exchanges[0]["required_context_unit_ids"] == [q.unit_id]
    assert {span.raw_text for span in _select(q, a).evidence_spans} == {q.raw_text, a.raw_text}


def test_all_question_fragments_are_mandatory_context():
    first = _unit("请介绍新产品客户验证进展，", "investor_question", 0)
    tail = _unit("以及海外订单交付的预计时间？", "investor_question", 1)
    answer = _unit(ANSWER, "management", 2)
    exchanges = _exchanges(first, tail, answer)
    assert len(exchanges) == 1
    assert exchanges[0]["required_context_unit_ids"] == [first.unit_id, tail.unit_id]
    assert exchanges[0]["anchor_unit_ids"] == [answer.unit_id]


@pytest.mark.parametrize("role,original_role,group", [
    ("management", None, None),
    ("company_filing", "company_statement", "record-1"),
])
def test_prepared_statement_does_not_invent_an_exchange_or_absorb_an_open_question(role, original_role, group):
    question = _unit("请介绍新产品验证进展，", "investor_question", 0)
    statement = _unit(ANSWER, role, 1, group=group, original_role=original_role)
    exchanges = _exchanges(question, statement)
    assert len(exchanges) == 1
    assert exchanges[0]["member_unit_ids"] == [question.unit_id]
    assert exchanges[0]["completeness"] == "partial"
    assert not _exchanges(statement)


def test_adapter_keeps_native_text_locators_roles_and_metadata_unchanged():
    units = (_unit(QUESTION, "investor_question", 0), _unit(ANSWER, "management", 1))
    before = [(unit.unit_id, unit.raw_text, dict(unit.metadata)) for unit in units]
    emitted = _observe(*units)["units"]
    assert before == [(unit.unit_id, unit.raw_text, dict(unit.metadata)) for unit in units]
    assert [unit["text"] for unit in emitted] == [unit.raw_text for unit in units]
    assert [unit["locator"] for unit in emitted] == [unit.metadata["source_locator"] for unit in units]
    assert [unit["role"] for unit in emitted] == [unit.source_role for unit in units]
    assert _observe(*units) == deepcopy(_observe(*units))


def test_source_owned_roles_override_quoted_question_or_answer_prefixes():
    question = _unit("答：公司即将量产。请确认该说法是否属实？", "investor_question", 0)
    answer = _unit("问：是否已经量产？公司的回答是尚未量产，仍在客户验证。", "management", 1)
    exchange = _exchanges(question, answer)[0]
    assert exchange["completeness"] == "complete"
    assert exchange["anchor_unit_ids"] == [answer.unit_id]
    assert exchange["required_context_unit_ids"] == [question.unit_id]


def test_marker_based_neutral_source_roles_keep_actual_answer_anchors_and_relation():
    q = _unit("问：新产品客户验证进展如何？", "company_filing", 0, group=None)
    a = _unit("答：公司新产品仍在客户验证，尚未批量交付。", "company_filing", 1, group=None)
    structure = build_structure(_observe(q, a))
    exchange = next(item for item in structure["semantic_units"] if item["kind"] == "qa_exchange")
    assert exchange["anchor_unit_ids"] == [a.unit_id]
    assert exchange["required_context_unit_ids"] == [q.unit_id]
    relation = next(item for item in structure["relations"] if item["kind"] == "question_answer")
    assert relation["from_unit_ids"] == [q.unit_id]
    assert relation["to_unit_ids"] == [a.unit_id]
    assert {span.raw_text for span in _select(q, a).evidence_spans} == {q.raw_text, a.raw_text}


def test_marker_based_exchange_without_record_group_cannot_cross_actual_parents():
    q = _unit("问：请介绍客户验证进展，", "company_filing", 0, group=None)
    a = _unit("答：该公司尚未批量交付。", "company_filing", 1,
              group=None, source_id=OTHER_SOURCE_ID)
    observation = _observe(q, a)
    assert [unit["hints"].get("source_id") for unit in observation["units"]] == [
        SOURCE_ID, OTHER_SOURCE_ID
    ]
    exchanges = _exchanges(q, a)
    assert len(exchanges) == 2
    assert all(exchange["completeness"] == "partial" for exchange in exchanges)
    assert not any(set(exchange["member_unit_ids"]) == {q.unit_id, a.unit_id} for exchange in exchanges)


def test_two_unbound_marker_turns_on_one_parent_remain_separate():
    first_q = _unit("问：请介绍产品客户验证？", "company_filing", 0, group=None)
    first_a = _unit("答：产品仍在客户验证。", "company_filing", 1, group=None)
    second_q = _unit("问：海外业务交付进展如何？", "company_filing", 2, group=None)
    second_a = _unit("答：海外订单尚未交付。", "company_filing", 3, group=None)
    exchanges = _exchanges(first_q, first_a, second_q, second_a)
    assert len(exchanges) == 2
    assert exchanges[0]["member_unit_ids"] == [first_q.unit_id, first_a.unit_id]
    assert exchanges[1]["member_unit_ids"] == [second_q.unit_id, second_a.unit_id]


def test_real_official_export_adapter_keeps_two_actual_parents_and_native_fields(tmp_path):
    from company_wiki.automation.narrative_official_json import (
        open_verified_projection, select_verified_projection,
    )
    from support.official_json_batch_fixture import official_batch_state

    with official_batch_state(tmp_path) as state:
        for subject in state.subjects:
            view = open_verified_projection(
                state.catalog, projection_id=subject.item_key,
                expected_projection_sha256=subject.subject_sha256,
            )
            package = select_verified_projection(
                view, title="Official investor relations Q&A", selector_version="0.9.0"
            )
            assert len(package.evidence_spans) == 4
            assert {span.structured_value["source_role"] for span in package.evidence_spans} == {
                "investor_question", "management"
            }
            assert {span.source_id for span in package.evidence_spans} == {
                parent["source_id"] for parent in subject.parent_source_refs
            }
            expected = {(span.source_id, span.locator, span.raw_text) for span in view.evidence_spans}
            actual = {(span.source_id, span.locator, span.raw_text) for span in package.evidence_spans}
            assert actual == expected
            groups = package.reading_context["groups"]
            assert len(groups) == 2
            by_id = {span.span_id: span for span in package.evidence_spans}
            for group in groups:
                members = [by_id[identifier] for identifier in group["evidence_ids"]]
                assert len(members) == 2
                assert len({span.source_id for span in members}) == 1
                assert {span.structured_value["source_role"] for span in members} == {
                    "investor_question", "management"
                }
