"""Independent counterexamples: modifiers, source offsets and actual work."""
import pytest

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.operating_states import relations as detector
from .helpers import make_observation, make_unit, run_text


@pytest.mark.parametrize('text,polarity,stage,modality', [
    ('公司未签署供货合同。', 'negative', 'current', 'actual'),
    ('公司计划签署供货合同。', 'positive', 'planned', 'planned'),
    ('公司尚未建立联系。', 'negative', 'not_yet', 'actual'),
    ('公司计划商业化新产品。', 'positive', 'planned', 'planned'),
    ('The company has not signed a supply contract.', 'negative', 'current', 'actual'),
    ('The company plans to sign a supply contract.', 'positive', 'planned', 'planned'),
    ('本公司拟交付ZX-9产品。', 'positive', 'planned', 'planned'),
    ('公司尚未正式签署供货合同。', 'negative', 'not_yet', 'actual'),
    ('公司没有与客户签署供货合同。', 'negative', 'current', 'actual'),
    ('公司并非没有签署供货合同。', 'unknown', 'unknown', 'uncertain'),
    ('The company would sign a supply contract.', 'positive', 'conditional', 'conditional'),
])
def test_qualifier_belongs_to_the_assertion_not_just_the_regex_family(text, polarity, stage, modality):
    result, units, _budget = run_text(text)
    assert result['relations']
    for relation in result['relations']:
        assert (relation['polarity'], relation['stage'], relation['modality']) == (polarity, stage, modality)
        assert relation['qualifier_refs']


@pytest.mark.parametrize('prefix', ['  ', '随后', '随后  ', '同时', '  并且'])
def test_prefix_removal_keeps_the_actual_actor_offsets(prefix):
    text = prefix+'本公司已量产X产品。'
    result, _units, _budget = run_text(text)
    assert result['relations']
    for relation in result['relations']:
        assert [text[r['char_start']:r['char_end']] for r in relation['actor_refs']] == ['本公司']
        assert relation['attribution'] == 'issuer'


def test_zero_budget_does_not_normalize_any_source_character(monkeypatch):
    observation = make_observation({'u': make_unit('甲'*5000)}, target='u')
    def forbidden(_text):
        pytest.fail('source conversion ran after the budget was already exhausted')
    monkeypatch.setattr(detector, 'build_matching_view', forbidden)
    result = detector.detect_operating_relations(observation, work_budget=WorkBudget(0))
    assert result['status'] == 'partial' and result['work_used'] == 0


def test_budget_does_not_walk_or_copy_unreferenced_units():
    class Units(dict):
        def items(self):
            pytest.fail('detector copied or validated the entire unrelated unit map')
        def __iter__(self):
            pytest.fail('detector walked the entire unrelated unit map')
    units = Units({'u': make_unit('公司未生产ZX-9产品。')})
    observation = {'schema_version':detector.OBSERVATION_SCHEMA,'unit_id':'u','units':units}
    result = detector.detect_operating_relations(observation, work_budget=WorkBudget(10000))
    assert result['relations']


def test_exhausted_budget_does_not_copy_the_context_tail():
    class Contexts(list):
        def __iter__(self):
            pytest.fail('context copied before spending any work')
    observation = {'schema_version':detector.OBSERVATION_SCHEMA,'unit_id':'u',
                   'units':{'u':make_unit('公司未生产ZX-9产品。')},
                   'context_unit_ids':Contexts(['missing']*10000)}
    result = detector.detect_operating_relations(observation, work_budget=WorkBudget(0))
    assert result['status']=='partial'


@pytest.mark.parametrize('limit', [0, 1, 20])
def test_context_proof_key_never_traverses_unpaid_tail(limit):
    class Contexts(list):
        def __iter__(self):
            pytest.fail('proof key traversed the unpaid context tail')
        def __getitem__(self, index):
            pytest.fail('context accessed before target preparation was paid')
    observation = {'schema_version':detector.OBSERVATION_SCHEMA, 'unit_id':'u',
                   'units':{'u':make_unit('公司未生产ZX-9产品。'*100)},
                   'context_unit_ids':Contexts(['missing']*10000)}
    budget = WorkBudget(limit)
    result = detector.detect_operating_relations(observation, work_budget=budget)
    assert result['status']=='partial'
    assert result['relations']==[]
    assert budget.used <= limit


