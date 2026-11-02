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
    'Our vessels transport liquefied gas between coastal terminals.',
    'The clinicians treat rare diseases at regional clinics.',
    'Northvale owns an insurer and two electricity utilities.',
    '船舶正在运输液化天然气。',
    '公司拥有沿海的码头。',
    '公司主要品牌都有专属的工厂，大多数工厂只为一个品牌服务。',
    '公司向山区医院提供维护服务。',
    'Our teams cover crops with shade nets.',
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
    # R4: the original None remains None; a bound use-location source scope
    # is now explicitly observed, without a factual/financial upgrade.
    assert prepared.passage.use == 'support' and prepared.passage.relevant
    assert prepared.source_roles.source_scope and not prepared.fact.eligible
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

    def counted(value, role, **kwargs):
        calls.append(value)
        return original(value, role, **kwargs)

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


@pytest.mark.parametrize('joiner', ('and', 'or', 'but'))
@pytest.mark.parametrize('specific_first', (False, True))
def test_coordinated_goal_preserves_each_predicates_own_arguments(joiner, specific_first):
    specific, abstract = 'reopen neonatal wards', 'create value'
    left, right = (specific, abstract) if specific_first else (abstract, specific)
    text = f'We aim to {left} {joiner} {right}.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    _assert_unknown_goal(text, prepared)
    assert not prepared.fact.eligible and not prepared.fact.financial_exempt


