"""WU-3.2: SQL pushdown for filing-candidate lookup (F-021/F-026).

Current runtime materializes the whole catalog in Python
(``catalog.query(limit=10_000_000)``) on every resolution. This suite
locks the target behavior:

1. ``query_filing_candidates(...)`` exists and filters in SQL:
   entity (via document_entities/entities), document_kind, source_status
   allowlist, reusable root_ids (via locations/roots), with a hard limit.
2. The resolver calls it instead of the all-table ``query``.
3. Candidate cap ≤100; ``EXPLAIN QUERY PLAN`` hits the dedicated indexes.
4. A 100k-document fixture resolves within the CI SLO.

RED phase: the method does not exist yet (AttributeError → RED) and the
resolver still calls ``query(limit=10_000_000)`` (probe fails).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def _seed_catalog(
    tmp_path: Path,
    n_docs: int = 100_000,
    with_files: bool = False,
    acme_only: bool = False,
):
    """Seed a catalog with n_docs documents: ACME annuals spread across
    statuses + roots, plus decoy entities (unless acme_only). ``with_files``
    creates real files and capture metadata for active ACME docs."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
            reusable_root_kinds=("company_raw",),
        )
    )
    # First connection bootstraps the schema (store._initialize).
    catalog.store.status()
    con = sqlite3.connect(catalog.config.database_path)
    con.execute("PRAGMA journal_mode=OFF")
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL UNIQUE,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL, first_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT,
            source_type TEXT, document_kind TEXT, published_date TEXT,
            source_status TEXT NOT NULL, metadata_priority INTEGER NOT NULL,
            metadata_json TEXT NOT NULL, text_fingerprint TEXT,
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_kind TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS document_entities (
            document_id TEXT NOT NULL, entity_id TEXT NOT NULL,
            confidence REAL NOT NULL, method TEXT NOT NULL,
            PRIMARY KEY(document_id, entity_id)
        );
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL,
            source_id TEXT, document_id TEXT, role TEXT NOT NULL,
            location_status TEXT NOT NULL, observed_size INTEGER,
            observed_mtime_ns INTEGER, last_seen_run TEXT NOT NULL,
            manifest_json TEXT, metadata_json TEXT NOT NULL, error TEXT
        );
        CREATE TABLE IF NOT EXISTS roots (
            root_id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL,
            priority INTEGER NOT NULL, last_scan_run TEXT, last_scanned_at TEXT
        );
        """
    )
    con.execute(
        "INSERT INTO roots VALUES ('company_raw', ?, 'company_raw', 10, NULL, NULL)",
        (str(companies),),
    )
    con.execute("INSERT INTO entities VALUES ('ticker:ACME', 'ACME', 'ticker')")
    con.execute("INSERT INTO entities VALUES ('ticker:DECOY', 'DECOY', 'ticker')")
    batch = 5000
    for start in range(0, n_docs, batch):
        rows = []
        for i in range(start, min(start + batch, n_docs)):
            is_acme = acme_only or i % 2 == 0
            entity = "ticker:ACME" if is_acme else "ticker:DECOY"
            status = "active" if i % 3 == 0 else "retired"
            did = f"doc-{i}"
            sid = f"src-{i}"
            is_active_acme = status == "active" and is_acme
            manifest_json = None
            if with_files and is_active_acme:
                file_dir = companies / "ACME"
                file_dir.mkdir(parents=True, exist_ok=True)
                (file_dir / f"{i}.pdf").write_bytes(b"%PDF-1.4 fake")
                metadata_json = json.dumps(
                    {
                        "acquisition": {
                            "source_url": "https://www.sec.gov/Archives/edgar/data/1/a.pdf",
                            "retrieved_at": "2026-02-21T10:00:00Z",
                            "collector_name": "test",
                            "collector_version": "1.0.0",
                            "market": "US",
                            "security_id": "ACME",
                            "fiscal_year": 2025,
                            "form_type": "10-K",
                            "provider": "sec",
                            "accession_number": "0001234567-26-000001",
                        }
                    }
                )
                manifest_json = json.dumps(
                    {
                        "content_sha256": "a" * 64,
                        "retrieved_at": "2026-02-21T10:00:00Z",
                        "collector_name": "test",
                        "collector_version": "1.0.0",
                        "mime_type": "application/pdf",
                        "byte_size": 13,
                    }
                )
            else:
                metadata_json = "{}"
            rows.append(
                (did, sid, f"ACME {i} annual", "filing", "annual_report",
                 f"2025-{(i % 12) + 1:02d}-15", status, 1, metadata_json, None,
                 "2025-01-01T00:00:00Z", "2026-08-08T13:44:53Z",
                 sid, "a" * 64, 1000, "application/pdf", "2025-01-01T00:00:00Z",
                 entity, 1.0, "path_ticker",
                 f"loc-{i}", "company_raw", f"ACME/{i}.pdf", f"{companies}/ACME/{i}.pdf",
                 sid, did, "original_primary", "active", 1000, 1, "scan-x", manifest_json, "{}", None)
            )
        con.executemany(
            """INSERT OR REPLACE INTO sources(source_id,content_sha256,byte_size,mime_type,first_seen_at)
               VALUES(?,?,?,?,?)""",
            [(r[12], r[13], r[14], r[15], r[16]) for r in rows],
        )
        con.executemany(
            """INSERT OR REPLACE INTO documents(document_id,primary_source_id,title,source_type,
               document_kind,published_date,source_status,metadata_priority,metadata_json,
               text_fingerprint,first_seen_at,last_seen_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            [r[:12] for r in rows],
        )
        con.executemany(
            """INSERT OR REPLACE INTO document_entities(document_id,entity_id,confidence,method)
               VALUES(?,?,?,?)""",
            [(r[0], r[17], r[18], r[19]) for r in rows],
        )
        con.executemany(
            """INSERT OR REPLACE INTO locations(location_id,root_id,relative_path,absolute_path,
               source_id,document_id,role,location_status,observed_size,observed_mtime_ns,
               last_seen_run,manifest_json,metadata_json,error)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [r[20:] for r in rows],
        )
    con.commit()
    con.close()
    return catalog


def test_query_filing_candidates_exists_and_filters_in_sql(tmp_path):
    """The dedicated SQL pushdown method must exist and return only the
    matching active ACME annuals, capped; entity and root filters are
    optional and usable by callers that want them."""
    catalog = _seed_catalog(tmp_path, n_docs=2_000, with_files=True, acme_only=True)
    candidates = catalog.query_filing_candidates(
        entity="ACME",
        document_kind="annual_report",
        source_statuses=("active",),
        root_ids=("company_raw",),
        limit=100,
    )
    assert candidates, "no candidates returned"
    assert len(candidates) <= 100
    for doc in candidates:
        assert doc["source_status"] == "active"
        assert doc["document_kind"] == "annual_report"
        assert any(e["entity_id"] == "ticker:ACME" for e in doc["entities"])
    # without root/entity filters: kind+status slice still filtered in SQL
    broad = catalog.query_filing_candidates(
        document_kind="annual_report",
        source_statuses=("active",),
        limit=100,
    )
    assert broad
    assert all(d["document_kind"] == "annual_report" for d in broad)
    assert all(d["source_status"] == "active" for d in broad)


def test_resolver_uses_sql_pushdown_not_all_table_query(tmp_path, monkeypatch):
    """The resolver must call query_filing_candidates and must NOT call the
    all-table query() inside resolve."""
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    catalog = _seed_catalog(tmp_path, n_docs=2_000, with_files=True, acme_only=True)

    calls = []
    real_fc = catalog.query_filing_candidates
    monkeypatch.setattr(
        catalog, "query_filing_candidates",
        lambda **kw: (calls.append(("fc", kw)), real_fc(**kw))[1],
    )

    def boom(**kw):
        raise AssertionError("resolver must not call all-table query()")

    monkeypatch.setattr(catalog, "query", boom)

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="ACME", market="US", security_id="ACME",
            document_kind="annual_report", as_of_date="2026-07-18",
            fiscal_year=2025,
        )
    )
    assert calls, "resolver did not call query_filing_candidates"
    assert result.status.value in {"reused_exact", "reused_equivalent", "ambiguous"}


def test_explain_query_plan_hits_dedicated_indexes(tmp_path):
    catalog = _seed_catalog(tmp_path, n_docs=1_000)
    plan = catalog.explain_filing_candidates_plan(
        entity="ACME",
        document_kind="annual_report",
        source_statuses=("active",),
        root_ids=("company_raw",),
    )
    plan_text = " ".join(str(row) for row in plan)
    assert "idx_" in plan_text, f"no index hit in plan: {plan_text}"


def test_100k_candidate_lookup_within_slo(tmp_path):
    """Warm 100k-document lookup must meet the plan SLO: p95 ≤500ms and
    RSS increment ≤100MB (WU-3.2 gate). Timing is sampled multiple times
    and takes the p95; RSS is measured separately (tracemalloc skews timing)."""
    import statistics
    import time
    import tracemalloc

    catalog = _seed_catalog(tmp_path, n_docs=100_000)
    # warm the page cache / prepared statements; measure the resolver's
    # actual path (kind/status slice — entity/root stay in Python).
    catalog.query_filing_candidates(
        document_kind="annual_report",
        source_statuses=("active",),
        limit=100,
    )
    samples: list[float] = []
    for _ in range(5):
        start = time.monotonic()
        candidates = catalog.query_filing_candidates(
            document_kind="annual_report",
            source_statuses=("active",),
            limit=100,
        )
        samples.append(time.monotonic() - start)
    assert candidates
    p95 = statistics.quantiles(samples, n=20)[18]
    assert p95 < 0.5, (
        f"100k lookup p95 {p95:.2f}s (SLO 500ms); samples={[round(s, 3) for s in samples]}"
    )
    tracemalloc.start()
    catalog.query_filing_candidates(
        document_kind="annual_report",
        source_statuses=("active",),
        limit=100,
    )
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 100 * 1_000_000, f"RSS increment {peak / 1e6:.1f}MB (SLO 100MB)"
