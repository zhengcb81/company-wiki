"""Source-language readability must not require an industry predicate lexicon."""
from copy import deepcopy

import pytest

from company_wiki.source_catalog.narrative_business_policy import project_reading_business_fact
from company_wiki.source_catalog.narrative_reading import _admitted
from company_wiki.source_catalog.narrative_support_use import source_narrative_relevance, source_support_use
from unit.du11_production.test_source_information_binding import session_for, unit_id


@pytest.mark.parametrize('text', (
    'Our vessels transport liquefied gas between coastal terminals.',
    'Our vessels are transporting liquefied gas between coastal terminals.',
    'Our trains carry passengers between rural communities.',
    'Our clinicians treat rare diseases at regional clinics.',
    'Our stores sell fresh vegetables to local households.',
    'We weave natural fibres into technical fabrics.',
    '本公司经营铁路运输业务。',
    '本集團經營鐵路運輸業務。',
    '我们的船舶运输液化天然气。',
    'The company transports liquefied gas between coastal terminals.',
    'Northvale transports liquefied gas between coastal terminals.',
    'Asteridge transports liquefied gas between coastal terminals.',
    'Northvale clinicians treat rare diseases at regional clinics.',
    '北岭公司经营铁路运输业务。',
    '晨曦公司经营铁路运输业务。',
))
def test_subject_led_unknown_business_is_readable_without_upgrading_fact(text):
    frozen = deepcopy(project_reading_business_fact(text, {'relations': []}))
    session, budget = session_for([text])
    uid = unit_id(0)
    fact = session.fact(uid)
    passage = session.source_passage(uid)
    assert passage.relevant and passage.use == 'support', (text, passage)
    roles = session.source_assertions(uid)
    use = source_support_use(text, fact=fact, financial_only=session.financial_only(uid),
                             source_roles=roles, passage=passage)
    assert _admitted(session.units[uid], {'priority': 1}, 'business_narrative',
                     fact=fact, support_use=use, offer_relevant=source_narrative_relevance(
                         fact=fact, source_roles=roles, passage=passage))[0]
    assert fact == frozen
    used = budget.used
    assert session.source_passage(uid) is passage
    assert budget.used == used


@pytest.mark.parametrize('text', (
    'Do our vessels transport liquefied gas?',
    'Our vessels transport liquefied gas. Is that correct?',
    'Template: Our vessels transport liquefied gas.',
    'Our trains',
    'Our trains in rural communities.',
    'Our products: vessels, trains and terminals.',
    '公司主要产品：船舶、车辆及设备。',
    'Our revenue was $100 million.',
    '本公司营业收入为100万元。',
    'We strive to create more value for shareholders.',
    'Our advanced vessels and trains.',
    'Our recently established coastal terminals.',
    'Our hospital trial results.',
    'The company coastal terminals.',
    '本公司的主要产品及业务。',
    '我们在西部地区的子公司。',
    '药物研发业务。',
    '药物代谢与动力学业务。',
    '公司的运营发展规划。',
    '部件装配流程。',
    '区域铁路持续发展的运输业务。',
    '这些不断改进的灌溉系统。',
))
def test_subject_alone_never_overrides_negative_or_financial_scope(text):
    session, _ = session_for([text])
    uid = unit_id(0)
    session.fact(uid)
    passage = session.source_passage(uid)
    assert not passage.relevant, (text, passage)


@pytest.mark.parametrize('text', (
    '-\n药物代谢与动力学业务持续精进科研与服务能力，实现7×24 小时自动化、智能\n化运营的生物分析流程闭环，进一步巩固在该领域的行业领先地位。',
    '-\n体外综合筛选平台技术加速突破，同步迭代自动化能力、提升运营效率，持续赢\n得新客户；',
    '体内药理学能力持续提升，驱动收入快速增长。',
    '区域铁路运力持续改善，同步扩展夜间客运线路。',
    '农业灌溉系统加速改造，同步迭代水压调节流程。',
))
def test_aspect_marked_real_and_unrelated_business_scopes_remain_readable(text):
    session, _ = session_for([text])
    uid = unit_id(0)
    session.fact(uid)
    passage = session.source_passage(uid)
    assert passage.relevant and passage.use == 'support', (text, passage)


@pytest.mark.parametrize('text', ('能力持续提升。', '产品持续开发，服务不断提升。'))
def test_generic_aspect_without_concrete_argument_remains_boilerplate(text):
    session, _ = session_for([text])
    uid = unit_id(0)
    session.fact(uid)
    assert not session.source_passage(uid).relevant


@pytest.mark.parametrize('text', (
    'Our vessels that are transporting gas.',
    'Our vessels which were built at coastal yards.',
    'The company whose vessels are transporting gas.',
    'The clinicians who have treated rare diseases.',
    '正在运输液化天然气的船舶。',
    '公司拥有的沿海码头。',
))
def test_relative_nominals_cannot_bypass_the_statement_grammar(text):
    from company_wiki.document_understanding.statement_grammar import observe_statement
    from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment

    assert observe_statement(text).status == 'fragment'
    passage = prepare_reading_business_assessment(text, {'relations': []}).passage
    assert not passage.relevant, (text, passage)
    assert passage.use != 'support'


