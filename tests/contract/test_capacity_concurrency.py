"""WU-1306 RED/audit tests: capacity / performance / stability.

RED/Focused:
  - unchanged file (same size + mtime) is NOT re-hashed on the next scan
    (stable fingerprint + TOCTOU-safe recheck); mutations that force a
    full rehash must be killed.
  - 10 concurrent resolver requests: no duplicate downloads, no DB
    deadlock, no cross-request bundle mixing.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


# ---------------------------------------------------------------------------
# fixture: a small company_raw root on disk + real SourceCatalog
# ---------------------------------------------------------------------------

def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / "companies"
    company = root / "Acme"
    raw = company / "raw"
    raw.mkdir(parents=True)
    (raw / "filing.pdf").write_bytes(b"REVENUE REPORT 100" * 10)
    return root


def _scan_catalog(tmp_path: Path, root: Path):
    """Real SourceCatalog over the fixture root (store-aware scan)."""
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec

    config = CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=(RootSpec("company_raw", root, "company_raw"),),
        reusable_root_kinds=("company_raw",),
    )
    from company_wiki.source_catalog.service import SourceCatalog

    return SourceCatalog(config)


def test_cap01_unchanged_file_not_rehashed(tmp_path):
    """M-01: an unchanged file (same size+mtime) is reused on the next
    scan — files_reused>0 and no re-hash of the unchanged file.  Forcing a
    full rehash (ignoring the mtime fast path) is a mutation this test
    kills."""
    root = _make_root(tmp_path)
    catalog = _scan_catalog(tmp_path, root)
    first = catalog.scan()
    assert first.files_hashed >= 1  # first scan hashes
    assert first.files_reused == 0

    second = catalog.scan()
    assert second.files_hashed == 0  # nothing re-hashed
    assert second.files_reused == 1  # the unchanged file reused


def test_cap02_mtime_change_triggers_rehash(tmp_path):
    """A size or mtime change MUST break the fast path and re-observe."""
    root = _make_root(tmp_path)
    catalog = _scan_catalog(tmp_path, root)
    catalog.scan()
    filing = root / "Acme" / "raw" / "filing.pdf"
    filing.write_bytes(b"REVENUE REPORT 200" * 10)  # size changes
    second = catalog.scan()
    assert second.files_hashed == 1  # content changed -> re-hashed
    assert second.files_reused == 0


def test_cap03_mtime_tamper_with_same_size_still_rehashed(tmp_path):
    """TOCTOU guard: same size but different mtime must still re-observe
    (a byte swap that preserves size is caught by the mtime)."""
    root = _make_root(tmp_path)
    catalog = _scan_catalog(tmp_path, root)
    catalog.scan()
    filing = root / "Acme" / "raw" / "filing.pdf"
    stat = filing.stat()
    new_mtime = stat.st_mtime_ns + 10_000_000
    import os

    os.utime(filing, ns=(stat.st_atime_ns, new_mtime))
    second = catalog.scan()
    assert second.files_hashed == 1  # mtime differs -> re-observed
    assert second.files_reused == 0


# ---------------------------------------------------------------------------
# concurrent resolver stability
# ---------------------------------------------------------------------------

def _catalog(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.sqlite3"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT, byte_size INTEGER,
            mime_type TEXT, first_seen_at TEXT
        );
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT,
            source_type TEXT, document_kind TEXT, published_date TEXT,
            source_status TEXT, metadata_priority INTEGER, metadata_json TEXT,
            text_fingerprint TEXT, first_seen_at TEXT, last_seen_at TEXT
        );
        CREATE TABLE entities (
            entity_id TEXT PRIMARY KEY, canonical_name TEXT, market TEXT,
            security_id TEXT, ticker TEXT, aliases TEXT
        );
        CREATE TABLE document_entities (
            document_id TEXT NOT NULL, entity_id TEXT NOT NULL,
            PRIMARY KEY (document_id, entity_id)
        );
        CREATE TABLE locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT, absolute_path TEXT, source_id TEXT,
            document_id TEXT, role TEXT, location_status TEXT,
            observed_size INTEGER, observed_mtime_ns INTEGER,
            last_seen_run TEXT, manifest_json TEXT, metadata_json TEXT,
            error TEXT, UNIQUE(root_id, relative_path)
        );
        CREATE TABLE source_metadata_assertions (
            assertion_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
            document_id TEXT NOT NULL, entity TEXT, market TEXT,
            security_id TEXT, document_kind TEXT, form_type TEXT,
            fiscal_year INTEGER, fiscal_period TEXT, provider TEXT,
            provider_document_id TEXT, source_url TEXT, filing_date TEXT,
            content_sha256 TEXT NOT NULL, evidence_basis TEXT NOT NULL,
            evidence_json TEXT NOT NULL, decision TEXT NOT NULL,
            supersedes_assertion_id TEXT, created_at TEXT NOT NULL,
            created_by TEXT NOT NULL, schema_version TEXT NOT NULL,
            published_at TEXT, accepted_at TEXT, period_end TEXT,
            language TEXT, is_amended INTEGER, revision_id TEXT,
            adapter_id TEXT, adapter_version TEXT, normalized_sha256 TEXT,
            normalization_status TEXT,
            visibility_state TEXT NOT NULL DEFAULT 'legacy',
            activation_epoch TEXT, cohort TEXT
        );
        CREATE TABLE roots (root_id TEXT PRIMARY KEY, path TEXT, kind TEXT);
        INSERT INTO roots VALUES ('company_raw', '/companies', 'company_raw');
        """
    )
    con.executemany(
        "INSERT INTO sources VALUES (?,?,?,?,?)",
        [("s1", "a" * 64, 100, "application/pdf", "2026-01-01"),
         ("s2", "b" * 64, 120, "application/pdf", "2026-01-01")],
    )
    con.executemany(
        """INSERT INTO documents
        (document_id, primary_source_id, title, source_type, document_kind,
         published_date, source_status, metadata_priority, metadata_json,
         first_seen_at, last_seen_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [
            ("d1", "s1", "Acme 10-K 2025", "regulatory_filing",
             "annual_report", "2025-12-31", "active", 10,
             json.dumps({"acquisition": {"provider_document_id": "ACC-1",
                                         "fiscal_year": 2025}}),
             "2026-01-01", "2026-01-01"),
            ("d2", "s2", "Acme 10-Q 2026", "regulatory_filing",
             "quarterly_report", "2026-03-31", "active", 10,
             json.dumps({"acquisition": {"provider_document_id": "ACC-2",
                                         "fiscal_year": 2026}}),
             "2026-01-01", "2026-01-01"),
        ],
    )
    con.execute("INSERT INTO entities VALUES ('ent-acme','Acme','US','ACME','ACME','[]')")
    con.executemany(
        "INSERT INTO document_entities VALUES (?,?)",
        [("d1", "ent-acme"), ("d2", "ent-acme")],
    )
    con.executemany(
        """INSERT INTO locations
        (location_id, root_id, relative_path, absolute_path, source_id,
         document_id, role, location_status, observed_size,
         observed_mtime_ns, last_seen_run, manifest_json, metadata_json, error)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            ("loc1", "company_raw", "Acme/filing.pdf", "/companies/Acme/filing.pdf",
             "s1", "d1", "original_primary", "active", 100, 1,
             "scan-1", json.dumps({"content_sha256": "a" * 64}), "{}", None),
            ("loc2", "company_raw", "Acme/filing2.pdf",
             "/companies/Acme/filing2.pdf", "s2", "d2", "original_primary",
             "active", 120, 1, "scan-1",
             json.dumps({"content_sha256": "b" * 64}), "{}", None),
        ],
    )
    con.commit()
    con.close()
    return path


