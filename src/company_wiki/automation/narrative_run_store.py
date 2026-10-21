"""Immutable narrative runs and conservative attempt accounting in the AUTO DB.

No provider call, automatic reservation expiry, CSV meter or body is stored here.
Admission and accounting use the existing database transaction/lease boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
import json
import sqlite3
from typing import Callable, TypeVar

from company_wiki._id_scope import normalize_id_scope

from . import migrations
from .models import (Attempt, HandlerOutcome, HandlerResult, Job, RuntimeGate, RuntimeState, canonical_json, canonical_json_hash,
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


def _job_prompt_versions(binding_json: str | None) -> dict[str, str] | None:
    """Optional immutable model-job prompts; old bindings keep the run default.

    This ledger knows only job IDs, types and accounting. The owner of a run
    binding chooses the actual prompt version; source/model modules are not
    imported or interpreted here.
    """
    if binding_json is None:
        return None
    try:
        binding = json.loads(binding_json)
        if not isinstance(binding, dict) or "job_prompt_versions" not in binding:
            return None
        versions = binding["job_prompt_versions"]
        if not isinstance(versions, dict):
            raise ValueError("job_prompt_versions must be an object")
        for job_id, prompt in versions.items():
            _name(job_id, "job_prompt_versions job_id")
            _name(prompt, "job_prompt_versions prompt")
        return versions
    except (TypeError, ValueError) as exc:
        raise RunConflictError("invalid immutable job prompt binding") from exc


def model_prompt_version(
    binding_json: str | None, *, job_id: str, default_prompt: str,
) -> str:
    """Resolve one frozen model job prompt without database or source reads.

    Admission and terminal compaction must use the same binding. A map that
    exists never falls back for an unbound job; only legacy absent maps use
    the immutable run default.
    """
    versions = _job_prompt_versions(binding_json)
    if versions is None:
        return default_prompt
    if job_id not in versions:
        raise RunScopeError("job has no immutable model prompt binding")
    return versions[job_id]


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
    paid_response_json: str | None = None

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


# ReservationRecord is the public accounting shape. Internal additive columns
# must not widen reads or become unexpected constructor keyword arguments.
_RESERVATION_COLUMNS = ", ".join(field.name for field in fields(ReservationRecord))

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


def _base_generation(run: RunRecord, item_key: str) -> dict | None:
    """Read this item's immutable base settings; never consult current config."""
    if run.binding_json is None:
        return None
    try:
        binding = json.loads(run.binding_json)
        record = binding.get("generation_manifests", {}).get(item_key)
        if record is None:
            if binding.get("execution_versions", {}).get("selector") == "0.9.0":
                raise ValueError("new selector has no bound base generation")
            return None
        if not isinstance(record, dict):
            raise ValueError("invalid generation record")
        if "settings_sha256" in record:
            common = binding["generation_settings"][record["settings_sha256"]]
            source = record["source_inputs"]
            if (not isinstance(common, dict) or not isinstance(source, dict)
                    or canonical_json_hash(common) != record["settings_sha256"]
                    or common.keys() & source.keys()):
                raise ValueError("invalid generation settings")
            manifest = {**common, **source}
            if canonical_json_hash(manifest) != record["generation_sha256"]:
                raise ValueError("invalid generation digest")
        else:
            manifest = record
        if (binding.get("execution_versions", {}).get("selector") == "0.9.0"
                and manifest.get("execution_versions", {}).get("selector") != "0.9.0"):
            raise ValueError("base selector differs from the owning run")
        return manifest
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise RunConflictError("invalid immutable base generation") from exc


