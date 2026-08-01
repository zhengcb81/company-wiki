"""Contracts for query-first source reuse and revenue-capture handoff."""

from __future__ import annotations

import json
from pathlib import Path


def _company_catalog(tmp_path: Path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    company = project / "companies"
    external = tmp_path / "external"
    source = (
        company
        / "Acme"
        / "raw"
        / "financial_reports"
        / "annual"
        / "2026-02-20_Acme_2025_annual_report.txt"
    )
    source.parent.mkdir(parents=True)
    source.write_text("ACME FY2025 audited annual report.", encoding="utf-8")
    external.mkdir()
    (external / "different-name.txt").write_bytes(source.read_bytes())
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec("company_raw", company, "company_raw", priority=10),
                RootSpec("external", external, "directory", priority=30),
            ),
        )
    )
    catalog.scan()
    return catalog, source


def _dayu_catalog(tmp_path: Path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    portfolio = tmp_path / "dayu" / "portfolio"
    filing = portfolio / "ACME" / "filings" / "fil_2025"
    filing.mkdir(parents=True)
    primary = filing / "annual.htm"
    primary.write_text("<html><body>ACME FY2025 annual report.</body></html>", encoding="utf-8")
    meta = {
        "ticker": "ACME",
        "market": "US",
        "security_id": "ACME",
        "document_id": "fil_2025",
        "accession_number": "0001234567-26-000001",
        "provider": "sec",
        "source_title": "ACME 2025 Annual Report",
        "form_type": "10-K",
        "filing_date": "2026-02-20",
        "fiscal_year": 2025,
        "fiscal_period": "FY",
        "primary_document": "annual.htm",
        "selected_primary_document": "annual.htm",
        "ingest_complete": True,
        "source_url": "https://www.sec.gov/Archives/edgar/data/1234567/annual.htm",
        "files": [{"name": "annual.htm", "source": "original"}],
    }
    (filing / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),),
        )
    )
    catalog.scan()
    return catalog, primary


def test_resolver_reuses_existing_exact_copy_without_downloader(tmp_path):
    from company_wiki.source_catalog import (
        ResolutionStatus,
        SourceRequest,
        SourceResolver,
    )

    catalog, canonical_path = _company_catalog(tmp_path)
    request = SourceRequest(
        entity="Acme",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
    )

    result = SourceResolver(catalog).resolve(request)

    assert result.status is ResolutionStatus.REUSED_EQUIVALENT
    assert result.download_required is False
    assert result.reason == "one_existing_source_satisfies_semantic_request"
    assert result.request_id == request.request_id
    assert len(result.matches) == 1
    handle = result.matches[0]
    assert Path(handle.canonical_path) == canonical_path
    assert handle.exact_duplicate_location_count == 1
    assert handle.content_sha256 == handle.source_id.rsplit(":", 1)[-1]
    assert handle.capture_ready is False
    assert handle.missing_capture_fields == ("https_url",)


def test_resolver_prefers_strong_provider_identity_and_builds_capture_ready_handle(tmp_path):
    from company_wiki.source_catalog import ResolutionStatus, SourceRequest, SourceResolver

    catalog, primary = _dayu_catalog(tmp_path)
    request = SourceRequest(
        entity="ACME",
        market="US",
        document_kind="annual_report",
        form_type="10-K",
        fiscal_year=2025,
        provider="sec",
        provider_document_id="0001234567-26-000001",
        as_of_date="2026-07-18",
    )

    result = SourceResolver(catalog).resolve(request)

    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.download_required is False
    handle = result.matches[0]
    assert handle.provider == "sec"
    assert handle.provider_document_id == "0001234567-26-000001"
    assert handle.https_url.startswith("https://www.sec.gov/")
    assert Path(handle.canonical_path) == primary
    assert handle.capture_ready is True
    assert handle.published_date == "2026-02-20"
    assert handle.fiscal_year == 2025
    assert handle.form_type == "10-K"
    assert handle.snapshot_sha256 == handle.content_sha256


def test_resolver_enforces_as_of_date_and_does_not_reuse_future_source(tmp_path):
    from company_wiki.source_catalog import ResolutionStatus, SourceRequest, SourceResolver

    catalog, _ = _dayu_catalog(tmp_path)
    request = SourceRequest(
        entity="ACME",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-01-31",
    )

    result = SourceResolver(catalog).resolve(request)

    assert result.status is ResolutionStatus.MISSING
    assert result.download_required is True
    assert result.reason == "only_sources_published_after_as_of_date"
    assert result.matches == ()


