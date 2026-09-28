"""One-view loading of a claimed job, its event, and direct dependencies."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from .models import (
    Attempt,
    ClaimedWork,
    Event,
    HandlerOutcome,
    HandlerResult,
    Job,
    JobStatus,
    RuntimeGate,
    RuntimeState,
)


_EVENT_COLS = (
    "event_id, event_type, subject_type, subject_id, input_hash, payload_json, "
    "policy_version, occurred_at, observed_at"
)
_JOB_COLS = (
    "job_id, job_key, job_type, subject_type, subject_id, input_hash, "
    "policy_version, handler_version, risk_class, status, priority, not_before, "
    "max_attempts, created_from_event_id, created_at, updated_at, "
    "last_error_code, last_error_detail"
)
_ATTEMPT_COLS = (
    "attempt_id, job_id, attempt_no, worker_id, lease_token, lease_until, "
    "started_at, heartbeat_at, finished_at, outcome, result_json, error_code, "
    "error_detail, runtime_generation"
)


class ExecutionSnapshotError(RuntimeError):
    """The claimed work no longer has one valid execution view."""


@dataclass(frozen=True)
class DependencyExecutionResult:
    job_id: str
    job_type: str
    handler_version: str
    attempt_id: str
    attempt_no: int
    result: HandlerResult

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, str) and value
            for value in (
                self.job_id,
                self.job_type,
                self.handler_version,
                self.attempt_id,
            )
        ):
            raise ValueError("dependency identity fields must be non-empty")
        if type(self.attempt_no) is not int or self.attempt_no < 1:
            raise ValueError("dependency attempt_no must be positive")
        if self.result.outcome is not HandlerOutcome.SUCCEEDED:
            raise ValueError("dependency result must be succeeded")


@dataclass(frozen=True)
class ExecutionSnapshot:
    job: Job
    attempt: Attempt
    event: Event
    dependencies: tuple[DependencyExecutionResult, ...]

    def __post_init__(self) -> None:
        if self.job.job_id != self.attempt.job_id:
            raise ValueError("snapshot job and attempt differ")
        if self.job.created_from_event_id != self.event.event_id:
            raise ValueError("snapshot job and event differ")
        types = [item.job_type for item in self.dependencies]
        if len(types) != len(set(types)):
            raise ValueError("snapshot dependency job types must be unique")


def _active_claim(
    connection: sqlite3.Connection, claimed: ClaimedWork, now: str
) -> tuple[Job, Attempt]:
    gate_row = connection.execute(
        "SELECT desired_state, control_generation, updated_at "
        "FROM runtime_gate WHERE singleton_id=1"
    ).fetchone()
    if gate_row is None:
        raise ExecutionSnapshotError("runtime gate is missing")
    gate = RuntimeGate.from_dict(dict(gate_row))
    if gate.desired_state is not RuntimeState.ENABLED:
        raise ExecutionSnapshotError("runtime gate is paused")
    if gate.control_generation != claimed.attempt.runtime_generation:
        raise ExecutionSnapshotError("runtime generation differs from claim")
    attempt_row = connection.execute(
        f"SELECT {_ATTEMPT_COLS} FROM attempts WHERE attempt_id=?",
        (claimed.attempt.attempt_id,),
    ).fetchone()
    if attempt_row is None:
        raise ExecutionSnapshotError("claimed attempt is missing")
    attempt = Attempt.from_dict(dict(attempt_row))
    _validate_attempt(connection, claimed, attempt, now)
    job_row = connection.execute(
        f"SELECT {_JOB_COLS} FROM jobs WHERE job_id=?", (attempt.job_id,)
    ).fetchone()
    if job_row is None:
        raise ExecutionSnapshotError("claimed job is missing")
    job = Job.from_dict(dict(job_row))
    if job != claimed.job or job.status is not JobStatus.RUNNING:
        raise ExecutionSnapshotError("claimed job identity or state changed")
    return job, attempt


def _validate_attempt(
    connection: sqlite3.Connection,
    claimed: ClaimedWork,
    attempt: Attempt,
    now: str,
) -> None:
    if attempt != claimed.attempt:
        raise ExecutionSnapshotError("claimed attempt identity changed")
    if attempt.finished_at is not None or attempt.lease_until < now:
        raise ExecutionSnapshotError("claimed attempt is finished or expired")
    latest = connection.execute(
        "SELECT MAX(attempt_no) FROM attempts WHERE job_id=?", (attempt.job_id,)
    ).fetchone()[0]
    if latest != attempt.attempt_no:
        raise ExecutionSnapshotError("claimed attempt is not latest")


def _event_for_job(connection: sqlite3.Connection, job: Job) -> Event:
    row = connection.execute(
        f"SELECT {_EVENT_COLS} FROM events WHERE event_id=?",
        (job.created_from_event_id,),
    ).fetchone()
    if row is None:
        raise ExecutionSnapshotError("job event is missing")
    event = Event.from_dict(dict(row))
    if (
        event.subject_type != job.subject_type
        or event.subject_id != job.subject_id
        or event.input_hash != job.input_hash
        or event.policy_version != job.policy_version
    ):
        raise ExecutionSnapshotError("job and event identity differ")
    return event


def _dependency_jobs(
    connection: sqlite3.Connection, job_id: str
) -> tuple[Job, ...]:
    rows = connection.execute(
        f"SELECT {_JOB_COLS.replace('job_id', 'parent.job_id', 1)} "
        "FROM job_dependencies dependency JOIN jobs parent "
        "ON parent.job_id=dependency.depends_on_job_id "
        "WHERE dependency.job_id=? ORDER BY parent.job_type, parent.job_id",
        (job_id,),
    ).fetchall()
    return tuple(Job.from_dict(dict(row)) for row in rows)


def _dependency_result(
    connection: sqlite3.Connection, job: Job
) -> DependencyExecutionResult:
    if job.status is not JobStatus.SUCCEEDED:
        raise ExecutionSnapshotError(f"dependency {job.job_id} is not succeeded")
    row = connection.execute(
        f"SELECT {_ATTEMPT_COLS} FROM attempts WHERE job_id=? "
        "ORDER BY attempt_no DESC, attempt_id DESC LIMIT 1",
        (job.job_id,),
    ).fetchone()
    if row is None:
        raise ExecutionSnapshotError(f"dependency {job.job_id} has no attempt")
    attempt = Attempt.from_dict(dict(row))
    if (
        attempt.outcome is not HandlerOutcome.SUCCEEDED
        or attempt.finished_at is None
        or attempt.result_json is None
    ):
        raise ExecutionSnapshotError(
            f"dependency {job.job_id} has no successful persisted result"
        )
    try:
        decoded = json.loads(attempt.result_json)
        result = HandlerResult.from_dict(decoded)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ExecutionSnapshotError(
            f"dependency result is malformed for {job.job_id}"
        ) from exc
    if result.outcome is not HandlerOutcome.SUCCEEDED:
        raise ExecutionSnapshotError(
            f"dependency result is not succeeded for {job.job_id}"
        )
    return DependencyExecutionResult(
        job.job_id,
        job.job_type,
        job.handler_version,
        attempt.attempt_id,
        attempt.attempt_no,
        result,
    )


def load_execution_snapshot(
    connection: sqlite3.Connection, claimed: ClaimedWork, *, now: str
) -> ExecutionSnapshot:
    """Load one claimed execution view from an already-open read transaction."""
    try:
        job, attempt = _active_claim(connection, claimed, now)
        event = _event_for_job(connection, job)
        dependencies = tuple(
            _dependency_result(connection, parent)
            for parent in _dependency_jobs(connection, job.job_id)
        )
        return ExecutionSnapshot(job, attempt, event, dependencies)
    except ExecutionSnapshotError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ExecutionSnapshotError("execution snapshot record is invalid") from exc


__all__ = [
    "DependencyExecutionResult",
    "ExecutionSnapshot",
    "ExecutionSnapshotError",
    "load_execution_snapshot",
]
