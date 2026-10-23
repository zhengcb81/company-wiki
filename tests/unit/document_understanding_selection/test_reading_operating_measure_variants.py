"""Existing public business observations: volume levels versus revenue growth.

No ObservedMeasure wire exists in the current producer.  Assertions therefore
use real OperatingFact reasons and exact source EvidenceSpan text/locators,
never invented normalized numbers, unit references or metric-kind fields.
"""
from hashlib import sha256
from pathlib import Path

import pytest

from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

VOLUMES = (
    ("cn-explicit-zero", "公司反应器总体积为0L。", "0L"),
    ("trad-grouped-l", "公司反應器總體積為36,400 L。", "36,400 L"),
    ("cn-reactor-kl", "公司反应器总体积已提升至逾8200kL。", "8200kL"),
    ("trad-reactor-kl", "公司反應器總體積已提升至逾6400kL。", "6400kL"),
    ("cn-storage-l", "公司储罐总体积为185000L。", "185000L"),
    ("trad-equipment-l", "公司生物反應設備的有效體積達到17600L。", "17600L"),
    ("cn-treatment-m3", "公司水处理装置的有效体积达到92.5m³。", "92.5m³"),
    ("en-reactor-m3", "Our reactor volume reached 18.6 m³ during the year.", "18.6 m³"),
    ("en-storage-kl", "Our storage capacity reached 470 kL during the year.", "470 kL"),
    ("en-treatment-l", "Our total treatment volume was 925000 L for the period.", "925000 L"),
    ("en-volume-to", "Our treatment volume increased to 68.2 m³ during the period.", "68.2 m³"),
)
GROWTH = (
    ("en-comparison-frame", "Compared with the previous year, our device maintenance services revenue increased by 5.8%.", "5.8%"),
    ("cn-support-up", "技术支持业务收入同比增长6.3%。", "6.3%"),
    ("trad-repair-down", "儀器維修業務收入同比下降8.7%。", "8.7%"),
    ("en-maintenance-up", "Our device maintenance services revenue grew 7.4% year over year.", "7.4%"),
    ("en-cloud-down", "Our cloud services revenue declined 9.6% year over year.", "9.6%"),
    ("en-owned-from", "Revenue from our device maintenance services increased by 5.8% year over year.", "5.8%"),
    ("trad-currency-basis", "技術支持業務收入按固定匯率同比增長6.1%。", "6.1%"),
)
LEVELS = (
    ("cn-amount", "技术支持业务收入为12.8亿元。", "12.8亿元"),
    ("cn-share", "技术支持业务收入占比提升至26.4%。", "26.4%"),
    ("en-amount", "Our device maintenance services revenue was USD 73 million.", "USD 73 million"),
    ("en-share", "Our device maintenance services revenue share reached 31.2%.", "31.2%"),
)
NEGATIVE = (
    ("cn-other-financial-comparator", "技术支持业务收入增长6.3%而公司税费同比下降8.7%。"),
    ("en-other-financial-comparator", "Our device maintenance services revenue grew 7.4% while tax expense fell 2.3% year over year."),
    ("cn-missing-comparator", "技术支持业务收入增长6.3%。"),
    ("en-missing-comparator", "Our device maintenance services revenue grew 7.4%."),
    ("cn-future-horizon", "未来三年，技术支持业务收入同比增长6.3%。"),
    ("trad-future-quantity", "未來公司的反應器總體積達到6400kL。"),
    ("cn-future-frame", "明年，技术支持业务收入同比增长6.3%。"),
    ("trad-future-frame", "下一年度，儀器維修業務收入同比下降8.7%。"),
    ("en-future-frame", "Next year, our cloud services revenue increased by 9.6%."),
    ("en-financial-assets-from", "Revenue from the sale of financial assets increased by 8.4%."),
    ("en-unrelated-business-comma", "Our cloud services were described in a meeting, revenue grew 9.6%."),
    ("cn-volume-id", "公司反应器体积编号8200号已登记。"),
    ("trad-volume-id", "公司反應器體積字段編號6400號已登記。"),
    ("en-volume-id", "The company has a product named Volume 742."),
    ("cn-volume-date", "公司反应器体积情况见2024年3月7日公告。"),
    ("en-volume-date", "Our reactor volume for 2024 is described in the notes."),
    ("cn-volume-cash", "公司反应器容积相关账户余额为8200元。"),
    ("en-volume-cash", "Our reactor volume account balance was USD 470."),
    ("cn-total-revenue", "公司营业收入同比增长6.3%。"),
    ("trad-total-revenue", "本公司營業收入同比下降8.7%。"),
    ("en-total-revenue", "Our total revenue grew 7.4% year over year."),
    ("cn-revenue-id", "技术支持业务收入字段编号742用于系统登记。"),
    ("en-revenue-date", "Our services revenue for 2024 is described in note 7."),
    ("en-financial-assets", "Our revenue increased due to higher sales of financial assets."),
    ("en-securities", "Our revenue increased due to higher sales of our securities."),
    ("cn-volume-if", "如果公司反应器总体积达到8200kL，公司将扩建基地。"),
    ("trad-volume-not", "公司反應器總體積尚未達到6400kL。"),
    ("en-volume-future", "Our storage capacity will reach 470 kL next year."),
    ("cn-volume-plan", "公司计划将储罐总体积提升至185000L。"),
    ("cn-growth-if", "如果技术支持业务收入同比增长6.3%，公司将追加投资。"),
    ("trad-growth-not", "儀器維修業務收入並未同比下降8.7%。"),
    ("en-growth-if", "If our cloud services revenue declined 9.6%, costs would fall."),
    ("en-growth-not", "Our device maintenance services revenue did not grow 7.4% year over year."),
    ("cn-growth-future", "公司预计技术支持业务收入明年同比增长6.3%。"),
    ("en-growth-future", "Our maintenance services revenue will increase by 5.8% next year."),
)
ACTUAL_MEASURE_REASONS = {
    "operating_quantity", "operating_metric_change", "business_revenue_measure",
    "operating_causal_driver", "product_operating_driver",
}


