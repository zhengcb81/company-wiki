"""Phase 16.1: scanner source_url enrichment.

RED contracts: dayu SEC documents get an EDGAR URL constructed from
accession_number; company_raw documents whose sidecar lacks a URL get the
URL from the matching dayu portfolio meta.json.
"""

from __future__ import annotations

import json
from pathlib import Path


def _dayu_sec_catalog(tmp_path: Path, meta: dict):
    """A dayu portfolio filing group with a primary file and SEC-style meta."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    portfolio = tmp_path / "dayu" / "portfolio"
    filing = portfolio / "MDB" / "filings" / "fil_x"
    filing.mkdir(parents=True)
    (filing / meta["primary_document"]).write_text(
        "<html>MDB annual report</html>", encoding="utf-8"
    )
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


def test_dayu_sec_document_gets_edgar_url_from_accession(tmp_path):
    """A dayu meta.json without source_url but with SEC accession_number must
    get a deterministically constructed EDGAR URL (Phase 16.1)."""
    from company_wiki.source_catalog import ResolutionStatus, SourceRequest, SourceResolver

    catalog = _dayu_sec_catalog(
        tmp_path,
        {
            "ticker": "MDB",
            "document_id": "fil_x",
            "company_id": "1441816",
            "accession_number": "0001441816-26-000059",
            "primary_document": "mdb-20260131.htm",
            "document_kind": "annual_report",
            "source_title": "MDB 10-K",
            "filing_date": "2026-03-11",
            "fiscal_year": 2026,
            "ingest_complete": True,
            "files": [{"name": "mdb-20260131.htm", "source": "original"}],
        },
    )

    docs = catalog.query(limit=10)
    assert len(docs) == 1
    dayu_meta = (docs[0].get("metadata") or {}).get("dayu_meta") or {}
    assert dayu_meta.get("source_url") == (
        "https://www.sec.gov/Archives/edgar/data/0001441816/"
        "000144181626000059/mdb-20260131.htm"
    )


def test_company_raw_sidecar_without_url_gets_dayu_meta_url(tmp_path):
    """A company_raw document whose sidecar lacks source_url must get the URL
    from the matching dayu portfolio meta.json (Phase 16.1)."""
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        RootSpec,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    project = tmp_path / "project"
    companies = project / "companies"
    portfolio = tmp_path / "dayu" / "portfolio"
    company = companies / "南大光电" / "raw" / "financial_reports" / "annual"
    company.mkdir(parents=True)
    (company / "2025-04-02_南大光电_2024年报.pdf").write_bytes(b"%PDF-1.7\nreal bytes")
    (company / "2025-04-02_南大光电_2024年报.pdf.source.json").write_text(
        json.dumps(
            {
                "market": "CN",
                "security_id": "南大光电",
                "source_title": "南大光电：2024年年度报告",
            }
        ),
        encoding="utf-8",
    )
    # matching dayu portfolio meta with a cninfo source_url
    filing = portfolio / "300346" / "filings" / "fil_cn_x"
    filing.mkdir(parents=True)
    (filing / "2024年报.pdf").write_bytes(b"%PDF-1.7\ndifferent dayu bytes")
    (filing / "meta.json").write_text(
        json.dumps(
            {
                "ticker": "300346",
                "company_name": "南大光电",
                "source_provider": "cninfo",
                "source_id": "1225087469",
                "source_url": "http://static.cninfo.com.cn/finalpage/2025-04-02/1225087469.PDF",
                "source_title": "南大光电：2024年年度报告",
            }
        ),
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10),
                RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),
            ),
        )
    )
    catalog.scan()

    docs = catalog.query(limit=10)
    assert len(docs) == 2
    target = next(
        d
        for d in docs
        if "南大光电" in str((d.get("metadata") or {}).get("acquisition", {}).get("source_title") or "")
    )
    acquisition = (target.get("metadata") or {}).get("acquisition") or {}
    assert acquisition.get("source_url") == (
        "http://static.cninfo.com.cn/finalpage/2025-04-02/1225087469.PDF"
    )


def test_same_content_two_paths_prefers_metadata_with_url(tmp_path):
    """When the same content is ingested from two company_raw paths (an old
    sidecar without URL and a new sidecar with URL), the document metadata
    must keep the URL-bearing version regardless of scan order (Phase 16.5)."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    old = companies / "Acme" / "raw" / "financial_reports" / "z_old" / "2026-02-20_Acme_2025_annual.pdf"
    new = companies / "Acme" / "raw" / "financial_reports" / "annual" / "2026-02-20_sec_1_2025_annual.pdf"
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    payload = b"%PDF-1.7\nidentical bytes"
    old.write_bytes(payload)
    new.write_bytes(payload)
    (old.parent / (old.name + ".source.json")).write_text(
        json.dumps({"market": "CN", "security_id": "600519", "source_title": "old sidecar"}),
        encoding="utf-8",
    )
    (new.parent / (new.name + ".source.json")).write_text(
        json.dumps(
            {
                "market": "CN",
                "security_id": "600519",
                "source_title": "new sidecar",
                "source_url": "https://www.cninfo.com.cn/new/disclosure/detail?announcementId=2",
            }
        ),
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
        )
    )
    catalog.scan()

    docs = catalog.query(limit=10)
    assert len(docs) == 1
    acquisition = (docs[0].get("metadata") or {}).get("acquisition") or {}
    assert acquisition.get("source_url") == (
        "https://www.cninfo.com.cn/new/disclosure/detail?announcementId=2"
    )
