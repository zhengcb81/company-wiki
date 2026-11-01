"""A complete sentence is syntax, not a source business-relevance proof."""
import pytest

from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment


@pytest.mark.parametrize('text', (
    'We remain committed to sustainable high-quality development and creating value.',
    '我们继续坚持高质量、可持续发展的原则。',
    '公司将努力满足不断变化的客户需求，争取推动收入增长。',
    '公司感谢投资者的关注，未来将继续努力提升综合实力。',
    '公司感谢投资者的关注。',
    '我们感谢读者的支持。',
    'The words paid seats appear in a list of terms.',
    '设备名称列于索引。用于。',
    'Due to rounding, the amounts shown may not add to the total.',
    '由于四舍五入，本表各项加总与总数可能存在差异。',
    'The art exhibit includes paintings and sculpture.',
))
def test_source_context_cannot_be_repromoted_by_complete_sentence_syntax(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use != 'support' and not prepared.passage.relevant
    assert not prepared.fact.eligible and not prepared.fact.financial_exempt


@pytest.mark.parametrize('text', (
    'Our service coverage includes remote factory maintenance.',
    'Our services include orchard planting and coastal transport.',
    'Our vessels transport liquefied gas between coastal terminals.',
    'The clinicians treat rare diseases at regional clinics.',
    'Northvale owns an insurer and two electricity utilities.',
    '船舶正在运输液化天然气。',
    '公司拥有沿海的码头。',
    '公司主要品牌都有专属的工厂，大多数工厂只为一个品牌服务。',
    '公司向山区医院提供维护服务。',
    'Our teams cover crops with shade nets.',
    'We are committed to treating rare diseases at regional clinics.',
    '公司将努力运输液化天然气。',
))
def test_business_content_does_not_need_a_company_or_industry_allowlist(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'support' and prepared.passage.relevant


@pytest.mark.parametrize('text', (
    '公司感谢投资者关注，船舶将运输液化天然气。',
    '公司船舶运输液化天然气，并感谢投资者的关注。',
))
def test_courtesy_inside_a_mixed_statement_cannot_erase_an_unfamiliar_operation(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'support' and prepared.passage.relevant


def test_an_existing_incomplete_role_proof_stays_readable_without_becoming_complete():
    text = 'Our equipment is used in rural clinics and urban markets.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'unresolved' and prepared.passage.relevant
    assert prepared.passage.reason == 'source_payload_unresolved'
    assert prepared.source_roles.independent_payload is None


@pytest.mark.parametrize('context', (
    'We remain committed to sustainable development and creating value.',
    'The words paid seats appear in a list of terms.',
    'Due to rounding, the amounts shown may not add to the total.',
))
def test_context_never_erases_an_independent_unfamiliar_business_sentence(context):
    text = context + ' Our vessels transport liquefied gas between coastal terminals.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'support' and prepared.passage.relevant
    assert not prepared.fact.eligible  # Readability cannot invent a typed event.


@pytest.mark.parametrize('text', ('(iv)\n经营租赁', '23  任意示范控股有限公司'))
def test_enumerator_and_legal_label_cannot_supply_a_matrix_subject(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use != 'support' and not prepared.passage.relevant


@pytest.mark.parametrize('text', (
    '本期毛利率主要原因是客户结构的调整。',
    '本期毛利率表现主要得益于客户结构和产品结构的调整以及生产措施的推进。',
))
def test_source_business_cause_uses_its_nominal_complement_without_a_false_event(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'support' and prepared.passage.relevant
    assert not {'operating_milestone', 'operating_current_state'} & set(prepared.fact.reasons)


@pytest.mark.parametrize('text', (
    '公司感谢投资者的关注。',
    'The words paid seats appear in a list of terms.',
    'Due to rounding, the amounts shown may not add to the total.',
    '23  任意示范控股有限公司',
    '我们继续坚持高质量、可持续发展的原则。',
))
def test_known_context_is_prepared_once_before_pos_and_repeated_access_is_free(monkeypatch, text):
    from company_wiki.source_catalog import narrative_source_passage as owner
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    original = owner.source_clause_context
    calls = []

    def counted(value, role):
        calls.append(value)
        return original(value, role)

    def unexpected(*args, **kwargs):
        raise AssertionError('known discourse context must not execute a POS fallback')

    monkeypatch.setattr(owner, 'source_clause_context', counted)
    monkeypatch.setattr(owner, 'observe_statement', unexpected)
    session, budget = session_for([text])
    uid = unit_id(0)
    fact, passage = session.fact(uid), session.source_passage(uid)
    assert passage.use == 'context_only' and not passage.relevant
    used = budget.used
    assert len(calls) == 1
    assert session.fact(uid) is fact and session.source_passage(uid) is passage
    assert len(calls) == 1 and budget.used == used


def test_generic_context_work_is_linear_in_source_length(monkeypatch):
    import re
    from company_wiki.document_understanding.operating_states.assertion_roles import AssertionRole
    from company_wiki.source_catalog import narrative_source_context as owner
    from unit.document_understanding_selection.test_prepared_predicate_context import RegexMeter

    patterns = {name: value for name, value in vars(owner).items() if isinstance(value, re.Pattern)}
    normalized = []
    for count in (32, 64, 128):
        text = 'Our vessels ' + 'transport coastal cargo ' * count
        totals = {}
        with monkeypatch.context() as patch:
            for name, pattern in patterns.items():
                patch.setattr(owner, name, RegexMeter(pattern, totals, name))
            owner.source_clause_context(text, AssertionRole(text, False))
        normalized.append(sum(totals.values()) / len(text))
    assert max(normalized) / min(normalized) <= 1.05


@pytest.mark.parametrize('text', ('为品牌服务。', '为田间作物服务。'))
def test_prepositional_nominal_argument_cannot_be_a_matrix_subject(text):
    from company_wiki.document_understanding.statement_grammar import observe_statement

    assert observe_statement(text).status == 'fragment'
    assert not prepare_reading_business_assessment(text, {'relations': []}).passage.relevant


def test_the_same_terminal_verbal_noun_with_an_explicit_subject_is_readable():
    text = '工厂只为一个品牌服务。'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'support' and prepared.passage.relevant


@pytest.mark.parametrize('text', (
    'Our vessels transport liquefied gas between coastal terminals.',
    'We remain committed to sustainable development and creating value.',
))
def test_objective_operator_observation_is_reused_for_the_exact_source_clause(monkeypatch, text):
    from company_wiki.source_catalog import narrative_source_context as owner
    from unit.document_understanding_selection.test_prepared_predicate_context import RegexMeter

    totals = {}
    monkeypatch.setattr(owner, '_OBJECTIVE', RegexMeter(owner._OBJECTIVE, totals, 'objective'))
    prepare_reading_business_assessment(text, {'relations': []})
    assert totals['objective'] == len(text)
