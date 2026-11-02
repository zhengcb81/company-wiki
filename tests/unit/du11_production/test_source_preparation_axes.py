"""Fact admission must not overwrite valid source role observations."""
from types import SimpleNamespace

import pytest

from company_wiki.document_understanding.operating_states.assertion_roles import prepare_source_assertions
from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment
from company_wiki.source_catalog.narrative_source_passage import prepare_source_statement_scope
from company_wiki.source_catalog.narrative_reading import _admitted


@pytest.mark.parametrize('text, payload, use', (
    ('Our software supports customer engagement.', False, 'context_only'),
    ('Our platform supports outstanding goals.', None, 'unresolved'),
    ('我们的平台支持宏伟愿景。', None, 'unresolved'),
))
def test_source_roles_survive_context_fact_filter_without_a_proof_upgrade(text, payload, use):
    raw = prepare_source_assertions(text)
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert raw.operating and prepared.source_roles.operating
    assert raw.independent_payload is payload
    assert prepared.source_roles.independent_payload is payload
    assert prepared.passage.use == use and not prepared.passage.relevant
    if payload is None:
        assert not prepared.fact.eligible
    else:
        # R5 erratum: a complete generic description can remain recallable
        # background. It is not qualified event/number or scarce material.
        assert not {'operating_milestone', 'operating_current_state', 'operating_quantity'} & set(prepared.fact.reasons)


def test_prepared_scope_has_separate_valid_source_and_fact_role_views():
    text = 'Our software supports customer engagement.'
    original = prepare_source_assertions(text)
    prepared = prepare_source_statement_scope(text, original)
    assert prepared.roles == original
    assert prepared.fact_roles is not None and not prepared.fact_roles.clauses
    assert len(prepared.text) == len(text) and not prepared.text.strip()


@pytest.mark.parametrize('text', (
    'Our sales services cover 17 regional markets.',
    '本企业的软件产品覆盖目标功能的45%。',
))
def test_existing_coverage_proof_is_prepared_before_generic_quote_fallback(monkeypatch, text):
    from company_wiki.source_catalog import narrative_source_passage as owner

    def unexpected(*args, **kwargs):
        raise AssertionError('existing bound coverage proof must not need POS to prove itself')

    monkeypatch.setattr(owner, 'observe_statement', unexpected)
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.fact.eligible and 'business_coverage_relation' in prepared.fact.reasons
    assert prepared.passage.use == 'support' and prepared.passage.relevant
    assert not {'operating_current_state', 'operating_milestone'} & set(prepared.fact.reasons)


@pytest.mark.parametrize('text', (
    'IV therapy services are provided to hospitals.',
    'Our 2026 product portfolio includes recycling systems.',
    '一体化生产服务覆盖多个下游客户工序。',
))
def test_each_original_marker_counterexample_is_independently_admitted(text):
    unit = SimpleNamespace(raw_text=text, source_role='company_filing', unit_kind='html_paragraph')
    assert _admitted(unit, {'section_role': 'business'}, 'narrative')[0]


@pytest.mark.parametrize('text', (
    'Our sales services cover 17 regional markets.',
    'Our products cover 45% of revenue from equipment markets.',
))
def test_bound_relation_owner_is_observed_once_for_true_and_false_results(monkeypatch, text):
    from company_wiki.source_catalog import narrative_business_policy as owner
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    real = owner._business_coverage_relation
    calls = []

    def counted(value):
        calls.append(value)
        return real(value)

    monkeypatch.setattr(owner, '_business_coverage_relation', counted)
    session, budget = session_for([text])
    uid = unit_id(0)
    fact = session.fact(uid)
    assert calls == [text[:-1]]
    used = budget.used
    assert session.fact(uid) is fact
    session.source_passage(uid)
    assert calls == [text[:-1]] and budget.used == used


def test_no_typed_pre_scan_runs_before_shared_phase_budget_reservation(monkeypatch):
    from company_wiki.source_catalog import narrative_business_policy as owner
    from company_wiki.source_catalog.narrative_operating_relations import READING_BUSINESS_SCAN_PASSES
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    text = 'Our sales services cover 17 regional markets.'
    session, budget = session_for([text])
    uid = unit_id(0)
    session.relations(uid)
    budget.max_work_units = budget.used + READING_BUSINESS_SCAN_PASSES * len(session.source_text(uid)) - 1

    def unexpected(*args, **kwargs):
        raise AssertionError('phase must reserve work before typed relation preparation')

    monkeypatch.setattr(owner, '_business_coverage_relation', unexpected)
    session.fact(uid)
    assert not session.complete and session.source_passage(uid) is None


@pytest.mark.parametrize('text', (
    'Our platform supports portable goals.',
    'Our platform supports portable customer aspirations.',
    'We aim to achieve portable goals.',
))
def test_unseen_adjective_cannot_prove_a_tentative_nominal_head(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'unresolved' and not prepared.passage.relevant
    assert not prepared.fact.eligible


def test_unseen_nominal_keeps_its_original_words_without_inventing_relevance():
    text = 'Our platform supports portable compressors.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    # R4 erratum: portable compressors has no positive argument proof in the
    # current owner. POS/unknown words cannot distinguish it from marketing.
    assert prepared.passage.use == 'unresolved' and not prepared.passage.relevant
    assert not prepared.fact.eligible and prepared.source_roles.independent_payload is None
    assert prepared.source_roles.clauses[0].text.rstrip('.') == text.rstrip('.')


def test_coordinated_nominal_arguments_keep_their_own_modifiers():
    from company_wiki.document_understanding.statement_grammar.predicate_arguments import predicate_argument_scopes

    tagged = [('supply', 'VB'), ('surgical', 'JJ'), ('services', 'NNS'), ('and', 'CC'),
              ('create', 'JJ'), ('value', 'NN')]
    scopes = predicate_argument_scopes(tagged, 0, language='en')
    assert [(scope.argument_nominals, scope.argument_modifiers) for scope in scopes] == [
        (('services',), ('surgical',)), (('value',), ('create',))]


def test_target_scans_are_precharged_and_memoized_with_the_shared_source_scope(monkeypatch):
    from company_wiki.source_catalog import narrative_source_context as owner
    from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    from company_wiki.document_understanding.statement_grammar import observe_statement

    text = 'We aim to pursue luminous horizons.'
    role = prepare_source_assertions(text).clauses[0]
    observation = observe_statement(text)
    arguments = [' '.join((*scope.argument_modifiers, *scope.argument_nominals))
                 for scope in observation.argument_scopes]
    amount = owner.SOURCE_TARGET_SCAN_PASSES * sum(map(len, dict.fromkeys(arguments)))
    assert amount > 0
    original = owner.source_argument_payload
    calls = []

    def counted(value):
        calls.append(value)
        return original(value)

    monkeypatch.setattr(owner, 'source_argument_payload', counted)
    with pytest.raises(WorkBudgetExceeded):
        owner.statement_complement_context(text, role, observation,
            prepared=owner.source_clause_context(text, role), work_budget=WorkBudget(amount - 1))
    assert not calls
    session, budget = session_for([text])
    passage = session.source_passage(unit_id(0))
    used = budget.used
    assert calls == list(dict.fromkeys(arguments))
    assert session.source_passage(unit_id(0)) is passage and budget.used == used
    assert calls == list(dict.fromkeys(arguments))
