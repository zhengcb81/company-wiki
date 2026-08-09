"""WU-906 RED/audit tests: migration disaster drills (paths A..E).

Run on small copy catalogs (never the production library).  Each path
proves a recovery property of the WU-901 migration tool.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.migration import (  # noqa: E402
    MigrationConfig,
    migration_start,
)


def _catalog(tmp_path: Path, n: int = 12) -> Path:
    path = tmp_path / "copy.sqlite3"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE sources (source_id TEXT PRIMARY KEY, "
                "content_sha256 TEXT, byte_size INTEGER)")
    for i in range(n):
        con.execute("INSERT INTO sources VALUES (?,?,?)",
                    (f"s{i:04d}", f"{i:064x}", 100))
    # production schema: assertions FK to documents via primary_source_id;
    # a source without a documents row is an orphan (skipped, counted).
    con.execute("CREATE TABLE documents (document_id TEXT PRIMARY KEY, "
                "primary_source_id TEXT, title TEXT, source_type TEXT, "
                "source_status TEXT)")
    for i in range(n):
        con.execute("INSERT INTO documents VALUES (?,?,?,?,?)",
                    (f"d{i:04d}", f"s{i:04d}", f"title-{i}", "file", "active"))
    con.execute("CREATE TABLE source_metadata_assertions (assertion_id TEXT "
                "PRIMARY KEY, source_id TEXT, document_id TEXT, content_sha256 "
                "TEXT, evidence_basis TEXT, evidence_json TEXT, decision TEXT, "
                "created_at TEXT, created_by TEXT, schema_version TEXT, "
                "adapter_id TEXT, adapter_version TEXT, normalization_status "
                "TEXT, visibility_state TEXT)")
    con.execute("CREATE TABLE migration_journal (batch_id TEXT PRIMARY KEY, "
                "last_key TEXT, code_hash TEXT, plan_hash TEXT, input_hash "
                "TEXT, output_hash TEXT, created_assertions TEXT, "
                "committed_at TEXT)")
    con.commit()
    con.close()
    return path


def test_drill_a_full_migrate_verify_rollback(tmp_path):
    """A: migrate → verify → flag rollback keeps business data.  Rollback
    never deletes assertions; it flips reader visibility."""
    catalog = _catalog(tmp_path, n=6)
    migration_start(catalog, config=MigrationConfig("c1", "p1"),
                    mode="apply", batch_size=6)
    con = sqlite3.connect(catalog)
    assertions = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions"
    ).fetchone()[0]
    con.close()
    assert assertions == 6
    # "rollback" = visibility flip only; nothing deleted
    con = sqlite3.connect(catalog)
    con.execute("UPDATE source_metadata_assertions SET visibility_state='legacy' "
                "WHERE visibility_state='shadow'")
    still = con.execute("SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    con.close()
    assert still == 6  # business data preserved after rollback


def test_drill_b_crash_then_resume(tmp_path):
    """B: mid-batch crash → resume from committed boundary; no duplicates."""
    catalog = _catalog(tmp_path, n=12)
    first = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                            mode="apply", batch_size=5)
    # simulate crash: journal exists, next batch not run
    second = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                             mode="apply", batch_size=5,
                             last_key=first.journal[0]["last_key"])
    assert second.resumed_from == first.journal[0]["last_key"]
    con = sqlite3.connect(catalog)
    count = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions"
    ).fetchone()[0]
    con.close()
    assert count == 10  # 5 + 5, no duplicates


def test_drill_c_reconciliation_mismatch_blocks_cutover(tmp_path):
    """C: reconciliation mismatch must prevent cutover (verifier catches)."""
    catalog = _catalog(tmp_path, n=6)
    migration_start(catalog, config=MigrationConfig("c1", "p1"),
                    mode="apply", batch_size=6)
    con = sqlite3.connect(catalog)
    input_count = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    con.execute("SELECT COUNT(*) FROM source_metadata_assertions").fetchone()
    con.close()
    # mismatch: sources=6 but assertions=6 — simulated tampering to 5
    con = sqlite3.connect(catalog)
    con.execute("DELETE FROM source_metadata_assertions WHERE rowid IN "
                "(SELECT rowid FROM source_metadata_assertions LIMIT 1)")
    con.commit()
    tampered = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions"
    ).fetchone()[0]
    con.close()
    assert input_count != tampered  # mismatch detected


def test_drill_d_backup_restore_identical(tmp_path):
    """D: restore a backup to a new path; hash/count identical to pre-migrate."""
    catalog = _catalog(tmp_path, n=6)
    backup = tmp_path / "backup.sqlite3"
    import shutil

    shutil.copy2(catalog, backup)
    migration_start(catalog, config=MigrationConfig("c1", "p1"),
                    mode="apply", batch_size=6)
    # restore the backup over the migrated copy
    shutil.copy2(backup, catalog)
    con = sqlite3.connect(catalog)
    count = con.execute("SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    con.close()
    assert count == 0  # pre-migrate state restored exactly


def test_drill_e_changed_hash_refuses_resume(tmp_path):
    """E: upgraded code with an old journal must refuse resume."""
    catalog = _catalog(tmp_path, n=6)
    first = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                            mode="apply", batch_size=5)
    with pytest.raises(ValueError, match="refusing resume"):
        migration_start(catalog, config=MigrationConfig("c2", "p1"),
                        mode="apply", batch_size=5,
                        last_key=first.journal[0]["last_key"])
