"""WU-3.1: resolver fail-closed on status and path filtering (F-024).

Current runtime only hides ``retired`` documents in ``SourceCatalog.query``;
``quarantined`` and ``upstream_rejected`` still flow into results, the
resolver never re-checks document ``source_status``, and ``.rejections``
locations can become canonical handles. These tests lock the fail-closed
behavior:

- RED (before fix): quarantined/upstream_rejected documents and
  ``.rejections`` locations produce a REUSED handle in the resolver.
- GREEN (after fix): none of them form a handle; each rejection carries a
  stable reason code in the trace.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


FIXED_SIDECAR = {
    "document_kind": "annual_report",
    "source_type": "filing",
    "company_name": "ACME Corp",
    "ticker": "ACME",
    "market": "US",
    "security_id": "ACME",
    "fiscal_year": 2025,
    "fiscal_period": "FY",
    "form_type": "10-K",
    "accession_number": "0001234567-26-000001",
    "provider": "sec",
    "source_url": "https://www.sec.gov/Archives/edgar/data/1234567/ACME-10K-2025.pdf",
    "filing_date": "2026-02-20",
    "ingest_complete": True,
    "retrieved_at": "2026-02-21T10:00:00Z",
    "collector_name": "test-collector",
    "collector_version": "1.0.0",
    "mime_type": "application/pdf",
    "byte_size": 1024,
    "content_sha256": "a" * 64,
}


def _catalog(tmp_path: Path, document_status: str, rejections_path: bool = False):
    """company_raw root (canonical writer) + a dayu-style root whose document
    carries the given source_status (or lives under .rejections)."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    portfolio = tmp_path / "portfolio"
    if rejections_path:
        filing_dir = portfolio / "ACME" / "filings" / ".rejections" / "fil_2025"
    else:
        filing_dir = portfolio / "ACME" / "filings" / "fil_2025"
    filing_dir.mkdir(parents=True)
    primary = filing_dir / "annual.pdf"
    body = b"%PDF-1.4 fake"
    primary.write_bytes(body)
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
        "primary_document": "annual.pdf",
        "ingest_complete": True,
        "source_url": "https://www.sec.gov/Archives/edgar/data/1234567/annual.pdf",
        "files": [{"name": "annual.pdf", "source": "original"}],
    }
    (filing_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10),
                RootSpec("dayu_portfolio", portfolio, "dayu_portfolio", priority=20),
            ),
            reusable_root_kinds=("company_raw", "dayu_portfolio"),
        )
    )
    catalog.scan()
    if document_status != "active":
        # Force the document's source_status (quarantined/upstream_rejected)
        # directly, as the acquisition pipeline would on a provider rejection.
        con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
        con.execute(
            "UPDATE documents SET source_status=? WHERE document_kind='annual_report'",
            (document_status,),
        )
        con.commit()
        con.close()
    return catalog


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


def test_active_document_still_reused(tmp_path):
    """Control: an active document under a reusable root still resolves."""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path, "active")
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace


def test_quarantined_document_not_reused(tmp_path):
    """End-to-end: a quarantined document never resolves to a handle.
    (The query layer already hides it, so the resolver sees no candidate —
    that is the intended fail-closed behavior.)"""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path, "quarantined")
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is not ResolutionStatus.REUSED_EXACT
    assert result.matches == ()


def test_upstream_rejected_document_not_reused(tmp_path):
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path, "upstream_rejected")
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is not ResolutionStatus.REUSED_EXACT
    assert result.matches == ()


def test_rejections_path_not_reused(tmp_path):
    """A document whose canonical location lives under .rejections must not
    form a handle even when the document itself is active."""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path, "active", rejections_path=True)
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is not ResolutionStatus.REUSED_EXACT
    assert result.matches == ()


def test_resolver_rejects_leaked_active_rejections_path(tmp_path, monkeypatch):
    """Directly drive the resolver's .rejections path filter: even when the
    document row is active AND the query layer leaks it, a canonical
    location under .rejections must be refused with reason code
    'rejections_path'. (The query layer normally intercepts first — this
    test proves the resolver filter is load-bearing, not dead code.)"""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path, "active", rejections_path=True)
    # scanner marks .rejections docs upstream_rejected; force back to active
    # to construct the leak scenario.
    import sqlite3

    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET source_status='active'")
    con.commit()
    con.close()

    real_query = catalog.query
    monkeypatch.setattr(
        catalog,
        "query",
        lambda **kwargs: real_query(source_status="active", **kwargs),
    )
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is not ResolutionStatus.REUSED_EXACT, result.debug_trace
    assert result.matches == ()
    assert any("rejections_path" in item for item in result.debug_trace), (
        result.debug_trace
    )


def test_resolver_defense_in_depth_rejects_leaked_document(tmp_path, monkeypatch):
    """Even if the query layer regresses and leaks a quarantined document,
    the resolver must refuse it with a stable reason code."""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path, "active")
    # Force the document status to quarantined AFTER scan, then simulate a
    # query-layer regression by monkeypatching query() to return everything.
    import sqlite3

    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET source_status='quarantined'")
    con.commit()
    con.close()

    real_query = catalog.query
    monkeypatch.setattr(
        catalog,
        "query",
        lambda **kwargs: real_query(source_status="quarantined", **kwargs),
    )
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is not ResolutionStatus.REUSED_EXACT
    assert result.matches == ()
    assert any("rejected_source_status" in item for item in result.debug_trace), (
        result.debug_trace
    )


def test_retired_document_not_reused(tmp_path):
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path, "retired")
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is not ResolutionStatus.REUSED_EXACT
    assert result.matches == ()


def test_query_hides_non_active_by_default(tmp_path):
    """SourceCatalog.query without source_status must not return
    quarantined/upstream_rejected documents (F-024 allowlist)."""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path, "upstream_rejected")
    docs = catalog.query(limit=100)
    statuses = {d["source_status"] for d in docs}
    assert "upstream_rejected" not in statuses
    assert "quarantined" not in statuses
    # and the resolver end-to-end also rejects
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is not ResolutionStatus.REUSED_EXACT
