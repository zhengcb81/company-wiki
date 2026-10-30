"""Next-node baseline only; no product edits or document/model IO."""
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
))
def test_self_contained_source_descriptions_have_independent_reading_value(text):
    session,_=session_for([text]);uid=unit_id(0)
    assert observed_use(session,uid)[0]=='support'

@pytest.mark.parametrize('text', (
    '显示器件制造企业',
    '公司主要产品为各类优质产品及全方位服务。',
    '公司主要产品是否为精密设备？',
    '公司持续遵守监管要求，规范完善信息披露。',
    '审计师已收到财务报表，并将在数据更新后恢复财务审计。',
    '所述会计政策变更未对公司的财务报表构成重大影响。',
))
def test_noun_classes_generic_rhetoric_and_accounting_are_not_operating_assertions(text):
    session,_=session_for([text]);uid=unit_id(0)
    assert observed_use(session,uid)[0]!='support'
