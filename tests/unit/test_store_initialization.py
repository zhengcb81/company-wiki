"""G2-13: ordinary opens are bounded; explicit health checks remain real."""

from __future__ import annotations

import sqlite3

import pytest

from company_wiki.automation import migrations
from company_wiki.automation.narrative_run_store import NarrativeRunError, NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.store import CatalogStore

from .test_narrative_run_store import claim, reserve, setup_run


def _trace(monkeypatch):
    statements = []
    connect = sqlite3.connect

    def traced(database, *args, **kwargs):
        connection = connect(database, *args, **kwargs)
        if str(database) != ":memory:":
            connection.set_trace_callback(
                lambda sql: statements.append(" ".join(sql.lower().split()))
            )
        return connection

    monkeypatch.setattr(sqlite3, "connect", traced)
    return statements


def _deep(statements):
    return [sql for sql in statements if sql in {
        "pragma integrity_check", "pragma foreign_key_check"
    }]


def _snapshot(db):
    with sqlite3.connect(db) as connection:
        return tuple(connection.iterdump())


def _catalog_document(db):
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO sources VALUES('src', ?, 12, 'text/plain', '2026-10-07')",
            ("a" * 64,),
        )
        connection.execute(
            "INSERT INTO documents(document_id,primary_source_id,title,source_type,"
            "document_kind,source_status,metadata_priority,metadata_json,first_seen_at,last_seen_at) "
            "VALUES('doc','src','fixture','news','news','active',0,'{}','2026-10-07','2026-10-07')"
        )


def test_repeated_auto_and_run_opens_and_budget_reads_have_no_deep_scan(tmp_path, monkeypatch):
    _, auto, _, _, _, _ = setup_run(tmp_path)
    before = _snapshot(auto.db_path)
    statements = _trace(monkeypatch)
    for _ in range(3):
        AutomationStore(auto.db_path)
        budget = NarrativeRunStore(auto.db_path)
        assert budget.budget_snapshot("run-one").charged_tokens == 0
    assert _deep(statements) == []
    assert not any(sql.startswith(("create ", "alter ", "insert ", "update ")) for sql in statements)
    assert _snapshot(auto.db_path) == before


def test_schema_inspection_does_not_claim_data_integrity(tmp_path, monkeypatch):
    db = tmp_path / "auto.db"
    AutomationStore(db)
    assert hasattr(migrations, "inspect_schema"), "lightweight schema API is missing"
    statements = _trace(monkeypatch)
    report = migrations.inspect_schema(db)
    assert report.user_version == migrations.SCHEMA_VERSION
    assert len(report.schema_fingerprint) == 64
    assert not hasattr(report, "integrity_ok")
    assert not hasattr(report, "foreign_key_violations")
    assert _deep(statements) == []


def test_explicit_schema_report_runs_exactly_one_pair_of_deep_checks(tmp_path, monkeypatch):
    auto = AutomationStore(tmp_path / "auto.db")
    statements = _trace(monkeypatch)
    report = auto.schema_report()
    assert report.integrity_ok and not report.foreign_key_violations
    assert _deep(statements) == ["pragma integrity_check", "pragma foreign_key_check"]


def test_new_auto_database_runs_one_deep_check_before_commit(tmp_path, monkeypatch):
    statements = _trace(monkeypatch)
    AutomationStore(tmp_path / "auto.db")
    assert _deep(statements) == ["pragma integrity_check", "pragma foreign_key_check"]
    assert statements.index("pragma foreign_key_check") < statements.index("commit")


def _v4(db, *, orphan=False):
    with sqlite3.connect(db) as connection:
        for group in (migrations._DDL_V1_STATEMENTS, migrations._DDL_V2_STATEMENTS,
                      migrations._DDL_V3_STATEMENTS, migrations._DDL_V4_STATEMENTS):
            for statement in group:
                connection.execute(statement)
        connection.execute("PRAGMA user_version=4")
        if orphan:
            connection.execute("INSERT INTO job_dependencies VALUES('missing','missing','succeeded')")


def test_actual_auto_upgrade_runs_one_deep_check_before_commit(tmp_path, monkeypatch):
    db = tmp_path / "auto.db"
    _v4(db)
    statements = _trace(monkeypatch)
    report = migrations.migrate_database(db)
    assert report.applied_versions == (5,)
    assert _deep(statements) == ["pragma integrity_check", "pragma foreign_key_check"]
    assert statements.index("pragma foreign_key_check") < statements.index("commit")


def test_orphan_is_diagnosed_by_explicit_check_and_failed_upgrade_rolls_back(tmp_path):
    db = tmp_path / "auto.db"
    _v4(db, orphan=True)
    before = _snapshot(db)
    with pytest.raises(migrations.SchemaDriftError, match="foreign_key_check"):
        migrations.migrate_database(db)
    assert _snapshot(db) == before
    with pytest.raises(migrations.SchemaDriftError, match="foreign_key_check"):
        migrations.validate_database(db)


@pytest.mark.parametrize("damage", ["index", "singleton", "future", "not_sqlite"])
def test_light_opens_still_reject_real_schema_and_file_errors(tmp_path, damage):
    db = tmp_path / "auto.db"
    AutomationStore(db)
    if damage == "not_sqlite":
        db.write_bytes(b"this is not a SQLite database")
    else:
        with sqlite3.connect(db) as connection:
            if damage == "index":
                name = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' LIMIT 1"
                ).fetchone()[0]
                connection.execute(f'DROP INDEX "{name}"')
            elif damage == "singleton":
                connection.execute("DELETE FROM runtime_gate")
            else:
                connection.execute("PRAGMA user_version=99")
    before = db.read_bytes()
    for cls in (AutomationStore, NarrativeRunStore):
        with pytest.raises(migrations.AutomationMigrationError):
            cls(db)
    assert db.read_bytes() == before


