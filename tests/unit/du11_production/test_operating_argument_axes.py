"""A source predicate binds arguments without an industry/company dictionary."""
import pytest

from unit.du11_production.test_source_information_binding import session_for, unit_id, observed_use
from company_wiki.source_catalog.narrative_support_use import source_narrative_relevance


@pytest.mark.parametrize('text', (
    '本公司现无生产QX-7（甲基环氧乙烷）的情况。',
    '本公司目前不生产TY-8（乙基硅烷）。',
    '公司尚未生产PX-3。',
    '本公司目前不生产六氟环氧丙烷。',
    '公司未生产qx-7。',
    'We do not manufacture KZ-4.',
    'We currently manufacture qx-7.',
    'The supplier does not manufacture KZ-4.',
))
def test_explicit_manufacturing_argument_does_not_need_a_known_product_suffix(text):
    session, _ = session_for([text])
    uid = unit_id(0)
    assert observed_use(session, uid)[0] == 'unresolved'
    assert source_narrative_relevance(fact=session.fact(uid), source_roles=session.source_assertions(uid))
    result = session.relations(uid)
    bound = session.engine.relation_bindings(uid)
    assert not any(bound)
    assert session.engine.unknown_argument(uid)
    relations = result['relations']
    if 'currently manufacture qx' not in text:
        assert all(r['polarity'] == 'negative' for r in relations)
    assert all(r['object_refs'] for r in relations)
    for relation in relations:
        for ref in relation['object_refs']:
            assert text[ref['char_start']:ref['char_end']]
        if text.startswith('The supplier'):
            assert relation['attribution'] != 'issuer'


@pytest.mark.parametrize('text', (
    '本公司现无生产人民币收入的情况。',
    'We do not produce financial statements.',
    'We do not manufacture EBITDA.',
    'We do not manufacture Cash Flow.',
    'We do not manufacture Working Capital.',
    'We do not manufacture ROI.',
    'We do not manufacture Efficiency.',
    'We do not manufacture Happiness.',
    '本公司现无生产EBITDA的情况。',
    'The company does not manufacture growth.',
    '公司未生产2025。',
    '公司未生产经营风险。',
    '公司是否已经生产QX-7？',
    '我们讨论客户是否已生产QX-7。',
    'We discussed whether our suppliers manufacture KZ-4.',
    '我们研究客户是否已生产QX-7。',
    'We considered whether our suppliers currently manufacture KZ-4.',
    '公司未生产QX-7（' + '未知名称' * 20 + '）。',
))
def test_financial_abstract_numeric_question_and_unclosed_arguments_are_not_qualified(text):
    session, _ = session_for([text])
    uid = unit_id(0)
    assert observed_use(session, uid)[0] != 'support'
    assert not any(session.engine.relation_bindings(uid))


def test_known_related_party_can_contact_a_named_party_without_resolving_its_entity_type():
    text = ('根据控股股东海岸集团信息，海岸集团与星河科技已经建立了联系，'
            '并希望建立业务协同与合作。')
    session, _ = session_for([text])
    uid = unit_id(0)
    assert observed_use(session, uid)[0] == 'support'
    result = session.relations(uid)['relations']
    contact = [r for r in result if r['stage'] == 'contact_established']
    assert contact and all(r['attribution'] == 'quoted_related_party' for r in contact)
    assert not any(r['stage'] == 'signed' for r in result)


def test_contact_without_a_counterparty_does_not_get_a_relationship_proof():
    session, _ = session_for(['本公司已经建立了联系。'])
    assert observed_use(session, unit_id(0))[0] != 'support'


@pytest.mark.parametrize('text', (
    '公司否认已经生产QX-7。',
    'The company denied that it currently manufactures qx-7.',
))
def test_denial_of_a_proposition_is_not_an_actual_positive_issuer_event(text):
    session, _ = session_for([text])
    result = session.relations(unit_id(0))
    assert result['relations']
    assert all(r['modality'] == 'uncertain' and r['polarity'] == 'unknown'
               for r in result['relations'])
    for relation in result['relations']:
        actors = [text[r['char_start']:r['char_end']] for r in relation['actor_refs']]
        assert not any('否认' in actor or 'denied' in actor for actor in actors)
        assert relation['qualifier_refs']


def test_unknown_argument_can_be_selected_for_reading_without_becoming_qualified_payload():
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence
    text = '本公司现无生产QX-7（甲基环氧乙烷）的情况。'
    parsed, _ = source_fixture([(text,)])
    selected = select_reading_evidence(parsed, title='业务进展', existing_kind='annual_report')
    assert text in {span.raw_text for span in selected.evidence_spans}
    views = [view for group in selected.reading_context['groups'] for view in group['citation_views']]
    assert views and all(view['reading_support_use'] == 'unresolved' for view in views)

