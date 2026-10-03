"""AUTO-2 AutomationStore: explicit-path, transactional, idempotent persistence.

This module depends only on the Python standard library, ``models`` (AUTO-1
contract) and ``migrations`` (schema v2). It does not import the legacy
scheduler, read configuration/environment variables, spawn threads, or open a
default database path.
"""

from __future__ import annotations

import sqlite3
import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

from company_wiki._id_scope import normalize_id_scope

from .dag_persistence import (
    DAGConflictError,
    DAGEventNotFoundError,
    DAGIntegrityError,
    DAGPutResult,
    write_materialized_dag,
)
from .migrations import (
    BackupHook,
    SchemaReport,
    migrate_database,
    validate_database,
)
from .execution_snapshot import ExecutionSnapshot, load_execution_snapshot
from .models import (
    Approval,
    ClaimedWork,
    Effect,
    EffectStatus,
    Event,
    HandlerOutcome,
    HandlerResult,
    Job,
    JobStatus,
    MaterializedDAG,
    Attempt,
    OutboxLease,
    RuntimeGate,
    RuntimeState,
    canonical_json,
    require_utc_timestamp,
    require_sha256,
    validate_job_transition,
)
from .terminal_receipt_contracts import (
    FinalArtifactPin, TerminalCompactionResult, TERMINAL_RECEIPT_SCHEMA,
    is_terminal_receipt, terminal_job_scope,
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


class TerminalResultCompactedError(IntegrityViolationError):
    """The original result was retired; read the exact final artifact instead."""

    code = "terminal_result_compacted"


class IdempotencyConflictError(AutomationStoreError):
    code = "idempotency_conflict"


class RecordNotFoundError(AutomationStoreError):
    code = "record_not_found"


class ConcurrentUpdateError(AutomationStoreError):
    code = "concurrent_update"


class CorruptRecordError(AutomationStoreError):
    code = "corrupt_record"


class RuntimeGateClosedError(AutomationStoreError):
    code = "runtime_gate_closed"


class RuntimeGenerationError(AutomationStoreError):
    code = "runtime_generation_mismatch"


class LeaseLostError(AutomationStoreError):
    code = "lease_lost"


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
    "error_code, error_detail, runtime_generation"
)
_APPROVAL_COLS = (
    "approval_id, job_id, action_hash, reviewer_principal, "
    "reviewer_session_id, role, decision, decided_at, receipt_hash"
)
_EFFECT_COLS = (
    "effect_id, effect_key, job_id, effect_type, target, before_hash, "
    "intended_after_hash, actual_after_hash, status, created_at, verified_at"
)
_OUTBOX_COLS = (
    "outbox_id, effect_id, payload_json, status, attempt_count, "
    "not_before, lease_token, lease_until, last_error"
)
_ATTEMPT_COLS_A = ", ".join(
    f"a.{column.strip()}" for column in _ATTEMPT_COLS.split(",")
)
_OUTBOX_COLS_O = ", ".join(
    f"o.{column.strip()}" for column in _OUTBOX_COLS.split(",")
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


def _runtime_gate_from_row(row: sqlite3.Row) -> RuntimeGate:
    return RuntimeGate.from_dict(dict(row))


def _job_row(connection: sqlite3.Connection, job_id: str) -> sqlite3.Row:
    row = connection.execute(
        f"SELECT {_JOB_COLS} FROM jobs WHERE job_id = ?", (job_id,)
    ).fetchone()
    if row is None:
        raise RecordNotFoundError(f"job {job_id} not found")
    return row


def _attempt_row(connection: sqlite3.Connection, attempt_id: str) -> sqlite3.Row:
    row = connection.execute(
        f"SELECT {_ATTEMPT_COLS} FROM attempts WHERE attempt_id = ?", (attempt_id,)
    ).fetchone()
    if row is None:
        raise RecordNotFoundError(f"attempt {attempt_id} not found")
    return row


def _enabled_gate(
    connection: sqlite3.Connection, expected_generation: int
) -> RuntimeGate:
    row = connection.execute(
        "SELECT desired_state, control_generation, updated_at "
        "FROM runtime_gate WHERE singleton_id = 1"
    ).fetchone()
    if row is None:
        raise RuntimeGateClosedError("runtime gate row is missing")
    try:
        gate = _runtime_gate_from_row(row)
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


def _latest_attempt_no(connection: sqlite3.Connection, job_id: str) -> int:
    return connection.execute(
        "SELECT COALESCE(MAX(attempt_no), 0) FROM attempts WHERE job_id = ?",
        (job_id,),
    ).fetchone()[0]


def _require_active_attempt(
    connection: sqlite3.Connection,
    *,
    attempt_id: str,
    lease_token: str,
    runtime_generation: int,
    now: str,
) -> tuple[Attempt, Job]:
    _enabled_gate(connection, runtime_generation)
    attempt = _attempt_from_row(_attempt_row(connection, attempt_id))
    if attempt.lease_token != lease_token:
        raise LeaseLostError("lease token does not match")
    if attempt.runtime_generation != runtime_generation:
        raise RuntimeGenerationError("attempt belongs to an older runtime generation")
    if attempt.finished_at is not None:
        raise LeaseLostError("attempt is already finished")
    if attempt.attempt_no != _latest_attempt_no(connection, attempt.job_id):
        raise LeaseLostError("attempt is not the latest attempt for its job")
    if attempt.lease_until < now:
        raise LeaseLostError("attempt lease has expired")
    job = _job_from_row(_job_row(connection, attempt.job_id))
    if job.status is not JobStatus.RUNNING:
        raise LeaseLostError(f"job is {job.status.value}, not running")
    return attempt, job


def _transition_job_in_transaction(
    connection: sqlite3.Connection,
    job: Job,
    *,
    target: JobStatus,
    updated_at: str,
    not_before: str | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
) -> Job:
    validate_job_transition(job.status, target)
    if updated_at < job.updated_at:
        raise IntegrityViolationError("job updated_at must not move backwards")
    due = job.not_before if not_before is None else not_before
    changed = connection.execute(
        "UPDATE jobs SET status = ?, updated_at = ?, not_before = ?, "
        "last_error_code = ?, last_error_detail = ? "
        "WHERE job_id = ? AND status = ?",
        (
            target.value,
            updated_at,
            due,
            error_code,
            error_detail,
            job.job_id,
            job.status.value,
        ),
    )
    if changed.rowcount != 1:
        raise ConcurrentUpdateError(f"job {job.job_id} changed during transaction")
    return _job_from_row(_job_row(connection, job.job_id))


def _insert_effect(connection: sqlite3.Connection, effect: Effect) -> None:
    try:
        connection.execute(
            "INSERT INTO effects (effect_id, effect_key, job_id, effect_type, "
            "target, before_hash, intended_after_hash, actual_after_hash, "
            "status, created_at, verified_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                effect.effect_id,
                effect.effect_key,
                effect.job_id,
                effect.effect_type,
                effect.target,
                effect.before_hash,
                effect.intended_after_hash,
                effect.actual_after_hash,
                effect.status.value,
                effect.created_at,
                effect.verified_at,
            ),
        )
    except sqlite3.IntegrityError as exc:
        by_id = connection.execute(
            f"SELECT {_EFFECT_COLS} FROM effects WHERE effect_id = ?",
            (effect.effect_id,),
        ).fetchone()
        by_key = connection.execute(
            f"SELECT {_EFFECT_COLS} FROM effects WHERE effect_key = ?",
            (effect.effect_key,),
        ).fetchone()
        existing_row = by_id or by_key
        if existing_row is not None and _effect_from_row(existing_row) == effect:
            return
        raise IdempotencyConflictError(
            f"effect identity conflict for {effect.effect_id}"
        ) from exc


