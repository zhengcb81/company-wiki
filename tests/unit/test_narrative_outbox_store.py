"""Focused persistence contracts required by narrative outbox projection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.automation import models
from company_wiki.automation.store import (
    AutomationStore,
    LeaseLostError,
    RecordNotFoundError,
)


T0 = "2026-09-29T10:00:00Z"
T1 = "2026-09-29T10:01:00Z"
T2 = "2026-09-29T10:02:00Z"
T3 = "2026-09-29T10:03:00Z"
T4 = "2026-09-29T10:04:00Z"
T8 = "2026-09-29T10:08:00Z"
INPUT_HASH = hashlib.sha256(b"narrative-outbox-input").hexdigest()
OTHER_HASH = hashlib.sha256(b"other-effect-result").hexdigest()
BUNDLE = {"schema_version": "narrative-bundle/2.0", "marker": "already-computed"}
BUNDLE_HASH = hashlib.sha256(
    models.canonical_json(BUNDLE).encode("utf-8")
).hexdigest()


def _ready_job(store: AutomationStore, suffix: str) -> models.Job:
    event = models.Event(
        event_id=f"event-{suffix}",
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
        job_id=f"job-{suffix}",
        job_key=models.make_job_key(
            "source.narrative_verify",
            "source",
            f"source-{suffix}",
            INPUT_HASH,
            "narrative-v1",
            "1.0.0",
        ),
        job_type="source.narrative_verify",
        subject_type="source",
        subject_id=f"source-{suffix}",
        input_hash=INPUT_HASH,
        policy_version="narrative-v1",
        handler_version="1.0.0",
        risk_class=models.RiskClass.LOW,
        status=models.JobStatus.READY,
        priority=10,
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


def _effect(
    job_id: str,
    *,
    effect_id: str,
    effect_type: str,
    output_hash: str,
) -> models.Effect:
    target = f"urn:company-wiki:{effect_id}"
    return models.Effect(
        effect_id=effect_id,
        effect_key=models.make_effect_key(effect_type, target, output_hash, "2.0"),
        job_id=job_id,
        effect_type=effect_type,
        target=target,
        before_hash=None,
        intended_after_hash=output_hash,
        actual_after_hash=None,
        status=models.EffectStatus.PENDING,
        created_at=T1,
        verified_at=None,
    )


def _finish(
    store: AutomationStore,
    job: models.Job,
    effect: models.Effect,
    *,
    generation: int,
    finished_at: str,
) -> models.HandlerResult:
    claimed = store.claim_next_ready(
        worker_id="test-worker",
        attempt_id=f"attempt-{job.job_id}",
        lease_token=f"lease-{job.job_id}",
        now=T1,
        lease_until=T8,
        expected_generation=generation,
        allowed_job_types=(job.job_type,),
    )
    assert claimed is not None
    result = models.HandlerResult(
        outcome=models.HandlerOutcome.SUCCEEDED,
        result=BUNDLE if effect.effect_type == "narrative_bundle.publish" else {"other": True},
        artifacts=(),
        effects=(effect,),
        metrics=models.HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=1),
        error=None,
    )
    store.finish_attempt(
        attempt_id=claimed.attempt.attempt_id,
        lease_token=claimed.attempt.lease_token,
        runtime_generation=generation,
        finished_at=finished_at,
        result=result,
        outbox_not_before=finished_at,
    )
    return result


def test_result_for_effect_reads_the_exact_persisted_handler_result(
    tmp_path: Path,
) -> None:
    store = AutomationStore(tmp_path / "automation.sqlite3")
    job = _ready_job(store, "narrative")
    generation = store.set_runtime_gate(
        models.RuntimeState.ENABLED, updated_at=T1
    ).control_generation
    effect = _effect(
        job.job_id,
        effect_id="effect-narrative",
        effect_type="narrative_bundle.publish",
        output_hash=BUNDLE_HASH,
    )
    original = _finish(
        store, job, effect, generation=generation, finished_at=T2
    )

    assert store.result_for_effect(effect.effect_id) == original
    assert json.loads(store.list_attempts(job.job_id)[-1].result_json)["effects"][0][
        "effect_id"
    ] == effect.effect_id


def test_result_for_effect_rejects_an_unknown_effect(tmp_path: Path) -> None:
    store = AutomationStore(tmp_path / "automation.sqlite3")

    with pytest.raises(RecordNotFoundError):
        store.result_for_effect("effect-does-not-exist")


def test_outbox_claim_can_skip_unhandled_effect_types(tmp_path: Path) -> None:
    store = AutomationStore(tmp_path / "automation.sqlite3")
    generation = store.set_runtime_gate(
        models.RuntimeState.ENABLED, updated_at=T1
    ).control_generation

    other_job = _ready_job(store, "other")
    other_effect = _effect(
        other_job.job_id,
        effect_id="effect-00-other",
        effect_type="another.effect",
        output_hash=OTHER_HASH,
    )
    _finish(store, other_job, other_effect, generation=generation, finished_at=T2)

    narrative_job = _ready_job(store, "narrative")
    narrative_effect = _effect(
        narrative_job.job_id,
        effect_id="effect-99-narrative",
        effect_type="narrative_bundle.publish",
        output_hash=BUNDLE_HASH,
    )
    _finish(
        store, narrative_job, narrative_effect, generation=generation, finished_at=T3
    )

    lease = store.claim_next_outbox(
        worker_id="narrative-projector",
        lease_token="narrative-lease",
        now=T3,
        lease_until=T8,
        expected_generation=generation,
        allowed_effect_types=("narrative_bundle.publish",),
    )

    assert lease is not None
    assert json.loads(lease.payload_json)["effect_id"] == narrative_effect.effect_id
    assert store.get_outbox_entry("outbox-effect-00-other")["status"] == "pending"

def test_expired_outbox_lease_can_be_reclaimed_and_old_token_is_fenced(
    tmp_path: Path,
) -> None:
    store = AutomationStore(tmp_path / "automation.sqlite3")
    job = _ready_job(store, "lease-recovery")
    generation = store.set_runtime_gate(
        models.RuntimeState.ENABLED, updated_at=T1
    ).control_generation
    effect = _effect(
        job.job_id,
        effect_id="effect-lease-recovery",
        effect_type="narrative_bundle.publish",
        output_hash=BUNDLE_HASH,
    )
    _finish(store, job, effect, generation=generation, finished_at=T2)

    first = store.claim_next_outbox(
        worker_id="projector-old",
        lease_token="old-token",
        now=T2,
        lease_until=T3,
        expected_generation=generation,
        allowed_effect_types=("narrative_bundle.publish",),
    )
    assert first is not None

    reclaimed = store.claim_next_outbox(
        worker_id="projector-restarted",
        lease_token="new-token",
        now=T3,
        lease_until=T8,
        expected_generation=generation,
        allowed_effect_types=("narrative_bundle.publish",),
    )

    assert reclaimed is not None
    assert reclaimed.outbox_id == first.outbox_id
    assert reclaimed.lease_token == "new-token"
    with pytest.raises(LeaseLostError):
        store.ack_outbox(
            outbox_id=first.outbox_id,
            lease_token=first.lease_token,
            runtime_generation=generation,
            verified_at=T4,
            actual_after_hash=BUNDLE_HASH,
        )
    completed = store.ack_outbox(
        outbox_id=reclaimed.outbox_id,
        lease_token=reclaimed.lease_token,
        runtime_generation=generation,
        verified_at=T4,
        actual_after_hash=BUNDLE_HASH,
    )
    assert completed.status is models.JobStatus.SUCCEEDED
    persisted_result = store.result_for_effect(effect.effect_id)
    assert persisted_result.outcome is models.HandlerOutcome.SUCCEEDED
    assert persisted_result.effects == (effect,)
    verified_effect = store.get_effect(effect.effect_id)
    assert verified_effect is not None
    assert verified_effect.status is models.EffectStatus.VERIFIED
    assert verified_effect.actual_after_hash == BUNDLE_HASH
