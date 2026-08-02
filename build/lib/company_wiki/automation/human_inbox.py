"""AUTO-6 Human inbox: structured view of blocked_human jobs.

This module depends on the store and models.  It does not import the legacy
scheduler, network, LLM or configuration modules.  The inbox is a read-only
view; it does not modify jobs or make decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Job, JobStatus


@dataclass(frozen=True)
class InboxEntry:
    """A single entry in the human inbox."""

    job_id: str
    job_type: str
    subject_type: str
    subject_id: str
    error_code: str | None
    error_detail: str | None
    why_blocked: str
    required_role: str
    next_safe_action: str


class HumanInbox:
    """Read-only view of jobs requiring human attention."""

    def __init__(self, store) -> None:
        self._store = store

    def list_pending(self, *, role: str | None = None) -> tuple[InboxEntry, ...]:
        """List all blocked_human jobs, optionally filtered by role.

        Returns a tuple of InboxEntry objects describing each pending item.
        """
        blocked_jobs = self._store.list_jobs(status=JobStatus.BLOCKED_HUMAN)
        entries: list[InboxEntry] = []

        for job in blocked_jobs:
            # Determine why_blocked from error_code.
            why_blocked = _why_blocked(job)
            required_role = _required_role(job)
            next_safe_action = _next_safe_action(job)

            # Filter by role if specified.
            if role and required_role != role:
                continue

            entries.append(InboxEntry(
                job_id=job.job_id,
                job_type=job.job_type,
                subject_type=job.subject_type,
                subject_id=job.subject_id,
                error_code=job.last_error_code,
                error_detail=job.last_error_detail,
                why_blocked=why_blocked,
                required_role=required_role,
                next_safe_action=next_safe_action,
            ))

        return tuple(entries)

    def count(self) -> int:
        """Count of blocked_human jobs."""
        return len(self._store.list_jobs(status=JobStatus.BLOCKED_HUMAN))


def _why_blocked(job: Job) -> str:
    """Determine why a job is blocked."""
    if job.last_error_code == "REVIEW_PENDING":
        return "awaiting human review"
    if job.last_error_code == "REVIEW_NEEDS_CHANGES":
        return "reviewer requested changes"
    if job.last_error_code == "LEASE_EXPIRED":
        return "worker lease expired during processing"
    return f"blocked: {job.last_error_code or 'unknown'}"


def _required_role(job: Job) -> str:
    """Determine the required role for unblocking."""
    if job.job_type.startswith("gold."):
        return "reviewer"
    if job.job_type.startswith("analysis."):
        return "analyst"
    return "operator"


def _next_safe_action(job: Job) -> str:
    """Determine the next safe action for the job."""
    if job.last_error_code in ("REVIEW_PENDING", "REVIEW_NEEDS_CHANGES"):
        return "submit-review"
    if job.last_error_code == "LEASE_EXPIRED":
        return "retry"
    return "approve-action"


__all__ = ["HumanInbox", "InboxEntry"]
