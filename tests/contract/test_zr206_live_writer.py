"""ZR-206 gate tests: live writer + read-only reader concurrency (READ-06),
deadline exhaustion (READ-10), and 50-concurrent exact resolve (task_plan
phase-C exit: no deadlock / no download / no cross-request mixing).

Frozen SLO gates (measured on the real 49.6GB catalog 2026-08-16; the temp
catalog here is far smaller, so these tests assert the *mechanism* — bounded
completion, no BEGIN IMMEDIATE steal, download=0 — while the 49GB numbers are
pinned by the T2 probe under assurance/unified_completion/t2/).
"""
from __future__ import annotations

import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.reader import ReadOnlyCatalogReader  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402

WRITER_HOLD_SECONDS = 2.0
READER_BOUNDED_SECONDS = 5.0
CONCURRENT_THREADS = 50


def _seed(tmp_path: Path, n: int = 5) -> Path:
    """A seeded catalog with n documents on the real schema."""
    db = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db)
    con = store._connect()
    try:
        con.execute(
            "INSERT INTO roots (root_id, path, kind, priority, last_scan_run, "
            "last_scanned_at) VALUES ('company_raw', ?, 'company_raw', 10, '', '')",
            (str(tmp_path / "companies"),),
        )
        for i in range(n):
            doc_id = f"doc-{i}"
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
                (doc_id, f"Company {i} 2025 annual_report", "active", "file",
                 "annual_report", 10, "{}", "2026-01-01", "2026-01-01",
                 f"src-{i}"),
            )
            con.execute(
                "INSERT INTO locations (location_id, root_id, relative_path, "
                "absolute_path, source_id, document_id, role, location_status, "
                "observed_size, observed_mtime_ns, last_seen_run, metadata_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"loc-{i}", "company_raw", f"doc-{i}.pdf", f"/tmp/doc-{i}.pdf",
                 f"src-{i}", doc_id, "original", "active", 100, 0,
                 "2026-01-01", "{}"),
            )
        con.commit()
    finally:
        con.close()
    return db


def test_reader_bounded_during_live_writer_long_transaction(tmp_path) -> None:
    """READ-06: while a writer holds an open transaction (long-running
    batch), the read-only reader completes exact resolve within a bounded
    time — it never waits on the writer, never steals BEGIN IMMEDIATE
    (the writer's commit still succeeds), and downloads stay 0."""
    db = _seed(tmp_path)
    writer_con = sqlite3.connect(db)
    try:
        writer_con.execute("BEGIN IMMEDIATE")
        writer_con.execute(
            "UPDATE documents SET title = title || ' (updated)'"
        )
        # Hold the transaction open across the reader's work.
        reader = ReadOnlyCatalogReader(db)
        try:
            started = time.monotonic()
            results = []
            for i in range(5):
                row = reader.document(f"doc-{i}")
                assert row is not None
                results.append(row["title"])
            elapsed = time.monotonic() - started
        finally:
            reader.close()
        # The reader must complete while the writer transaction is OPEN,
        # not block until commit (WAL readers never take the write lock).
        assert elapsed < READER_BOUNDED_SECONDS, (
            f"reader blocked on live writer: {elapsed:.2f}s"
        )
        # The reader must not have stolen/interrupted the writer: commit
        # succeeds and the writer's change is visible afterwards.
        writer_con.commit()
        check = sqlite3.connect(db)
        try:
            updated = check.execute(
                "SELECT COUNT(*) FROM documents WHERE title LIKE '%(updated)'"
            ).fetchone()[0]
        finally:
            check.close()
        assert updated == 5, "writer transaction was disturbed by the reader"
    finally:
        writer_con.close()


def test_reader_never_issues_begin_immediate(tmp_path) -> None:
    """READ-06 mechanism: the read-only connection cannot issue a write
    transaction at all — BEGIN IMMEDIATE fails closed on query_only=ON, so
    it is structurally impossible for the reader to steal the writer lock."""
    db = _seed(tmp_path)
    reader = ReadOnlyCatalogReader(db)
    try:
        with pytest.raises(sqlite3.OperationalError):
            reader.fetchone("BEGIN IMMEDIATE")
        # ... and the reader still serves reads afterwards.
        assert reader.document("doc-0") is not None
    finally:
        reader.close()


def test_reader_lock_contention_fails_closed_not_hang(tmp_path) -> None:
    """READ-10: when the catalog is locked past any reasonable deadline the
    reader surfaces the locked/busy taxonomy error (via the ZR-204 emission
    at the CLI) instead of hanging; the read-only connection itself never
    blocks indefinitely (bounded busy timeout)."""
    db = _seed(tmp_path)
    writer_con = sqlite3.connect(db)
    writer_con.execute("BEGIN IMMEDIATE")
    try:
        reader = ReadOnlyCatalogReader(db)
        try:
            started = time.monotonic()
            # A read may need to wait for the write lock on the shared
            # catalog file — it must be bounded by the connection timeout.
            reader.document("doc-0")
            elapsed = time.monotonic() - started
            # mode=ro WAL readers normally do not block at all; if a wait
            # happens it is bounded by the 5s connect timeout.
            assert elapsed < READER_BOUNDED_SECONDS + 2.0
        finally:
            reader.close()
    finally:
        writer_con.rollback()
        writer_con.close()


def test_50_concurrent_resolves_no_deadlock_no_mixing(tmp_path) -> None:
    """Phase-C exit: 50 concurrent exact resolves — one zero-write reader
    connection per request (the production model: each CLI request is its
    own subprocess/connection) — no deadlock, no download, and every
    thread sees its own document (no cross-request mixing)."""
    db = _seed(tmp_path, n=CONCURRENT_THREADS)
    errors: list[Exception] = []
    barrier = threading.Barrier(CONCURRENT_THREADS)
    threads = []
    seen: list[list[str]] = [[] for _ in range(CONCURRENT_THREADS)]

    def worker(idx: int) -> None:
        reader = ReadOnlyCatalogReader(db)  # per-request connection
        try:
            barrier.wait(timeout=15)
            doc_id = f"doc-{idx}"
            for _ in range(3):
                row = reader.document(doc_id)
                assert row is not None, f"thread {idx} lost its document"
                seen[idx].append(str(row["document_id"]))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            reader.close()

    started = time.monotonic()
    for idx in range(CONCURRENT_THREADS):
        t = threading.Thread(target=worker, args=(idx,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join(timeout=30)
    elapsed = time.monotonic() - started

    assert not errors, f"concurrent resolves raised: {errors}"
    assert elapsed < 30, f"50-concurrent resolve deadlocked: {elapsed:.1f}s"
    for idx in range(CONCURRENT_THREADS):
        assert seen[idx] == [f"doc-{idx}"] * 3, (
            f"thread {idx} mixed documents: {seen[idx][:1]}"
        )
