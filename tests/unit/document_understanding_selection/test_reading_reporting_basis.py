"""A source-defined reporting basis is useful without becoming a result."""

from hashlib import sha256

import pytest

from company_wiki.source_catalog.narrative_business_policy import (
    _reading_clauses,
    detect_reading_business_fact,
)
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_catalog.narrative_reading import _admitted
from company_wiki.source_catalog.narrative_source_purpose import (
    NON_OPERATING_PURPOSES,
    source_purpose,
)
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256


def unit(text: str, index: int = 0):
    digest = sha256(b"source-reporting-basis").hexdigest()
    return _make_unit(
        source_id=source_id_for_sha256(digest),
        parser_version="1.0.0",
        coordinates=EvidenceCoordinates(page_number=1, paragraph_index=index),
        raw_text=text,
        unit_kind="html_paragraph",
        source_role="company_filing",
        language="en",
        metadata={},
    )


@pytest.mark.parametrize("text", (
    "Our service bookings growth: for commercial cloud services, sum of revenue "
    "growth plus changes in deferred revenue and contracted amounts not yet billed.",
    "Our remaining performance obligation: commercial revenue allocated to remaining "
    "customer services, including unearned revenue and amounts invoiced and recognized "
    "as revenue in future periods.",
))
def test_company_metric_definitions_are_readable_without_becoming_actual_metrics(text):
    fact = detect_reading_business_fact(text)

    assert fact.eligible
    assert fact.purpose == "operating_metric_basis"
    assert any(reason.startswith("reporting_metric_definition") for reason in fact.reasons)
    assert not {"operating_quantity", "operating_metric_change", "business_revenue_measure"} & set(fact.reasons)
    assert source_purpose(text) not in NON_OPERATING_PURPOSES


def test_updated_reporting_definition_survives_a_long_flat_native_paragraph():
    text = (
        "Azure revenue growth metric definition has been updated to reflect a move "
        "of services to a different reported business. "
        + "Prior metric descriptions and scope notes remain source context. " * 45
    )
    assert len(text) > 1200

    clauses = _reading_clauses(text)
    fact = detect_reading_business_fact(text)

    assert clauses and "Azure revenue growth metric definition" in clauses[0]
    assert fact.eligible
    assert "reporting_definition_change" in fact.reasons
    assert "reporting_metric_definition" in fact.reasons
    assert "operating_metric_change" not in fact.reasons
    assert _admitted(unit(text), {"section_role": "business"}, "background", fact=fact)[0]


def test_mechanical_outlook_recast_is_retained_without_inventing_growth():
    text = (
        "Our FY28 Q1 revenue outlook has only mechanical adjustments for the reporting "
        "changes; our total company revenue outlook is unchanged."
    )
    fact = detect_reading_business_fact(text)

    assert fact.eligible
    assert "reporting_outlook_recast" in fact.reasons
    assert "source_revenue_guidance" not in fact.reasons
    assert "operating_metric_change" not in fact.reasons
    assert _admitted(unit(text), {"section_role": "business"}, "background", fact=fact)[0]


@pytest.mark.parametrize("text, reason", (
    ("The group has only one operating segment.", "reporting_segment_scope"),
    ("As at June 30, the group had no future material investments or capital asset plans.",
     "future_investment_disclosure"),
))
def test_reporting_scope_and_future_investment_limits_are_preserved(text, reason):
    fact = detect_reading_business_fact(text)

    assert fact.eligible
    assert reason in fact.reasons
    assert source_purpose(text) not in NON_OPERATING_PURPOSES
    assert _admitted(unit(text), {"section_role": "business"}, "background", fact=fact)[0]


@pytest.mark.parametrize("text", (
    "An accounting textbook defines a revenue forecast as a prediction.",
    "Our cash balance was $25 million.",
    "The auditor tested controls over revenue allocations to performance obligations.",
))
def test_generic_definitions_balances_and_audit_statements_remain_out_of_business_reading(text):
    fact = detect_reading_business_fact(text)

    assert not fact.eligible


