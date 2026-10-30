"""Frozen next-node expectations: actual public reading, no model calls."""
import pytest
from unit.document_understanding_selection.test_reading_structured_qa import _unit, _select

BUSINESS = '本公司已交付27台专用设备至客户进行生产验证。'
RESTRICTION = '该设备尚未完成量产认证，不代表已经形成批量销售。'
FINANCIAL = '公司2025年营业收入为37.17亿元，归属于上市公司股东的净利润为2.84亿元。'
GREETING = '感谢您对公司的关注！'

def case(answers):
    question = _unit('请介绍公司的主要业务与产品进展？', 'investor_question', 0)
    units = [question, *(_unit(text, 'management', i+1) for i, text in enumerate(answers))]
    return units, _select(*units)

def supports(selected):
    texts = {span.span_id: span.raw_text for span in selected.evidence_spans}
    return [{texts[eid] for eid in view['support_evidence_ids']} for group in selected.reading_context['groups']
            for view in group['citation_views'] if view['reading_support_use'] == 'support']

@pytest.mark.parametrize('answers', (
    [BUSINESS, FINANCIAL, GREETING],
    [FINANCIAL, BUSINESS, GREETING],
))
def test_financial_and_thanks_do_not_borrow_business_support_or_prompt_membership(answers):
    units, selected = case(answers)
    assert BUSINESS in {s.raw_text for s in selected.evidence_spans}
    assert {FINANCIAL, GREETING}.isdisjoint(s.raw_text for s in selected.evidence_spans)
    forbidden = {FINANCIAL, GREETING}
    assert supports(selected) and all(not (scope & forbidden) for scope in supports(selected))

def test_later_restriction_cannot_be_detached_to_offer_a_smaller_positive_fact():
    units, selected = case([BUSINESS, RESTRICTION, FINANCIAL])
    for scope in supports(selected):
        if BUSINESS in scope:
            assert RESTRICTION in scope
    assert {BUSINESS, RESTRICTION} <= {s.raw_text for s in selected.evidence_spans}

def test_independent_business_answers_remain_distinct_closed_support_scopes():
    other = '公司已启动电子材料项目建设，项目产能为200吨每年。'
    units, selected = case([BUSINESS, FINANCIAL, other, GREETING])
    scopes = supports(selected)
    assert any(BUSINESS in scope and other not in scope for scope in scopes)
    assert any(other in scope and BUSINESS not in scope for scope in scopes)
    assert all(FINANCIAL not in scope and GREETING not in scope for scope in scopes)
