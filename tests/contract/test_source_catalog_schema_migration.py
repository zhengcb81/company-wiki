"""Schema migration contracts: additive text_fingerprint column."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def _catalog_module():
    import company_wiki.source_catalog as module

    return module


def _catalog_store_cls():
    from company_wiki.source_catalog.store import CatalogStore

    return CatalogStore


def _documents_columns(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        return [row[1] for row in conn.execute("PRAGMA table_info(documents)")]


def _schema_version(db_path: Path) -> str:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT value FROM catalog_meta WHERE key='schema_version'"
        ).fetchone()[0]


def test_fresh_database_has_text_fingerprint_column(tmp_path):
    module = _catalog_module()
    db_path = tmp_path / "catalog.sqlite3"

    _catalog_store_cls()(db_path)

    assert "text_fingerprint" in _documents_columns(db_path)
    assert _schema_version(db_path) == module.CATALOG_SCHEMA_VERSION


def test_migrate_legacy_database_adds_text_fingerprint(tmp_path):
    """A 1.0.0 DB (full schema, no text_fingerprint) migrates on open, idempotently."""
    module = _catalog_module()
    db_path = tmp_path / "catalog.sqlite3"

    # Build a current-schema DB, then regress it to the legacy 1.0.0 shape:
    # drop the new column and reset the schema version. This mirrors a real
    # production catalog created before this column existed.
    _catalog_store_cls()(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO documents(document_id, title, source_type, document_kind, "
            "source_status, metadata_priority, metadata_json, first_seen_at, last_seen_at) "
            "VALUES('d1','legacy','news','news','active',0,'{}',"
            "'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z')"
        )
        conn.execute("ALTER TABLE documents DROP COLUMN text_fingerprint")
        conn.execute(
            "UPDATE catalog_meta SET value='1.0.0' WHERE key='schema_version'"
        )
        conn.commit()
    assert "text_fingerprint" not in _documents_columns(db_path)

    store = _catalog_store_cls()(db_path)
    assert "text_fingerprint" in _documents_columns(db_path)
    assert _schema_version(db_path) == module.CATALOG_SCHEMA_VERSION
    # Existing rows survive the migration; fingerprint stays null until computed.
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT document_id, text_fingerprint FROM documents WHERE document_id='d1'"
        ).fetchone()
    assert row == ("d1", None)

    # Idempotent: re-opening must not error and must keep the column/version.
    _catalog_store_cls()(db_path)
    assert "text_fingerprint" in _documents_columns(db_path)
    assert _schema_version(db_path) == module.CATALOG_SCHEMA_VERSION
    assert store is not None


# ---------------------------------------------------------------------
# CW-2.28 Phase 2R (§12.3 / §12.4.2 T2-01, T2-02): document_fingerprint_state
# ---------------------------------------------------------------------


def _tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        return {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}


def _fingerprint_state_counts(db_path: Path) -> dict[str, int]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM document_fingerprint_state GROUP BY status"
        ).fetchall()
    return {row[0]: int(row[1]) for row in rows}


def _insert_document(
    db_path: Path, doc_id: str, *, content_sha: str, fingerprint: str | None
) -> None:
    """Insert a source + document bound to it with the given fingerprint.

    Tolerates a missing ``text_fingerprint`` column (1.0.0 shape): when the
    column is absent the fingerprint is simply not set, so the row will be NULL
    after the migration re-adds the column.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO sources(source_id, content_sha256, byte_size, mime_type, "
            "first_seen_at) VALUES(?,?,?,?,?)",
            (f"src_{doc_id}", content_sha, 100, "text/plain", "2026-01-01T00:00:00Z"),
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(documents)")}
        if "text_fingerprint" in columns:
            conn.execute(
                "INSERT INTO documents(document_id, primary_source_id, title, "
                "source_type, document_kind, source_status, metadata_priority, "
                "metadata_json, text_fingerprint, first_seen_at, last_seen_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    doc_id, f"src_{doc_id}", doc_id, "news", "news", "active", 0, "{}",
                    fingerprint, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z",
                ),
            )
        else:
            conn.execute(
                "INSERT INTO documents(document_id, primary_source_id, title, "
                "source_type, document_kind, source_status, metadata_priority, "
                "metadata_json, first_seen_at, last_seen_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    doc_id, f"src_{doc_id}", doc_id, "news", "news", "active", 0, "{}",
                    "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z",
                ),
            )
        conn.commit()


def test_t2_01_fresh_database_has_fingerprint_state_and_dispatch_index(tmp_path):
    module = _catalog_module()
    db_path = tmp_path / "catalog.sqlite3"
    _catalog_store_cls()(db_path)

    assert "document_fingerprint_state" in _tables(db_path)
    assert _schema_version(db_path) == "1.2.0"
    with sqlite3.connect(db_path) as conn:
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
    assert "idx_fingerprint_state_dispatch" in indexes
    assert module.CATALOG_SCHEMA_VERSION == "1.2.0"


