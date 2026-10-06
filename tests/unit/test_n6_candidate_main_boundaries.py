"""MAIN contract counterexamples for candidate completion and rule injection."""

from dataclasses import replace

import pytest

from company_wiki.source_catalog.n6_candidate_completion import completion_indices
from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_evidence import _make_unit, _minimal_matching_unit_windows
from company_wiki.source_catalog.narrative_group_candidates import GroupCandidateRules, enrich_context_groups
from company_wiki.source_catalog.narrative_neighbors import NeighborRules, enrich_neighbor_context
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def unit(index, text="句子的片段，", *, metadata=None, digest="a", role="management", language="zh"):
    return _make_unit(
        source_id=source_id_for_sha256(digest * 64), parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
        raw_text=text, unit_kind="pdf_text_block", source_role=role,
        language=language, metadata=metadata or {},
    )


def test_completion_never_exceeds_eight_members_when_hit_is_near_the_end():
    members = tuple(unit(index) for index in range(12))
    chosen = completion_indices(members, 7, barrier=lambda _: False)
    assert 7 in chosen
    assert len(chosen) <= 8


def test_finished_english_sentence_is_a_completion_boundary():
    members = (unit(0, "Unrelated previous event.", language="en"),
               unit(1, "Company deployed the new product.", language="en"),
               unit(2, "Another unrelated event.", language="en"))
    assert completion_indices(members, 1, barrier=lambda _: False) == (1,)


@pytest.mark.parametrize("name", ["qa_group_id", "qa_parent_id", "speaker", "section"])
def test_completion_cannot_borrow_context_from_another_question_or_speaker(name):
    members = (unit(0, metadata={name: "left"}), unit(1, metadata={name: "right"}))
    assert completion_indices(members, 1, barrier=lambda _: False) == (1,)


def test_fact_window_obeys_the_injected_detector():
    members = (unit(0, "公司拟收购一家拥有新技术的企业。"),)
    group = ("g", members, members[0].raw_text)
    rules = GroupCandidateRules(window_finder=_minimal_matching_unit_windows,
                                operating_facts=lambda _: OperatingFact())
    result = enrich_context_groups((group,), initial_candidates=(), initial_group_ids={},
                                   project_scores={}, business_scores={}, rules=rules)
    assert result.candidates == ()


@pytest.mark.parametrize("options", [{"digest": "b"}, {"language": "en"}])
def test_linked_question_must_belong_to_the_answer_source_and_language(options):
    answer = unit(0, "公司新产品已进入客户产线。", metadata={"qa_group_id": "qa1"})
    question = unit(1, "请问新产品何时投入使用？", role="investor_question",
                    metadata={"qa_group_id": "qa1"}, **options)
    candidate = EvidenceCandidate(answer, ("core_business",), ("specific_business_event",), 6)
    result = enrich_neighbor_context((answer, question), initial_candidates=(candidate,),
                                     initial_group_ids={}, rules=NeighborRules())
    assert result.candidates == (candidate,)


def test_completion_preserves_all_members_of_a_valid_fragmented_sentence():
    members = (unit(0, "公司新产品"), unit(1, "已进入客户产线，"), unit(2, "尚未量产。"))
    assert completion_indices(members, 1, barrier=lambda _: False) == (0, 1, 2)


def test_injected_fact_detection_can_select_a_group_without_global_patterns():
    members = (unit(0, "Alpha is in phase one,"), unit(1, "with the next phase still planned."))
    calls = []

    def detector(text):
        calls.append(text)
        return OperatingFact(eligible=True, topics=("new_business",),
                             reasons=("project_plan_or_status",), score=3)

    rules = replace(GroupCandidateRules(), operating_facts=detector,
                    window_finder=lambda _members, _pattern: ((0, 1),))
    result = enrich_context_groups((("g", members, "".join(m.raw_text for m in members)),),
                                   initial_candidates=(), initial_group_ids={},
                                   project_scores={}, business_scores={}, rules=rules)
    assert len(result.candidates) == 2
    assert len(set(result.group_ids.values())) == 1
    assert calls


def test_quantified_operating_fact_competes_as_business_evidence_not_unclassified_noise():
    from company_wiki.source_catalog.narrative_budget import BudgetItem, select_budget_items

    def item(name, reason, score):
        return BudgetItem(item_id=name, group_id=None, page_key=('page', 1),
                          locator='page:1', order_key=(1,), reasons=(reason,),
                          score=score, is_heading=False, payload=name)

    choices = (item('capacity-utilization', 'quantified_operating_status', 4),
               item('broad-industry-background', 'current_industry_context', 50))
    chosen = select_budget_items(choices, limit=1)
    assert [entry.payload for entry in chosen] == ['capacity-utilization']