def test_public_selector_emits_the_original_metric_definition_span():
    text = "Our remaining performance obligation: commercial revenue allocated to remaining "
    text += "customer services, including unearned revenue and amounts invoiced in future periods."
    digest = sha256(b"source-reporting-basis-selection").hexdigest()
    parsed = DocumentStructure(
        source_id_for_sha256(digest), digest, "en", (unit(text),),
        page_count=1, pages_read=1, mime_type="text/html",
    )

    result = select_narrative_evidence(
        parsed, title="Investor metrics", existing_kind="ir", selector_version="0.9.0"
    )

    assert text in [span.raw_text for span in result.evidence_spans]


def test_multi_metric_definition_is_not_misclassified_as_reported_growth():
    text = (
        "Commercial bookings growth: sum of revenue growth for commercial cloud "
        "services plus changes in deferred revenue and contracted amounts not yet "
        "billed. Commercial remaining performance obligation: revenue allocated "
        "to remaining customer services, including amounts expected to be recognized "
        "in future periods."
    )
    fact = detect_reading_business_fact(text)

    assert fact.eligible
    assert "reporting_metric_definition" in fact.reasons
    assert "operating_metric_change" not in fact.reasons
    assert "business_revenue_measure" not in fact.reasons


@pytest.mark.parametrize("text", (
    "Commercial bookings growth: sum of service revenue growth and our paid seats growth.",
    "Commercial bookings growth: sum of service revenue growth and our paid seats growth, "
    "which represents the change in subscriptions.",
))
def test_metric_formula_with_coordinated_metric_noun_is_not_a_new_observed_fact(text):
    fact = detect_reading_business_fact(text)

    assert fact.eligible
    assert "reporting_metric_definition" in fact.reasons
    assert "operating_metric_change" not in fact.reasons


@pytest.mark.parametrize("text", (
    "The auditor tested revenue controls: number of samples included 40 contracts.",
    "Employee revenue training: includes instructions for reviewing deferred revenue.",
))
def test_audit_and_training_labels_do_not_become_metric_definitions(text):
    fact = detect_reading_business_fact(text)

    assert not fact.eligible
    assert "reporting_metric_definition" not in fact.reasons
    assert source_purpose(text) not in {
        "operating_metric_basis", "operating_guidance", "operating_structure_basis",
        "operating_investment_disclosure",
    }


@pytest.mark.parametrize("text", (
    "Microsoft 365 commercial seat growth metric definition has been updated "
    "to include paid GitHub seats.",
    "Microsoft 365 commercial seat growth: the number of Microsoft 365 "
    "Commercial seats and GitHub Cloud seats at end of period where seats "
    "are paid users covered by a subscription.",
))
def test_growth_in_a_metric_definition_label_is_not_an_observed_change(text):
    fact = detect_reading_business_fact(text)

    assert fact.eligible
    assert "reporting_metric_definition" in fact.reasons
    assert "operating_metric_change" not in fact.reasons


@pytest.mark.parametrize("text", (
    "The auditor tested revenue: includes manual inspection of contract samples.",
    "Audit of revenue: includes contract sample testing.",
    "The Auditor Tested Revenue: includes manual inspection of contract samples.",
    "Training for revenue: includes instructions for reviewing deferred revenue.",
    "Training for Revenue: includes instructions for reviewing deferred revenue.",
))
def test_verb_or_preposition_led_revenue_labels_do_not_define_metrics(text):
    fact = detect_reading_business_fact(text)

    assert not fact.eligible
    assert "reporting_metric_definition" not in fact.reasons
    assert source_purpose(text) not in {
        "operating_metric_basis", "operating_guidance", "operating_structure_basis",
        "operating_investment_disclosure",
    }


@pytest.mark.parametrize("text", (
    "Paid seats: number of licensed users, and our paid seats increased 20% to "
    "240 million during the quarter.",
    "Paid seats: number of licensed users and our paid seats increased 20% to "
    "240 million during the quarter.",
    "Paid seats: number of licensed users and our paid seats growth increased 20% "
    "to 240 million during the quarter.",
))
def test_real_metric_change_outside_definition_stays_readable_in_same_clause(text):
    fact = detect_reading_business_fact(text)

    assert fact.eligible
    assert "reporting_metric_definition" in fact.reasons
    assert "operating_metric_change" in fact.reasons
