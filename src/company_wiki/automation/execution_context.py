"""Immutable handler input assembled from one AutomationStore snapshot."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from .execution_snapshot import ExecutionSnapshot
from .models import Attempt, ClaimedWork, Event, HandlerResult, Job
from .narrative_contracts import NarrativeContractError, SourceRevisionEventPayload


_NARRATIVE_DEPENDENCIES = {
    "source.narrative_select": frozenset(),
    "source.narrative_summarize": frozenset({"source.narrative_select"}),
    "source.narrative_verify": frozenset(
        {"source.narrative_select", "source.narrative_summarize"}
    ),
}


class ExecutionContextError(RuntimeError):
    """The snapshot cannot become a valid handler context."""


class ExecutionSnapshotStore(Protocol):
    def read_execution_snapshot(
        self, claimed: ClaimedWork, *, now: str
    ) -> ExecutionSnapshot: ...


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze_json(child) for key, child in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json(child) for child in value)
    return value


@dataclass(frozen=True)
class JobExecutionContext:
    job: Job
    attempt: Attempt
    event: Event
    payload: Mapping[str, Any]
    dependency_results: Mapping[str, HandlerResult]
    source_revision: SourceRevisionEventPayload | None
    _checkpoint: Callable[[], None]

    @classmethod
    def from_snapshot(
        cls,
        snapshot: ExecutionSnapshot,
        *,
        checkpoint: Callable[[], None],
    ) -> "JobExecutionContext":
        _validate_snapshot_identity(snapshot)
        payload = _decode_event_payload(snapshot.event)
        dependencies = _dependency_mapping(snapshot)
        _validate_dependency_types(snapshot.job.job_type, frozenset(dependencies))
        source_revision = _source_revision(snapshot.job, snapshot.event, payload)
        return cls(
            snapshot.job,
            snapshot.attempt,
            snapshot.event,
            _freeze_json(payload),
            MappingProxyType(dependencies),
            source_revision,
            checkpoint,
        )

    def checkpoint(self) -> None:
        self._checkpoint()


def _validate_snapshot_identity(snapshot: ExecutionSnapshot) -> None:
    job = snapshot.job
    event = snapshot.event
    if (
        job.job_id != snapshot.attempt.job_id
        or job.created_from_event_id != event.event_id
        or job.subject_type != event.subject_type
        or job.subject_id != event.subject_id
        or job.input_hash != event.input_hash
        or job.policy_version != event.policy_version
    ):
        raise ExecutionContextError("snapshot job/event/attempt identity differs")


def _decode_event_payload(event: Event) -> dict[str, Any]:
    try:
        value = json.loads(event.payload_json)
    except json.JSONDecodeError as exc:
        raise ExecutionContextError("event payload is not JSON") from exc
    if not isinstance(value, dict):
        raise ExecutionContextError("event payload must be an object")
    return value


def _dependency_mapping(snapshot: ExecutionSnapshot) -> dict[str, HandlerResult]:
    values: dict[str, HandlerResult] = {}
    for dependency in snapshot.dependencies:
        if dependency.job_type in values:
            raise ExecutionContextError(
                "narrative dependencies contain duplicate job types"
            )
        values[dependency.job_type] = dependency.result
    return values


def _validate_dependency_types(job_type: str, actual: frozenset[str]) -> None:
    expected = _NARRATIVE_DEPENDENCIES.get(job_type)
    if expected is not None and actual != expected:
        raise ExecutionContextError(
            f"narrative dependencies differ: expected={sorted(expected)}, "
            f"actual={sorted(actual)}"
        )


def _source_revision(
    job: Job, event: Event, payload: Mapping[str, Any]
) -> SourceRevisionEventPayload | None:
    if job.job_type not in _NARRATIVE_DEPENDENCIES:
        return None
    try:
        parsed = SourceRevisionEventPayload.from_dict(payload)
    except NarrativeContractError as exc:
        raise ExecutionContextError(
            f"source revision payload is invalid: {exc}"
        ) from exc
    if (
        event.event_type != "source.revision_registered"
        or event.subject_type
        != (
            "narrative_subject"
            if parsed.subject.kind == "official_json"
            else "source_revision"
        )
        or event.subject_id != parsed.item_key
        or event.input_hash != parsed.input_hash
    ):
        raise ExecutionContextError(
            "source revision event identity differs from payload"
        )
    return parsed


class ExecutionContextFactory:
    def __init__(self, store: ExecutionSnapshotStore) -> None:
        self._store = store

    def create(
        self,
        claimed: ClaimedWork,
        *,
        now: str,
        checkpoint: Callable[[], None],
    ) -> JobExecutionContext:
        snapshot = self._store.read_execution_snapshot(claimed, now=now)
        return JobExecutionContext.from_snapshot(snapshot, checkpoint=checkpoint)


__all__ = [
    "ExecutionContextError",
    "ExecutionContextFactory",
    "JobExecutionContext",
]
