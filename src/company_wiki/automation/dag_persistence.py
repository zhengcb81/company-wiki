"""Connection-local persistence for one deterministic automation DAG.

The caller owns the SQLite transaction. This module owns only the DAG schema
rules, so ``AutomationStore`` remains the transaction boundary without growing
another unrelated set of row helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from .models import Event, Job, JobStatus, MaterializedDAG


class DAGPersistenceError(RuntimeError):
    """Base error translated to the stable AutomationStore error taxonomy."""


class DAGConflictError(DAGPersistenceError):
    pass


class DAGIntegrityError(DAGPersistenceError):
    pass


class DAGEventNotFoundError(DAGPersistenceError):
    pass


@dataclass(frozen=True)
class DAGPutResult:
    jobs_created: int
    jobs_existing: int
    dependencies_created: int
    dependencies_existing: int


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
_IMMUTABLE_JOB_FIELDS = (
    "job_id",
    "job_key",
    "job_type",
    "subject_type",
    "subject_id",
    "input_hash",
    "policy_version",
    "handler_version",
    "priority",
    "max_attempts",
    "created_from_event_id",
    "created_at",
)


def _validate(event: Event, dag: MaterializedDAG) -> None:
    dependent_ids = {child for child, _parent in dag.dependencies}
    for job in dag.jobs:
        if job.created_from_event_id != event.event_id:
            raise DAGIntegrityError("DAG job does not belong to the materialized event")
        expected_status = (
            JobStatus.PLANNED if job.job_id in dependent_ids else JobStatus.READY
        )
        if job.status is not expected_status:
            raise DAGIntegrityError(
                f"job {job.job_id} must start as {expected_status.value}"
            )


def _require_exact_event(connection: sqlite3.Connection, event: Event) -> None:
    row = connection.execute(
        f"SELECT {_EVENT_COLS} FROM events WHERE event_id = ?",
        (event.event_id,),
    ).fetchone()
    if row is None:
        raise DAGEventNotFoundError(f"event {event.event_id} not found")
    expected = event.to_dict()
    if any(row[name] != value for name, value in expected.items()):
        raise DAGConflictError(
            f"event {event.event_id} payload or metadata changed before materialization"
        )


def _same_job(row: sqlite3.Row, planned: Job) -> bool:
    if any(row[name] != getattr(planned, name) for name in _IMMUTABLE_JOB_FIELDS):
        return False
    if row["risk_class"] != planned.risk_class.value:
        return False
    existing_status = JobStatus(row["status"])
    if existing_status is JobStatus.DETECTED:
        return False
    return not (
        planned.status is JobStatus.READY
        and existing_status is JobStatus.PLANNED
    )


def _insert_job(connection: sqlite3.Connection, job: Job) -> bool:
    try:
        connection.execute(
            "INSERT INTO jobs (job_id, job_key, job_type, subject_type, "
            "subject_id, input_hash, policy_version, handler_version, "
            "risk_class, status, priority, not_before, max_attempts, "
            "created_from_event_id, created_at, updated_at, "
            "last_error_code, last_error_detail) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                job.job_id,
                job.job_key,
                job.job_type,
                job.subject_type,
                job.subject_id,
                job.input_hash,
                job.policy_version,
                job.handler_version,
                job.risk_class.value,
                job.status.value,
                job.priority,
                job.not_before,
                job.max_attempts,
                job.created_from_event_id,
                job.created_at,
                job.updated_at,
                job.last_error_code,
                job.last_error_detail,
            ),
        )
        return True
    except sqlite3.IntegrityError as exc:
        row = connection.execute(
            f"SELECT {_JOB_COLS} FROM jobs WHERE job_id = ? OR job_key = ?",
            (job.job_id, job.job_key),
        ).fetchone()
        if row is not None and _same_job(row, job):
            return False
        raise DAGConflictError(
            f"job {job.job_key} already exists with different materialized content"
        ) from exc


def _insert_dependency(
    connection: sqlite3.Connection,
    *,
    job_id: str,
    depends_on_job_id: str,
) -> bool:
    try:
        connection.execute(
            "INSERT INTO job_dependencies (job_id, depends_on_job_id, required_status) "
            "VALUES (?,?,?)",
            (job_id, depends_on_job_id, JobStatus.SUCCEEDED.value),
        )
        return True
    except sqlite3.IntegrityError as exc:
        row = connection.execute(
            "SELECT required_status FROM job_dependencies "
            "WHERE job_id = ? AND depends_on_job_id = ?",
            (job_id, depends_on_job_id),
        ).fetchone()
        if row is not None and row["required_status"] == JobStatus.SUCCEEDED.value:
            return False
        raise DAGConflictError(
            f"dependency ({job_id}, {depends_on_job_id}) conflicts"
        ) from exc


def _require_exact_dependencies(
    connection: sqlite3.Connection,
    dag: MaterializedDAG,
) -> None:
    expected = set(dag.dependencies)
    placeholders = ",".join("?" for _ in dag.jobs)
    rows = connection.execute(
        "SELECT job_id, depends_on_job_id FROM job_dependencies "
        f"WHERE job_id IN ({placeholders})",
        tuple(job.job_id for job in dag.jobs),
    ).fetchall()
    actual = {(row["job_id"], row["depends_on_job_id"]) for row in rows}
    if actual != expected:
        raise DAGConflictError("materialized dependency set differs from stored DAG")


def write_materialized_dag(
    connection: sqlite3.Connection,
    event: Event,
    dag: MaterializedDAG,
) -> DAGPutResult:
    """Write all jobs and edges using the transaction owned by the caller."""

    _validate(event, dag)
    _require_exact_event(connection, event)
    job_results = tuple(_insert_job(connection, job) for job in dag.jobs)
    dependency_results = tuple(
        _insert_dependency(
            connection,
            job_id=job_id,
            depends_on_job_id=depends_on_job_id,
        )
        for job_id, depends_on_job_id in dag.dependencies
    )
    _require_exact_dependencies(connection, dag)
    return DAGPutResult(
        jobs_created=sum(job_results),
        jobs_existing=len(job_results) - sum(job_results),
        dependencies_created=sum(dependency_results),
        dependencies_existing=len(dependency_results) - sum(dependency_results),
    )


__all__ = [
    "DAGConflictError",
    "DAGEventNotFoundError",
    "DAGIntegrityError",
    "DAGPutResult",
    "write_materialized_dag",
]
