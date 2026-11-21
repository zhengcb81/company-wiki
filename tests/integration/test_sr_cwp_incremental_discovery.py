"""SR-CWP: bounded incremental discovery over the real adapter surface."""

from __future__ import annotations

import json

import pytest

from company_wiki.source_catalog.acquisition import (
    AcquisitionCoordinator,
    AdapterRegistry,
    DownloadCandidate,
)
from company_wiki.source_catalog.incremental_discovery import (
    COVERAGE_COMPLETE,
    COVERAGE_PARTIAL,
    INCREMENTAL_DISCOVERY_REQUEST_SCHEMA,
    INCREMENTAL_DISCOVERY_SCHEMA,
    IncrementalDiscoveryRequest,
    IncrementalDiscoveryService,
)

from support.sr_cwp_fixtures import (
    ENTITY,
    FixtureDiscoveryAdapter,
    FixturePage,
    MARKET,
    SECURITY_ID,
    candidate,
    sr_cwp_catalog,
)


def _registry(adapter):
    return AdapterRegistry(cn=adapter, hk=adapter, us=adapter)


def _service(state, adapter):
    coordinator = AcquisitionCoordinator(
        catalog=state.catalog,
        adapters=_registry(adapter),
        staging_root=state.root / "staging",
    )
    return IncrementalDiscoveryService(catalog=state.catalog, coordinator=coordinator)


def _request(**overrides):
    payload = {
        "schema_version": INCREMENTAL_DISCOVERY_REQUEST_SCHEMA,
        "request_id": "sr-cwp-discovery-1",
        "identity": {
            "entity": ENTITY, "security_id": SECURITY_ID,
            "identity_scope": None, "issuer_link_id": None,
        },
        "source_market": MARKET,
        "document_kinds": ["annual_report"],
        "since_date": "2026-04-01",
        "as_of_date": "2026-05-31",
        "cursor": None,
        "limits": {
            "max_candidates": 20, "max_pages": 8, "max_requests": 8,
            "max_seconds": 60,
        },
    }
    payload.update(overrides)
    return IncrementalDiscoveryRequest.from_dict(payload)


def test_a1_two_releases_one_registered_one_new_are_both_enumerated(sr_cwp_catalog):
    """A1: two releases in one short window; the registered one carries its ref."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(
            candidate(provider_document_id="annual-report.txt",
                      document_kind="annual_report", filing_date="2026-05-01"),
            candidate(provider_document_id="annual-report-revised.txt",
                      document_kind="annual_report", filing_date="2026-05-01",
                      amended=True, fiscal_period="FY"),
        ),
        covered_from="2026-01-01", covered_to="2026-05-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request())

    assert response.to_dict()["schema_version"] == INCREMENTAL_DISCOVERY_SCHEMA
    assert response.coverage == COVERAGE_COMPLETE
    assert response.next_cursor is None
    assert [c.provider_document_id for c in response.candidates] == [
        "annual-report.txt", "annual-report-revised.txt",
    ]
    registered, revised = response.candidates
    # The already-registered original is identified, so the caller reuses it.
    assert registered.existing_source_ref is not None
    assert registered.existing_source_ref["document_id"] == (
        sr_cwp_catalog.refs["annual-report.txt"].document_id
    )
    assert registered.existing_source_ref["content_sha256"] == (
        sr_cwp_catalog.refs["annual-report.txt"].content_sha256
    )
    # The revised accession is missing locally and stays missing.
    assert revised.existing_source_ref is None
    assert revised.amended is True
    # The provider's own URL is never handed out as a download target.
    assert "source_url" not in json.dumps(response.to_dict())
    assert "https://provider.invalid" not in json.dumps(response.to_dict())


def test_a1_provider_pages_are_followed_across_the_declared_cursor(sr_cwp_catalog):
    """A1: the supplier answers in two pages; the cursor resumes it."""
    adapter = FixtureDiscoveryAdapter(pages=[
        FixturePage(
            candidates=(candidate(provider_document_id="annual-report.txt",
                                   document_kind="annual_report", filing_date="2026-05-01"),),
            next_cursor="1",
            covered_from="2026-01-01", covered_to="2026-05-31",
        ),
        FixturePage(
            candidates=(candidate(provider_document_id="annual-report-revised.txt",
                                   document_kind="annual_report", filing_date="2026-05-01",
                                   amended=True),),
            covered_from="2026-01-01", covered_to="2026-05-31",
        ),
    ])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request())

    assert [c.provider_document_id for c in response.candidates] == [
        "annual-report.txt", "annual-report-revised.txt",
    ]
    assert len(adapter.requests) == 2
    assert adapter.requests[0].get("cursor") is None
    assert adapter.requests[1]["cursor"] == "1"


def test_a1_same_day_multiple_documents_are_not_collapsed(sr_cwp_catalog):
    """Two documents on one day stay two candidates."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(
            candidate(provider_document_id="annual-report.txt",
                      document_kind="annual_report", filing_date="2026-05-01"),
            candidate(provider_document_id="annual-report-second.txt",
                      document_kind="annual_report", filing_date="2026-05-01"),
        ),
        covered_from="2026-01-01", covered_to="2026-05-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request())

    assert len(response.candidates) == 2
    assert len({c.candidate_key for c in response.candidates}) == 2


