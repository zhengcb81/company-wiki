"""Reporting-rule actions must not consume the operating reading budget."""
from hashlib import sha256

import pytest

from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact
from company_wiki.source_catalog.narrative_business_disclosures import disclosure_relations
from company_wiki.source_catalog.narrative_business_meaning import concrete_operating_event
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_catalog.narrative_reading_admission import is_admitted
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
        raw_text=text, unit_kind="paragraph", source_role="company_filing",
        language="zh" if not text.isascii() else "en", metadata={})


@pytest.mark.parametrize("text", REPORTING_RULES)
def test_reporting_object_and_treatment_are_not_operating_events(text):
    assert source_purpose(text) == "accounting_policy"
    fact = detect_reading_business_fact(text)
    assert not fact.eligible
    assert not is_admitted(unit(text), {"section_role": "business"}, "background", fact=fact)[0]


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
    assert is_admitted(unit(text), {"section_role": "business"}, "background")[0]


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


@pytest.mark.parametrize("text", [
    "三、本半年度报告未经审计。",
    "附註：上述子公司財務數據未經審計。",
    "The accompanying interim financial statements have not been audited.",
    "Financial information in this quarterly report is unaudited.",
    "二、公司全体董事出席董事会会议。",
    "All board directors attended the meeting of the board of directors.",
    "本报告中的前瞻性陈述不构成公司对投资者的承诺。",
    "本报告中所涉及的未来计划、发展战略等前瞻性描述不构成本公司对投资者的承诺，敬请投资者注意投资风险。",
    "Forward-looking statements in this report do not constitute commitments to investors.",
])
def test_administrative_assertions_about_the_disclosure_do_not_become_operating_support(text):
    assert source_purpose(text) == "reporting_definition"
    assert not is_admitted(unit(text), {"section_role": "business"}, "paragraph_event")[0]


@pytest.mark.parametrize("text", [
    "本期客户审计已通过，新增订单预计将在验收后交付。",
    "The plant passed a customer audit and delivered upgraded units to customers.",
    "本半年度报告未经审计。公司向海外客户交付了新产品。",
    "The directors attended the meeting. The company opened a second production line.",
    "本报告中的前瞻性陈述不构成承诺。公司拟在明年建设海外生产基地。",
    "本報告所載未來計劃包括在東南亞建設一座年產5萬噸的工廠，惟不構成公司承諾。",
    "Forward-looking statements about the second production facility in the report do not constitute commitments.",
    "The company signed a commitment with a distributor to open new sales channels.",
])
def test_reporting_language_does_not_erase_an_independent_operation(text):
    assert source_purpose(text) not in NON_OPERATING_PURPOSES
    assert is_admitted(unit(text), {"section_role": "business"}, "paragraph_event")[0]


@pytest.mark.parametrize("text", [
    "本报告披露的未来计划为明年建设海外工厂，但不构成投资承诺。",
    "本报告中未来计划包括公司明年拟新建工厂，不构成承诺。",
    "Our future plans include building a second manufacturing facility after customer acceptance.",
    "公司计划在客户验收后建设海外工厂。",
    "公司否认已经与当地政府签约，但仍计划建设海外新工厂。",
    "The company denied that it had signed with the local government, but still plans to build a new factory overseas.",
])
def test_disclosed_future_projects_keep_their_operating_plan_without_a_number(text):
    assert source_purpose(text) not in NON_OPERATING_PURPOSES
    admitted, fact = is_admitted(unit(text), {"section_role": "business"}, "paragraph_event")
    assert admitted
    assert "operating_plan" in fact.reasons
    assert "operating_milestone" not in fact.reasons


@pytest.mark.parametrize("text", [
    "公司是否拟于明年建设海外工厂？",
    "公司计划建设海外工厂吗？",
    "Are their future plans to build a new plant?",
    "公司未来计划为明年建设厂房融资方案。",
    "Our future plans include building a warehouse financing model.",
    "公司拟做安排。厂区设施待定。",
    "公司未计划在海外建设新工厂。",
    "公司不打算扩建海外工厂。",
    "The company does not plan to build a new factory.",
    "The company has no plans to build an overseas factory.",
    "Do they plan to build a new plant",
    "Are their future plans to build a new plant",
    "财务模型假设公司将建设海外工厂。",
    "The financial model assumes that the company will build an overseas plant next year.",
    "如果公司拟建设海外工厂，需测算资本开支。",
    "If the company plans to build a second manufacturing facility, capital expenditure would rise.",
])
def test_project_relevance_requires_a_scoped_predicate_and_facility_object(text):
    assert "operating_plan" not in disclosure_relations(text)


@pytest.mark.parametrize("text", [
    "公司全体董事出席会议，批准在海外建设新产线。",
    "All directors attended the board meeting and approved a second production line.",
])
def test_board_action_survives_when_attendance_is_not_the_only_disclosure(text):
    assert source_purpose(text) not in NON_OPERATING_PURPOSES
    assert is_admitted(unit(text), {"section_role": "business"}, "paragraph_event")[0]


def test_published_selection_keeps_operating_evidence_and_its_bound_locator():
    texts = (
        "本半年度报告未经审计。",
        "本报告中的前瞻性陈述不构成公司对投资者的承诺。",
        "公司完成海外新产线的客户认证，并已交付首批产品。",
    )
    digest = sha256(b"reporting-purpose-neutral-source").hexdigest()
    parsed = DocumentStructure(
        source_id_for_sha256(digest), digest, "zh",
        tuple(unit(text, index) for index, text in enumerate(texts)),
        page_count=1, pages_read=1, mime_type="text/plain",
    )
    result = select_narrative_evidence(parsed, title="Semiannual report", existing_kind="semi_annual_report",
                                      selector_version="0.9.0", max_selected=3)
    supports = {item for group in result.reading_context["groups"] for view in group["citation_views"]
                if view["reading_support_use"] == "support" for item in view["support_evidence_ids"]}
    spans = [span for span in result.evidence_spans if span.span_id in supports]
    assert [(span.raw_text, span.coordinates.paragraph_index) for span in spans] == [(texts[2], 2)]
    assert [item.raw_text for item in parsed.units] == list(texts)
