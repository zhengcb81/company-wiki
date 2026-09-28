"""Automation schema v2 migration contracts for the recoverable worker."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from company_wiki.automation import migrations


EXPECTED_V2_TABLES = {
    "events",
    "jobs",
    "job_dependencies",
    "attempts",
    "approvals",
    "effects",
    "outbox",
    "notifications",
    "runtime_gate",
}


def _create_v1_database(path: Path) -> None:
    """Create the frozen predecessor schema without invoking current migration."""
    statements = getattr(migrations, "_DDL_V1_STATEMENTS", migrations._DDL_STATEMENTS)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        for statement in statements:
            connection.execute(statement)
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
    finally:
        connection.close()


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


def test_v2_new_database_has_gate_generation_and_claim_indexes(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"

    report = migrations.migrate_database(database)

    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert _table_names(connection) == EXPECTED_V2_TABLES
        columns = {
            row[1]: (row[2], row[3], row[4])
            for row in connection.execute("PRAGMA table_info(attempts)")
        }
        assert columns["runtime_generation"] == ("INTEGER", 1, "0")
        gate = connection.execute(
            "SELECT singleton_id, desired_state, control_generation, updated_at "
            "FROM runtime_gate"
        ).fetchone()
        assert gate == (1, "paused", 1, "1970-01-01T00:00:00Z")
        index_names = {
            row[1]
            for table in ("jobs", "attempts", "outbox")
            for row in connection.execute(f"PRAGMA index_list({table})")
        }
        assert {
            "idx_jobs_claim",
            "idx_attempts_latest",
            "idx_outbox_claim",
        } <= index_names
    finally:
        connection.close()

    assert report.from_version == 0
    assert report.to_version == 2
    assert report.applied_versions == (1, 2)


def test_v1_to_v2_backs_up_once_and_preserves_existing_rows(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"
    _create_v1_database(database)
    connection = sqlite3.connect(database)
    connection.execute(
        "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "evt-existing",
            "source.revision_registered",
            "source_revision",
            "rev-existing",
            "a" * 64,
            "{}",
            "v1",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00Z",
        ),
    )
    connection.commit()
    connection.close()
    calls: list[tuple[int, int]] = []

    def backup(source: Path, from_version: int, to_version: int) -> Path:
        target = tmp_path / "automation.v1.backup.db"
        shutil.copy2(source, target)
        calls.append((from_version, to_version))
        return target

    report = migrations.migrate_database(database, backup_hook=backup)

    assert calls == [(1, 2)]
    assert report.applied_versions == (2,)
    assert report.backup_path == str(tmp_path / "automation.v1.backup.db")
    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute(
            "SELECT event_id FROM events WHERE event_id='evt-existing'"
        ).fetchone() == ("evt-existing",)
        assert connection.execute(
            "SELECT COUNT(*) FROM attempts WHERE runtime_generation != 0"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_v1_to_v2_backup_failure_leaves_v1_untouched(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"
    _create_v1_database(database)

    def backup_failure(_source: Path, _from: int, _to: int) -> Path:
        raise OSError("injected backup failure")

    with pytest.raises(migrations.BackupError):
        migrations.migrate_database(database, backup_hook=backup_failure)

    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert "runtime_gate" not in _table_names(connection)
        assert "runtime_generation" not in {
            row[1] for row in connection.execute("PRAGMA table_info(attempts)")
        }
    finally:
        connection.close()


def test_v1_to_v2_requires_an_explicit_backup_hook(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"
    _create_v1_database(database)

    with pytest.raises(migrations.BackupError):
        migrations.migrate_database(database)

    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert "runtime_gate" not in _table_names(connection)
    finally:
        connection.close()


def test_v1_to_v2_ddl_failure_rolls_back_the_entire_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "automation.db"
    _create_v1_database(database)
    original = migrations._execute_statement

    def fail_on_v2(connection: sqlite3.Connection, sql: str):
        if "runtime_generation" in sql:
            raise sqlite3.OperationalError("injected v2 DDL failure")
        return original(connection, sql)

    monkeypatch.setattr(migrations, "_execute_statement", fail_on_v2)
    backup = tmp_path / "automation.v1.backup.db"

    with pytest.raises(migrations.MigrationExecutionError):
        migrations.migrate_database(
            database,
            backup_hook=lambda source, _from, _to: Path(
                shutil.copy2(source, backup)
            ),
        )

    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert "runtime_gate" not in _table_names(connection)
        assert "runtime_generation" not in {
            row[1] for row in connection.execute("PRAGMA table_info(attempts)")
        }
    finally:
        connection.close()


def test_v2_reopen_is_a_read_only_noop_with_stable_fingerprint(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"
    first = migrations.migrate_database(database)

    second = migrations.migrate_database(database)

    assert second.from_version == 2
    assert second.to_version == 2
    assert second.applied_versions == ()
    assert second.backup_path is None
    assert second.schema_fingerprint == first.schema_fingerprint


def test_future_v3_is_rejected_without_downgrade(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA user_version = 3")
    connection.commit()
    connection.close()

    with pytest.raises(migrations.UnsupportedSchemaVersionError):
        migrations.migrate_database(database)

    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
    finally:
        connection.close()


def test_v2_missing_claim_index_is_schema_drift(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"
    migrations.migrate_database(database)
    connection = sqlite3.connect(database)
    connection.execute("DROP INDEX idx_jobs_claim")
    connection.commit()
    connection.close()

    with pytest.raises(migrations.SchemaDriftError):
        migrations.migrate_database(database)


def test_v2_missing_runtime_gate_row_is_schema_drift(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"
    migrations.migrate_database(database)
    connection = sqlite3.connect(database)
    connection.execute("DELETE FROM runtime_gate")
    connection.commit()
    connection.close()

    with pytest.raises(migrations.SchemaDriftError):
        migrations.migrate_database(database)
