"""Neutral prefix boundaries and financial/operating causal payloads."""
import pytest
from copy import deepcopy

from unit.du11_production.test_source_passage_admission import assessed


@pytest.mark.parametrize('text', (
    '是否已经批量交付？目前尚未量产，公司仍在客户验证阶段。',
    'Has Elarin completed validation? Our new device has completed customer validation.',
    'Thank you. Our new device has completed customer validation.',
    '谢谢您的提问。星渊新装置已经完成客户验证。',
    'What is the current stage? Thank you. Our new device has completed validation.',
))
def test_closed_prefix_allows_only_the_later_statement(text):
    session, _, uid, _, passage = assessed(text)
    assert passage.use == 'support' and passage.relevant, passage
    assert session.source_text(uid) == text


@pytest.mark.parametrize('text', (
    'Did Elarin complete customer validation? Net income was $20 million.',
    '新装置是否已经完成客户验证？净利润为200万元。',
    'Our device has completed validation. Is that correct?',
    'Has the device completed validation, our software has processed orders; is that correct?',
    'What is the current stage? Thank you for the question.',
    'Thank you. Net income was $20 million.',
    '是否已经完成客户验证？',
    'Thank you for your question.',
    'Question: Elarin owns two utilities. Net income was $20 million.',
    'Thank you for explaining that our device has completed customer validation.',
    'Thank you. Net income was $20 million. Has the device completed validation? Revenue was $40 million.',
    '谢谢。净利润为200万元。新装置是否已经完成客户验证？营业收入为400万元。',
    'Thank you. Template: Elarin owns two utilities.',
))
def test_prefix_claims_do_not_donate_proof_to_finance_or_courtesy(text):
    _, _, _, _, passage = assessed(text)
    assert passage.use != 'support' and not passage.relevant, passage


@pytest.mark.parametrize('text', (
    '星渊毛利率表现主要得益于客户结构和产品结构的调整以及精益生产措施的推进。',
    'Gross margin improved reflecting a change in customer mix and lean manufacturing.',
    '星渊毛利率主要原因是客户结构的调整。',
    '星渊毛利率受工厂运营效率提高带动。',
))
def test_shared_causal_grammar_admits_business_explanation(text):
    session, _, uid, _, passage = assessed(text)
    assert passage.use == 'support' and passage.relevant, passage
    assert session.source_text(uid) == text


@pytest.mark.parametrize('text', (
    '净利润增加主要得益于所得税费用下降。',
    'Net income increased reflecting lower tax expense.',
    '毛利率提高主要原因是折旧费用减少。',
    'Gross margin increased due to lower depreciation expense.',
    'Accounting rules require gross margin to reflect adjusted depreciation.',
))
def test_shared_causal_grammar_keeps_pure_accounting_context(text):
    _, _, _, _, passage = assessed(text)
    assert passage.use != 'support' and not passage.relevant, passage


@pytest.mark.parametrize('text', (
    'Net income was $20 million. Did the plant complete customer validation? Gross margin was 20%.',
    'Net income was $20 million. Thank you for confirming our new device has completed validation.',
    '净利润为200万元。新装置是否已经完成客户验证？毛利率为20%。',
    '净利润为200万元。感谢您确认公司新装置已经完成客户验证。',
    'Did the plant complete customer validation? Net income was $20 million.',
    'Thank you for confirming our new device has completed validation. Net income was $20 million.',
    '净利润为200万元。 是否已经完成客户验证。',
    '淨利潤為200萬元。 感謝您確認公司新裝置已經完成客戶驗證。',
))
def test_nonassertions_at_any_position_cannot_manufacture_operating_fact(text):
    session, budget, uid, fact, passage = assessed(text)
    assert not fact.eligible and not fact.financial_exempt, fact
    assert not session.source_assertions(uid).operating
    assert passage.use != 'support' and not passage.relevant, passage
    assert session.source_text(uid) == text
    used = budget.used
    assert session.fact(uid) is fact
    assert session.source_passage(uid) is passage
    assert budget.used == used


@pytest.mark.parametrize('text', (
    'Net income was $20 million. Our new device has completed validation.',
    'Net income was $20 million. Did the plant complete validation? Our software processes customer orders.',
    'Our software processes customer orders. Did the plant complete validation? Net income was $20 million.',
    '净利润为200万元。新装置是否完成客户验证？公司软件处理客户订单。',
    '公司软件处理客户订单。感谢您确认新装置已经完成客户验证。净利润为200万元。',
))
def test_real_business_statement_keeps_its_own_proof_around_nonassertions(text):
    session, _, uid, fact, passage = assessed(text)
    assert fact.eligible, fact
    assert passage.use == 'support' and passage.relevant, passage
    assert session.source_text(uid) == text


