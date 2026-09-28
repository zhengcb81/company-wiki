"""E2 contracts for deterministic, atomic DAG materialization."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import sqlite3
from pathlib import Path

import pytest


NOW = "2026-09-28T10:00:00Z"
LATER = "2026-09-28T10:01:00Z"
INPUT_HASH = hashlib.sha256(b"e2-scheduler-input").hexdigest()


def _event(*, payload: dict[str, object] | None = None):
    from company_wiki.automation.models import Event, canonical_json

    return Event(
        event_id="evt-e2-001",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id="rev-e2-001",
        input_hash=INPUT_HASH,
        payload_json=canonical_json(payload or {"source_id": "src-e2-001"}),
        policy_version="v1",
        occurred_at=NOW,
        observed_at=NOW,
    )


def _scheduler(tmp_path: Path):
    from company_wiki.automation.policy import PolicyConfig
    from company_wiki.automation.registry import create_default_registry
    from company_wiki.automation.scheduler import AutomationScheduler
    from company_wiki.automation.store import AutomationStore

    store = AutomationStore(tmp_path / "automation.db")
    scheduler = AutomationScheduler(
        store,
        create_default_registry(),
        PolicyConfig(allow_llm=True, allow_network=True),
    )
    return store, scheduler


def _job_by_type(store, job_type: str):
    return next(job for job in store.list_jobs() if job.job_type == job_type)


def test_materialize_same_event_twice_creates_one_exact_dag(tmp_path: Path) -> None:
    from company_wiki.automation.models import JobStatus

    store, scheduler = _scheduler(tmp_path)
    event = _event()
    store.put_event(event)

    first = scheduler.materialize_event(event)
    second = scheduler.materialize_event(event)

    assert (first.jobs_created, first.dependencies_created) == (3, 3)
    assert (second.jobs_created, second.dependencies_created) == (0, 0)
    assert (second.jobs_existing, second.dependencies_existing) == (3, 3)
    jobs = store.list_jobs()
    assert len(jobs) == 3
    root = _job_by_type(store, "source.narrative_select")
    child = _job_by_type(store, "source.narrative_summarize")
    verify = _job_by_type(store, "source.narrative_verify")
    assert root.status is JobStatus.READY
    assert child.status is JobStatus.PLANNED
    assert verify.status is JobStatus.PLANNED
    assert store.list_job_dependencies(child.job_id) == ((child.job_id, root.job_id),)
    assert set(store.list_job_dependencies(verify.job_id)) == {
        (verify.job_id, root.job_id),
        (verify.job_id, child.job_id),
    }


def test_materialize_rejects_changed_event_payload_reusing_job_key(
    tmp_path: Path,
) -> None:
    from company_wiki.automation.models import canonical_json
    from company_wiki.automation.store import IdempotencyConflictError

    store, scheduler = _scheduler(tmp_path)
    event = _event()
    store.put_event(event)
    scheduler.materialize_event(event)
    changed = replace(
        event,
        payload_json=canonical_json({"source_id": "src-e2-001", "changed": True}),
    )

    with pytest.raises(IdempotencyConflictError, match="event"):
        scheduler.materialize_event(changed)

    assert len(store.list_jobs()) == 3


def test_materialize_rolls_back_partial_dag_on_job_conflict(tmp_path: Path) -> None:
    from company_wiki.automation.planner import plan_jobs
    from company_wiki.automation.policy import PolicyConfig
    from company_wiki.automation.registry import create_default_registry
    from company_wiki.automation.scheduler import materialize_plan
    from company_wiki.automation.store import IdempotencyConflictError

    store, _scheduler_instance = _scheduler(tmp_path)
    event = _event()
    store.put_event(event)
    plan = plan_jobs(
        event,
        create_default_registry(),
        PolicyConfig(allow_llm=True, allow_network=True),
    )
    dag = materialize_plan(event, plan)
    root, child, verify = dag.jobs
    store.put_job(replace(child, priority=child.priority + 1))

    with pytest.raises(IdempotencyConflictError, match="different materialized content"):
        store.materialize_dag(event, dag)

    assert store.get_job(root.job_id) is None
    assert store.get_job(child.job_id) is not None
    assert store.get_job(verify.job_id) is None
    assert store.list_job_dependencies(child.job_id) == ()


def test_downstream_waits_for_success_result_payload(tmp_path: Path) -> None:
    from company_wiki.automation.models import Attempt, HandlerOutcome, JobStatus

    store, scheduler = _scheduler(tmp_path)
    event = _event()
    store.put_event(event)
    scheduler.materialize_event(event)
    root = _job_by_type(store, "source.narrative_select")
    child = _job_by_type(store, "source.narrative_summarize")

    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?",
            (JobStatus.SUCCEEDED.value, LATER, root.job_id),
        )
        connection.commit()
    finally:
        connection.close()
    store.put_attempt(
        Attempt(
            attempt_id="attempt-e2-parent",
            job_id=root.job_id,
            attempt_no=1,
            worker_id="worker-e2",
            lease_token="lease-e2",
            lease_until=LATER,
            started_at=NOW,
            heartbeat_at=NOW,
            finished_at=LATER,
            outcome=HandlerOutcome.SUCCEEDED,
            result_json=None,
            error_code=None,
            error_detail=None,
            runtime_generation=1,
        )
    )

    assert store.promote_ready_jobs(now=LATER) == ()
    assert store.get_job(child.job_id).status is JobStatus.PLANNED

    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE attempts SET result_json = '{}' WHERE attempt_id = ?",
            ("attempt-e2-parent",),
        )
        connection.commit()
    finally:
        connection.close()

    assert store.promote_ready_jobs(now=LATER) == (child.job_id,)
    assert store.get_job(child.job_id).status is JobStatus.READY


@pytest.mark.parametrize("terminal_status", ["cancelled", "dead_letter"])
def test_terminal_predecessor_blocks_downstream_with_diagnostic(
    tmp_path: Path,
    terminal_status: str,
) -> None:
    from company_wiki.automation.models import JobStatus

    store, scheduler = _scheduler(tmp_path)
    event = _event()
    store.put_event(event)
    scheduler.materialize_event(event)
    root = _job_by_type(store, "source.narrative_select")
    child = _job_by_type(store, "source.narrative_summarize")
    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?",
            (terminal_status, LATER, root.job_id),
        )
        connection.commit()
    finally:
        connection.close()

    assert store.promote_ready_jobs(now=LATER) == ()
    blocked = store.get_job(child.job_id)
    assert blocked is not None
    assert blocked.status is JobStatus.BLOCKED_HUMAN
    assert blocked.last_error_code == "DEPENDENCY_TERMINAL"
    assert root.job_id in (blocked.last_error_detail or "")
    assert terminal_status in (blocked.last_error_detail or "")
