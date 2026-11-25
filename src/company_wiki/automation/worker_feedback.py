"""Deliver committed worker observations without restarting business work."""

import logging
from typing import Protocol

from company_wiki import runtime_feedback
from company_wiki.diagnostic_redaction import format_diagnostic_exception


_logger = logging.getLogger(__name__)


class WorkerFeedbackStore(Protocol):
    def pending_worker_feedback(
        self, *, allowed_job_ids: tuple[str, ...] | None = None,
    ) -> tuple[tuple[str, str, str], ...]: ...

    def ack_worker_feedback(self, job_id: str, attempt_id: str, payload: str) -> bool: ...


def flush_worker_feedback(
    store: WorkerFeedbackStore, *, allowed_job_ids: tuple[str, ...] | None = None,
) -> dict[str, int | bool]:
    """Acknowledge only frozen payloads durably available to F4 intake."""
    try:
        pending = store.pending_worker_feedback(allowed_job_ids=allowed_job_ids)
    except Exception as exc:
        _logger.warning("worker feedback queue unavailable\n%s", format_diagnostic_exception(exc))
        return {"published": 0, "deferred": 0, "unavailable": True}

    published = deferred = 0
    for job_id, attempt_id, payload in pending:
        try:
            if runtime_feedback.publish_worker_failure(payload, job_id=job_id, attempt_id=attempt_id):
                published += store.ack_worker_feedback(job_id, attempt_id, payload)
            else:
                deferred += 1
        except Exception as exc:
            _logger.warning("worker feedback delivery remains pending\n%s", format_diagnostic_exception(exc))
            deferred += 1
    return {"published": published, "deferred": deferred, "unavailable": False}
