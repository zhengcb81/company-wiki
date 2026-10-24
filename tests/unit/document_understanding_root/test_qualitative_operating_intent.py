"""Business plans need no invented metric or completed operating milestone."""

from __future__ import annotations

import pytest

from company_wiki.source_catalog.narrative_business_policy import (
    detect_reading_business_fact,
)


@pytest.mark.parametrize(
    "text",
    [
        "往后整个产品的思路还是会延续，更多地采用存量运营的方式。",
        "后期我们希望能够在新的水平去稳住这款产品，但目前不好判断。",
        "我们会跟随这些节点集中推出更新迭代的版本，但具体计划尚未确定。",
        "公司计划减少对广告投放的依赖，更多采用用户留存运营。",
        "Our company plans to update the product, but the timing remains uncertain.",
        "We hope to stabilize customer retention, but no schedule has been set.",
        "The group intends to reduce reliance on paid customer acquisition.",
        "公司计划更新产品。",
        "We plan to continue customer support.",
        "We hope to continue our service platform.",
        "公司计划更新服务平台。",
    ],
)
def test_specific_qualitative_operating_intent_is_useful_source_material(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible
    assert "operating_plan" in fact.reasons
    assert fact.purpose == "operating"
    assert "applied_operating_milestone" not in fact.reasons


@pytest.mark.parametrize(
    "text",
    [
        "公司希望未来越来越好。",
        "公司将提升综合管理水平。",
        "计划更新员工培训材料。产品收入增长。",
        "公司希望现金余额增加，产品目录已有介绍。",
        "请问公司会不会推出更新迭代的版本？",
        "Our products are excellent. We plan to update employee benefits.",
        "The company hopes cash balances increase, while customers receive training.",
        "Our products will update employee benefits.",
        "我们的产品会更新员工培训文件。",
        "The company plans to update business expense records.",
        "We plan to update customer acquisition training records.",
        "We plan to launch product training manuals for employees.",
    ],
)
def test_intent_does_not_borrow_an_unrelated_noun_or_turn_a_question_into_a_plan(text):
    assert "operating_plan" not in detect_reading_business_fact(text).reasons
