"""RED contracts for source business meaning, separate from issuer vocabulary.

Canonical source units exercise real routing, admission, closure and budget.
No original, network, model, credential, production config or gold write.
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from company_wiki.document_understanding import understand_units  # noqa: E402
from company_wiki.source_catalog import narrative_evidence as selector  # noqa: E402
from company_wiki.source_catalog.narrative_document import DocumentStructure  # noqa: E402
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256  # noqa: E402

SHA = "e" * 64
SOURCE_ID = source_id_for_sha256(SHA)


def _unit(text, index, *, heading=None):
    return selector._make_unit(
        source_id=SOURCE_ID, parser_version="1.0.0",
        coordinates=EvidenceCoordinates(paragraph_index=index), raw_text=text,
        unit_kind="html_heading" if heading else "html_paragraph",
        source_role="company_filing", language="en",
        metadata={"source_locator": f"cwp-html-dom/1|n=0.{index}",
                  **({"tag_name": f"h{heading}", "heading_level": heading} if heading else {})},
    )


def _document(*texts):
    return DocumentStructure(SOURCE_ID, SHA, "en", tuple(_unit(text, i) for i, text in enumerate(texts)),
                             line_count=len(texts), mime_type="text/html")


def _select(document, *, limit=32):
    return selector.select_narrative_evidence(document, title="Annual report",
        existing_kind="annual_report", max_selected=limit, selector_version="0.9.0")


@pytest.mark.parametrize("text", [
    "The Helio hosting platform generates revenue primarily from consumption-based services, rather than per-seat subscriptions.",
    "Orion software revenue is affected mainly by active licensed seats and average revenue per user, not by metered compute usage.",
    "Our managed data platform charges customers based on storage consumed and computation used; the billing basis differs from fixed subscriptions.",
])
def test_actual_billing_basis_is_business_mechanism_even_with_the_word_revenue(text):
    result = _select(_document(text))
    assert [span.raw_text for span in result.evidence_spans] == [text]


@pytest.mark.parametrize("text", [
    "We operate our business using four reportable segments: Diagnostics, Instruments, Data Services, and Field Support.",
    "In February 2023, we changed the composition of our reporting segments and moved customer-support services into Data Services. Prior-year segment information was recast to conform to this presentation.",
])
def test_segment_scope_and_comparability_are_business_context_not_empty_financial_data(text):
    assert {span.raw_text for span in _select(_document(text)).evidence_spans} == {text}


@pytest.mark.parametrize("text", [
    "Managed hosting and data services revenue increased 19% driven by Helio consumption-based services growth of 27%; the product is included within the combined services line.",
    "Consumer service revenue grew 8% with 62 million paid subscribers, while Enterprise service revenue grew 16% with paid seats up 13%.",
])
def test_product_metric_nesting_and_operating_driver_explanation_are_not_finance_only(text):
    assert {span.raw_text for span in _select(_document(text)).evidence_spans} == {text}


def test_remaining_performance_obligations_conversion_keeps_future_period_and_units():
    text = (
        "Revenue allocated to remaining performance obligations was $ 2.7 billion as of March 31, 2026, "
        "including $ 2.2 billion of commercial contracts. We expect to recognize approximately 55 % "
        "of the remaining obligation revenue over the next 18 months and the remainder thereafter."
    )
    result = _select(_document(text))
    assert [span.raw_text for span in result.evidence_spans] == [text]
    assert "expect" in result.evidence_spans[0].raw_text
    assert "18 months" in result.evidence_spans[0].raw_text


def test_source_form_routes_to_actual_family_policy_instead_of_a_nominal_profile_with_fallback():
    units = (
        _unit("FORM 10-K", 0, heading=1),
        _unit("For the fiscal year ended March 31, 2026", 1),
        _unit("PART I", 2, heading=1),
        _unit("Item 1. Business", 3, heading=2),
        _unit("The Helio platform generates revenue from metered service usage.", 4),
    )
    pipeline = understand_units(units, source_id=SOURCE_ID, source_sha256=SHA,
        declared_kind="annual_report", mime_type="text/html", language="en")
    assert pipeline["route"]["family"] == "annual"
    view = pipeline["reading_plan"]["unit_profiles"][units[-1].unit_id]
    assert view["family_policy"].get("id"), "actual source form should resolve a concrete reading family"
    assert any(component["kind"] == "family" for component in view["policy_components"])
    assert view["section_role"] == "business"


def test_source_detected_form_survives_split_native_item_number_and_business_heading():
    units = (
        _unit("FORM 10-K", 0, heading=1),
        _unit("For the fiscal year ended March 31, 2026", 1),
        _unit("PART I", 2, heading=1),
        _unit("Item 1", 3, heading=2),
        _unit("BUSINESS", 4, heading=3),
        _unit("Our platform generates revenue from metered service usage.", 5),
    )
    pipeline = understand_units(units, source_id=SOURCE_ID, source_sha256=SHA,
        declared_kind="annual_report", mime_type="text/html", language="en")
    assert pipeline["route"]["profile_id"] == "sec_10k"
    view = pipeline["reading_plan"]["unit_profiles"][units[-1].unit_id]
    assert view["family_policy"].get("id") == "sec_10k", (
        "a source-detected form must be carried once into policy resolution; "
        "split native headings must not force a second independent type guess"
    )
    assert view["section_role"] == "business"


def test_core_operating_mechanism_survives_generic_risk_crowding_in_the_same_priority_band():
    risks = [f"Our services are subject to disruptions in regional network {chr(65+i)} during the period."
             for i in range(12)]
    mechanism = "Our services depend on metered workload consumption rather than the number of licensed seats."
    package = _select(_document(*risks, mechanism), limit=4)
    assert mechanism in {span.raw_text for span in package.evidence_spans}
    assert len(package.evidence_spans) <= 4
    assert package.omitted_candidate_count > 0


def test_billing_model_embedded_in_product_description_gets_coverage_amid_repeated_activity_risks():
    risks = [f"Our service platforms expand customer access but remain subject to disruptions "
             f"across regional network {chr(65+i)} during the period." for i in range(12)]
    mechanism = (
        "Nimbus provides cloud services for computing, networking and storage. Customers can deploy "
        "applications using our worldwide infrastructure. Revenue of this service is mainly affected "
        "by consumption-based services, rather than by paid seats or fixed subscriptions."
    )
    package = _select(_document(*risks, mechanism), limit=4)
    assert mechanism in {span.raw_text for span in package.evidence_spans}
    assert len(package.evidence_spans) <= 4


@pytest.mark.parametrize("text", [
    "Revenue increased 19% to $ 8.4 billion. Net income increased 5% to $ 1.1 billion.",
    "Cash flow increased 7% during the year. Earnings per share rose 9%.",
    "Total revenue was $ 12 billion; a new product is described in an unrelated section.",
])
def test_routine_financial_numbers_and_unrelated_product_noun_are_not_business_mechanisms(text):
    assert not _select(_document(text)).evidence_spans


@pytest.mark.parametrize("text", [
    "云服务收入主要取决于客户实际使用量，采用按量计费，而办公软件采用按席位订阅计费。",
    "公司报告分部由设备、耗材和服务三个业务板块组成，2023年调整了分部口径并重述比较期间。",
    "平台业务收入增长21%，主要由客户使用量增长30%带动。",
    "剩余履约义务包括尚未开票的客户合同，预计未来18个月确认其中约55%的收入，其余在之后期间确认。",
])
def test_shared_relations_support_chinese_without_changing_the_original_text(text):
    assert [span.raw_text for span in _select(_document(text)).evidence_spans] == [text]


@pytest.mark.parametrize("text", [
    "Revenue increased 11%. Products are discussed in an unrelated section.",
    "Revenue increased 11%. A glossary elsewhere defines consumption-based services.",
    "Revenue was $ 900 million. The words paid seats appear in a list of terms.",
    "Cash flow increased 17%. Contract and pricing definitions are listed elsewhere.",
    "Revenue growth is driven by strong financial performance.",
    "A subscription is defined as a fixed agreement; consumption-based pricing is a generic billing definition.",
    "Revenue allocated to remaining performance obligations was $ 90 million, with no conversion schedule disclosed.",
    "Our service revenue grew 15% driven by happy customers and a great product philosophy.",
    "公司软件收入增长20%，主要由于客户满意和创新理念。",
    "The cash flow segments include financing cash movements and investing cash movements.",
    "Tax segments include domestic and foreign accruals.",
])
def test_unrelated_keywords_and_definitions_do_not_exempt_routine_finance(text):
    assert not _select(_document(text)).evidence_spans


def test_new_meaning_version_preserves_the_explicit_legacy_fact_detector():
    from company_wiki.source_catalog.narrative_business_policy import (
        READING_BUSINESS_POLICY_VERSION, detect_business_fact, detect_reading_business_fact,
    )
    text = "Orion software revenue is affected mainly by active licensed seats and average revenue per user."
    assert READING_BUSINESS_POLICY_VERSION
    assert not detect_business_fact(text).eligible
    assert detect_reading_business_fact(text).eligible
    assert not _select(_document(text)).reading_context["groups"][0].get("raw_text")