def _insert_outbox(
    connection: sqlite3.Connection,
    effect: Effect,
    *,
    not_before: str,
) -> None:
    outbox_id = f"outbox-{effect.effect_id}"
    payload = canonical_json(effect.to_dict())
    try:
        connection.execute(
            "INSERT INTO outbox (outbox_id, effect_id, payload_json, status, "
            "attempt_count, not_before) VALUES (?,?,?,?,0,?)",
            (outbox_id, effect.effect_id, payload, "pending", not_before),
        )
    except sqlite3.IntegrityError as exc:
        row = connection.execute(
            "SELECT outbox_id, effect_id, payload_json, status, attempt_count, "
            "not_before, lease_token, lease_until, last_error "
            "FROM outbox WHERE outbox_id = ? OR effect_id = ?",
            (outbox_id, effect.effect_id),
        ).fetchone()
        if row is not None and dict(row) == {
            "outbox_id": outbox_id,
            "effect_id": effect.effect_id,
            "payload_json": payload,
            "status": "pending",
            "attempt_count": 0,
            "not_before": not_before,
            "lease_token": None,
            "lease_until": None,
            "last_error": None,
        }:
            return
        raise IdempotencyConflictError(
            f"outbox identity conflict for {outbox_id}"
        ) from exc


def _finish_target(result: HandlerResult, *, has_effects: bool) -> JobStatus:
    if result.outcome is HandlerOutcome.SUCCEEDED:
        return JobStatus.VERIFYING if has_effects else JobStatus.SUCCEEDED
    if result.outcome is HandlerOutcome.RETRYABLE:
        return JobStatus.RETRY_WAIT
    if result.outcome is HandlerOutcome.BLOCKED_HUMAN:
        return JobStatus.BLOCKED_HUMAN
    return JobStatus.DEAD_LETTER


def _validate_result_effects(result: HandlerResult, job_id: str) -> None:
    if result.effects and result.outcome is not HandlerOutcome.SUCCEEDED:
        raise IntegrityViolationError(
            "non-succeeded handler result must not publish effects"
        )
    for effect in result.effects:
        if effect.job_id != job_id:
            raise IntegrityViolationError(
                f"effect {effect.effect_id} belongs to another job"
            )
        if effect.status not in {EffectStatus.PLANNED, EffectStatus.PENDING}:
            raise IntegrityViolationError(
                f"effect {effect.effect_id} is already {effect.status.value}"
            )


def _update_finished_attempt(
    connection: sqlite3.Connection,
    attempt: Attempt,
    *,
    finished_at: str,
    result: HandlerResult,
) -> None:
    error_code = result.error.code if result.error is not None else None
    error_detail = result.error.detail if result.error is not None else None
    changed = connection.execute(
        "UPDATE attempts SET finished_at = ?, outcome = ?, result_json = ?, "
        "error_code = ?, error_detail = ? WHERE attempt_id = ? "
        "AND lease_token = ? AND finished_at IS NULL",
        (
            finished_at,
            result.outcome.value,
            canonical_json(result.to_dict()),
            error_code,
            error_detail,
            attempt.attempt_id,
            attempt.lease_token,
        ),
    )
    if changed.rowcount != 1:
        raise LeaseLostError("attempt changed during completion")


def _transition_finished_job(
    connection: sqlite3.Connection,
    job: Job,
    *,
    target: JobStatus,
    finished_at: str,
    retry_not_before: str | None,
    result: HandlerResult,
) -> None:
    if target is JobStatus.RETRY_WAIT and retry_not_before is None:
        raise IntegrityViolationError("retryable result requires retry_not_before")
    error_code = result.error.code if result.error is not None else None
    error_detail = result.error.detail if result.error is not None else None
    if target is JobStatus.SUCCEEDED:
        verifying = _transition_job_in_transaction(
            connection, job, target=JobStatus.VERIFYING, updated_at=finished_at
        )
        _transition_job_in_transaction(
            connection,
            verifying,
            target=JobStatus.SUCCEEDED,
            updated_at=finished_at,
        )
        return
    _transition_job_in_transaction(
        connection,
        job,
        target=target,
        updated_at=finished_at,
        not_before=retry_not_before if target is JobStatus.RETRY_WAIT else None,
        error_code=error_code,
        error_detail=error_detail,
    )


def _outbox_row(connection: sqlite3.Connection, outbox_id: str) -> sqlite3.Row:
    row = connection.execute(
        f"SELECT {_OUTBOX_COLS} FROM outbox WHERE outbox_id = ?", (outbox_id,)
    ).fetchone()
    if row is None:
        raise RecordNotFoundError(f"outbox {outbox_id} not found")
    return row


def _require_outbox_lease(
    connection: sqlite3.Connection,
    *,
    outbox_id: str,
    lease_token: str,
    runtime_generation: int,
    now: str,
) -> sqlite3.Row:
    _enabled_gate(connection, runtime_generation)
    row = _outbox_row(connection, outbox_id)
    if row["status"] != "leased" or row["lease_token"] != lease_token:
        raise LeaseLostError("outbox lease token or state does not match")
    if row["lease_until"] is None or row["lease_until"] < now:
        raise LeaseLostError("outbox lease has expired")
    return row


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


