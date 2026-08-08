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


def test_dayu_sec_document_gets_market_and_security_id(tmp_path):
    """A dayu SEC meta.json without market/security_id must get market="US"
    and security_id from its ticker so capture-ready handles can resolve
    (Alphabet 10-K pilot deadlock, Phase 17 checklist)."""
    catalog = _dayu_sec_catalog(
        tmp_path,
        {
            "ticker": "GOOG",
            "document_id": "fil_x",
            "company_id": "1652044",
            "accession_number": "0001652044-26-000018",
            "primary_document": "goog-20251231.htm",
            "document_kind": "annual_report",
            "source_title": "Alphabet Inc. 10-K 2025-12-31",
            "filing_date": "2026-02-05",
            "fiscal_year": 2025,
            "ingest_complete": True,
            "files": [{"name": "goog-20251231.htm", "source": "original"}],
        },
    )

    docs = catalog.query(limit=10)
    assert len(docs) == 1
    dayu_meta = (docs[0].get("metadata") or {}).get("dayu_meta") or {}
    assert dayu_meta.get("market") == "US"
    assert dayu_meta.get("security_id") == "GOOG"


def test_rescan_backfills_market_and_security_id_on_existing_document(tmp_path):
    """A dayu SEC document ingested before the identity backfill must gain
    market/security_id on rescan even when it already carries a source URL
    (Phase 17 pilot: Alphabet 10-K capture_ready deadlock)."""
    import sqlite3

    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    portfolio = tmp_path / "dayu" / "portfolio"
    filing = portfolio / "GOOG" / "filings" / "fil_x"
    filing.mkdir(parents=True)
    (filing / "goog-20251231.htm").write_text(
        "<html>GOOG 10-K</html>", encoding="utf-8"
    )
    meta = {
        "ticker": "GOOG",
        "document_id": "fil_x",
        "company_id": "1652044",
        "accession_number": "0001652044-26-000018",
        "primary_document": "goog-20251231.htm",
        "document_kind": "annual_report",
        "source_title": "Alphabet Inc. 10-K 2025-12-31",
        "filing_date": "2026-02-05",
        "fiscal_year": 2025,
        "ingest_complete": True,
        "files": [{"name": "goog-20251231.htm", "source": "original"}],
    }
    (filing / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    config = CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),),
    )
    catalog = SourceCatalog(config)
    catalog.scan()

    # Simulate a pre-fix ingestion: the document exists and carries a source
    # URL (Phase 16.1) but no market/security identity — the exact Alphabet
    # state that deadlocked capture_ready.
    conn = sqlite3.connect(config.catalog_dir / "catalog.sqlite3")
    row = conn.execute("SELECT metadata_json FROM documents LIMIT 1").fetchone()
    old_meta = json.loads(row[0])
    old_meta["dayu_meta"] = {
        **{k: v for k, v in meta.items() if k != "files"},
        "source_url": "https://www.sec.gov/Archives/edgar/data/0001652044/"
        "000165204426000018/goog-20251231.htm",
    }
    conn.execute("UPDATE documents SET metadata_json=?", (json.dumps(old_meta),))
    conn.commit()
    conn.close()

    catalog.scan()

    docs = catalog.query(limit=10)
    assert len(docs) == 1
    dayu_meta = (docs[0].get("metadata") or {}).get("dayu_meta") or {}
    assert dayu_meta.get("market") == "US"
    assert dayu_meta.get("security_id") == "GOOG"


