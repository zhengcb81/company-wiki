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