def _block_terminal_dependencies(
    connection: sqlite3.Connection,
    *,
    now: str,
    allowed_job_ids: tuple[str, ...] | None = None,
) -> None:
    scope_sql = ""
    parameters: tuple[object, ...] = (
        JobStatus.PLANNED.value, JobStatus.DEAD_LETTER.value, JobStatus.CANCELLED.value,
    )
    if allowed_job_ids is not None:
        scope_sql = "AND child.job_id IN (" + ",".join("?" for _ in allowed_job_ids) + ") "
        parameters += allowed_job_ids
    rows = connection.execute(
        "SELECT child.job_id AS child_id, parent.job_id AS parent_id, "
        "parent.status AS parent_status FROM jobs child "
        "JOIN job_dependencies d ON d.job_id = child.job_id "
        "JOIN jobs parent ON parent.job_id = d.depends_on_job_id "
        "WHERE child.status = ? AND parent.status IN (?, ?) "
        f"{scope_sql}"
        "ORDER BY child.job_id, parent.job_id",
        parameters,
    ).fetchall()
    failures: dict[str, list[str]] = {}
    for row in rows:
        failures.setdefault(row["child_id"], []).append(
            f"{row['parent_id']}={row['parent_status']}"
        )
    for child_id, details in failures.items():
        child = _job_from_row(_job_row(connection, child_id))
        _transition_job_in_transaction(
            connection,
            child,
            target=JobStatus.BLOCKED_HUMAN,
            updated_at=now,
            error_code="DEPENDENCY_TERMINAL",
            error_detail="terminal dependencies: " + ", ".join(details),
        )