def test_current_catalog_opens_do_not_ddl_seed_or_write(tmp_path, monkeypatch):
    db = tmp_path / "catalog.db"
    CatalogStore(db)
    _catalog_document(db)
    before = _snapshot(db)
    statements = _trace(monkeypatch)
    for _ in range(3):
        CatalogStore(db)
    assert not any(sql.startswith(("create ", "alter ", "insert ", "update ")) for sql in statements)
    assert not any("journal_mode=" in sql for sql in statements)
    assert _snapshot(db) == before


def test_document_without_fingerprint_state_remains_dispatchable_and_upserts(tmp_path):
    db = tmp_path / "catalog.db"
    store = CatalogStore(db)
    _catalog_document(db)
    selected = store.select_fingerprint_batch(limit=1, now_iso="2026-10-07T00:00:00Z")
    assert [row["document_id"] for row in selected] == ["doc"]
    assert selected[0]["attempt_count"] == 0
    store.record_fingerprint_outcome(
        document_id="doc", source_id="src", source_sha256="a" * 64,
        fingerprint="fingerprint", status="completed", attempt_count=1,
    )
    assert store.select_fingerprint_batch(limit=1, now_iso="2026-10-07T00:00:00Z") == []
    assert store.fingerprint_state_counts() == {"completed": 1}


def test_unknown_catalog_version_is_rejected_before_any_ddl(tmp_path, monkeypatch):
    db = tmp_path / "catalog.db"
    CatalogStore(db)
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE catalog_meta SET value='99' WHERE key='schema_version'")
        connection.execute("DROP TABLE document_restore_audit")
    before = _snapshot(db)
    statements = _trace(monkeypatch)
    with pytest.raises(ValueError, match="unsupported source catalog schema version"):
        CatalogStore(db)
    assert not any(sql.startswith(("create ", "alter ", "insert ", "update ")) for sql in statements)
    assert _snapshot(db) == before


@pytest.mark.parametrize("sql", [
    "DROP TABLE document_restore_audit",
    "ALTER TABLE documents DROP COLUMN text_fingerprint",
    "DROP INDEX idx_fingerprint_state_dispatch",
])
def test_current_catalog_drift_fails_without_silently_repairing(tmp_path, sql):
    db = tmp_path / "catalog.db"
    CatalogStore(db)
    with sqlite3.connect(db) as connection:
        connection.execute(sql)
    before = _snapshot(db)
    with pytest.raises(ValueError, match="schema structure"):
        CatalogStore(db)
    assert _snapshot(db) == before


def test_catalog_upgrade_is_atomic_when_additive_step_fails(tmp_path, monkeypatch):
    db = tmp_path / "catalog.db"
    CatalogStore(db)
    _catalog_document(db)
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE catalog_meta SET value='1.1.0' WHERE key='schema_version'")
        connection.execute("DROP TABLE document_restore_audit")
    before = _snapshot(db)
    original = CatalogStore._apply_additive_migrations

    def fail_after_additions(connection):
        original(connection)
        raise RuntimeError("injected migration failure")

    monkeypatch.setattr(CatalogStore, "_apply_additive_migrations", staticmethod(fail_after_additions))
    with pytest.raises(RuntimeError, match="injected migration failure"):
        CatalogStore(db)
    assert _snapshot(db) == before


@pytest.mark.parametrize("upgrade", [False, True])
def test_catalog_create_or_real_upgrade_deep_checks_once_before_commit(tmp_path, monkeypatch, upgrade):
    db = tmp_path / "catalog.db"
    if upgrade:
        CatalogStore(db)
        _catalog_document(db)
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE catalog_meta SET value='1.1.0' WHERE key='schema_version'")
    statements = _trace(monkeypatch)
    store = CatalogStore(db)
    assert _deep(statements) == ["pragma integrity_check", "pragma foreign_key_check"]
    assert statements.index("pragma foreign_key_check") < statements.index("commit")
    if upgrade:
        assert store.fingerprint_state_counts() == {"pending": 1}


def test_catalog_orphan_prevents_upgrade_and_preserves_original_schema_and_data(tmp_path):
    db = tmp_path / "catalog.db"
    CatalogStore(db)
    _catalog_document(db)
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE catalog_meta SET value='1.1.0' WHERE key='schema_version'")
        connection.execute("UPDATE documents SET primary_source_id='missing'")
    before = _snapshot(db)
    with pytest.raises(ValueError, match="foreign_key_check"):
        CatalogStore(db)
    assert _snapshot(db) == before


@pytest.mark.parametrize("field", ["input_tokens_bound", "reserved_micro_usd", "output_bytes_bound"])
def test_selected_corrupt_ledger_is_never_coerced_into_a_lower_charge(tmp_path, field):
    _, auto, budget, generation, a, _ = setup_run(tmp_path)
    reservation = reserve(budget, claim(auto, generation, a)).record
    assert budget.budget_snapshot("run-one").charged_tokens == reservation.reserved_tokens
    with sqlite3.connect(auto.db_path) as connection:
        connection.execute("PRAGMA ignore_check_constraints=ON")
        connection.execute(
            f"UPDATE narrative_model_reservations SET {field}='broken' WHERE run_id='run-one'"
        )
    # Lightweight opening is not a data-health assertion. The selected ledger
    # is validated in its own responsibility layer before any arithmetic.
    budget = NarrativeRunStore(auto.db_path)
    with pytest.raises(NarrativeRunError, match="stored reservation"):
        budget.budget_snapshot("run-one")
