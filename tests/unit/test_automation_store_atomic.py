"""Atomic Store contracts for worker leases, completion, and the outbox."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from company_wiki.automation import models
from company_wiki.automation import store as store_module


T0 = "2026-09-28T10:00:00Z"
T1 = "2026-09-28T10:01:00Z"
T2 = "2026-09-28T10:02:00Z"
T3 = "2026-09-28T10:03:00Z"
T4 = "2026-09-28T10:04:00Z"
T5 = "2026-09-28T10:05:00Z"
T9 = "2026-09-28T10:09:00Z"
INPUT_HASH = hashlib.sha256(b"m3-e1-input").hexdigest()
AFTER_HASH = hashlib.sha256(b"m3-e1-after").hexdigest()


def _seed_ready_job(
    store: store_module.AutomationStore,
    *,
    suffix: str = "one",
    max_attempts: int = 3,
) -> models.Job:
    event_id = f"evt-{suffix}"
    job_id = f"job-{suffix}"
    subject_id = f"source-{suffix}"
    event = models.Event(
        event_id=event_id,
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id=f"revision-{suffix}",
        input_hash=INPUT_HASH,
        payload_json=models.canonical_json({"suffix": suffix}),
        policy_version="narrative-v1",
        occurred_at=T0,
        observed_at=T0,
    )
    store.put_event(event)
    job = models.Job(
        job_id=job_id,
        job_key=models.make_job_key(
            "source.narrative_select",
            "source",
            subject_id,
            INPUT_HASH,
            "narrative-v1",
            "1.0.0",
        ),
        job_type="source.narrative_select",
        subject_type="source",
        subject_id=subject_id,
        input_hash=INPUT_HASH,
        policy_version="narrative-v1",
        handler_version="1.0.0",
        risk_class=models.RiskClass.LOW,
        status=models.JobStatus.READY,
        priority=10,
        not_before=T0,
        max_attempts=max_attempts,
        created_from_event_id=event_id,
        created_at=T0,
        updated_at=T0,
        last_error_code=None,
        last_error_detail=None,
    )
    store.put_job(job)
    return job


def _enable(store: store_module.AutomationStore) -> int:
    gate = store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=T1)
    assert gate.desired_state is models.RuntimeState.ENABLED
    return gate.control_generation


def _claim(
    store: store_module.AutomationStore,
    generation: int,
    *,
    suffix: str = "one",
    now: str = T1,
    lease_until: str = T5,
):
    claimed = store.claim_next_ready(
        worker_id="worker-a",
        attempt_id=f"attempt-{suffix}",
        lease_token=f"lease-{suffix}",
        now=now,
        lease_until=lease_until,
        expected_generation=generation,
        allowed_job_types=("source.narrative_select",),
    )
    assert claimed is not None
    return claimed


def _success_result(*effects: models.Effect) -> models.HandlerResult:
    return models.HandlerResult(
        outcome=models.HandlerOutcome.SUCCEEDED,
        result={"selected": 7},
        artifacts=(),
        effects=tuple(effects),
        metrics=models.HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=12),
        error=None,
    )


def _retryable_result() -> models.HandlerResult:
    return models.HandlerResult(
        outcome=models.HandlerOutcome.RETRYABLE,
        result={"stage": "provider"},
        artifacts=(),
        effects=(),
        metrics=models.HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=4),
        error=models.HandlerError(code="PROVIDER_TIMEOUT", detail="retry later"),
    )


def _effect(job_id: str, *, suffix: str = "one") -> models.Effect:
    target = f"artifacts/narrative/{suffix}.json"
    return models.Effect(
        effect_id=f"effect-{suffix}",
        effect_key=models.make_effect_key(
            "artifact_write", target, AFTER_HASH, "1.0.0"
        ),
        job_id=job_id,
        effect_type="artifact_write",
        target=target,
        before_hash=None,
        intended_after_hash=AFTER_HASH,
        actual_after_hash=None,
        status=models.EffectStatus.PENDING,
        created_at=T2,
        verified_at=None,
    )


def test_runtime_gate_is_seeded_paused_and_generation_changes_only_on_state_change(
    tmp_path: Path,
) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")

    initial = store.read_runtime_gate()
    enabled = store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=T1)
    enabled_again = store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=T2)
    paused = store.set_runtime_gate(models.RuntimeState.PAUSED, updated_at=T3)

    assert initial == models.RuntimeGate(
        desired_state=models.RuntimeState.PAUSED,
        control_generation=1,
        updated_at="1970-01-01T00:00:00Z",
    )
    assert enabled.control_generation == 2
    assert enabled_again == enabled
    assert paused.control_generation == 3


def test_claim_is_atomic_and_rolls_back_if_attempt_insert_fails(tmp_path: Path) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")
    _seed_ready_job(store, suffix="target")
    _seed_ready_job(store, suffix="existing")
    generation = _enable(store)
    store.put_attempt(
        models.Attempt(
            attempt_id="attempt-collision",
            job_id="job-existing",
            attempt_no=1,
            worker_id="old-worker",
            lease_token="old-lease",
            lease_until=T5,
            started_at=T0,
            heartbeat_at=T0,
            finished_at=T1,
            outcome=models.HandlerOutcome.TERMINAL_FAILURE,
            result_json=None,
            error_code="OLD",
            error_detail="old attempt",
            runtime_generation=0,
        )
    )

    with pytest.raises(store_module.IntegrityViolationError):
        store.claim_next_ready(
            worker_id="worker-new",
            attempt_id="attempt-collision",
            lease_token="new-lease",
            now=T1,
            lease_until=T5,
            expected_generation=generation,
            allowed_job_types=("source.narrative_select",),
        )

    assert store.get_job("job-target").status is models.JobStatus.READY
    assert len(store.list_attempts("job-target")) == 0


def test_finish_updates_the_claimed_attempt_and_completes_no_effect_job(
    tmp_path: Path,
) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")
    _seed_ready_job(store)
    generation = _enable(store)
    claimed = _claim(store, generation)

    finished = store.finish_attempt(
        attempt_id=claimed.attempt.attempt_id,
        lease_token=claimed.attempt.lease_token,
        runtime_generation=generation,
        finished_at=T2,
        result=_success_result(),
    )

    assert finished.finished_at == T2
    assert finished.outcome is models.HandlerOutcome.SUCCEEDED
    assert finished.result_json == models.canonical_json(_success_result().to_dict())
    assert len(store.list_attempts(claimed.job.job_id)) == 1
    assert store.get_job(claimed.job.job_id).status is models.JobStatus.SUCCEEDED


@pytest.mark.parametrize("failure", ["token", "generation", "expired", "not_latest"])
def test_heartbeat_and_finish_reject_every_stale_lease(
    tmp_path: Path, failure: str
) -> None:
    store = store_module.AutomationStore(tmp_path / f"{failure}.db")
    _seed_ready_job(store)
    generation = _enable(store)
    claimed = _claim(store, generation, lease_until=T3)
    attempt = claimed.attempt
    token = attempt.lease_token
    supplied_generation = generation
    now = T2
    if failure == "token":
        token = "wrong-token"
    elif failure == "generation":
        supplied_generation = generation - 1
    elif failure == "expired":
        now = T4
    else:
        store.put_attempt(
            models.Attempt(
                attempt_id="attempt-newer",
                job_id=claimed.job.job_id,
                attempt_no=2,
                worker_id="worker-b",
                lease_token="lease-newer",
                lease_until=T5,
                started_at=T1,
                heartbeat_at=T1,
                finished_at=None,
                outcome=None,
                result_json=None,
                error_code=None,
                error_detail=None,
                runtime_generation=generation,
            )
        )

    with pytest.raises(
        (store_module.LeaseLostError, store_module.RuntimeGenerationError)
    ):
        store.heartbeat_attempt(
            attempt_id=attempt.attempt_id,
            lease_token=token,
            runtime_generation=supplied_generation,
            now=now,
            lease_until=T9,
        )
    with pytest.raises(
        (store_module.LeaseLostError, store_module.RuntimeGenerationError)
    ):
        store.finish_attempt(
            attempt_id=attempt.attempt_id,
            lease_token=token,
            runtime_generation=supplied_generation,
            finished_at=now,
            result=_success_result(),
        )

    assert store.get_attempt(attempt.attempt_id).finished_at is None
    assert store.get_job(claimed.job.job_id).status is models.JobStatus.RUNNING


def test_effect_and_outbox_commit_with_attempt_or_all_roll_back(tmp_path: Path) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")
    first = _seed_ready_job(store, suffix="first")
    second = _seed_ready_job(store, suffix="second")
    generation = _enable(store)

    first_claim = _claim(store, generation, suffix="first")
    first_effect = _effect(first.job_id, suffix="shared")
    store.finish_attempt(
        attempt_id=first_claim.attempt.attempt_id,
        lease_token=first_claim.attempt.lease_token,
        runtime_generation=generation,
        finished_at=T2,
        result=_success_result(first_effect),
        outbox_not_before=T2,
    )
    assert store.get_job(first.job_id).status is models.JobStatus.VERIFYING
    assert store.get_effect(first_effect.effect_id) == first_effect
    outbox = store.get_outbox_entry(f"outbox-{first_effect.effect_id}")
    assert outbox is not None and outbox["status"] == "pending"

    second_claim = _claim(store, generation, suffix="second")
    conflicting = _effect(second.job_id, suffix="shared")
    with pytest.raises(store_module.IdempotencyConflictError):
        store.finish_attempt(
            attempt_id=second_claim.attempt.attempt_id,
            lease_token=second_claim.attempt.lease_token,
            runtime_generation=generation,
            finished_at=T3,
            result=_success_result(conflicting),
            outbox_not_before=T3,
        )

    assert store.get_attempt(second_claim.attempt.attempt_id).finished_at is None
    assert store.get_job(second.job_id).status is models.JobStatus.RUNNING
    assert len(store.list_effects(second.job_id)) == 0


def test_retry_wait_respects_not_before_and_reaper_fences_the_slow_worker(
    tmp_path: Path,
) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")
    _seed_ready_job(store)
    generation = _enable(store)
    claimed = _claim(store, generation, lease_until=T2)

    reaped = store.reap_expired_attempts(now=T3)

    assert reaped == (claimed.attempt.attempt_id,)
    attempt = store.get_attempt(claimed.attempt.attempt_id)
    assert attempt.error_code == "LEASE_EXPIRED"
    assert attempt.outcome is models.HandlerOutcome.RETRYABLE
    assert store.get_job(claimed.job.job_id).status is models.JobStatus.RETRY_WAIT
    assert store.promote_ready_jobs(now=T2) == ()
    assert store.promote_ready_jobs(now=T3) == (claimed.job.job_id,)
    assert store.promote_ready_jobs(now=T3) == ()
    with pytest.raises(store_module.LeaseLostError):
        store.finish_attempt(
            attempt_id=claimed.attempt.attempt_id,
            lease_token=claimed.attempt.lease_token,
            runtime_generation=generation,
            finished_at=T4,
            result=_retryable_result(),
            retry_not_before=T5,
        )


def test_outbox_ack_is_fenced_and_finishes_verifying_job(tmp_path: Path) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")
    job = _seed_ready_job(store)
    generation = _enable(store)
    claimed = _claim(store, generation)
    effect = _effect(job.job_id)
    store.finish_attempt(
        attempt_id=claimed.attempt.attempt_id,
        lease_token=claimed.attempt.lease_token,
        runtime_generation=generation,
        finished_at=T2,
        result=_success_result(effect),
        outbox_not_before=T2,
    )
    lease = store.claim_next_outbox(
        worker_id="projector-a",
        lease_token="outbox-lease",
        now=T2,
        lease_until=T5,
        expected_generation=generation,
    )
    assert lease is not None

    with pytest.raises(store_module.LeaseLostError):
        store.ack_outbox(
            outbox_id=lease.outbox_id,
            lease_token="wrong-token",
            runtime_generation=generation,
            verified_at=T3,
            actual_after_hash=AFTER_HASH,
        )

    completed = store.ack_outbox(
        outbox_id=lease.outbox_id,
        lease_token=lease.lease_token,
        runtime_generation=generation,
        verified_at=T3,
        actual_after_hash=AFTER_HASH,
    )
    assert completed.status is models.JobStatus.SUCCEEDED
    assert store.get_effect(effect.effect_id).status is models.EffectStatus.VERIFIED
    assert store.get_outbox_entry(lease.outbox_id)["status"] == "delivered"


def test_outbox_retry_dead_letters_at_budget(tmp_path: Path) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")
    job = _seed_ready_job(store)
    generation = _enable(store)
    claimed = _claim(store, generation)
    effect = _effect(job.job_id)
    store.finish_attempt(
        attempt_id=claimed.attempt.attempt_id,
        lease_token=claimed.attempt.lease_token,
        runtime_generation=generation,
        finished_at=T2,
        result=_success_result(effect),
        outbox_not_before=T2,
    )
    lease = store.claim_next_outbox(
        worker_id="projector-a",
        lease_token="outbox-lease",
        now=T2,
        lease_until=T5,
        expected_generation=generation,
    )
    assert lease is not None

    retried = store.retry_outbox(
        outbox_id=lease.outbox_id,
        lease_token=lease.lease_token,
        runtime_generation=generation,
        now=T3,
        not_before=T4,
        error="disk full",
        max_attempts=1,
    )

    assert retried["status"] == "failed"
    assert retried["attempt_count"] == 1
    assert store.get_effect(effect.effect_id).status is models.EffectStatus.FAILED
    assert store.get_job(job.job_id).status is models.JobStatus.DEAD_LETTER


def test_pause_after_claim_invalidates_worker_completion(tmp_path: Path) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")
    _seed_ready_job(store)
    generation = _enable(store)
    claimed = _claim(store, generation)
    paused = store.set_runtime_gate(models.RuntimeState.PAUSED, updated_at=T2)
    assert paused.control_generation == generation + 1

    with pytest.raises(store_module.RuntimeGateClosedError):
        store.finish_attempt(
            attempt_id=claimed.attempt.attempt_id,
            lease_token=claimed.attempt.lease_token,
            runtime_generation=generation,
            finished_at=T3,
            result=_success_result(),
        )

    assert store.get_attempt(claimed.attempt.attempt_id).finished_at is None
    assert store.get_job(claimed.job.job_id).status is models.JobStatus.RUNNING


def test_all_effects_must_be_delivered_before_job_succeeds(tmp_path: Path) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")
    job = _seed_ready_job(store)
    generation = _enable(store)
    claimed = _claim(store, generation)
    first = _effect(job.job_id, suffix="first")
    second = _effect(job.job_id, suffix="second")
    store.finish_attempt(
        attempt_id=claimed.attempt.attempt_id,
        lease_token=claimed.attempt.lease_token,
        runtime_generation=generation,
        finished_at=T2,
        result=_success_result(first, second),
        outbox_not_before=T2,
    )

    first_lease = store.claim_next_outbox(
        worker_id="projector-a",
        lease_token="outbox-first",
        now=T2,
        lease_until=T5,
        expected_generation=generation,
    )
    assert first_lease is not None
    after_first = store.ack_outbox(
        outbox_id=first_lease.outbox_id,
        lease_token=first_lease.lease_token,
        runtime_generation=generation,
        verified_at=T3,
        actual_after_hash=AFTER_HASH,
    )
    assert after_first.status is models.JobStatus.VERIFYING

    second_lease = store.claim_next_outbox(
        worker_id="projector-b",
        lease_token="outbox-second",
        now=T3,
        lease_until=T9,
        expected_generation=generation,
    )
    assert second_lease is not None
    after_second = store.ack_outbox(
        outbox_id=second_lease.outbox_id,
        lease_token=second_lease.lease_token,
        runtime_generation=generation,
        verified_at=T4,
        actual_after_hash=AFTER_HASH,
    )
    assert after_second.status is models.JobStatus.SUCCEEDED


def test_outbox_ack_rejects_a_hash_that_differs_from_intended_output(
    tmp_path: Path,
) -> None:
    store = store_module.AutomationStore(tmp_path / "automation.db")
    job = _seed_ready_job(store)
    generation = _enable(store)
    claimed = _claim(store, generation)
    effect = _effect(job.job_id)
    store.finish_attempt(
        attempt_id=claimed.attempt.attempt_id,
        lease_token=claimed.attempt.lease_token,
        runtime_generation=generation,
        finished_at=T2,
        result=_success_result(effect),
        outbox_not_before=T2,
    )
    lease = store.claim_next_outbox(
        worker_id="projector",
        lease_token="outbox-lease",
        now=T2,
        lease_until=T5,
        expected_generation=generation,
    )
    assert lease is not None

    with pytest.raises(store_module.IntegrityViolationError):
        store.ack_outbox(
            outbox_id=lease.outbox_id,
            lease_token=lease.lease_token,
            runtime_generation=generation,
            verified_at=T3,
            actual_after_hash=hashlib.sha256(b"wrong").hexdigest(),
        )

    assert store.get_job(job.job_id).status is models.JobStatus.VERIFYING
    assert store.get_effect(effect.effect_id).status is models.EffectStatus.PENDING
    assert store.get_outbox_entry(lease.outbox_id)["status"] == "leased"


def test_atomic_store_does_not_run_business_io_inside_transaction() -> None:
    source = Path(store_module.__file__).read_text(encoding="utf-8")
    forbidden = (
        "source_catalog",
        "LLMClient",
        "pdfplumber",
        "time.sleep",
        "subprocess",
    )
    for token in forbidden:
        assert token not in source
