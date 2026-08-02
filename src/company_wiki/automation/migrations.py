"""AUTO-2 schema v1 migration and read-only validation for AutomationStore.

This module owns the frozen DDL, the version migration algorithm and the
read-only schema report.  It deliberately depends only on the Python standard
library: it does not import the legacy scheduler, generate business IDs, perform
CRUD, read configuration/environment variables, or open a default database path.

Hard rules (enforced by tests M01-M17 and the boundary scan):

* The DDL statements are frozen; a missing table, extra table, altered column,
  altered unique constraint or altered foreign key is a drift error, never
  silently repaired.
* Every connection applies the same PRAGMAs; write transactions are explicit and
  roll back on any failure.
* A pre-existing file that is not SQLite, or a schema that has drifted, fails
  closed.  Read-only classification and validation never modify the file, so a
  rejected migration leaves the database byte-for-byte untouched.
"""

from __future__ import annotations

import functools
import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = 1

EXPECTED_TABLES = frozenset({
    "events", "jobs", "job_dependencies", "attempts",
    "approvals", "effects", "outbox", "notifications",
})

BackupHook = Callable[[Path, int, int], Path]

SQLITE_HEADER = b"SQLite format 3\x00"
_CONNECT_TIMEOUT_S = 5.0


# --------------------------------------------------------------------------- #
# Frozen schema v1 DDL (single source of truth; matches AUTO-D exactly).
# --------------------------------------------------------------------------- #
_DDL_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE events (
      event_id TEXT PRIMARY KEY,
      event_type TEXT NOT NULL,
      subject_type TEXT NOT NULL,
      subject_id TEXT NOT NULL,
      input_hash TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      policy_version TEXT NOT NULL,
      occurred_at TEXT NOT NULL,
      observed_at TEXT NOT NULL,
      UNIQUE(event_type, subject_type, subject_id, input_hash, policy_version)
    )
    """,
    """
    CREATE TABLE jobs (
      job_id TEXT PRIMARY KEY,
      job_key TEXT NOT NULL UNIQUE,
      job_type TEXT NOT NULL,
      subject_type TEXT NOT NULL,
      subject_id TEXT NOT NULL,
      input_hash TEXT NOT NULL,
      policy_version TEXT NOT NULL,
      handler_version TEXT NOT NULL,
      risk_class TEXT NOT NULL,
      status TEXT NOT NULL,
      priority INTEGER NOT NULL DEFAULT 0,
      not_before TEXT NOT NULL,
      max_attempts INTEGER NOT NULL,
      created_from_event_id TEXT NOT NULL REFERENCES events(event_id),
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      last_error_code TEXT,
      last_error_detail TEXT
    )
    """,
    """
    CREATE TABLE job_dependencies (
      job_id TEXT NOT NULL REFERENCES jobs(job_id),
      depends_on_job_id TEXT NOT NULL REFERENCES jobs(job_id),
      required_status TEXT NOT NULL DEFAULT 'succeeded',
      PRIMARY KEY(job_id, depends_on_job_id)
    )
    """,
    """
    CREATE TABLE attempts (
      attempt_id TEXT PRIMARY KEY,
      job_id TEXT NOT NULL REFERENCES jobs(job_id),
      attempt_no INTEGER NOT NULL,
      worker_id TEXT NOT NULL,
      lease_token TEXT NOT NULL UNIQUE,
      lease_until TEXT NOT NULL,
      started_at TEXT NOT NULL,
      heartbeat_at TEXT NOT NULL,
      finished_at TEXT,
      outcome TEXT,
      result_json TEXT,
      error_code TEXT,
      error_detail TEXT,
      UNIQUE(job_id, attempt_no)
    )
    """,
    """
    CREATE TABLE approvals (
      approval_id TEXT PRIMARY KEY,
      job_id TEXT NOT NULL REFERENCES jobs(job_id),
      action_hash TEXT NOT NULL,
      reviewer_principal TEXT NOT NULL,
      reviewer_session_id TEXT NOT NULL,
      role TEXT NOT NULL,
      decision TEXT NOT NULL,
      decided_at TEXT NOT NULL,
      receipt_hash TEXT NOT NULL,
      UNIQUE(job_id, role, reviewer_principal, receipt_hash)
    )
    """,
    """
    CREATE TABLE effects (
      effect_id TEXT PRIMARY KEY,
      effect_key TEXT NOT NULL UNIQUE,
      job_id TEXT NOT NULL REFERENCES jobs(job_id),
      effect_type TEXT NOT NULL,
      target TEXT NOT NULL,
      before_hash TEXT,
      intended_after_hash TEXT,
      actual_after_hash TEXT,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      verified_at TEXT
    )
    """,
    """
    CREATE TABLE outbox (
      outbox_id TEXT PRIMARY KEY,
      effect_id TEXT NOT NULL UNIQUE REFERENCES effects(effect_id),
      payload_json TEXT NOT NULL,
      status TEXT NOT NULL,
      attempt_count INTEGER NOT NULL DEFAULT 0,
      not_before TEXT NOT NULL,
      lease_token TEXT,
      lease_until TEXT,
      last_error TEXT
    )
    """,
    """
    CREATE TABLE notifications (
      notification_id TEXT PRIMARY KEY,
      notification_key TEXT NOT NULL UNIQUE,
      job_id TEXT REFERENCES jobs(job_id),
      channel TEXT NOT NULL,
      severity TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      delivered_at TEXT
    )
    """,
)


# --------------------------------------------------------------------------- #
# Migration errors (stable code strings; original exceptions chained).
# --------------------------------------------------------------------------- #
class AutomationMigrationError(Exception):
    """Base class for all migration/validation failures."""

    code = "automation_migration_error"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.code)
        self.detail = detail


class InvalidDatabasePathError(AutomationMigrationError):
    code = "invalid_database_path"


class InvalidDatabaseFileError(AutomationMigrationError):
    code = "invalid_database_file"


class UnsupportedSchemaVersionError(AutomationMigrationError):
    code = "unsupported_schema_version"


class UnknownSchemaError(AutomationMigrationError):
    code = "unknown_schema"


class SchemaDriftError(AutomationMigrationError):
    code = "schema_drift"


class MigrationExecutionError(AutomationMigrationError):
    code = "migration_execution"


class BackupError(AutomationMigrationError):
    code = "backup_failed"


# --------------------------------------------------------------------------- #
# Frozen report value objects.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class MigrationReport:
    from_version: int
    to_version: int
    applied_versions: tuple[int, ...]
    backup_path: str | None
    schema_fingerprint: str


@dataclass(frozen=True)
class SchemaReport:
    user_version: int
    tables: tuple[str, ...]
    schema_fingerprint: str
    integrity_ok: bool
    foreign_key_violations: tuple[tuple, ...]


# --------------------------------------------------------------------------- #
# Public seam: a single private hook through which every DDL statement flows.
# Production code calls ``connection.execute(sql)`` only via this function.
# --------------------------------------------------------------------------- #
def _execute_statement(connection: sqlite3.Connection, sql: str) -> sqlite3.Cursor:
    return connection.execute(sql)


# --------------------------------------------------------------------------- #
# Path and file guards.
# --------------------------------------------------------------------------- #
def _require_valid_path_object(db_path) -> Path:
    if not isinstance(db_path, Path):
        raise InvalidDatabasePathError("db_path must be a pathlib.Path instance")
    if db_path.name == ":memory:" or str(db_path) == ":memory:":
        raise InvalidDatabasePathError(":memory: databases are not supported")
    if db_path.name == "":
        raise InvalidDatabasePathError("db_path must include a database file name")
    return db_path


def _require_writable_target(db_path: Path) -> None:
    parent = db_path.parent
    if not parent.is_dir():
        raise InvalidDatabasePathError(
            f"parent directory does not exist; refusing to create it: {parent}"
        )


def _ensure_sqlite_file(db_path: Path) -> None:
    """Reject a non-empty file that is not a SQLite database.  Empty files are
    treated as valid uninitialized databases (they migrate at v0 -> v1)."""
    size = db_path.stat().st_size
    if size == 0:
        return
    with db_path.open("rb") as handle:
        header = handle.read(len(SQLITE_HEADER))
    if header != SQLITE_HEADER:
        raise InvalidDatabaseFileError(f"not a SQLite database file: {db_path}")


# --------------------------------------------------------------------------- #
# Connection helpers.
# --------------------------------------------------------------------------- #
def _configure_connection(connection: sqlite3.Connection, *, read_only: bool) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    if not read_only:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")


def _open_connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), timeout=_CONNECT_TIMEOUT_S, isolation_level=None)
    connection.row_factory = sqlite3.Row
    _configure_connection(connection, read_only=False)
    return connection


def _open_readonly_connection(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=_CONNECT_TIMEOUT_S, isolation_level=None)
    connection.row_factory = sqlite3.Row
    _configure_connection(connection, read_only=True)
    return connection


def _user_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def _user_version(connection: sqlite3.Connection) -> int:
    return connection.execute("PRAGMA user_version").fetchone()[0]


# --------------------------------------------------------------------------- #
# Structured schema fingerprint (independent of sqlite_master whitespace).
# --------------------------------------------------------------------------- #
def _read_structure(connection: sqlite3.Connection) -> dict:
    structure: dict[str, dict] = {}
    for table in sorted(EXPECTED_TABLES):
        columns = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
        col_tuples = tuple(
            (row["cid"], row["name"], row["type"], row["notnull"], row["dflt_value"], row["pk"])
            for row in columns
        )
        unique_indexes: list[tuple] = []
        for index in connection.execute(f'PRAGMA index_list("{table}")').fetchall():
            if index["origin"] == "u":
                info = connection.execute(f'PRAGMA index_info("{index["name"]}")').fetchall()
                unique_indexes.append(tuple(row["name"] for row in info))
        foreign_keys = connection.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
        fk_tuples = tuple(
            (row["seq"], row["from"], row["table"], row["to"], row["on_update"], row["on_delete"])
            for row in sorted(foreign_keys, key=lambda r: r["seq"])
        )
        structure[table] = {
            "columns": col_tuples,
            "unique": tuple(sorted(unique_indexes)),
            "foreign_keys": fk_tuples,
        }
    return structure


@functools.lru_cache(maxsize=1)
def _expected_structure() -> dict:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        for statement in _DDL_STATEMENTS:
            connection.execute(statement)
        return _read_structure(connection)
    finally:
        connection.close()


def _require_expected_structure(connection: sqlite3.Connection) -> None:
    tables = set(_user_tables(connection))
    if tables != EXPECTED_TABLES:
        missing = sorted(EXPECTED_TABLES - tables)
        extra = sorted(tables - EXPECTED_TABLES)
        raise SchemaDriftError(f"table set mismatch; missing={missing} extra={extra}")
    actual = _read_structure(connection)
    expected = _expected_structure()
    differences = [table for table in sorted(set(actual) | set(expected))
                   if actual.get(table) != expected.get(table)]
    if differences:
        raise SchemaDriftError(f"schema structure drift in: {differences}")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise SchemaDriftError(f"integrity_check failed: {integrity}")
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise SchemaDriftError(
            f"foreign_key_check violations: {[tuple(row) for row in violations]}"
        )


def _canonical_json(value) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _fingerprint(connection: sqlite3.Connection) -> str:
    return hashlib.sha256(_canonical_json(_read_structure(connection)).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Backup hook.
# --------------------------------------------------------------------------- #
def _perform_backup(
    db_path: Path, pre_existing: bool, backup_hook: BackupHook | None
) -> str | None:
    if backup_hook is None or not pre_existing:
        return None
    try:
        target = backup_hook(db_path, 0, SCHEMA_VERSION)
    except BackupError:
        raise
    except Exception as exc:  # noqa: BLE001 - hook is untrusted caller code
        raise BackupError(f"backup hook raised: {exc}") from exc
    if target is None:
        raise BackupError("backup hook returned no path")
    target_path = Path(target)
    if target_path == db_path:
        raise BackupError("backup path must differ from the source database")
    if not target_path.exists() or not target_path.is_file():
        raise BackupError(f"backup receipt file does not exist: {target_path}")
    return str(target_path)


# --------------------------------------------------------------------------- #
# Read-only classification (never modifies the file).
# --------------------------------------------------------------------------- #
def _classify_existing(db_path: Path) -> str:
    connection = _open_readonly_connection(db_path)
    try:
        version = _user_version(connection)
        if version > SCHEMA_VERSION:
            raise UnsupportedSchemaVersionError(
                f"user_version {version} is newer than supported {SCHEMA_VERSION}"
            )
        tables = _user_tables(connection)
        if version == SCHEMA_VERSION:
            return "v1"
        unknown = [name for name in tables if name not in EXPECTED_TABLES]
        if unknown:
            raise UnknownSchemaError(f"unrecognized tables in uninitialized database: {unknown}")
        return "v0_empty"
    finally:
        connection.close()


def _validate_v1_readonly(db_path: Path) -> MigrationReport:
    connection = _open_readonly_connection(db_path)
    try:
        _require_expected_structure(connection)
        return MigrationReport(SCHEMA_VERSION, SCHEMA_VERSION, (), None, _fingerprint(connection))
    finally:
        connection.close()


def _apply_write_migration(
    connection: sqlite3.Connection, backup_path_str: str | None
) -> MigrationReport:
    version = _user_version(connection)
    if version > SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(
            f"user_version {version} is newer than supported {SCHEMA_VERSION}"
        )
    if version == SCHEMA_VERSION:
        # Another worker migrated between classification and the write lock.
        _require_expected_structure(connection)
        return MigrationReport(SCHEMA_VERSION, SCHEMA_VERSION, (), None, _fingerprint(connection))
    tables = _user_tables(connection)
    unknown = [name for name in tables if name not in EXPECTED_TABLES]
    if unknown:
        raise UnknownSchemaError(f"unrecognized tables in uninitialized database: {unknown}")
    try:
        for statement in _DDL_STATEMENTS:
            _execute_statement(connection, statement)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    except sqlite3.OperationalError as exc:
        raise MigrationExecutionError(f"DDL execution failed and was rolled back: {exc}") from exc
    _require_expected_structure(connection)
    return MigrationReport(
        0, SCHEMA_VERSION, (SCHEMA_VERSION,), backup_path_str, _fingerprint(connection)
    )


def migrate_database(
    db_path: Path, *, backup_hook: BackupHook | None = None
) -> MigrationReport:
    """Create or validate the automation database at schema v1.

    A new file or an empty v0 file is migrated to v1 in a single transaction.
    An existing v1 database is validated read-only and left untouched.  Higher
    versions, unknown schemas and drifted schemas fail closed without modifying
    the file.
    """
    db_path = _require_valid_path_object(db_path)
    _require_writable_target(db_path)
    pre_existing = db_path.exists()
    if pre_existing:
        if not db_path.is_file():
            raise InvalidDatabasePathError(f"target path is not a regular file: {db_path}")
        _ensure_sqlite_file(db_path)
        classification = _classify_existing(db_path)
    else:
        classification = "new"

    if classification == "v1":
        return _validate_v1_readonly(db_path)

    # classification in {"v0_empty", "new"}: back up the pre-existing file
    # before opening any write connection, so a backup failure leaves the file
    # byte-for-byte unchanged.
    backup_path_str = _perform_backup(
        db_path, pre_existing=(classification == "v0_empty"), backup_hook=backup_hook
    )

    connection = _open_connection(db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            report = _apply_write_migration(connection, backup_path_str)
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")
        return report
    finally:
        connection.close()


def validate_database(db_path: Path) -> SchemaReport:
    """Read-only structural report.  Never creates or repairs a database."""
    db_path = _require_valid_path_object(db_path)
    if not db_path.exists() or not db_path.is_file():
        raise InvalidDatabasePathError(f"database file does not exist: {db_path}")
    _ensure_sqlite_file(db_path)

    connection = _open_readonly_connection(db_path)
    try:
        version = _user_version(connection)
        if version > SCHEMA_VERSION:
            raise UnsupportedSchemaVersionError(
                f"user_version {version} is newer than supported {SCHEMA_VERSION}"
            )
        tables = _user_tables(connection)
        if version == SCHEMA_VERSION:
            _require_expected_structure(connection)
        else:  # uninitialized v0
            unknown = [name for name in tables if name not in EXPECTED_TABLES]
            if unknown:
                raise UnknownSchemaError(f"unrecognized tables in database: {unknown}")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        return SchemaReport(
            user_version=version,
            tables=tuple(tables),
            schema_fingerprint=_fingerprint(connection),
            integrity_ok=(integrity == "ok"),
            foreign_key_violations=tuple(tuple(row) for row in violations),
        )
    finally:
        connection.close()


__all__ = [
    "SCHEMA_VERSION",
    "EXPECTED_TABLES",
    "BackupHook",
    "MigrationReport",
    "SchemaReport",
    "AutomationMigrationError",
    "InvalidDatabasePathError",
    "InvalidDatabaseFileError",
    "UnsupportedSchemaVersionError",
    "UnknownSchemaError",
    "SchemaDriftError",
    "MigrationExecutionError",
    "BackupError",
    "migrate_database",
    "validate_database",
]
