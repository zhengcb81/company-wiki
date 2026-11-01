"""Quote readability is not a proof of an issuer operating event."""
from copy import deepcopy

import pytest

from company_wiki.source_catalog.narrative_support_use import (
    source_narrative_relevance, source_support_use,
)
from unit.du11_production.test_source_information_binding import session_for, unit_id


def assessed(text):
    session, budget = session_for([text])
    uid = unit_id(0)
    fact = session.fact(uid)
    return session, budget, uid, fact, session.source_passage(uid)


@pytest.mark.parametrize('text', (
    'Northvale owns an insurer and two electricity utilities.',
    '北岭子公司拥有两座水电站及一家保险业务。',
    'Northvale increased its share from 4.2% to 4.7% and ranked third.',
    '北岭水电的装机容量从40兆瓦增加到85兆瓦。',
    'Northvale wind capacity was 40 megawatts at acquisition and is now 85 megawatts.',
    '第二期项目预计2028年投产，实际进度取决于订单及审批。',
    'The second phase is expected to start production in 2028, subject to orders and permits.',
    '品牌客户正在去库存，对各品牌订单影响不同。',
    'Customers are reducing inventories, affecting orders differently across brands.',
    '公司的主要品牌都会有专属的工厂，大多数工厂只为一个品牌服务。',
))
def test_unknown_entities_structures_plans_and_industry_scopes_are_readable(text):
    session, budget, uid, fact, passage = assessed(text)
    assert passage.use == 'support', (text, passage)
    assert passage.relevant
    roles = session.source_assertions(uid)
    assert source_support_use(text, fact=fact, financial_only=session.financial_only(uid),
                              source_roles=roles, passage=passage)[0] == 'support'
    assert source_narrative_relevance(fact=fact, source_roles=roles, passage=passage)
    used = budget.used
    assert session.source_passage(uid) is passage
    assert budget.used == used


@pytest.mark.parametrize('text', (
    'Revenue was $100 million and net income was $20 million.',
    '营业收入100万元，净利润20万元。',
    'Total assets 100 200 300; total liabilities 20 30 40.',
    '2025 2026 100 200 300',
    'We will strive to create more value for our shareholders.',
    '公司将继续努力，为股东创造更大价值。',
    'Our software supports customer engagement.',
    'Our platform supports outstanding goals.',
    'Our platform supports outstanding services.',
    'Company provides best-in-class products.',
    '我们的平台支持宏伟愿景。',
    '公司未来将开发更多产品促进高质量发展。',
    'What is the capacity of the second phase?',
    '请问公司第二期产能预计是多少？',
    'Template: Northvale owns two power stations.',
    '模板示例：北岭子公司拥有两座水电站。',
    'The procedure states that the applicant received review questions.',
    'We recognize depreciation according to accounting standards.',
    '本公司按照会计准则计提折旧。',
    'Equipment manufacturing companies in Europe.',
    '显示器件制造企业',
    '主要产品：设备、传感器及材料',
    'Thank you for your question.',
    '9 Example Holdings Limited',
    'For the six months ended June 30',
    'All amounts in thousands except per share data',
    'Product names appear in the glossary. Production.',
    'Software is mentioned in the glossary. Supports.',
    'The glossary contains product names.',
    'The other matters are still being examined.',
    '单位为人民币千元。',
))
def test_pure_financial_rules_templates_questions_and_objectives_are_not_support(text):
    session, _, uid, fact, passage = assessed(text)
    assert passage.use != 'support', (text, passage)
    assert not source_narrative_relevance(fact=fact, source_roles=session.source_assertions(uid),
                                         passage=passage)


@pytest.mark.parametrize('text', (
    'Gross margin declined because orders shifted to a different product mix.',
    '毛利率下降主要由于订单转向不同的产品组合。',
    'Northvale owns two electricity utilities. Net income was $20 million.',
    '北岭子公司拥有两座水电站。净利润20万元。',
))
def test_mixed_narrative_and_financial_context_preserves_readable_original_scope(text):
    session, _, uid, fact, passage = assessed(text)
    assert passage.use == 'support'
    assert session.source_text(uid) == text
    assert source_support_use(text, fact=fact, financial_only=session.financial_only(uid),
                              source_roles=session.source_assertions(uid), passage=passage)[0] == 'support'


def test_financial_cause_does_not_turn_a_pure_accounting_result_into_business_quote():
    _, _, _, _, passage = assessed('Net income declined because income tax expense increased.')
    assert passage.use != 'support'


def test_readability_never_changes_event_or_attribution_proof():
    from company_wiki.source_catalog.narrative_business_policy import (
        prepare_reading_business_assessment, project_reading_business_fact,
    )
    text = 'Northvale owns an insurer and two electricity utilities.'
    old = project_reading_business_fact(text, {'relations': []})
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    frozen = deepcopy(prepared.fact)
    assert prepared.fact == old
    assert prepared.passage.use == 'support'
    assert prepared.source_roles.independent_payload is None
    assert not prepared.source_roles.bound_operating
    assert prepared.fact == frozen


def test_table_and_question_roles_remain_owner_controlled():
    session, _, uid, fact, passage = assessed('Northvale owns an insurer and two utilities.')
    assert source_support_use(session.source_text(uid), fact=fact,
        financial_only=session.financial_only(uid), passage=passage, context_role=True)[0] == 'context_only'


def test_budget_stop_cannot_restart_a_text_scan_or_claim_no_content():
    session, budget = session_for(['Northvale owns two utilities.'])
    budget.charge(budget.max_work_units)
    assert session.source_passage(unit_id(0)) is None
    assert not session.complete


