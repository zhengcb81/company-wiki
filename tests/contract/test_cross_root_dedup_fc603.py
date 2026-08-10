"""FC-603 RED/acceptance tests: 跨根去重与 deterministic location.

Same bytes across roots produce ONE document with multiple locations and
a deterministic canonical location chosen by policy priority + stable
tie-break (root_id, relative_path, location_id) — independent of scan
order (EX-04/EX-07).  Same company/year with different provider ids
selects exactly (EX-05); amended + original coexist under a stable
revision rule (EX-06); cross-root duplicates share the artifact
(AR-09).
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _same_bytes_fixture(tmp_path: Path) -> tuple[Path, list[RootSpec], bytes]:
    """The same PDF bytes placed in companies (p10), dayu (p20) and
    dropbox (p30) — one document, three locations."""
    body = b"%PDF-1.4 dupacrossroots"
    companies = tmp_path / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    companies.mkdir(parents=True)
    companies_file = companies / "2025.pdf"
    companies_file.write_bytes(body)
    (companies / "2025.pdf.source.json").write_text(json.dumps({
        "market": "US", "security_id": "ACME", "fiscal_year": 2025,
        "filing_date": "2026-02-20", "form_type": "10-K",
        "document_kind": "annual_report", "provider": "sec",
        "provider_document_id": "doc-1",
        "source_url": "https://sec.gov/x/2025",
    }, ensure_ascii=False), encoding="utf-8")
    dayu = tmp_path / "portfolio" / "ACME" / "filings" / "fil_x"
    dayu.mkdir(parents=True)
    (dayu / "fil_x.pdf").write_bytes(body)
    (dayu / "meta.json").write_text(json.dumps({
        "document_id": "fil_x", "ticker": "ACME", "form_type": "10-K",
        "fiscal_year": 2025, "filing_date": "2026-02-20",
        "source_provider": "sec", "source_id": "doc-1",
        "source_url": "https://sec.gov/x/2025", "source_language": "en",
        "ingest_complete": True, "primary_document": "fil_x.pdf",
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "portfolio" / "ACME" / "meta.json").write_text(json.dumps(
        {"ticker": "ACME", "market": "US"}, ensure_ascii=False), encoding="utf-8")
    dropbox = tmp_path / "Dropbox" / "Stock"
    dropbox.mkdir(parents=True)
    (dropbox / "2025.pdf").write_bytes(body)
    (dropbox / "2025.pdf.source.json").write_text(json.dumps({
        "schema_version": "1.0", "canonical_entity_id": "ent-acme",
        "display_name": "Acme", "market": "US", "security_id": "ACME",
        "document_kind": "annual_report", "fiscal_year": 2025,
        "filing_date": "2026-02-20", "form_type": "10-K",
        "period_end": "2025-12-31", "provider": "sec",
        "provider_document_id": "doc-1",
        "source_url": "https://sec.gov/x/2025",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }, ensure_ascii=False), encoding="utf-8")
    roots = [
        RootSpec("company_raw", tmp_path / "companies", "company_raw",
                 priority=10, adapter_id="company_raw_v1",
                 read_only=False, reusable_for_filing=True,
                 canonical_write_target="companies"),
        RootSpec("dayu_portfolio", tmp_path / "portfolio", "dayu_portfolio",
                 priority=20, adapter_id="dayu_filing_v1", read_only=True,
                 reusable_for_filing=True),
        RootSpec("dropbox_stock", tmp_path / "Dropbox" / "Stock", "directory",
                 priority=30, adapter_id="sidecar_filing_v1", read_only=True,
                 reusable_for_filing=True),
    ]
    return tmp_path, roots, body


def _scan_catalog(tmp_path: Path, roots: list[RootSpec]):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
            roots=tuple(roots),
        )
    )
    catalog.scan()
    return catalog


# --- EX-04: same bytes across roots -> one document, deterministic canonical


def test_fc603_ex04_same_bytes_one_document_canonical(tmp_path):
    """Three roots hold the same bytes: one document with three active
    original_primary locations and the lowest-priority root (companies)
    wins the canonical location."""
    from company_wiki.source_catalog.resolver import (
        ResolutionStatus,
        SourceRequest,
        SourceResolver,
    )

    tmp, roots, body = _same_bytes_fixture(tmp_path)
    catalog = _scan_catalog(tmp, roots)
    digest = hashlib.sha256(body).hexdigest()
    rows = catalog.store.fetchall(
        """SELECT l.root_id, l.role, l.location_status
           FROM locations l JOIN sources s ON s.source_id = l.source_id
           WHERE s.content_sha256 = ? ORDER BY l.root_id""",
        (digest,),
    )
    assert len(rows) == 3
    assert {r["root_id"] for r in rows} == {
        "company_raw", "dayu_portfolio", "dropbox_stock"}
    assert all(r["role"] == "original_primary" for r in rows)
    # one document: the same document_id backs all three locations
    doc_ids = {
        r["document_id"] for r in catalog.store.fetchall(
            """SELECT l.document_id FROM locations l
               JOIN sources s ON s.source_id = l.source_id
               WHERE s.content_sha256 = ?""", (digest,))
    }
    assert len(doc_ids) == 1
    # canonical = companies (priority 10) via priority + stable tie-break
    result = SourceResolver(catalog).resolve(SourceRequest(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", form_type="10-K",
        fiscal_year=2025, provider="sec", provider_document_id="doc-1",
        as_of_date="2026-08-10", mode="exact",
    ))
    assert result.status is ResolutionStatus.REUSED_EXACT
    handle = result.matches[0]
    assert "companies" in handle.canonical_path.replace("\\", "/")
    assert handle.exact_duplicate_location_count == 2


def test_fc603_ex04_canonical_stable_across_scan_order(tmp_path):
    """Reversing the root scan order does not change the canonical
    location or the duplicate group id (EX-04/EX-07 order stability).

    Each scan uses its OWN catalog database; with the sort removed the
    canonical would follow insertion order (scan order) and the two
    scans would disagree."""
    tmp, roots, body = _same_bytes_fixture(tmp_path)
    forward = _scan_catalog(tmp / "cat_a", roots)
    backward = _scan_catalog(tmp / "cat_b", list(reversed(roots)))
    def canonical_of(catalog):
        from company_wiki.source_catalog.resolver import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        result = SourceResolver(catalog).resolve(SourceRequest(
            entity="Acme", market="US", security_id="ACME",
            document_kind="annual_report", form_type="10-K",
            fiscal_year=2025, provider="sec", provider_document_id="doc-1",
            as_of_date="2026-08-10", mode="exact",
        ))
        assert result.status is ResolutionStatus.REUSED_EXACT
        handle = result.matches[0]
        return (handle.canonical_path, handle.duplicate_group_id,
                handle.exact_duplicate_location_count)
    assert canonical_of(forward) == canonical_of(backward)
    assert "companies" in canonical_of(forward)[0].replace("\\", "/")


# --- EX-05: same company/year, diff provider ids -> exact select -------------


def test_fc603_ex04_priority_beats_alphabetical_root_id(tmp_path):
    """The canonical winner is chosen by policy priority, not by
    alphabetical root id: with companies p30 and dropbox p10, dropbox
    wins even though 'company_raw' sorts first alphabetically."""
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    body = b"%PDF-1.4 priority"
    companies = tmp_path / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    companies.mkdir(parents=True)
    (companies / "2025.pdf").write_bytes(body)
    (companies / "2025.pdf.source.json").write_text(json.dumps({
        "market": "US", "security_id": "ACME", "fiscal_year": 2025,
        "filing_date": "2026-02-20", "form_type": "10-K",
        "document_kind": "annual_report", "provider": "sec",
        "provider_document_id": "doc-1",
        "source_url": "https://sec.gov/x/2025",
    }, ensure_ascii=False), encoding="utf-8")
    dayu = tmp_path / "portfolio" / "ACME" / "filings" / "fil_x"
    dayu.mkdir(parents=True)
    (dayu / "fil_x.pdf").write_bytes(body)
    (dayu / "meta.json").write_text(json.dumps({
        "document_id": "fil_x", "ticker": "ACME", "form_type": "10-K",
        "fiscal_year": 2025, "filing_date": "2026-02-20",
        "source_provider": "sec", "source_id": "doc-1",
        "source_url": "https://sec.gov/x/2025", "source_language": "en",
        "ingest_complete": True, "primary_document": "fil_x.pdf",
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "portfolio" / "ACME" / "meta.json").write_text(json.dumps(
        {"ticker": "ACME", "market": "US"}, ensure_ascii=False), encoding="utf-8")
    roots = (
        RootSpec("company_raw", tmp_path / "companies", "company_raw",
                 priority=30, adapter_id="company_raw_v1", read_only=False,
                 reusable_for_filing=True, canonical_write_target="companies"),
        RootSpec("dayu_portfolio", tmp_path / "portfolio", "dayu_portfolio",
                 priority=10, adapter_id="dayu_filing_v1", read_only=True,
                 reusable_for_filing=True),
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "dayu_portfolio"),
            roots=roots,
        )
    )
    catalog.scan()
    result = SourceResolver(catalog).resolve(SourceRequest(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", form_type="10-K",
        fiscal_year=2025, provider="sec", provider_document_id="doc-1",
        as_of_date="2026-08-10", mode="exact",
    ))
    assert result.status is ResolutionStatus.REUSED_EXACT
    # dayu has the lower priority (10 < 30) and wins the canonical
    assert "portfolio" in result.matches[0].canonical_path.replace("\\", "/")


def test_fc603_ex05_same_company_year_diff_pdoc_exact_select(tmp_path):
    """Two documents for the same company/year with different provider
    document ids never merge ambiguously: the pdoc-bound request selects
    exactly one."""
    from company_wiki.source_catalog import (
        CatalogConfig,
        ResolutionStatus,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    raw = tmp_path / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True)
    for pdoc, body in (("acc-1", b"%PDF-1.4 v1"), ("acc-2", b"%PDF-1.4 v2")):
        (raw / f"{pdoc}.pdf").write_bytes(body)
        (raw / f"{pdoc}.pdf.source.json").write_text(json.dumps({
            "market": "US", "security_id": "ACME", "fiscal_year": 2025,
            "filing_date": "2026-02-20", "form_type": "10-K",
            "document_kind": "annual_report", "provider": "sec",
            "provider_document_id": pdoc,
            "source_url": f"https://sec.gov/x/{pdoc}",
        }, ensure_ascii=False), encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            roots=(RootSpec("company_raw", tmp_path / "companies",
                            "company_raw"),),
        )
    )
    catalog.scan()
    for pdoc in ("acc-1", "acc-2"):
        result = SourceResolver(catalog).resolve(SourceRequest(
            entity="Acme", market="US", security_id="ACME",
            document_kind="annual_report", form_type="10-K",
            fiscal_year=2025, provider="sec", provider_document_id=pdoc,
            as_of_date="2026-08-10", mode="exact",
        ))
        assert result.status is ResolutionStatus.REUSED_EXACT
        assert len(result.matches) == 1
        assert result.matches[0].provider_document_id == pdoc


# --- EX-06: amended + original coexist -> stable revision rule ----------------

from company_wiki.source_catalog.gap_plan import (  # noqa: E402
    build_gap_plan,
)


def test_fc603_ex06_amended_original_stable_revision_rule():
    """With an original and its amended revision for the same period, the
    gap plan keeps the local original and flags only the newer accession
    as a newer revision — a stable, deterministic rule (EX-06)."""
    class Candidate:
        def __init__(self, accession, amended, title=""):
            self.provider_document_id = accession
            self.amended = amended
            self.title = title
            self.fiscal_year = 2024

    class Handle:
        def __init__(self, accession):
            self.provider_document_id = accession
            self.fiscal_year = 2024

    local = [Handle("0001-25-000001")]
    remote = [
        Candidate("0001-25-000001", False, "original"),
        Candidate("0001-25-000099", True, "amended"),
    ]
    plan = build_gap_plan(
        request_id="req-1", as_of_date="2026-08-10",
        document_kind="annual_report", entity="Acme", market="US",
        local_handles=local, remote_candidates=remote,
    )
    # the local original stays reusable; only the newer accession is a
    # newer revision (stable rule, never ambiguous)
    assert plan.reuse == tuple(local)
    newer = [c.provider_document_id for c in plan.newer_revision]
    assert newer == ["0001-25-000099"]
    assert plan.missing == ()
    # determinism
    plan2 = build_gap_plan(
        request_id="req-1", as_of_date="2026-08-10",
        document_kind="annual_report", entity="Acme", market="US",
        local_handles=local, remote_candidates=list(reversed(remote)),
    )
    assert [c.provider_document_id for c in plan2.newer_revision] == newer


# --- AR-09: cross-root duplicates share the artifact --------------------------


def test_fc603_ar09_artifact_shared_across_roots(tmp_path):
    """The artifact for the cross-root duplicate document is shared: the
    source bundle binds the same document/content regardless of which
    root location is canonical."""
    from company_wiki.source_catalog.source_bundle import build_source_bundle

    tmp, roots, body = _same_bytes_fixture(tmp_path)
    catalog = _scan_catalog(tmp, roots)
    digest = hashlib.sha256(body).hexdigest()
    rows = catalog.store.fetchall(
        """SELECT l.absolute_path, l.document_id, l.manifest_json
           FROM locations l JOIN sources s ON s.source_id = l.source_id
           WHERE s.content_sha256 = ?""", (digest,))
    doc_ids = {r["document_id"] for r in rows}
    assert len(doc_ids) == 1  # one document
    source = {"document_id": next(iter(doc_ids)),
              "content_sha256": digest}
    artifact = {
        "artifact_role": "original",
        "content_sha256": digest,
        "byte_size": len(body),
        "mime_type": "application/pdf",
        "path": rows[0]["absolute_path"],
        "provider": "sec",
        "provider_document_id": "doc-1",
        "published_date": "2026-02-20",
    }
    bundle = build_source_bundle(
        source=source,
        artifacts=[artifact],
        registry={digest: {"paths": {rows[0]["absolute_path"]}}},
        allowed_roots=(tmp_path / "companies", tmp_path / "portfolio",
                       tmp_path / "Dropbox" / "Stock"),
        now="2026-08-10T00:00:00Z",
    )
    # the bundle is keyed by document/content — the duplicate locations
    # share it (same artifact hash regardless of the canonical root)
    assert bundle.to_dict()["source"]["document_id"] == source["document_id"]