# --------------------------------------------------------------------------- #
# AutomationStore.
# --------------------------------------------------------------------------- #
def _compact_terminal_narrative(
    connection: sqlite3.Connection,
    scope: tuple[str, ...],
    pin: FinalArtifactPin,
    compacted_at: str,
    *,
    write: bool,
) -> TerminalCompactionResult | None:
    """Derive and validate all AUTO facts in the caller's transaction."""
    placeholders = ",".join("?" for _ in scope)
    if not write and connection.execute(
        f"SELECT 1 FROM attempts WHERE job_id IN ({placeholders}) "
        "AND instr(result_json,?) > 0 LIMIT 1",
        scope + (f'"schema_version":"{TERMINAL_RECEIPT_SCHEMA}"',),
    ).fetchone() is None:
        # The normal path avoids decoding large bodies in its no-op preflight.
        return None
    attempt_rows = connection.execute(
        f"SELECT {_ATTEMPT_COLS} FROM attempts WHERE job_id IN ({placeholders}) "
        "ORDER BY job_id,attempt_no,attempt_id", scope,
    ).fetchall()
    parsed = []
    for row in attempt_rows:
        result = None
        if row["result_json"] is not None:
            try:
                result = HandlerResult.from_dict(json.loads(row["result_json"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise IntegrityViolationError("terminal attempt result is invalid") from exc
        parsed.append((row, result))
    markers = [result for _, result in parsed if result is not None and is_terminal_receipt(result.result)]
    if not write and not markers:
        return None

    jobs = [_job_from_row(_job_row(connection, job_id)) for job_id in scope]
    jobs_by_id = {job.job_id: job for job in jobs}
    kinds = {job.job_type: job for job in jobs}
    if set(kinds) != {"source.narrative_select", "source.narrative_summarize", "source.narrative_verify"}:
        raise IntegrityViolationError("scope is not one canonical narrative DAG")
    if any(job.status is not JobStatus.SUCCEEDED for job in jobs):
        raise IntegrityViolationError("narrative DAG is not fully succeeded")
    event_ids = {job.created_from_event_id for job in jobs}
    if len(event_ids) != 1:
        raise IntegrityViolationError("narrative jobs belong to different events")
    event_id = jobs[0].created_from_event_id
    event_row = connection.execute(f"SELECT {_EVENT_COLS} FROM events WHERE event_id=?", (event_id,)).fetchone()
    if event_row is None:
        raise IntegrityViolationError("terminal narrative event is missing")
    event = _event_from_row(event_row)
    if (event.event_type, event.subject_type) != ("source.revision_registered", "source_revision") or any(
        (job.input_hash, job.policy_version, job.subject_type, job.subject_id) !=
        (event.input_hash, event.policy_version, event.subject_type, event.subject_id) for job in jobs
    ):
        raise IntegrityViolationError("terminal narrative event/input pins differ")
    payload = json.loads(event.payload_json)
    source = payload.get("source_ref", {}) if isinstance(payload, dict) else {}
    if not isinstance(source, dict):
        raise IntegrityViolationError("terminal event source is invalid")
    if (source.get("document_id"), source.get("source_id"), source.get("content_sha256")) != (
        pin.document_id, pin.source_id, pin.source_sha256
    ):
        raise IntegrityViolationError("terminal event source differs from final artifact")
    members = connection.execute(
        "SELECT run_id,job_id,input_hash,handler_version FROM narrative_run_jobs "
        f"WHERE job_id IN ({placeholders})", scope,
    ).fetchall()
    if len(members) != 3 or len({row["run_id"] for row in members}) != 1:
        raise IntegrityViolationError("terminal narrative scope must belong to one immutable run")
    run_id = members[0]["run_id"]
    run = connection.execute("SELECT * FROM narrative_runs WHERE run_id=?", (run_id,)).fetchone()
    if run is None or any((row["input_hash"], row["handler_version"]) !=
                          (jobs_by_id[row["job_id"]].input_hash,
                           jobs_by_id[row["job_id"]].handler_version)
                          for row in members):
        raise IntegrityViolationError("immutable run job pins differ")

    select = kinds["source.narrative_select"].job_id
    summary = kinds["source.narrative_summarize"].job_id
    verify = kinds["source.narrative_verify"].job_id
    edges = connection.execute(
        f"SELECT job_id,depends_on_job_id,required_status FROM job_dependencies WHERE job_id IN ({placeholders})", scope,
    ).fetchall()
    if {tuple(row) for row in edges} != {(summary, select, "succeeded"), (verify, select, "succeeded"), (verify, summary, "succeeded")}:
        raise IntegrityViolationError("terminal narrative dependency set differs")
    if connection.execute(
        "SELECT 1 FROM job_dependencies d JOIN jobs j ON j.job_id=d.job_id "
        f"WHERE d.depends_on_job_id IN ({placeholders}) AND d.job_id NOT IN ({placeholders}) "
        "AND j.status NOT IN ('succeeded','dead_letter','cancelled') LIMIT 1", scope + scope,
    ).fetchone():
        raise IntegrityViolationError("a nonterminal outside job still needs an intermediate result")
    if any(row["finished_at"] is None or row["outcome"] is None or row["finished_at"] > compacted_at for row in attempt_rows):
        raise IntegrityViolationError("terminal DAG has an unfinished or later attempt")
    latest = {row["job_id"]: (row, result) for row, result in parsed}
    if set(latest) != set(scope) or any(row["outcome"] != "succeeded" or result is None or result.outcome is not HandlerOutcome.SUCCEEDED
                                      for row, result in latest.values()):
        raise IntegrityViolationError("terminal DAG has no latest successful result")
    effects = connection.execute(f"SELECT {_EFFECT_COLS} FROM effects WHERE job_id IN ({placeholders})", scope).fetchall()
    if len(effects) != 1:
        raise IntegrityViolationError("terminal narrative DAG does not have one final effect")
    effect = _effect_from_row(effects[0])
    if (effect.effect_id, effect.job_id, effect.effect_type, effect.target, effect.status,
        effect.intended_after_hash, effect.actual_after_hash) != (
        pin.effect_id, verify, "narrative_bundle.publish",
        f"urn:company-wiki:narrative-bundle:{pin.document_id}:{pin.source_sha256}",
        EffectStatus.VERIFIED, pin.artifact_sha256, pin.artifact_sha256
    ) or effect.verified_at is None:
        raise IntegrityViolationError("final effect is not acknowledged with the pinned hash")
    outbox = connection.execute(f"SELECT {_OUTBOX_COLS} FROM outbox WHERE effect_id=?", (pin.effect_id,)).fetchall()
    if len(outbox) != 1 or outbox[0]["status"] != "delivered" or outbox[0]["lease_token"] is not None or outbox[0]["lease_until"] is not None:
        raise IntegrityViolationError("final outbox is not delivered")

    before = sum(len(row["result_json"].encode("utf-8")) for row, result in parsed if result is not None)
    changes = []
    for row, result in parsed:
        if result is None:
            continue
        if is_terminal_receipt(result.result):
            receipt = result.result
            if (dict(receipt.get("final_artifact", {})), receipt.get("run_id"), receipt.get("event_id"),
                receipt.get("input_hash"), receipt.get("job_id"), receipt.get("attempt_id")) != (
                pin.to_dict(), run_id, event_id, event.input_hash, row["job_id"], row["attempt_id"]
            ):
                raise IntegrityViolationError("compacted result is bound to a different final artifact or DAG")
            continue
        if row["job_id"] == verify and row["outcome"] == "succeeded":
            if len(result.effects) != 1 or result.effects[0].effect_id != pin.effect_id:
                raise IntegrityViolationError("verify attempt did not emit the final effect")
            data = canonical_json(result.to_dict()["result"]).encode("utf-8")
            if len(data) != pin.byte_size or hashlib.sha256(data).hexdigest() != pin.artifact_sha256:
                raise IntegrityViolationError("verify result bytes differ from the final artifact")
            versions = result.result.get("versions", {})
            if versions.get("prompt") not in (None, run["prompt_version"]) or versions.get("model") not in (None, run["model_id"]):
                raise IntegrityViolationError("final model/prompt differs from the immutable run")
        original = row["result_json"].encode("utf-8")
        receipt = {"schema_version": TERMINAL_RECEIPT_SCHEMA, "final_artifact": pin.to_dict(),
                   "run_id": run_id, "event_id": event_id, "input_hash": event.input_hash,
                   "job_id": row["job_id"], "attempt_id": row["attempt_id"],
                   "original_result_sha256": hashlib.sha256(original).hexdigest(),
                   "original_result_bytes": len(original), "compacted_at": compacted_at}
        # The outer envelope retains metrics, outcome, error and logical effect IDs.
        value = result.to_dict()
        value["result"] = receipt
        changes.append((row["attempt_id"], canonical_json(value)))
    if markers and changes:
        raise IntegrityViolationError("terminal compaction markers are incomplete")
    if not changes:
        return TerminalCompactionResult(scope, 0, before, before, True)
    if not write:
        return None
    for attempt_id, payload in changes:
        connection.execute("UPDATE attempts SET result_json=? WHERE attempt_id=?", (payload, attempt_id))
    after = sum(len(payload.encode("utf-8")) for _, payload in changes)
    return TerminalCompactionResult(scope, len(changes), before, after)


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

    # -- Runtime gate ----------------------------------------------------- #

    def read_runtime_gate(self) -> RuntimeGate:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT desired_state, control_generation, updated_at "
                "FROM runtime_gate WHERE singleton_id = 1"
            ).fetchone()
            if row is None:
                return RuntimeGate(
                    RuntimeState.PAUSED, 1, "1970-01-01T00:00:00Z"
                )
            try:
                return _runtime_gate_from_row(row)
            except (TypeError, ValueError):
                return RuntimeGate(
                    RuntimeState.PAUSED, 1, "1970-01-01T00:00:00Z"
                )
        finally:
            conn.close()

    def set_runtime_gate(
        self, desired_state: RuntimeState, *, updated_at: str,
        expected_generation: int | None = None,
    ) -> RuntimeGate:
        if not isinstance(desired_state, RuntimeState):
            raise TypeError("desired_state must be RuntimeState")
        RuntimeGate(desired_state, 1, updated_at)
        if expected_generation is not None and (type(expected_generation) is not int or expected_generation < 1):
            raise ValueError("expected_generation must be a positive integer")

        def _op(conn):
            row = conn.execute(
                "SELECT desired_state, control_generation, updated_at "
                "FROM runtime_gate WHERE singleton_id = 1"
            ).fetchone()
            if row is None:
                raise RuntimeGateClosedError("runtime gate row is missing")
            current = _runtime_gate_from_row(row)
            if expected_generation is not None and current.control_generation != expected_generation:
                raise ConcurrentUpdateError("runtime gate generation changed")
            if current.desired_state is desired_state:
                return current
            if updated_at < current.updated_at:
                raise IntegrityViolationError("runtime gate updated_at must not regress")
            generation = current.control_generation + 1
            changed = conn.execute(
                "UPDATE runtime_gate SET desired_state = ?, "
                "control_generation = ?, updated_at = ? WHERE singleton_id = 1 "
                "AND control_generation = ?",
                (
                    desired_state.value,
                    generation,
                    updated_at,
                    current.control_generation,
                ),
            )
            if changed.rowcount != 1:
                raise ConcurrentUpdateError("runtime gate generation changed")
            return RuntimeGate(desired_state, generation, updated_at)

        return self._write_transaction(_op)

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

    def read_execution_snapshot(
        self, claimed: ClaimedWork, *, now: str
    ) -> ExecutionSnapshot:
        """Read event, claim and direct dependency results from one DB view."""
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            try:
                result = load_execution_snapshot(conn, claimed, now=now)
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

    def materialize_dag(
        self,
        event: Event,
        dag: MaterializedDAG,
    ) -> DAGPutResult:
        """Persist one deterministic DAG and all dependency edges atomically."""

        if not isinstance(event, Event) or not isinstance(dag, MaterializedDAG):
            raise TypeError("event and dag must use automation model types")

        def _op(conn):
            try:
                return write_materialized_dag(conn, event, dag)
            except DAGConflictError as exc:
                raise IdempotencyConflictError(str(exc)) from exc
            except DAGEventNotFoundError as exc:
                raise RecordNotFoundError(str(exc)) from exc
            except DAGIntegrityError as exc:
                raise IntegrityViolationError(str(exc)) from exc

        return self._write_transaction(_op)

    # -- Attempt CRUD ------------------------------------------------------ #

    def put_attempt(self, value: Attempt) -> PutResult[Attempt]:
        def _op(conn):
            try:
                conn.execute(
                    "INSERT INTO attempts (attempt_id, job_id, attempt_no, "
                    "worker_id, lease_token, lease_until, started_at, "
                    "heartbeat_at, finished_at, outcome, result_json, "
                    "error_code, error_detail, runtime_generation) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        value.attempt_id, value.job_id, value.attempt_no,
                        value.worker_id, value.lease_token, value.lease_until,
                        value.started_at, value.heartbeat_at, value.finished_at,
                        value.outcome.value if value.outcome is not None else None,
                        value.result_json, value.error_code, value.error_detail,
                        value.runtime_generation,
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

    # -- Atomic worker operations ---------------------------------------- #

    def claim_next_ready(
        self,
        *,
        worker_id: str,
        attempt_id: str,
        lease_token: str,
        now: str,
        lease_until: str,
        expected_generation: int,
        allowed_job_types: tuple[str, ...] | None = None,
        allowed_job_ids: tuple[str, ...] | None = None,
    ) -> ClaimedWork | None:
        allowed_job_ids = normalize_id_scope(allowed_job_ids, name="allowed_job_ids")
        if allowed_job_ids == ():
            return None
        if allowed_job_types is not None and not allowed_job_types:
            return None

        def _op(conn):
            gate = _enabled_gate(conn, expected_generation)
            type_sql = ""
            params: list[object] = [JobStatus.READY.value, now]
            if allowed_job_types is not None:
                placeholders = ",".join("?" for _ in allowed_job_types)
                type_sql = f" AND j.job_type IN ({placeholders})"
                params.extend(allowed_job_types)
            if allowed_job_ids is not None:
                placeholders = ",".join("?" for _ in allowed_job_ids)
                type_sql += f" AND j.job_id IN ({placeholders})"
                params.extend(allowed_job_ids)
            row = conn.execute(
                f"SELECT {_JOB_COLS.replace('job_id', 'j.job_id', 1)} FROM jobs j "
                "WHERE j.status = ? AND j.not_before <= ?"
                f"{type_sql} "
                "AND NOT EXISTS ("
                "SELECT 1 FROM job_dependencies d JOIN jobs parent "
                "ON parent.job_id = d.depends_on_job_id "
                "WHERE d.job_id = j.job_id AND (parent.status != d.required_status "
                "OR NOT EXISTS (SELECT 1 FROM attempts a "
                "WHERE a.job_id = parent.job_id AND a.outcome = 'succeeded' "
                "AND a.result_json IS NOT NULL))) "
                "ORDER BY j.priority DESC, j.created_at, j.job_id LIMIT 1",
                tuple(params),
            ).fetchone()
            if row is None:
                return None
            job = _job_from_row(row)
            next_attempt = _latest_attempt_no(conn, job.job_id) + 1
            attempt = Attempt(
                attempt_id=attempt_id,
                job_id=job.job_id,
                attempt_no=next_attempt,
                worker_id=worker_id,
                lease_token=lease_token,
                lease_until=lease_until,
                started_at=now,
                heartbeat_at=now,
                finished_at=None,
                outcome=None,
                result_json=None,
                error_code=None,
                error_detail=None,
                runtime_generation=gate.control_generation,
            )
            leased = _transition_job_in_transaction(
                conn, job, target=JobStatus.LEASED, updated_at=now
            )
            try:
                conn.execute(
                    "INSERT INTO attempts (attempt_id, job_id, attempt_no, "
                    "worker_id, lease_token, lease_until, started_at, heartbeat_at, "
                    "finished_at, outcome, result_json, error_code, error_detail, "
                    "runtime_generation) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        attempt.attempt_id,
                        attempt.job_id,
                        attempt.attempt_no,
                        attempt.worker_id,
                        attempt.lease_token,
                        attempt.lease_until,
                        attempt.started_at,
                        attempt.heartbeat_at,
                        None,
                        None,
                        None,
                        None,
                        None,
                        attempt.runtime_generation,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise IntegrityViolationError(f"attempt claim conflict: {exc}") from exc
            running = _transition_job_in_transaction(
                conn, leased, target=JobStatus.RUNNING, updated_at=now
            )
            return ClaimedWork(job=running, attempt=attempt)

        return self._write_transaction(_op)

    def heartbeat_attempt(
        self,
        *,
        attempt_id: str,
        lease_token: str,
        runtime_generation: int,
        now: str,
        lease_until: str,
    ) -> Attempt:
        def _op(conn):
            attempt, _job = _require_active_attempt(
                conn,
                attempt_id=attempt_id,
                lease_token=lease_token,
                runtime_generation=runtime_generation,
                now=now,
            )
            if lease_until < now or lease_until < attempt.lease_until:
                raise IntegrityViolationError("heartbeat must extend the active lease")
            changed = conn.execute(
                "UPDATE attempts SET heartbeat_at = ?, lease_until = ? "
                "WHERE attempt_id = ? AND lease_token = ? AND finished_at IS NULL",
                (now, lease_until, attempt_id, lease_token),
            )
            if changed.rowcount != 1:
                raise LeaseLostError("attempt changed during heartbeat")
            return _attempt_from_row(_attempt_row(conn, attempt_id))

        return self._write_transaction(_op)

    def finish_attempt(
        self,
        *,
        attempt_id: str,
        lease_token: str,
        runtime_generation: int,
        finished_at: str,
        result: HandlerResult,
        retry_not_before: str | None = None,
        outbox_not_before: str | None = None,
    ) -> Attempt:
        if not isinstance(result, HandlerResult):
            raise TypeError("result must be HandlerResult")

        def _op(conn):
            attempt, job = _require_active_attempt(
                conn,
                attempt_id=attempt_id,
                lease_token=lease_token,
                runtime_generation=runtime_generation,
                now=finished_at,
            )
            _validate_result_effects(result, job.job_id)
            target = _finish_target(result, has_effects=bool(result.effects))
            _update_finished_attempt(
                conn, attempt, finished_at=finished_at, result=result
            )
            _transition_finished_job(
                conn,
                job,
                target=target,
                finished_at=finished_at,
                retry_not_before=retry_not_before,
                result=result,
            )
            publication_due = outbox_not_before or finished_at
            for effect in result.effects:
                _insert_effect(conn, effect)
                _insert_outbox(conn, effect, not_before=publication_due)
            return _attempt_from_row(_attempt_row(conn, attempt_id))

        return self._write_transaction(_op)

    def promote_ready_jobs(
        self, *, now: str, allowed_job_ids: tuple[str, ...] | None = None,
    ) -> tuple[str, ...]:
        allowed_job_ids = normalize_id_scope(allowed_job_ids, name="allowed_job_ids")
        if allowed_job_ids == ():
            return ()
        def _op(conn):
            _block_terminal_dependencies(conn, now=now, allowed_job_ids=allowed_job_ids)
            scope_sql = ""
            parameters: tuple[object, ...] = (JobStatus.PLANNED.value, JobStatus.RETRY_WAIT.value, now)
            if allowed_job_ids is not None:
                scope_sql = "AND j.job_id IN (" + ",".join("?" for _ in allowed_job_ids) + ") "
                parameters += allowed_job_ids
            rows = conn.execute(
                f"SELECT {_JOB_COLS.replace('job_id', 'j.job_id', 1)} FROM jobs j "
                "WHERE j.status IN (?, ?) AND j.not_before <= ? "
                f"{scope_sql}"
                "AND NOT EXISTS (SELECT 1 FROM job_dependencies d JOIN jobs parent "
                "ON parent.job_id = d.depends_on_job_id "
                "WHERE d.job_id = j.job_id AND (parent.status != d.required_status "
                "OR NOT EXISTS (SELECT 1 FROM attempts a WHERE a.job_id = parent.job_id "
                "AND a.outcome = 'succeeded' AND a.result_json IS NOT NULL))) "
                "ORDER BY j.priority DESC, j.created_at, j.job_id",
                parameters,
            ).fetchall()
            promoted: list[str] = []
            for row in rows:
                job = _job_from_row(row)
                _transition_job_in_transaction(
                    conn, job, target=JobStatus.READY, updated_at=now
                )
                promoted.append(job.job_id)
            return tuple(promoted)

        return self._write_transaction(_op)

    def reap_expired_attempts(
        self, *, now: str, allowed_job_ids: tuple[str, ...] | None = None,
    ) -> tuple[str, ...]:
        allowed_job_ids = normalize_id_scope(allowed_job_ids, name="allowed_job_ids")
        if allowed_job_ids == ():
            return ()
        require_utc_timestamp(now)
        def _op(conn):
            gate_row = conn.execute(
                "SELECT desired_state,control_generation,updated_at FROM runtime_gate WHERE singleton_id=1"
            ).fetchone()
            if gate_row is None:
                raise RuntimeGateClosedError("runtime gate row is missing")
            generation = _runtime_gate_from_row(gate_row).control_generation
            scope_sql = ""
            parameters: tuple[object, ...] = (now, generation, JobStatus.RUNNING.value)
            if allowed_job_ids is not None:
                scope_sql = "AND j.job_id IN (" + ",".join("?" for _ in allowed_job_ids) + ") "
                parameters += allowed_job_ids
            rows = conn.execute(
                f"SELECT {_ATTEMPT_COLS_A} "
                "FROM attempts a JOIN jobs j ON j.job_id = a.job_id "
                "WHERE a.finished_at IS NULL AND (a.lease_until < ? OR a.runtime_generation != ?) "
                "AND j.status = ? AND a.attempt_no = (SELECT MAX(a2.attempt_no) "
                "FROM attempts a2 WHERE a2.job_id = a.job_id) "
                f"{scope_sql}"
                "ORDER BY a.job_id",
                parameters,
            ).fetchall()
            reaped: list[str] = []
            for row in rows:
                attempt = _attempt_from_row(row)
                job = _job_from_row(_job_row(conn, attempt.job_id))
                if now < attempt.started_at:
                    raise IntegrityViolationError("attempt reaping time precedes its start")
                obsolete = attempt.runtime_generation != generation
                error_code = "RUNTIME_GENERATION_CHANGED" if obsolete else "LEASE_EXPIRED"
                error_detail = "worker runtime generation changed" if obsolete else "worker lease expired"
                exhausted = attempt.attempt_no >= job.max_attempts
                outcome = (
                    HandlerOutcome.TERMINAL_FAILURE
                    if exhausted
                    else HandlerOutcome.RETRYABLE
                )
                conn.execute(
                    "UPDATE attempts SET finished_at = ?, outcome = ?, "
                    "error_code = ?, error_detail = ? "
                    "WHERE attempt_id = ? AND finished_at IS NULL",
                    (now, outcome.value, error_code, error_detail, attempt.attempt_id),
                )
                target = JobStatus.DEAD_LETTER if exhausted else JobStatus.RETRY_WAIT
                _transition_job_in_transaction(
                    conn,
                    job,
                    target=target,
                    updated_at=now,
                    not_before=None if exhausted else now,
                    error_code=error_code,
                    error_detail=error_detail,
                )
                reaped.append(attempt.attempt_id)
            return tuple(reaped)

        return self._write_transaction(_op)

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

    def result_for_effect(self, effect_id: str) -> HandlerResult:
        """Return the single successful attempt result that emitted an effect."""
        effect = self.get_effect(effect_id)
        if effect is None:
            raise RecordNotFoundError(f"effect {effect_id!r} not found")

        matches: list[HandlerResult] = []
        for attempt in self.list_attempts(effect.job_id):
            if attempt.result_json is None:
                continue
            try:
                result = HandlerResult.from_dict(json.loads(attempt.result_json))
            except (KeyError, TypeError, ValueError) as exc:
                raise IntegrityViolationError(
                    f"attempt result for effect {effect_id!r} is invalid"
                ) from exc
            emitted = [item for item in result.effects if item.effect_id == effect_id]
            if not emitted:
                continue
            if is_terminal_receipt(result.result):
                raise TerminalResultCompactedError(
                    f"effect {effect_id!r} has a terminal receipt; read its exact final artifact"
                )
            if result.outcome is not HandlerOutcome.SUCCEEDED or len(emitted) != 1:
                raise IntegrityViolationError(
                    f"attempt result for effect {effect_id!r} is inconsistent"
                )
            original_effect = emitted[0]
            immutable_fields = (
                "effect_id",
                "effect_key",
                "job_id",
                "effect_type",
                "target",
                "before_hash",
                "intended_after_hash",
                "created_at",
            )
            if any(
                getattr(original_effect, name) != getattr(effect, name)
                for name in immutable_fields
            ) or (
                original_effect.status
                not in {EffectStatus.PLANNED, EffectStatus.PENDING}
                or original_effect.actual_after_hash is not None
                or original_effect.verified_at is not None
            ):
                raise IntegrityViolationError(
                    f"attempt result does not match stored effect {effect_id!r}"
                )
            if (
                effect.status is EffectStatus.VERIFIED
                and (
                    effect.actual_after_hash != effect.intended_after_hash
                    or effect.verified_at is None
                )
            ):
                raise IntegrityViolationError(
                    f"verified effect {effect_id!r} has an invalid result hash"
                )
            matches.append(result)

        if len(matches) != 1:
            raise IntegrityViolationError(
                f"expected one attempt result for effect {effect_id!r}; found {len(matches)}"
            )
        return matches[0]

    def compact_terminal_narrative_jobs(
        self, *, job_ids: tuple[str, ...], final_artifact: FinalArtifactPin, compacted_at: str,
    ) -> TerminalCompactionResult:
        """Replace terminal intermediate bodies, after the application proves visibility.

        This AUTO-only transaction cannot independently inspect Catalog bytes.
        ``terminal_receipts`` owns that proof and its short catalog lock.
        """
        scope = terminal_job_scope(job_ids)
        if not scope:
            return TerminalCompactionResult((), 0, 0, 0)
        if not isinstance(final_artifact, FinalArtifactPin):
            raise TypeError("final_artifact must be FinalArtifactPin")
        require_utc_timestamp(compacted_at)
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            repeat = _compact_terminal_narrative(connection, scope, final_artifact, compacted_at, write=False)
        finally:
            connection.rollback()
            connection.close()
        if repeat is not None:
            return repeat
        result = self._write_transaction(lambda conn: _compact_terminal_narrative(
            conn, scope, final_artifact, compacted_at, write=True,
        ))
        assert result is not None
        return result

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

    def effect_ids_for_jobs(
        self, allowed_job_ids: tuple[str, ...], *, effect_type: str,
    ) -> tuple[str, ...]:
        """Map a batch to effect IDs in one read, without catalog/AUTO coupling."""
        scope = normalize_id_scope(allowed_job_ids, name="allowed_job_ids")
        if scope is None:
            raise TypeError("allowed_job_ids must be a tuple")
        if not isinstance(effect_type, str) or not effect_type or effect_type.strip() != effect_type:
            raise ValueError("effect_type must be a non-empty name")
        if not scope:
            return ()
        placeholders = ",".join("?" for _ in scope)
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT effect_id FROM effects WHERE effect_type=? "
                f"AND job_id IN ({placeholders}) ORDER BY created_at, effect_id",
                (effect_type,) + scope,
            ).fetchall()
            return tuple(row["effect_id"] for row in rows)
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
                f"SELECT {_OUTBOX_COLS} FROM outbox WHERE outbox_id = ?",
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
                    f"SELECT {_OUTBOX_COLS} FROM outbox WHERE status = ? "
                    "ORDER BY not_before LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {_OUTBOX_COLS} FROM outbox "
                    "ORDER BY not_before LIMIT ?",
                    (limit,),
                ).fetchall()
            return tuple(dict(r) for r in rows)
        finally:
            conn.close()

    def claim_next_outbox(
        self,
        *,
        worker_id: str,
        lease_token: str,
        now: str,
        lease_until: str,
        expected_generation: int,
        allowed_effect_types: tuple[str, ...] | None = None,
        allowed_job_ids: tuple[str, ...] | None = None,
    ) -> OutboxLease | None:
        allowed_job_ids = normalize_id_scope(allowed_job_ids, name="allowed_job_ids")
        if allowed_job_ids == ():
            return None
        if not worker_id or not lease_token:
            raise ValueError("worker_id and lease_token must not be empty")
        if lease_until < now:
            raise ValueError("outbox lease_until must not be before now")
        if allowed_effect_types is not None:
            allowed_effect_types = tuple(dict.fromkeys(allowed_effect_types))
            if not allowed_effect_types or any(
                not isinstance(value, str) or not value or value.strip() != value
                for value in allowed_effect_types
            ):
                raise ValueError("allowed_effect_types must contain non-empty names")

        def _op(conn):
            gate = _enabled_gate(conn, expected_generation)
            statement = (
                f"SELECT {_OUTBOX_COLS_O} FROM outbox o "
                "JOIN effects e ON e.effect_id = o.effect_id "
                "JOIN jobs j ON j.job_id = e.job_id "
                "WHERE ((o.status = 'pending' AND o.not_before <= ?) "
                "OR (o.status = 'leased' AND o.lease_until <= ?)) "
                "AND e.status IN ('planned', 'pending') AND j.status = 'verifying' "
            )
            parameters: tuple[object, ...] = (now, now)
            if allowed_effect_types is not None:
                placeholders = ",".join("?" for _ in allowed_effect_types)
                statement += f"AND e.effect_type IN ({placeholders}) "
                parameters += allowed_effect_types
            if allowed_job_ids is not None:
                placeholders = ",".join("?" for _ in allowed_job_ids)
                statement += f"AND j.job_id IN ({placeholders}) "
                parameters += allowed_job_ids
            statement += (
                "ORDER BY CASE WHEN o.status = 'leased' THEN o.lease_until "
                "ELSE o.not_before END, o.outbox_id LIMIT 1"
            )
            row = conn.execute(statement, parameters).fetchone()
            if row is None:
                return None
            changed = conn.execute(
                "UPDATE outbox SET status = 'leased', lease_token = ?, "
                "lease_until = ? WHERE outbox_id = ? AND "
                "(status = 'pending' OR "
                "(status = 'leased' AND lease_until <= ?))",
                (lease_token, lease_until, row["outbox_id"], now),
            )
            if changed.rowcount != 1:
                raise ConcurrentUpdateError("outbox entry changed during claim")
            return OutboxLease(
                outbox_id=row["outbox_id"],
                effect_id=row["effect_id"],
                payload_json=row["payload_json"],
                attempt_count=row["attempt_count"],
                lease_token=lease_token,
                lease_until=lease_until,
                runtime_generation=gate.control_generation,
            )

        return self._write_transaction(_op)

    def ack_outbox(
        self,
        *,
        outbox_id: str,
        lease_token: str,
        runtime_generation: int,
        verified_at: str,
        actual_after_hash: str,
    ) -> Job:
        require_sha256(actual_after_hash, field_name="actual_after_hash")

        def _op(conn):
            row = _require_outbox_lease(
                conn,
                outbox_id=outbox_id,
                lease_token=lease_token,
                runtime_generation=runtime_generation,
                now=verified_at,
            )
            effect_row = conn.execute(
                f"SELECT {_EFFECT_COLS} FROM effects WHERE effect_id = ?",
                (row["effect_id"],),
            ).fetchone()
            if effect_row is None:
                raise IntegrityViolationError("outbox effect is missing")
            effect = _effect_from_row(effect_row)
            if effect.status not in {EffectStatus.PLANNED, EffectStatus.PENDING}:
                raise LeaseLostError(f"effect is already {effect.status.value}")
            if (
                effect.intended_after_hash is not None
                and effect.intended_after_hash != actual_after_hash
            ):
                raise IntegrityViolationError(
                    "actual_after_hash does not match intended_after_hash"
                )
            job = _job_from_row(_job_row(conn, effect.job_id))
            if job.status is not JobStatus.VERIFYING:
                raise LeaseLostError(f"job is {job.status.value}, not verifying")
            conn.execute(
                "UPDATE effects SET actual_after_hash = ?, status = ?, "
                "verified_at = ? WHERE effect_id = ?",
                (
                    actual_after_hash,
                    EffectStatus.VERIFIED.value,
                    verified_at,
                    effect.effect_id,
                ),
            )
            conn.execute(
                "UPDATE outbox SET status = 'delivered', lease_token = NULL, "
                "lease_until = NULL, last_error = NULL WHERE outbox_id = ?",
                (outbox_id,),
            )
            remaining = conn.execute(
                "SELECT COUNT(*) FROM outbox o JOIN effects e "
                "ON e.effect_id = o.effect_id WHERE e.job_id = ? "
                "AND o.status != 'delivered'",
                (job.job_id,),
            ).fetchone()[0]
            if remaining:
                return _job_from_row(_job_row(conn, job.job_id))
            return _transition_job_in_transaction(
                conn,
                job,
                target=JobStatus.SUCCEEDED,
                updated_at=verified_at,
            )

        return self._write_transaction(_op)

    def retry_outbox(
        self,
        *,
        outbox_id: str,
        lease_token: str,
        runtime_generation: int,
        now: str,
        not_before: str,
        error: str,
        max_attempts: int,
    ) -> dict:
        if type(max_attempts) is not int or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")

        def _op(conn):
            row = _require_outbox_lease(
                conn,
                outbox_id=outbox_id,
                lease_token=lease_token,
                runtime_generation=runtime_generation,
                now=now,
            )
            count = row["attempt_count"] + 1
            exhausted = count >= max_attempts
            status = "failed" if exhausted else "pending"
            conn.execute(
                "UPDATE outbox SET status = ?, attempt_count = ?, not_before = ?, "
                "lease_token = NULL, lease_until = NULL, last_error = ? "
                "WHERE outbox_id = ?",
                (status, count, not_before, error, outbox_id),
            )
            if exhausted:
                effect_row = conn.execute(
                    f"SELECT {_EFFECT_COLS} FROM effects WHERE effect_id = ?",
                    (row["effect_id"],),
                ).fetchone()
                if effect_row is None:
                    raise IntegrityViolationError("outbox effect is missing")
                effect = _effect_from_row(effect_row)
                conn.execute(
                    "UPDATE effects SET status = ? WHERE effect_id = ?",
                    (EffectStatus.FAILED.value, effect.effect_id),
                )
                job = _job_from_row(_job_row(conn, effect.job_id))
                _transition_job_in_transaction(
                    conn,
                    job,
                    target=JobStatus.DEAD_LETTER,
                    updated_at=now,
                    error_code="OUTBOX_FAILED",
                    error_detail=error,
                )
            return dict(_outbox_row(conn, outbox_id))

        return self._write_transaction(_op)


__all__ = [
    "AutomationStore",
    "PutResult",
    "DAGPutResult",
    "AutomationStoreError",
    "InvalidStorePathError",
    "StoreBusyError",
    "IntegrityViolationError",
    "TerminalResultCompactedError",
    "IdempotencyConflictError",
    "RecordNotFoundError",
    "ConcurrentUpdateError",
    "CorruptRecordError",
    "RuntimeGateClosedError",
    "RuntimeGenerationError",
    "LeaseLostError",
]