def test_account_cause_after_a_valid_clause_does_not_erase_prior_readability():
    text = 'Northvale owns two utilities. Net income declined because of miscellaneous items.'
    _, _, _, _, passage = assessed(text)
    assert passage.use == 'support'


def test_generic_objective_after_specific_narrative_cannot_erase_prior_scope():
    _, _, _, _, passage = assessed(
        'Northvale owns two utilities. We strive to create value for shareholders.')
    assert passage.use == 'support'


def test_explicit_scope_numeric_uncertainty_remains_unresolved_but_readable():
    text = 'Northvale owns two utilities.'
    session, _, uid, fact, passage = assessed(text)
    assert passage.use == 'support'
    assert source_support_use(text, fact=fact, financial_only=False,
        source_roles=session.source_assertions(uid), passage=passage,
        numeric_ambiguous=True) == ('unresolved', 'source_numeric_scope_unresolved')
    assert source_narrative_relevance(fact=fact, source_roles=session.source_assertions(uid),
                                      passage=passage)


@pytest.mark.parametrize('text', (
    '問題：第二期项目预计2028年投产。',
    'Question: Northvale owns two utilities.',
    'Q: Northvale owns two utilities.',
))
def test_shared_explicit_question_markers_never_become_passage_support(text):
    _, _, _, _, passage = assessed(text)
    assert passage.use != 'support'


@pytest.mark.parametrize('text', (
    '截至报告期末，研发人员达1,237人。',
    'We provide option-pricing software to banks.',
    '公司向银行提供公允价值计量软件。',
    '公司抗体药物产线新增年产能10,000批。',
    'Capacity utilization\n80\n75',
))
def test_established_support_or_relevant_uncertainty_is_monotonic(text):
    session, _, uid, fact, passage = assessed(text)
    roles = session.source_assertions(uid)
    old = source_support_use(text, fact=fact, financial_only=session.financial_only(uid),
                             source_roles=roles)
    old_relevant = source_narrative_relevance(fact=fact, source_roles=roles)
    if old[0] == 'support':
        assert passage.use == 'support' and passage.relevant
    elif old[0] == 'unresolved' and old_relevant:
        assert passage.use == 'unresolved' and passage.relevant
    else:
        pytest.fail('fixture does not exercise established support/uncertainty')


@pytest.mark.parametrize('text', (
    'However, our software processes customer orders.',
    'Whereas our software processes customer orders, our equipment sterilises tools.',
    'Whenever orders arrive, our software processes the transaction records.',
))
def test_discourse_connectors_are_not_questions_by_prefix(text):
    session, _, uid, fact, passage = assessed(text)
    old = source_support_use(text, fact=fact, financial_only=session.financial_only(uid),
        source_roles=session.source_assertions(uid))
    assert old[0] == 'support'
    assert passage.use == 'support' and passage.relevant


@pytest.mark.parametrize('text', (
    'How will the software process orders?',
    'Where will the plant be located?',
    'When is production expected to begin?',
))
def test_real_wh_questions_remain_context(text):
    _, _, _, _, passage = assessed(text)
    assert passage.use != 'support' and not passage.relevant


@pytest.mark.parametrize('text', (
    'Accounting rules required firms to value securities at market instead of cost. '
    'Results before 1980 have been restated to conform to the rules.',
    'All per-share figures in this report apply to Class A shares. '
    'Figures for Class B shares are one twentieth of those shown.',
    'Here are some key figures on the subsidiary operations:',
    '以下为子公司经营数据：',
))
def test_reporting_governors_basis_and_table_introductions_are_context(text):
    from company_wiki.source_catalog.narrative_source_purpose import NON_OPERATING_PURPOSES
    session, _, uid, fact, passage = assessed(text)
    assert fact.purpose in NON_OPERATING_PURPOSES
    assert passage.use == 'context_only' and not passage.relevant
    assert session.source_text(uid) == text


@pytest.mark.parametrize('text', (
    'Our software processes customer billing records and contract allocations.',
    'Our software can value securities using accounting rules.',
    'Premiums are received before claims are settled. The insurance float had no interest cost.',
    'Northvale will not increase prices for urgent customer orders, but quarterly revenue grew.',
    '北岭不会因客户急单而提价，但是本季度收入规模增长。',
    '辰枫不会对客户的紧急追加订单提\n价，但是紧急订单会增加季度收入规模。',
))
def test_true_financial_software_float_and_negative_customer_pricing_stay_support(text):
    session, _, uid, _, passage = assessed(text)
    assert passage.use == 'support', (text, passage)
    assert session.source_text(uid) == text


def test_accounting_rule_does_not_swallow_a_separate_explicit_business_statement():
    _, _, _, _, passage = assessed(
        'Accounting rules require firms to value securities at market. '
        'Our software processes customer billing records.')
    assert passage.use == 'support'


@pytest.mark.parametrize('text', (
    'Template: Northvale will not increase prices for urgent customer orders.',
    'Will Northvale increase prices for urgent customer orders?',
    'The accounting rule requires prices of securities to be restated.',
))
def test_pricing_words_inside_questions_templates_or_valuation_do_not_prove_operations(text):
    _, _, _, _, passage = assessed(text)
    assert passage.use != 'support'


def test_new_pricing_description_does_not_change_legacy_function_event_capability():
    from company_wiki.document_understanding.operating_states.assertion_roles import (
        descriptive_operating_relation, prepare_source_assertions,
    )
    text = 'Northvale will not increase prices for urgent customer orders.'
    roles = prepare_source_assertions(text)
    assert descriptive_operating_relation(text, prepared=roles)
    assert not descriptive_operating_relation(text, prepared=roles, include_source_descriptions=False)
