"""Syntax and unknown words do not prove a business argument's semantics."""
import pytest

from company_wiki.document_understanding.operating_states.assertion_roles import prepare_source_assertions
from company_wiki.source_catalog.narrative_business_policy import prepare_reading_business_assessment


def _no_event_or_actual_measure(prepared):
    # R5: material eligibility/self-contained source information is not world
    # verification. These are the actual event/number boundary assertions.
    assert not {'operating_milestone', 'operating_current_state', 'operating_quantity',
                'operating_metric_change', 'business_revenue_measure'} & set(prepared.fact.reasons)


@pytest.mark.parametrize('text', (
    'Our platform supports remarkable ambitions.',
    'Our platform supports promising possibilities.',
    'Our software supports ambitious priorities.',
    'Our platform plans to support unfamiliar technical endeavours.',
    'We aim to pursue luminous horizons.',
))
def test_unknown_function_or_goal_arguments_cannot_donate_positive_relevance(text):
    original = prepare_source_assertions(text)
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert original.independent_payload is None and not original.bound_payload
    assert prepared.source_roles.independent_payload is None and not prepared.source_roles.bound_payload
    assert prepared.passage.use == 'unresolved' and not prepared.passage.relevant
    assert not prepared.fact.eligible
    from company_wiki.source_catalog.narrative_support_use import source_narrative_relevance
    assert not source_narrative_relevance(fact=prepared.fact, source_roles=prepared.source_roles)


@pytest.mark.parametrize('text', (
    'Our production services cover customer assembly operations.',
    'Our software platform covers hospital workflows.',
    'Our service range includes coastal transport processes.',
    '一体化生产服务覆盖多个下游客户工序。',
    '我们的设备服务涵盖田间灌溉作业。',
    '本公司的产品覆盖多个地区的检验流程。',
))
def test_explicit_qualitative_operating_scope_has_a_positive_source_argument(text):
    original = prepare_source_assertions(text)
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert original.operating and (original.source_scope or original.independent_payload is True)
    assert prepared.passage.use == 'support' and prepared.passage.relevant
    assert not {'operating_milestone', 'operating_current_state'} & set(prepared.fact.reasons)
    if original.independent_payload is None:
        _no_event_or_actual_measure(prepared)