def test_t2_01_migrate_legacy_1_0_creates_state_table_and_seeds(tmp_path):
    """A 1.0.0 catalog (no text_fingerprint, no state table) upgrades to 1.2.0.

    Existing documents are seeded as ``pending`` (their fingerprint column is
    NULL after re-add). The state table + dispatch index must appear.
    """
    db_path = tmp_path / "catalog.sqlite3"
    _catalog_store_cls()(db_path)
    # Regress to a 1.0.0 shape: drop state table + fingerprint column.
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE document_fingerprint_state")
        conn.execute("ALTER TABLE documents DROP COLUMN text_fingerprint")
        conn.execute("UPDATE catalog_meta SET value='1.0.0' WHERE key='schema_version'")
        conn.commit()
    _insert_document(db_path, "d1", content_sha="aa" * 32, fingerprint=None)
    # column dropped above; d1 has no fingerprint column to set — that's the point
    with sqlite3.connect(db_path) as conn:
        # documents row count sanity
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1

    _catalog_store_cls()(db_path)  # reopen → migrates 1.0.0 -> 1.2.0

    assert "document_fingerprint_state" in _tables(db_path)
    assert "text_fingerprint" in _documents_columns(db_path)
    assert _schema_version(db_path) == "1.2.0"
    counts = _fingerprint_state_counts(db_path)
    assert counts.get("pending", 0) == 1, counts
    assert counts.get("completed", 0) == 0, counts


def test_t2_01_migrate_legacy_1_1_seeds_completed_and_pending(tmp_path):
    """A 1.1.0 catalog upgrades to 1.2.0 and seeds by fingerprint presence."""
    db_path = tmp_path / "catalog.sqlite3"
    _catalog_store_cls()(db_path)
    # Two docs: one already has a fingerprint, one does not.
    _insert_document(db_path, "d_done", content_sha="cc" * 32, fingerprint="fp_done")
    _insert_document(db_path, "d_null", content_sha="dd" * 32, fingerprint=None)
    # Regress to 1.1.0: drop state table only (keep text_fingerprint column+data).
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE document_fingerprint_state")
        conn.execute("UPDATE catalog_meta SET value='1.1.0' WHERE key='schema_version'")
        conn.commit()
    assert "document_fingerprint_state" not in _tables(db_path)

    _catalog_store_cls()(db_path)  # reopen → migrates 1.1.0 -> 1.2.0

    assert _schema_version(db_path) == "1.2.0"
    counts = _fingerprint_state_counts(db_path)
    assert counts.get("completed", 0) == 1, counts
    assert counts.get("pending", 0) == 1, counts


def test_t2_02_migration_is_idempotent(tmp_path):
    """Re-opening a 1.2.0 catalog must not duplicate or alter fingerprint state."""
    db_path = tmp_path / "catalog.sqlite3"
    _catalog_store_cls()(db_path)
    _insert_document(db_path, "d1", content_sha="ee" * 32, fingerprint=None)
    _insert_document(db_path, "d2", content_sha="ff" * 32, fingerprint="fp2")
    # First reopen seeds the new docs (seed runs on every open for missing rows).
    _catalog_store_cls()(db_path)
    counts_before = _fingerprint_state_counts(db_path)
    with sqlite3.connect(db_path) as conn:
        row_before = conn.execute(
            "SELECT status, attempt_count, source_sha256 FROM document_fingerprint_state "
            "WHERE document_id='d2'"
        ).fetchone()

    _catalog_store_cls()(db_path)  # reopen again — must be a no-op on state
    _catalog_store_cls()(db_path)

    assert _schema_version(db_path) == "1.2.0"
    assert _fingerprint_state_counts(db_path) == counts_before, "state counts drifted"
    with sqlite3.connect(db_path) as conn:
        row_after = conn.execute(
            "SELECT status, attempt_count, source_sha256 FROM document_fingerprint_state "
            "WHERE document_id='d2'"
        ).fetchone()
    assert row_after == row_before, "seeded row was mutated on idempotent reopen"


def test_t2_01_unknown_future_version_fails_closed(tmp_path):
    """An unrecognized schema version must be rejected with no state seeding."""
    db_path = tmp_path / "catalog.sqlite3"
    _catalog_store_cls()(db_path)
    _insert_document(db_path, "d1", content_sha="11" * 32, fingerprint=None)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE catalog_meta SET value='9.9.9' WHERE key='schema_version'")
        conn.commit()

    with pytest.raises(ValueError, match="unsupported source catalog schema version"):
        _catalog_store_cls()(db_path)

    # Fail-closed: no fingerprint state rows were written for the unknown version.
    assert _fingerprint_state_counts(db_path) == {}

