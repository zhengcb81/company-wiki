"""Immutable narrative runs and conservative attempt accounting in the AUTO DB.

No provider call, automatic reservation expiry, CSV meter or body is stored here.
Admission and accounting use the existing database transaction/lease boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Callable, TypeVar

from company_wiki._id_scope import normalize_id_scope

from . import migrations
from .models import (RuntimeGate, RuntimeState, canonical_json_hash,
                     require_canonical_json, require_sha256, require_utc_timestamp)
from .store import (
    ConcurrentUpdateError, StoreBusyError, _read_runtime_gate_in_transaction,
    _require_active_attempt, _set_runtime_gate_in_transaction,
)


_MAX_INT = (1 << 63) - 1
T = TypeVar("T")


class NarrativeRunError(RuntimeError):
    code = "narrative_run_error"


class RunConflictError(NarrativeRunError):
    code = "narrative_run_conflict"


class ReservationConflictError(NarrativeRunError):
    code = "reservation_conflict"


class RunBudgetExceededError(NarrativeRunError):
    code = "run_budget_exceeded"


class RunScopeError(NarrativeRunError):
    code = "run_scope_mismatch"


class RunOwnershipError(NarrativeRunError):
    code = "run_ownership_conflict"


def _name(value: str, name: str) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{name} must be non-empty unpadded text")


def _integer(value: int, name: str) -> None:
    if type(value) is not int or not 0 <= value <= _MAX_INT:
        raise ValueError(f"{name} must be a nonnegative SQLite integer")


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        _integer(self.input_tokens, "input_tokens")
        _integer(self.output_tokens, "output_tokens")
        _integer(self.total_tokens, "total_tokens")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    input_hash: str
    scope_sha256: str
    model_id: str
    prompt_version: str
    pricing_version: str
    input_micro_usd_per_million_tokens: int
    output_micro_usd_per_million_tokens: int
    max_tokens: int
    max_micro_usd: int
    max_output_bytes: int
    state: str
    block_reason: str | None
    created_at: str
    updated_at: str
    job_ids: tuple[str, ...]
    last_runtime_generation: int | None = None
    binding_json: str | None = None

    def __post_init__(self) -> None:
        try:
            for name in (
                "input_micro_usd_per_million_tokens", "output_micro_usd_per_million_tokens",
                "max_tokens", "max_micro_usd", "max_output_bytes",
            ):
                _integer(getattr(self, name), name)
        except ValueError as exc:
            raise NarrativeRunError("invalid stored run accounting") from exc

    @property
    def blocked(self) -> bool:
        return self.state == "blocked"


@dataclass(frozen=True)
class ReservationRecord:
    attempt_id: str
    run_id: str
    job_id: str
    request_sha256: str
    input_tokens_bound: int
    max_output_tokens: int
    output_bytes_bound: int
    reserved_micro_usd: int
    usage_status: str
    input_tokens: int | None
    output_tokens: int | None
    estimated_micro_usd: int | None
    response_sha256: str | None
    error_code: str | None
    output_bytes: int | None
    output_sha256: str | None
    reserved_at: str
    usage_settled_at: str | None
    output_settled_at: str | None

    def __post_init__(self) -> None:
        try:
            for name in (
                "input_tokens_bound", "max_output_tokens", "output_bytes_bound",
                "reserved_micro_usd",
            ):
                _integer(getattr(self, name), name)
            for name in ("input_tokens", "output_tokens", "estimated_micro_usd", "output_bytes"):
                value = getattr(self, name)
                if value is not None:
                    _integer(value, name)
            if self.usage_status not in {"reserved", "unknown", "known"}:
                raise ValueError("invalid usage status")
            if self.usage_status == "known" and any(
                value is None for value in (self.input_tokens, self.output_tokens, self.estimated_micro_usd)
            ):
                raise ValueError("known usage lacks actual accounting")
        except ValueError as exc:
            raise NarrativeRunError("invalid stored reservation accounting") from exc

    @property
    def reserved_tokens(self) -> int:
        return self.input_tokens_bound + self.max_output_tokens

    @property
    def charged_tokens(self) -> int:
        if self.usage_status == "known":
            assert self.input_tokens is not None and self.output_tokens is not None
            return self.input_tokens + self.output_tokens
        return self.reserved_tokens

    @property
    def charged_micro_usd(self) -> int:
        return (
            self.reserved_micro_usd
            if self.estimated_micro_usd is None
            else self.estimated_micro_usd
        )

    @property
    def reserved_output_bytes(self) -> int:
        return self.output_bytes_bound

    @property
    def charged_output_bytes(self) -> int:
        return (
            self.output_bytes_bound if self.output_bytes is None else self.output_bytes
        )


@dataclass(frozen=True)
class ReservationAdmission:
    record: ReservationRecord
    created: bool
    may_send_http: bool


@dataclass(frozen=True)
class RunBudgetSnapshot:
    run_id: str
    charged_tokens: int
    charged_micro_usd: int
    charged_output_bytes: int
    unknown_reservations: int
    unsettled_reservations: int


def _run(connection: sqlite3.Connection, run_id: str) -> RunRecord | None:
    row = connection.execute(
        "SELECT * FROM narrative_runs WHERE run_id=?", (run_id,)
    ).fetchone()
    if row is None:
        return None
    jobs = connection.execute(
        "SELECT job_id FROM narrative_run_jobs WHERE run_id=? ORDER BY job_id",
        (run_id,),
    ).fetchall()
    return RunRecord(**dict(row), job_ids=tuple(job["job_id"] for job in jobs))


def _required_run(connection: sqlite3.Connection, run_id: str) -> RunRecord:
    run = _run(connection, run_id)
    if run is None:
        raise RunScopeError(f"run {run_id!r} does not exist")
    return run


def _reservation(
    connection: sqlite3.Connection, run_id: str, attempt_id: str
) -> ReservationRecord | None:
    row = connection.execute(
        "SELECT * FROM narrative_model_reservations WHERE run_id=? AND attempt_id=?",
        (run_id, attempt_id),
    ).fetchone()
    return ReservationRecord(**dict(row)) if row is not None else None


def _required_reservation(
    connection: sqlite3.Connection, run_id: str, attempt_id: str
) -> ReservationRecord:
    record = _reservation(connection, run_id, attempt_id)
    if record is None:
        raise RunScopeError("attempt has no reservation in this run")
    return record


def _budget(connection: sqlite3.Connection, run_id: str) -> RunBudgetSnapshot:
    rows = connection.execute(
        "SELECT * FROM narrative_model_reservations WHERE run_id=?",
        (run_id,),
    ).fetchall()
    records = [ReservationRecord(**dict(row)) for row in rows]
    # Validate this run's ledger before arithmetic; SQLite would silently coerce
    # malformed text in an addition. Python also preserves exact large totals.
    # Admission still holds the same BEGIN IMMEDIATE transaction.
    return RunBudgetSnapshot(
        run_id=run_id,
        charged_tokens=sum(record.charged_tokens for record in records),
        charged_micro_usd=sum(record.charged_micro_usd for record in records),
        charged_output_bytes=sum(record.charged_output_bytes for record in records),
        unknown_reservations=sum(record.usage_status == "unknown" for record in records),
        unsettled_reservations=sum(record.usage_status == "reserved" for record in records),
    )


def _price(run: RunRecord, input_tokens: int, output_tokens: int) -> int:
    numerator = (
        input_tokens * run.input_micro_usd_per_million_tokens
        + output_tokens * run.output_micro_usd_per_million_tokens
    )
    price = (numerator + 999_999) // 1_000_000
    _integer(price, "estimated_micro_usd")
    return price


def _block(connection: sqlite3.Connection, run_id: str, reason: str, now: str) -> None:
    connection.execute(
        "UPDATE narrative_runs SET state='blocked',block_reason=?,updated_at=? WHERE run_id=? AND state='open'",
        (reason, now, run_id),
    )


class NarrativeRunStore:
    """Read an initialized current AUTO database; never initialize or migrate it."""

    def __init__(self, db_path: Path) -> None:
        report = migrations.inspect_schema(db_path)
        if report.user_version != migrations.SCHEMA_VERSION:
            raise NarrativeRunError(
                "run store requires an explicitly migrated current AUTO database"
            )
        self.db_path = db_path

    def _read(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        connection = migrations._open_readonly_connection(self.db_path)
        try:
            return operation(connection)
        finally:
            connection.close()

    def _write(self, operation: Callable[[sqlite3.Connection], T]) -> T:
        connection = migrations._open_connection(self.db_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                result = operation(connection)
            except BaseException:
                connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")
            return result
        except sqlite3.OperationalError as exc:
            if "database is locked" in str(exc).lower():
                raise StoreBusyError("AUTO run accounting database is busy") from exc
            raise
        finally:
            connection.close()

    def get_run(self, run_id: str) -> RunRecord | None:
        return self._read(lambda connection: _run(connection, run_id))

    def job_bindings(self, run_id: str) -> dict[str, tuple[str, str]]:
        """Read the immutable execution membership captured on first creation."""
        def read(connection):
            return {row["job_id"]: (row["input_hash"], row["handler_version"])
                    for row in connection.execute(
                        "SELECT job_id,input_hash,handler_version FROM narrative_run_jobs WHERE run_id=?",
                        (run_id,),
                    )}
        return self._read(read)

    def activate_run(
        self, run_id: str, *, expected_generation: int, updated_at: str,
    ) -> RuntimeGate:
        """Bind and fence this run atomically; the coordinator holds its OS mutex.

        Creation is not ownership. An enabled generation can only be recovered
        by its recorded run, including a parent failure before the first claim.
        A recovery advances the generation so old attempts cannot finish.
        """
        _name(run_id, "run_id")
        require_utc_timestamp(updated_at)
        if type(expected_generation) is not int or expected_generation < 1:
            raise ValueError("expected_generation must be a positive integer")

        def write(connection):
            current = _read_runtime_gate_in_transaction(connection)
            if current.control_generation != expected_generation:
                raise ConcurrentUpdateError("runtime gate generation changed")
            run = _required_run(connection, run_id)
            if (current.desired_state is RuntimeState.ENABLED
                    and run.last_runtime_generation != current.control_generation):
                raise RunOwnershipError("enabled runtime generation belongs to another or unknown run")
            gate = _set_runtime_gate_in_transaction(
                connection, RuntimeState.ENABLED, updated_at=updated_at,
                expected_generation=expected_generation, advance_generation=True,
            )
            connection.execute(
                "UPDATE narrative_runs SET last_runtime_generation=?,updated_at=? WHERE run_id=?",
                (gate.control_generation, updated_at, run_id),
            )
            return gate

        return self._write(write)

    def run_for_job(self, job_id: str) -> RunRecord | None:
        def read(connection):
            row = connection.execute(
                "SELECT run_id FROM narrative_run_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            return _run(connection, row["run_id"]) if row else None

        return self._read(read)

    def get_reservation(self, run_id: str, attempt_id: str) -> ReservationRecord | None:
        return self._read(
            lambda connection: _reservation(connection, run_id, attempt_id)
        )

    def reservations_for_run(self, run_id: str) -> tuple[ReservationRecord, ...]:
        def read(connection):
            _required_run(connection, run_id)
            rows = connection.execute(
                "SELECT * FROM narrative_model_reservations WHERE run_id=? ORDER BY attempt_id",
                (run_id,),
            ).fetchall()
            return tuple(ReservationRecord(**dict(row)) for row in rows)

        return self._read(read)

    def settle_finished_attempt_reservations(
        self, *, run_id: str, settled_at: str,
    ) -> tuple[str, ...]:
        """Mark finished attempts without a receipt unknown, keeping their charge.

        A reserved model request may have reached the provider before a worker
        died. Reconciliation therefore records uncertainty and never refunds
        the original token or cost bounds. One transaction makes retry safe if
        the coordinator loses the commit acknowledgement.
        """
        _name(run_id, "run_id")
        require_utc_timestamp(settled_at)

        def write(connection):
            _required_run(connection, run_id)
            rows = connection.execute(
                """SELECT r.attempt_id FROM narrative_model_reservations r
                   JOIN attempts a ON a.attempt_id=r.attempt_id
                   WHERE r.run_id=? AND r.usage_status='reserved'
                     AND a.finished_at IS NOT NULL ORDER BY r.attempt_id""",
                (run_id,),
            ).fetchall()
            settled = []
            for row in rows:
                changed = connection.execute(
                    """UPDATE narrative_model_reservations
                       SET usage_status='unknown',error_code='MODEL_WORKER_LOST',usage_settled_at=?
                       WHERE run_id=? AND attempt_id=? AND usage_status='reserved'
                         AND EXISTS (SELECT 1 FROM attempts a
                                     WHERE a.attempt_id=? AND a.finished_at IS NOT NULL)""",
                    (settled_at, run_id, row["attempt_id"], row["attempt_id"]),
                )
                if changed.rowcount == 1:
                    settled.append(row["attempt_id"])
            return tuple(settled)

        return self._write(write)

    def budget_snapshot(self, run_id: str) -> RunBudgetSnapshot:
        def read(connection):
            _required_run(connection, run_id)
            return _budget(connection, run_id)

        return self._read(read)

    def create_run(
        self,
        *,
        run_id: str,
        input_hash: str,
        job_ids: tuple[str, ...],
        model_id: str,
        prompt_version: str,
        pricing_version: str,
        input_micro_usd_per_million_tokens: int,
        output_micro_usd_per_million_tokens: int,
        max_tokens: int,
        max_micro_usd: int,
        max_output_bytes: int,
        created_at: str,
        binding_json: str | None = None,
    ) -> RunRecord:
        for name, value in (
            ("run_id", run_id),
            ("model_id", model_id),
            ("prompt_version", prompt_version),
            ("pricing_version", pricing_version),
        ):
            _name(value, name)
        require_sha256(input_hash, field_name="input_hash")
        require_utc_timestamp(created_at)
        if binding_json is not None:
            require_canonical_json(binding_json)
            if len(binding_json.encode("utf-8")) > 262144:
                raise ValueError("narrative run binding exceeds its byte limit")
        scope = normalize_id_scope(job_ids, name="job_ids")
        if scope is None:
            raise TypeError("job_ids must be a tuple")
        scope = tuple(sorted(scope))
        values = dict(
            run_id=run_id,
            input_hash=input_hash,
            scope_sha256=canonical_json_hash(list(scope)),
            model_id=model_id,
            prompt_version=prompt_version,
            pricing_version=pricing_version,
            input_micro_usd_per_million_tokens=input_micro_usd_per_million_tokens,
            output_micro_usd_per_million_tokens=output_micro_usd_per_million_tokens,
            max_tokens=max_tokens,
            max_micro_usd=max_micro_usd,
            max_output_bytes=max_output_bytes,
            binding_json=binding_json,
        )
        for name, cap_value in (
            ("input_micro_usd_per_million_tokens", input_micro_usd_per_million_tokens),
            (
                "output_micro_usd_per_million_tokens",
                output_micro_usd_per_million_tokens,
            ),
            ("max_tokens", max_tokens),
            ("max_micro_usd", max_micro_usd),
            ("max_output_bytes", max_output_bytes),
        ):
            _integer(cap_value, name)

        def write(connection):
            existing = _run(connection, run_id)
            if existing is not None:
                if existing.job_ids != scope or any(
                    getattr(existing, name) != value for name, value in values.items()
                ):
                    raise RunConflictError(
                        "run identity, scope, pricing or limits differ"
                    )
                return existing
            jobs = []
            if scope:
                placeholders = ",".join("?" for _ in scope)
                jobs = connection.execute(
                    f"SELECT job_id,input_hash,handler_version FROM jobs WHERE job_id IN ({placeholders})",
                    scope,
                ).fetchall()
                if len(jobs) != len(scope):
                    raise RunScopeError("run scope contains a missing job")
                if connection.execute(
                    f"SELECT 1 FROM narrative_run_jobs WHERE job_id IN ({placeholders}) LIMIT 1",
                    scope,
                ).fetchone():
                    raise RunConflictError(
                        "a job already belongs to another budget run"
                    )
            columns = tuple(values)
            connection.execute(
                f"INSERT INTO narrative_runs ({','.join(columns)},state,created_at,updated_at) VALUES ({','.join('?' for _ in columns)},'open',?,?)",
                tuple(values.values()) + (created_at, created_at),
            )
            for job in jobs:
                connection.execute(
                    "INSERT INTO narrative_run_jobs (run_id,job_id,input_hash,handler_version) VALUES (?,?,?,?)",
                    (run_id, job["job_id"], job["input_hash"], job["handler_version"]),
                )
            return _required_run(connection, run_id)

        return self._write(write)

    def reserve_model_attempt(
        self,
        *,
        run_id: str,
        job_id: str,
        attempt_id: str,
        lease_token: str,
        runtime_generation: int,
        request_sha256: str,
        model_id: str,
        prompt_version: str,
        pricing_version: str,
        input_tokens_bound: int,
        max_output_tokens: int,
        output_bytes_bound: int,
        now: str,
    ) -> ReservationAdmission:
        require_sha256(request_sha256, field_name="request_sha256")
        require_utc_timestamp(now)
        for name, value in (
            ("input_tokens_bound", input_tokens_bound),
            ("max_output_tokens", max_output_tokens),
            ("output_bytes_bound", output_bytes_bound),
        ):
            _integer(value, name)
        _integer(input_tokens_bound + max_output_tokens, "reserved_tokens")

        def write(connection):
            run = _required_run(connection, run_id)
            if (model_id, prompt_version, pricing_version) != (
                run.model_id,
                run.prompt_version,
                run.pricing_version,
            ):
                raise RunConflictError(
                    "model, prompt or pricing differs from the immutable run"
                )
            membership = connection.execute(
                "SELECT input_hash,handler_version FROM narrative_run_jobs WHERE run_id=? AND job_id=?",
                (run_id, job_id),
            ).fetchone()
            if membership is None:
                raise RunScopeError("job is outside the immutable run scope")
            attempt = connection.execute(
                "SELECT job_id,lease_token,runtime_generation FROM attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if attempt is None or attempt["job_id"] != job_id:
                raise RunScopeError("attempt and scoped job differ")
            if (
                attempt["lease_token"] != lease_token
                or attempt["runtime_generation"] != runtime_generation
            ):
                from .store import LeaseLostError

                raise LeaseLostError("reservation attempt token or generation differs")
            cost = _price(run, input_tokens_bound, max_output_tokens)
            existing = _reservation(connection, run_id, attempt_id)
            if existing is not None:
                if (
                    existing.job_id,
                    existing.request_sha256,
                    existing.input_tokens_bound,
                    existing.max_output_tokens,
                    existing.output_bytes_bound,
                    existing.reserved_micro_usd,
                ) != (
                    job_id,
                    request_sha256,
                    input_tokens_bound,
                    max_output_tokens,
                    output_bytes_bound,
                    cost,
                ):
                    raise ReservationConflictError(
                        "attempt reservation differs from its original request or bounds"
                    )
                return ReservationAdmission(existing, False, False)
            _, job = _require_active_attempt(
                connection,
                attempt_id=attempt_id,
                lease_token=lease_token,
                runtime_generation=runtime_generation,
                now=now,
            )
            if (job.input_hash, job.handler_version) != (
                membership["input_hash"],
                membership["handler_version"],
            ):
                raise RunConflictError("scoped job input or handler version changed")
            budget = _budget(connection, run_id)
            if (
                run.blocked
                or budget.charged_tokens + input_tokens_bound + max_output_tokens
                > run.max_tokens
                or budget.charged_micro_usd + cost > run.max_micro_usd
                or budget.charged_output_bytes + output_bytes_bound
                > run.max_output_bytes
            ):
                raise RunBudgetExceededError(
                    "run is blocked or this request exceeds its remaining budget"
                )
            connection.execute(
                """INSERT INTO narrative_model_reservations
                (attempt_id,run_id,job_id,request_sha256,input_tokens_bound,max_output_tokens,output_bytes_bound,reserved_micro_usd,usage_status,reserved_at)
                VALUES (?,?,?,?,?,?,?,?,'reserved',?)""",
                (
                    attempt_id,
                    run_id,
                    job_id,
                    request_sha256,
                    input_tokens_bound,
                    max_output_tokens,
                    output_bytes_bound,
                    cost,
                    now,
                ),
            )
            return ReservationAdmission(
                _required_reservation(connection, run_id, attempt_id), True, True
            )

        return self._write(write)

    def settle_model_usage(
        self,
        *,
        run_id: str,
        attempt_id: str,
        usage: ModelUsage | None,
        response_sha256: str | None,
        error_code: str | None,
        settled_at: str,
    ) -> ReservationRecord:
        require_utc_timestamp(settled_at)
        if usage is not None and not isinstance(usage, ModelUsage):
            raise TypeError("usage must be ModelUsage or None")
        if response_sha256 is not None:
            require_sha256(response_sha256, field_name="response_sha256")
        if error_code is not None:
            _name(error_code, "error_code")

        def write(connection):
            run = _required_run(connection, run_id)
            record = _required_reservation(connection, run_id, attempt_id)
            status = "known" if usage is not None else "unknown"
            counts = (
                (
                    usage.input_tokens,
                    usage.output_tokens,
                    _price(run, usage.input_tokens, usage.output_tokens),
                )
                if usage
                else (None, None, None)
            )
            values = (status, *counts, response_sha256, error_code)
            previous = (
                record.usage_status,
                record.input_tokens,
                record.output_tokens,
                record.estimated_micro_usd,
                record.response_sha256,
                record.error_code,
            )
            if record.usage_status == "known" or (
                record.usage_status == "unknown" and status == "unknown"
            ):
                if previous != values:
                    raise ReservationConflictError(
                        "attempt usage receipt conflicts with the durable receipt"
                    )
                return record
            connection.execute(
                "UPDATE narrative_model_reservations SET usage_status=?,input_tokens=?,output_tokens=?,estimated_micro_usd=?,response_sha256=?,error_code=?,usage_settled_at=? WHERE run_id=? AND attempt_id=?",
                values + (settled_at, run_id, attempt_id),
            )
            settled = _required_reservation(connection, run_id, attempt_id)
            if usage is not None and (
                usage.input_tokens > record.input_tokens_bound
                or usage.output_tokens > record.max_output_tokens
                or settled.charged_micro_usd > record.reserved_micro_usd
            ):
                _block(
                    connection, run_id, "MODEL_USAGE_EXCEEDS_RESERVATION", settled_at
                )
            return settled

        return self._write(write)

    def settle_output(
        self,
        *,
        run_id: str,
        attempt_id: str,
        output_bytes: int,
        output_sha256: str | None,
        settled_at: str,
    ) -> ReservationRecord:
        _integer(output_bytes, "output_bytes")
        require_utc_timestamp(settled_at)
        if output_sha256 is not None:
            require_sha256(output_sha256, field_name="output_sha256")
        if (output_bytes > 0) != (output_sha256 is not None):
            raise ValueError(
                "positive final output bytes require a hash; zero output must have no hash"
            )

        def write(connection):
            _required_run(connection, run_id)
            record = _required_reservation(connection, run_id, attempt_id)
            if record.output_bytes is not None:
                if (record.output_bytes, record.output_sha256) != (
                    output_bytes,
                    output_sha256,
                ):
                    raise ReservationConflictError(
                        "final output differs from its durable receipt"
                    )
                return record
            connection.execute(
                "UPDATE narrative_model_reservations SET output_bytes=?,output_sha256=?,output_settled_at=? WHERE run_id=? AND attempt_id=?",
                (output_bytes, output_sha256, settled_at, run_id, attempt_id),
            )
            if output_bytes > record.output_bytes_bound:
                _block(
                    connection, run_id, "FINAL_OUTPUT_EXCEEDS_RESERVATION", settled_at
                )
            return _required_reservation(connection, run_id, attempt_id)

        return self._write(write)

    def block_run(self, run_id: str, *, error_code: str, updated_at: str) -> RunRecord:
        _name(error_code, "error_code")
        require_utc_timestamp(updated_at)

        def write(connection):
            _required_run(connection, run_id)
            _block(connection, run_id, error_code, updated_at)
            return _required_run(connection, run_id)

        return self._write(write)


__all__ = [
    "NarrativeRunStore",
    "NarrativeRunError",
    "RunConflictError",
    "RunBudgetExceededError",
    "ReservationConflictError",
    "RunScopeError",
    "RunOwnershipError",
    "ModelUsage",
    "RunRecord",
    "ReservationRecord",
    "ReservationAdmission",
    "RunBudgetSnapshot",
]
