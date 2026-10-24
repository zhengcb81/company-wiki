"""Development RED probes for existing pure meaning ports; not a new oracle.

Source selection/model tasks still need the concentrated acceptance in report.md.
These probes contain no company names, source amounts, provider calls or IO.
"""

import pytest

from company_wiki.source_catalog.narrative_business_policy import (
    detect_reading_business_fact,
    reading_financial_only,
)


@pytest.mark.parametrize(
    "text",
    [
        "Our service bookings growth: for commercial cloud services, sum of revenue "
        "growth plus changes in deferred revenue and contracted amounts not yet billed.",
        "Our remaining performance obligation: commercial revenue allocated to remaining "
        "customer services, including unearned revenue and amounts invoiced and recognized "
        "as revenue in future periods.",
        "Our cloud revenue growth metric definition has been updated to exclude the "
        "developer cloud service, which now moves to our business applications metric.",
        "Our FY28 Q1 revenue outlook has only mechanical adjustments for the reporting "
        "changes; our total company revenue outlook is unchanged.",
        "本集團的主要經營決策者審閱合併經營業績，因此本集團僅有一個經營分部。",
        "截至二零二五年六月三十日，本集團並無任何未來重大投資及資本資產計劃。",
    ],
    ids=["metric-definition", "rpo-composition-definition", "metric-scope-change",
         "mechanical-not-upgrade", "one-operating-segment", "no-future-material-investment"],
)
def test_source_bound_business_basis_is_readable_without_becoming_an_actual_metric(text):
    fact = detect_reading_business_fact(text)
    assert fact.eligible, "Source-owned operating basis is useful even without an event/amount"
    assert not reading_financial_only(text, fact)


@pytest.mark.parametrize(
    "text",
    [
        "An accounting textbook defines a revenue forecast as a prediction.",
        "Our cash balance was $25 million.",
        "The auditor tested controls over revenue allocations to performance obligations.",
    ],
    ids=["generic-definition", "financial-balance-only", "auditor-assertion"],
)
def test_basis_retention_must_not_admit_unrelated_generic_finance_or_audit(text):
    assert not detect_reading_business_fact(text).eligible


def test_existing_forward_revenue_outlook_is_still_a_plan_not_a_realized_level():
    fact = detect_reading_business_fact(
        "Our subscription revenue is expected to grow by 23% in constant currency."
    )
    assert fact.eligible
    assert fact.purpose == "operating_guidance"
    assert "source_revenue_guidance" in fact.reasons
