"""Business-driver proof belongs to the shared assessment, not a finance veto."""
import pytest

from company_wiki.source_catalog import narrative_business_policy as policy
from unit.du11_production.test_source_information_binding import session_for, unit_id, observed_use


@pytest.mark.parametrize('text', (
    '本公司本期催化材料业务收入下降，主要由于下游需求减少。',
    '公司本期检测试剂收入增加，主要原因是客户需求增长。',
    'Our sensor revenue declined due to lower customer demand.',
    'Our reagent revenue grew because downstream demand increased.',
    '公司2025年度影响收入的主要原因为催化材料业务下游需求减少，相关产品收入略低于上年度。',
))
def test_closed_business_demand_cause_is_not_just_an_accounting_result(text):
    session, budget = session_for([text])
    uid = unit_id(0)
    assert observed_use(session, uid)[0] == 'support'
    assert session.source_assertions(uid).independent_payload is True
    assert not session.financial_only(uid)
    before = budget.used
    assert observed_use(session, uid)[0] == 'support'
    assert budget.used == before


@pytest.mark.parametrize('text', (
    '本期营业收入增长12%，净利润增长8%。',
    'Revenue increased due to a change in accounting policy.',
    'Revenue rose due to foreign exchange gains.',
    'Our revenue rose because accounting adjustment demand increased.',
    '公司收入增加，主要由于会计核算需求增长。',
    '公司将努力满足不断变化的客户需求，争取推动收入增长。',
    'We aim to meet growing customer demand and improve revenue.',
))
def test_finance_generic_goal_and_another_assertion_do_not_supply_a_cause(text):
    session, _ = session_for([text])
    assert observed_use(session, unit_id(0))[0] != 'support'


@pytest.mark.parametrize('text', (
    '公司收入下降。另一公司预计未来市场需求增长。',
    'Our revenue declined. The industry expects future demand to increase.',
))
def test_another_assertion_does_not_donate_a_revenue_cause(text):
    session, _ = session_for([text])
    assert 'operating_causal_driver' not in session.fact(unit_id(0)).reasons


def test_actual_demand_is_retained_when_other_sentences_are_financial():
    business = '本公司催化材料业务收入下降，主要由于下游需求减少。'
    accounting = '本期营业收入为20亿元，净利润为1亿元。'
    for text in (business + accounting, accounting + business):
        session, _ = session_for([text])
        assert observed_use(session, unit_id(0))[0] == 'support'


def test_negated_demand_explanation_does_not_become_a_positive_actual_driver():
    text = 'Our revenue decline was not due to lower customer demand.'
    assert not policy._operating_causal_relation(text)


@pytest.mark.parametrize('text', (
    '本公司收入下降，并非因为下游需求减少。',
    '本公司收入增长，并非因为客户需求增加。',
    'Our revenue decline was not because customer demand decreased.',
))
def test_negated_causal_relation_is_not_made_true_by_a_metric_direction(text):
    session, _ = session_for([text])
    assert not policy._operating_causal_relation(text)
    assert 'operating_causal_driver' not in session.fact(unit_id(0)).reasons