@pytest.fixture(autouse=True)
def imported_modules_are_this_checkout():
    root = Path(__file__).resolve().parents[3] / "src"
    for module in (policy, reading):
        assert Path(module.__file__).resolve().is_relative_to(root)


def document(text):
    digest = sha256(("neutral source\n" + text).encode()).hexdigest()
    source = source_id_for_sha256(digest)
    units = tuple(_make_unit(
        source_id=source, parser_version="0.1.1",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
        raw_text=raw, unit_kind="pdf_text_block", source_role="company_filing",
        language="mixed", metadata={"heading_level": 1} if index == 0 else {},
    ) for index, raw in enumerate(("经营情况", text)))
    return DocumentStructure(source, digest, "mixed", units,
                             page_count=1, pages_read=1, mime_type="application/pdf")


def observed(text):
    return policy.detect_reading_business_fact(text)


def select_original(text, expected_reason, literal):
    parsed = document(text)
    before = tuple((u.unit_id, u.raw_text, u.coordinates, repr(u.metadata)) for u in parsed.units)
    budget = WorkBudget(16_000_000)
    result = reading.select_reading_evidence(
        parsed, title="2025年度报告", existing_kind="annual_report", work_budget=budget,
    )
    spans = [s for s in result.evidence_spans if s.raw_text == text]
    assert len(spans) == 1, "the original observed operating measure remains source evidence"
    span = spans[0]
    assert expected_reason in span.structured_value["selection_reasons"]
    assert span.structured_value["reading_value_band"] == "meaningful_fact"
    assert span.source_id == parsed.source_id and span.coordinates == parsed.units[-1].coordinates
    assert span.coordinates.locator() == parsed.units[-1].coordinates.locator()
    start = text.index(literal)
    assert span.raw_text[start:start + len(literal)] == literal
    assert any(span.span_id in view["support_evidence_ids"]
               for group in result.reading_context["groups"] for view in group["citation_views"])
    assert not {"amount", "currency", "unit", "period", "growthRate"}.intersection(span.structured_value)
    assert tuple((u.unit_id, u.raw_text, u.coordinates, repr(u.metadata)) for u in parsed.units) == before
    assert not budget.exhausted and 0 < budget.used <= 16_000_000
    assert result.selection_limit == 96 and reading.MAX_READING_CHARS == 48_000
    return span


@pytest.mark.parametrize("case", VOLUMES, ids=lambda c: c[0])
def test_observed_physical_volume_is_quantity_not_amount(case):
    _identifier, text, _literal = case
    fact = observed(text)
    assert fact.eligible and "operating_quantity" in fact.reasons
    assert "business_revenue_measure" not in fact.reasons


@pytest.mark.parametrize("case", VOLUMES, ids=lambda c: c[0])
def test_public_volume_support_preserves_exact_quantity_and_unit(case):
    _identifier, text, literal = case
    select_original(text, "operating_quantity", literal)


@pytest.mark.parametrize("case", GROWTH, ids=lambda c: c[0])
def test_named_business_growth_rate_is_change_not_revenue_level_or_share(case):
    _identifier, text, _literal = case
    fact = observed(text)
    assert fact.eligible and "operating_metric_change" in fact.reasons
    assert "business_revenue_measure" not in fact.reasons


@pytest.mark.parametrize("case", GROWTH, ids=lambda c: c[0])
def test_public_named_business_growth_support_keeps_original_percent_and_scope(case):
    _identifier, text, literal = case
    span = select_original(text, "operating_metric_change", literal)
    assert "business_revenue_measure" not in span.structured_value["selection_reasons"]


@pytest.mark.parametrize("case", LEVELS, ids=lambda c: c[0])
def test_existing_business_revenue_amount_and_share_remain_levels_with_raw_basis(case):
    _identifier, text, literal = case
    fact = observed(text)
    assert fact.eligible and "business_revenue_measure" in fact.reasons
    select_original(text, "business_revenue_measure", literal)


@pytest.mark.parametrize("case", NEGATIVE, ids=lambda c: c[0])
def test_identity_financial_total_and_unrealized_scope_do_not_assert_actual_measure(case):
    _identifier, text = case
    fact = observed(text)
    assert not ACTUAL_MEASURE_REASONS.intersection(fact.reasons)


@pytest.mark.parametrize("text,literal", [
    ("本期技术支持业务收入同比增长6.3%，明年公司计划扩建厂房。", "6.3%"),
    ("Our cloud services revenue grew 9.6% year over year, and next year we plan to expand equipment capacity.", "9.6%"),
])
def test_independent_later_plan_does_not_erase_current_business_growth(text, literal):
    assert "operating_metric_change" in observed(text).reasons
    select_original(text, "operating_metric_change", literal)
