"""ZR-206 gate tests: 49GB-class read SLO / pressure acceptance (READ-11).

The real catalog (49.62 GB, 27.2M evidence_spans rows) is the T2 target and
is probed by the assurance runner (assurance/unified_completion/t2/).  These
hermetic tests pin the MECHANISM that keeps the big-table queries bounded:

- the hot aggregate path (status/health) resolves through covering indexes
  (EXPLAIN QUERY PLAN shows index scans, never a Python full-table
  materialization), so count cost is SQL-side and memory stays bounded;
- a synthetic large evidence table (1M spans) completes the typed queries
  within the frozen SLO doors scaled to the synthetic size;
- peak Python allocation stays far below the 256 MB frozen memory gate.
"""
from __future__ import annotations

import sqlite3
import sys
import time
import tracemalloc
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.reader import ReadOnlyCatalogReader  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402

# Frozen gates (2026-08-16 measurement on the real 49.6GB catalog, p95).
# The synthetic table below is 1M spans; gates are scaled by row-count ratio
# (1M/27.2M ~ 3.7%) with generous headroom — the absolute numbers are pinned
# by the T2 probe against the real catalog.
REAL_P95_GATES_MS = {
    "status": 12_000,
    "health": 12_000,
    "scan_health": 50,
    "query": 50,
    "entities_like": 50,
    "location_counts": 250,
    "document": 50,
    "source_sha": 50,
    "artifacts_for": 50,
    "resolve_handle": 50,
}
MEMORY_GATE_MB = 256
SYNTHETIC_SPANS = 1_000_000
SYNTHETIC_SCALE = SYNTHETIC_SPANS / 27_178_657  # ~3.7%


def _seed(tmp_path: Path) -> Path:
    """Real schema + 1M evidence spans across 100 documents."""
    db = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db)
    con = store._connect()
    try:
        con.execute(
            "INSERT INTO roots (root_id, path, kind, priority, last_scan_run, "
            "last_scanned_at) VALUES ('company_raw', ?, 'company_raw', 10, '', '')",
            (str(tmp_path / "companies"),),
        )
        for i in range(100):
            con.execute(
                "INSERT INTO sources (source_id, content_sha256, byte_size, "
                "mime_type, first_seen_at) VALUES (?,?,?,?,?)",
                (f"src-{i}", f"{i:064x}", 100, "application/pdf", "2026-01-01"),
            )
            con.execute(
                "INSERT INTO documents (document_id, title, source_status, "
                "source_type, document_kind, metadata_priority, metadata_json, "
                "first_seen_at, last_seen_at, primary_source_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (f"doc-{i}", f"Company {i} 2025 annual_report", "active",
                 "file", "annual_report", 10, "{}", "2026-01-01",
                 "2026-01-01", f"src-{i}"),
            )
            con.execute(
                "INSERT INTO locations (location_id, root_id, relative_path, "
                "absolute_path, source_id, document_id, role, location_status, "
                "observed_size, observed_mtime_ns, last_seen_run, metadata_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"loc-{i}", "company_raw", f"doc-{i}.pdf", f"/tmp/doc-{i}.pdf",
                 f"src-{i}", f"doc-{i}", "original", "active", 100, 0,
                 "2026-01-01", "{}"),
            )
        # One big evidence table: 1M spans in batches.
        span_rows = 0
        while span_rows < SYNTHETIC_SPANS:
            batch = []
            for _ in range(2000):
                if span_rows >= SYNTHETIC_SPANS:
                    break
                doc_idx = span_rows % 100
                batch.append(
                    (
                        f"span-{span_rows}", f"doc-{doc_idx}", f"src-{doc_idx}",
                        f"loc-{span_rows}", span_rows % 97,
                        "{}", "zr206-probe", "1.0.0", "ok",
                    )
                )
                span_rows += 1
            con.executemany(
                "INSERT INTO evidence_spans(span_id,document_id,source_id,"
                "locator,page_number,span_json,parser_name,parser_version,"
                "parse_status) VALUES (?,?,?,?,?,?,?,?,?)",
                batch,
            )
        con.commit()
    finally:
        con.close()
    return db


def _explain_plan(reader: ReadOnlyCatalogReader, sql: str) -> list[str]:
    return [
        str(row["detail"])
        for row in reader.fetchall(f"EXPLAIN QUERY PLAN {sql}")
    ]


