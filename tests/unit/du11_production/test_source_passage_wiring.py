"""The shared closed-source capability reaches real cards without a second veto."""
import pytest

from unit.du11_production.test_qa_closed_scopes import case, admitted_cards, FINANCIAL, GREETING


@pytest.mark.parametrize('text', [
    '北岭子公司拥有两座水电站及一家保险业务。',
    'Northvale owns an insurer and two electricity utilities.',
    '第二期项目预计2028年投产，实际进度取决于客户订单及审批。',
    'The second phase is expected to start production in 2028, subject to customer orders and permits.',
    '品牌客户正在去库存，对各品牌订单影响不同。',
    '营业毛利变化主要由于品牌客户正在调整产品组合。',
])
def test_actual_source_card_keeps_unknown_operating_descriptions_and_conditions(text):
    _, selected = case([text, FINANCIAL, GREETING])
    cards = admitted_cards(selected)
    assert any(text in members for _, members in cards)
    assert all(FINANCIAL not in members and GREETING not in members for _, members in cards)
    assert text in {s.raw_text for s in selected.evidence_spans}


def test_question_business_words_cannot_donate_a_passage_capability_to_a_financial_answer():
    _, selected = case([FINANCIAL, GREETING])
    assert not admitted_cards(selected)
