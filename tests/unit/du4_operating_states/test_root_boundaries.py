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
