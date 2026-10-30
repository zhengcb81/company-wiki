"""Self-contained descriptions/processes: no donated stage, entity or values."""
import pytest
from unit.du11_production.test_source_information_binding import session_for, unit_id, observed_use

@pytest.mark.parametrize('text', (
    '公司主要产品为精密设备、传感器和光学材料。',
    '澜芯材料主要产品为精密设备、传感器和光学材料。',
    '公司主要產品為精密設備、感測器和光學材料。',
    'Our main products are precision equipment, sensors and optical materials.',
    '目前公司在精密材料领域已销售的产品主要为催化剂、聚合物和光学材料，现已开发超300种化合物。',
    '澜芯材料主要产品为显示材料，下游客户为显示材料生产企业，显示材料生产企业的下游为面板生产企业。',
    '澜芯材料已收到交易所第二轮上市审核问询函，因前期报送的财务数据过期申请中止审核，待资料更新后将申请恢复审核。',
    '澜芯材料已收到交易所第二轮上市审核问询函，因资料有效期已过申请中止审核，待资料更新后将申请恢复审核。',
    '据报道，所述事项未对澜芯材料经营构成重大影响。',
    '公司已收到交易所上市审核问询函，待补充资料后将回复问询。',
    'The subsidiary received second-round IPO review questions from the exchange.',
    'The subsidiary applied to suspend the listing review pending revised financial statements.',
))
def test_self_contained_source_descriptions_have_independent_reading_value(text):
    session,_=session_for([text])
    uid=unit_id(0)
    assert observed_use(session,uid)[0]=='support'

@pytest.mark.parametrize('text', (
    '显示器件制造企业',
    '公司主要产品为各类优质产品及全方位服务。',
    '公司主营业务包括多类产品和配套解决方案。',
    '公司主營業務包括多類產品和配套解決方案。',
    'Our main business includes multiple types of products and complementary solutions.',
    '公司主要产品是否为精密设备？',
    '公司持续遵守监管要求，规范完善信息披露。',
    '审计师已收到财务报表，并将在数据更新后恢复财务审计。',
    '所述会计政策变更未对公司的财务报表构成重大影响。',
    '设备制造企业',
    'equipment manufacturing companies',
    '公司主要产品为收入和利润。',
    '公司主要产品为现金流及营运资金。',
    'Our main products are various high-quality products and comprehensive services.',
    '主要产品：设备、传感器及材料',
    '上市审核中止申请表模板',
    '申请中止上市审核的流程说明',
    'The procedure to apply to suspend a listing review is described below.',
    '公司收到审计问询函，拟更新财务报表。',
))
def test_noun_classes_generic_rhetoric_and_accounting_are_not_operating_assertions(text):
    session,_=session_for([text])
    uid=unit_id(0)
    assert observed_use(session,uid)[0]!='support'

@pytest.mark.parametrize('text', (
    'Our products include Cash Flow Management Software and Sensor Analytics Software.',
    '本公司提供企业级软件，用于实时处理客户订单。',
))
def test_true_software_offerings_are_not_accounting_or_agent_nominalizations(text):
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]=='support'

@pytest.mark.parametrize('text', (
    '澜芯材料主要产品为精密设备、传感器和光学材料。',
    '澜芯材料下游客户为显示材料生产企业，该类企业下游主要为面板生产企业。',
    '澜芯材料已收到第二轮上市审核问询函，因资料过期申请中止审核，待更新后将申请恢复审核。',
))
def test_descriptive_subject_does_not_become_issuer_production_or_completed_listing(text):
    session,_=session_for([text])
    uid=unit_id(0)
    observed_use(session,uid)
    relations=session.relations(uid)['relations']
    assert not any(r['activity']=='production' and r['stage'] in {'current','completed','suspended'}
                   and r['attribution']=='issuer' for r in relations)

@pytest.mark.parametrize('name', ('澜芯材料','辰枫科技'))
@pytest.mark.parametrize('finance_first', (False,True))
def test_named_subject_description_is_a_closed_actual_task_without_financial_donation(name,finance_first):
    from unit.du11_production.test_qa_closed_scopes import case,admitted_cards,FINANCIAL,GREETING
    roster=name+'主要产品为精密设备、传感器和光学材料。'
    parts=[FINANCIAL,roster,GREETING] if finance_first else [roster,FINANCIAL,GREETING]
    _,selected=case(parts)
    cards=admitted_cards(selected)
    assert cards and any(roster in members for _,members in cards)
    assert all(FINANCIAL not in members and GREETING not in members for _,members in cards)

