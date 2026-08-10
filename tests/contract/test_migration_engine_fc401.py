"""FC-401 RED/acceptance tests: recoverable migration engine additions.

The WU-901 engine already supports dry-run / resume-key / batch /
idempotency.  FC-401 adds: explicit cancel (no partial batch lands),
copy validation (verify a batch on a temp copy before apply), and a
rollback journal (MIG-04: a migrated batch can be rolled back to the
before trace without deleting records).  Batches stay bounded (no
long transactions, no full-table Python loads).
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.migration import (  # noqa: E402
    JOURNAL_TABLE,
    MigrationConfig,
    migration_start,
)


def _catalog(tmp_path: Path, n: int = 5) -> Path:
    path = tmp_path / "catalog.sqlite3"
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(
        """
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


def _config() -> MigrationConfig:
    return MigrationConfig(code_hash="c" * 64, plan_hash="p" * 64, batch_size=2)


def _assertions(path: Path) -> list[str]:
    con = sqlite3.connect(path)
    rows = [r[0] for r in con.execute(
        "SELECT assertion_id FROM source_metadata_assertions ORDER BY 1")]
    con.close()
    return rows


# --- explicit cancel: no partial batch lands ------------------------------


def test_cancel_prevents_batch_commit(tmp_path):
    """cancel=True must abort before any batch writes land."""
    catalog = _catalog(tmp_path)
    result = migration_start(
        catalog, config=_config(), mode="apply", cancel=True,
    )
    assert _assertions(catalog) == []
    assert result.created_assertions == 0


def test_cancel_after_partial_batches_resumes_cleanly(tmp_path):
    """Batch 1 applies; batch 2 is cancelled -> only batch 1's assertions
    exist and the journal boundary is exactly the committed last_key."""
    catalog = _catalog(tmp_path)
    first = migration_start(catalog, config=_config(), mode="apply")
    assert first.created_assertions == 2  # batch_size=2
    con = sqlite3.connect(catalog)
    journal = con.execute(
        f"SELECT last_key FROM {JOURNAL_TABLE} ORDER BY committed_at DESC "
        "LIMIT 1").fetchone()
    con.close()
    boundary = journal[0]
    # cancel the next batch: nothing new lands
    second = migration_start(
        catalog, config=_config(), mode="apply",
        last_key=boundary, cancel=True,
    )
    assert second.created_assertions == 0
    assert len(_assertions(catalog)) == 2


# --- copy validation: verify a batch on a temp copy before apply -----------


def test_copy_validation_runs_batch_on_copy(tmp_path):
    """validate_on_copy runs the batch against a temporary copy and
    returns its result without touching the source catalog."""
    catalog = _catalog(tmp_path)
    result = migration_start(
        catalog, config=_config(), mode="apply",
        validate_on_copy=True,
    )
    # source catalog untouched (only the copy received writes)
    assert _assertions(catalog) == []
    assert result.created_assertions == 2  # copy result reported


def test_copy_validation_catches_problems(tmp_path):
    """A copy that cannot be opened must fail closed, not silently skip."""
    catalog = _catalog(tmp_path)
    with pytest.raises(OSError):
        migration_start(
            catalog, config=_config(), mode="apply",
            validate_on_copy=True, copy_path=tmp_path / "no_dir" / "x.sqlite3",
        )


# --- rollback journal (MIG-04) ---------------------------------------------


def test_rollback_reverts_batch_keeps_records(tmp_path):
    """rollback_batch reverts a migrated batch: assertions become shadow
    (invisible) but are NOT deleted; the journal records the rollback."""
    from company_wiki.source_catalog.migration import rollback_batch

    catalog = _catalog(tmp_path)
    result = migration_start(catalog, config=_config(), mode="apply")
    assert result.created_assertions == 2
    before = _assertions(catalog)
    assert len(before) == 2
    # activate the migrated assertions so the rollback actually has
    # something to revert (assertions are born shadow)
    con = sqlite3.connect(catalog)
    con.execute(
        "UPDATE source_metadata_assertions SET visibility_state='active'")
    con.commit()
    con.close()

    rolled = rollback_batch(
        catalog, config=_config(), batch_id=result.journal[0]["batch_id"],
    )
    assert rolled["reverted"] == 2
    # records kept but shadow (invisible)
    con = sqlite3.connect(catalog)
    states = [r[0] for r in con.execute(
        "SELECT visibility_state FROM source_metadata_assertions "
        "ORDER BY assertion_id")]
    con.close()
    assert states == ["shadow", "shadow"]
    assert len(_assertions(catalog)) == 2  # not deleted
    # rollback journal row recorded
    con = sqlite3.connect(catalog)
    rows = con.execute(
        "SELECT batch_id, reverted_assertions FROM "
        "migration_rollback_journal ORDER BY 1").fetchall()
    con.close()
    assert len(rows) == 1
    assert rows[0][0] == result.journal[0]["batch_id"]


def test_rollback_unknown_batch_fails_closed(tmp_path):
    from company_wiki.source_catalog.migration import rollback_batch

    catalog = _catalog(tmp_path)
    with pytest.raises(KeyError):
        rollback_batch(catalog, config=_config(), batch_id="no-such-batch")


# --- bounded batches: no full-table loads ----------------------------------


def test_batch_stays_bounded(tmp_path):
    """A batch must process at most batch_size rows per pass (no full
    table load into Python)."""
    catalog = _catalog(tmp_path, n=100)
    result = migration_start(catalog, config=_config(), mode="dry-run")
    assert result.processed == 2  # batch_size=2, not 100