@pytest.mark.parametrize('text', (
    'Our vessels are transporting gas.',
    'Our vessels were built at coastal yards.',
    'The company owns vessels that are transporting gas.',
    'The clinicians have treated rare diseases.',
    '船舶正在运输液化天然气。',
    '公司拥有沿海码头。',
))
def test_the_same_vocabulary_with_a_matrix_predicate_is_readable(text):
    from company_wiki.document_understanding.statement_grammar import observe_statement
    from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment

    assert observe_statement(text).independent
    passage = prepare_reading_business_assessment(text, {'relations': []}).passage
    assert passage.relevant and passage.use == 'support', (text, passage)


@pytest.mark.parametrize('text', (
    'Our vessels that are transporting gas.',
    '公司拥有的沿海码头。',
))
def test_causal_hint_without_an_independent_proof_uses_charged_grammar(text):
    from company_wiki.document_understanding.operating_states.assertion_roles import (
        AssertionRole, SourceAssertionRoles,
    )
    from company_wiki.document_understanding.statement_grammar import STATEMENT_GRAMMAR_WORK_PER_CHAR
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_catalog.narrative_source_passage import (
        SourceStatementScope, prepare_source_passage, statement_assertion_key,
    )

    # Isolate the mixed-financial causal branch. A prepared lexical hint is
    # deliberately present, while no event/measurement/role proof is present.
    roles = SourceAssertionRoles((AssertionRole(text, False),))
    scope = SourceStatementScope(text, roles,
        business_causal_keys=frozenset((statement_assertion_key(text),)))
    budget = WorkBudget(100_000)
    passage = prepare_source_passage(text, roles, purpose='unknown', financial_only=True,
        accounting_text=lambda _text: True, non_operating_purposes=frozenset(),
        existing_use=('context_only', 'financial_only'), existing_relevant=False,
        statement_scope=scope, grammar_work_budget=budget)
    assert not passage.relevant and passage.use != 'support'
    assert budget.used == STATEMENT_GRAMMAR_WORK_PER_CHAR * len(text) + 1


@pytest.mark.parametrize('text', (
    '订单转向不同的产品组合。',
    '公司拥有沿海的码头。',
))
def test_object_internal_modifiers_do_not_nominalize_the_matrix_predicate(text):
    from company_wiki.document_understanding.statement_grammar import observe_statement
    from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment

    assert observe_statement(text).independent
    assert prepare_reading_business_assessment(text, {'relations': []}).passage.use == 'support'


@pytest.mark.parametrize('text', (
    'When order volumes recover, we reopen the coastal terminals.',
    'Where equipment fails, we dispatch a maintenance crew.',
))
def test_adverbial_conditions_preserve_the_matrix_clause_and_fact_qualifications(text):
    from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment

    prepared = prepare_reading_business_assessment(text, {'relations': []})
    old = project_reading_business_fact(text, {'relations': []}, source_roles=prepared.source_roles)
    assert prepared.passage.use == 'support' and prepared.passage.relevant
    assert prepared.fact == old
    assert not {'operating_milestone', 'operating_current_state'} & set(prepared.fact.reasons)
    assert not prepared.source_roles.bound_operating


@pytest.mark.parametrize('text', (
    'When will we reopen the coastal terminals?',
    'When will we reopen the coastal terminals',
    'Where will we dispatch a maintenance crew?',
    'Where will we dispatch a maintenance crew',
    'Which software processes customer billing records',
    'What equipment manufactures medical tools',
    'Which products are available to customers',
    'Who provides software to banks',
))
def test_interrogative_inversion_stays_non_assertion_with_or_without_question_mark(text):
    from company_wiki.document_understanding.statement_grammar import observe_statement
    from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment

    assert observe_statement(text).status == 'fragment'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use != 'support' and not prepared.passage.relevant


@pytest.mark.parametrize('text', ('When order volumes recover.', 'Where equipment fails.'))
def test_an_adverbial_introduction_alone_is_not_a_matrix_statement(text):
    from company_wiki.document_understanding.statement_grammar import observe_statement
    from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment

    assert observe_statement(text).status == 'fragment'
    assert not prepare_reading_business_assessment(text, {'relations': []}).passage.relevant


@pytest.mark.parametrize('text', ('农户购买新鲜的蔬菜。', '农户购买蔬菜的村庄。'))
def test_fixed_pos_lexical_ambiguity_keeps_the_original_without_a_fact_upgrade(text):
    from company_wiki.document_understanding.statement_grammar import observe_statement

    # The packaged dictionary labels 新鲜 as a place name (ns), not an
    # adjective. A small POS observer cannot resolve this sense from a noun
    # modifier's surface shape; no company/word-specific override is added.
    observation = observe_statement(text)
    assert observation.status == 'unknown'
    assert observation.reason == 'statement_grammar_ambiguous'
    session, budget = session_for([text])
    uid = unit_id(0)
    fact = session.fact(uid)
    roles = session.source_assertions(uid)
    passage = session.source_passage(uid)
    assert passage.use == 'unresolved' and passage.relevant
    assert passage.reason == 'source_grammar_ambiguous'
    assert not fact.eligible and not roles.bound_operating and roles.independent_payload is None
    assert fact == project_reading_business_fact(text, {'relations': []}, source_roles=roles)
    use = source_support_use(text, fact=fact, financial_only=session.financial_only(uid),
                             source_roles=roles, passage=passage)
    assert _admitted(session.units[uid], {'priority': 1}, 'business_narrative', fact=fact,
        support_use=use, offer_relevant=source_narrative_relevance(
            fact=fact, source_roles=roles, passage=passage))[0]
    assert session.source_text(uid) == text
    used = budget.used
    assert session.source_passage(uid) is passage and budget.used == used
