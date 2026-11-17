"""Display complete source scopes, including attribution and conditions."""

import pytest

from company_wiki.source_catalog.narrative_business_quotes import project_business_quotes
from company_wiki.source_catalog.narrative_claims import SummaryClaim
from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan, source_id_for_sha256


def span(text, paragraph, *, role="management", speaker="", metadata=None):
    return EvidenceSpan.create(
        source_id=source_id_for_sha256("a" * 64),
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=paragraph),
        raw_text=text,
        structured_value={"source_role": role, "speaker": speaker, **(metadata or {})},
        parser_name="fixture",
        parser_version="1.0.0",
        parse_status="parsed",
        quality_flags=(),
    )


@pytest.mark.parametrize(("answer", "question", "draft"), [
    (
        "据新闻报道，相关事项涉及对方的家电产品，未对本公司经营构成重大影响。",
        "这家企业是否是贵司客户，并计划全面退出该市场？",
        "客户全面退出该市场，对本公司经营没有任何影响。",
    ),
    (
        "根据控股股东信息，股东已与对方建立联系，并希望进一步合作。",
        "请问公司是否已经签订合作合同？",
        "公司与对方达成合作。",
    ),
    (
        "项目包括约 750 吨/年的产能，建成后将提供生产保障。",
        "方案是否必须完成试产才生效？",
        "设计产能为 750 吨/年，以建成投产为前提。",
    ),
])
def test_chosen_scope_preserves_complete_support_and_context(answer, question, draft):
    asked = span(question, 0, role="investor_question")
    support = span(answer, 1, speaker="负责人")
    background = span("本报告未经审计。", 2, role="company_filing")
    selected = SummaryClaim("useful", draft, (support.span_id,), "company_statement",
                            "uncertain", context_evidence_ids=(asked.span_id,))
    repeated = SummaryClaim("same-scope", "相同范围", (support.span_id,), "company_statement",
                            "uncertain", context_evidence_ids=(asked.span_id,))
    unselected = SummaryClaim("background", background.raw_text, (background.span_id,),
                              "company_statement", "actual")

    quotes = project_business_quotes(
        (asked, support, background), (unselected, repeated, selected),
        ("useful", "same-scope"),
    )

    assert len(quotes) == 1
    quote = quotes[0]
    assert quote["claim_id"] == "useful"
    assert quote["support"] == [{
        "source_id": support.source_id,
        "span_id": support.span_id,
        "locator": support.locator,
        "text": answer,
        "parse_status": "parsed",
        "quality_flags": [],
        "source_role": "management",
        "speaker": "负责人",
    }]
    assert quote["context"][0]["span_id"] == asked.span_id
    assert quote["context"][0]["locator"] == asked.locator
    assert quote["context"][0]["text"] == question
    assert quote["context"][0]["source_role"] == "investor_question"
    assert draft not in str(quote)
    assert background.raw_text not in str(quotes)


def test_different_support_closures_remain_separate_in_requested_order():
    first = span("本期向欧洲客户交付。 ", 0)
    second = span("若获监管批准，计划明年扩大交付。", 1)
    claims = (
        SummaryClaim("current", first.raw_text, (first.span_id,), "company_statement", "actual"),
        SummaryClaim("plan", second.raw_text, (second.span_id,), "company_statement", "planned"),
    )
    quotes = project_business_quotes((first, second), claims, ("plan", "current"))
    assert [quote["claim_id"] for quote in quotes] == ["plan", "current"]
    assert quotes[0]["support"][0]["text"] == second.raw_text
    assert quotes[1]["support"][0]["text"] == first.raw_text


def test_printed_pdf_turn_carries_its_attribution_and_label_location():
    label = span("李女士，运营负责人", 0)
    turn = {
        "speaker": "李女士",
        "title": "运营负责人",
        "role": "management",
        "turn_id": "printed-turn",
        "label_locator": label.locator,
    }
    body = span(
        "计划在完成客户验证后增加供货。",
        1, metadata={"printed_turn": {**turn, "body_start": 0, "body_end": 15}},
    )
    claim = SummaryClaim("plan", body.raw_text, (body.span_id,), "company_statement", "planned")

    quote = project_business_quotes((body,), (claim,), ("plan",))[0]["support"][0]

    assert "speaker" not in quote
    assert quote["printed_turn"] == turn
    assert quote["locator"] == body.locator


def test_automatic_summary_keeps_low_priority_operating_detail_and_source_attribution():
    from company_wiki.source_catalog.narrative_business_quotes import project_automatic_business_quotes

    contact = span("董事会秘书 证券事务代表 姓名 某甲 联系地址 地址一", 0, role="company_filing")
    listing = span("股票种类 股票上市交易所 股票简称 股票代码 A股 交易所 示例 123456", 1, role="company_filing")
    disclosure = span("本半年度报告未经审计。", 2, role="company_filing")
    financing = span("筹资活动产生的现金流量净额变动原因说明：报告期内，公司筹资活动使用的现金流量净额为人民币89,931.05万元，主要为现金股息和股份回购。", 6, role="company_filing")
    operator = span("The operator announced that the call will begin immediately.", 7, role="operator")
    question = span("Are customer shipments expected to reach their target?", 8, role="analyst_question")
    actual = span("根据合作方通报，第二条生产线须在完成客户验收后才可批量供货。", 3, speaker="负责人",
                  metadata={"reading_priority": 2, "reading_value_band": "description", "reading_score": 0})
    scope = span("客户现在可通过电话与电邮提交售后请求，响应时间为两个工作日。", 4)
    spans = (contact, listing, disclosure, actual, scope, financing, operator, question)
    draft = SummaryClaim("draft-plan", "公司已批量供货。", (actual.span_id,), "company_statement", "actual")
    result = project_automatic_business_quotes(spans, (draft,), None)
    assert [[part["text"] for part in row["support"]] for row in result] == [[actual.raw_text], [scope.raw_text]]
    assert result[0]["claim_id"] == draft.claim_id
    assert result[0]["support"][0]["speaker"] == "负责人"
    assert result[1]["claim_id"] is None
    assert result[0]["task_key"] != result[1]["task_key"]
    assert draft.text not in str(result)
