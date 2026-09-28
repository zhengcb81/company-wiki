"""Strict, side-effect-free contracts for the automation control plane.

The types in this module mirror the schema frozen in ``task_plan.md``.  They
perform validation only; persistence, clocks, IDs, leases, and execution are
deliberately outside AUTO-1.
"""

from dataclasses import MISSING, dataclass, fields
from datetime import datetime
from enum import Enum
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, ClassVar, Mapping


UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class JobStatus(str, Enum):
    DETECTED = "detected"
    PLANNED = "planned"
    READY = "ready"
    LEASED = "leased"
    RUNNING = "running"
    VERIFYING = "verifying"
    RETRY_WAIT = "retry_wait"
    BLOCKED_HUMAN = "blocked_human"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"
    SUCCEEDED = "succeeded"


class HandlerOutcome(str, Enum):
    SUCCEEDED = "succeeded"
    RETRYABLE = "retryable"
    BLOCKED_HUMAN = "blocked_human"
    TERMINAL_FAILURE = "terminal_failure"


class RiskClass(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"


class EffectStatus(str, Enum):
    PLANNED = "planned"
    PENDING = "pending"
    APPLIED = "applied"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RuntimeState(str, Enum):
    PAUSED = "paused"
    ENABLED = "enabled"


JOB_STATUS_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.DETECTED: {JobStatus.PLANNED, JobStatus.CANCELLED},
    JobStatus.PLANNED: {JobStatus.READY, JobStatus.BLOCKED_HUMAN, JobStatus.CANCELLED},
    JobStatus.READY: {JobStatus.LEASED, JobStatus.CANCELLED},
    JobStatus.LEASED: {JobStatus.RUNNING, JobStatus.READY},
    JobStatus.RUNNING: {
        JobStatus.VERIFYING,
        JobStatus.RETRY_WAIT,
        JobStatus.BLOCKED_HUMAN,
        JobStatus.DEAD_LETTER,
    },
    JobStatus.VERIFYING: {
        JobStatus.SUCCEEDED,
        JobStatus.RETRY_WAIT,
        JobStatus.BLOCKED_HUMAN,
        JobStatus.DEAD_LETTER,
    },
    JobStatus.RETRY_WAIT: {JobStatus.READY, JobStatus.DEAD_LETTER},
    JobStatus.BLOCKED_HUMAN: {JobStatus.READY, JobStatus.CANCELLED},
    JobStatus.SUCCEEDED: set(),
    JobStatus.DEAD_LETTER: set(),
    JobStatus.CANCELLED: set(),
}


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} contains a non-string object key")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise TypeError(f"{path} contains unsupported JSON type {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize a JSON value deterministically without ASCII escaping."""
    _validate_json_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def require_canonical_json(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("canonical JSON must be text")
    try:
        decoded = json.loads(value, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid canonical JSON: {exc}") from exc
    if canonical_json(decoded) != value:
        raise ValueError("JSON text is not canonical")
    return value


def require_utc_timestamp(value: str) -> str:
    if not isinstance(value, str) or not UTC_TIMESTAMP_RE.fullmatch(value):
        raise ValueError("timestamp must be UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("timestamp must be a valid UTC YYYY-MM-DDTHH:MM:SSZ") from exc
    return value


def require_sha256(value: str, *, field_name: str = "hash") -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase 64-character SHA-256")
    return value


def _require_nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _require_positive_integer(value: int, field_name: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _require_nonnegative_integer(value: int, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _require_optional_text(value: str | None, field_name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{field_name} must be text or null")


def _validate_attempt_times(
    *,
    started_at: str,
    heartbeat_at: str,
    lease_until: str,
    finished_at: str | None,
) -> None:
    for value in (lease_until, started_at, heartbeat_at):
        require_utc_timestamp(value)
    if finished_at is not None:
        require_utc_timestamp(finished_at)
    if heartbeat_at < started_at:
        raise ValueError("heartbeat_at must not be before started_at")
    if lease_until < heartbeat_at:
        raise ValueError("lease_until must not be before heartbeat_at")
    if finished_at is not None and finished_at < started_at:
        raise ValueError("finished_at must not be before started_at")
    if finished_at is not None and heartbeat_at > finished_at:
        raise ValueError("heartbeat_at must not be after finished_at")


def _identity_hash(parts: tuple[str, ...]) -> str:
    for index, part in enumerate(parts):
        _require_nonempty(part, f"key component {index}")
        if "|" in part:
            raise ValueError("key components must not contain the '|' delimiter")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def make_job_key(
    job_type: str,
    subject_type: str,
    subject_id: str,
    input_hash: str,
    policy_version: str,
    handler_version: str,
) -> str:
    return _identity_hash(
        (job_type, subject_type, subject_id, input_hash, policy_version, handler_version)
    )


def make_effect_key(
    effect_type: str,
    target: str,
    action_hash: str,
    projector_version: str,
) -> str:
    return _identity_hash((effect_type, target, action_hash, projector_version))


def validate_job_transition(current: JobStatus, target: JobStatus) -> None:
    if not isinstance(current, JobStatus) or not isinstance(target, JobStatus):
        raise TypeError("job transition endpoints must be JobStatus values")
    if target not in JOB_STATUS_TRANSITIONS[current]:
        raise ValueError(f"illegal job status transition: {current.value} -> {target.value}")


def _to_plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, StrictModel):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _to_plain(item) for key, item in value.items()}
    return value


def _freeze_json(value: Any) -> Any:
    """Recursively freeze a value already proven to be valid JSON."""
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


class StrictModel:
    """Exact-field JSON conversion shared by frozen schema value objects."""

    _enum_fields: ClassVar[dict[str, type[Enum]]] = {}

    @classmethod
    def _prepare_dict(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(data, Mapping):
            raise TypeError(f"{cls.__name__} input must be an object")
        known = {field.name for field in fields(cls)}
        supplied = set(data)
        unknown = supplied - known
        if unknown:
            raise ValueError(f"{cls.__name__} unknown fields: {sorted(unknown)}")
        required = {
            field.name
            for field in fields(cls)
            if field.default is MISSING and field.default_factory is MISSING
        }
        missing = required - supplied
        if missing:
            raise ValueError(f"{cls.__name__} missing fields: {sorted(missing)}")
        prepared = dict(data)
        for name, enum_type in cls._enum_fields.items():
            if name in prepared and prepared[name] is not None and not isinstance(prepared[name], enum_type):
                try:
                    prepared[name] = enum_type(prepared[name])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{name} is not a valid {enum_type.__name__}") from exc
        return prepared

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]):
        return cls(**cls._prepare_dict(data))

    def to_dict(self) -> dict[str, Any]:
        return {field.name: _to_plain(getattr(self, field.name)) for field in fields(self)}


@dataclass(frozen=True)
class Event(StrictModel):
    event_id: str
    event_type: str
    subject_type: str
    subject_id: str
    input_hash: str
    payload_json: str
    policy_version: str
    occurred_at: str
    observed_at: str

    def __post_init__(self) -> None:
        for name in ("event_id", "event_type", "subject_type", "subject_id", "policy_version"):
            _require_nonempty(getattr(self, name), name)
        require_sha256(self.input_hash, field_name="input_hash")
        require_canonical_json(self.payload_json)
        require_utc_timestamp(self.occurred_at)
        require_utc_timestamp(self.observed_at)
        if self.observed_at < self.occurred_at:
            raise ValueError("observed_at must not be before occurred_at")


@dataclass(frozen=True)
class Job(StrictModel):
    job_id: str
    job_key: str
    job_type: str
    subject_type: str
    subject_id: str
    input_hash: str
    policy_version: str
    handler_version: str
    risk_class: RiskClass
    status: JobStatus
    priority: int
    not_before: str
    max_attempts: int
    created_from_event_id: str
    created_at: str
    updated_at: str
    last_error_code: str | None
    last_error_detail: str | None

    _enum_fields: ClassVar[dict[str, type[Enum]]] = {
        "risk_class": RiskClass,
        "status": JobStatus,
    }

    def __post_init__(self) -> None:
        for name in (
            "job_id", "job_type", "subject_type", "subject_id", "policy_version",
            "handler_version", "created_from_event_id",
        ):
            _require_nonempty(getattr(self, name), name)
        require_sha256(self.input_hash, field_name="input_hash")
        require_sha256(self.job_key, field_name="job_key")
        if self.job_key != make_job_key(
            self.job_type, self.subject_type, self.subject_id, self.input_hash,
            self.policy_version, self.handler_version,
        ):
            raise ValueError("job_key does not match the frozen identity formula")
        if not isinstance(self.risk_class, RiskClass) or not isinstance(self.status, JobStatus):
            raise TypeError("risk_class and status must be enum values")
        if type(self.priority) is not int:
            raise TypeError("priority must be an integer, not bool or coercible text")
        _require_positive_integer(self.max_attempts, "max_attempts")
        for value in (self.not_before, self.created_at, self.updated_at):
            require_utc_timestamp(value)
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be before created_at")
        for name in ("last_error_code", "last_error_detail"):
            _require_optional_text(getattr(self, name), name)


@dataclass(frozen=True)
class MaterializedDAG(StrictModel):
    """Concrete jobs and dependency edges ready for one atomic store write."""

    jobs: tuple[Job, ...]
    dependencies: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.jobs:
            raise ValueError("materialized DAG must contain at least one job")
        if not all(isinstance(job, Job) for job in self.jobs):
            raise TypeError("jobs must contain Job values")
        job_ids = tuple(job.job_id for job in self.jobs)
        if len(set(job_ids)) != len(job_ids):
            raise ValueError("materialized DAG job_id values must be unique")
        normalized_edges: list[tuple[str, str]] = []
        for edge in self.dependencies:
            if not isinstance(edge, tuple) or len(edge) != 2:
                raise TypeError("dependency edges must be (job_id, depends_on_job_id)")
            child, parent = edge
            if child not in job_ids or parent not in job_ids:
                raise ValueError("dependency edge references a job outside the DAG")
            if child == parent:
                raise ValueError("self-dependency is not allowed")
            normalized_edges.append(edge)
        if len(set(normalized_edges)) != len(normalized_edges):
            raise ValueError("materialized DAG dependency edges must be unique")


@dataclass(frozen=True)
class Attempt(StrictModel):
    attempt_id: str
    job_id: str
    attempt_no: int
    worker_id: str
    lease_token: str
    lease_until: str
    started_at: str
    heartbeat_at: str
    finished_at: str | None
    outcome: HandlerOutcome | None
    result_json: str | None
    error_code: str | None
    error_detail: str | None
    runtime_generation: int = 0

    _enum_fields: ClassVar[dict[str, type[Enum]]] = {"outcome": HandlerOutcome}

    def __post_init__(self) -> None:
        for name in ("attempt_id", "job_id", "worker_id", "lease_token"):
            _require_nonempty(getattr(self, name), name)
        _require_positive_integer(self.attempt_no, "attempt_no")
        _require_nonnegative_integer(self.runtime_generation, "runtime_generation")
        _validate_attempt_times(
            started_at=self.started_at,
            heartbeat_at=self.heartbeat_at,
            lease_until=self.lease_until,
            finished_at=self.finished_at,
        )
        if self.outcome is not None and not isinstance(self.outcome, HandlerOutcome):
            raise TypeError("outcome must be HandlerOutcome or null")
        if self.result_json is not None:
            require_canonical_json(self.result_json)
        for name in ("error_code", "error_detail"):
            _require_optional_text(getattr(self, name), name)


@dataclass(frozen=True)
class RuntimeGate(StrictModel):
    desired_state: RuntimeState
    control_generation: int
    updated_at: str

    _enum_fields: ClassVar[dict[str, type[Enum]]] = {"desired_state": RuntimeState}

    def __post_init__(self) -> None:
        if not isinstance(self.desired_state, RuntimeState):
            raise TypeError("desired_state must be RuntimeState")
        if type(self.control_generation) is not int or self.control_generation < 1:
            raise ValueError("control_generation must be a positive integer")
        require_utc_timestamp(self.updated_at)


@dataclass(frozen=True)
class ClaimedWork(StrictModel):
    job: Job
    attempt: Attempt

    def __post_init__(self) -> None:
        if not isinstance(self.job, Job) or not isinstance(self.attempt, Attempt):
            raise TypeError("job and attempt must use automation model types")
        if self.job.job_id != self.attempt.job_id:
            raise ValueError("claimed job and attempt must have the same job_id")
        if self.job.status is not JobStatus.RUNNING:
            raise ValueError("claimed job must be RUNNING")


@dataclass(frozen=True)
class OutboxLease(StrictModel):
    outbox_id: str
    effect_id: str
    payload_json: str
    attempt_count: int
    lease_token: str
    lease_until: str
    runtime_generation: int

    def __post_init__(self) -> None:
        for name in ("outbox_id", "effect_id", "lease_token"):
            _require_nonempty(getattr(self, name), name)
        require_canonical_json(self.payload_json)
        if type(self.attempt_count) is not int or self.attempt_count < 0:
            raise ValueError("attempt_count must be a non-negative integer")
        if type(self.runtime_generation) is not int or self.runtime_generation < 1:
            raise ValueError("runtime_generation must be a positive integer")
        require_utc_timestamp(self.lease_until)


@dataclass(frozen=True)
class Approval(StrictModel):
    approval_id: str
    job_id: str
    action_hash: str
    reviewer_principal: str
    reviewer_session_id: str
    role: str
    decision: ApprovalDecision
    decided_at: str
    receipt_hash: str

    _enum_fields: ClassVar[dict[str, type[Enum]]] = {"decision": ApprovalDecision}

    def __post_init__(self) -> None:
        for name in (
            "approval_id", "job_id", "reviewer_principal", "reviewer_session_id", "role",
        ):
            _require_nonempty(getattr(self, name), name)
        require_sha256(self.action_hash, field_name="action_hash")
        require_sha256(self.receipt_hash, field_name="receipt_hash")
        if not isinstance(self.decision, ApprovalDecision):
            raise TypeError("decision must be ApprovalDecision")
        require_utc_timestamp(self.decided_at)


@dataclass(frozen=True)
class Effect(StrictModel):
    effect_id: str
    effect_key: str
    job_id: str
    effect_type: str
    target: str
    before_hash: str | None
    intended_after_hash: str | None
    actual_after_hash: str | None
    status: EffectStatus
    created_at: str
    verified_at: str | None

    _enum_fields: ClassVar[dict[str, type[Enum]]] = {"status": EffectStatus}

    def __post_init__(self) -> None:
        for name in ("effect_id", "job_id", "effect_type", "target"):
            _require_nonempty(getattr(self, name), name)
        require_sha256(self.effect_key, field_name="effect_key")
        for name in ("before_hash", "intended_after_hash", "actual_after_hash"):
            value = getattr(self, name)
            if value is not None:
                require_sha256(value, field_name=name)
        if not isinstance(self.status, EffectStatus):
            raise TypeError("status must be EffectStatus")
        require_utc_timestamp(self.created_at)
        if self.verified_at is not None:
            require_utc_timestamp(self.verified_at)
            if self.verified_at < self.created_at:
                raise ValueError("verified_at must not be before created_at")


@dataclass(frozen=True)
class ArtifactRef(StrictModel):
    path: str
    sha256: str

    def __post_init__(self) -> None:
        _require_nonempty(self.path, "path")
        require_sha256(self.sha256, field_name="sha256")


@dataclass(frozen=True)
class HandlerMetrics(StrictModel):
    tokens: int
    cost_usd: float
    duration_ms: int

    def __post_init__(self) -> None:
        if type(self.tokens) is not int or self.tokens < 0:
            raise ValueError("tokens must be a non-negative integer")
        if isinstance(self.cost_usd, bool) or not isinstance(self.cost_usd, (int, float)):
            raise TypeError("cost_usd must be numeric")
        if not math.isfinite(float(self.cost_usd)) or self.cost_usd < 0:
            raise ValueError("cost_usd must be finite and non-negative")
        if type(self.duration_ms) is not int or self.duration_ms < 0:
            raise ValueError("duration_ms must be a non-negative integer")


@dataclass(frozen=True)
class HandlerError(StrictModel):
    code: str
    detail: str

    def __post_init__(self) -> None:
        _require_nonempty(self.code, "code")
        if not isinstance(self.detail, str):
            raise TypeError("detail must be text")


@dataclass(frozen=True)
class HandlerResult(StrictModel):
    outcome: HandlerOutcome
    result: Mapping[str, Any]
    artifacts: tuple[ArtifactRef, ...]
    effects: tuple[Effect, ...]
    metrics: HandlerMetrics
    error: HandlerError | None

    _enum_fields: ClassVar[dict[str, type[Enum]]] = {"outcome": HandlerOutcome}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "HandlerResult":
        prepared = cls._prepare_dict(data)
        if not isinstance(prepared.get("result"), dict):
            raise TypeError("result must be a JSON object")
        if not isinstance(prepared.get("artifacts"), list):
            raise TypeError("artifacts must be a list")
        if not isinstance(prepared.get("effects"), list):
            raise TypeError("effects must be a list")
        prepared["artifacts"] = tuple(ArtifactRef.from_dict(item) for item in prepared["artifacts"])
        prepared["effects"] = tuple(Effect.from_dict(item) for item in prepared["effects"])
        prepared["metrics"] = HandlerMetrics.from_dict(prepared["metrics"])
        if prepared["error"] is not None:
            prepared["error"] = HandlerError.from_dict(prepared["error"])
        return cls(**prepared)

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, HandlerOutcome):
            raise TypeError("outcome must be HandlerOutcome")
        if not isinstance(self.result, dict):
            raise TypeError("result must be a JSON object")
        canonical_json(self.result)
        object.__setattr__(self, "result", _freeze_json(self.result))
        if not all(isinstance(item, ArtifactRef) for item in self.artifacts):
            raise TypeError("artifacts must contain ArtifactRef values")
        if not all(isinstance(item, Effect) for item in self.effects):
            raise TypeError("effects must contain Effect values")
        if not isinstance(self.metrics, HandlerMetrics):
            raise TypeError("metrics must be HandlerMetrics")
        if self.outcome is HandlerOutcome.SUCCEEDED and self.error is not None:
            raise ValueError("succeeded HandlerResult must not contain error")
        if self.outcome is not HandlerOutcome.SUCCEEDED and self.error is None:
            raise ValueError("non-succeeded HandlerResult requires error")
