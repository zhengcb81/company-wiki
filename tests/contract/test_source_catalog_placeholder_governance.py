"""Phase 15.4: dayu placeholder governance — metadata-only groups must not
create placeholder documents, and provider_company_id identity must be
propagated from the security master during ingestion.

These tests MUST fail against current code before the scanner fix.
"""

from __future__ import annotations

import json
from pathlib import Path


def _placeholder_portfolio(tmp_path: Path) -> Path:
    """A dayu portfolio group holding only meta.json (no preferred file)."""
    filing = tmp_path / "portfolio" / "Zijin" / "filings" / "fil_2025"
    filing.mkdir(parents=True)
    (filing / "meta.json").write_text(
        json.dumps(
            {
                "ticker": "Zijin",
                "document_id": "fil_2025",
                "document_kind": "annual_report",
                "source_title": "Zijin 2025 Annual Report",
                "filing_date": "2026-03-20",
                "fiscal_year": 2025,
                "ingest_complete": False,
                "files": [],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path / "portfolio"


def test_scan_does_not_create_placeholder_document_for_manifest_only_group(tmp_path):
    """A dayu group holding only filing_manifest.json (no preferred file) must
    NOT produce a document either: manifest.json is a pipeline listing, not a
    primary document (Phase 15.4, real-catalog finding)."""
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        RootSpec,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    project = tmp_path / "project"
    portfolio = tmp_path / "portfolio"
    filings = portfolio / "601899" / "filings"
    filings.mkdir(parents=True)
    (filings / "filing_manifest.json").write_text("{}", encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),),
        )
    )
    catalog.scan()

    assert catalog.query(limit=10) == []

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="601899",
            market="CN",
            security_id="601899",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-31",
        )
    )
    assert result.status is ResolutionStatus.MISSING
    assert result.reason == "no_existing_source_satisfies_request"


def test_scan_does_not_create_placeholder_document_for_metadata_only_group(tmp_path):
    """A dayu group with only meta.json (no preferred file) must NOT produce
    a document, so re-scanning a stale dayu portfolio never re-creates
    placeholder documents (Phase 15.4)."""
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        RootSpec,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    project = tmp_path / "project"
    portfolio = _placeholder_portfolio(tmp_path)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),),
        )
    )
    catalog.scan()

    documents = list(catalog.query(limit=100))
    assert documents == []

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


def test_scan_propagates_identity_from_provider_company_id(tmp_path):
    """A dayu meta.json carrying provider_company_id (the security-master
    org id) must get market/security_id propagated into the ingested document
    metadata, so identity checks pass instead of failing closed (Phase 15.4)."""
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        RootSpec,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    project = tmp_path / "project"
    catalog_dir = project / ".source_catalog"
    master_dir = catalog_dir / "security_master"
    master_dir.mkdir(parents=True)
    (master_dir / "cn.json").write_text(
        json.dumps(
            {
                "market": "CN",
                "record_count": 1,
                "records": [
                    {
                        "active": True,
                        "aliases": [],
                        "canonical_name": "紫金矿业",
                        "exchange": "SSE",
                        "identifiers": {
                            "cninfo_category": "A股",
                            "org_id": "9900004143",
                        },
                        "market": "CN",
                        "schema_version": "1.0",
                        "security_id": "601899",
                        "source_name": "cninfo",
                        "source_record_id": "9900004143",
                        "source_url": (
                            "https://www.cninfo.com.cn/new/data/szse_stock.json"
                        ),
                        "ticker": "601899",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    portfolio = tmp_path / "portfolio"
    filing = portfolio / "Zijin" / "filings" / "fil_2025"
    filing.mkdir(parents=True)
    primary = filing / "annual.htm"
    primary.write_text("<html>Zijin FY2025 annual report</html>", encoding="utf-8")
    (filing / "meta.json").write_text(
        json.dumps(
            {
                "ticker": "Zijin",
                "document_id": "fil_2025",
                "provider_company_id": "CNINFO:9900004143",
                "document_kind": "annual_report",
                "source_title": "Zijin 2025 Annual Report",
                "filing_date": "2026-03-20",
                "fiscal_year": 2025,
                "ingest_complete": True,
                "primary_document": "annual.htm",
                "files": [{"name": "annual.htm", "source": "original"}],
            }
        ),
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=catalog_dir,
            roots=(RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),),
        )
    )
    catalog.scan()

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
    assert result.status is ResolutionStatus.REUSED_EQUIVALENT
    assert len(result.matches) == 1
