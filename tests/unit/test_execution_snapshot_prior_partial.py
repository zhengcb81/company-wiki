"""The execution snapshot exposes the earlier partial attempt to its retry."""
from company_wiki.automation.models import (
    HandlerError, HandlerMetrics, HandlerOutcome, HandlerResult,
)
from unit.test_narrative_run_store import claim, setup_run, T2, T9


def _partial():
    return HandlerResult(
        outcome=HandlerOutcome.RETRYABLE,
        result={"coverage_partial": True, "summary": {"status": "completed"},
                "uncovered_task_keys": ["t2"]},
        artifacts=(), effects=(),
        metrics=HandlerMetrics(tokens=1, cost_usd=0.0, duration_ms=1),
        error=HandlerError("SUMMARY_COVERAGE_PARTIAL", "partial"),
    )


def test_a_retry_snapshot_sees_the_earlier_partial_attempt(tmp_path):
    module, auto, budget, generation, a, _b = setup_run(tmp_path)
    first = claim(auto, generation, a)
    finished = auto.finish_attempt(
        attempt_id=first.attempt.attempt_id,
        lease_token=first.attempt.lease_token,
        runtime_generation=first.attempt.runtime_generation,
        finished_at=T2,
        result=_partial(),
        retry_not_before=T2,
    )
    assert finished.outcome is HandlerOutcome.RETRYABLE
    auto.promote_ready_jobs(now=T9)
    ready = auto.claim_next_ready(
        worker_id="model-worker", attempt_id="attempt-retry",
        lease_token="lease-retry", now=T9, lease_until="2026-10-03T10:19:00Z",
        expected_generation=generation, allowed_job_ids=(a.job_id,),
    )
    assert ready is not None and ready.attempt.attempt_no == 2
    snapshot = auto.read_execution_snapshot(ready, now=T9)
    assert snapshot.prior_partial_result is not None
    assert snapshot.prior_partial_result.result["coverage_partial"] is True