def test_resolver_returns_ambiguous_instead_of_guessing_between_semantic_matches(tmp_path):
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        RootSpec,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    project = tmp_path / "project"
    company = project / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    company.mkdir(parents=True)
    (company / "2026-02-20_Acme_2025_annual_report_A.txt").write_text(
        "first bytes", encoding="utf-8"
    )
    (company / "2026-02-21_Acme_2025_annual_report_B.txt").write_text(
        "second bytes", encoding="utf-8"
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", project / "companies", "company_raw"),),
        )
    )
    catalog.scan()

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="Acme",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
    )

    assert result.status is ResolutionStatus.AMBIGUOUS
    assert result.download_required is False
    assert result.reason == "multiple_existing_sources_match_semantic_request"
    assert len(result.matches) == 2


def test_source_request_id_is_deterministic_and_action_independent():
    from company_wiki.source_catalog import SourceRequest

    first = SourceRequest(
        entity="ACME",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=False,
    )
    second = SourceRequest(
        entity="ACME",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=True,
    )
    other_security = SourceRequest(
        entity="ACME",
        security_id="ACM.A",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=True,
    )

    assert first.request_id == second.request_id
    assert first.request_id != other_security.request_id
    assert first.to_dict()["schema_version"] == "1.0"


def _placeholder_catalog(tmp_path: Path, meta: dict, *, with_primary: bool = False):
    """A dayu portfolio directory holding meta.json (and optionally a primary
    file).  Without a primary file it is the Phase 15.3 placeholder-document
    shape; with one it is a real document whose metadata may contradict the
    request identity."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    portfolio = tmp_path / "dayu" / "portfolio"
    filing = portfolio / "Zijin" / "filings" / "fil_2025"
    filing.mkdir(parents=True)
    if with_primary:
        (filing / "annual.htm").write_text(
            "<html>Zijin FY2025 annual report</html>", encoding="utf-8"
        )
        meta.setdefault("primary_document", "annual.htm")
        meta.setdefault("ingest_complete", True)
        meta.setdefault("files", [{"name": "annual.htm", "source": "original"}])
    (filing / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),),
        )
    )
    catalog.scan()
    return catalog


def test_resolver_missing_identity_metadata_is_not_identity_conflict(tmp_path):
    """A document with no market/security_id metadata and no assertion must
    resolve MISSING (download allowed), not IDENTITY_CONFLICT (Phase 15.3)."""
    from company_wiki.source_catalog import (
        ResolutionStatus,
        SourceRequest,
        SourceResolver,
    )

    catalog = _placeholder_catalog(
        tmp_path,
        {
            "ticker": "Zijin",
            "document_id": "fil_2025",
            "document_kind": "annual_report",
            "source_title": "Zijin 2025 Annual Report",
            "filing_date": "2026-03-20",
            "fiscal_year": 2025,
            "ingest_complete": False,
            "files": [],
        },
    )

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="Zijin",
            market="CN",
            security_id="601899",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-31",
        )
    )

    assert result.status is ResolutionStatus.MISSING
    assert result.reason == "no_existing_source_satisfies_request"
    assert result.download_required is True
    assert result.download_allowed is False


def test_resolver_contradictory_market_is_still_identity_conflict(tmp_path):
    """A document whose metadata contradicts the request identity (market HK vs
    CN) must stay IDENTITY_CONFLICT and never reach the downloader (Phase 15.3
    control group: true conflicts remain fail-closed)."""
    from company_wiki.source_catalog import (
        ResolutionStatus,
        SourceRequest,
        SourceResolver,
    )

    catalog = _placeholder_catalog(
        tmp_path,
        {
            "ticker": "Zijin",
            "market": "HK",
            "security_id": "02899",
            "document_id": "fil_2025",
            "document_kind": "annual_report",
            "source_title": "Zijin 2025 Annual Report",
            "filing_date": "2026-03-20",
            "fiscal_year": 2025,
        },
        with_primary=True,
    )

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="Zijin",
            market="CN",
            security_id="601899",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-31",
        )
    )

    assert result.status is ResolutionStatus.IDENTITY_CONFLICT
    assert result.reason == "identity_mismatch_market_or_security_id"
    assert result.download_required is False
