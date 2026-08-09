"""WU-901 RED/audit tests: migration tool (MIG-01..08)."""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.migration import (  # noqa: E402
    MigrationConfig,
    migration_start,
)


def _catalog(tmp_path: Path, n_sources: int = 10) -> Path:
    """A small catalog with n sources (no assertion rows yet)."""
    import sqlite3

    path = tmp_path / "catalog.sqlite3"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE sources (source_id TEXT PRIMARY KEY, "
                "content_sha256 TEXT, byte_size INTEGER)")
    for i in range(n_sources):
        con.execute("INSERT INTO sources VALUES (?,?,?)",
                    (f"s{i:04d}", f"{i:064x}", 100))
    # production schema: assertions FK to documents via primary_source_id;
    # a source without a documents row is an orphan (skipped, counted).
    con.execute("CREATE TABLE documents (document_id TEXT PRIMARY KEY, "
                "primary_source_id TEXT, title TEXT, source_type TEXT, "
                "source_status TEXT)")
    for i in range(n_sources):
        con.execute("INSERT INTO documents VALUES (?,?,?,?,?)",
                    (f"d{i:04d}", f"s{i:04d}", f"title-{i}", "file", "active"))
    con.execute("CREATE TABLE source_metadata_assertions (assertion_id TEXT "
                "PRIMARY KEY, source_id TEXT, document_id TEXT, content_sha256 "
                "TEXT, evidence_basis TEXT, evidence_json TEXT, decision TEXT, "
                "created_at TEXT, created_by TEXT, schema_version TEXT, "
                "adapter_id TEXT, adapter_version TEXT, "
                "normalization_status TEXT, visibility_state TEXT)")
    con.execute("CREATE TABLE migration_journal (batch_id TEXT PRIMARY KEY, "
                "last_key TEXT, code_hash TEXT, plan_hash TEXT, input_hash "
                "TEXT, output_hash TEXT, created_assertions TEXT, "
                "committed_at TEXT)")
    con.commit()
    con.close()
    return path


def test_mig01_dry_run_writes_nothing(tmp_path):
    catalog = _catalog(tmp_path)
    result = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                             mode="dry-run")
    assert result.processed == 10
    assert result.created_assertions == 0
    import sqlite3

    con = sqlite3.connect(catalog)
    count = con.execute("SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    assert count == 0  # dry-run: zero writes


def test_mig02_apply_creates_assertions_and_journal(tmp_path):
    catalog = _catalog(tmp_path, n_sources=12)
    result = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                             mode="apply", batch_size=5)
    assert result.processed == 5
    assert result.created_assertions == 5
    import sqlite3

    con = sqlite3.connect(catalog)
    journal = con.execute("SELECT * FROM migration_journal").fetchall()
    assert len(journal) == 1
    assert journal[0][1] == "s0004"  # last key of the first batch


def test_mig04_resume_from_last_key(tmp_path):
    catalog = _catalog(tmp_path, n_sources=12)
    first = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                            mode="apply", batch_size=5)
    second = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                             mode="apply", batch_size=5,
                             last_key=first.journal[0]["last_key"])
    assert second.resumed_from == "s0004"
    assert second.processed == 5  # next 5 sources
    assert second.created_assertions == 5


def test_mig05_different_plan_hash_refuses_resume(tmp_path):
    catalog = _catalog(tmp_path, n_sources=6)
    first = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                            mode="apply", batch_size=5)
    with pytest.raises(ValueError, match="refusing resume"):
        migration_start(catalog, config=MigrationConfig("c2", "p2"),
                        mode="apply", batch_size=5,
                        last_key=first.journal[0]["last_key"])


def test_mig06_repeat_apply_no_duplicates(tmp_path):
    catalog = _catalog(tmp_path, n_sources=5)
    migration_start(catalog, config=MigrationConfig("c1", "p1"),
                    mode="apply", batch_size=5)
    migration_start(catalog, config=MigrationConfig("c1", "p1"),
                    mode="apply", batch_size=5)  # same batch again
    import sqlite3

    con = sqlite3.connect(catalog)
    count = con.execute("SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    assert count == 5  # idempotent: no duplicates


def test_mig07_unknown_mode_rejected(tmp_path):
    with pytest.raises(ValueError, match="unknown mode"):
        migration_start(_catalog(tmp_path), config=MigrationConfig("c1", "p1"),
                        mode="explode")


def test_mig08_input_output_hash_recorded(tmp_path):
    catalog = _catalog(tmp_path, n_sources=3)
    result = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                             mode="apply", batch_size=3)
    assert result.journal[0]["input_hash"]
    assert result.journal[0]["output_hash"]
    assert result.journal[0]["input_hash"] == result.journal[0]["output_hash"]


def test_mig09_orphan_source_skipped_not_fk_crash(tmp_path):
    """A source with no documents row cannot carry a FK-bound assertion on
    real catalogs: it is skipped and counted, never a crash (WU-906 drill A
    surfaced this against the production schema)."""
    catalog = _catalog(tmp_path, n_sources=4)
    con = sqlite3.connect(catalog)
    # remove one document row -> s0003 becomes an orphan source
    con.execute("DELETE FROM documents WHERE document_id='d0003'")
    con.commit()
    con.close()
    result = migration_start(catalog, config=MigrationConfig("c1", "p1"),
                             mode="apply", batch_size=4)
    assert result.processed == 4
    assert result.created_assertions == 3
    assert result.skipped == 1  # the orphan, counted not crashed
    con = sqlite3.connect(catalog)
    n = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    con.close()
    assert n == 3
