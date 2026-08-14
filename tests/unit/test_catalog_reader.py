"""ZR-201 gate tests: zero-write CatalogReader protocol + read-only factory.

The counterexample under test (ZR001-W1): CatalogStore on a nonexistent
path creates a writable WAL database and crashes on an OS-read-only file.
These tests pin the reader's opposite behavior, fully hermetic on temp
databases only (the real 46GB catalog is never opened).
"""

from __future__ import annotations

import os
import sqlite3
import stat
from pathlib import Path

import pytest

from company_wiki.source_catalog.reader import (
    CatalogReader,
    CatalogReaderUnavailable,
    ReadOnlyCatalogReader,
)
from company_wiki.source_catalog.store import CatalogStore
from company_wiki.source_catalog.models import CATALOG_SCHEMA_VERSION


def _seed_catalog(path: Path) -> None:
    store = CatalogStore(path)
    del store


# ---------------------------------------------------------------------------
# missing path: raise, create nothing
# ---------------------------------------------------------------------------


def test_missing_path_raises_and_creates_nothing(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "catalog.sqlite3"
    with pytest.raises(CatalogReaderUnavailable):
        ReadOnlyCatalogReader(target)
    assert not target.exists(), "reader must not create the database file"
    assert not target.parent.exists(), "reader must not create parent dirs"
    assert list(tmp_path.iterdir()) == [], "filesystem must stay byte-identical"


# ---------------------------------------------------------------------------
# seeded temp catalog: read-only queries work; writes fail closed
# ---------------------------------------------------------------------------


def test_reads_work_and_writes_fail_closed(tmp_path: Path) -> None:
    db = tmp_path / "catalog.sqlite3"
    _seed_catalog(db)
    reader = ReadOnlyCatalogReader(db)
    try:
        row = reader.fetchone("SELECT COUNT(*) AS n FROM documents")
        assert row is not None
        assert row["n"] == 0
        rows = reader.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        names = [str(r["name"]) for r in rows]
        assert "documents" in names and "artifacts" in names
        with pytest.raises(sqlite3.OperationalError) as excinfo:
            reader.fetchone("CREATE TABLE zr201_probe(x INTEGER)")
        assert "readonly" in str(excinfo.value).lower()
    finally:
        reader.close()


def test_fetchone_none_for_missing_row(tmp_path: Path) -> None:
    db = tmp_path / "catalog.sqlite3"
    _seed_catalog(db)
    reader = ReadOnlyCatalogReader(db)
    try:
        assert reader.fetchone("SELECT * FROM documents WHERE document_id='?'") is None
    finally:
        reader.close()


# ---------------------------------------------------------------------------
# OS-read-only file: construction + SELECT succeed (anti-CatalogStore)
# ---------------------------------------------------------------------------


def test_os_read_only_file_succeeds(tmp_path: Path) -> None:
    db = tmp_path / "catalog.sqlite3"
    _seed_catalog(db)
    os.chmod(db, stat.S_IREAD)
    try:
        reader = ReadOnlyCatalogReader(db)
        try:
            row = reader.fetchone(
                "SELECT value FROM catalog_meta WHERE key='schema_version'"
            )
            assert row is not None
            assert row["value"] == CATALOG_SCHEMA_VERSION
        finally:
            reader.close()
    finally:
        os.chmod(db, stat.S_IWRITE)


# ---------------------------------------------------------------------------
# no WAL / no data-file mutation
# ---------------------------------------------------------------------------


def test_no_wal_and_no_data_file_mutation(tmp_path: Path) -> None:
    db = tmp_path / "catalog.sqlite3"
    _seed_catalog(db)
    # The SEEDER (CatalogStore) runs WAL mode; after close its -wal may be
    # checkpointed away.  SQLite's read protocol for a WAL-mode database may
    # (re)create EMPTY -wal/-shm side files when absent — that is OS-level
    # behavior, not a reader write (the reader never issues journal_mode/DDL
    # and the data file itself is byte-identical).  The invariant asserted
    # here: the data file is untouched and no side file ever receives data.
    size_before = db.stat().st_size
    mtime_before = db.stat().st_mtime_ns
    reader = ReadOnlyCatalogReader(db)
    try:
        reader.fetchall("SELECT COUNT(*) FROM documents")
    finally:
        reader.close()
    assert db.stat().st_size == size_before, "reader must not grow the data file"
    assert db.stat().st_mtime_ns == mtime_before, "reader must not write the data file"
    wal = Path(str(db) + "-wal")
    if wal.exists():
        assert wal.stat().st_size == 0, "no committed frames may appear in -wal"
    shm = Path(str(db) + "-shm")
    if shm.exists():
        # SQLite allocates a fixed 32KiB shm index header on open; anything
        # beyond the header would mean real index pages were written.
        assert shm.stat().st_size <= 32768, f"shm grew beyond header: {shm}"


# ---------------------------------------------------------------------------
# schema version + context manager + protocol + surface checks
# ---------------------------------------------------------------------------


def test_schema_version_reads_seeded_value(tmp_path: Path) -> None:
    db = tmp_path / "catalog.sqlite3"
    _seed_catalog(db)
    reader = ReadOnlyCatalogReader(db)
    try:
        assert reader.schema_version() == CATALOG_SCHEMA_VERSION
    finally:
        reader.close()


def test_context_manager(tmp_path: Path) -> None:
    db = tmp_path / "catalog.sqlite3"
    _seed_catalog(db)
    with ReadOnlyCatalogReader(db) as reader:
        assert reader.fetchone("SELECT 1 AS one")["one"] == 1


def test_protocol_runtime_checkable(tmp_path: Path) -> None:
    db = tmp_path / "catalog.sqlite3"
    _seed_catalog(db)
    reader = ReadOnlyCatalogReader(db)
    try:
        assert isinstance(reader, CatalogReader)
    finally:
        reader.close()


def test_no_public_write_surface(tmp_path: Path) -> None:
    db = tmp_path / "catalog.sqlite3"
    _seed_catalog(db)
    reader = ReadOnlyCatalogReader(db)
    try:
        public = {name for name in dir(reader) if not name.startswith("_")}
        forbidden = {"execute", "executescript", "commit", "rollback", "migrate"}
        assert not (public & forbidden), (
            f"reader exposes write surface: {public & forbidden}"
        )
    finally:
        reader.close()


def test_type_error_on_non_path(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        ReadOnlyCatalogReader(str(tmp_path / "catalog.sqlite3"))  # type: ignore[arg-type]
