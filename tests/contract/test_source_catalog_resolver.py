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
    (company / "Acme" / "raw" / "financial_reports" / "annual" / "2026-02-20_Acme_2025_annual_report.txt.source.json").write_text(
        json.dumps({
            "market": "CN", "security_id": "600519", "source_title": "Acme 2025 Annual Report",
            "source_url": "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=600519&announcementId=1",
        }), encoding="utf-8")
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
    assert handle.capture_ready is True
    assert handle.https_url.startswith("https://www.cninfo.com.cn/")


def test_resolver_prefers_strong_provider_identity_and_builds_capture_ready_handle(tmp_path):
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        RootSpec,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    # A canonical company_raw document with a complete sidecar identity.
    project = tmp_path / "project"
    company = project / "companies" / "ACME" / "raw" / "financial_reports" / "annual"
    company.mkdir(parents=True)
    primary = company / "2026-02-20_ACME_2025_annual_report.htm"
    primary.write_text("<html>ACME FY2025 annual report.</html>", encoding="utf-8")
    (company / "2026-02-20_ACME_2025_annual_report.htm.source.json").write_text(
        json.dumps(
            {
                "market": "US",
                "security_id": "ACME",
                "source_title": "ACME 2025 Annual Report",
                "form_type": "10-K",
                "filing_date": "2026-02-20",
                "fiscal_year": 2025,
                "provider": "sec",
                "provider_document_id": "0001234567-26-000001",
                "source_url": "https://www.sec.gov/Archives/edgar/data/1/0001-26-000001/annual.htm",
            }
        ),
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", project / "companies", "company_raw"),),
        )
    )
    catalog.scan()
    request = SourceRequest(
        entity="ACME",
        market="US",
        security_id="ACME",
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


def test_resolver_does_not_reuse_capture_incomplete_document(tmp_path):
    """A company_raw document whose handle is not capture-ready (missing
    https_url) must not be offered as a reuse candidate: filing-fetch rejects
    such handles and would otherwise deadlock instead of downloading (Phase
    16.2)."""
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
    (company / "2026-02-20_Acme_2025_annual_report.pdf").write_bytes(
        b"%PDF-1.7\nreal bytes"
    )
    (company / "2026-02-20_Acme_2025_annual_report.pdf.source.json").write_text(
        json.dumps(
            {
                "market": "CN",
                "security_id": "Acme",
                "source_title": "Acme 2025 Annual Report",
            }
        ),
        encoding="utf-8",
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
            market="CN",
            security_id="Acme",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-31",
        )
    )

    assert result.status is ResolutionStatus.MISSING
    assert result.reason == "no_existing_source_satisfies_request"
    assert result.download_required is True


def test_resolver_does_not_reuse_dayu_portfolio_non_canonical_documents(tmp_path):
    """Documents ingested from the dayu portfolio live outside the canonical
    companies/ subtree; filing-fetch rejects such paths, so reuse-first must
    yield MISSING and let the download path proceed (MongoDB finding)."""
    from company_wiki.source_catalog import ResolutionStatus, SourceRequest, SourceResolver

    catalog, _ = _dayu_catalog(tmp_path)
    request = SourceRequest(
        entity="ACME",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        form_type="10-K",
        fiscal_year=2025,
        provider="sec",
        provider_document_id="0001234567-26-000001",
        as_of_date="2026-07-18",
    )

    result = SourceResolver(catalog).resolve(request)

    assert result.status is ResolutionStatus.MISSING
    assert result.reason == "no_existing_source_satisfies_request"
    assert result.download_required is True


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
    for name in ("2026-02-20_Acme_2025_annual_report_A", "2026-02-21_Acme_2025_annual_report_B"):
        (company / (name + ".txt.source.json")).write_text(
            json.dumps({
                "market": "CN", "security_id": "600519", "source_title": name,
                "source_url": f"https://www.cninfo.com.cn/new/disclosure/detail?announcementId={name}",
            }), encoding="utf-8")

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


# --- Phase 18.1: issuer-name anchoring (dual-class / same-issuer tickers) ---

_ALPHABET_SECURITY_MASTER = {
    "market": "US",
    "record_count": 2,
    "records": [
        {
            "active": True,
            "aliases": ["Alphabet"],
            "canonical_name": "Alphabet Inc.",
            "market": "US",
            "security_id": "GOOG",
            "ticker": "GOOG",
            "source_record_id": "0001652044",
            "identifiers": {"cik": "0001652044"},
        },
        {
            "active": True,
            "aliases": ["Alphabet"],
            "canonical_name": "Alphabet Inc.",
            "market": "US",
            "security_id": "GOOGL",
            "ticker": "GOOGL",
            "source_record_id": "0001652044",
            "identifiers": {"cik": "0001652044"},
        },
    ],
}