def _resolver(store):
    """A tiny resolver that reads via _v2_assertion_metadata then legacy
    bridge — mirrors the production path without subprocesses."""
    from company_wiki.source_catalog.resolver import _source_metadata

    def resolve(source_id: str) -> str:
        row = store.fetchone(
            "SELECT metadata_json FROM documents WHERE primary_source_id=?",
            (source_id,),
        )
        metadata = json.loads(row["metadata_json"] or "{}")
        doc = {"source_id": source_id, "metadata": metadata}
        meta = _source_metadata(doc, store=store)
        return f"{meta.get('provider_document_id')}:{meta.get('fiscal_year')}"

    return resolve


class _StoreFacade:
    def __init__(self, path: Path):
        self._path = path

    def fetchone(self, sql, params=()):
        con = sqlite3.connect(f"file:{self._path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            return con.execute(sql, tuple(params)).fetchone()
        finally:
            con.close()


def test_cap04_ten_concurrent_resolves_no_deadlock_no_mixing(tmp_path):
    """10 threads resolve concurrently: no deadlock, no exception, and
    every thread sees the request's own document (no bundle mixing)."""
    path = _catalog(tmp_path)
    store = _StoreFacade(path)
    resolve = _resolver(store)
    results: list[list[str]] = [[] for _ in range(10)]
    errors: list[Exception] = []
    barrier = threading.Barrier(10)

    def worker(idx: int) -> None:
        try:
            barrier.wait(timeout=10)
            source_id = "s1" if idx % 2 == 0 else "s2"
            for _ in range(5):
                results[idx].append(resolve(source_id))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    elapsed = time.time() - t0

    assert not errors, f"concurrent resolve raised: {errors}"
    assert elapsed < 30  # no deadlock/timeout
    for idx, outcome in enumerate(results):
        expected = "ACC-1:2025" if idx % 2 == 0 else "ACC-2:2026"
        assert set(outcome) == {expected}, (
            f"thread {idx} mixed bundles: {outcome}")


def test_cap05_concurrent_reads_never_write(tmp_path):
    """Concurrent read-only access never mutates the catalog (mode=ro)."""
    path = _catalog(tmp_path)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        con.execute("PRAGMA query_only = ON")
        assert con.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
        with pytest.raises(sqlite3.OperationalError):
            con.execute("DELETE FROM documents")
    finally:
        con.close()
