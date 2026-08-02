"""AUTO-4 Retry policy: exponential backoff with deterministic jitter.

This module depends only on the Python standard library and ``models``.
It does not import the store, network, LLM or configuration modules.
"""

from __future__ import annotations

import hashlib
import math

from .models import HandlerOutcome, JobStatus


def compute_retry_delay(
    attempt_no: int,
    base_seconds: float = 30.0,
    max_delay_seconds: float = 3600.0,
    job_id: str = "",
) -> float:
    """Compute retry delay: ``min(base * 2^(attempt_no-1), max_delay) + jitter``.

    The jitter is deterministic (derived from ``job_id``) so that retries are
    reproducible and testable.
    """
    exponential = base_seconds * math.pow(2, max(0, attempt_no - 1))
    capped = min(exponential, max_delay_seconds)
    # Deterministic jitter: 0..base_seconds derived from job_id hash.
    if job_id:
        jitter = (int(hashlib.sha256(job_id.encode()).hexdigest()[:8], 16) % 1000) / 1000 * base_seconds
    else:
        jitter = 0.0
    return capped + jitter


def classify_outcome(
    outcome: HandlerOutcome,
    error_code: str | None,
    retryable_errors: tuple[str, ...],
    human_errors: tuple[str, ...],
    terminal_errors: tuple[str, ...],
    attempt_no: int,
    max_attempts: int,
) -> tuple[JobStatus, str | None]:
    """Map handler outcome to the next job status and error code.

    Returns ``(next_status, error_code_or_None)``.
    """
    if outcome is HandlerOutcome.SUCCEEDED:
        return JobStatus.SUCCEEDED, None

    if outcome is HandlerOutcome.BLOCKED_HUMAN:
        return JobStatus.BLOCKED_HUMAN, error_code

    if outcome is HandlerOutcome.TERMINAL_FAILURE:
        return JobStatus.DEAD_LETTER, error_code

    # RETRYABLE: check error classification and attempt budget.
    if error_code in terminal_errors:
        return JobStatus.DEAD_LETTER, error_code
    if error_code in human_errors:
        return JobStatus.BLOCKED_HUMAN, error_code
    if error_code in retryable_errors:
        if attempt_no >= max_attempts:
            return JobStatus.DEAD_LETTER, error_code
        return JobStatus.RETRY_WAIT, error_code
    # Unknown error code with retryable outcome → dead-letter (fail closed).
    return JobStatus.DEAD_LETTER, error_code


__all__ = [
    "compute_retry_delay",
    "classify_outcome",
]