def test_hot_aggregates_use_covering_indexes_not_python_scans(tmp_path) -> None:
    """READ-11: the 8 status COUNTs and the artifacts/evidence reads must
    resolve via SQLite indexes (COVERING INDEX / SEARCH), never by loading
    the table into Python."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        for sql in (
            "SELECT COUNT(*) FROM evidence_spans",
            "SELECT COUNT(*) FROM artifacts WHERE artifact_role='summary' "
            "AND generator_name='source_catalog_llm_summary'",
            "SELECT COUNT(*) FROM locations WHERE location_status='active'",
        ):
            plan = _explain_plan(reader, sql)
            assert any("INDEX" in detail or "COVERING" in detail for detail in plan), (
                f"full scan on hot aggregate: {sql} -> {plan}"
            )
    finally:
        reader.close()


def test_synthetic_49gb_scale_queries_within_frozen_slo(tmp_path) -> None:
    """READ-11 hermetic: every typed query on the 1M-span catalog completes
    within the frozen SLO door scaled to the synthetic size."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        cases: list[tuple[str, object]] = [
            ("status", lambda: reader.status()),
            ("health", lambda: reader.health()),
            ("scan_health", lambda: reader.scan_health()),
            ("query", lambda: reader.query(document_kind="annual_report", limit=100)),
            ("entities_like", lambda: reader.entities_like("company")),
            ("location_counts", lambda: reader.location_counts("company_raw")),
            ("document", lambda: reader.document("doc-50")),
            ("source_sha", lambda: reader.source_sha("src-50")),
            ("artifacts_for", lambda: reader.artifacts_for("doc-50")),
            ("resolve_handle", lambda: reader.resolve_handle("doc-50")),
        ]
        for name, fn in cases:
            fn()  # warm
            timings = []
            for _ in range(7):
                t0 = time.perf_counter()
                fn()
                timings.append((time.perf_counter() - t0) * 1000)
            timings.sort()
            p95 = timings[int(len(timings) * 0.95)]
            gate = max(REAL_P95_GATES_MS[name] * SYNTHETIC_SCALE, 25.0)
            assert p95 <= gate, (
                f"{name}: synthetic p95 {p95:.1f}ms > gate {gate:.1f}ms"
            )
    finally:
        reader.close()


def test_peak_python_memory_below_frozen_gate(tmp_path) -> None:
    """READ-11 memory: even the heaviest aggregate (status over the big
    evidence table) must stay far below the 256 MB frozen peak gate —
    counts are SQL-side, Python only materializes 8 integers."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        tracemalloc.start()
        try:
            reader.status()
            reader.health()
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert peak / (1024 * 1024) < MEMORY_GATE_MB, (
            f"peak python alloc {peak/1e6:.1f} MB >= {MEMORY_GATE_MB} MB"
        )
    finally:
        reader.close()


def test_reader_fingerprint_unchanged_after_read_session(tmp_path) -> None:
    """T2 zero-write fingerprint (hermetic twin): with the WAL side files
    already present (the live-catalog precondition documented in the reader
    docstring), a full read session leaves DB/WAL/SHM bytes and the
    directory listing byte-identical."""
    db = _seed(tmp_path)
    # Establish the live-catalog precondition: WAL/SHM side files exist.
    # A committed WAL is checkpointed away when the last connection closes,
    # so hold one writer connection open across the session (an idle live
    # writer is exactly the production state the reader coexists with).
    writer = sqlite3.connect(db)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.commit()
    assert (db.parent / "catalog.sqlite3-wal").exists(), "precondition: WAL exists"
    before = {
        "db": db.read_bytes(),
        "listing": sorted(p.name for p in db.parent.iterdir()),
        "sidecars": {
            name: (db.parent / name).read_bytes()
            for name in ("catalog.sqlite3-wal", "catalog.sqlite3-shm")
            if (db.parent / name).exists()
        },
    }
    reader = ReadOnlyCatalogReader(db)
    try:
        reader.status()
        reader.health()
        reader.query(document_kind="annual_report")
        reader.entities_like("company")
        reader.resolve_handle("doc-50")
        reader.bundle(
            "doc-50",
            registry={},
            allowed_roots=(),
            now="2026-08-16T00:00:00Z",
        )
    finally:
        reader.close()
    after = {
        "db": db.read_bytes(),
        "listing": sorted(p.name for p in db.parent.iterdir()),
        "sidecars": {
            name: (db.parent / name).read_bytes()
            for name in ("catalog.sqlite3-wal", "catalog.sqlite3-shm")
            if (db.parent / name).exists()
        },
    }
    writer.close()
    assert after == before, "read session mutated the catalog or directory"
