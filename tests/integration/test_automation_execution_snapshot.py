from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import sqlite3
import threading
from pathlib import Path

import pytest

from company_wiki.automation import models
from company_wiki.automation import execution_snapshot as snapshot_module
from company_wiki.automation.execution_snapshot import ExecutionSnapshotError
from company_wiki.automation.store import AutomationStore
from company_wiki.source_contract import source_id_for_sha256


T0 = "2026-09-28T14:00:00Z"
T1 = "2026-09-28T14:01:00Z"
T2 = "2026-09-28T14:02:00Z"
T5 = "2026-09-28T14:05:00Z"


def _sha(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _event() -> models.Event:
    source_sha = _sha("snapshot-source")
    payload = {
        "schema_version": "source-revision-event/2.0",
        "source_ref": {
            "schema_version": "2.0",
            "document_id": "doc-snapshot",
            "source_id": source_id_for_sha256(source_sha),
            "content_sha256": source_sha,
            "byte_size": 10,
            "mime_type": "application/pdf",
        },
        "expected_read_policy_sha256": _sha("read-policy"),
        "source_metadata": {
            "source_class": "filing",
            "title": None,
            "document_kind": "annual_report",
            "language": "zh",
        },
    }
    return models.Event(
        event_id="evt-snapshot",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id="doc-snapshot",
        input_hash=models.canonical_json_hash(payload),
        payload_json=models.canonical_json(payload),
        policy_version="narrative-v1",
        occurred_at=T0,
        observed_at=T0,
    )


def _job(event: models.Event, job_type: str, status: models.JobStatus) -> models.Job:
    job_id = "job-" + job_type.rsplit("_", 1)[-1]
    return models.Job(
        job_id=job_id,
        job_key=models.make_job_key(
            job_type, event.subject_type, event.subject_id, event.input_hash,
            event.policy_version, "1.0.0",
        ),
        job_type=job_type,
        subject_type=event.subject_type,
        subject_id=event.subject_id,
        input_hash=event.input_hash,
        policy_version=event.policy_version,
        handler_version="1.0.0",
        risk_class=models.RiskClass.LOW,
        status=status,
        priority=0,
        not_before=T0,
        max_attempts=3,
        created_from_event_id=event.event_id,
        created_at=T0,
        updated_at=T0,
        last_error_code=None,
        last_error_detail=None,
    )


def _success(value: str) -> models.HandlerResult:
    return models.HandlerResult(
        outcome=models.HandlerOutcome.SUCCEEDED,
        result={"value": value},
        artifacts=(),
        effects=(),
        metrics=models.HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=1),
        error=None,
    )


def _seed_claimed_child(tmp_path: Path) -> tuple[AutomationStore, models.ClaimedWork]:
    store = AutomationStore(tmp_path / "automation.db")
    event = _event()
    parent = _job(event, "source.narrative_select", models.JobStatus.READY)
    child = _job(event, "source.narrative_summarize", models.JobStatus.PLANNED)
    store.put_event(event)
    store.put_job(parent)
    store.put_job(child)
    store.add_job_dependency(child.job_id, parent.job_id)
    generation = store.set_runtime_gate(
        models.RuntimeState.ENABLED, updated_at=T1
    ).control_generation
    claimed_parent = store.claim_next_ready(
        worker_id="worker-parent",
        attempt_id="attempt-parent",
        lease_token="lease-parent",
        now=T1,
        lease_until=T5,
        expected_generation=generation,
        allowed_job_types=(parent.job_type,),
    )
    assert claimed_parent is not None
    store.finish_attempt(
        attempt_id=claimed_parent.attempt.attempt_id,
        lease_token=claimed_parent.attempt.lease_token,
        runtime_generation=generation,
        finished_at=T2,
        result=_success("old"),
        retry_not_before=None,
        outbox_not_before=T2,
    )
    assert store.promote_ready_jobs(now=T2) == (child.job_id,)
    claimed_child = store.claim_next_ready(
        worker_id="worker-child",
        attempt_id="attempt-child",
        lease_token="lease-child",
        now=T2,
        lease_until=T5,
        expected_generation=generation,
        allowed_job_types=(child.job_type,),
    )
    assert claimed_child is not None
    return store, claimed_child


