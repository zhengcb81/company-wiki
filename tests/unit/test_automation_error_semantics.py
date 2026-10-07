"""Machine failure/recovery contracts; no review receipts, providers or production writes."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from company_wiki.automation import models as m
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.retry import classify_outcome
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from company_wiki.automation.worker import HandlerExecutor, Worker
from company_wiki.source_contract import source_id_for_sha256


T0 = "2026-10-07T10:00:00Z"
T1 = "2026-10-07T10:01:00Z"
T2 = "2026-10-07T10:02:00Z"


class _Clock:
    def now(self) -> str:
        return T1


def _seed(
    root: Path, *, job_type: str = "source.narrative_select",
    version: str | None = None, status: m.JobStatus = m.JobStatus.READY,
    max_attempts: int = 3,
) -> tuple[AutomationStore, m.Job]:
    store = AutomationStore(root / "automation.sqlite3")
    raw_digest = m.canonical_json_hash({"source": "original text"})
    payload = {
        "schema_version": "source-revision-event/2.0",
        "source_ref": {
            "schema_version": "2.0", "document_id": "document-one",
            "source_id": source_id_for_sha256(raw_digest), "content_sha256": raw_digest,
            "byte_size": 19, "mime_type": "text/plain",
        },
        "expected_read_policy_sha256": "a" * 64,
        "source_metadata": {"source_class": "transcript", "title": "Original call",
                            "document_kind": "earnings_call_transcript", "language": "en"},
    }
    digest = SourceRevisionEventPayload.from_dict(payload).input_hash
    event = m.Event(
        "event-one", "source.revision_registered", "source_revision", "document-one",
        digest, m.canonical_json(payload), "v1", T0, T0,
    )
    store.put_event(event)
    handler_version = version or create_default_registry().get(job_type).handler_version
    job = m.Job(
        "job-one", m.make_job_key(job_type, "source_revision", "document-one", digest, "v1", handler_version),
        job_type, "source_revision", "document-one", digest, "v1", handler_version,
        m.RiskClass.LOW, status, 0, T0, max_attempts, event.event_id, T0, T0,
        None, None,
    )
    store.put_job(job)
    store.set_runtime_gate(m.RuntimeState.ENABLED, updated_at=T0)
    return store, job


def _failure(code: str, outcome: m.HandlerOutcome = m.HandlerOutcome.RETRYABLE) -> m.HandlerResult:
    return m.HandlerResult(
        outcome, {"reason": "original machine cause"}, (), (),
        m.HandlerMetrics(tokens=7, cost_usd=0.001, duration_ms=3),
        m.HandlerError(code, "field=source_id; original machine cause"),
    )


@pytest.mark.parametrize(
    ("job_type", "error_code"),
    [
        ("source.narrative_select", "PARSER_INCOMPLETE"),
        ("source.narrative_select", "SOURCE_UNAVAILABLE"),
        ("source.narrative_summarize", "MODEL_NOT_CONFIGURED"),
        ("source.narrative_verify", "LOCATOR_REPLAY_FAILED"),
        ("source.narrative_verify", "SOURCE_UNAVAILABLE"),
    ],
)
def test_configuration_and_data_errors_are_machine_failures(job_type: str, error_code: str) -> None:
    spec = create_default_registry().get(job_type)
    status, returned_code = classify_outcome(
        m.HandlerOutcome.RETRYABLE, error_code, spec.retryable_errors,
        spec.human_errors, spec.terminal_errors, 1, spec.default_max_attempts,
    )
    assert (status, returned_code) == (m.JobStatus.DEAD_LETTER, error_code)
    assert spec.human_errors == ()
    assert spec.handler_version == "1.1.0"


def test_legacy_blocked_outcome_does_not_create_new_manual_work() -> None:
    status, code = classify_outcome(
        m.HandlerOutcome("blocked_human"), "REVIEW_PENDING", (), ("REVIEW_PENDING",), (), 1, 3,
    )
    assert (status, code) == (m.JobStatus.DEAD_LETTER, "REVIEW_PENDING")


@pytest.mark.parametrize("code", ["SOURCE_HASH_MISMATCH", "LOCATOR_REPLAY_FAILED"])
def test_invalid_source_evidence_cannot_be_relabelled_as_success(code: str) -> None:
    spec = create_default_registry().get("source.narrative_verify")
    status, returned = classify_outcome(
        m.HandlerOutcome.RETRYABLE, code, spec.retryable_errors, spec.human_errors,
        spec.terminal_errors, 1, 3,
    )
    assert (status, returned) == (m.JobStatus.DEAD_LETTER, code)


@pytest.mark.parametrize("code", ["MODEL_TIMEOUT", "MODEL_RATE_LIMIT", "IO_TRANSIENT"])
def test_transient_model_and_io_errors_have_finite_attempts(code: str) -> None:
    spec = create_default_registry().get("source.narrative_summarize")
    assert [
        classify_outcome(m.HandlerOutcome.RETRYABLE, code, spec.retryable_errors,
                         spec.human_errors, spec.terminal_errors, attempt, 3)[0]
        for attempt in (1, 2, 3)
    ] == [m.JobStatus.RETRY_WAIT, m.JobStatus.RETRY_WAIT, m.JobStatus.DEAD_LETTER]


def test_worker_preserves_failure_details_metrics_and_terminalizes_dependents(tmp_path: Path) -> None:
    store, parent = _seed(tmp_path)
    child = replace(
        parent, job_id="job-child", job_type="source.narrative_summarize",
        job_key=m.make_job_key("source.narrative_summarize", parent.subject_type, parent.subject_id,
                              parent.input_hash, parent.policy_version, parent.handler_version),
        status=m.JobStatus.PLANNED,
    )
    store.put_job(child)
    store.add_job_dependency(child.job_id, parent.job_id)
    executor = HandlerExecutor()
    raw = _failure("PARSER_INCOMPLETE")
    executor.register(parent.job_type, lambda _: raw)
    assert Worker(store, create_default_registry(), executor, clock=_Clock()).process_one()
    failed = store.get_job(parent.job_id)
    assert failed.status is m.JobStatus.DEAD_LETTER
    assert (failed.last_error_code, failed.last_error_detail) == (raw.error.code, raw.error.detail)
    attempt = store.list_attempts(parent.job_id)[0]
    stored_result = m.HandlerResult.from_dict(json.loads(attempt.result_json))
    assert stored_result.metrics == raw.metrics
    assert stored_result.result == raw.result
    assert stored_result.outcome is m.HandlerOutcome.TERMINAL_FAILURE
    assert store.promote_ready_jobs(now=T2) == ()
    assert store.get_job(child.job_id).status is m.JobStatus.DEAD_LETTER
    assert store.get_job(child.job_id).last_error_code == "DEPENDENCY_TERMINAL"
    assert store.list_effects(parent.job_id) == ()
    assert store.list_outbox_entries() == ()


def test_worker_respects_persisted_attempt_limit(tmp_path: Path) -> None:
    store, job = _seed(tmp_path, max_attempts=1)
    executor = HandlerExecutor()
    executor.register(job.job_type, lambda _: _failure("IO_TRANSIENT"))
    assert Worker(store, create_default_registry(), executor, clock=_Clock()).process_one()
    assert store.get_job(job.job_id).status is m.JobStatus.DEAD_LETTER
    assert len(store.list_attempts(job.job_id)) == 1


def test_old_handler_identity_is_not_executed_with_new_semantics(tmp_path: Path) -> None:
    store, job = _seed(tmp_path, version="1.0.0")
    executor = HandlerExecutor()
    calls: list[object] = []
    executor.register(job.job_type, lambda context: calls.append(context))
    assert Worker(store, create_default_registry(), executor, clock=_Clock()).process_one()
    assert calls == []
    failed = store.get_job(job.job_id)
    assert failed.status is m.JobStatus.DEAD_LETTER
    assert failed.last_error_code == "HANDLER_VERSION_MISMATCH"
    assert "1.0.0" in failed.last_error_detail and "1.1.0" in failed.last_error_detail
    assert store.list_attempts(job.job_id)[0].result_json is not None


def test_historical_blocked_record_remains_readable_and_has_no_review_receipt(tmp_path: Path) -> None:
    store, historical = _seed(tmp_path, version="1.0.0", status=m.JobStatus.BLOCKED_HUMAN)
    assert store.get_job(historical.job_id) == historical
    assert m.Job.from_dict(historical.to_dict()).status is m.JobStatus.BLOCKED_HUMAN
    ready = store.transition_job(
        historical.job_id, expected=m.JobStatus.BLOCKED_HUMAN,
        target=m.JobStatus.READY, updated_at=T1,
    )
    assert ready.handler_version == historical.handler_version
    assert ready.input_hash == historical.input_hash
    assert store.list_attempts(historical.job_id) == ()


def test_atomic_store_normalizes_legacy_outcome_without_erasing_metrics(tmp_path: Path) -> None:
    store, job = _seed(tmp_path)
    gate = store.read_runtime_gate()
    claimed = store.claim_next_ready(
        worker_id="worker", attempt_id="attempt", lease_token="lease", now=T1,
        lease_until=T2, expected_generation=gate.control_generation,
    )
    raw = _failure("MODEL_NOT_CONFIGURED", m.HandlerOutcome.BLOCKED_HUMAN)
    attempt = store.finish_attempt(
        attempt_id=claimed.attempt.attempt_id, lease_token="lease",
        runtime_generation=gate.control_generation, finished_at=T1, result=raw,
    )
    assert store.get_job(job.job_id).status is m.JobStatus.DEAD_LETTER
    assert attempt.outcome is m.HandlerOutcome.TERMINAL_FAILURE
    assert attempt.error_code == raw.error.code
    assert '"tokens":7' in attempt.result_json
    assert store.list_outbox_entries() == ()


def test_corrected_configuration_uses_new_event_and_keeps_historical_usage(tmp_path: Path) -> None:
    store, historical = _seed(tmp_path, version="1.0.0", status=m.JobStatus.BLOCKED_HUMAN)
    raw = _failure("MODEL_NOT_CONFIGURED", m.HandlerOutcome.BLOCKED_HUMAN)
    historical_attempt = m.Attempt(
        "historical-attempt", historical.job_id, 1, "old-worker", "old-lease", T1,
        T0, T0, T0, raw.outcome, m.canonical_json(raw.to_dict()),
        raw.error.code, raw.error.detail,
    )
    store.put_attempt(historical_attempt)
    old_event = store.get_event(historical.created_from_event_id)
    corrected_intent_hash = m.canonical_json_hash({"run_id": "corrected", "model_config": "configured"})
    event = replace(
        old_event, event_id="corrected-event",
        policy_version="narrative-batch/1:" + corrected_intent_hash,
        occurred_at=T1, observed_at=T1,
    )
    scheduler = AutomationScheduler(
        store, create_default_registry(), PolicyConfig(allow_llm=True, allow_network=True),
    )
    scheduler.materialize_event(store.put_event(event).value)
    current = next(job for job in store.list_jobs(event_ids=(event.event_id,))
                   if job.job_type == "source.narrative_select")
    assert current.handler_version == "1.1.0"
    assert current.job_key != historical.job_key
    executor = HandlerExecutor()
    executor.register(current.job_type, lambda _: m.HandlerResult(
        m.HandlerOutcome.SUCCEEDED, {"selected": 1}, (), (),
        m.HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=1), None,
    ))
    assert Worker(store, create_default_registry(), executor, clock=_Clock(),
                  allowed_job_ids=(current.job_id,)).process_one()
    assert store.get_job(current.job_id).status is m.JobStatus.SUCCEEDED
    assert store.get_job(historical.job_id) == historical
    assert store.get_attempt(historical_attempt.attempt_id) == historical_attempt
    assert '"cost_usd":0.001' in store.get_attempt(historical_attempt.attempt_id).result_json
