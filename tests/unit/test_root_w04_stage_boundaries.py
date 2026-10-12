"""General completed-production/customer-certification proof boundaries."""
import pytest
from company_wiki.source_catalog.narrative_stage_assertions import commercialization_milestone

@pytest.mark.parametrize("text",[
    "公司新型传感器产品已经实现量产。",
    "公司先后实现了高纯材料新产品的量产，并陆续获得终端客户的认证。",
    "本公司的医疗设备已取得终端客户认证。",
    "Our new product has achieved mass production.",
    "The product has obtained customer qualification.",
])
def test_achieved_production_and_customer_certification_are_stage_proofs(text):
    assert commercialization_milestone(text)

@pytest.mark.parametrize("text",[
    "公司新型产品尚未实现量产。",
    "公司新型产品预计明年实现量产。",
    "若公司新型产品实现量产，则按合同收取货款。",
    "公司产品资料已获得客户认证。",
    "公司产品进入量产验证阶段，仍需客户确认。",
    "The product may achieve mass production next year.",
    "The product has not obtained customer qualification.",
    "Our product documents have obtained customer qualification.",
    "竞争对手的设备已实现量产。",
    "供应商的产品已经取得客户认证。",
    "公司正在研究产品是否已经量产。",
])
def test_plans_conditions_documents_and_foreign_actor_do_not_prove_issuer_stage(text):
    assert not commercialization_milestone(text)
