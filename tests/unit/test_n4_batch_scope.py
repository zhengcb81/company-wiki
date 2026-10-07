"""N4A: batch candidates are isolated before selection, maintenance and replay."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

import pytest

from company_wiki.automation import models
from company_wiki.automation.narrative_projection import NarrativeEffectDispatcher
from company_wiki.automation.store import AutomationStore
from company_wiki.automation.supervisor import AutomationSupervisor, SupervisorConfig
from company_wiki.automation.worker import HandlerExecutor, Worker
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.worker_process import WorkerProcessSpec
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactDraft, NarrativeArtifactStore,
)
from company_wiki.source_catalog.store import CatalogStore


T0 = "2026-09-29T10:00:00Z"
T1 = "2026-09-29T10:01:00Z"
T2 = "2026-09-29T10:02:00Z"
T3 = "2026-09-29T10:03:00Z"
T9 = "2026-09-29T10:09:00Z"
SHA = hashlib.sha256(b"batch-scope-source").hexdigest()
EFFECT_TYPE = "narrative_bundle.publish"


def _job(store, name, *, status=models.JobStatus.READY, priority=10,
         job_type="source.narrative_verify", timestamp=T0):
    event = models.Event(
        event_id=f"event-{name}", event_type="source.revision_registered",
        subject_type="source_revision", subject_id=f"revision-{name}",
        input_hash=SHA, payload_json="{}", policy_version="narrative-v1",
        occurred_at=timestamp, observed_at=timestamp,
    )
    store.put_event(event)
    job = models.Job(
        job_id=f"job-{name}",
        job_key=models.make_job_key(job_type, event.subject_type, event.subject_id, SHA, "narrative-v1", "1.0.0"),
        job_type=job_type, subject_type=event.subject_type, subject_id=event.subject_id, input_hash=SHA,
        policy_version="narrative-v1", handler_version="1.0.0", risk_class=models.RiskClass.LOW,
        status=status, priority=priority, not_before=timestamp, max_attempts=3,
        created_from_event_id=event.event_id, created_at=timestamp, updated_at=timestamp,
        last_error_code=None, last_error_detail=None,
    )
    store.put_job(job)
    return job


def _store(tmp_path):
    store = AutomationStore(tmp_path / "auto.db")
    generation = store.set_runtime_gate(models.RuntimeState.ENABLED, updated_at=T1).control_generation
    return store, generation


def _claim(store, generation, name, scope=None, *, now=T1, lease_until=T2):
    return store.claim_next_ready(
        worker_id="scope-worker", attempt_id=f"attempt-{name}", lease_token=f"lease-{name}",
        now=now, lease_until=lease_until, expected_generation=generation, allowed_job_ids=scope,
    )


def _effect(store, generation, job, *, finished_at=T2):
    payload = models.canonical_json({"name": job.job_id}).encode()
    digest = hashlib.sha256(payload).hexdigest()
    effect = models.Effect(
        effect_id=f"effect-{job.job_id}",
        effect_key=models.make_effect_key(EFFECT_TYPE, job.job_id, digest, "2.0"),
        job_id=job.job_id, effect_type=EFFECT_TYPE, target=job.job_id, before_hash=None,
        intended_after_hash=digest, actual_after_hash=None, status=models.EffectStatus.PENDING,
        created_at=finished_at, verified_at=None,
    )
    claimed = _claim(store, generation, job.job_id, (job.job_id,), lease_until=T9)
    assert claimed is not None
    store.finish_attempt(
        attempt_id=claimed.attempt.attempt_id, lease_token=claimed.attempt.lease_token,
        runtime_generation=generation, finished_at=finished_at,
        result=models.HandlerResult(
            outcome=models.HandlerOutcome.SUCCEEDED, result={"name": job.job_id},
            artifacts=(), effects=(effect,),
            metrics=models.HandlerMetrics(tokens=0, cost_usd=0, duration_ms=0), error=None,
        ),
    )
    return effect, payload


def _outbox(store, generation, scope, *, token="project-lease", now=T3, lease_until=T9):
    return store.claim_next_outbox(
        worker_id="projector", lease_token=token, now=now, lease_until=lease_until,
        expected_generation=generation, allowed_effect_types=(EFFECT_TYPE,), allowed_job_ids=scope,
    )


def _artifacts(tmp_path):
    catalog = CatalogStore(tmp_path / "catalog.db")
    with catalog.transaction() as conn:
        conn.execute("INSERT INTO sources (source_id,content_sha256,byte_size,mime_type,first_seen_at) VALUES (?,?,?,?,?)",
                     ("source", SHA, 10, "text/plain", T0))
        conn.execute("INSERT INTO documents (document_id,primary_source_id,title,source_type,document_kind,published_date,source_status,metadata_priority,metadata_json,text_fingerprint,first_seen_at,last_seen_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                     ("document", "source", "Batch source", "file", "investor_call_transcript", None, "active", 10, "{}", None, T0, T0))
    return NarrativeArtifactStore(catalog, LocalNarrativeObjectStore(tmp_path / "objects"))


def _prepare(artifacts, effect_id, payload, *, timestamp=T2):
    return artifacts.prepare(NarrativeArtifactDraft(
        effect_id=effect_id, work_key=hashlib.sha256(effect_id.encode()).hexdigest(),
        document_id="document", source_id="source", source_sha256=SHA,
        producer_name="company_wiki.narrative_bundle", producer_version="2.0",
        policy_sha256=SHA, selection_status="selected", quality_status="verified",
        metadata_json="{}", created_at=timestamp,
    ), payload)


def test_ready_scope_beats_outside_priority_and_combines_with_job_type(tmp_path):
    store, generation = _store(tmp_path)
    outside = _job(store, "outside", priority=999)
    inside = _job(store, "inside")
    claimed = store.claim_next_ready(
        worker_id="worker", attempt_id="inside-attempt", lease_token="inside-token",
        now=T1, lease_until=T9, expected_generation=generation,
        allowed_job_types=(inside.job_type,), allowed_job_ids=(inside.job_id,),
    )
    assert claimed.job.job_id == inside.job_id
    assert store.get_job(outside.job_id) == outside
    assert store.list_attempts(outside.job_id) == ()


def test_scope_none_keeps_daemon_selection(tmp_path):
    store, generation = _store(tmp_path)
    outside = _job(store, "outside", priority=999)
    _job(store, "inside")
    assert _claim(store, generation, "one").job.job_id == outside.job_id


def test_promotion_scopes_child_but_can_read_outside_terminal_parent(tmp_path):
    store, _ = _store(tmp_path)
    parent = _job(store, "failed", status=models.JobStatus.DEAD_LETTER)
    inside = _job(store, "inside", status=models.JobStatus.PLANNED)
    outside = _job(store, "outside", status=models.JobStatus.PLANNED)
    ready = _job(store, "ready", status=models.JobStatus.RETRY_WAIT)
    outside_due = _job(store, "outside-due", status=models.JobStatus.RETRY_WAIT)
    store.add_job_dependency(inside.job_id, parent.job_id)
    store.add_job_dependency(outside.job_id, parent.job_id)
    assert store.promote_ready_jobs(now=T3, allowed_job_ids=(inside.job_id, ready.job_id)) == (ready.job_id,)
    assert store.get_job(inside.job_id).status is models.JobStatus.DEAD_LETTER
    assert store.get_job(outside.job_id) == outside
    assert store.get_job(outside_due.job_id) == outside_due
    assert store.get_job(parent.job_id) == parent


def test_reaper_keeps_outside_expired_attempt_untouched(tmp_path):
    store, generation = _store(tmp_path)
    inside = _job(store, "inside")
    outside = _job(store, "outside")
    a = _claim(store, generation, "inside", (inside.job_id,))
    b = _claim(store, generation, "outside", (outside.job_id,))
    assert store.reap_expired_attempts(now=T3, allowed_job_ids=(inside.job_id,)) == (a.attempt.attempt_id,)
    assert store.list_attempts(outside.job_id) == (b.attempt,)
    assert store.get_job(outside.job_id).status is models.JobStatus.RUNNING


def test_scoped_child_can_promote_and_claim_from_outside_successful_parent(tmp_path):
    store, generation = _store(tmp_path)
    parent = _job(store, "parent")
    claimed = _claim(store, generation, "parent", (parent.job_id,), lease_until=T9)
    store.finish_attempt(
        attempt_id=claimed.attempt.attempt_id, lease_token=claimed.attempt.lease_token,
        runtime_generation=generation, finished_at=T2,
        result=models.HandlerResult(
            outcome=models.HandlerOutcome.SUCCEEDED, result={"parent": True},
            artifacts=(), effects=(),
            metrics=models.HandlerMetrics(tokens=0, cost_usd=0, duration_ms=0), error=None,
        ),
    )
    child = _job(store, "child", status=models.JobStatus.PLANNED)
    store.add_job_dependency(child.job_id, parent.job_id)
    assert store.promote_ready_jobs(now=T3, allowed_job_ids=(child.job_id,)) == (child.job_id,)
    assert _claim(store, generation, "child", (child.job_id,), now=T3, lease_until=T9).job.job_id == child.job_id
    assert store.get_job(parent.job_id).status is models.JobStatus.SUCCEEDED


@pytest.mark.parametrize("expired", [False, True])
def test_outbox_scope_skips_earlier_pending_and_expired_leases(tmp_path, expired):
    store, generation = _store(tmp_path)
    outside = _job(store, "outside")
    effect, _ = _effect(store, generation, outside)
    if expired:
        assert _outbox(store, generation, (outside.job_id,), now=T2, lease_until=T2) is not None
    inside = _job(store, "inside")
    inside_effect, _ = _effect(store, generation, inside, finished_at=T3)
    before = store.get_outbox_entry(f"outbox-{effect.effect_id}")
    assert _outbox(store, generation, (inside.job_id,)).effect_id == inside_effect.effect_id
    assert store.get_outbox_entry(f"outbox-{effect.effect_id}") == before


def test_empty_scope_never_enters_write_transaction(tmp_path, monkeypatch):
    store, generation = _store(tmp_path)
    _job(store, "outside", status=models.JobStatus.PLANNED)
    def unexpected_write(*args, **kwargs):
        raise AssertionError("empty scope entered write transaction")
    monkeypatch.setattr(store, "_write_transaction", unexpected_write)
    assert _claim(store, generation, "empty", ()) is None
    assert _outbox(store, generation, ()) is None
    assert store.promote_ready_jobs(now=T3, allowed_job_ids=()) == ()
    assert store.reap_expired_attempts(now=T3, allowed_job_ids=()) == ()


@pytest.mark.parametrize("scope", [("",), (" padded",), ("padded ",), (None,), (42,), "job-inside", tuple(f"job-{i}" for i in range(901))])
def test_invalid_scopes_fail_before_any_mutation(tmp_path, scope):
    store, generation = _store(tmp_path)
    outside = _job(store, "outside")
    expected = TypeError if isinstance(scope, str) else ValueError
    with pytest.raises(expected, match="must"):
        _claim(store, generation, "invalid", scope)
    assert store.get_job(outside.job_id) == outside
    assert store.list_attempts(outside.job_id) == ()


def test_900_unique_scope_and_deduplication_and_sql_parameters(tmp_path):
    store, generation = _store(tmp_path)
    inside = _job(store, "inside")
    scope = (inside.job_id,) + tuple(f"missing-{i}" for i in range(899))
    assert _claim(store, generation, "900", scope).job.job_id == inside.job_id
    other = _job(store, "other")
    assert _claim(store, generation, "injection", ("' OR 1=1 --",)) is None
    assert _claim(store, generation, "duplicates", (other.job_id,) * 1000).job.job_id == other.job_id


def test_prepared_scope_is_applied_before_limit_and_reconcile_activates_only_batch(tmp_path):
    store, generation = _store(tmp_path)
    artifacts = _artifacts(tmp_path)
    for i in range(101):
        _prepare(artifacts, f"outside-{i:03}", b'{"outside":true}', timestamp=T0)
    outside = _job(store, "outside")
    outside_effect, outside_payload = _effect(store, generation, outside)
    outside_version = _prepare(artifacts, outside_effect.effect_id, outside_payload, timestamp=T0)
    outside_lease = _outbox(store, generation, (outside.job_id,))
    store.ack_outbox(outbox_id=outside_lease.outbox_id, lease_token=outside_lease.lease_token,
                     runtime_generation=generation, verified_at=T3, actual_after_hash=outside_version.content_sha256)
    inside = _job(store, "inside")
    effect, payload = _effect(store, generation, inside)
    version = _prepare(artifacts, effect.effect_id, payload)
    lease = _outbox(store, generation, (inside.job_id,))
    store.ack_outbox(outbox_id=lease.outbox_id, lease_token=lease.lease_token,
                     runtime_generation=generation, verified_at=T3, actual_after_hash=version.content_sha256)
    assert artifacts.prepared_effects(allowed_effect_ids=(effect.effect_id,), limit=1) == (version,)
    dispatcher = NarrativeEffectDispatcher(store, artifacts, allowed_job_ids=(inside.job_id,))
    assert dispatcher.reconcile_prepared(activated_at=T3, limit=1) == (effect.effect_id,)
    remaining = artifacts.prepared_effects(limit=200)
    assert len(remaining) == 102
    assert outside_version in remaining
    assert artifacts.read_visible(document_id="document", source_id="source", source_sha256=SHA)[1] == payload
    assert dispatcher.reconcile_prepared(activated_at=T3) == ()


def test_empty_dispatcher_does_not_access_outbox_or_catalog(tmp_path, monkeypatch):
    store, generation = _store(tmp_path)
    artifacts = _artifacts(tmp_path)
    dispatcher = NarrativeEffectDispatcher(store, artifacts, allowed_job_ids=())
    def unexpected(*args, **kwargs):
        raise AssertionError("empty dispatcher accessed work stores")
    monkeypatch.setattr(store, "claim_next_outbox", unexpected)
    monkeypatch.setattr(artifacts, "prepared_effects", unexpected)
    assert dispatcher.dispatch_next(worker_id="empty", now=T3, lease_until=T9, expected_generation=generation).status == "empty"
    assert dispatcher.reconcile_prepared(activated_at=T3) == ()


def test_dispatcher_forwards_scope_to_claim_before_preparation(tmp_path, monkeypatch):
    store, generation = _store(tmp_path)
    artifacts = _artifacts(tmp_path)
    outside = _job(store, "outside")
    outside_effect, _ = _effect(store, generation, outside)
    inside = _job(store, "inside")
    inside_effect, _ = _effect(store, generation, inside, finished_at=T3)
    before = store.get_outbox_entry(f"outbox-{outside_effect.effect_id}")
    dispatcher = NarrativeEffectDispatcher(store, artifacts, allowed_job_ids=(inside.job_id,))
    from company_wiki.automation.narrative_projection import NarrativeProjectionError
    prepared = []
    def preparation_boundary(effect_id):
        prepared.append(effect_id)
        raise NarrativeProjectionError("fixture stops after scoped claim")
    monkeypatch.setattr(dispatcher, "_prepare_effect", preparation_boundary)
    dispatcher.dispatch_next(worker_id="projector", now=T3, lease_until=T9, expected_generation=generation)
    assert prepared == [inside_effect.effect_id]
    assert store.get_outbox_entry(f"outbox-{outside_effect.effect_id}") == before


def test_empty_worker_does_not_read_runtime_or_reap(tmp_path, monkeypatch):
    store, _ = _store(tmp_path)
    worker = Worker(store, create_default_registry(), HandlerExecutor(), allowed_job_ids=())
    def unexpected(*args, **kwargs):
        raise AssertionError("empty worker touched store")
    monkeypatch.setattr(store, "read_runtime_gate", unexpected)
    monkeypatch.setattr(store, "reap_expired_attempts", unexpected)
    assert worker.process_one() is False
    assert worker.reap_expired() == 0


def test_scoped_supervisor_real_spawn_executes_only_batch_and_keeps_outside_due_jobs(tmp_path):
    store, _ = _store(tmp_path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    outside = _job(store, "outside", priority=999, job_type="test.compute", timestamp=now)
    due = _job(store, "outside-due", status=models.JobStatus.PLANNED, job_type="test.compute", timestamp=now)
    inside = _job(store, "inside", job_type="test.compute", timestamp=now)
    config = SupervisorConfig(
        db_path=store.db_path, log_dir=tmp_path / "logs", profile="P1",
        runtime_factory_path="support.automation_worker_fixture:create_runtime",
        runtime_options_json=json.dumps({"trace_dir": str(tmp_path / "trace")}),
        compute_job_types=("test.compute",), model_job_types=("test.model",),
        lease_seconds=5, heartbeat_interval_seconds=0.1, idle_sleep_seconds=0.03,
        maintenance_interval_seconds=0.05, stop_grace_seconds=0.5,
        allowed_job_ids=(inside.job_id, inside.job_id),
    )
    assert config.allowed_job_ids == (inside.job_id,)
    spec = WorkerProcessSpec("test", "compute", str(store.db_path), str(tmp_path / "logs"),
                             config.runtime_factory_path, config.runtime_options_json,
                             config.compute_job_types, 5, 0.1, 0.03, 4096,
                             allowed_job_ids=(inside.job_id, inside.job_id))
    assert spec.allowed_job_ids == (inside.job_id,)
    supervisor = AutomationSupervisor(config)
    try:
        supervisor.start()
        supervisor.wait_for_terminal((inside.job_id,), timeout_seconds=15)
    finally:
        supervisor.stop()
    assert store.get_job(inside.job_id).status is models.JobStatus.SUCCEEDED
    assert store.get_job(outside.job_id) == outside
    assert store.get_job(due.job_id) == due
    assert store.list_attempts(outside.job_id) == ()
    assert len(list((tmp_path / "trace").glob(f"handler_started--{inside.job_id}--*.json"))) == 1
