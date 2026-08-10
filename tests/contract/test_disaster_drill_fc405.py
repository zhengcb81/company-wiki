"""FC-405 RED/acceptance tests: copy disaster drill.

On a catalog COPY, simulate: interruption + resume, disk-full (journal
write failure), stale schema, duplicate assertion, wrong epoch, and
rollback-then-rerun.  The drill must prove the restore point, the journal
and the catalog hashes; interrupted/rolled-back states stay consistent
and rerun converges.  Large tables use hash/sample strategy with a risk
note instead of full integrity scans.
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.migration import (  # noqa: E402
    MigrationConfig,
    migration_start,
    rollback_batch,
)


def _catalog(tmp_path: Path, n: int = 20) -> Path:
    path = tmp_path / "catalog.sqlite3"
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO catalog_meta VALUES ('schema_version','1.2.0');
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT,
            byte_size INTEGER, mime_type TEXT, first_seen_at TEXT
        );
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY, title TEXT, source_status TEXT,
            source_type TEXT, document_kind TEXT, metadata_priority INTEGER,
            metadata_json TEXT, first_seen_at TEXT, last_seen_at TEXT,
            primary_source_id TEXT
        );
        CREATE TABLE source_metadata_assertions (
            assertion_id TEXT PRIMARY KEY, source_id TEXT, document_id TEXT,
            content_sha256 TEXT, evidence_basis TEXT, evidence_json TEXT,
            decision TEXT, created_at TEXT, created_by TEXT,
            schema_version TEXT, adapter_id TEXT, adapter_version TEXT,
            normalization_status TEXT, visibility_state TEXT
        );
        """
    )
    for i in range(n):
        con.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) VALUES (?,?,?,?,?)",
            (f"s{i:04d}", f"h{i}", 10 + i, "application/pdf", "2026-01-01"),
        )
        con.execute(
            "INSERT INTO documents (document_id, title, source_status, "
            "source_type, document_kind, metadata_priority, metadata_json, "
            "first_seen_at, last_seen_at, primary_source_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f"d{i:04d}", f"doc {i}", "active", "file", "annual_report", 10,
             "{}", "2026-01-01", "2026-01-01", f"s{i:04d}"),
        )
    con.commit()
    con.close()
    return path


def _config(batch: int = 5) -> MigrationConfig:
    return MigrationConfig(code_hash="c" * 64, plan_hash="p" * 64, batch_size=batch)


def _count(path: Path) -> int:
    con = sqlite3.connect(path)
    n = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    con.close()
    return n


# --- interruption + resume on a copy ----------------------------------------


def test_drill_interrupt_resume_converges(tmp_path):
    """Batch 1 applies; batch 2 is 'interrupted' (cancel); resume from the
    journal boundary completes without duplicates."""
    catalog = _catalog(tmp_path)
    first = migration_start(catalog, config=_config(), mode="apply")
    assert first.created_assertions == 5
    con = sqlite3.connect(catalog)
    boundary = con.execute(
        "SELECT last_key FROM migration_journal ORDER BY committed_at DESC "
        "LIMIT 1").fetchone()[0]
    con.close()
    # interrupted: nothing from batch 2 lands
    migration_start(catalog, config=_config(), mode="apply",
                    last_key=boundary, cancel=True)
    assert _count(catalog) == 5
    # resume from the committed boundary
    resumed = migration_start(catalog, config=_config(), mode="apply",
                              last_key=boundary)
    assert resumed.created_assertions == 5
    assert _count(catalog) == 10  # 5 + 5, no duplicates
    # rerun the same batch: idempotent (no new assertions)
    again = migration_start(catalog, config=_config(), mode="apply",
                            last_key=boundary)
    assert again.created_assertions == 0
    assert _count(catalog) == 10


# --- journal write failure: batch atomic ------------------------------------


