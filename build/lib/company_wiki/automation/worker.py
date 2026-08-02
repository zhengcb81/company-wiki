"""AUTO-4 Worker: claim, lease, execute and commit jobs.

This module depends on ``models``, ``registry``, ``retry`` and the store.
It does not import the legacy scheduler, network, LLM or configuration modules.
Clock and IDGenerator are injectable for deterministic testing.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .models import (
    Attempt,
    HandlerOutcome,
    HandlerResult,
    Job,
    JobStatus,
    canonical_json,
    _to_plain,
)
from .registry import HandlerRegistry
from .retry import classify_outcome, compute_retry_delay


# Re-export from _clock (injectable clock and ID generator).
from ._clock import Clock, IDGenerator


# --------------------------------------------------------------------------- #
# Handler executor interface.
# --------------------------------------------------------------------------- #
class HandlerExecutor:
    """Registry of callable handlers keyed by job_type."""

    def __init__(self) -> None:
        self._handlers: dict[str, object] = {}

    def register(self, job_type: str, handler) -> None:
        self._handlers[job_type] = handler

    def execute(self, job_type: str, input_data: dict) -> HandlerResult:
        handler = self._handlers.get(job_type)
        if handler is None:
            raise UnknownHandlerError(f"no handler registered for {job_type}")
        return handler(input_data)


class UnknownHandlerError(Exception):
    """Raised when no handler is registered for a job_type."""


# --------------------------------------------------------------------------- #
# Worker.
# --------------------------------------------------------------------------- #
class Worker:
    """Single-threaded worker that claims, executes and commits jobs."""

    def __init__(
        self,
        store,
        registry: HandlerRegistry,
        executor: HandlerExecutor,
        *,
        clock: Clock | None = None,
        id_gen: IDGenerator | None = None,
        lease_seconds: int = 300,
        worker_id: str = "local-worker",
    ) -> None:
        self._store = store
        self._registry = registry
        self._executor = executor
        self._clock = clock or Clock()
        self._id_gen = id_gen or IDGenerator()
        self._lease_seconds = lease_seconds
        self._worker_id = worker_id

    def process_one(self) -> bool:
        """Claim and execute one ready job.

        Returns ``True`` if a job was processed, ``False`` if no ready jobs
        were available or all claims failed (another worker won the race).
        """
        now = self._clock.now()
        ready_jobs = self._store.list_jobs(status=JobStatus.READY)
        # Filter by not_before and sort by priority DESC, created_at ASC.
        eligible = [j for j in ready_jobs if j.not_before <= now]
        eligible.sort(key=lambda j: (-j.priority, j.created_at, j.job_id))

        for job in eligible:
            attempt = self._try_claim(job, now)
            if attempt is None:
                continue  # lost race, try next
            return self._execute_and_commit(job, attempt, now)
        return False

    def _try_claim(self, job: Job, now: str) -> Attempt | None:
        """Try to atomically claim a ready job. Returns Attempt or None."""
        self._registry.get(job.job_type)
        lease_until = _add_seconds(now, self._lease_seconds)
        attempt_id = self._id_gen.new_id()
        lease_token = hashlib.sha256(attempt_id.encode()).hexdigest()[:32]

        attempt = Attempt(
            attempt_id=attempt_id,
            job_id=job.job_id,
            attempt_no=self._count_attempts(job.job_id) + 1,
            worker_id=self._worker_id,
            lease_token=lease_token,
            lease_until=lease_until,
            started_at=now,
            heartbeat_at=now,
            finished_at=None,
            outcome=None,
            result_json=None,
            error_code=None,
            error_detail=None,
        )

        try:
            self._store.transition_job(
                job.job_id,
                expected=JobStatus.READY,
                target=JobStatus.LEASED,
                updated_at=now,
            )
            self._store.put_attempt(attempt)
            # Transition to RUNNING immediately after claim.
            self._store.transition_job(
                job.job_id,
                expected=JobStatus.LEASED,
                target=JobStatus.RUNNING,
                updated_at=now,
            )
            return attempt
        except Exception:
            return None  # lost race or error

    def _execute_and_commit(self, job: Job, attempt: Attempt, now: str) -> bool:
        """Execute handler and commit result. Returns True on success."""
        try:
            spec = self._registry.get(job.job_type)
            input_data = {"job_id": job.job_id, "subject_id": job.subject_id}
            result = self._executor.execute(job.job_type, input_data)
            self._commit_success(job, attempt, result, spec, now)
            return True
        except Exception as exc:
            self._commit_failure(job, attempt, str(exc), now)
            return True  # job was processed (failed), not a "no job" signal

    def _commit_success(
        self, job: Job, attempt: Attempt, result, spec, now: str
    ) -> None:
        """Commit a successful handler result."""
        outcome = result.outcome
        next_status, error_code = classify_outcome(
            outcome,
            result.error.code if result.error else None,
            spec.retryable_errors,
            spec.human_errors,
            spec.terminal_errors,
            attempt.attempt_no,
            spec.default_max_attempts,
        )

        # Update attempt with result.
        finished = Attempt(
            attempt_id=attempt.attempt_id,
            job_id=attempt.job_id,
            attempt_no=attempt.attempt_no,
            worker_id=attempt.worker_id,
            lease_token=attempt.lease_token,
            lease_until=attempt.lease_until,
            started_at=attempt.started_at,
            heartbeat_at=attempt.heartbeat_at,
            finished_at=now,
            outcome=outcome,
            result_json=canonical_json(_to_plain(result.result)) if result.result else None,
            error_code=error_code,
            error_detail=result.error.detail if result.error else None,
        )
        # Re-put attempt with finished fields (idempotent by attempt_id).
        try:
            self._store.put_attempt(finished)
        except Exception:
            pass  # attempt already exists, update not critical for AUTO-4

        # Transition job (from RUNNING state).
        if next_status is JobStatus.SUCCEEDED:
            # RUNNING → VERIFYING → SUCCEEDED.
            self._store.transition_job(
                job.job_id,
                expected=JobStatus.RUNNING,
                target=JobStatus.VERIFYING,
                updated_at=now,
            )
            self._store.transition_job(
                job.job_id,
                expected=JobStatus.VERIFYING,
                target=JobStatus.SUCCEEDED,
                updated_at=now,
            )
        elif next_status is JobStatus.RETRY_WAIT:
            retry_at = _add_seconds(
                now, compute_retry_delay(attempt.attempt_no, job_id=job.job_id)
            )
            self._store.transition_job(
                job.job_id,
                expected=JobStatus.RUNNING,
                target=JobStatus.RETRY_WAIT,
                updated_at=now,
                error_code=error_code,
            )
            # Reset to ready at retry_at (simplified: immediate for AUTO-4).
            self._store.transition_job(
                job.job_id,
                expected=JobStatus.RETRY_WAIT,
                target=JobStatus.READY,
                updated_at=retry_at,
            )
        elif next_status is JobStatus.BLOCKED_HUMAN:
            self._store.transition_job(
                job.job_id,
                expected=JobStatus.RUNNING,
                target=JobStatus.BLOCKED_HUMAN,
                updated_at=now,
                error_code=error_code,
            )
        elif next_status is JobStatus.DEAD_LETTER:
            self._store.transition_job(
                job.job_id,
                expected=JobStatus.RUNNING,
                target=JobStatus.DEAD_LETTER,
                updated_at=now,
                error_code=error_code,
            )

        # Write outbox entries for effects.
        for eff in result.effects:
            outbox_id = self._id_gen.new_id()
            self._store.put_outbox_entry(
                outbox_id=outbox_id,
                effect_id=eff.effect_id,
                payload_json=canonical_json(eff.to_dict()),
                status="pending",
                not_before=now,
            )

    def _commit_failure(self, job: Job, attempt: Attempt, error: str, now: str) -> None:
        """Commit a handler execution failure (exception, not HandlerResult)."""
        try:
            finished = Attempt(
                attempt_id=attempt.attempt_id,
                job_id=attempt.job_id,
                attempt_no=attempt.attempt_no,
                worker_id=attempt.worker_id,
                lease_token=attempt.lease_token,
                lease_until=attempt.lease_until,
                started_at=attempt.started_at,
                heartbeat_at=attempt.heartbeat_at,
                finished_at=now,
                outcome=HandlerOutcome.TERMINAL_FAILURE,
                result_json=None,
                error_code="HANDLER_EXCEPTION",
                error_detail=error,
            )
            self._store.put_attempt(finished)
        except Exception:
            pass
        try:
            self._store.transition_job(
                job.job_id,
                expected=JobStatus.RUNNING,
                target=JobStatus.DEAD_LETTER,
                updated_at=now,
                error_code="HANDLER_EXCEPTION",
                error_detail=error,
            )
        except Exception:
            pass

    def _count_attempts(self, job_id: str) -> int:
        return len(self._store.list_attempts(job_id))

    def reap_expired(self) -> int:
        """Reap expired leases: reset jobs to ready, mark attempts as expired.

        Returns the number of jobs reset.  Handles both LECTED and RUNNING
        states (the latter via RETRY_WAIT → READY to stay within the state
        machine).
        """
        now = self._clock.now()
        count = 0
        for status in (JobStatus.LEASED, JobStatus.RUNNING):
            for job in self._store.list_jobs(status=status):
                attempts = self._store.list_attempts(job.job_id)
                if not attempts:
                    continue
                latest = max(attempts, key=lambda a: a.attempt_no)
                if latest.lease_until and latest.lease_until <= now:
                    try:
                        if status is JobStatus.LEASED:
                            self._store.transition_job(
                                job.job_id,
                                expected=JobStatus.LEASED,
                                target=JobStatus.READY,
                                updated_at=now,
                            )
                        else:
                            # RUNNING → RETRY_WAIT → READY.
                            self._store.transition_job(
                                job.job_id,
                                expected=JobStatus.RUNNING,
                                target=JobStatus.RETRY_WAIT,
                                updated_at=now,
                                error_code="LEASE_EXPIRED",
                            )
                            self._store.transition_job(
                                job.job_id,
                                expected=JobStatus.RETRY_WAIT,
                                target=JobStatus.READY,
                                updated_at=now,
                            )
                        count += 1
                    except Exception:
                        pass  # another worker may have already transitioned
        return count


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #
def _add_seconds(iso_time: str, seconds: int) -> str:
    """Add seconds to an ISO 8601 UTC timestamp."""
    dt = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    from datetime import timedelta
    result = dt + timedelta(seconds=seconds)
    return result.strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "Clock",
    "IDGenerator",
    "HandlerExecutor",
    "UnknownHandlerError",
    "Worker",
]