@pytest.mark.parametrize('text', (
    'We are committed to treating rare diseases and creating value.',
    'We are committed to creating value and treating rare diseases.',
    'We aim to reopen neonatal wards, treat rare diseases and create value.',
    'We aim to create value, treat rare diseases and reopen neonatal wards.',
    'We aim to help clinicians to treat rare diseases and create value.',
    'We aim to create value by treating rare diseases.',
    'We aim to supply products that detect rare diseases and create value.',
))
def test_nested_and_multiple_goal_predicates_do_not_lose_concrete_arguments(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    _assert_unknown_goal(text, prepared)
    assert not {'operating_milestone', 'operating_current_state'} & set(prepared.fact.reasons)


@pytest.mark.parametrize('text', (
    'We aim to create value for customers.',
    'We aim to create value for clinicians.',
    'We aim to create value for customers who reopen neonatal wards.',
    'We aim to create value for customers who treat rare diseases and reopen wards.',
    'We aim to create value and improve customer satisfaction.',
    'We aim to improve customer satisfaction or create value.',
    'We are committed to creating value for clinicians and customers.',
))
def test_beneficiary_background_or_abstract_coordination_cannot_create_business_content(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use != 'support' and not prepared.passage.relevant
    assert not prepared.fact.eligible and not prepared.fact.financial_exempt


@pytest.mark.parametrize('joiner', ('并', '或者', '而且'))
@pytest.mark.parametrize('specific_first', (False, True))
def test_chinese_goal_coordination_has_the_same_order_invariance(joiner, specific_first):
    specific, abstract = '重开新生儿病房', '创造价值'
    left, right = (specific, abstract) if specific_first else (abstract, specific)
    text = f'公司努力{left}{joiner}{right}。'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    _assert_unknown_goal(text, prepared)
    assert not prepared.fact.eligible and not prepared.fact.financial_exempt


@pytest.mark.parametrize('text', (
    '公司努力为客户创造价值。',
    '公司努力创造价值并满足客户需求。',
    '公司努力满足客户需求或者创造价值。',
))
def test_chinese_benefit_and_abstract_goal_coordination_stays_context(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use != 'support' and not prepared.passage.relevant
    assert not prepared.fact.eligible and not prepared.fact.financial_exempt


@pytest.mark.parametrize('operator', ('aim', 'strive', 'aspire'))
def test_goal_governor_does_not_supply_a_whole_sentence_veto(operator):
    text = f'We {operator} to reopen neonatal wards and create value.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    _assert_unknown_goal(text, prepared)
    assert not prepared.fact.eligible


@pytest.mark.parametrize('operator', ('努力', '争取', '坚持'))
def test_prepared_operator_boundary_is_not_a_dictionary_or_predicate_override(operator):
    statement = f'公司{operator}创造价值并重开新生儿病房。'
    nominal = f'公司的{operator}创造计划。'
    _assert_unknown_goal(statement, prepare_reading_business_assessment(statement, {'relations': []}))
    assert not prepare_reading_business_assessment(nominal, {'relations': []}).passage.relevant


def test_goal_matrix_and_complements_are_prepared_once_before_fact_projection(monkeypatch):
    from company_wiki.source_catalog import narrative_source_passage as owner
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    original = owner.observe_statement
    calls = []

    def counted(text, **kwargs):
        calls.append(text)
        return original(text, **kwargs)

    monkeypatch.setattr(owner, 'observe_statement', counted)
    text = 'We aim to reopen neonatal wards and create value.'
    session, budget = session_for([text])
    uid = unit_id(0)
    fact, passage = session.fact(uid), session.source_passage(uid)
    assert passage.use == 'unresolved' and not passage.relevant and not fact.eligible
    assert calls == [text]
    used = budget.used
    assert session.fact(uid) is fact and session.source_passage(uid) is passage
    assert calls == [text] and budget.used == used


def test_predicate_scope_keeps_the_two_direct_objects_and_excludes_the_beneficiary():
    from company_wiki.document_understanding.statement_grammar import observe_statement

    text = 'We aim to reopen neonatal wards and create value for clinicians.'
    observation = observe_statement(text)
    assert observation.independent
    assert [scope.argument_nominals for scope in observation.argument_scopes] == [('wards',), ('value',)]
    assert 'clinicians' not in observation.argument_nominals


def test_a_typed_function_inside_a_beneficiary_relative_cannot_supply_the_goal():
    text = 'We aim to create value for customers whose products process orders.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use != 'support' and not prepared.passage.relevant
    assert not prepared.fact.eligible and not prepared.fact.financial_exempt


def test_the_same_typed_function_as_a_direct_product_goal_is_preserved():
    text = 'We aim to supply software that processes customer orders and create value.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    _assert_unknown_goal(text, prepared)


def test_a_separate_typed_business_statement_survives_an_abstract_goal():
    text = 'We aim to create value for customers. Our software processes customer orders.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'support' and prepared.passage.relevant
    assert prepared.fact.eligible


@pytest.mark.parametrize('text', (
    'We aim to serve 1200 customers and create value.',
    '公司努力新增300个客户并创造价值。',
))
def test_direct_quantified_operating_goals_remain_original_unresolved_without_fake_numbers(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'unresolved' and prepared.passage.relevant
    assert prepared.passage.reason == 'source_goal_quantity_unresolved'
    assert not {'operating_quantity', 'operating_metric_change', 'operating_current_state'} & set(prepared.fact.reasons)


@pytest.mark.parametrize('text', (
    'We aim to create one vision for customers.',
    'We aim to create value for 300 clinicians.',
    'We aim to create value for 300 customers.',
))
def test_numbers_in_abstract_heads_or_beneficiary_pps_do_not_prove_operating_goals(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use != 'support' and not prepared.passage.relevant
    assert not prepared.fact.eligible and not prepared.fact.financial_exempt


def test_direct_operating_quantity_role_is_observed_once_in_prepared_scope(monkeypatch):
    from company_wiki.source_catalog import narrative_business_policy as owner

    real = owner.source_has_operating_measure
    calls = []

    def observed(value):
        calls.append(value)
        return real(value)

    monkeypatch.setattr(owner, 'source_has_operating_measure', observed)
    prepared = owner.prepare_reading_business_assessment(
        'We aim to serve 1200 customers and serve 1400 customers.', {'relations': []})
    assert prepared.passage.use == 'unresolved' and prepared.passage.relevant
    assert calls == ['customers']


def test_predicate_argument_scope_walk_is_linear_and_does_not_retag():
    from company_wiki.document_understanding.statement_grammar.predicate_arguments import predicate_argument_scopes

    for count in (32, 64, 128):
        visits = []

        class ObservedTags(list):
            def __getitem__(self, value):
                result = super().__getitem__(value)
                if isinstance(value, slice):
                    visits.append(len(result))
                    return type(self)(result)
                visits.append(1)
                return result

            def __iter__(self):
                for value in super().__iter__():
                    visits.append(1)
                    yield value

        tagged = ObservedTags([('act', 'VB'), ('object', 'NN'), ('or', 'CC')] * count)
        scopes = predicate_argument_scopes(tagged, 0, language='en')
        assert len(scopes) == count
        assert sum(visits) == 2 * len(tagged)


def test_a_concrete_noun_modifier_is_not_removed_with_rhetorical_adjectives():
    text = 'We aim to supply surgical services and create value.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    _assert_unknown_goal(text, prepared)


def test_unavailable_goal_binding_does_not_stop_an_independent_non_goal_typed_scope(monkeypatch):
    from company_wiki.document_understanding import statement_grammar as grammar
    from unit.document_understanding_selection.test_reading_production_selection import _document, _unit, _select

    goal = 'We aim to create value for customers whose products process orders.'
    healthy = 'Our software processes customer orders.'

    def unavailable():
        raise LookupError('isolated missing model')

    monkeypatch.setattr(grammar, '_english_tagger', unavailable)
    result = _select(_document(_unit(goal, paragraph=0, kind='html_paragraph'),
                              _unit(healthy, paragraph=1, kind='html_paragraph')))
    assert result.status == 'partial'
    assert [span.raw_text for span in result.evidence_spans] == [healthy]
    assert result.reading_context['source_processing_complete'] is False
    assert any(diagnostic['code'] == 'source_grammar_unavailable' for diagnostic in result.selection_diagnostics)


def _assert_unknown_goal(text, prepared):
    # R4 erratum: POS binds these words but supplies no positive operating
    # argument. Keep the original claim, not an invented economic proof.
    from company_wiki.document_normalization.text_matching import matching_reading_text
    assert prepared.passage.use == 'unresolved' and not prepared.passage.relevant
    assert not prepared.fact.eligible
    assert prepared.source_roles.independent_payload is None
    assert not prepared.source_roles.bound_payload
    expected = matching_reading_text(text).strip(' .。!?;；')
    assert ''.join(c.text for c in prepared.source_roles.clauses).strip(' .。!?;；') == expected


@pytest.mark.parametrize('text', (
    'We are committed to treating rare diseases at regional clinics.',
    '公司将努力运输液化天然气。',
))
def test_unknown_goals_remain_source_words_without_unproved_relevance(text):
    _assert_unknown_goal(text, prepare_reading_business_assessment(text, {'relations': []}))



def test_unknown_catalogue_members_do_not_prove_each_others_semantics():
    text = 'Our services include orchard planting and coastal transport.'
    _assert_unknown_goal(text, prepare_reading_business_assessment(text, {'relations': []}))
