"""WU-805 RED/audit tests: resolver performance SLO on a synthetic 100k
document library (exact resolve warm p95 <= 300ms; latest/gap <= 750ms).
"""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.service import SourceCatalog  # noqa: E402

EXACT_P95_MS = 300
LATEST_P95_MS = 750
LIBRARY_SIZE = 100_000


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    """A synthetic 100k-document catalog with the real schema."""
    tmp = tmp_path_factory.mktemp("perf")
    from company_wiki.source_catalog.models import CatalogConfig

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp,
            catalog_dir=tmp / ".source_catalog",
            roots=(
                _root("company_raw", tmp / "companies", "company_raw"),
                _root("dropbox_stock", tmp / "stock", "directory"),
            ),
        )
    )
    catalog.store  # initialize the catalog schema
    con = catalog.store._connect()
    try:
        con.execute("BEGIN")
        con.execute(
            "INSERT INTO roots (root_id, path, kind, priority, last_scan_run, "
            "last_scanned_at) VALUES ('company_raw', ?, 'company_raw', 10, '', '')",
            (str(tmp / "companies"),),
        )
        con.execute(
            "INSERT INTO roots (root_id, path, kind, priority, last_scan_run, "
            "last_scanned_at) VALUES ('dropbox_stock', ?, 'directory', 20, '', '')",
            (str(tmp / "stock"),),
        )
        for i in range(LIBRARY_SIZE):
            company = f"C{i % 500}"
            year = 2015 + (i % 12)
            kind = "annual_report" if i % 2 == 0 else "quarterly_report"
            doc_id = f"doc-{i}"
            con.execute(
                "INSERT INTO sources (source_id, content_sha256, byte_size, "
                "mime_type, first_seen_at) VALUES (?,?,?,?,?)",
                (f"src-{i}", f"{i:064x}", 100, "application/pdf", "2026-01-01"),
            )
            con.execute(
                "INSERT INTO documents (document_id, title, source_status, "
                "source_type, document_kind, metadata_priority, metadata_json, "
                "first_seen_at, last_seen_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (doc_id, f"{company} {year} {kind}", "active", "file", kind,
                 10, '{}', "2026-01-01", "2026-01-01"),
            )
            con.execute(
                "INSERT INTO locations (location_id, root_id, relative_path, "
                "absolute_path, source_id, document_id, role, location_status, "
                "observed_size, observed_mtime_ns, last_seen_run, metadata_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"loc-{i}", "company_raw" if i % 2 == 0 else "dropbox_stock",
                 f"doc-{i}.pdf", f"/tmp/doc-{i}.pdf", f"src-{i}", doc_id,
                 "original", "active", 100, 0, "2026-01-01", '{}'),
            )
        con.execute("COMMIT")
    finally:
        con.close()
    return catalog


def _root(root_id, path, kind):
    from company_wiki.source_catalog.models import RootSpec

    return RootSpec(root_id=root_id, path=path, kind=kind)


def test_exact_resolve_warm_p95(tmp_path, library):
    """WU-805: exact resolve on 100k docs must stay under 300ms p95."""
    samples = [f"C{i % 500}" for i in range(0, LIBRARY_SIZE, 1000)]
    timings = []
    for company in samples:
        start = time.perf_counter()
        library.query_filing_candidates(
            entity=company, document_kind="annual_report",
            source_statuses=("active",)
        )
        timings.append((time.perf_counter() - start) * 1000)
    timings.sort()
    p95 = timings[int(len(timings) * 0.95)]
    assert p95 <= EXACT_P95_MS, f"exact p95 {p95:.1f}ms > {EXACT_P95_MS}ms"