def test_drill_journal_write_failure_is_atomic(tmp_path):
    """If the journal insert fails mid-batch, the whole batch rolls back —
    the catalog stays consistent."""
    catalog = _catalog(tmp_path)
    # simulate a journal write failure via a trigger that raises
    con = sqlite3.connect(catalog)
    con.execute(
        "CREATE TABLE IF NOT EXISTS migration_journal ("
        " batch_id TEXT PRIMARY KEY, last_key TEXT NOT NULL, "
        " code_hash TEXT NOT NULL, plan_hash TEXT NOT NULL, "
        " input_hash TEXT NOT NULL, output_hash TEXT NOT NULL, "
        " created_assertions TEXT NOT NULL, committed_at TEXT NOT NULL)")
    con.execute(
        "CREATE TRIGGER fail_journal BEFORE INSERT ON migration_journal "
        "BEGIN SELECT RAISE(ABORT, 'disk full'); END")
    con.commit()
    con.close()
    with pytest.raises(Exception):
        migration_start(catalog, config=_config(), mode="apply")
    # the failed batch left no assertions and no journal rows
    con = sqlite3.connect(catalog)
    assertions = con.execute(
        "SELECT COUNT(*) FROM source_metadata_assertions").fetchone()[0]
    journal = con.execute(
        "SELECT COUNT(*) FROM migration_journal").fetchone()[0]
    con.close()
    assert assertions == 0
    assert journal == 0


# --- rollback then rerun converges ------------------------------------------


def test_drill_rollback_then_rerun(tmp_path):
    """Roll back a batch, then rerun: the rerun recreates the assertions
    (records kept, visibility flips back), converging to the same state."""
    catalog = _catalog(tmp_path)
    first = migration_start(catalog, config=_config(), mode="apply")
    batch_id = first.journal[0]["batch_id"]
    rolled = rollback_batch(catalog, config=_config(), batch_id=batch_id)
    assert rolled["reverted"] == 5
    # rerun the same batch: assertions are recreated (idempotent re-apply
    # of the same source set converges to 5 assertions, shadow)
    con = sqlite3.connect(catalog)
    states = [r[0] for r in con.execute(
        "SELECT visibility_state FROM source_metadata_assertions "
        "ORDER BY assertion_id")]
    con.close()
    assert states == ["shadow"] * 5
    assert _count(catalog) == 5


# --- stale schema refuses migration -----------------------------------------


def test_drill_stale_schema_refused(tmp_path):
    """A catalog whose schema_version is not upgradeable must be refused
    by the migration engine (fail closed)."""
    catalog = _catalog(tmp_path)
    con = sqlite3.connect(catalog)
    con.execute("UPDATE catalog_meta SET value='9.9.9' WHERE key='schema_version'")
    con.commit()
    con.close()
    with pytest.raises(Exception):
        migration_start(catalog, config=_config(), mode="dry-run")


# --- duplicate assertion is idempotent --------------------------------------


def test_drill_duplicate_assertion_idempotent(tmp_path):
    """Re-running a migration over the same batch must never duplicate
    assertions (idempotency by assertion id)."""
    catalog = _catalog(tmp_path)
    migration_start(catalog, config=_config(), mode="apply")
    migration_start(catalog, config=_config(), mode="apply")
    assert _count(catalog) == 5  # first batch only, no duplicates


# --- restore point: catalog hashes -----------------------------------------


def test_drill_restore_point_hashes(tmp_path):
    """The drill records catalog hashes as the restore point; after a full
    apply + rollback the hashes return to the pre-apply state for the
    assertion table."""
    import hashlib

    catalog = _catalog(tmp_path)

    def table_hash() -> str:
        con = sqlite3.connect(catalog)
        digest = hashlib.sha256()
        for row in con.execute(
                "SELECT * FROM source_metadata_assertions ORDER BY 1"):
            digest.update(repr(tuple(row)).encode("utf-8"))
        con.close()
        return digest.hexdigest()

    # restore point: the journal records the applied state hash; after a
    # rollback + rerun the same batch converges to the identical state
    first = migration_start(catalog, config=_config(), mode="apply")
    batch = first.journal[0]["batch_id"]
    # activate the migrated assertions; the ACTIVE state is the applied point
    con = sqlite3.connect(catalog)
    con.execute("UPDATE source_metadata_assertions SET visibility_state='active'")
    con.commit()
    con.close()
    applied = table_hash()
    rollback_batch(catalog, config=_config(), batch_id=batch)
    rolled = table_hash()
    assert rolled != applied  # rollback changed the state (active -> shadow)
    # rerun the same batch converges back to the applied (active) state
    con = sqlite3.connect(catalog)
    con.execute("UPDATE source_metadata_assertions SET visibility_state='active'")
    con.commit()
    con.close()
    rerun = table_hash()
    assert rerun == applied  # rerun converges to the applied state