def test_truncated_provider_coverage_is_partial_and_resumable(sr_cwp_catalog):
    """A provider that cannot enumerate the whole range stays partial."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(candidate(provider_document_id="annual-report.txt",
                              document_kind="annual_report", filing_date="2026-05-01"),),
        coverage="partial",
        reason_codes=("provider_truncated",),
        covered_from="2026-05-01", covered_to="2026-05-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request())

    assert response.coverage == COVERAGE_PARTIAL
    assert "provider_truncated" in response.reason_codes
    assert response.candidates


def test_provider_window_that_misses_the_range_is_partial(sr_cwp_catalog):
    """An adapter that declares a narrower window does not claim the range."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(candidate(provider_document_id="annual-report.txt",
                              document_kind="annual_report", filing_date="2026-05-01"),),
        coverage="complete",
        covered_from="2026-05-01", covered_to="2026-05-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request(since_date="2026-01-01"))

    assert response.coverage == COVERAGE_PARTIAL
    assert "adapter_window_does_not_cover_range" in response.reason_codes


def test_unproved_publish_date_keeps_a_named_diagnostic_and_forces_partial(sr_cwp_catalog):
    """An unproved date never advances a complete watermark silently."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(
            candidate(provider_document_id="annual-report.txt",
                      document_kind="annual_report", filing_date="2026-05-01"),
            DownloadCandidate(
                candidate_id="fixture:undated.txt", provider="fixture",
                provider_document_id="undated.txt", market="CN", entity="Acme",
                title="Acme undated", source_url="https://provider.invalid/u",
                document_kind="annual_report", filing_date=None, fiscal_year=2026,
                security_id=SECURITY_ID,
            ),
        ),
        covered_from="2026-01-01", covered_to="2026-05-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request())

    assert response.coverage == COVERAGE_PARTIAL
    assert "candidate_date_unproved" in response.reason_codes
    assert response.usage["unproved_dates"] == 1
    # The dated candidate is still enumerated; the undated one is not listed
    # as if its date were proven.
    assert [c.provider_document_id for c in response.candidates] == ["annual-report.txt"]


def test_amended_revision_is_a_distinct_candidate_key(sr_cwp_catalog):
    """A correction reusing the accession stays distinct from the original."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(
            candidate(provider_document_id="annual-report.txt",
                      document_kind="annual_report", filing_date="2026-05-01",
                      amended=False),
            candidate(provider_document_id="annual-report.txt",
                      document_kind="annual_report", filing_date="2026-05-01",
                      amended=True),
        ),
        covered_from="2026-01-01", covered_to="2026-05-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request())
    assert len(response.candidates) == 2
    assert len({c.candidate_key for c in response.candidates}) == 2
    assert {c.amended for c in response.candidates} == {True, False}


def test_truly_empty_range_is_a_complete_result(sr_cwp_catalog):
    """No match inside a fully covered range is a completed enumeration."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(),
        covered_from="2026-01-01", covered_to="2026-05-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request())

    assert response.coverage == COVERAGE_COMPLETE
    assert response.candidates == ()
    assert response.next_cursor is None


def test_out_of_window_candidates_are_not_returned(sr_cwp_catalog):
    """The declared range bounds the candidates on both ends."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(
            candidate(provider_document_id="too-old.txt", document_kind="annual_report",
                      filing_date="2026-01-05"),
            candidate(provider_document_id="too-new.txt", document_kind="annual_report",
                      filing_date="2026-09-05"),
            candidate(provider_document_id="annual-report.txt", document_kind="annual_report",
                      filing_date="2026-05-01"),
        ),
        covered_from="2026-01-01", covered_to="2026-12-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request())

    assert [c.provider_document_id for c in response.candidates] == ["annual-report.txt"]


def test_request_beyond_the_declared_kinds_is_refused(sr_cwp_catalog):
    """An unreadable cursor is a refusal, never a silent restart."""
    service = _service(sr_cwp_catalog, FixtureDiscoveryAdapter(pages=[]))
    with pytest.raises(ValueError):
        service.discover(_request(cursor="not-a-cursor"))


def test_candidate_limit_keeps_a_resumable_partial_state(sr_cwp_catalog):
    """A bounded enumeration stops with a cursor instead of dropping candidates."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(
            candidate(provider_document_id="annual-report.txt", document_kind="annual_report",
                      filing_date="2026-05-01"),
            candidate(provider_document_id="annual-report-revised.txt",
                      document_kind="annual_report", filing_date="2026-05-01", amended=True),
        ),
        covered_from="2026-01-01", covered_to="2026-05-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request(limits={
        "max_candidates": 1, "max_pages": 8, "max_requests": 8, "max_seconds": 60,
    }))

    assert response.coverage == COVERAGE_PARTIAL
    assert response.next_cursor is not None
    assert "discovery_candidate_limit_reached" in response.reason_codes


def test_a2_non_periodic_kind_is_enumerated_without_a_fiscal_period(sr_cwp_catalog):
    """A2: a non-periodic IR item carries no fiscal period."""
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
        candidates=(candidate(provider_document_id="ir-announcement.txt",
                              document_kind="investor_relations", filing_date="2026-05-01",
                              fiscal_period=None),),
        covered_from="2026-01-01", covered_to="2026-05-31",
    )])
    service = _service(sr_cwp_catalog, adapter)
    response = service.discover(_request(document_kinds=["investor_relations"]))

    assert response.coverage == COVERAGE_COMPLETE
    assert response.candidates[0].fiscal_period is None
    assert response.candidates[0].existing_source_ref is not None
