"""Runtime-state and lease operations within an existing AUTO SQLite transaction."""

from __future__ import annotations

import sqlite3

from .models import Attempt, Job, JobStatus, RuntimeGate, RuntimeState
from .store_errors import (
    ConcurrentUpdateError,
    IntegrityViolationError,
    LeaseLostError,
    RecordNotFoundError,
    RuntimeGateClosedError,
    RuntimeGenerationError,
)


__all__ = [
    "JOB_COLUMNS",
    "ATTEMPT_COLUMNS",
    "job_from_row",
    "attempt_from_row",
    "runtime_gate_from_row",
    "read_runtime_gate",
    "set_runtime_gate",
    "job_row",
    "attempt_row",
    "enabled_gate",
    "latest_attempt_no",
    "require_active_attempt",
]


JOB_COLUMNS = (
    "job_id, job_key, job_type, subject_type, subject_id, input_hash, "
    "policy_version, handler_version, risk_class, status, priority, "
    "not_before, max_attempts, created_from_event_id, created_at, "
    "updated_at, last_error_code, last_error_detail"
)


ATTEMPT_COLUMNS = (
    "attempt_id, job_id, attempt_no, worker_id, lease_token, lease_until, "
    "started_at, heartbeat_at, finished_at, outcome, result_json, "
    "error_code, error_detail, runtime_generation"
)


def job_from_row(row: sqlite3.Row) -> Job:
    return Job.from_dict(dict(row))


def attempt_from_row(row: sqlite3.Row) -> Attempt:
    return Attempt.from_dict(dict(row))


def runtime_gate_from_row(row: sqlite3.Row) -> RuntimeGate:
    return RuntimeGate.from_dict(dict(row))


def read_runtime_gate(connection: sqlite3.Connection) -> RuntimeGate:
    row = connection.execute(
        "SELECT desired_state, control_generation, updated_at "
        "FROM runtime_gate WHERE singleton_id = 1"
    ).fetchone()
    if row is None:
        raise RuntimeGateClosedError("runtime gate row is missing")
    return runtime_gate_from_row(row)


def set_runtime_gate(
    connection: sqlite3.Connection, desired_state: RuntimeState, *, updated_at: str,
    expected_generation: int | None = None, advance_generation: bool = False,
) -> RuntimeGate:
    """Fence a generation inside the caller's existing write transaction."""
    if not isinstance(desired_state, RuntimeState):
        raise TypeError("desired_state must be RuntimeState")
    RuntimeGate(desired_state, 1, updated_at)
    if expected_generation is not None and (type(expected_generation) is not int or expected_generation < 1):
        raise ValueError("expected_generation must be a positive integer")
    current = read_runtime_gate(connection)
    if expected_generation is not None and current.control_generation != expected_generation:
        raise ConcurrentUpdateError("runtime gate generation changed")
    if current.desired_state is desired_state and not advance_generation:
        return current
    if updated_at < current.updated_at:
        raise IntegrityViolationError("runtime gate updated_at must not regress")
    generation = current.control_generation + 1
    changed = connection.execute(
        "UPDATE runtime_gate SET desired_state = ?, "
        "control_generation = ?, updated_at = ? WHERE singleton_id = 1 "
        "AND control_generation = ?",
        (desired_state.value, generation, updated_at, current.control_generation),
    )
    if changed.rowcount != 1:
        raise ConcurrentUpdateError("runtime gate generation changed")
    return RuntimeGate(desired_state, generation, updated_at)


def job_row(connection: sqlite3.Connection, job_id: str) -> sqlite3.Row:
    row = connection.execute(
        f"SELECT {JOB_COLUMNS} FROM jobs WHERE job_id = ?", (job_id,)
    ).fetchone()
    if row is None:
        raise RecordNotFoundError(f"job {job_id} not found")
    return row


def attempt_row(connection: sqlite3.Connection, attempt_id: str) -> sqlite3.Row:
    row = connection.execute(
        f"SELECT {ATTEMPT_COLUMNS} FROM attempts WHERE attempt_id = ?", (attempt_id,)
    ).fetchone()
    if row is None:
        raise RecordNotFoundError(f"attempt {attempt_id} not found")
    return row


def enabled_gate(
    connection: sqlite3.Connection, expected_generation: int
) -> RuntimeGate:
    try:
        gate = read_runtime_gate(connection)
    except (TypeError, ValueError) as exc:
        raise RuntimeGateClosedError("runtime gate row is invalid") from exc
    if gate.desired_state is not RuntimeState.ENABLED:
        raise RuntimeGateClosedError("runtime gate is paused")
    if gate.control_generation != expected_generation:
        raise RuntimeGenerationError(
            f"expected generation {expected_generation}, actual "
            f"{gate.control_generation}"
        )
    return gate


def latest_attempt_no(connection: sqlite3.Connection, job_id: str) -> int:
    return connection.execute(
        "SELECT COALESCE(MAX(attempt_no), 0) FROM attempts WHERE job_id = ?",
        (job_id,),
    ).fetchone()[0]


def require_active_attempt(
    connection: sqlite3.Connection,
    *,
    attempt_id: str,
    lease_token: str,
    runtime_generation: int,
    now: str,
) -> tuple[Attempt, Job]:
    enabled_gate(connection, runtime_generation)
    attempt = attempt_from_row(attempt_row(connection, attempt_id))
    if attempt.lease_token != lease_token:
        raise LeaseLostError("lease token does not match")
    if attempt.runtime_generation != runtime_generation:
        raise RuntimeGenerationError("attempt belongs to an older runtime generation")
    if attempt.finished_at is not None:
        raise LeaseLostError("attempt is already finished")
    if attempt.attempt_no != latest_attempt_no(connection, attempt.job_id):
        raise LeaseLostError("attempt is not the latest attempt for its job")
    if attempt.lease_until < now:
        raise LeaseLostError("attempt lease has expired")
    job = job_from_row(job_row(connection, attempt.job_id))
    if job.status is not JobStatus.RUNNING:
        raise LeaseLostError(f"job is {job.status.value}, not running")
    return attempt, job
