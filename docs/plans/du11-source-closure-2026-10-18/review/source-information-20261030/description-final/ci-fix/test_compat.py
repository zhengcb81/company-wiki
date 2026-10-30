import sys
sys.path[:0]=['src','tests']
import pytest
from unit.test_narrative_evidence import _source, _unit
from company_wiki.source_catalog.narrative_evidence import NarrativeParseResult, select_narrative_evidence
from company_wiki.source_catalog.narrative_business_groups import _operating_fact
from unit.du11_production.test_source_information_binding import session_for,unit_id,observed_use

def selected_legacy(text):
    sid,sha=_source('ci-independent:'+text)
    unit=_unit(text,source_id=sid)
    parsed=NarrativeParseResult(sid,sha,'zh',(unit,),page_count=1,pages_read=1)
    return select_narrative_evidence(parsed,title='年报.pdf')

@pytest.mark.parametrize('text',(
 '公司主营业务包括高端装备研发、生产和销售，持续关注行业发展。',
 '公司主营业务包括多类产品和配套解决方案。',
 '公司主营业务是指高端装备研发、生产和销售，海外市场是公司未来的发展方向。',
))
def test_original_static_boundaries_remain_unselected_in_default_legacy(text):
    assert not _operating_fact(text).eligible
    result=selected_legacy(text)
    assert result.evidence_spans==()
    assert result.status=='needs_review'

@pytest.mark.parametrize('text',(
 'Our paid seats increased to 3 million.',
 'Our service revenue is based on actual customer usage.',
))
def test_existing_quantified_and_billing_proofs_do_not_need_raw_material_roles(text):
    assert _operating_fact(text).eligible
    assert text in {s.raw_text for s in selected_legacy(text).evidence_spans}

def test_concrete_new_composition_keeps_reading_value_without_legacy_injection():
    text='Our main products are XN-7 and RX-3.'
    assert not _operating_fact(text).eligible
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]=='support'

def test_generic_composition_modifiers_are_not_independent_reading_payload():
    text='公司主营业务包括多类产品和配套解决方案。'
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]!='support'
    assert session.source_assertions(unit_id(0)).independent_payload is not True

def test_existing_true_function_event_still_has_legacy_value():
    text='公司设备已完成客户认证。'
    assert _operating_fact(text).eligible
    assert text in {s.raw_text for s in selected_legacy(text).evidence_spans}

def test_unknown_singleton_description_is_not_legacy_event_payload():
    text='公司主要产品为XN-7。'
    assert not _operating_fact(text).eligible
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]=='unresolved'
    assert session.source_assertions(unit_id(0)).independent_payload is None
