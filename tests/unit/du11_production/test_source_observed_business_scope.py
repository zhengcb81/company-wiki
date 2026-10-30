"""Source-owned material scope, without inventing a dynamic operating event."""
import pytest

from company_wiki.document_understanding.operating_states.assertion_roles import prepare_source_assertions
from company_wiki.source_catalog.narrative_business_disclosures import reading_material_value
from unit.du11_production.test_source_information_binding import session_for, unit_id


@pytest.mark.parametrize("text", (
    "公司目前已销售的产品主要为甲素、乙素及丙素，现已开发了超300种相关化合物。",
    "本公司的下游客户主要为制剂生产商和检测机构。",
    "光学材料的下游客户主要为器件制造商和终端显示厂商。",
    "Our customers include hospitals and independent laboratories.",
    "本公司已开发超过80种检测试剂。",
    "现已开发了超300种相关化合物。",
    "We have developed over 80 diagnostic assays.",
    "Our company currently sells sterile tools and diagnostic cartridges.",
    "Our software provides accounting policy management tools.",
    "Our software identifies accounting policies and automates compliance.",
    "We have developed over 80 accounting policy management software products.",
))
def test_closed_observed_scope_is_material_without_requiring_growth(text):
    session, _ = session_for([text])
    roles = session.source_assertions(unit_id(0))
    assert roles.independent_payload is True
    assert not roles.descriptive_only
    assert reading_material_value(session.fact(unit_id(0)), source_roles=roles) == "meaningful_fact"


@pytest.mark.parametrize("text", (
    "产品包括高质量的产品和优质服务。",
    "公司未来将开发更多产品促进高质量发展。",
    "销售管理流程规定产品主要为甲素和乙素时如何填表。",
    "公司的目标客户包括医院和独立实验室。",
    "Our target customers include hospitals and independent laboratories.",
    "Our future major customers include hospitals and laboratories.",
    "本公司的未来主要客户包括医院和实验室。",
    "Our products include rich and complementary services.",
    "本公司已开发80项会计政策。",
    "We have developed over 80 accounting policies.",
    "The template says: we have developed over 80 diagnostic assays.",
    "流程要求：公司已开发超过80种检测试剂时应填报本表。",
    "模板示例：客户包括医院和实验室。",
    "填报示例：公司已销售的产品主要为试剂和耗材。",
    "公司利润包括投资收益和汇兑收益。",
    "请问公司已开发多少种相关化合物？",
))
def test_templates_targets_and_financial_background_do_not_gain_observed_scope(text):
    roles = prepare_source_assertions(text)
    assert not any(clause.material_payload for clause in roles.clauses)


def test_static_customer_scope_does_not_become_manufacturing_event():
    roles = prepare_source_assertions("光学材料的下游客户主要为器件制造商和终端显示厂商。")
    assert not roles.descriptive_only
    assert not any(clause.function_or_event for clause in roles.clauses)


def test_real_multilevel_chain_and_developed_count_have_separate_scope():
    chain = ("九目化学主要产品为 OLED升华前材料，下游客户为国内外OLED 成品材料企业，"
             "OLED 成品材料生产企业下游主要为 OLED 显示面板生产企业，"
             "OLED 显示面板生产企业下游为各类显示屏应用企业。")
    roles = prepare_source_assertions(chain)
    assert not roles.descriptive_only
    assert not any(clause.function_or_event for clause in roles.clauses)
    # The sold list cannot donate material status to the independent developed
    # count. Verify that count itself with its original following clause.
    roles = prepare_source_assertions("现已开发了超300 种化合物，在所涉足的产品方面技术已经处于国内领先水平。")
    assert any(clause.material_payload and '300' in clause.text for clause in roles.clauses)
