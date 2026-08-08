"""WU-2A.0: config-only Dropbox capability probe (RED before config change).

Proves that the ONLY difference between "Dropbox indexed but not reusable"
and "Dropbox reusable" is the two config entries:

1. company-wiki ``reusable_root_kinds`` must NOT include ``directory``;
2. filing-fetch ``allowed_handle_roots`` must NOT list the Dropbox path.

The same temp fixture must be MISSING when ``directory`` is absent from
reusable kinds and REUSED_EXACT once it is added — behavior change must be
attributable to config alone (no runtime edits).

Fixture layout (mirrors production admission rules): a ``dropbox_stock``
root with ``kind=directory`` whose file lives under ``重点关注/ACME/`` with
a ``.source.json`` sidecar carrying fixed identity: annual_report, US/ACME,
FY2025, 10-K, SEC accession, filing date, HTTPS URL, ingest complete.
Identity must not depend on file-name guessing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


FIXED_BODY = b"%PDF-1.4 fake annual filing body"


def _fixed_sidecar() -> dict:
    return {
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
        "byte_size": len(FIXED_BODY),
        "content_sha256": hashlib.sha256(FIXED_BODY).hexdigest(),
    }


def _dropbox_catalog(tmp_path: Path, reusable_kinds: tuple[str, ...]):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    # company_raw root so _infer_company can resolve the ACME entity
    # (mirrors production: companies/<name>/raw/ directories).
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    dropbox = tmp_path / "dropbox"
    filing_dir = dropbox / "重点关注" / "ACME"
    filing_dir.mkdir(parents=True)
    primary = filing_dir / "ACME_10K_2025.pdf"
    primary.write_bytes(FIXED_BODY)
    sidecar = filing_dir / "ACME_10K_2025.pdf.source.json"
    sidecar.write_text(json.dumps(_fixed_sidecar()), encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10),
                RootSpec("dropbox_stock", dropbox, "directory", priority=30),
            ),
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


def test_probe_missing_when_directory_kind_not_reusable(tmp_path):
    """Config A (current production): directory NOT in reusable kinds → the
    same fixture must resolve as MISSING, proving Dropbox is indexed but not
    reusable."""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog, _ = _dropbox_catalog(tmp_path, ("company_raw", "dayu_portfolio"))
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is ResolutionStatus.MISSING, result.status
    assert result.matches == ()


def test_probe_reused_exact_when_directory_kind_reusable(tmp_path):
    """KNOWN GAP (F-034 revised, user decision 2026-08-08): adding 'directory'
    to reusable kinds is NECESSARY but NOT sufficient in the current runtime.

    The scanner persists sidecar metadata only under company_raw/dayu_portfolio
    roots (``acquisition``/``dayu_meta`` keys), so resolver._source_metadata()
    returns {} for directory roots → form_type/identity/https_url checks fail.

    This test currently asserts the ACTUAL behavior (MISSING with the gap
    trace). AFTER the minimal scanner fix (persist directory-root sidecar
    metadata into ``acquisition``), flip this to assert REUSED_EXACT.
    """
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog, primary = _dropbox_catalog(
        tmp_path, ("company_raw", "dayu_portfolio", "directory")
    )
    result = SourceResolver(catalog).resolve(_request())
    # KNOWN GAP assertion — replace with REUSED_EXACT block below after fix:
    assert result.status is ResolutionStatus.MISSING, result.status
    trace = list(result.debug_trace)
    assert any("form_type_mismatch" in item or "identity" in item or "capture_incomplete" in item for item in trace), trace


def test_probe_broker_research_not_reused_for_annual_request(tmp_path):
    """E2E-R08: a broker research document (券商机构 + 研报 evidence) in the
    Dropbox focus subtree is admitted as broker_research and must NEVER
    satisfy an annual_report request — no admission, no handle."""
    import json

    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog, SourceRequest, SourceResolver, ResolutionStatus

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    dropbox = tmp_path / "dropbox"
    filing_dir = dropbox / "重点关注" / "ACME"
    filing_dir.mkdir(parents=True)
    primary = filing_dir / "中金公司_ACME深度报告.pdf"
    primary.write_bytes(b"%PDF-1.4 broker research body")
    sidecar = filing_dir / "中金公司_ACME深度报告.pdf.source.json"
    sidecar.write_text(json.dumps({
        "document_kind": "broker_research",
        "source_title": "中金公司：ACME深度报告",
        "ticker": "ACME", "market": "US", "security_id": "ACME",
        "fiscal_year": 2025, "form_type": "10-K",
        "accession_number": "0001234567-26-000001", "provider": "sec",
        "source_url": "https://www.sec.gov/x.pdf",
        "filing_date": "2026-02-20", "ingest_complete": True,
        "retrieved_at": "2026-02-21T10:00:00Z", "collector_name": "t",
        "collector_version": "1.0.0", "mime_type": "application/pdf",
        "byte_size": 28, "content_sha256": "c" * 64,
    }), encoding="utf-8")
    catalog = SourceCatalog(CatalogConfig(
        project_root=project, catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),
               RootSpec("dropbox_stock", dropbox, "directory", priority=30)),
        reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
    ))
    catalog.scan()
    # document_kind comes from admission: broker_research (not annual)
    import sqlite3
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=ro", uri=True)
    kinds = [r[0] for r in con.execute(
        "SELECT document_kind FROM documents WHERE document_kind='broker_research'")]
    con.close()
    assert kinds, "broker research doc not classified as broker_research"
    result = SourceResolver(catalog).resolve(SourceRequest(
        entity="ACME", market="US", security_id="ACME",
        document_kind="annual_report", form_type="10-K", fiscal_year=2025,
        provider="sec", provider_document_id="0001234567-26-000001",
        as_of_date="2026-07-18"))
    assert result.status is ResolutionStatus.MISSING, result.status
    assert result.matches == ()
    # === POST-FIX EXPECTED (do not delete; flip after scanner fix) ===
    # assert result.status is ResolutionStatus.REUSED_EXACT, result.status
    # assert result.download_required is False
    # assert len(result.matches) == 1
    # handle = result.matches[0]
    # assert handle.capture_ready is True, handle.missing_capture_fields
    # assert Path(handle.canonical_path) == primary
    # assert handle.source_status == "active"