@pytest.mark.parametrize('text', (
    'Our production services cover remarkable ambitions.',
    'Our software platform supports promises for regional operations.',
    'Our loans cover customer liabilities.',
    'Our services have outstanding goals. Regional operations are mentioned elsewhere.',
    'The procedure states that our services cover regional workflows.',
    '流程指南规定本公司的服务应覆盖多个客户工序。',
))
def test_unproved_financial_cross_sentence_and_template_scopes_cannot_borrow_operating_head(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use != 'support' and not prepared.passage.relevant
    assert not prepared.fact.eligible


@pytest.mark.parametrize('text', (
    'Our vessels transport liquefied gas between coastal terminals.',
    'Our software processes customer order records.',
    'Our sales services cover 17 regional markets.',
    'We aim to supply sterilisation tools and create value.',
))
def test_actual_quotes_and_existing_positive_payloads_remain_distinct_from_unknown_goals(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.passage.use == 'support' and prepared.passage.relevant


@pytest.mark.parametrize('text', (
    'Our product portfolio includes recycling systems.',
    'Our equipment lineup comprises control systems.',
    'Our service range includes coastal transport processes.',
    'IV therapy services are provided to hospitals.',
    '一体化生产服务覆盖多个下游客户工序。',
))
def test_source_scope_preserves_source_information_without_an_event_or_actual_measure(text):
    from company_wiki.source_catalog.narrative_business_disclosures import reading_material_value
    from company_wiki.source_catalog.narrative_support_use import source_support_use

    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.source_roles.source_scope
    assert prepared.passage.use == 'support'
    _no_event_or_actual_measure(prepared)
    if prepared.source_roles.independent_payload is None:
        assert reading_material_value(prepared.fact, source_roles=prepared.source_roles) == 'description'
        assert source_support_use(text, fact=prepared.fact, financial_only=False,
                                  source_roles=prepared.source_roles)[0] == 'support'


@pytest.mark.parametrize('text, payload, scope', (
    ('We plan to develop new products.', True, True),
    ('Our sales services cover 17 regional markets.', True, False),
    ('Our platform supports remarkable ambitions.', False, False),
))
def test_one_bound_relation_owner_exposes_its_actual_axes(text, payload, scope):
    from company_wiki.source_catalog import narrative_business_policy as owner

    cache = {}
    kwargs = dict(causal_observations={}, metric_observations={}, prepared=cache)
    assert owner._independent_reading_relation(text, **kwargs) is payload
    assert owner._reading_source_scope(text, **kwargs) is scope
    assert bool(any(value.payload_reasons for value in cache.values())) is payload
    assert bool(any(value.scope_reasons for value in cache.values())) is scope


@pytest.mark.parametrize('text', (
    'Our services include remarkable ambitions and promising possibilities.',
    'Our product range comprises luminous horizons and unfamiliar endeavours.',
))
def test_closed_declared_members_supply_source_information_without_world_verification(text):
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    # R5 erratum: declared member names are self-contained source data; no
    # industry dictionary or inference that the names are true is required.
    assert prepared.source_roles.independent_payload is True and prepared.fact.eligible
    assert prepared.passage.use == 'support' and prepared.passage.relevant
    assert prepared.source_roles.clauses[0].text == text
    _no_event_or_actual_measure(prepared)


def test_catalogue_preserves_material_members_without_an_event_or_actual_measure():
    text = 'Our product range includes recycling systems and control systems.'
    prepared = prepare_reading_business_assessment(text, {'relations': []})
    assert prepared.source_roles.independent_payload is True and prepared.source_roles.source_scope
    assert prepared.fact.eligible
    _no_event_or_actual_measure(prepared)
    assert prepared.passage.use == 'support' and prepared.passage.relevant
    assert prepared.source_roles.clauses[0].text == text


def test_compat_relevance_cannot_override_unknown_source_roles_with_a_legacy_label():
    from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact
    from company_wiki.source_catalog.narrative_support_use import source_narrative_relevance

    roles = prepare_source_assertions('Our platform supports remarkable ambitions.')
    legacy = OperatingFact(True, reasons=('operating_mechanism',), purpose='operating')
    assert roles.independent_payload is None and not roles.source_scope
    assert not source_narrative_relevance(fact=legacy, source_roles=roles)


def test_scope_observer_precharges_and_memoizes_a_false_result(monkeypatch):
    from company_wiki.document_understanding.operating_states import assertion_roles as owner
    from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded

    target = 'remarkable ambitions'
    cost = owner.SOURCE_SCOPE_ARGUMENT_WORK_PER_CHAR * len(target) + 1
    real = owner._operating_scope_argument
    calls = []

    def counted(value):
        calls.append(value)
        return real(value)

    monkeypatch.setattr(owner, '_operating_scope_argument', counted)
    cache = {}
    with pytest.raises(WorkBudgetExceeded):
        owner._scope_argument_observation(target, cache, work_budget=WorkBudget(cost - 1))
    assert not calls and not cache
    budget = WorkBudget(cost)
    first = owner._scope_argument_observation(target, cache, work_budget=budget)
    assert not any((first.operating, first.customer, first.member_class, first.incentive))
    assert owner._scope_argument_observation(target, cache, work_budget=budget) is first
    assert calls == [target] and budget.used == cost


def test_real_preparation_entries_share_the_same_scope_work_account(monkeypatch):
    from company_wiki.document_understanding.operating_states import assertion_roles as owner
    from company_wiki.resource_budget import WorkBudget
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    real = owner._scope_argument_observation
    accounts = []

    def counted(value, cache, *, work_budget):
        accounts.append(work_budget)
        return real(value, cache, work_budget=work_budget)

    monkeypatch.setattr(owner, '_scope_argument_observation', counted)
    text = 'Our software platform covers hospital workflows.'
    session, budget = session_for([text])
    fact = session.fact(unit_id(0))
    assert accounts and all(account is budget for account in accounts)
    visits, used = len(accounts), budget.used
    assert session.fact(unit_id(0)) is fact
    session.source_passage(unit_id(0))
    assert len(accounts) == visits and budget.used == used
    accounts.clear()
    direct = WorkBudget(200000)
    prepare_reading_business_assessment(text, {'relations': []}, grammar_work_budget=direct)
    assert accounts and all(account is direct for account in accounts)


def test_scope_budget_failure_never_caches_partial_assertions_as_complete():
    from company_wiki.document_understanding.operating_states import assertion_roles as owner
    from company_wiki.source_catalog.narrative_operating_relations import READING_BUSINESS_SCAN_PASSES
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    text = 'Our software platform covers hospital workflows.'
    session, budget = session_for([text])
    uid = unit_id(0)
    session.relations(uid)
    cost = owner.SOURCE_SCOPE_ARGUMENT_WORK_PER_CHAR * len('hospital workflows.') + 1
    budget.max_work_units = budget.used + READING_BUSINESS_SCAN_PASSES * len(session.source_text(uid)) + cost - 1
    fact = session.fact(uid)
    assert fact.purpose == 'unassessed' and not session.complete
    assert session.source_assertions(uid) is None and session.source_passage(uid) is None
    used = budget.used
    assert session.fact(uid) is fact and budget.used == used


def test_explicit_passage_compat_account_reaches_its_prepared_scope(monkeypatch):
    from company_wiki.source_catalog import narrative_source_passage as owner
    from company_wiki.resource_budget import WorkBudget

    text = 'We aim to pursue luminous horizons.'
    account = WorkBudget(200000)
    original = owner.prepare_source_statement_scope
    accounts = []

    def observed(value, roles, **kwargs):
        accounts.append(kwargs.get('grammar_work_budget'))
        return original(value, roles, **kwargs)

    monkeypatch.setattr(owner, 'prepare_source_statement_scope', observed)
    owner.prepare_source_passage(text, prepare_source_assertions(text), purpose='unknown', financial_only=False,
        accounting_text=lambda value: False, non_operating_purposes=frozenset(),
        existing_use=('context_only', 'none'), existing_relevant=False, grammar_work_budget=account)
    assert accounts == [account] and account.used > 0