def test_plain_rescan_re_enriches_existing_dayu_document(tmp_path):
    """ADR-008 Strategy B: a plain rescan (no file change, no location-row
    deletion) must re-enrich an already-indexed dayu_portfolio document with
    the full reuse metadata — document_kind via form_type mapping, fiscal_year,
    provider_document_id, security_id and market — so it becomes capture-ready.

    Guards against the documented operational trap: the scanner reuses the
    unchanged file's manifest for the location, but the document metadata is
    rebuilt each scan and prefer_new promotes the richer enriched copy.
    """
    import sqlite3

    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    portfolio = tmp_path / "dayu" / "portfolio"
    filing = portfolio / "03896" / "filings" / "fil_hk"
    filing.mkdir(parents=True)
    (filing / "annual.pdf").write_bytes(b"%PDF-1.7\nHK annual report bytes")
    meta = {
        "ticker": "3896",
        "market": "HK",
        "document_id": "fil_hk",
        "source_provider": "hkex",
        "source_id": "2026042301428",
        "form_type": "FY",
        "fiscal_year": 2025,
        "fiscal_period": "FY",
        "source_title": "Sample Co. 2025 Annual Report",
        "source_url": "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0423/2026042301428_c.pdf",
        "filing_date": "2026-04-23",
        "primary_document": "annual.pdf",
        "ingest_complete": True,
        "files": [{"name": "annual.pdf", "source": "original"}],
    }
    (filing / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    config = CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),),
    )
    catalog = SourceCatalog(config)
    catalog.scan()

    # Simulate a pre-ADR-008 ingestion: stored document metadata carries only
    # the minimal marker (no form_type/fiscal_year/provider_document_id/
    # security_id/market in dayu_meta).  The file on disk is untouched.
    conn = sqlite3.connect(config.catalog_dir / "catalog.sqlite3")
    row = conn.execute("SELECT metadata_json FROM documents LIMIT 1").fetchone()
    old_meta = json.loads(row[0])
    old_meta["dayu_meta"] = {
        "source_title": "Sample Co. 2025 Annual Report",
        "filing_date": "2026-04-23",
    }
    conn.execute("UPDATE documents SET metadata_json=?", (json.dumps(old_meta),))
    conn.commit()
    conn.close()

    catalog.scan()

    docs = catalog.query(limit=10)
    assert len(docs) == 1
    dayu_meta = (docs[0].get("metadata") or {}).get("dayu_meta") or {}
    assert dayu_meta.get("form_type") == "FY"
    assert dayu_meta.get("fiscal_year") == 2025
    assert dayu_meta.get("security_id") == "3896"
    assert dayu_meta.get("market") == "HK"
    assert dayu_meta.get("source_url") == meta["source_url"]
    assert docs[0]["document_kind"] == "annual_report"


def test_company_raw_sidecar_without_url_gets_dayu_meta_url(tmp_path):
    """A company_raw document whose sidecar lacks source_url must get the URL
    from the matching dayu portfolio meta.json (Phase 16.1)."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

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

    # WU-3.1: the default query is active-only; this enrichment check needs
    # the URL-bearing dayu document even when its row is not yet active.
    docs = catalog.query(limit=10, source_status="active") + catalog.query(
        limit=10, source_status="incomplete"
    )
    assert len(docs) == 2
    target = next(
        d
        for d in docs
        if "南大光电"
        in str(
            (d.get("metadata") or {}).get("acquisition", {}).get("source_title") or ""
        )
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
    old = (
        companies
        / "Acme"
        / "raw"
        / "financial_reports"
        / "z_old"
        / "2026-02-20_Acme_2025_annual.pdf"
    )
    new = (
        companies
        / "Acme"
        / "raw"
        / "financial_reports"
        / "annual"
        / "2026-02-20_sec_1_2025_annual.pdf"
    )
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    payload = b"%PDF-1.7\nidentical bytes"
    old.write_bytes(payload)
    new.write_bytes(payload)
    (old.parent / (old.name + ".source.json")).write_text(
        json.dumps(
            {"market": "CN", "security_id": "600519", "source_title": "old sidecar"}
        ),
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


def test_company_raw_sec_sidecar_gets_market_and_security_id(tmp_path):
    """Phase 18.4: a company_raw SEC document whose sidecar carries
    accession_number/provider but no market must get market="US" and
    security_id from its ticker on ingestion — mirroring the dayu portfolio
    backfill (Alphabet 10-K shape), so capture-ready handles resolve by
    market."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    company = companies / "Alphabet Inc" / "raw" / "financial_reports" / "annual"
    company.mkdir(parents=True)
    primary = "2026-02-05_sec_0001652044-26-000018_Alphabet_10K.htm"
    (company / primary).write_text(
        "<html>Alphabet FY2025 10-K</html>", encoding="utf-8"
    )
    (company / (primary + ".source.json")).write_text(
        json.dumps(
            {
                "ticker": "GOOG",
                "provider": "sec",
                "provider_document_id": "0001652044-26-000018",
                "accession_number": "0001652044-26-000018",
                "source_title": "Alphabet Inc. 10-K 2025-12-31",
                "form_type": "10-K",
                "fiscal_year": 2025,
                "source_url": "https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/10k.htm",
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
    assert acquisition.get("market") == "US"
    assert acquisition.get("security_id") == "GOOG"
