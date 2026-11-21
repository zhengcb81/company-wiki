"""SR-CWP: bounded incremental discovery over the real adapter surface."""

from __future__ import annotations

from dataclasses import replace
import json

import pytest

from company_wiki.source_catalog.acquisition import (
    AcquisitionCoordinator,
    AdapterRegistry,
    DownloadCandidate,
)
from company_wiki.source_catalog.adapter_process import AdapterProcessError
from company_wiki.source_catalog.incremental_discovery import (
    COVERAGE_COMPLETE,
    COVERAGE_PARTIAL,
    INCREMENTAL_DISCOVERY_REQUEST_SCHEMA,
    INCREMENTAL_DISCOVERY_SCHEMA,
    IncrementalDiscoveryRequest,
    IncrementalDiscoveryService,
)
from company_wiki.source_catalog.security_identity import SecurityMasterStore, SecurityRecord

from support.sr_cwp_fixtures import (
    ENTITY,
    FixtureDiscoveryAdapter,
    FixturePage,
    MARKET,
    SECURITY_ID,
    build_catalog,
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


def test_candidate_limit_resumes_inside_then_across_provider_pages(sr_cwp_catalog):
    """The page remainder and the next provider page are distinct resume points."""
    adapter = FixtureDiscoveryAdapter(pages=[
        FixturePage(candidates=(
            candidate(provider_document_id="annual-report.txt", document_kind="annual_report",
                      filing_date="2026-05-01"),
            candidate(provider_document_id="annual-report-revised.txt",
                      document_kind="annual_report", filing_date="2026-05-01", amended=True),
        ), next_cursor="1", covered_from="2026-01-01", covered_to="2026-05-31"),
        FixturePage(candidates=(
            candidate(provider_document_id="annual-other.txt", document_kind="annual_report",
                      filing_date="2026-05-02"),
        ), covered_from="2026-01-01", covered_to="2026-05-31"),
    ])
    service = _service(sr_cwp_catalog, adapter)
    limits = {
        "max_candidates": 1, "max_pages": 8, "max_requests": 8, "max_seconds": 60,
    }
    actual = []
    cursor = None
    for expected in ("annual-report.txt", "annual-report-revised.txt", "annual-other.txt"):
        response = service.discover(_request(limits=limits, cursor=cursor))
        assert response.coverage == COVERAGE_COMPLETE
        assert [c.provider_document_id for c in response.candidates] == [expected]
        if response.next_cursor:
            assert "discovery_candidate_limit_reached" in response.reason_codes
        actual.append(expected)
        cursor = response.next_cursor
    assert cursor is None
    assert len(actual) == len(set(actual)) == 3


def test_provider_failure_for_one_kind_keeps_other_kinds_and_partial_coverage(sr_cwp_catalog):
    class FilingOnly(FixtureDiscoveryAdapter):
        def discover_page(self, request, *, since_date=None):
            if request.document_kind == "investor_relations":
                failure = AdapterProcessError("no IR enumeration")
                failure.error_code = "provider_kind_unsupported"
                raise failure
            return super().discover_page(request, since_date=since_date)

    adapter = FilingOnly(pages=[FixturePage(
        candidates=(candidate(provider_document_id="annual-report.txt", document_kind="annual_report",
                              filing_date="2026-05-01"),),
        covered_from="2026-01-01", covered_to="2026-05-31",
    )])
    response = _service(sr_cwp_catalog, adapter).discover(_request(
        document_kinds=["investor_relations", "annual_report"],
    ))
    assert response.coverage == COVERAGE_PARTIAL
    assert [c.provider_document_id for c in response.candidates] == ["annual-report.txt"]
    assert response.next_cursor is None
    assert "discovery_failed:provider_kind_unsupported" in response.reason_codes


def test_download_only_adapters_remain_usable_and_discovery_does_not_download(sr_cwp_catalog):
    class DownloadOnly:
        name = "download-only"
        version = "1.0.0"

        def discover(self, _request):
            raise AssertionError("legacy download discovery must never run during enumeration")

        def fetch(self, _candidate, _directory):
            raise AssertionError("metadata enumeration never fetches originals")

    receipt = _service(sr_cwp_catalog, DownloadOnly()).discover(_request())
    assert receipt.coverage == COVERAGE_PARTIAL
    assert receipt.candidates == ()
    assert receipt.reason_codes == ("provider_metadata_only_unavailable",)


def test_ff_native_discovery_wire_binds_listing_and_keeps_quarter_proof(sr_cwp_catalog):
    store = SecurityMasterStore(sr_cwp_catalog.catalog.config.catalog_dir / "security_master")
    url = "https://provider.invalid/securities"
    store.write_market(MARKET, [SecurityRecord(
        canonical_name=ENTITY, market=MARKET, exchange="SSE", ticker=SECURITY_ID,
        security_id=SECURITY_ID, aliases=(), active=True, source_name="fixture",
        source_url=url, source_record_id=SECURITY_ID, identifiers={},
    )], retrieved_at="2026-05-30T00:00:00Z", sources=(url,))
    identity = {"entity_id": "stockwiki-company", "listing_id": "stockwiki-cn-listing",
                "market": MARKET, "ticker": SECURITY_ID, "exchange": "SSE"}
    adapter = FixtureDiscoveryAdapter(pages=[FixturePage(candidates=(
        candidate(provider_document_id="quarterly-report.txt", document_kind="quarterly_report",
                  filing_date="2026-05-01", fiscal_period="Q1"),
    ), covered_from="2026-01-01", covered_to="2026-05-31")])
    request = _request(identity=identity, document_kinds=["quarterly_report"], limits={
        "max_bytes": 4_000_000, "timeout_seconds": 45, "max_cost_usd": "0.00", "max_requests": 6,
    })
    assert request.limits.max_bytes == 4_000_000 and request.limits.max_seconds == 45
    receipt = _service(sr_cwp_catalog, adapter).discover(request).to_dict()
    assert receipt["scope"]["identity"] == identity
    assert receipt["coverage"] == COVERAGE_COMPLETE
    assert receipt["candidates"][0]["fiscal_period"] == {
        "fiscal_year": 2026, "name": "Q1", "fiscal_quarter": 1,
    }
    assert receipt["candidates"][0]["source_ref"] is None
    assert "revision_id" not in receipt["candidates"][0]
    assert adapter.requests[0]["entity"] == ENTITY
    assert adapter.requests[0]["mode"] == "latest_as_of"
    assert adapter.fetches == []


def test_discovery_reuses_a_legacy_exact_release_url_only_for_the_same_edition(tmp_path):
    original = "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0501/notice_c.pdf"
    other_language = original.replace("_c.pdf", "_e.pdf")
    state = build_catalog(tmp_path, sidecar_overrides={"annual-report.txt": {
        "market": "HK", "security_id": "00700", "source_url": original,
        "provider": None, "provider_document_id": None, "form_type": None, "language": "zh-HK",
    }})
    try:
        common = candidate(provider_document_id="HKEX-RELEASE", document_kind="annual_report",
                           filing_date="2026-05-01", market="HK", security_id="00700")
        chinese = replace(common, provider="hkexnews", source_url=original, form_type="FY", language="zh")
        english = replace(chinese, candidate_id="other-edition", provider_document_id="HKEX-ENGLISH",
                          source_url=other_language, language="en")
        adapter = FixtureDiscoveryAdapter(pages=[FixturePage(
            candidates=(chinese, english), covered_from="2026-01-01", covered_to="2026-05-31",
        )], market="HK")
        request = _request(source_market="HK", identity={
            "entity": ENTITY, "security_id": "00700", "identity_scope": None, "issuer_link_id": None,
        })
        receipt = _service(state, adapter).discover(request).to_dict()
        registered = state.refs["annual-report.txt"]
        assert receipt["candidates"][0]["source_ref"]["content_sha256"] == registered.content_sha256
        assert receipt["candidates"][1]["source_ref"] is None
        assert adapter.fetches == []
        # An exact path may have an explicit provider-version query. Never
        # discard that component and infer old bytes from the clean URL.
        revision = replace(chinese, source_url=original + "?revision=2")
        adapter = FixtureDiscoveryAdapter(pages=[FixturePage(candidates=(revision,))], market="HK")
        assert _service(state, adapter).discover(request).candidates[0].existing_source_ref is None
    finally:
        state.catalog.close()


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
