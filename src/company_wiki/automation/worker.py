"""Atomic worker orchestration for the automation control plane.

The Worker executes handlers outside SQLite transactions. Claim, completion,
retry state, effects and outbox persistence are delegated to AutomationStore
application operations so a process crash cannot leave a split claim/commit.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from ._clock import Clock, IDGenerator
from .heartbeat import AttemptHeartbeat
from .execution_context import (
    ExecutionContextFactory,
    ExecutionSnapshotStore,
    JobExecutionContext,
)
from .models import (
    Attempt,
    ClaimedWork,
    HandlerError,
    HandlerMetrics,
    HandlerOutcome,
    HandlerResult,
    JobStatus,
    RuntimeGate,
    RuntimeState,
)
from .registry import HandlerRegistry, HandlerSpec
from .retry import classify_outcome, compute_retry_delay


Handler = Callable[[JobExecutionContext], HandlerResult]


class WorkerStore(ExecutionSnapshotStore, Protocol):
    """Small Store surface required by one worker process."""

    def read_runtime_gate(self) -> RuntimeGate: ...

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
    ) -> ClaimedWork | None: ...

    def heartbeat_attempt(
        self,
        *,
        attempt_id: str,
        lease_token: str,
        runtime_generation: int,
        now: str,
        lease_until: str,
    ) -> Attempt: ...

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
    ) -> Attempt: ...

    def reap_expired_attempts(self, *, now: str) -> tuple[str, ...]: ...


class HandlerExecutor:
    """Registry of callable handlers keyed by job_type."""

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, job_type: str, handler: Handler) -> None:
        self._handlers[job_type] = handler

    def execute(
        self, job_type: str, context: JobExecutionContext
    ) -> HandlerResult:
        handler = self._handlers.get(job_type)
        if handler is None:
            raise UnknownHandlerError(f"no handler registered for {job_type}")
        return handler(context)


class UnknownHandlerError(Exception):
    """Raised when no handler is registered for a job_type."""


class Worker:
    """Single-process executor backed by fenced, atomic Store operations."""

    def __init__(
        self,
        store: WorkerStore,
        registry: HandlerRegistry,
        executor: HandlerExecutor,
        *,
        clock: Clock | None = None,
        id_gen: IDGenerator | None = None,
        lease_seconds: int = 300,
        worker_id: str = "local-worker",
        heartbeat_interval_seconds: float | None = None,
        allowed_job_types: tuple[str, ...] | None = None,
        lifecycle_callback: Callable[[str, ClaimedWork], None] | None = None,
        context_factory: ExecutionContextFactory | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._executor = executor
        self._clock = clock or Clock()
        self._id_gen = id_gen or IDGenerator()
        self._lease_seconds = lease_seconds
        self._worker_id = worker_id
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        known = set(registry.known_job_types())
        selected = allowed_job_types or registry.known_job_types()
        unknown = set(selected) - known
        if unknown:
            raise ValueError(f"allowed job types are not registered: {sorted(unknown)}")
        self._allowed_job_types = tuple(sorted(selected))
        self._lifecycle_callback = lifecycle_callback
        self._context_factory = context_factory or ExecutionContextFactory(store)

    def process_one(self) -> bool:
        gate = self._store.read_runtime_gate()
        if gate.desired_state is not RuntimeState.ENABLED:
            return False
        now = self._clock.now()
        attempt_id = self._id_gen.new_id()
        lease_token = hashlib.sha256(
            f"{self._worker_id}|{attempt_id}".encode("utf-8")
        ).hexdigest()
        claimed = self._store.claim_next_ready(
            worker_id=self._worker_id,
            attempt_id=attempt_id,
            lease_token=lease_token,
            now=now,
            lease_until=_add_seconds(now, self._lease_seconds),
            expected_generation=gate.control_generation,
            allowed_job_types=self._allowed_job_types,
        )
        if claimed is None:
            return False
        self._notify("claimed", claimed)
        self._execute_and_finish(claimed)
        return True

    def _execute_and_finish(self, claimed: ClaimedWork) -> None:
        job = claimed.job
        attempt = claimed.attempt
        spec = self._registry.get(job.job_type)
        heartbeat = self._heartbeat(claimed)
        if heartbeat is not None:
            heartbeat.start()
        try:
            try:
                checkpoint = (
                    heartbeat.raise_if_failed if heartbeat is not None else lambda: None
                )
                context = self._context_factory.create(
                    claimed, now=self._clock.now(), checkpoint=checkpoint
                )
                raw_result = self._executor.execute(
                    job.job_type,
                    context,
                )
                result, target = _classify_result(raw_result, spec, attempt.attempt_no)
            except Exception as exc:  # noqa: BLE001 - handler boundary
                result = _handler_exception_result(exc)
                target = JobStatus.DEAD_LETTER
            self._notify("before_finish", claimed)
        finally:
            if heartbeat is not None:
                heartbeat.stop()
        if heartbeat is not None:
            heartbeat.raise_if_failed()
        finished_at = self._clock.now()
        retry_at = None
        if target is JobStatus.RETRY_WAIT:
            retry_at = _add_seconds(
                finished_at,
                compute_retry_delay(attempt.attempt_no, job_id=job.job_id),
            )
        self._store.finish_attempt(
            attempt_id=attempt.attempt_id,
            lease_token=attempt.lease_token,
            runtime_generation=attempt.runtime_generation,
            finished_at=finished_at,
            result=result,
            retry_not_before=retry_at,
            outbox_not_before=finished_at,
        )
        self._notify("attempt_finished", claimed)

    def _heartbeat(self, claimed: ClaimedWork) -> AttemptHeartbeat | None:
        if self._heartbeat_interval_seconds is None:
            return None
        return AttemptHeartbeat(
            self._store,
            claimed,
            interval_seconds=self._heartbeat_interval_seconds,
            lease_seconds=self._lease_seconds,
            clock=self._clock,
        )

    def _notify(self, phase: str, claimed: ClaimedWork) -> None:
        if self._lifecycle_callback is not None:
            self._lifecycle_callback(phase, claimed)

    def reap_expired(self) -> int:
        return len(self._store.reap_expired_attempts(now=self._clock.now()))


def _classify_result(
    result: HandlerResult, spec: HandlerSpec, attempt_no: int
) -> tuple[HandlerResult, JobStatus]:
    error_code = result.error.code if result.error is not None else None
    target, _classified_code = classify_outcome(
        result.outcome,
        error_code,
        spec.retryable_errors,
        spec.human_errors,
        spec.terminal_errors,
        attempt_no,
        spec.default_max_attempts,
    )
    desired = {
        JobStatus.SUCCEEDED: HandlerOutcome.SUCCEEDED,
        JobStatus.RETRY_WAIT: HandlerOutcome.RETRYABLE,
        JobStatus.BLOCKED_HUMAN: HandlerOutcome.BLOCKED_HUMAN,
        JobStatus.DEAD_LETTER: HandlerOutcome.TERMINAL_FAILURE,
    }[target]
    if result.outcome is desired:
        return result, target
    return (
        HandlerResult(
            outcome=desired,
            result=dict(result.result),
            artifacts=result.artifacts,
            effects=result.effects if desired is HandlerOutcome.SUCCEEDED else (),
            metrics=result.metrics,
            error=result.error,
        ),
        target,
    )


def _handler_exception_result(exc: Exception) -> HandlerResult:
    return HandlerResult(
        outcome=HandlerOutcome.TERMINAL_FAILURE,
        result={},
        artifacts=(),
        effects=(),
        metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
        error=HandlerError(code="HANDLER_EXCEPTION", detail=str(exc)),
    )


def _add_seconds(iso_time: str, seconds: float) -> str:
    dt = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    return (dt + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "Clock",
    "IDGenerator",
    "HandlerExecutor",
    "UnknownHandlerError",
    "Worker",
]
