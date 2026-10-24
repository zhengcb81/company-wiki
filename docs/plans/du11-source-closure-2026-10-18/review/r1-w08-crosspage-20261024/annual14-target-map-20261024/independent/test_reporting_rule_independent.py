"""Independent semantic boundaries; no product code or old goldens changed."""
import pytest

from company_wiki.source_catalog.narrative_source_purpose import NON_OPERATING_PURPOSES, source_purpose
from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact


@pytest.mark.parametrize("text", (
    "公司推出金融工具信用风险管理平台，并按客户要求评估信用风险是否显著增加。",
    "The bank designated financial instruments launched for customers as hedging instruments.",
    "The bank designated financial instruments delivered to customers as hedging instruments.",
    "本集团指定已向客户交付的新金融工具作为套期工具。",
    "本集团指定某些金融工具作为套期工具。公司的新设备已经向海外客户交付。",
    "The group applies hedge accounting and launched an analytics platform for enterprise customers.",
    "公司的产品用于金融工具的信用风险评估，并判断是否发生显著变化。",
    "本集团评估金融工具的信用风险是否显著变化，客户的新产品已经推出并交付。",
    "金融工具的信用风险是否显著变化之外，借款人的新生产设备已交付客户。",
    "The company assesses whether credit risk on financial instruments has increased significantly, "
    "but launched a new customer platform this year.",
))
def test_independent_customer_product_is_not_erased_by_reporting_rule(text):
    assert source_purpose(text) not in NON_OPERATING_PURPOSES
    assert detect_reading_business_fact(text).eligible


@pytest.mark.parametrize("text", (
    "本集团指定某些金融工具作为套期工具，以降低产品价格风险。",
    "Foreign currency monetary items are translated at the closing exchange rate to reduce customer risk.",
    "本集团指定某些金融工具作为套期工具，以降低产品价格风险并提高管理效率。",
    "The group applies hedge accounting to reduce customer risk.",
    "Foreign currency monetary items are translated at the closing spot exchange rate at each reporting date.",
    "於資產負債表日，外幣貨幣性項目採用即期匯率折算為人民幣。",
    "本集团评估金融工具的信用风险是否显著变化，考虑客户的新产品是否推出。",
    "金融工具的信用风险是否显著变化，包括借款人的产品是否投产和订单能否交付。",
    "本集团评估金融工具的信用风险是否显著变化，考虑客户产品交付是否顺利。",
    "本集团评估金融工具的信用风险是否显著变化，考虑客户新产品投产是否延期。",
    "The group assesses whether credit risk on financial instruments increased significantly "
    "by checking whether products launched, equipment delivered, and factories opened.",
))
def test_subordinate_generic_risk_purpose_does_not_become_customer_business(text):
    assert source_purpose(text) == "accounting_policy"
    assert not detect_reading_business_fact(text).eligible