def test_snapshot_returns_event_and_latest_successful_direct_dependency(
    tmp_path: Path,
) -> None:
    store, claimed = _seed_claimed_child(tmp_path)

    snapshot = store.read_execution_snapshot(claimed, now=T2)

    assert snapshot.job == claimed.job
    assert snapshot.attempt == claimed.attempt
    assert snapshot.event == _event()
    assert len(snapshot.dependencies) == 1
    dependency = snapshot.dependencies[0]
    assert dependency.job_type == "source.narrative_select"
    assert dependency.attempt_id == "attempt-parent"
    assert dependency.result.result["value"] == "old"


@pytest.mark.parametrize("mutation", ["token", "generation", "expired"])
def test_snapshot_rejects_stale_claims(tmp_path: Path, mutation: str) -> None:
    store, claimed = _seed_claimed_child(tmp_path)
    if mutation == "token":
        attempt = replace(claimed.attempt, lease_token="wrong-token")
        now = T2
    elif mutation == "generation":
        attempt = replace(claimed.attempt, runtime_generation=99)
        now = T2
    else:
        attempt = claimed.attempt
        now = "2026-09-28T14:06:00Z"
    stale = models.ClaimedWork(claimed.job, attempt)

    with pytest.raises(ExecutionSnapshotError):
        store.read_execution_snapshot(stale, now=now)


def test_snapshot_rejects_malformed_dependency_result(tmp_path: Path) -> None:
    store, claimed = _seed_claimed_child(tmp_path)
    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE attempts SET result_json=? WHERE attempt_id='attempt-parent'",
            (models.canonical_json({"malformed": True}),),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ExecutionSnapshotError, match="dependency result"):
        store.read_execution_snapshot(claimed, now=T2)


def test_snapshot_maps_corrupt_runtime_gate_to_domain_error(tmp_path: Path) -> None:
    store, claimed = _seed_claimed_child(tmp_path)
    connection = sqlite3.connect(store.db_path)
    try:
        connection.execute(
            "UPDATE runtime_gate SET updated_at='corrupt' WHERE singleton_id=1"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ExecutionSnapshotError, match="record is invalid"):
        store.read_execution_snapshot(claimed, now=T2)


def test_snapshot_is_one_sqlite_read_view_during_concurrent_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, claimed = _seed_claimed_child(tmp_path)
    event_read = threading.Event()
    writer_done = threading.Event()
    writer_errors: list[BaseException] = []
    original = snapshot_module._event_for_job

    def observed_event(connection: sqlite3.Connection, job: models.Job) -> models.Event:
        value = original(connection, job)
        event_read.set()
        assert writer_done.wait(timeout=5)
        return value

    monkeypatch.setattr(snapshot_module, "_event_for_job", observed_event)

    def writer() -> None:
        try:
            assert event_read.wait(timeout=5)
            connection = sqlite3.connect(store.db_path, timeout=5)
            try:
                replacement = _success("new")
                connection.execute(
                    "UPDATE attempts SET result_json=? WHERE attempt_id='attempt-parent'",
                    (models.canonical_json(replacement.to_dict()),),
                )
                connection.commit()
            finally:
                connection.close()
        except BaseException as exc:  # pragma: no cover - asserted below
            writer_errors.append(exc)
        finally:
            writer_done.set()

    thread = threading.Thread(target=writer)
    thread.start()
    snapshot = store.read_execution_snapshot(claimed, now=T2)
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert writer_errors == []
    assert snapshot.dependencies[0].result.result["value"] == "old"
    persisted = store.get_attempt("attempt-parent")
    assert persisted is not None
    assert json.loads(persisted.result_json)["result"]["value"] == "new"

