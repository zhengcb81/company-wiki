"""Scoped coverage is business meaning, not an achieved operating milestone."""
import pytest

from company_wiki.source_catalog.narrative_business_policy import (
    assess_reading_business_fact, detect_business_fact,
)


def assessed(text):
    return assess_reading_business_fact(text, {"relations": []})[0]


@pytest.mark.parametrize("text", [
    "星河仪器的42类设备产品已覆盖27%的晶圆工艺功能，未来三年计划覆盖45%的先进封装设备市场。",
    "本企业的软件模块计划在未来三年覆盖45%的目标功能。",
    "曙光軟件的18類產品已覆蓋32%的目標工藝，未來四年擬覆蓋55%的設備市場。",
    "Delta Labs' equipment products currently cover 27% of wafer-processing functions.",
    "Our software products are planned to cover 45 percent of the target applications within three years.",
    "本企业的服务已经覆盖17个海外地区。",
    "Our services cover seventeen regional markets and 12 countries.",
    "According to a supplier, its equipment products cover 28% of the target process functions.",
    "本公司尚未达到覆盖45%设备市场的产品布局目标。",
    "本企业的软件产品覆盖目标功能的45%。",
    "Our software coverage of target applications is 45 percent.",
    "Our products cover 45% of wafer process functions and revenue increased 20%.",
    "Revenue increased 20%, while our products cover 45% of wafer process functions.",
    "Our sales services cover 17 regional markets.",
])
def test_specific_scoped_coverage_survives_without_inventing_completed_state(text):
    fact = assessed(text)
    assert fact.eligible
    assert "business_coverage_relation" in fact.reasons
    assert not {"operating_milestone", "operating_current_state"}.intersection(fact.reasons)


@pytest.mark.parametrize("text", [
    "本公司产品受到好评。贷款拨备覆盖率为137%。",
    "Our product brand is well known. Collateral coverage reached 145% of loan balances.",
    "Our insurance products have an insurance coverage ratio of 32% of insured values.",
    "软件产品相关贷款的拨备覆盖率达到137%。",
    "Our products cover 40% of outstanding debt balances.",
    "本公司产品目录丰富，覆盖率为45%。",
    "Our products cover 45%.",
    "公司的目标是覆盖市场并成为全球领先平台。",
    "Our products aim to cover world-leading markets.",
    "Our product portfolio is extensive. Coverage is 45% of the target functions.",
    "The forecast is 45% of equipment markets. Our products are innovative.",
    "27%的市场规模与公司的软件产品有关。",
    "Our software products cover target functions, and building occupancy is 45%.",
    "Our software products cover target functions and building occupancy is 45%.",
    "Our software products cover 45% and our debt balances relate to equipment markets.",
    "本公司产品覆盖多个应用，办公室出租率为45%。",
    "本公司产品覆盖目标功能且办公室出租率为45%。",
    "Loans for equipment purchases cover 45% of equipment asset balances.",
    "Our products cover 45% of revenue from equipment markets.",
    "Our software-related receivables cover 45% of equipment market receivables.",
    "本公司的设备产品覆盖45%的设备市场收入。",
    "Our products cover 45% of revenues from equipment markets.",
    "Our products cover 45% of sales in equipment markets.",
    "Our products cover 45% of equipment market profits.",
    "Our products cover 45% of equipment market earnings.",
    "本公司的设备产品覆盖45%的设备市场营收。",
    "本公司的设备产品覆盖45%的设备市场销售额。",
    "本公司的设备产品覆盖45%的设备市场利润。",
    "本公司的設備產品覆蓋45%的設備市場營收。",
])
def test_financial_ratios_vague_claims_and_cross_sentence_subjects_are_not_coverage_facts(text):
    assert "business_coverage_relation" not in assessed(text).reasons


def test_legacy_detector_is_not_upgraded_by_reading_coverage():
    text = "本企业的产品覆盖27%的目标工艺。"
    assert "business_coverage_relation" not in detect_business_fact(text).reasons
    assert "business_coverage_relation" in assessed(text).reasons
