"""One source order concept across scripts; no invented count/value or issuer."""
from dataclasses import fields
from hashlib import sha256
from pathlib import Path

import pytest

from company_wiki.source_catalog import narrative_business_policy as policy
from company_wiki.source_catalog import narrative_business_meaning as legacy
from company_wiki.source_catalog.n6_candidate_operating_facts import OperatingFact

ACTUAL_REASONS = {
    "operating_quantity", "operating_metric_change", "business_revenue_measure",
    "operating_causal_driver", "product_operating_driver",
}
DIRECTIONS = (
    "- 客户订单同比增长20%。",
    "- 客戶訂單同比增長20%。",
    "- Customer orders increased 20% year over year.",
    "报告期内订单同比下降7%。",
    "報告期內訂單同比下降7%。",
    "Orders fell 7% during the reporting period.",
    "公司订单增长。",
    "公司訂單增長。",
    "Our orders increased.",
)
COUNTS = (
    "报告期内订单数量为417项。",
    "報告期內訂單數量為417項。",
    "Order counts were 417 during the reporting period.",
    "公司订单数量为0项。",
    "公司訂單數量為0項。",
    "Our order count was 0.",
)
PLANS = (
    "公司计划订单数量达到619项。",
    "公司計劃訂單數量達到619項。",
    "We plan order counts of 619 next year.",
    "预计明年订单同比增长12%。",
    "預計明年訂單同比增長12%。",
    "We expect orders to increase 12% next year.",
)
CONDITIONS = (
    "假设订单数量为619项。",
    "假設訂單數量為619項。",
    "Assuming order counts of 619, we could expand operations.",
)
NON_MEASURES = (
    "订单742号在登记表中列示。",
    "訂單742號在登記表中列示。",
    "Order 742 is listed in the register.",
    "客户订单余额同比增长20%。",
    "客戶訂單餘額同比增長20%。",
    "Customer order balances increased 20% year over year.",
    "订单金额为8200元。",
    "訂單金額為8200元。",
    "Order value was USD 8200.",
    "订单数量是指客户提交的采购请求数量。",
    "訂單數量是指客戶提交的採購請求數量。",
    "Order counts are defined as the number of purchase requests.",
    "订单情况见附表。",
    "訂單情況見附表。",
    "The order situation is described in the appendix.",
)


@pytest.fixture(autouse=True)
def imports_are_the_current_owned_checkout():
    root = Path(__file__).resolve().parents[3] / "src"
    assert Path(policy.__file__).resolve().is_relative_to(root)
    assert Path(legacy.__file__).resolve().is_relative_to(root)


def observe(text):
    original = text.encode("utf8")
    result = policy.detect_reading_business_fact(text)
    assert text.encode("utf8") == original
    return result


@pytest.mark.parametrize("text", DIRECTIONS)
def test_actual_order_direction_is_not_an_invented_count_or_revenue(text):
    fact = observe(text)
    assert fact.eligible and "operating_metric_change" in fact.reasons
    assert "operating_quantity" not in fact.reasons
    assert "business_revenue_measure" not in fact.reasons
    assert "operating_plan" not in fact.reasons
    assert fact.purpose == "operating_metric"


@pytest.mark.parametrize("text", COUNTS)
def test_explicit_order_count_including_zero_keeps_existing_quantity_reason(text):
    fact = observe(text)
    assert fact.eligible and "operating_quantity" in fact.reasons
    assert "operating_metric_change" not in fact.reasons
    assert "business_revenue_measure" not in fact.reasons
    assert "operating_plan" not in fact.reasons


@pytest.mark.parametrize("text", PLANS)
def test_forward_order_count_or_trend_stays_a_plan_not_an_actual(text):
    fact = observe(text)
    assert fact.eligible and "operating_plan" in fact.reasons
    assert not ACTUAL_REASONS.intersection(fact.reasons)


@pytest.mark.parametrize("text", CONDITIONS)
def test_explicit_order_hypothesis_does_not_assert_an_actual(text):
    assert not ACTUAL_REASONS.intersection(observe(text).reasons)


@pytest.mark.parametrize("text", NON_MEASURES)
def test_order_identifier_financial_subject_definition_and_noun_are_not_metrics(text):
    assert not ACTUAL_REASONS.intersection(observe(text).reasons)


def test_existing_legacy_entry_and_fact_vocabulary_are_not_replaced():
    assert policy.detect_business_fact is legacy.detect_business_fact
    assert {field.name for field in fields(OperatingFact)} == {
        "eligible", "topics", "reasons", "score", "financial_exempt", "purpose",
    }
    text = "客户订单同比增长20%。"
    digest = sha256(text.encode("utf8")).hexdigest()
    fact = observe(text)
    assert not {"amount", "currency", "unit", "period", "issuer", "order_count"}.intersection(vars(fact))
    assert sha256(text.encode("utf8")).hexdigest() == digest


@pytest.mark.parametrize("text,planned", [
    ("Next year, orders to increase 12%.", True),
    ("We expect our order count to increase 12% next year.", True),
    ("We expect customer numbers to increase 12% next year.", True),
    ("We expect projects to increase 12% next year.", True),
    ("Our orders to increase 12%.", False),
    ("Order count to increase 12%.", False),
    ("During the reporting period, orders to increase 12%.", False),
    ("We do not expect orders to increase 12% next year.", False),
    ("We expect order 742 to increase 12% next year.", False),
])
def test_infinitive_direction_needs_the_existing_forward_predicate(text, planned):
    fact = observe(text)
    assert not ACTUAL_REASONS.intersection(fact.reasons)
    assert ("operating_plan" in fact.reasons) is planned
