"""ADR-008 Strategy B: config-driven reusable root kinds.

Adding a root *kind* to ``reusable_root_kinds`` makes every already-indexed
document under such roots a direct reuse candidate for the resolve pipeline
(no download, no promotion). The default remains company_raw only.
"""

from __future__ import annotations

import json
from pathlib import Path


def _dayu_catalog(tmp_path: Path, reusable_kinds: tuple[str, ...]):
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
            reusable_root_kinds=reusable_kinds,
        )
    )
    catalog.scan()
    return catalog, primary


def _request():
    from company_wiki.source_catalog import SourceRequest

    return SourceRequest(
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


def test_dayu_portfolio_reused_when_kind_is_config_driven(tmp_path):
    """Whitelisting dayu_portfolio in reusable_root_kinds makes the indexed
    portfolio document directly reusable: REUSED + capture_ready handle whose
    canonical_path lives under the portfolio root."""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog, primary = _dayu_catalog(tmp_path, ("company_raw", "dayu_portfolio"))

    result = SourceResolver(catalog).resolve(_request())

    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.download_required is False
    assert len(result.matches) == 1
    handle = result.matches[0]
    assert handle.capture_ready is True
    assert Path(handle.canonical_path) == primary
    assert handle.https_url.startswith("https://www.sec.gov/")
    assert not handle.missing_capture_fields


def test_dayu_portfolio_excluded_by_default(tmp_path):
    """Default reusable_root_kinds (company_raw only) keeps portfolio
    documents non-reusable: MISSING (the legacy fail-closed semantic)."""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog, _ = _dayu_catalog(tmp_path, ("company_raw",))

    result = SourceResolver(catalog).resolve(_request())

    assert result.status is ResolutionStatus.MISSING
    assert result.download_required is True


def test_stale_reusable_document_with_missing_file_is_not_reused(tmp_path):
    """A whitelisted document whose file vanished between scans must not be
    served as reusable (staleness guard in handle construction)."""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog, primary = _dayu_catalog(tmp_path, ("company_raw", "dayu_portfolio"))
    primary.unlink()  # dayu-agent deleted the file after the scan

    result = SourceResolver(catalog).resolve(_request())

    assert result.status is ResolutionStatus.MISSING
    assert result.download_required is True