def _alphabet_catalog(tmp_path: Path, *, security_id: str):
    """A company_raw catalog with one Alphabet 10-K plus a security_master
    fixture that resolves GOOGL/GOOG to the same canonical issuer."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    company = (
        project / "companies" / "Alphabet Inc" / "raw" / "financial_reports" / "annual"
    )
    company.mkdir(parents=True)
    (company / "2026-02-05_Alphabet_2025_10K.htm").write_text(
        "<html>Alphabet FY2025 10-K</html>", encoding="utf-8"
    )
    (company / "2026-02-05_Alphabet_2025_10K.htm.source.json").write_text(
        json.dumps(
            {
                "market": "US",
                "security_id": security_id,
                "company_name": "Alphabet Inc.",
                "source_title": "Alphabet 2025 Annual Report",
                "form_type": "10-K",
                "fiscal_year": 2025,
                "provider": "sec",
                "provider_document_id": "0001652044-26-000001",
                "source_url": "https://www.sec.gov/Archives/edgar/data/1652044/000165204426000001/10k.htm",
            }
        ),
        encoding="utf-8",
    )
    security_master = project / ".source_catalog" / "security_master"
    security_master.mkdir(parents=True)
    (security_master / "us.json").write_text(
        json.dumps(_ALPHABET_SECURITY_MASTER), encoding="utf-8"
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", project / "companies", "company_raw"),),
        )
    )
    catalog.scan()
    return catalog


def test_resolver_anchors_ticker_to_issuer_canonical_name(tmp_path):
    """Phase 18.1: a GOOGL request must reuse the Alphabet document even though
    the document only carries the sibling ticker GOOG and the issuer name."""
    from company_wiki.source_catalog import ResolutionStatus, SourceRequest, SourceResolver

    catalog = _alphabet_catalog(tmp_path, security_id="GOOG")

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="GOOGL",
            market="US",
            document_kind="annual_report",
            form_type="10-K",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
    )

    assert result.status is ResolutionStatus.REUSED_EQUIVALENT
    assert len(result.matches) == 1
    assert result.matches[0].https_url.startswith("https://www.sec.gov/")


def test_resolver_matches_sibling_ticker_and_alias_of_same_issuer(tmp_path):
    """Phase 18.1 reverse: a GOOG request (document carries GOOGL) and an
    issuer-alias request (Alphabet) must both hit the same document."""
    from company_wiki.source_catalog import ResolutionStatus, SourceRequest, SourceResolver

    catalog = _alphabet_catalog(tmp_path, security_id="GOOGL")

    for entity in ("GOOG", "Alphabet"):
        result = SourceResolver(catalog).resolve(
            SourceRequest(
                entity=entity,
                market="US",
                document_kind="annual_report",
                form_type="10-K",
                fiscal_year=2025,
                as_of_date="2026-07-18",
            )
        )
        assert result.status is ResolutionStatus.REUSED_EQUIVALENT, entity
        assert len(result.matches) == 1, entity


def test_resolver_unknown_ticker_does_not_anchor_to_unrelated_issuer(tmp_path):
    """Phase 18.1 control: a ticker absent from security_master must not start
    matching the Alphabet document (fail-closed, no over-matching)."""
    from company_wiki.source_catalog import ResolutionStatus, SourceRequest, SourceResolver

    catalog = _alphabet_catalog(tmp_path, security_id="GOOG")

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="MSFT",
            market="US",
            document_kind="annual_report",
            form_type="10-K",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
    )

    assert result.status is ResolutionStatus.MISSING


def test_resolve_debug_trace_names_candidate_exclusion_reasons(tmp_path):
    """Phase 19.6: a non-reused resolution must carry a debug_trace naming each
    candidate that passed the entity gate and its exclusion reasons (identity /
    year / form / capture steps) plus the entity-gate reject count, so a
    not_found result explains itself."""
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
    (company / "2026-02-20_Acme_2025_annual_report.pdf").write_bytes(
        b"%PDF-1.7\nreal bytes"
    )
    (company / "2026-02-20_Acme_2025_annual_report.pdf.source.json").write_text(
        json.dumps(
            {
                "market": "CN",
                "security_id": "600519",
                "source_title": "Acme 2025 Annual Report",
            }
        ),
        encoding="utf-8",
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
            market="US",  # conflicts with the CN document identity
            document_kind="annual_report",
            fiscal_year=2024,  # mismatches the 2025 document
            as_of_date="2026-07-31",
        )
    )

    assert result.status is ResolutionStatus.IDENTITY_CONFLICT
    trace = result.to_dict().get("debug_trace")
    assert trace, "non-reused resolution must carry a debug_trace"
    joined = "\n".join(trace)
    assert "Acme 2025" in joined
    assert "identity_conflict" in joined
    assert "entity_gate_rejected" in joined
