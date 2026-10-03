"""The budget migration preserves frozen predecessors and read-only rejection."""

from __future__ import annotations

import shutil
import sqlite3

import pytest

from company_wiki.automation import migrations


def _v2(path):
    with sqlite3.connect(path) as connection:
        for sql in migrations._DDL_V1_STATEMENTS + migrations._DDL_V2_STATEMENTS:
            connection.execute(sql)
        connection.execute("PRAGMA user_version=2")


def test_v3_new_database_has_exact_three_additive_budget_tables(tmp_path):
    database = tmp_path / "auto.db"
    report = migrations.migrate_database(database)
    assert report.to_version == 4 and report.applied_versions == (1, 2, 3, 4)
    assert set(migrations.validate_database(database).tables) == set(
        migrations.EXPECTED_TABLES_V1
    ) | {
        "runtime_gate",
        "narrative_runs",
        "narrative_run_jobs",
        "narrative_model_reservations",
    }


def test_v2_is_validated_readonly_then_upgraded_once_with_exact_backup(tmp_path):
    database = tmp_path / "auto.db"
    _v2(database)
    before = database.read_bytes()
    assert migrations.validate_database(database).user_version == 2
    assert database.read_bytes() == before
    with pytest.raises(migrations.BackupError):
        migrations.migrate_database(database)
    assert database.read_bytes() == before
    calls = []

    def backup(source, old, new):
        calls.append((old, new))
        target = tmp_path / "before.db"
        shutil.copy2(source, target)
        return target

    report = migrations.migrate_database(database, backup_hook=backup)
    assert calls == [(2, 4)] and report.applied_versions == (3, 4)
    assert (tmp_path / "before.db").read_bytes() == before
    assert migrations.migrate_database(database).applied_versions == ()


def test_v3_partial_ddl_failure_rolls_back_to_unchanged_v2(tmp_path, monkeypatch):
    database = tmp_path / "auto.db"
    _v2(database)
    original = migrations._execute_statement

    def fail(connection, sql):
        if "CREATE TABLE narrative_run_jobs" in sql:
            raise sqlite3.OperationalError("injected v3 failure")
        return original(connection, sql)

    monkeypatch.setattr(migrations, "_execute_statement", fail)
    with pytest.raises(migrations.MigrationExecutionError):
        migrations.migrate_database(
            database,
            backup_hook=lambda source, old, new: shutil.copy2(
                source, tmp_path / "before.db"
            ),
        )
    report = migrations.validate_database(database)
    assert report.user_version == 2
    assert "narrative_runs" not in report.tables


def test_drifted_v2_is_rejected_before_backup_and_write_open(tmp_path):
    database = tmp_path / "auto.db"
    _v2(database)
    with sqlite3.connect(database) as connection:
        connection.execute("DROP INDEX idx_jobs_claim")
    before = database.read_bytes()
    calls = []
    with pytest.raises(migrations.SchemaDriftError):
        migrations.migrate_database(
            database, backup_hook=lambda *args: calls.append(args)
        )
    assert calls == [] and database.read_bytes() == before


def test_current_reopen_rechecks_version_in_its_validation_snapshot(
    tmp_path, monkeypatch
):
    database = tmp_path / "auto.db"
    migrations.migrate_database(database)
    classify = migrations._classify_existing
    after_change = []

    def concurrent_version_change(path):
        classification = classify(path)
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA user_version=5")
        after_change.append(path.read_bytes())
        return classification

    monkeypatch.setattr(migrations, "_classify_existing", concurrent_version_change)
    with pytest.raises(migrations.UnsupportedSchemaVersionError):
        migrations.migrate_database(database)
    assert database.read_bytes() == after_change[0]
