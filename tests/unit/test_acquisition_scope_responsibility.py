"""Request scope rejects explicit conflicts without requiring extra fields."""

from dataclasses import replace

import pytest

from company_wiki.source_catalog.acquisition import DownloadCandidate
from company_wiki.source_catalog.acquisition_validation import candidate_scope_problem
from company_wiki.source_catalog.resolver import SourceRequest


def _case():
    request = SourceRequest(entity="Acme Inc.", market="US", document_kind="annual_report",
                            as_of_date="2026-10-08", fiscal_year=2025)
    candidate = DownloadCandidate(candidate_id="selected", provider="sec", provider_document_id="doc-1",
                                  market="US", entity="ACME INC", title="2025 annual report",
                                  source_url="https://sec.gov/2025", document_kind="annual_report",
                                  filing_date=None, fiscal_year=2025)
    return request, candidate


def test_unspecified_market_is_not_a_conflicting_market():
    request, candidate = _case()
    assert candidate_scope_problem(replace(request, market=None), candidate) is None


def test_punctuation_and_case_share_one_company_comparison():
    request, candidate = _case()
    assert candidate_scope_problem(request, candidate) is None


@pytest.mark.parametrize("mutation,field", [
    ({"market": "HK"}, "market"), ({"entity": "Other Inc"}, "entity"),
    ({"fiscal_year": 2024}, "fiscal_year"), ({"document_kind": "quarterly_report"}, "document_kind"),
])
def test_explicit_wrong_target_is_still_rejected(mutation, field):
    request, candidate = _case()
    assert candidate_scope_problem(request, replace(candidate, **mutation)) == field


def test_requested_period_and_form_must_be_present_on_candidate():
    request, candidate = _case()
    request = replace(request, fiscal_period="FY", form_type="20-F")
    assert candidate_scope_problem(request, candidate) == "fiscal_period"
    candidate = replace(candidate, fiscal_period="FY")
    assert candidate_scope_problem(request, candidate) == "form_type"


def test_scoped_listing_candidate_must_carry_the_exact_market_code():
    request, candidate = _case()
    request = replace(request, schema_version="1.1", identity_scope="listing",
                      issuer_link_id="issuer-link-v1:" + "a" * 64, security_id="BABA")
    candidate = replace(candidate, security_id="BILI")
    assert candidate_scope_problem(request, candidate) == "security_id"


def test_explicit_security_id_is_checked_without_identity_scope():
    request, candidate = _case()
    request = replace(request, security_id="BABA")
    assert candidate_scope_problem(request, replace(candidate, security_id="BILI")) == "security_id"
    assert candidate_scope_problem(request, candidate) == "security_id"


def test_issuer_candidate_link_is_derived_from_current_market_listing():
    request, candidate = _case()
    request = replace(request, schema_version="1.1", identity_scope="issuer",
                      issuer_link_id="issuer-link-v1:" + "a" * 64)
    candidate = replace(candidate, security_id="BABA")
    link_id = request.issuer_link_id
    assert candidate_scope_problem(
        request, candidate,
        issuer_link_lookup=lambda market, code: link_id if (market, code) == ("US", "BABA") else None,
    ) is None
    wrong = replace(candidate, security_id="BILI")
    assert candidate_scope_problem(
        request, wrong,
        issuer_link_lookup=lambda market, code: "issuer-link-v1:" + "b" * 64,
    ) == "issuer_link_id"
