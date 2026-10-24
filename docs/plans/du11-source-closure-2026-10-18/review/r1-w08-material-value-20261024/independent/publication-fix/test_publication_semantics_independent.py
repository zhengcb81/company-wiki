"""Neutral supplementary guards for publication delta, not new company facts."""
import pytest
from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact, reading_material_value

@pytest.mark.parametrize("period", ("next twelve months", "next eighteen months", "next twenty-four months", "next three years"))
def test_same_contract_conversion_accepts_numeric_word_period(period):
    text = "Our remaining performance obligations are expected to be recognized in the " + period + "."
    fact = detect_reading_business_fact(text)
    assert "contract_revenue_conversion" in fact.topics
    assert reading_material_value(fact) == "meaningful_fact"

@pytest.mark.parametrize("text", (
    "Our order backlog was $50 million, and our supplier will deliver machinery in the next twelve months.",
    "Our remaining obligations were $50 million for future employee payments in the next twelve months.",
))
def test_word_period_does_not_restore_unbound_keyword_fallback(text):
    assert "contract_revenue_conversion" not in detect_reading_business_fact(text).topics

@pytest.mark.parametrize("text", (
    "Our core values comprise customer service and research excellence.",
    "Our service platform aims to improve customer efficiency and reduce customer costs.",
))
def test_generic_material_stays_background(text):
    assert reading_material_value(detect_reading_business_fact(text)) == "description"
