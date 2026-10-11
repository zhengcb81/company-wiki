"""Evidence quality must precede category quota; metadata never invents progress.

Synthetic source groups reproduce the observed 3/5/3 whole-span cost problem,
using public tokenization/finalization instead of hand-built overlap values.
"""
from dataclasses import replace
import re

import pytest

from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_routing import route_document
from integration.test_w04_novelty_finalize import make, SHA, SOURCE

PRODUCT = ("new_product_commercialization_milestone",)
RISK = ("business_risk_or_constraint",)
INDUSTRY = ("current_industry_context",)


def finalize(groups, limit, *, legacy=False, reverse=False):
    candidates = tuple(replace(make(page, paragraph, text, score), reasons=reasons)
        for page, texts, score, reasons in groups
        for paragraph, text in enumerate(texts, 1))
    structure = DocumentStructure(source_id=SOURCE, source_sha256=SHA,
        language="zh", units=tuple(candidate.unit for candidate in candidates),
        page_count=max(g[0] for g in groups), pages_read=max(g[0] for g in groups))
    group_ids = {c.unit.unit_id: f"whole-group-{c.unit.coordinates.page_number}" for c in candidates}
    route = replace(route_document("2025年度报告", existing_kind="annual"), selection_limit=limit)
    result = finalize_selection(structure, route,
        tuple(reversed(candidates)) if reverse else candidates,
        group_ids=group_ids, heading_pattern=re.compile(r"(?!)"),
        dropped_financial_count=0,
        budget_policy="legacy" if legacy else "semantic_coverage/1")
    pages = {span.coordinates.page_number for span in result.evidence_spans}
    assert len(result.evidence_spans) <= limit
    assert result.omitted_candidate_count == result.candidate_count - len(result.evidence_spans)
    for page, texts, _score, _reasons in groups:
        selected = [span for span in result.evidence_spans if span.coordinates.page_number == page]
        assert not selected or len(selected) == len(texts)
    expected = {c.unit.coordinates.locator():c.unit.raw_text for c in candidates}
    assert all(span.raw_text == expected[span.locator] for span in result.evidence_spans)
    return result, pages


def product(page, score=10, cost=2):
    return (page, [f"新型设备型号{page}已完成客户现场验证。"]
        + [f"该设备第{n}项技术范围覆盖关键工艺。" for n in range(1,cost)],
        score, PRODUCT)


def test_realized_progress_can_enter_before_other_low_quality_category_quota_is_full():
    groups = [product(i, score=30-i) for i in range(1,5)]
    groups += [(i, [f"公司第{i}阶段持续完善ESG供应商治理，促进长期可持续合作。",
                   "公司继续推动负责任的业务发展。"], 1, RISK) for i in range(10,16)]
    groups += [(i, [f"行业第{i}阶段继续强化技术支持，促进生态长期合作。",
                   "公司不断提升行业服务价值。"], 1, INDUSTRY) for i in range(20,26)]
    result, pages = finalize(groups, 12)
    assert {1,2,3,4} <= pages
    assert result == finalize(groups, 12, reverse=True)[0]


@pytest.mark.parametrize("alternative", [
    "新型设备预计到2027年完成客户验证。",
    "新型设备计划通过客户验证后交付500台。",
    "新型设备尚未完成客户验证，规划交付500台。",
    "新型设备型号2027的技术特征涵盖500台规模。",
])
def test_same_reason_labels_do_not_turn_planned_negated_or_unproved_text_into_realized(alternative):
    reasons = (*PRODUCT, "quantified_operating_status")
    groups = [(1, ["新型设备已完成客户验证并获得重复订单。"], 1, reasons),
              (2, [alternative], 99, reasons)]
    assert finalize(groups, 1)[1] == {1}


def test_important_concrete_risk_and_quantified_industry_change_share_high_quality_fairness():
    groups = [product(i, score=50-i) for i in range(1,21)]
    groups += [(30, ["关键零部件供应商短缺导致设备交期延长。",
                     "公司采取多厂商策略缓解供应限制。"], 2, ("specific_operating_constraint",)),
               (31, ["行业设备市场需求本期同比增长20%。",
                     "新增客户的工厂采购规模明显扩大。"], 2, ("quantified_industry_change",))]
    assert {30,31} <= finalize(groups, 12)[1]


def test_actual_three_five_three_span_costs_are_not_crowded_out_by_generic_families():
    groups = [product(1, 30, 4), product(2, 29, 5),
              product(3, 28, 3), product(4, 27, 5), product(5, 26, 3)]
    groups += [(i, [f"公司第{i}阶段继续改善ESG沟通。"]*3, 1, RISK) for i in range(10,20)]
    groups += [(i, [f"行业第{i}阶段促进长期生态合作。"]*3, 1, INDUSTRY) for i in range(20,30)]
    # Repeated rows within a group must carry distinct source text, otherwise
    # conservative dedup correctly changes their span cost before budgeting.
    groups = [(page, [f"{text}附属说明{n}。" for n,text in enumerate(texts)], score,reasons)
              for page,texts,score,reasons in groups]
    assert {3,4,5} <= finalize(groups, 24)[1]


def test_same_quality_true_repetition_keeps_room_for_another_realized_fact():
    old = "公司推进工艺支持服务，LPCVD设备已完成客户验证。"
    repeated = "公司推进工艺支持服务，LPCVD 设备已完成客户验证！"
    novel = "医疗设备已获得客户重复订单并交付300台。"
    assert finalize([(1,[old],30,PRODUCT),(2,[repeated],29,PRODUCT),(3,[novel],1,PRODUCT)],2)[1] == {1,3}


def test_semantic_quality_does_not_change_explicit_legacy_replay():
    groups = [product(i, score=20-i) for i in range(1,6)]
    groups += [(20,["行业需求本期同比增长20%。"],1,("quantified_industry_change",))]
    assert finalize(groups, 5, legacy=True)[0] == finalize(groups, 5, legacy=True, reverse=True)[0]


def test_reserved_reason_uses_the_same_quality_order_as_ordinary_offers():
    reasons = ("downstream_business_extension", *PRODUCT, "quantified_operating_status")
    groups = [(1,["新型设备已完成客户验证并获得重复订单。"],1,reasons),
              (2,["新型设备计划到2027年完成客户验证并交付500台。"],99,reasons)]
    assert finalize(groups,1)[1] == {1}