def test_context_proof_key_uses_the_once_validated_order_for_all_relations():
    class Contexts(list):
        reads = 0
        def __iter__(self):
            pytest.fail('validated contexts must not be traversed again')
        def __getitem__(self, index):
            self.reads += 1
            return super().__getitem__(index)
    contexts = Contexts(['b', 'a'])
    units = {'u':make_unit('本公司已交付ZX-9产品。本公司的设备已完成客户认证。'),
             'a':make_unit('本公司从事设备制造。'), 'b':make_unit('本公司制造新型设备。')}
    session = detector.OperatingRelationSession(units, work_budget=WorkBudget(100000))
    result = detector._detect_operating_relations(
        {'schema_version':detector.OBSERVATION_SCHEMA, 'unit_id':'u',
         'units':units, 'context_unit_ids':contexts},
        work_budget=session.work_budget, prepared=session)
    assert result['status']=='complete' and len(result['relations']) >= 2
    assert contexts.reads == 2
    assert len(session.relation_bindings('u', ('b', 'a'))) == len(result['relations'])
    assert not session.relation_bindings('u', ('a', 'b'))


def test_context_identity_work_does_not_multiply_with_relation_count():
    class CountedId(str):
        hashes = 0
        def __hash__(self):
            self.__class__.hashes += 1
            return super().__hash__()

    counts = []
    for relation_count in (1, 20):
        contexts = tuple(CountedId(f'c{i}') for i in range(100))
        units = {'u':make_unit('公司已交付ZX-9产品。'*relation_count),
                 **{str(uid):make_unit('') for uid in contexts}}
        session = detector.OperatingRelationSession(units, work_budget=WorkBudget(100000))
        CountedId.hashes = 0
        result = session.detect('u', contexts)
        assert result['status']=='complete'
        assert len(result['relations'])==relation_count
        counts.append(CountedId.hashes)
    # Cache identity depends on this source scope, not on how many operating
    # predicates it contains. Counting work avoids a machine-dependent timer.
    assert counts[1] == counts[0]


def test_prepared_target_stops_mid_context_before_an_unpaid_index_read():
    class Contexts(list):
        reads = 0
        def __iter__(self):
            pytest.fail('context source must be consumed by charged indexes')
        def __getitem__(self, index):
            self.reads += 1
            return super().__getitem__(index)

    text = '公司已交付ZX-9产品。'
    contexts = Contexts([f'missing-{i}' for i in range(10000)])
    budget = WorkBudget(1 + len(text) + 2)
    units = {'u':make_unit(text)}
    session = detector.OperatingRelationSession(units, work_budget=budget)
    session.matching_text('u')
    assert budget.used == 1 + len(text)
    result = detector._detect_operating_relations(
        {'schema_version':detector.OBSERVATION_SCHEMA, 'unit_id':'u',
         'units':units, 'context_unit_ids':contexts}, work_budget=budget, prepared=session)
    assert result['status']=='partial' and result['relations']==[]
    assert contexts.reads == 2
    assert budget.used == budget.max_work_units
    assert result['diagnostics'][-1]['code']=='work_budget_exhausted'


def test_conditional_qualification_cannot_be_overwritten_by_result_construction():
    text='如果客户验证通过，公司将交付ZX-9产品。'
    result, _units, _budget=run_text(text)
    qualification=[r for r in result['relations'] if r['activity']=='qualification']
    assert qualification
    assert qualification[0]['stage']=='conditional'
    assert qualification[0]['modality']=='conditional'
    assert all(text[r['char_start']:r['char_end']]!='如果' for r in qualification[0]['actor_refs'])


def test_attributive_vendor_qualification_cannot_become_an_issuer_assertion():
    text='我们已与未获认证的供应商签署供货合同。'
    result, _units, _budget=run_text(text)
    qualification=[r for r in result['relations'] if r['activity']=='qualification']
    assert all(r['attribution']!='issuer' for r in qualification)
    assert all(r['object_refs']==[] for r in qualification)
    signed=[r for r in result['relations'] if r['activity']=='business_relationship']
    assert signed
    assert [text[r['char_start']:r['char_end']] for r in signed[0]['actor_refs']]==['我们']


def test_control_verb_binds_the_following_product_not_the_preceding_actor():
    text='公司计划停止生产X产品。'
    result, _units, _budget=run_text(text)
    assert result['relations']
    relation=result['relations'][0]
    assert relation['modality']=='planned'
    assert [text[r['char_start']:r['char_end']] for r in relation['object_refs']]==['X产品']