def test_shared_statement_scope_is_prepared_once_and_keeps_original_relation_refs(monkeypatch):
    from company_wiki.source_catalog import narrative_business_policy as policy
    from company_wiki.source_catalog import narrative_source_passage as passage_owner
    from unit.du11_production.test_source_information_binding import session_for, unit_id

    original = passage_owner.prepare_source_statement_scope
    calls = []

    def observe(text, roles, **kwargs):
        result = original(text, roles, **kwargs)
        calls.append(result)
        assert len(result.text) == len(text)
        return result

    monkeypatch.setattr(policy, 'prepare_source_statement_scope', observe)
    monkeypatch.setattr(passage_owner, 'prepare_source_statement_scope', observe)
    text = ('Net income was $20 million. Thank you for confirming our new device has completed validation. '
            'Our new equipment has not completed customer validation.')
    session, _ = session_for([text])
    uid = unit_id(0)
    before = deepcopy(session.relations(uid))
    fact = session.fact(uid)
    assert fact.eligible
    assert session.source_passage(uid).use == 'support'
    assert session.source_text(uid) == text
    assert session.relations(uid) == before
    assert len(calls) == 1


def test_statement_mask_preserves_original_length_despite_wrapping_and_script_matching():
    from company_wiki.document_understanding.operating_states.assertion_roles import prepare_source_assertions
    from company_wiki.source_catalog.narrative_source_passage import prepare_source_statement_scope

    text = '淨利潤為200萬元。感謝您確認新裝置已經完成客戶驗證。\r\n公司軟體處理客\n戶訂單。'
    scope = prepare_source_statement_scope(text, prepare_source_assertions(text))
    assert len(scope.text) == len(text)
    tail = text.index('公司軟體')
    assert scope.text[tail:] == text[tail:]
    assert all('感' not in clause.text for clause in scope.roles.clauses)
    assert any('订单' in clause.text for clause in scope.roles.clauses)


@pytest.mark.parametrize('text', (
    '净利润为200万元。公司软件处理客户订单。新装置是否完成客户验证？',
    'Our software processes invoices. Did the separate plant complete validation?',
))
def test_unrelated_trailing_question_cannot_erase_an_independent_statement(text):
    session, _, uid, fact, passage = assessed(text)
    assert fact.eligible
    assert passage.use == 'support' and passage.relevant
    assert session.source_text(uid) == text


@pytest.mark.parametrize('text', (
    'Our device has completed validation. Is that correct?',
    '公司新装置已经完成客户验证。请确认上述说法是否属实？',
    'Operating income rose 8%. New devices are discussed in another chapter.',
    'Operating income rose 8% because of excellent financial performance.',
    'Operating income rose 8% due to delighted customers and our product philosophy.',
    'A metered service is defined as a usage contract.',
))
def test_confirmation_metatext_and_nominal_benefits_are_not_independent_business_proof(text):
    _, _, _, _, passage = assessed(text)
    assert passage.use != 'support' and not passage.relevant


@pytest.mark.parametrize('text', (
    'Gross margin improved because of a scheduled meeting.',
    'Operating income rose because of unrelated wording.',
    'Gross margin increased because of improved financial performance.',
    'Gross margin increased because of changes in financial results.',
))
def test_cause_requires_operating_argument_and_process_not_word_morphology(text):
    _, _, _, fact, passage = assessed(text)
    assert not fact.eligible and not fact.financial_exempt, fact
    assert passage.use != 'support' and not passage.relevant, passage


@pytest.mark.parametrize('separator', ('; ', '. ', '；'))
def test_metatext_boundary_preserves_following_independent_validation_statement(separator):
    text = 'Our new equipment is described in section 3' + separator + 'it has completed customer validation.'
    session, _, uid, _, passage = assessed(text)
    assert passage.use == 'support' and passage.relevant
    assert session.source_text(uid) == text


@pytest.mark.parametrize('text', (
    'Our services revenue increased due to 317 new customers.',
    'Our reagent revenue grew because downstream demand increased.',
    '平台服务收入增长主要由客户数量同比增加带动。',
    '本期毛利率下降主要是由于服务器成本增加，以支持AI业务扩张。',
))
def test_source_owned_causal_proof_precedes_generic_quote_fallback(text):
    session, _, uid, fact, passage = assessed(text)
    assert 'operating_causal_driver' in fact.reasons
    assert passage.use == 'support' and passage.relevant
    assert session.source_text(uid) == text


def test_authoritative_cause_is_observed_once_in_its_canonical_clause_view(monkeypatch):
    from company_wiki.source_catalog import narrative_business_policy as policy
    real = policy._operating_causal_relation
    calls = []

    def observe(clause):
        calls.append(clause)
        return real(clause)

    monkeypatch.setattr(policy, '_operating_causal_relation', observe)
    text = 'Our services revenue increased due to higher active customer count.'
    _, _, _, fact, passage = assessed(text)
    assert 'operating_causal_driver' in fact.reasons
    assert passage.use == 'support'
    assert calls == [text[:-1]]
