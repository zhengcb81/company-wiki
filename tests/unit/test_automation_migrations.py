"""AUTO-2 migration contract tests (M01-M17).

Each test asserts the production module path exists before importing it, so the
red phase fails as a normal assertion rather than a collection/import error.  No
test opens a real ``.state`` database; every database lives under ``tmp_path``.
"""

import sqlite3
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_PATH = ROOT / "src" / "company_wiki" / "automation" / "migrations.py"

EXPECTED_TABLES = frozenset({
    "events", "jobs", "job_dependencies", "attempts",
    "approvals", "effects", "outbox", "notifications",
})


def _migrations():
    """Import the module lazily after proving the source file exists."""
    assert MIGRATIONS_PATH.is_file(), "expected red: automation/migrations.py is not implemented"
    from company_wiki.automation import migrations
    return migrations


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return [row["name"] for row in rows]


def _user_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


# --------------------------------------------------------------------------- #
# M01: new Path initializes all eight business tables at version 1
# --------------------------------------------------------------------------- #
def test_m01_new_path_initializes_eight_tables_at_version_1(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    report = migrations.migrate_database(db)
    assert db.is_file()
    conn = _connect_readonly(db)
    try:
        assert set(_user_tables(conn)) == EXPECTED_TABLES
        assert _user_version(conn) == 1
    finally:
        conn.close()
    assert report.to_version == 1
    assert report.applied_versions == (1,)


# --------------------------------------------------------------------------- #
# M02: full-table structure matches AUTO-D (columns/types/null/default/PK/unique/FK)
# --------------------------------------------------------------------------- #
def test_m02_full_structure_matches_frozen_ddl(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    migrations.migrate_database(db)

    expected = {
        "events": {
            "columns": [
                ("event_id", "TEXT", 0, None, 1),
                ("event_type", "TEXT", 1, None, 0),
                ("subject_type", "TEXT", 1, None, 0),
                ("subject_id", "TEXT", 1, None, 0),
                ("input_hash", "TEXT", 1, None, 0),
                ("payload_json", "TEXT", 1, None, 0),
                ("policy_version", "TEXT", 1, None, 0),
                ("occurred_at", "TEXT", 1, None, 0),
                ("observed_at", "TEXT", 1, None, 0),
            ],
            "pk": [("event_id",)],
        },
        "jobs": {
            "columns": [
                ("job_id", "TEXT", 0, None, 1),
                ("job_key", "TEXT", 1, None, 0),
                ("job_type", "TEXT", 1, None, 0),
                ("subject_type", "TEXT", 1, None, 0),
                ("subject_id", "TEXT", 1, None, 0),
                ("input_hash", "TEXT", 1, None, 0),
                ("policy_version", "TEXT", 1, None, 0),
                ("handler_version", "TEXT", 1, None, 0),
                ("risk_class", "TEXT", 1, None, 0),
                ("status", "TEXT", 1, None, 0),
                ("priority", "INTEGER", 1, "0", 0),
                ("not_before", "TEXT", 1, None, 0),
                ("max_attempts", "INTEGER", 1, None, 0),
                ("created_from_event_id", "TEXT", 1, None, 0),
                ("created_at", "TEXT", 1, None, 0),
                ("updated_at", "TEXT", 1, None, 0),
                ("last_error_code", "TEXT", 0, None, 0),
                ("last_error_detail", "TEXT", 0, None, 0),
            ],
            "pk": [("job_id",)],
        },
        "attempts": {
            "columns": [
                ("attempt_id", "TEXT", 0, None, 1),
                ("job_id", "TEXT", 1, None, 0),
                ("attempt_no", "INTEGER", 1, None, 0),
                ("worker_id", "TEXT", 1, None, 0),
                ("lease_token", "TEXT", 1, None, 0),
                ("lease_until", "TEXT", 1, None, 0),
                ("started_at", "TEXT", 1, None, 0),
                ("heartbeat_at", "TEXT", 1, None, 0),
                ("finished_at", "TEXT", 0, None, 0),
                ("outcome", "TEXT", 0, None, 0),
                ("result_json", "TEXT", 0, None, 0),
                ("error_code", "TEXT", 0, None, 0),
                ("error_detail", "TEXT", 0, None, 0),
            ],
            "pk": [("attempt_id",)],
        },
        "approvals": {
            "columns": [
                ("approval_id", "TEXT", 0, None, 1),
                ("job_id", "TEXT", 1, None, 0),
                ("action_hash", "TEXT", 1, None, 0),
                ("reviewer_principal", "TEXT", 1, None, 0),
                ("reviewer_session_id", "TEXT", 1, None, 0),
                ("role", "TEXT", 1, None, 0),
                ("decision", "TEXT", 1, None, 0),
                ("decided_at", "TEXT", 1, None, 0),
                ("receipt_hash", "TEXT", 1, None, 0),
            ],
            "pk": [("approval_id",)],
        },
        "effects": {
            "columns": [
                ("effect_id", "TEXT", 0, None, 1),
                ("effect_key", "TEXT", 1, None, 0),
                ("job_id", "TEXT", 1, None, 0),
                ("effect_type", "TEXT", 1, None, 0),
                ("target", "TEXT", 1, None, 0),
                ("before_hash", "TEXT", 0, None, 0),
                ("intended_after_hash", "TEXT", 0, None, 0),
                ("actual_after_hash", "TEXT", 0, None, 0),
                ("status", "TEXT", 1, None, 0),
                ("created_at", "TEXT", 1, None, 0),
                ("verified_at", "TEXT", 0, None, 0),
            ],
            "pk": [("effect_id",)],
        },
        "outbox": {
            "columns": [
                ("outbox_id", "TEXT", 0, None, 1),
                ("effect_id", "TEXT", 1, None, 0),
                ("payload_json", "TEXT", 1, None, 0),
                ("status", "TEXT", 1, None, 0),
                ("attempt_count", "INTEGER", 1, "0", 0),
                ("not_before", "TEXT", 1, None, 0),
                ("lease_token", "TEXT", 0, None, 0),
                ("lease_until", "TEXT", 0, None, 0),
                ("last_error", "TEXT", 0, None, 0),
            ],
            "pk": [("outbox_id",)],
        },
        "notifications": {
            "columns": [
                ("notification_id", "TEXT", 0, None, 1),
                ("notification_key", "TEXT", 1, None, 0),
                ("job_id", "TEXT", 0, None, 0),
                ("channel", "TEXT", 1, None, 0),
                ("severity", "TEXT", 1, None, 0),
                ("payload_json", "TEXT", 1, None, 0),
                ("status", "TEXT", 1, None, 0),
                ("created_at", "TEXT", 1, None, 0),
                ("delivered_at", "TEXT", 0, None, 0),
            ],
            "pk": [("notification_id",)],
        },
        "job_dependencies": {
            "columns": [
                ("job_id", "TEXT", 1, None, 1),
                ("depends_on_job_id", "TEXT", 1, None, 2),
                ("required_status", "TEXT", 1, "'succeeded'", 0),
            ],
            "pk": [("job_id",), ("depends_on_job_id",)],
        },
    }

    conn = _connect_readonly(db)
    try:
        for table, spec in expected.items():
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            actual_cols = [
                (r["name"], r["type"], r["notnull"], r["dflt_value"], r["pk"])
                for r in rows
            ]
            assert actual_cols == spec["columns"], f"column drift in {table}"
            # composite / single primary key columns in pk order
            pk_cols = [r["name"] for r in sorted(rows, key=lambda r: r["pk"]) if r["pk"] > 0]
            assert pk_cols == [c[0] for c in spec["pk"]], f"pk drift in {table}"
    finally:
        conn.close()


def test_m02_unique_constraints_present(tmp_path):
    """AUTO-D UNIQUE constraints must materialize as unique indexes."""
    migrations = _migrations()
    db = tmp_path / "automation.db"
    migrations.migrate_database(db)
    expected_unique = {
        "events": {"(event_type,subject_type,subject_id,input_hash,policy_version)"},
        "jobs": {"(job_key)"},
        "attempts": {"(lease_token)", "(job_id,attempt_no)"},
        "approvals": {"(job_id,role,reviewer_principal,receipt_hash)"},
        "effects": {"(effect_key)"},
        "outbox": {"(effect_id)"},
        "notifications": {"(notification_key)"},
    }
    conn = _connect_readonly(db)
    try:
        for table, expected in expected_unique.items():
            indexes = conn.execute(f"PRAGMA index_list({table})").fetchall()
            unique_cols = set()
            for idx in indexes:
                if idx["origin"] == "u":  # created by UNIQUE constraint
                    info = conn.execute(f"PRAGMA index_info({idx['name']})").fetchall()
                    cols = "(" + ",".join(row["name"] for row in info) + ")"
                    unique_cols.add(cols)
            assert unique_cols == expected, f"unique index drift in {table}: {unique_cols}"
    finally:
        conn.close()


def test_m02_foreign_keys_target_frozen_tables(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    migrations.migrate_database(db)
    expected_fk = {
        "jobs": {("created_from_event_id", "events", "event_id")},
        "job_dependencies": {
            ("job_id", "jobs", "job_id"),
            ("depends_on_job_id", "jobs", "job_id"),
        },
        "attempts": {("job_id", "jobs", "job_id")},
        "approvals": {("job_id", "jobs", "job_id")},
        "effects": {("job_id", "jobs", "job_id")},
        "outbox": {("effect_id", "effects", "effect_id")},
        "notifications": {("job_id", "jobs", "job_id")},
    }
    conn = _connect_readonly(db)
    try:
        for table, expected in expected_fk.items():
            rows = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
            actual = {(row["from"], row["table"], row["to"]) for row in rows}
            assert actual == expected, f"fk drift in {table}: {actual}"
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# M03: connection PRAGMAs (foreign_keys/journal_mode/busy_timeout/synchronous)
# --------------------------------------------------------------------------- #
def test_m03_journal_mode_persists_and_pragmas_are_issued(tmp_path):
    """journal_mode is persisted in the DB header and survives close; the
    per-connection PRAGMAs (foreign_keys/busy_timeout/synchronous) are not
    persisted, so they are verified by proving the production source issues
    them and by exercising FK enforcement through the store tests."""
    migrations = _migrations()
    db = tmp_path / "automation.db"
    migrations.migrate_database(db)
    conn = _connect_readonly(db)
    try:
        # journal_mode is the one PRAGMA persisted in the database header.
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        conn.close()
    source = MIGRATIONS_PATH.read_text(encoding="utf-8")
    for required in (
        "PRAGMA foreign_keys = ON",
        "PRAGMA busy_timeout = 5000",
        "PRAGMA synchronous = FULL",
        "PRAGMA journal_mode = WAL",
    ):
        assert required in source, f"production connection must issue: {required}"


# --------------------------------------------------------------------------- #
# M04: repeated open of a v1 database is a no-op with a stable fingerprint
# --------------------------------------------------------------------------- #
def test_m04_repeated_v1_open_is_noop_with_stable_fingerprint(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    first = migrations.migrate_database(db)
    fingerprint = first.schema_fingerprint
    assert fingerprint
    for _ in range(9):
        report = migrations.migrate_database(db)
        assert report.applied_versions == ()
        assert report.from_version == 1
        assert report.to_version == 1
        assert report.schema_fingerprint == fingerprint
        assert report.backup_path is None


# --------------------------------------------------------------------------- #
# M05: pre-existing empty v0 file migrates; optional backup hook fires once
# --------------------------------------------------------------------------- #
def test_m05_preexisting_empty_v0_file_migrates_with_one_backup(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    db.write_bytes(b"")
    calls: list[tuple] = []

    def backup_hook(source: Path, from_version: int, to_version: int) -> Path:
        target = tmp_path / "backup.db"
        target.write_bytes(source.read_bytes())
        calls.append((str(source), from_version, to_version))
        return target

    report = migrations.migrate_database(db, backup_hook=backup_hook)
    assert report.from_version == 0
    assert report.to_version == 1
    assert report.applied_versions == (1,)
    assert len(calls) == 1
    assert calls[0][1] == 0 and calls[0][2] == 1
    conn = _connect_readonly(db)
    try:
        assert _user_version(conn) == 1
        assert set(_user_tables(conn)) == EXPECTED_TABLES
    finally:
        conn.close()


def test_m05_new_file_does_not_call_backup_hook(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    calls: list[tuple] = []

    def backup_hook(source: Path, from_version: int, to_version: int) -> Path:
        calls.append((str(source), from_version, to_version))
        return tmp_path / "unused.db"

    migrations.migrate_database(db, backup_hook=backup_hook)
    assert calls == []


# --------------------------------------------------------------------------- #
# M06: v0 with unknown user table -> UnknownSchemaError, zero changes
# --------------------------------------------------------------------------- #
def test_m06_v0_with_unknown_user_table_is_unknown_schema(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    # Build a v0 database that already has an unrecognized user table.
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE legacy_jobs (id TEXT)")
    conn.execute("PRAGMA user_version = 0")
    conn.commit()
    conn.close()
    before = db.read_bytes()
    with pytest.raises(migrations.UnknownSchemaError):
        migrations.migrate_database(db)
    assert db.read_bytes() == before  # zero changes


# --------------------------------------------------------------------------- #
# M07: user_version > 1 -> UnsupportedSchemaVersionError, no downgrade
# --------------------------------------------------------------------------- #
def test_m07_higher_user_version_is_unsupported(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA user_version = 2")
    conn.commit()
    conn.close()
    before = db.read_bytes()
    with pytest.raises(migrations.UnsupportedSchemaVersionError):
        migrations.migrate_database(db)
    # user_version must remain 2 (no downgrade/clear)
    conn = _connect_readonly(db)
    try:
        assert _user_version(conn) == 2
    finally:
        conn.close()
    assert db.read_bytes() == before


# --------------------------------------------------------------------------- #
# M08: v1 with missing/extra table -> SchemaDriftError
# --------------------------------------------------------------------------- #
def test_m08_v1_missing_table_is_schema_drift(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    migrations.migrate_database(db)
    conn = sqlite3.connect(db)
    conn.execute("DROP TABLE notifications")
    conn.commit()
    conn.close()
    with pytest.raises(migrations.SchemaDriftError):
        migrations.migrate_database(db)


def test_m08_v1_extra_table_is_schema_drift(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    migrations.migrate_database(db)
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE extra_table (id TEXT)")
    conn.execute("PRAGMA user_version = 1")
    conn.commit()
    conn.close()
    with pytest.raises(migrations.SchemaDriftError):
        migrations.migrate_database(db)


# --------------------------------------------------------------------------- #
# M09: v1 column/PK/default altered -> SchemaDriftError
# --------------------------------------------------------------------------- #
def test_m09_v1_column_default_altered_is_schema_drift(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    migrations.migrate_database(db)
    conn = sqlite3.connect(db)
    conn.execute("DROP TABLE outbox")
    conn.execute(
        "CREATE TABLE outbox (outbox_id TEXT PRIMARY KEY, effect_id TEXT NOT NULL, "
        "payload_json TEXT NOT NULL, status TEXT NOT NULL, attempt_count INTEGER NOT NULL DEFAULT 99, "
        "not_before TEXT NOT NULL, lease_token TEXT, lease_until TEXT, last_error TEXT)"
    )
    conn.execute("PRAGMA user_version = 1")
    conn.commit()
    conn.close()
    with pytest.raises(migrations.SchemaDriftError):
        migrations.migrate_database(db)


# --------------------------------------------------------------------------- #
# M10: v1 unique index removed/altered -> SchemaDriftError
# --------------------------------------------------------------------------- #
def test_m10_v1_unique_constraint_removed_is_schema_drift(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    migrations.migrate_database(db)
    conn = sqlite3.connect(db)
    conn.execute("DROP TABLE effects")
    # Recreate effects without the UNIQUE(effect_key) constraint.
    conn.execute(
        "CREATE TABLE effects (effect_id TEXT PRIMARY KEY, effect_key TEXT, job_id TEXT NOT NULL, "
        "effect_type TEXT NOT NULL, target TEXT NOT NULL, before_hash TEXT, "
        "intended_after_hash TEXT, actual_after_hash TEXT, status TEXT NOT NULL, "
        "created_at TEXT NOT NULL, verified_at TEXT)"
    )
    conn.execute("PRAGMA user_version = 1")
    conn.commit()
    conn.close()
    with pytest.raises(migrations.SchemaDriftError):
        migrations.migrate_database(db)


# --------------------------------------------------------------------------- #
# M11: v1 FK removed/altered -> SchemaDriftError
# --------------------------------------------------------------------------- #
def test_m11_v1_foreign_key_removed_is_schema_drift(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    migrations.migrate_database(db)
    conn = sqlite3.connect(db)
    conn.execute("DROP TABLE attempts")
    conn.execute(
        "CREATE TABLE attempts (attempt_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, "
        "attempt_no INTEGER NOT NULL, worker_id TEXT NOT NULL, lease_token TEXT NOT NULL UNIQUE, "
        "lease_until TEXT NOT NULL, started_at TEXT NOT NULL, heartbeat_at TEXT NOT NULL, "
        "finished_at TEXT, outcome TEXT, result_json TEXT, error_code TEXT, error_detail TEXT, "
        "UNIQUE(job_id, attempt_no))"
    )
    conn.execute("PRAGMA user_version = 1")
    conn.commit()
    conn.close()
    with pytest.raises(migrations.SchemaDriftError):
        migrations.migrate_database(db)


# --------------------------------------------------------------------------- #
# M12: DDL mid-failure injection -> rollback, version 0, no partial tables
# --------------------------------------------------------------------------- #
def test_m12_ddl_mid_failure_rolls_back(tmp_path, monkeypatch):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    original = migrations._execute_statement
    call = {"n": 0}

    def failing(connection, sql):
        call["n"] += 1
        # Fail partway through the DDL statements (after a couple succeed).
        if call["n"] == 3:
            raise sqlite3.OperationalError("injected failure")
        return original(connection, sql)

    monkeypatch.setattr(migrations, "_execute_statement", failing)
    with pytest.raises(migrations.MigrationExecutionError):
        migrations.migrate_database(db)
    conn = _connect_readonly(db)
    try:
        assert _user_version(conn) == 0
        assert _user_tables(conn) == []  # no partial business tables
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# M13: backup hook raises / invalid receipt -> BackupError, no DDL run
# --------------------------------------------------------------------------- #
def test_m13_backup_hook_raising_is_backup_error(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    db.write_bytes(b"")

    def bad_hook(source: Path, from_version: int, to_version: int) -> Path:
        raise OSError("disk full")

    before = db.read_bytes()
    with pytest.raises(migrations.BackupError):
        migrations.migrate_database(db, backup_hook=bad_hook)
    # DDL must not have started: still v0 with no tables.
    conn = _connect_readonly(db)
    try:
        assert _user_version(conn) == 0
        assert _user_tables(conn) == []
    finally:
        conn.close()
    assert db.read_bytes() == before


def test_m13_backup_hook_invalid_receipt_is_backup_error(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    db.write_bytes(b"")

    def invalid_hook(source: Path, from_version: int, to_version: int) -> Path:
        # Return the source path itself (not an independent backup).
        return source

    with pytest.raises(migrations.BackupError):
        migrations.migrate_database(db, backup_hook=invalid_hook)

    def missing_hook(source: Path, from_version: int, to_version: int) -> Path:
        return tmp_path / "does-not-exist.db"

    db2 = tmp_path / "automation2.db"
    db2.write_bytes(b"")
    with pytest.raises(migrations.BackupError):
        migrations.migrate_database(db2, backup_hook=missing_hook)


# --------------------------------------------------------------------------- #
# M14: two instances concurrently initializing the same new DB -> one v1 schema
# --------------------------------------------------------------------------- #
def test_m14_concurrent_init_produces_one_v1_schema(tmp_path):
    threading = pytest.importorskip("threading")
    migrations = _migrations()
    db = tmp_path / "automation.db"
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def init():
        try:
            barrier.wait()
            migrations.migrate_database(db)
        except BaseException as exc:  # pragma: no cover - recorded for diagnosis
            errors.append(exc)

    threads = [threading.Thread(target=init) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    conn = _connect_readonly(db)
    try:
        assert _user_version(conn) == 1
        assert set(_user_tables(conn)) == EXPECTED_TABLES
        report = migrations.validate_database(db)
        assert report.integrity_ok
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# M15: non-SQLite / truncated file -> typed error, original file untouched
# --------------------------------------------------------------------------- #
def test_m15_non_sqlite_file_is_rejected_and_not_overwritten(tmp_path):
    migrations = _migrations()
    db = tmp_path / "automation.db"
    payload = b"this is definitely not a sqlite database"
    db.write_bytes(payload)
    with pytest.raises(migrations.AutomationMigrationError):
        migrations.validate_database(db)
    with pytest.raises(migrations.AutomationMigrationError):
        migrations.migrate_database(db)
    assert db.read_bytes() == payload  # not overwritten


# --------------------------------------------------------------------------- #
# M16: static anti-pattern scan (no IF NOT EXISTS / executescript / default .state)
# --------------------------------------------------------------------------- #
def test_m16_no_static_anti_patterns():
    assert MIGRATIONS_PATH.is_file()
    source = MIGRATIONS_PATH.read_text(encoding="utf-8")
    forbidden = [
        "CREATE TABLE IF NOT EXISTS",
        "executescript",
        "INSERT OR REPLACE",
        "ON CONFLICT",
        ".state/automation.db",
        ".state",
    ]
    for token in forbidden:
        assert token not in source, f"forbidden anti-pattern in migrations.py: {token!r}"


# --------------------------------------------------------------------------- #
# M17: validate missing path -> typed error, no DB/parent created
# --------------------------------------------------------------------------- #
def test_m17_validate_missing_path_does_not_create(tmp_path):
    migrations = _migrations()
    missing = tmp_path / "nested" / "absent.db"
    assert not missing.exists()
    with pytest.raises(migrations.InvalidDatabasePathError):
        migrations.validate_database(missing)
    # Neither the database nor the parent directory may be created.
    assert not missing.exists()
    assert not missing.parent.exists()