@pytest.mark.parametrize('text', (
    '流程说明：申请人收到上市审核问询函后应提交补充资料。',
    '申请人收到上市审核问询函后应提交补充资料。',
    'The procedure states that the applicant received IPO review questions.',
    '模板：公司主要产品为传感器和光学材料。',
    'Template: Our products are sensors and optical materials.',
    '产品介绍模板：公司主要产品为传感器和光学材料。',
    'Product description template: our products are sensors and optical materials.',
))
def test_procedural_examples_are_not_source_updates(text):
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]!='support'

@pytest.mark.parametrize('text', (
    'Our products are XN-7, RX-3 and HM-2.',
    'Our products are XN-7 and RX-3.',
    'The incident did not materially affect the subsidiary operations.',
    '公司已收到上市审核问询函后应尽快回复。',
    '原料成本上涨未对远星科技生产经营构成重大影响。',
    'Higher raw material costs did not materially affect the subsidiary operations.',
))
def test_closed_source_enumeration_and_impact_are_language_independent(text):
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]=='support'

@pytest.mark.parametrize('text', (
    '远星科技已收到第二轮上市审核问询函。',
    '远星科技因更新资料申请中止上市审核。',
    '所述事件未对远星科技经营构成重大影响。',
    'The incident did not materially affect the subsidiary operations.',
))
@pytest.mark.parametrize('finance_first', (False,True))
def test_every_description_family_closes_actual_tasks(text,finance_first):
    from unit.du11_production.test_qa_closed_scopes import case,admitted_cards,FINANCIAL,GREETING
    parts=[FINANCIAL,text,GREETING] if finance_first else [text,FINANCIAL,GREETING]
    _,selected=case(parts)
    cards=admitted_cards(selected)
    assert cards and any(text in members for _,members in cards)
    assert all(FINANCIAL not in members and GREETING not in members for _,members in cards)

def test_repeated_process_steps_do_not_rescan_growing_prefixes(monkeypatch):
    from company_wiki.document_understanding.operating_states import assertion_roles as roles
    original=roles._PROCESS_RULE_SUBJECT
    class ObservedRule:
        chars=0
        def search(self,value,*args):
            self.chars+=len(value)
            return original.search(value,*args)
    measurements=[]
    for repeats in (100,200):
        observer=ObservedRule()
        monkeypatch.setattr(roles,'_PROCESS_RULE_SUBJECT',observer)
        text='公司'+('申请中止上市审核 '*repeats)+'。'
        session,budget=session_for([text])
        assert observed_use(session,unit_id(0))[0]=='support'
        assert observer.chars <= budget.used
        measurements.append(observer.chars)
    assert measurements[1] <= 2.1*max(1,measurements[0])

def test_explicit_future_subject_does_not_borrow_previous_business_support():
    from unit.du11_production.test_qa_closed_scopes import case,admitted_cards
    business='公司已量产精密设备，全年交付300台。'
    rhetoric='未来公司也会努力在电子信息材料产业、环保材料产业、新能源材料产业、生命科学与医药产业四大领域向国内市场提供更多优质产品。'
    actual_plan='未来公司计划建设新的服务平台。'
    _,selected=case([business,rhetoric,actual_plan])
    cards=admitted_cards(selected)
    assert any(business in members for _,members in cards)
    assert any(actual_plan in members for _,members in cards)
    assert all(rhetoric not in members for _,members in cards)

@pytest.mark.parametrize('text', (
    '公司提供的软件识别流程说明：申请人收到上市审核问询函后应提交补充资料。',
    'Our software identifies the procedure described below: the applicant received IPO review questions.',
))
def test_product_that_actually_processes_procedural_text_keeps_its_function(text):
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]=='support'

@pytest.mark.parametrize('text', (
    '公司主要产品为精密设备、传感器和光学材料。',
    '公司主要产品为XN-7和QR-4。',
    '公司主营业务是指高端装备研发、生产和销售。',
))
def test_compatibility_event_policy_does_not_implicitly_opt_in_source_rosters(text):
    from company_wiki.source_catalog.narrative_business_groups import _operating_fact
    session,_=session_for([text])
    assert observed_use(session,unit_id(0))[0]=='support'
    assert not _operating_fact(text).eligible

@pytest.mark.parametrize('text', (
    'Our paid seats increased to 3 million.',
    'Our service revenue is based on actual customer usage.',
    '本公司提供企业级软件，用于实时处理客户订单。',
))
def test_compatibility_keeps_independent_measures_billing_and_functions(text):
    from company_wiki.source_catalog.narrative_business_groups import _operating_fact
    assert _operating_fact(text).eligible
