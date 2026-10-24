"""Reporting-rule actions must not consume the operating reading budget."""
from hashlib import sha256

import pytest

from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact
from company_wiki.source_catalog.narrative_business_meaning import concrete_operating_event
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_catalog.narrative_reading import _admitted
from company_wiki.source_catalog.narrative_source_purpose import NON_OPERATING_PURPOSES, source_purpose
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


REPORTING_RULES = (
    "于资产负债表日，外币货币性项目采用该日即期汇率折算为人民币，汇兑差额计入当期损益。",
    "为管理外汇风险引起的风险敞口，本集团指定某些金融工具作为套期工具进行套期。"
    "满足规定条件的套期，本集团采用套期会计方法进行处理。",
    "同一金融工具或具有相同预计存续期的类似金融工具的信用风险的外部市场指标是否发生显著变化。"
    "这些指标包括信用利差、金融资产的公允价值和借款人的债务工具价格变动。",
    "The group translates foreign currency monetary items using the closing exchange rate at each balance sheet date. "
    "Exchange differences are recognized in profit or loss.",
    "Foreign currency monetary items are translated at the closing spot exchange rate at each reporting date.",
    "The group designates financial instruments as hedging instruments and applies hedge accounting "
    "when qualifying conditions are met.",
    "The group assesses whether credit risk on financial instruments has increased significantly "
    "by examining external market indicators.",
    "The group applies hedge accounting which consists of designating financial instruments.",
    "Foreign currency monetary items are translated at closing exchange rates using a method "
    "that consists of rate selection and remeasurement.",
)


def unit(text, index=0):
    digest = sha256(b"reporting-purpose-neutral-source").hexdigest()
    return _make_unit(source_id=source_id_for_sha256(digest), parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
        raw_text=text, unit_kind="paragraph", source_role="company_filing", language="zh", metadata={})


@pytest.mark.parametrize("text", REPORTING_RULES)
def test_reporting_object_and_treatment_are_not_operating_events(text):
    assert source_purpose(text) == "accounting_policy"
    fact = detect_reading_business_fact(text)
    assert not fact.eligible
    assert not _admitted(unit(text), {"section_role": "business"}, "background", fact=fact)[0]


@pytest.mark.parametrize("text", (
    "公司营业收入以美元结算为主，若人民币未来大幅升值，可能导致折算后的人民币收入相应减少；"
    "同时本公司所持美元资产兑换为人民币时可能产生汇兑损失，进而直接影响公司的盈利水平。",
    "公司推出用于外汇风险管理的软件平台，并已向海外客户交付。",
    "本集团采用套期会计，公司的新设备已经向海外客户交付。",
    "本集团指定某些金融工具作为套期工具，并在本年向客户交付新型生产设备。",
    "The group applies hedge accounting and launched a new software platform for customers.",
    "The company launched a platform that translates foreign currency monetary items "
    "at closing exchange rates for customers.",
    "The bank launched new financial instruments and expanded its service platform for enterprise customers.",
    "公司的产品用于金融工具的信用风险评估，并判断是否发生显著变化。",
    "本集团采用套期会计，并通过经销商向海外客户销售工业设备。",
))
def test_actual_customer_business_and_currency_exposure_are_preserved(text):
    assert source_purpose(text) not in NON_OPERATING_PURPOSES
    assert _admitted(unit(text), {"section_role": "business"}, "background")[0]


@pytest.mark.parametrize("text", ("外币货币性项目", "Financial instruments and foreign currency monetary items."))
def test_financial_object_nouns_alone_do_not_prove_a_reporting_rule(text):
    assert source_purpose(text) != "accounting_policy"


@pytest.mark.parametrize("text, asserted", (
    ("考虑客户的新产品是否推出", False),
    ("包括借款人的产品是否投产和订单能否交付", False),
    ("考虑客户产品交付是否顺利", False),
    ("考虑客户新产品投产是否延期", False),
    ("Check whether products launched, equipment delivered, and factories opened", False),
    ("Assess whether the customer's product has already launched", False),
    ("Determine if the customer's equipment was delivered", False),
    ("客户的新产品已经推出并交付", True),
    ("The company launched a platform to assess whether credit risk changed", True),
    ("评估产品是否推出，客户的新设备已经交付", True),
    ("Assess whether credit risk changed, but launched a new customer platform this year", True),
    ("Assess whether credit risk changed, but whether a customer platform launched is unknown", False),
))
def test_event_questions_and_independent_observations_have_distinct_assertion_scope(text, asserted):
    assert concrete_operating_event(text) is asserted


def test_public_selection_spends_limited_slots_on_business_instead_of_reporting_templates():
    backlog = "公司持续经营业务在手订单人民币80亿元，同比增长18%，未来一年按交付进度确认收入。"
    delivery = "公司新增软件平台已经交付客户，并将服务范围拓展至海外市场。"
    texts = (*REPORTING_RULES, backlog, delivery)
    digest = sha256(b"reporting-purpose-neutral-source").hexdigest()
    parsed = DocumentStructure(source_id_for_sha256(digest), digest, "zh",
        tuple(unit(text, index) for index, text in enumerate(texts)),
        page_count=1, pages_read=1, mime_type="text/plain")
    result = select_narrative_evidence(parsed, title="Annual report", existing_kind="annual_report",
        selector_version="0.9.0", max_selected=4)
    selected = {span.raw_text for span in result.evidence_spans}
    assert selected.isdisjoint(REPORTING_RULES)
    assert {backlog, delivery} <= selected
