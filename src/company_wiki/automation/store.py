"""AUTO-2 AutomationStore: explicit-path, transactional, idempotent persistence.

This module depends only on the Python standard library, ``models`` (AUTO-1
frozen contract) and ``migrations`` (schema v1).  It does not import the legacy
scheduler, read configuration/environment variables, spawn threads, or open a
default database path.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from .migrations import (
    BackupHook,
    SchemaReport,
    migrate_database,
    validate_database,
)
from .models import (
    Approval,
    Effect,
    Event,
    Job,
    JobStatus,
    Attempt,
    validate_job_transition,
)

T = TypeVar("T")


# --------------------------------------------------------------------------- #
# Store errors (stable codes; original exceptions chained).
# --------------------------------------------------------------------------- #
class AutomationStoreError(Exception):
    code = "automation_store_error"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.code)
        self.detail = detail


class InvalidStorePathError(AutomationStoreError):
    code = "invalid_store_path"


class StoreBusyError(AutomationStoreError):
    code = "store_busy"


class IntegrityViolationError(AutomationStoreError):
    code = "integrity_violation"


class IdempotencyConflictError(AutomationStoreError):
    code = "idempotency_conflict"


class RecordNotFoundError(AutomationStoreError):
    code = "record_not_found"


class ConcurrentUpdateError(AutomationStoreError):
    code = "concurrent_update"


class CorruptRecordError(AutomationStoreError):
    code = "corrupt_record"


# --------------------------------------------------------------------------- #
# PutResult.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PutResult(Generic[T]):
    value: T
    created: bool


# --------------------------------------------------------------------------- #
# Explicit column lists (AUTO-2.20).
# --------------------------------------------------------------------------- #
_EVENT_COLS = (
    "event_id, event_type, subject_type, subject_id, input_hash, "
    "payload_json, policy_version, occurred_at, observed_at"
)
_JOB_COLS = (
    "job_id, job_key, job_type, subject_type, subject_id, input_hash, "
    "policy_version, handler_version, risk_class, status, priority, "
    "not_before, max_attempts, created_from_event_id, created_at, "
    "updated_at, last_error_code, last_error_detail"
)
_ATTEMPT_COLS = (
    "attempt_id, job_id, attempt_no, worker_id, lease_token, lease_until, "
    "started_at, heartbeat_at, finished_at, outcome, result_json, "
    "error_code, error_detail"
)
_APPROVAL_COLS = (
    "approval_id, job_id, action_hash, reviewer_principal, "
    "reviewer_session_id, role, decision, decided_at, receipt_hash"
)
_EFFECT_COLS = (
    "effect_id, effect_key, job_id, effect_type, target, before_hash, "
    "intended_after_hash, actual_after_hash, status, created_at, verified_at"
)


# --------------------------------------------------------------------------- #
# Row-to-model mappers (private, one per type).
# --------------------------------------------------------------------------- #
def _event_from_row(row: sqlite3.Row) -> Event:
    return Event.from_dict(dict(row))


def _job_from_row(row: sqlite3.Row) -> Job:
    return Job.from_dict(dict(row))


def _attempt_from_row(row: sqlite3.Row) -> Attempt:
    return Attempt.from_dict(dict(row))


def _approval_from_row(row: sqlite3.Row) -> Approval:
    return Approval.from_dict(dict(row))


def _effect_from_row(row: sqlite3.Row) -> Effect:
    return Effect.from_dict(dict(row))


# --------------------------------------------------------------------------- #
# Idempotency helpers.
# --------------------------------------------------------------------------- #
def _idempotent_match(existing: object, new: object, ignore_key: str) -> bool:
    d1 = {k: v for k, v in existing.to_dict().items() if k != ignore_key}
    d2 = {k: v for k, v in new.to_dict().items() if k != ignore_key}
    return d1 == d2


def _resolve_idempotency(
    conn: sqlite3.Connection,
    table: str,
    pk_col: str,
    natural_key_cols: tuple[str, ...],
    ignore_col: str,
    col_list: str,
    from_row_fn,
    value,
    exc: sqlite3.IntegrityError,
):
    pk_value = getattr(value, pk_col)
    row = conn.execute(
        f"SELECT {col_list} FROM {table} WHERE {pk_col} = ?", (pk_value,)
    ).fetchone()
    if row is not None:
        existing = from_row_fn(row)
        if _idempotent_match(existing, value, ignore_col):
            return PutResult(value=existing, created=False)
        raise IdempotencyConflictError(
            f"{table} {pk_col}={pk_value} already exists with different content"
        )
    nk_values = tuple(getattr(value, c) for c in natural_key_cols)
    where = " AND ".join(f"{c} = ?" for c in natural_key_cols)
    row = conn.execute(
        f"SELECT {col_list} FROM {table} WHERE {where}", nk_values
    ).fetchone()
    if row is not None:
        existing = from_row_fn(row)
        if _idempotent_match(existing, value, ignore_col):
            return PutResult(value=existing, created=False)
        raise IdempotencyConflictError(
            f"{table} natural key already exists with different content"
        )
    raise IntegrityViolationError(
        f"INSERT {table} failed but no matching record found: {exc}"
    )


# --------------------------------------------------------------------------- #
# AutomationStore.
# --------------------------------------------------------------------------- #
class AutomationStore:
    def __init__(
        self,
        db_path: Path,
        *,
        timeout_seconds: float = 5.0,
        backup_hook: BackupHook | None = None,
    ) -> None:
        if not isinstance(db_path, Path):
            raise TypeError("db_path must be a pathlib.Path instance")
        if db_path.name == ":memory:" or str(db_path) == ":memory:":
            raise InvalidStorePathError(":memory: databases are not supported")
        if db_path.name == "":
            raise InvalidStorePathError("db_path must include a database file name")
        if not db_path.parent.is_dir():
            raise InvalidStorePathError(
                f"parent directory does not exist; refusing to mkdir: {db_path.parent}"
            )
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive number")
        self._db_path = db_path
        self._timeout = float(timeout_seconds)
        migrate_database(db_path, backup_hook=backup_hook)

    @property
    def db_path(self) -> Path:
        return self._db_path

    def schema_report(self) -> SchemaReport:
        return validate_database(self._db_path)

    # -- connection helpers ------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self._db_path), timeout=self._timeout, isolation_level=None
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(f"PRAGMA busy_timeout = {int(self._timeout * 1000)}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = FULL")
        return conn

    def _write_transaction(self, operation):
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                result = operation(conn)
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
            return result
        except sqlite3.OperationalError as exc:
            if "database is locked" in str(exc).lower():
                raise StoreBusyError(
                    f"database locked after {self._timeout}s timeout"
                ) from exc
            raise
        finally:
            conn.close()

    # -- Event CRUD -------------------------------------------------------- #

    def put_event(self, value: Event) -> PutResult[Event]:
        def _op(conn):
            try:
                conn.execute(
                    "INSERT INTO events (event_id, event_type, subject_type, "
                    "subject_id, input_hash, payload_json, policy_version, "
                    "occurred_at, observed_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        value.event_id, value.event_type, value.subject_type,
                        value.subject_id, value.input_hash, value.payload_json,
                        value.policy_version, value.occurred_at, value.observed_at,
                    ),
                )
                return PutResult(value=value, created=True)
            except sqlite3.IntegrityError as exc:
                return _resolve_idempotency(
                    conn, "events", "event_id",
                    ("event_type", "subject_type", "subject_id", "input_hash", "policy_version"),
                    "event_id", _EVENT_COLS, _event_from_row, value, exc,
                )

        return self._write_transaction(_op)

    def get_event(self, event_id: str) -> Event | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {_EVENT_COLS} FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
            return _event_from_row(row) if row else None
        finally:
            conn.close()

    def get_event_by_identity(
        self, event_type: str, subject_type: str, subject_id: str,
        input_hash: str, policy_version: str,
    ) -> Event | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {_EVENT_COLS} FROM events WHERE event_type=? AND "
                "subject_type=? AND subject_id=? AND input_hash=? AND policy_version=?",
                (event_type, subject_type, subject_id, input_hash, policy_version),
            ).fetchone()
            return _event_from_row(row) if row else None
        finally:
            conn.close()

    # -- Job CRUD ---------------------------------------------------------- #

    def put_job(self, value: Job) -> PutResult[Job]:
        def _op(conn):
            try:
                conn.execute(
                    "INSERT INTO jobs (job_id, job_key, job_type, subject_type, "
                    "subject_id, input_hash, policy_version, handler_version, "
                    "risk_class, status, priority, not_before, max_attempts, "
                    "created_from_event_id, created_at, updated_at, "
                    "last_error_code, last_error_detail) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        value.job_id, value.job_key, value.job_type,
                        value.subject_type, value.subject_id, value.input_hash,
                        value.policy_version, value.handler_version,
                        value.risk_class.value, value.status.value,
                        value.priority, value.not_before, value.max_attempts,
                        value.created_from_event_id, value.created_at,
                        value.updated_at, value.last_error_code,
                        value.last_error_detail,
                    ),
                )
                return PutResult(value=value, created=True)
            except sqlite3.IntegrityError as exc:
                return _resolve_idempotency(
                    conn, "jobs", "job_id", ("job_key",), "job_id",
                    _JOB_COLS, _job_from_row, value, exc,
                )

        return self._write_transaction(_op)

    def get_job(self, job_id: str) -> Job | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {_JOB_COLS} FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            return _job_from_row(row) if row else None
        finally:
            conn.close()

    def get_job_by_key(self, job_key: str) -> Job | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {_JOB_COLS} FROM jobs WHERE job_key = ?", (job_key,)
            ).fetchone()
            return _job_from_row(row) if row else None
        finally:
            conn.close()

    def list_jobs(self, *, status: JobStatus | None = None) -> tuple[Job, ...]:
        conn = self._connect()
        try:
            base = f"SELECT {_JOB_COLS} FROM jobs"
            if status is not None:
                rows = conn.execute(
                    base + " WHERE status = ? ORDER BY priority DESC, created_at ASC, job_id ASC",
                    (status.value,),
                ).fetchall()
            else:
                rows = conn.execute(
                    base + " ORDER BY priority DESC, created_at ASC, job_id ASC"
                ).fetchall()
            return tuple(_job_from_row(r) for r in rows)
        finally:
            conn.close()

    # -- Job dependency ---------------------------------------------------- #

    def add_job_dependency(
        self,
        job_id: str,
        depends_on_job_id: str,
        required_status: JobStatus = JobStatus.SUCCEEDED,
    ) -> bool:
        if required_status is not JobStatus.SUCCEEDED:
            raise IntegrityViolationError(
                f"required_status must be SUCCEEDED, got {required_status.value}"
            )
        if job_id == depends_on_job_id:
            raise IntegrityViolationError("self-dependency is not allowed")

        def _op(conn):
            try:
                conn.execute(
                    "INSERT INTO job_dependencies (job_id, depends_on_job_id, "
                    "required_status) VALUES (?,?,?)",
                    (job_id, depends_on_job_id, required_status.value),
                )
                return True
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT required_status FROM job_dependencies "
                    "WHERE job_id = ? AND depends_on_job_id = ?",
                    (job_id, depends_on_job_id),
                ).fetchone()
                if row is not None and row["required_status"] == required_status.value:
                    return False
                raise IntegrityViolationError(
                    f"dependency ({job_id}, {depends_on_job_id}) exists with "
                    f"different required_status"
                )

        return self._write_transaction(_op)

    def list_job_dependencies(self, job_id: str) -> tuple[tuple[str, str], ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT job_id, depends_on_job_id FROM job_dependencies "
                "WHERE job_id = ? ORDER BY depends_on_job_id",
                (job_id,),
            ).fetchall()
            return tuple((r["job_id"], r["depends_on_job_id"]) for r in rows)
        finally:
            conn.close()

    # -- Attempt CRUD ------------------------------------------------------ #

    def put_attempt(self, value: Attempt) -> PutResult[Attempt]:
        def _op(conn):
            try:
                conn.execute(
                    "INSERT INTO attempts (attempt_id, job_id, attempt_no, "
                    "worker_id, lease_token, lease_until, started_at, "
                    "heartbeat_at, finished_at, outcome, result_json, "
                    "error_code, error_detail) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        value.attempt_id, value.job_id, value.attempt_no,
                        value.worker_id, value.lease_token, value.lease_until,
                        value.started_at, value.heartbeat_at, value.finished_at,
                        value.outcome.value if value.outcome is not None else None,
                        value.result_json, value.error_code, value.error_detail,
                    ),
                )
                return PutResult(value=value, created=True)
            except sqlite3.IntegrityError as exc:
                return _resolve_idempotency(
                    conn, "attempts", "attempt_id",
                    ("job_id", "attempt_no"), "attempt_id",
                    _ATTEMPT_COLS, _attempt_from_row, value, exc,
                )

        return self._write_transaction(_op)

    def get_attempt(self, attempt_id: str) -> Attempt | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {_ATTEMPT_COLS} FROM attempts WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
            return _attempt_from_row(row) if row else None
        finally:
            conn.close()

    def list_attempts(self, job_id: str) -> tuple[Attempt, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                f"SELECT {_ATTEMPT_COLS} FROM attempts WHERE job_id = ? "
                "ORDER BY attempt_no, attempt_id",
                (job_id,),
            ).fetchall()
            return tuple(_attempt_from_row(r) for r in rows)
        finally:
            conn.close()

    # -- Approval CRUD ----------------------------------------------------- #

    def put_approval(self, value: Approval) -> PutResult[Approval]:
        def _op(conn):
            try:
                conn.execute(
                    "INSERT INTO approvals (approval_id, job_id, action_hash, "
                    "reviewer_principal, reviewer_session_id, role, decision, "
                    "decided_at, receipt_hash) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        value.approval_id, value.job_id, value.action_hash,
                        value.reviewer_principal, value.reviewer_session_id,
                        value.role, value.decision.value, value.decided_at,
                        value.receipt_hash,
                    ),
                )
                return PutResult(value=value, created=True)
            except sqlite3.IntegrityError as exc:
                return _resolve_idempotency(
                    conn, "approvals", "approval_id",
                    ("job_id", "role", "reviewer_principal", "receipt_hash"),
                    "approval_id", _APPROVAL_COLS, _approval_from_row, value, exc,
                )

        return self._write_transaction(_op)

    def get_approval(self, approval_id: str) -> Approval | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {_APPROVAL_COLS} FROM approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
            return _approval_from_row(row) if row else None
        finally:
            conn.close()

    def list_approvals(self, job_id: str) -> tuple[Approval, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                f"SELECT {_APPROVAL_COLS} FROM approvals WHERE job_id = ? "
                "ORDER BY decided_at, approval_id",
                (job_id,),
            ).fetchall()
            return tuple(_approval_from_row(r) for r in rows)
        finally:
            conn.close()

    # -- Effect CRUD ------------------------------------------------------- #

    def put_effect(self, value: Effect) -> PutResult[Effect]:
        def _op(conn):
            try:
                conn.execute(
                    "INSERT INTO effects (effect_id, effect_key, job_id, "
                    "effect_type, target, before_hash, intended_after_hash, "
                    "actual_after_hash, status, created_at, verified_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        value.effect_id, value.effect_key, value.job_id,
                        value.effect_type, value.target, value.before_hash,
                        value.intended_after_hash, value.actual_after_hash,
                        value.status.value, value.created_at, value.verified_at,
                    ),
                )
                return PutResult(value=value, created=True)
            except sqlite3.IntegrityError as exc:
                return _resolve_idempotency(
                    conn, "effects", "effect_id", ("effect_key",), "effect_id",
                    _EFFECT_COLS, _effect_from_row, value, exc,
                )

        return self._write_transaction(_op)

    def get_effect(self, effect_id: str) -> Effect | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {_EFFECT_COLS} FROM effects WHERE effect_id = ?",
                (effect_id,),
            ).fetchone()
            return _effect_from_row(row) if row else None
        finally:
            conn.close()

    def get_effect_by_key(self, effect_key: str) -> Effect | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {_EFFECT_COLS} FROM effects WHERE effect_key = ?",
                (effect_key,),
            ).fetchone()
            return _effect_from_row(row) if row else None
        finally:
            conn.close()

    def list_effects(self, job_id: str) -> tuple[Effect, ...]:
        conn = self._connect()
        try:
            rows = conn.execute(
                f"SELECT {_EFFECT_COLS} FROM effects WHERE job_id = ? "
                "ORDER BY created_at, effect_id",
                (job_id,),
            ).fetchall()
            return tuple(_effect_from_row(r) for r in rows)
        finally:
            conn.close()

    # -- Job CAS transition (batch 3 skeleton) ----------------------------- #

    def transition_job(
        self,
        job_id: str,
        *,
        expected: JobStatus,
        target: JobStatus,
        updated_at: str,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> Job:
        validate_job_transition(expected, target)

        def _op(conn):
            row = conn.execute(
                f"SELECT {_JOB_COLS} FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise RecordNotFoundError(f"job {job_id} not found")
            current = _job_from_row(row)
            if current.status is not expected:
                raise ConcurrentUpdateError(
                    f"expected status {expected.value} but actual is {current.status.value}"
                )
            if updated_at < current.updated_at:
                raise IntegrityViolationError(
                    f"updated_at {updated_at} is before current {current.updated_at}"
                )
            result = conn.execute(
                "UPDATE jobs SET status = ?, updated_at = ?, last_error_code = ?, "
                "last_error_detail = ? WHERE job_id = ? AND status = ?",
                (target.value, updated_at, error_code, error_detail,
                 job_id, expected.value),
            )
            if result.rowcount != 1:
                raise ConcurrentUpdateError(
                    f"CAS update failed: expected 1 row, got {result.rowcount}"
                )
            return _job_from_row(
                conn.execute(
                    f"SELECT {_JOB_COLS} FROM jobs WHERE job_id = ?", (job_id,)
                ).fetchone()
            )

        return self._write_transaction(_op)

    # -- Outbox CRUD (written in same txn as job transition) --------------- #

    _OUTBOX_COLS = (
        "outbox_id, effect_id, payload_json, status, attempt_count, "
        "not_before, lease_token, lease_until, last_error"
    )

    def put_outbox_entry(
        self,
        outbox_id: str,
        effect_id: str,
        payload_json: str,
        status: str,
        not_before: str,
    ) -> None:
        """Insert an outbox entry (called within a write transaction)."""
        def _op(conn):
            conn.execute(
                "INSERT INTO outbox (outbox_id, effect_id, payload_json, "
                "status, attempt_count, not_before) VALUES (?,?,?,?,0,?)",
                (outbox_id, effect_id, payload_json, status, not_before),
            )
        self._write_transaction(_op)

    def get_outbox_entry(self, outbox_id: str) -> dict | None:
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {self._OUTBOX_COLS} FROM outbox WHERE outbox_id = ?",
                (outbox_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_outbox_entries(
        self, *, status: str | None = None, limit: int = 100
    ) -> tuple[dict, ...]:
        conn = self._connect()
        try:
            if status is not None:
                rows = conn.execute(
                    f"SELECT {self._OUTBOX_COLS} FROM outbox WHERE status = ? "
                    "ORDER BY not_before LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {self._OUTBOX_COLS} FROM outbox "
                    "ORDER BY not_before LIMIT ?",
                    (limit,),
                ).fetchall()
            return tuple(dict(r) for r in rows)
        finally:
            conn.close()


__all__ = [
    "AutomationStore",
    "PutResult",
    "AutomationStoreError",
    "InvalidStorePathError",
    "StoreBusyError",
    "IntegrityViolationError",
    "IdempotencyConflictError",
    "RecordNotFoundError",
    "ConcurrentUpdateError",
    "CorruptRecordError",
]
