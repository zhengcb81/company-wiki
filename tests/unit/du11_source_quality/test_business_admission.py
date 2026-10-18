"""Business purpose cannot be inferred from a generic relation or section label."""
from hashlib import sha256

import pytest

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_operating_relations import SourceOperatingSession
from company_wiki.source_catalog.narrative_reading import _admitted


def assessment(text, *, role="company_filing", section="business"):
    digest = sha256(text.encode()).hexdigest()
    unit = _make_unit(source_id=source_id_for_sha256(digest), parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0), raw_text=text,
        unit_kind="pdf_text_block", source_role=role, language="mixed", metadata={})
    session = SourceOperatingSession({unit.unit_id: unit}, work_budget=WorkBudget(500000))
    fact = session.fact(unit.unit_id)
    admitted, _ = _admitted(unit, {"section_role": section, "family": "annual"},
        "paragraph_event", fact=fact, financial_only=session.financial_only(unit.unit_id))
    return admitted, fact, session


@pytest.mark.parametrize("text", [
    "本公司采用期权定价模型，按无风险利率和预期波动率估计股票期权的公允价值。",
    "租赁变更导致租赁范围缩小或租赁期缩短，本集团调减使用权资产账面价值，并将相关利得计入损益。",
    "We evaluated the design of internal controls over impairment assessment and tested management assumptions.",
    "We use a valuation model and a risk-free rate to determine the fair value of employee share options.",
    "□适用 √不适用",
    "新增重要非主营业务情况\n□适用√不适用",
    "报告期内经营情况变化及预计未来重大事项\n□适用 √不适用",
    "新產品交付客戶情況\n☐適用☑不適用",
    "See Note 18 for information about contractual liabilities.",
    "The Board approved low-risk wealth management products to improve cash management.",
    "本集團採用期權定價模型，按照無風險利率估計股份支付的公允價值。",
    "We tested remaining performance obligations of $368 billion as part of our audit procedures.",
    "We use employee share options in our valuation model. Our customers use the platform.",
    "Our consolidated financial statements and accompanying notes are prepared in accordance with GAAP. Preparing consolidated financial statements requires management to make estimates and assumptions that affect the reported amounts of assets, liabilities, revenue, and expenses.",
    "The Company designs and maintains accounting and internal control systems to provide reasonable assurance that assets are safeguarded and financial records are reliable for preparing consolidated financial statements.",
    "We allocate goodwill to reporting units based on the reporting unit expected to benefit from the business combination. We reassign goodwill using a relative fair value allocation approach. Goodwill is tested for impairment at the reporting unit level.",
    "Revenue allocated to remaining performance obligations was $90 million, with no conversion schedule disclosed.",
    "Our audit procedures included testing revenue from software delivered to customers.",
    "The independent auditor tested software delivered to customers as part of audit procedures.",
    "审计程序包括检查已交付客户的产品及其收入确认凭证。",
])
def test_pure_non_operating_purpose_is_not_promoted_by_a_business_section(text):
    admitted, fact, _ = assessment(text)
    assert not admitted, (fact.reasons, fact.financial_exempt)


@pytest.mark.parametrize("text", [
    "公司已租赁新工厂用于先进封装产线，计划明年投产。",
    "公司已完成收购一家CMP设备公司，其抛光设备与本公司的产品形成互补，预计产生客户协同。",
    "We launched an AI model platform for enterprise customers and received repeat orders.",
    "Our derivative pricing platform was launched for 200 institutional customers.",
    "Commercial remaining performance obligations were $368 billion at June 30, 2025; we expect to recognize 40% as revenue in the next twelve months.",
    "公司尚未完成新产品的客户认证，量产仍取决于后续验证。",
    "We hired 120 engineers to expand our overseas pilot production line and shorten customer certification cycles.",
    "We use a valuation model for employee share options. We launched a platform for enterprise customers.",
    "We launched software for customers to automate audit procedures.",
    "公司已交付新产品，并完成客户验证。其他事项 □适用√不适用",
    "公司采用期权定价模型计量股份支付。公司已收购设备企业，与现有产品形成客户协同。",
    "Revenue allocated to remaining performance obligations was $90 million, and we expect to recognize 40% as revenue in the next twelve months.",
])
def test_actual_operating_activity_survives_financial_vocabulary(text):
    admitted, _, _ = assessment(text)
    assert admitted


def test_exhausted_purpose_budget_does_not_restart_an_unbounded_text_fallback(monkeypatch):
    import company_wiki.source_catalog.narrative_reading as reading
    text = "We launched a platform for customers."
    digest = sha256(text.encode()).hexdigest()
    unit = _make_unit(source_id=source_id_for_sha256(digest), parser_version="0.1.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=0), raw_text=text,
        unit_kind="pdf_text_block", source_role="company_filing", language="en", metadata={})
    session = SourceOperatingSession({unit.unit_id: unit}, work_budget=WorkBudget(0))
    fact = session.fact(unit.unit_id)
    monkeypatch.setattr(reading, "detect_reading_business_fact",
                        lambda *args: pytest.fail("unbudgeted text fallback"))
    admitted, _ = reading._admitted(unit, {"section_role": "business"}, "paragraph_event",
        fact=fact, financial_only=session.financial_only(unit.unit_id))
    assert not admitted
    assert not session.complete
