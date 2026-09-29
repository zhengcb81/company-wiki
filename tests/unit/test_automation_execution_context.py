from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib

import pytest

from company_wiki.automation import models
from company_wiki.automation.execution_context import (
    ExecutionContextError,
    ExecutionContextFactory,
    JobExecutionContext,
)
from company_wiki.automation.execution_snapshot import (
    DependencyExecutionResult,
    ExecutionSnapshot,
)
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.source_contract import source_id_for_sha256


T0 = "2026-09-28T13:00:00Z"
T1 = "2026-09-28T13:01:00Z"


def _sha(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _payload() -> dict:
    source_sha = _sha("source")
    return {
        "schema_version": "source-revision-event/2.0",
        "source_ref": {
            "schema_version": "2.0",
            "document_id": "doc-ctx",
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


def _event(*, payload: dict | None = None) -> models.Event:
    body = payload or _payload()
    return models.Event(
        event_id="evt-ctx",
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id="doc-ctx",
        input_hash=models.canonical_json_hash(body),
        payload_json=models.canonical_json(body),
        policy_version="narrative-v1",
        occurred_at=T0,
        observed_at=T0,
    )


def _job(job_type: str, *, job_id: str = "job-ctx") -> models.Job:
    event = _event()
    return models.Job(
        job_id=job_id,
        job_key=models.make_job_key(
            job_type,
            event.subject_type,
            event.subject_id,
            event.input_hash,
            event.policy_version,
            "1.0.0",
        ),
        job_type=job_type,
        subject_type=event.subject_type,
        subject_id=event.subject_id,
        input_hash=event.input_hash,
        policy_version=event.policy_version,
        handler_version="1.0.0",
        risk_class=models.RiskClass.LOW,
        status=models.JobStatus.RUNNING,
        priority=0,
        not_before=T0,
        max_attempts=3,
        created_from_event_id=event.event_id,
        created_at=T0,
        updated_at=T1,
        last_error_code=None,
        last_error_detail=None,
    )


def _attempt(job_id: str = "job-ctx") -> models.Attempt:
    return models.Attempt(
        attempt_id="attempt-ctx",
        job_id=job_id,
        attempt_no=1,
        worker_id="worker-ctx",
        lease_token="lease-ctx",
        lease_until="2026-09-28T13:05:00Z",
        started_at=T1,
        heartbeat_at=T1,
        finished_at=None,
        outcome=None,
        result_json=None,
        error_code=None,
        error_detail=None,
        runtime_generation=2,
    )


def _result(value: str = "selected") -> models.HandlerResult:
    return models.HandlerResult(
        outcome=models.HandlerOutcome.SUCCEEDED,
        result={"value": value},
        artifacts=(),
        effects=(),
        metrics=models.HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=1),
        error=None,
    )


def _dependency(job_type: str = "source.narrative_select") -> DependencyExecutionResult:
    return DependencyExecutionResult(
        job_id="job-parent",
        job_type=job_type,
        handler_version="1.0.0",
        attempt_id="attempt-parent",
        attempt_no=1,
        result=_result(),
    )


def _snapshot(job_type: str, dependencies: tuple[DependencyExecutionResult, ...]) -> ExecutionSnapshot:
    job = _job(job_type)
    return ExecutionSnapshot(
        job=job,
        attempt=_attempt(job.job_id),
        event=_event(),
        dependencies=dependencies,
    )


class SnapshotStore:
    def __init__(self, snapshot: ExecutionSnapshot):
        self.snapshot = snapshot
        self.calls: list[tuple[str, str]] = []

    def read_execution_snapshot(self, claimed: models.ClaimedWork, *, now: str) -> ExecutionSnapshot:
        self.calls.append((claimed.job.job_id, now))
        return self.snapshot


def test_factory_builds_immutable_source_context_and_checkpoint() -> None:
    snapshot = _snapshot("source.narrative_summarize", (_dependency(),))
    store = SnapshotStore(snapshot)
    checkpoints: list[str] = []
    factory = ExecutionContextFactory(store)

    context = factory.create(
        models.ClaimedWork(snapshot.job, snapshot.attempt),
        now=T1,
        checkpoint=lambda: checkpoints.append("checked"),
    )

    assert isinstance(context, JobExecutionContext)
    assert isinstance(context.source_revision, SourceRevisionEventPayload)
    assert context.job is snapshot.job
    assert context.attempt is snapshot.attempt
    assert context.dependency_results["source.narrative_select"].result["value"] == "selected"
    assert store.calls == [(snapshot.job.job_id, T1)]
    context.checkpoint()
    assert checkpoints == ["checked"]
    with pytest.raises(FrozenInstanceError):
        context.event = _event()  # type: ignore[misc]
    with pytest.raises(TypeError):
        context.dependency_results["extra"] = _result()  # type: ignore[index]


@pytest.mark.parametrize(
    "job_type,dependencies",
    [
        ("source.narrative_select", (_dependency(),)),
        ("source.narrative_summarize", ()),
        ("source.narrative_verify", (_dependency(),)),
    ],
)
def test_factory_rejects_missing_extra_or_duplicate_narrative_dependencies(
    job_type: str, dependencies: tuple[DependencyExecutionResult, ...]
) -> None:
    snapshot = _snapshot(job_type, dependencies)
    with pytest.raises(ExecutionContextError, match="dependencies"):
        ExecutionContextFactory(SnapshotStore(snapshot)).create(
            models.ClaimedWork(snapshot.job, snapshot.attempt),
            now=T1,
            checkpoint=lambda: None,
        )


def test_snapshot_model_rejects_duplicate_dependency_job_types() -> None:
    with pytest.raises(ValueError, match="unique"):
        _snapshot(
            "source.narrative_verify",
            (_dependency(), _dependency("source.narrative_select")),
        )


def test_factory_rejects_malformed_source_event_and_identity_drift() -> None:
    snapshot = _snapshot("source.narrative_select", ())
    malformed_event = _event(payload={"not": "a source event"})
    malformed_job_data = snapshot.job.to_dict()
    malformed_job_data["input_hash"] = malformed_event.input_hash
    malformed_job_data["job_key"] = models.make_job_key(
        malformed_job_data["job_type"],
        malformed_job_data["subject_type"],
        malformed_job_data["subject_id"],
        malformed_event.input_hash,
        malformed_job_data["policy_version"],
        malformed_job_data["handler_version"],
    )
    malformed_job = models.Job.from_dict(malformed_job_data)
    malformed = ExecutionSnapshot(
        job=malformed_job,
        attempt=_attempt(malformed_job.job_id),
        event=malformed_event,
        dependencies=(),
    )
    with pytest.raises(ExecutionContextError, match="source revision payload"):
        ExecutionContextFactory(SnapshotStore(malformed)).create(
            models.ClaimedWork(snapshot.job, snapshot.attempt),
            now=T1,
            checkpoint=lambda: None,
        )

    wrong_data = {**snapshot.job.to_dict(), "subject_id": "other"}
    wrong_data["job_key"] = models.make_job_key(
        wrong_data["job_type"],
        wrong_data["subject_type"],
        wrong_data["subject_id"],
        wrong_data["input_hash"],
        wrong_data["policy_version"],
        wrong_data["handler_version"],
    )
    wrong_subject = models.Job.from_dict(wrong_data)
    drift = ExecutionSnapshot(
        job=wrong_subject,
        attempt=_attempt(wrong_subject.job_id),
        event=snapshot.event,
        dependencies=(),
    )
    with pytest.raises(ExecutionContextError, match="identity"):
        JobExecutionContext.from_snapshot(drift, checkpoint=lambda: None)


def test_generic_job_keeps_canonical_payload_without_source_parser() -> None:
    payload = {"fixture": "generic"}
    event = _event(payload=payload)
    job = _job("timer.execute_step")
    job = models.Job.from_dict(
        {
            **job.to_dict(),
            "input_hash": event.input_hash,
            "job_key": models.make_job_key(
                job.job_type,
                job.subject_type,
                job.subject_id,
                event.input_hash,
                job.policy_version,
                job.handler_version,
            ),
        }
    )
    snapshot = ExecutionSnapshot(job, _attempt(job.job_id), event, ())

    context = ExecutionContextFactory(SnapshotStore(snapshot)).create(
        models.ClaimedWork(job, snapshot.attempt), now=T1, checkpoint=lambda: None
    )

    assert context.source_revision is None
    assert dict(context.payload) == payload

