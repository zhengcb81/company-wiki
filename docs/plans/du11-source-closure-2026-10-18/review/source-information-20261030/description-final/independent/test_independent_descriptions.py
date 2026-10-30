import sys
sys.path[:0]=['src','tests']
import pytest
from unit.du11_production.test_source_information_binding import session_for, unit_id, observed_use
from unit.du11_production.test_qa_closed_scopes import case, admitted_cards, FINANCIAL, GREETING

@pytest.mark.parametrize('text', (
 '流程说明：申请人收到上市审核问询函后应提交补充资料。',
 'The procedure states that the applicant received IPO review questions.',
 '模板：公司主要产品为传感器和光学材料。',
 '产品介绍模板：公司主要产品为传感器和光学材料。',
 'Product description template: our products are sensors and optical materials.',
))
def test_template_purpose_cannot_donate_real_process_or_composition_payload(text):
    session,_=session_for([text]); uid=unit_id(0)
    assert observed_use(session,uid)[0]!='support'
    assert session.source_assertions(uid).independent_payload is not True

@pytest.mark.parametrize('text', (
 'Our products are XN-7, RX-3 and HM-2.',
 '公司主要产品为XN-7，RX-3和HM-2。',
 '公司主要產品為XN-7、RX-3和HM-2。',
 'Our products are XN-7 and RX-3.',
))
def test_closed_unknown_literal_composition_does_not_require_known_product_suffix(text):
    session,_=session_for([text]); uid=unit_id(0)
    assert observed_use(session,uid)[0]=='support'
    assert session.source_text(uid)==text
    assert not any(r['activity']=='production' and r['modality']=='actual'
                   for r in session.relations(uid)['relations'])

@pytest.mark.parametrize('text', (
 '停电事件未对远星科技经营构成重大影响。',
 '停電事件未對遠星科技經營構成重大影響。',
 'The incident did not materially affect the subsidiary operations.',
 '原料成本上涨未对远星科技生产经营构成重大影响。',
 'Raw material cost increases did not materially affect the subsidiary operations.',
))
def test_operating_impact_denial_has_source_value_without_rewriting_degree(text):
    session,_=session_for([text]); uid=unit_id(0)
    assert observed_use(session,uid)[0]=='support'
    assert session.source_text(uid)==text

@pytest.mark.parametrize('finance_first',(False,True))
@pytest.mark.parametrize('text', (
 '远星科技已收到第二轮上市审核问询函。',
 '远星科技申请中止上市审核，资料更新后将申请恢复审核。',
 'The subsidiary received second-round IPO review questions from the exchange.',
))
def test_explicit_process_subject_produces_closed_actual_source_card_without_finance(text,finance_first):
    parts=[FINANCIAL,text,GREETING] if finance_first else [text,FINANCIAL,GREETING]
    _,selected=case(parts)
    cards=admitted_cards(selected)
    assert cards and any(text in members for _,members in cards)
    for card,members in cards:
        assert FINANCIAL not in members and GREETING not in members
        assert set(card.task.member_ids)==set(card.task.support_ids)|set(card.task.context_ids)
        if text in members:
            assert text in {span.raw_text for span in card.support}

@pytest.mark.parametrize('text', (
 '公司主要客户为设备制造企业。',
 'Our customers are equipment manufacturing companies.',
))
def test_customer_manufacturer_class_is_a_description_and_not_actual_manufacturing(text):
    session,_=session_for([text]); uid=unit_id(0)
    assert observed_use(session,uid)[0]=='support'
    assert not any(r['activity']=='production' and r['modality']=='actual'
                   for r in session.relations(uid)['relations'])

def test_repeated_prepared_read_does_not_charge_or_scan_again():
    text='远星科技申请中止上市审核，资料更新后将申请恢复审核。'
    session,budget=session_for([text]);uid=unit_id(0)
    assert observed_use(session,uid)[0]=='support'
    before=budget.used
    assert observed_use(session,uid)[0]=='support'
    assert budget.used==before

def test_process_rule_observation_does_not_rescan_growing_prefixes(monkeypatch):
    from company_wiki.document_understanding.operating_states import assertion_roles as roles
    original=roles._PROCESS_RULE_SUBJECT
    class Counted:
        chars=0
        def search(self,value,*args):
            self.chars+=len(value)
            return original.search(value,*args)
        def finditer(self,value,*args):
            self.chars+=len(value)
            return original.finditer(value,*args)
        def __getattr__(self,name): return getattr(original,name)
    counter=Counted()
    monkeypatch.setattr(roles,'_PROCESS_RULE_SUBJECT',counter)
    text='公司'+('申请中止上市审核 '*400)+'。'
    session,budget=session_for([text]);uid=unit_id(0)
    assert observed_use(session,uid)[0]=='support'
    assert counter.chars<=budget.used

@pytest.mark.parametrize('text', (
 '本公司软件识别模板：产品为传感器和光学材料。',
 'The software identifies the template: products are sensors and optical materials.',
))
def test_a_real_product_predicate_governs_its_template_argument(text):
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]=='support'

def test_accounting_impact_on_financial_statements_is_still_not_operating_support():
    text='所述会计政策变更未对公司的财务报表构成重大影响。'
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]!='support'