def _freeze_select_generation_in_transaction(connection, job, result) -> None:
    """CAS the final content identity beside its select result in one transaction.

    The caller already fenced the owning attempt's lease and runtime generation.
    Legacy unbound handlers and historical selectors retain their old behavior.
    """
    if job.job_type != "source.narrative_select" or result.outcome.value != "succeeded":
        return
    membership = connection.execute(
        "SELECT run_id,final_generation_json FROM narrative_run_jobs WHERE job_id=?",
        (job.job_id,),
    ).fetchone()
    if membership is None:
        return
    run = _required_run(connection, membership["run_id"])
    base = _base_generation(run, job.subject_id)
    if base is None or base.get("execution_versions", {}).get("selector") != "0.9.0":
        return
    from .narrative_contracts import NarrativeSelectResult

    selected = NarrativeSelectResult.from_dict(result.to_dict()["result"])
    if selected.selector.version != "0.9.0" or selected.reading_context is None:
        raise RunConflictError("new selector requires its actual reading context")
    subject_matches = (
        selected.subject.to_dict() == base.get("subject_binding")
        if selected.subject.kind == "official_json"
        else selected.source_ref.to_dict() == base.get("source_ref")
    )
    if (selected.item_key != job.subject_id or not subject_matches
            or selected.source_metadata.to_dict() != base.get("source_metadata")):
        raise RunConflictError("select result differs from its immutable base generation")
    selected_wire = selected.to_dict()
    from .narrative_selection_generation import reading_material_sha256
    final = {**base, "selection_generation": {
        "schema_version": "narrative-selection-generation/1",
        "select_result_sha256": canonical_json_hash(selected_wire),
        "reading_policy_version": selected_wire["reading_context"]["reading_policy_version"],
        "evidence_sha256": canonical_json_hash(selected_wire["evidence_spans"]),
        "material_sha256": reading_material_sha256(selected),
    }}
    dependencies = selected_wire.get("reading_dependencies")
    if dependencies is not None:
        final["reading_dependencies"] = dependencies
        if dependencies.get("status") == "complete":
            digest = dependencies.get("decision_digest")
            require_sha256(digest, field_name="reading_dependencies.decision_digest")
            final["selection_generation"]["decision_digest"] = digest
    encoded = canonical_json(final)
    current = membership["final_generation_json"]
    if current is not None:
        if current != encoded:
            raise RunConflictError("final generation differs from its frozen selection")
        return
    changed = connection.execute(
        "UPDATE narrative_run_jobs SET final_generation_json=? "
        "WHERE job_id=? AND run_id=? AND final_generation_json IS NULL",
        (encoded, job.job_id, membership["run_id"]),
    ).rowcount
    if changed != 1:
        raise RunConflictError("final generation CAS lost its owning row")


def _final_generation_rows(connection, *, run_id: str, item_key: str | None = None):
    run = _required_run(connection, run_id)
    query = (
        "SELECT j.subject_id,j.status,r.final_generation_json FROM narrative_run_jobs r "
        "JOIN jobs j ON j.job_id=r.job_id WHERE r.run_id=? "
        "AND j.job_type='source.narrative_select' AND r.final_generation_json IS NOT NULL"
    )
    parameters: tuple = (run_id,)
    if item_key is not None:
        query += " AND j.subject_id=?"
        parameters += (item_key,)
    values = {}
    for row in connection.execute(query, parameters):
        if row["status"] != "succeeded":
            continue
        try:
            require_canonical_json(row["final_generation_json"])
            final = json.loads(row["final_generation_json"])
            from .narrative_selection_generation import validate_selection_generation
            validate_selection_generation(final)
            base = _base_generation(run, row["subject_id"])
            extra = {"selection_generation"}
            dependencies = final.get("reading_dependencies")
            if dependencies is not None:
                extra.add("reading_dependencies")
            if (base is None
                    or {key: value for key, value in final.items() if key not in extra} != base):
                raise ValueError("final generation differs from its immutable base")
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise RunConflictError("stored final generation is invalid") from exc
        if row["subject_id"] in values:
            raise RunConflictError("multiple frozen selections for one run item")
        values[row["subject_id"]] = final
    return values


