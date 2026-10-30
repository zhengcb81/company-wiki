import sys
sys.path[:0] = ['src', 'tests']
import pytest
from unit.du11_production.test_source_information_binding import session_for, unit_id, observed_use
from company_wiki.source_catalog.narrative_support_use import source_narrative_relevance

@pytest.mark.parametrize('text', (
    'We do not manufacture EBITDA.',
    'We do not manufacture Cash Flow.',
    'We do not manufacture Working Capital.',
    '本公司现无生产EBITDA的情况。',
    'We do not manufacture Efficiency.',
    'We do not manufacture Happiness.',
    'We do not manufacture ROI.',
    '我们研究客户是否已生产QX-7。',
    'We considered whether our suppliers currently manufacture KZ-4.',
))
def test_nonoperating_or_unasserted_propositions_never_get_proof(text):
    session, _ = session_for([text])
    uid = unit_id(0)
    use = observed_use(session, uid)
    assert not any(session.engine.relation_bindings(uid))
    assert use[0] != 'support'
    if '是否' in text or 'whether' in text:
        assert not any(r['modality'] == 'actual' and r['polarity'] == 'positive'
                       for r in session.relations(uid)['relations'])

@pytest.mark.parametrize('text', (
    '本公司收入下降，并非因为下游需求减少。',
    '本公司收入增长，并非因为客户需求增加。',
))
def test_explicitly_denied_cause_never_becomes_actual_causal_driver(text):
    session, _ = session_for([text])
    assert 'operating_causal_driver' not in session.fact(unit_id(0)).reasons

def test_denial_of_proposition_never_becomes_positive_actual_manufacturing():
    session, _ = session_for(['公司否认已经生产QX-7。'])
    uid = unit_id(0)
    observed_use(session, uid)
    relations = session.relations(uid)['relations']
    assert not any(r['activity'] == 'production' and r['polarity'] == 'positive'
                   and r['modality'] == 'actual' and r['attribution'] == 'issuer'
                   for r in relations)

@pytest.mark.parametrize('text', (
    '本公司目前不生产六氟环氧丙烷。',
    'We currently manufacture qx-7.',
    '本公司现无生产QX-7（甲基环氧乙烷）的情况。',
    'We currently manufacture KZ-4.',
))
def test_unknown_manufacturing_argument_is_readable_without_payload_qualification(text):
    session, _ = session_for([text])
    uid = unit_id(0)
    use = observed_use(session, uid)
    assert use[0] == 'unresolved'
    assert not any(session.engine.relation_bindings(uid))
    assert session.engine.unknown_argument(uid)
    assert session.source_assertions(uid).independent_payload is None
    assert source_narrative_relevance(fact=session.fact(uid), source_roles=session.source_assertions(uid))
    assert session.source_text(uid) == text
    assert all(r['object_refs'] for r in session.relations(uid)['relations'])
    before = session.work_budget.used
    assert session.engine.unknown_argument(uid)
    assert observed_use(session, uid)[0] == 'unresolved'
    assert session.work_budget.used == before

@pytest.mark.parametrize('text', (
    '本公司现无生产QX-7材料的情况。',
    'We currently manufacture sensor devices.',
    '本公司本期催化材料业务收入下降，主要由于下游需求减少。',
    'Our sensor revenue declined due to lower customer demand.',
))
def test_positive_controls_cache_and_exact_refs(text):
    session, budget = session_for([text])
    uid = unit_id(0)
    assert observed_use(session, uid)[0] == 'support'
    result = session.relations(uid)
    for relation in result['relations']:
        for key in ('actor_refs','object_refs','predicate_refs','qualifier_refs','assertion_refs'):
            for ref in relation[key]:
                assert ref['unit_id'] == uid
                assert 0 <= ref['char_start'] < ref['char_end'] <= len(text)
                assert text[ref['char_start']:ref['char_end']]
    before = budget.used
    assert observed_use(session, uid)[0] == 'support'
    assert budget.used == before

def test_financial_software_table_keeps_actual_offering_row():
    from company_wiki.document_understanding.structure.table_purpose import qualify_table
    assert qualify_table(['Product', 'Customers'], ['Cash Flow Management Software 100']).eligible

def test_financial_software_governing_head_stays_support():
    text = 'We currently manufacture cash flow management software.'
    session, _ = session_for([text])
    assert observed_use(session, unit_id(0))[0] == 'support'

def test_unclosed_argument_does_not_become_cached_complete_unknown():
    session, _ = session_for(['公司未生产qx-7（未闭合'])
    uid = unit_id(0)
    assert observed_use(session, uid)[0] != 'support'
    assert not session.engine.unknown_argument(uid)

def test_unknown_argument_reaches_actual_native_reading_selection_unresolved():
    from unit.document_understanding_selection.test_reading_native_carriers import source_fixture
    from company_wiki.source_catalog.narrative_reading import select_reading_evidence
    text = '本公司目前不生产六氟环氧丙烷。'
    parsed, _ = source_fixture([(text,)])
    selected = select_reading_evidence(parsed, title='业务进展', existing_kind='annual_report')
    assert text in {span.raw_text for span in selected.evidence_spans}
    views = [v for g in selected.reading_context['groups'] for v in g['citation_views']]
    assert views and all(v['reading_support_use'] == 'unresolved' for v in views)

def test_existing_known_participants_keep_actual_contact_support():
    text = '公司与客户已经建立了联系。'
    session, _ = session_for([text])
    uid = unit_id(0)
    assert observed_use(session, uid)[0] == 'support'
    assert any(session.engine.relation_bindings(uid))
    relations = session.relations(uid)['relations']
    assert any(r['stage'] == 'contact_established' and r['modality'] == 'actual' for r in relations)
    assert not any(r['stage'] == 'signed' for r in relations)
