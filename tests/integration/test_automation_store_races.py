"""Two-connection race tests for claim and outbox leasing."""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

from company_wiki.automation import models
from company_wiki.automation.store import AutomationStore


T0 = "2026-09-28T12:00:00Z"
T1 = "2026-09-28T12:01:00Z"
T2 = "2026-09-28T12:02:00Z"
T5 = "2026-09-28T12:05:00Z"
INPUT_HASH = hashlib.sha256(b"m3-e1-race").hexdigest()
AFTER_HASH = hashlib.sha256(b"m3-e1-race-after").hexdigest()


def _seed(store: AutomationStore) -> models.Job:
    event = models.Event(
        event_id="evt-race",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id="revision-race",
        input_hash=INPUT_HASH,
        payload_json=models.canonical_json({"race": True}),
        policy_version="narrative-v1",
        occurred_at=T0,
        observed_at=T0,
    )
    store.put_event(event)
    job = models.Job(
        job_id="job-race",
        job_key=models.make_job_key(
            "source.narrative_select",
            "source",
            "source-race",
            INPUT_HASH,
            "narrative-v1",
            "1.0.0",
        ),
        job_type="source.narrative_select",
        subject_type="source",
        subject_id="source-race",
        input_hash=INPUT_HASH,
        policy_version="narrative-v1",
        handler_version="1.0.0",
        risk_class=models.RiskClass.LOW,
        status=models.JobStatus.READY,
        priority=1,
        not_before=T0,
        max_attempts=3,
        created_from_event_id=event.event_id,
        created_at=T0,
        updated_at=T0,
        last_error_code=None,
        last_error_detail=None,
    )
    store.put_job(job)
    return job


def test_two_stores_claim_one_ready_job_exactly_once(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"
    setup = AutomationStore(database)
    _seed(setup)
    generation = setup.set_runtime_gate(
        models.RuntimeState.ENABLED, updated_at=T1
    ).control_generation
    barrier = threading.Barrier(2)
    results: list[object] = []
    errors: list[BaseException] = []

    def claim(worker: str) -> None:
        try:
            candidate = AutomationStore(database)
            barrier.wait()
            results.append(
                candidate.claim_next_ready(
                    worker_id=worker,
                    attempt_id=f"attempt-{worker}",
                    lease_token=f"lease-{worker}",
                    now=T1,
                    lease_until=T5,
                    expected_generation=generation,
                    allowed_job_types=("source.narrative_select",),
                )
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=claim, args=(f"worker-{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert sum(result is not None for result in results) == 1
    assert len(setup.list_attempts("job-race")) == 1
    assert setup.get_job("job-race").status is models.JobStatus.RUNNING


def test_two_stores_claim_one_outbox_entry_exactly_once(tmp_path: Path) -> None:
    database = tmp_path / "automation.db"
    setup = AutomationStore(database)
    job = _seed(setup)
    generation = setup.set_runtime_gate(
        models.RuntimeState.ENABLED, updated_at=T1
    ).control_generation
    claimed = setup.claim_next_ready(
        worker_id="worker",
        attempt_id="attempt-worker",
        lease_token="lease-worker",
        now=T1,
        lease_until=T5,
        expected_generation=generation,
        allowed_job_types=("source.narrative_select",),
    )
    assert claimed is not None
    target = "artifacts/narrative/race.json"
    effect = models.Effect(
        effect_id="effect-race",
        effect_key=models.make_effect_key(
            "artifact_write", target, AFTER_HASH, "1.0.0"
        ),
        job_id=job.job_id,
        effect_type="artifact_write",
        target=target,
        before_hash=None,
        intended_after_hash=AFTER_HASH,
        actual_after_hash=None,
        status=models.EffectStatus.PENDING,
        created_at=T2,
        verified_at=None,
    )
    result = models.HandlerResult(
        outcome=models.HandlerOutcome.SUCCEEDED,
        result={"ready": True},
        artifacts=(),
        effects=(effect,),
        metrics=models.HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=1),
        error=None,
    )
    setup.finish_attempt(
        attempt_id=claimed.attempt.attempt_id,
        lease_token=claimed.attempt.lease_token,
        runtime_generation=generation,
        finished_at=T2,
        result=result,
        outbox_not_before=T2,
    )
    barrier = threading.Barrier(2)
    results: list[object] = []
    errors: list[BaseException] = []

    def claim(projector: str) -> None:
        try:
            candidate = AutomationStore(database)
            barrier.wait()
            results.append(
                candidate.claim_next_outbox(
                    worker_id=projector,
                    lease_token=f"outbox-{projector}",
                    now=T2,
                    lease_until=T5,
                    expected_generation=generation,
                )
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [
        threading.Thread(target=claim, args=(f"projector-{i}",))
        for i in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert sum(result is not None for result in results) == 1
    assert setup.get_outbox_entry("outbox-effect-race")["status"] == "leased"