def _reservation(
    connection: sqlite3.Connection, run_id: str, attempt_id: str
) -> ReservationRecord | None:
    row = connection.execute(
        f"SELECT {_RESERVATION_COLUMNS} FROM narrative_model_reservations WHERE run_id=? AND attempt_id=?",
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


def _settle_output_in_transaction(
    connection: sqlite3.Connection, *, run_id: str, attempt_id: str,
    output_bytes: int, output_sha256: str | None, settled_at: str,
) -> ReservationRecord:
    """Use the caller's transaction and validated output arguments exactly once."""
    _required_run(connection, run_id)
    record = _required_reservation(connection, run_id, attempt_id)
    if record.output_bytes is not None:
        if (record.output_bytes, record.output_sha256) != (output_bytes, output_sha256):
            raise ReservationConflictError("final output differs from its durable receipt")
        return record
    connection.execute(
        "UPDATE narrative_model_reservations SET output_bytes=?,output_sha256=?,output_settled_at=? WHERE run_id=? AND attempt_id=?",
        (output_bytes, output_sha256, settled_at, run_id, attempt_id),
    )
    if output_bytes > record.output_bytes_bound:
        _block(connection, run_id, "FINAL_OUTPUT_EXCEEDS_RESERVATION", settled_at)
    return _required_reservation(connection, run_id, attempt_id)


def _settle_failed_summary_output_in_transaction(
    connection: sqlite3.Connection, attempt: Attempt, job: Job, result: HandlerResult,
    *, finished_at: str,
) -> None:
    """An owned failed result proves no final artifact, never a free provider call.

    Store already fenced this attempt and writes its result/status in the same
    transaction. Lost/unreported attempts do not pass through this lifecycle rule.
    """
    if (job.job_type != "source.narrative_summarize"
            or result.outcome is HandlerOutcome.SUCCEEDED or result.artifacts or result.effects):
        return
    row = connection.execute(
        "SELECT run_id,job_id FROM narrative_model_reservations WHERE attempt_id=?",
        (attempt.attempt_id,),
    ).fetchone()
    if row is None:
        return  # Unmetered historical handlers have no output slot to settle.
    if row["job_id"] != job.job_id or attempt.job_id != job.job_id:
        raise RunScopeError("failed output reservation and owning attempt differ")
    require_utc_timestamp(finished_at)
    _settle_output_in_transaction(connection, run_id=row["run_id"], attempt_id=attempt.attempt_id,
        output_bytes=0, output_sha256=None, settled_at=finished_at)


def _budget(
    connection: sqlite3.Connection, run_id: str, *,
    output_reservation: tuple[str, int] | None = None,
) -> RunBudgetSnapshot:
    rows = connection.execute(
        f"SELECT {_RESERVATION_COLUMNS} FROM narrative_model_reservations WHERE run_id=?",
        (run_id,),
    ).fetchall()
    records = [ReservationRecord(**dict(row)) for row in rows]
    # Each summarize job publishes one final artifact. A retry consumes another
    # provider call, but it replaces the same final-output slot. Keep every
    # attempt's uncertain bytes/usage intact; physical scratch/object growth is
    # measured separately by the batch storage guard.
    output_slots: dict[str, int] = {}
    for record in records:
        output_slots[record.job_id] = max(
            output_slots.get(record.job_id, 0), record.charged_output_bytes,
        )
    if output_reservation is not None:
        job_id, output_bound = output_reservation
        output_slots[job_id] = max(output_slots.get(job_id, 0), output_bound)
    # Validate this run's ledger before arithmetic; SQLite would silently coerce
    # malformed text in an addition. Python also preserves exact large totals.
    # Admission still holds the same BEGIN IMMEDIATE transaction.
    return RunBudgetSnapshot(
        run_id=run_id,
        charged_tokens=sum(record.charged_tokens for record in records),
        charged_micro_usd=sum(record.charged_micro_usd for record in records),
        charged_output_bytes=sum(output_slots.values()),
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

    @classmethod
    def read_existing_run(cls, db_path: Path, run_id: str) -> RunRecord | None:
        """Inspect the prior run before the coordinator's additive upgrade.

        The v5 run/binding/accounting schema is unchanged by v6's nullable
        selection column. Pure preparation therefore reads that history
        without migrating or re-signing it. AutomationStore remains the sole
        migration owner before any job or accounting mutation.
        """
        report = migrations.inspect_schema(db_path)
        if report.user_version not in {5, 6, migrations.SCHEMA_VERSION}:
            raise NarrativeRunError("run history requires an explicitly migrated AUTO database")
        connection = migrations._open_readonly_connection(db_path)
        try:
            return _run(connection, run_id)
        finally:
            connection.close()

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

    def final_generations(self, run_id: str) -> dict[str, dict]:
        """Return completed select identities from the existing run membership."""
        def read(connection):
            _required_run(connection, run_id)
            return _final_generation_rows(connection, run_id=run_id)
        return self._read(read)

    def final_generation_for_job(self, job_id: str) -> dict | None:
        """Resolve select/summarize/verify through the same run and source item."""
        def read(connection):
            row = connection.execute(
                "SELECT r.run_id,j.subject_id FROM narrative_run_jobs r "
                "JOIN jobs j ON j.job_id=r.job_id WHERE r.job_id=?", (job_id,),
            ).fetchone()
            if row is None:
                return None
            return _final_generation_rows(connection, run_id=row["run_id"],
                                          item_key=row["subject_id"]).get(row["subject_id"])
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

    def model_attempts_for_job(self, *, run_id: str, job_id: str) -> tuple[ReservationRecord, ...]:
        """Read one immutable operation's paid history, never a cross-run cache."""
        def read(connection):
            _required_run(connection, run_id)
            member = connection.execute("SELECT input_hash,handler_version FROM narrative_run_jobs WHERE run_id=? AND job_id=?",
                                        (run_id, job_id)).fetchone()
            if member is None:
                raise RunScopeError("job is outside this narrative run")
            job = connection.execute("SELECT input_hash,handler_version FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if job is None or tuple(member) != tuple(job):
                raise RunConflictError("paid recovery frozen job identity differs")
            return tuple(ReservationRecord(**dict(row)) for row in connection.execute(
                f"SELECT {_RESERVATION_COLUMNS} FROM narrative_model_reservations WHERE run_id=? AND job_id=? ORDER BY reserved_at,attempt_id",
                (run_id, job_id)).fetchall())
        return self._read(read)

    def attach_paid_response(self, *, run_id: str, attempt_id: str, lease_token: str,
                             runtime_generation: int, request_sha256: str,
                             paid_response_json: str, recorded_at: str) -> ReservationRecord:
        """Attach original paid evidence, even when its worker can no longer publish.

        Token/generation identify the original reservation. This method does not
        finish a job or create an effect and never grants a current lease.
        """
        from .narrative_paid_response import PaidResponsePin
        require_utc_timestamp(recorded_at)
        pin = PaidResponsePin.from_json(paid_response_json)
        def write(connection):
            run = _required_run(connection, run_id)
            record = _required_reservation(connection, run_id, attempt_id)
            attempt = connection.execute("SELECT * FROM attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
            if (attempt is None or attempt["job_id"] != record.job_id
                    or attempt["lease_token"] != lease_token or attempt["runtime_generation"] != runtime_generation):
                raise RunScopeError("paid response original attempt identity differs")
            prompt = model_prompt_version(run.binding_json, job_id=record.job_id, default_prompt=run.prompt_version)
            if (pin.request_sha256 != request_sha256 or record.request_sha256 != request_sha256
                    or pin.model_id != run.model_id or pin.prompt_version != prompt):
                raise ReservationConflictError("paid response request identity differs")
            if record.paid_response_json is not None:
                if record.paid_response_json != paid_response_json:
                    raise ReservationConflictError("paid response cannot replace original bytes")
                return record
            connection.execute("UPDATE narrative_model_reservations SET paid_response_json=? WHERE run_id=? AND attempt_id=?",
                               (paid_response_json, run_id, attempt_id))
            return _required_reservation(connection, run_id, attempt_id)
        return self._write(write)

    def reopen_paid_output(self, *, run_id: str, paid_attempt_id: str, current_attempt_id: str,
                           lease_token: str, runtime_generation: int, request_sha256: str,
                           verified_response_sha256: str, now: str) -> ReservationRecord:
        """Re-reserve the same failed output slot after verified paid-byte recovery."""
        from .narrative_paid_response import PaidResponsePin
        require_utc_timestamp(now)
        def write(connection):
            run = _required_run(connection, run_id)
            record = _required_reservation(connection, run_id, paid_attempt_id)
            _, job = _require_active_attempt(connection, attempt_id=current_attempt_id,
                lease_token=lease_token, runtime_generation=runtime_generation, now=now)
            member = connection.execute("SELECT input_hash,handler_version FROM narrative_run_jobs WHERE run_id=? AND job_id=?",
                                        (run_id, job.job_id)).fetchone()
            if (member is None or record.job_id != job.job_id or job.job_type != "source.narrative_summarize"
                    or (member["input_hash"], member["handler_version"]) != (job.input_hash, job.handler_version)):
                raise RunScopeError("paid recovery job binding differs")
            paid_json = record.paid_response_json
            if not isinstance(paid_json, str):
                raise ReservationConflictError("paid response has no pinned bytes")
            pin = PaidResponsePin.from_json(paid_json)
            if (record.request_sha256 != request_sha256 or pin.request_sha256 != request_sha256
                    or pin.body_sha256 != verified_response_sha256):
                raise ReservationConflictError("paid recovery verified byte binding differs")
            if (record.output_bytes != 0 or record.output_sha256 is not None
                    or connection.execute("SELECT 1 FROM effects WHERE job_id=? LIMIT 1", (job.job_id,)).fetchone()
                    or connection.execute("SELECT 1 FROM attempts WHERE job_id=? AND outcome='succeeded' LIMIT 1", (job.job_id,)).fetchone()):
                raise ReservationConflictError("paid recovery cannot reopen an active or successful output")
            budget = _budget(connection, run_id, output_reservation=(job.job_id, record.output_bytes_bound))
            if run.blocked or budget.charged_output_bytes > run.max_output_bytes:
                raise RunBudgetExceededError("paid recovery output exceeds run bound")
            connection.execute("UPDATE narrative_model_reservations SET output_bytes=NULL,output_sha256=NULL,output_settled_at=NULL WHERE run_id=? AND attempt_id=?",
                               (run_id, paid_attempt_id))
            return _required_reservation(connection, run_id, paid_attempt_id)
        return self._write(write)

    def reservations_for_run(self, run_id: str) -> tuple[ReservationRecord, ...]:
        def read(connection):
            _required_run(connection, run_id)
            rows = connection.execute(
                f"SELECT {_RESERVATION_COLUMNS} FROM narrative_model_reservations WHERE run_id=? ORDER BY attempt_id",
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
        job_prompt_versions = _job_prompt_versions(binding_json)
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
                    f"SELECT job_id,input_hash,handler_version,job_type FROM jobs WHERE job_id IN ({placeholders})",
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
            if job_prompt_versions is not None:
                model_job_ids = {
                    job["job_id"] for job in jobs
                    if job["job_type"] == "source.narrative_summarize"
                }
                if set(job_prompt_versions) != model_job_ids:
                    raise RunScopeError(
                        "job prompt binding must exactly cover scoped model jobs"
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
            expected_prompt = model_prompt_version(
                run.binding_json, job_id=job_id, default_prompt=run.prompt_version,
            )
            if (model_id, prompt_version, pricing_version) != (
                run.model_id,
                expected_prompt,
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
            base = _base_generation(run, job.subject_id)
            if (base is not None and base.get("execution_versions", {}).get("selector") == "0.9.0"
                    and not _final_generation_rows(connection, run_id=run_id, item_key=job.subject_id)):
                raise RunConflictError("MODEL_SELECTION_NOT_FROZEN")
            budget = _budget(connection, run_id, output_reservation=(job_id, output_bytes_bound))
            if (
                run.blocked
                or budget.charged_tokens + input_tokens_bound + max_output_tokens
                > run.max_tokens
                or budget.charged_micro_usd + cost > run.max_micro_usd
                or budget.charged_output_bytes > run.max_output_bytes
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

        return self._write(lambda connection: _settle_output_in_transaction(
            connection, run_id=run_id, attempt_id=attempt_id, output_bytes=output_bytes,
            output_sha256=output_sha256, settled_at=settled_at))

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