def test_a_second_category_on_a_busy_page_is_offered_before_the_budget_fills():
    from company_wiki.source_catalog.narrative_budget import BudgetItem, select_budget_items

    def item(name, page, reason, score=10):
        return BudgetItem(item_id=name, group_id=None, page_key=('page', page),
                          locator=f'loc:v1/page:{page}', order_key=(page,),
                          reasons=(reason,), score=score, is_heading=False, payload=name)

    choices = (item('capacity', 1, 'direct_capacity_constraint'),
               item('industry', 1, 'current_industry_context'),
               *(item(f'risk-{p}', p, 'business_risk_or_constraint', 40) for p in range(2, 10)))
    selected = select_budget_items(choices, limit=6)
    assert {'capacity', 'industry'} <= {i.payload for i in selected}
    assert len(selected) == 6


def test_customer_validation_milestone_survives_a_dense_generic_event_document():
    from company_wiki.source_catalog.narrative_evidence import NarrativeParseResult, select_narrative_evidence

    milestone = unit(0, '公司X7设备已进入客户端量产验证阶段。')
    from company_wiki.source_catalog.narrative_candidates import assess_unit
    from company_wiki.source_catalog.narrative_evidence import _candidate_rules

    candidate = assess_unit(milestone, _candidate_rules()).candidate
    assert candidate is not None
    assert 'new_product_commercialization_milestone' in candidate.reasons
    other = tuple(replace(unit(i + 1, f'公司推进第{i}项设备生产项目建设，持续完善配套设施。'),
                          coordinates=EvidenceCoordinates(page_number=i + 2, paragraph_index=0))
                  for i in range(110))
    parsed = NarrativeParseResult(source_id=milestone.source_id, source_sha256='a' * 64, language='zh',
                                  units=(milestone, *other), page_count=111, pages_read=111)
    result = select_narrative_evidence(parsed, title='2026年年度报告', existing_kind='annual_report')
    assert any(span.raw_text == milestone.raw_text for span in result.evidence_spans)
    assert len(result.evidence_spans) <= 96


def test_completion_reasons_do_not_leak_from_an_unrelated_sentence_on_the_page():
    import re

    product = unit(0, '公司新产品已进入客户端量产验证阶段。')
    prefix = unit(1, '公司继续稳健发展，')
    suffix = unit(2, '进一步完善日常经营流程。')
    candidates = (EvidenceCandidate(product, ('products_rd',), ('new_product_commercialization_milestone',), 8),
                  EvidenceCandidate(suffix, ('core_business',), ('specific_business_event',), 3))
    rules = GroupCandidateRules(new_product_milestone=re.compile('新产品.*验证'),
                                operating_facts=lambda _: OperatingFact())
    members = (product, prefix, suffix)
    result = enrich_context_groups((('page', members, ''.join(m.raw_text for m in members)),),
                                   initial_candidates=candidates, initial_group_ids={},
                                   project_scores={}, business_scores={}, rules=rules)
    added = next(c for c in result.candidates if c.unit.unit_id == prefix.unit_id)
    assert 'new_product_commercialization_milestone' not in added.reasons
    assert result.group_ids[prefix.unit_id] == result.group_ids[suffix.unit_id]
    assert result.group_ids[product.unit_id] != result.group_ids[suffix.unit_id]


def test_existing_fact_candidate_keeps_all_injected_window_reasons():
    body = unit(0, '项目已开工，预计次年建成投产。')
    initial = EvidenceCandidate(body, ('capacity_projects',), ('specific_business_event',), 5)
    fact = OperatingFact(eligible=True, topics=('capacity_projects',),
                         reasons=('specific_business_event', 'project_execution_timeline'), score=4)
    rules = GroupCandidateRules(window_finder=lambda _members, _pattern: ((0, 0),),
                                operating_facts=lambda _: fact)
    result = enrich_context_groups((('page', (body,), body.raw_text),),
                                   initial_candidates=(initial,), initial_group_ids={},
                                   project_scores={}, business_scores={}, rules=rules)
    assert 'project_execution_timeline' in result.candidates[0].reasons


def test_started_project_with_a_future_completion_date_is_a_concrete_timeline():
    from company_wiki.source_catalog.n6_candidate_operating_facts import detect_operating_fact

    fact = detect_operating_fact('2025年9月开工建设的一期项目占地约50亩，预计2026年年底建成，2027年投产。')
    assert fact.eligible
    assert 'project_execution_timeline' in fact.reasons
