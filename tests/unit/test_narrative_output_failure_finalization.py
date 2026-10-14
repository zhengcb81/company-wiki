"""Final output quota and attempt lifecycle commit in the same fenced AUTO write."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import (
    ArtifactRef, HandlerError, HandlerMetrics, HandlerOutcome, HandlerResult,
    JobStatus, RuntimeState, canonical_json, make_job_key,
)
from company_wiki.automation.narrative_model import FailedFinalDiagnostic
from company_wiki.automation import narrative_run_store as accounting
from company_wiki.automation.store import (
    IntegrityViolationError, LeaseLostError, RuntimeGateClosedError, RuntimeGenerationError,
)
from unit.test_narrative_run_store import (
    setup_run, claim, reserve, create_run, seed_job, T1, T2, T3, T9, RESPONSE,
)
from unit.test_automation_store_atomic import _effect
from support import narrative_batch_fixtures as fixtures
from integration.test_narrative_failed_final_cli import _invoke, _dump

loopback_model_server = fixtures.loopback_model_server


@pytest.fixture(autouse=True)
def protected_production_config():
    root = Path(__file__).resolve().parents[2]
    protected = {path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, path.stat().st_mtime_ns)
                 for path in (root / "config.yaml", root / "config/source_catalog.yaml")}
    yield
    assert all((hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, path.stat().st_mtime_ns) == saved
               for path, saved in protected.items())


@pytest.fixture
def lake():
    with tempfile.TemporaryDirectory(prefix="cw-output-finalization-") as name:
        root = Path(name)
        original = root / "original.txt"
        original.write_bytes(b"immutable original fixture")
        sentinel = root / "existing.txt"
        sentinel.write_bytes(b"restore original test directory")
        try:
            yield root
        finally:
            assert original.read_bytes() == b"immutable original fixture"
            assert sentinel.read_bytes() == b"restore original test directory"
    assert not root.exists()


def state(root, status="known", *, other_type=False):
    _, auto, ledger, generation, a, b = setup_run(root)
    if other_type:
        # A separate ordinary worker job is legally included in its run scope;
        # its lifecycle must not trigger this source-summary-specific rule.
        auto = type(auto)(root / "other.db")
        template = seed_job(auto, "other")
        a = replace(template, job_id="job-ordinary", job_type="test.other",
                    job_key=make_job_key("test.other", template.subject_type, template.subject_id,
                                        template.input_hash, template.policy_version, template.handler_version))
        auto.put_job(a)
        generation = auto.set_runtime_gate(RuntimeState.ENABLED, updated_at=T1).control_generation
        ledger = accounting.NarrativeRunStore(auto.db_path)
        create_run(ledger, (a,))
        b = None
    work = claim(auto, generation, a)
    reserve(ledger, work)
    if status != "reserved":
        ledger.settle_model_usage(run_id="run-one", attempt_id=work.attempt.attempt_id,
            usage=accounting.ModelUsage(30, 10) if status == "known" else None,
            response_sha256=RESPONSE if status == "known" else None,
            error_code=None if status == "known" else "MODEL_TRANSPORT_UNKNOWN", settled_at=T1)
    return SimpleNamespace(auto=auto, ledger=ledger, generation=generation, job=a, other_job=b, work=work)


def failure(s, *, outcome=HandlerOutcome.TERMINAL_FAILURE, diagnostic=False, artifacts=(), effects=()):
    record = s.ledger.get_reservation("run-one", s.work.attempt.attempt_id)
    result = {}
    if diagnostic:
        result["failed_final"] = FailedFinalDiagnostic.from_observation(
            provider_body=None, content="bounded invalid model final").to_dict()
    return HandlerResult(outcome, result, artifacts, effects,
        HandlerMetrics(record.charged_tokens, record.charged_micro_usd / 1000000, 1),
        HandlerError("SUMMARY_INVALID", "strict contract failure"))


def finish(s, result, *, now=T2, **overrides):
    args = dict(attempt_id=s.work.attempt.attempt_id, lease_token=s.work.attempt.lease_token,
                runtime_generation=s.work.attempt.runtime_generation, finished_at=now, result=result)
    if result.outcome is HandlerOutcome.RETRYABLE:
        args["retry_not_before"] = T3
    args.update(overrides)
    return s.auto.finish_attempt(**args)


def accounting_fields(record):
    return {key: value for key, value in asdict(record).items()
            if key not in {"output_bytes", "output_sha256", "output_settled_at"}}


@pytest.mark.parametrize("status", ["known", "unknown", "reserved"])
@pytest.mark.parametrize("outcome", [HandlerOutcome.TERMINAL_FAILURE, HandlerOutcome.RETRYABLE])
def test_explicit_failed_summary_releases_only_its_output_slot_with_exact_charges(lake, status, outcome):
    s = state(lake, status)
    old = s.ledger.get_reservation("run-one", s.work.attempt.attempt_id)
    before = s.ledger.budget_snapshot("run-one")
    result = failure(s, outcome=outcome, diagnostic=True)
    completed = finish(s, result)
    new = s.ledger.get_reservation("run-one", s.work.attempt.attempt_id)
    after = s.ledger.budget_snapshot("run-one")
    assert new.output_bytes == 0 and new.output_sha256 is None and new.output_settled_at == T2
    assert accounting_fields(new) == accounting_fields(old)
    assert (after.charged_tokens, after.charged_micro_usd, after.unknown_reservations, after.unsettled_reservations) == (
        before.charged_tokens, before.charged_micro_usd, before.unknown_reservations, before.unsettled_reservations)
    assert after.charged_output_bytes == 0
    assert json.loads(completed.result_json) == result.to_dict()
    assert not s.auto.list_effects(s.job.job_id)
    assert s.auto.get_job(s.job.job_id).status is (
        JobStatus.RETRY_WAIT if outcome is HandlerOutcome.RETRYABLE else JobStatus.DEAD_LETTER)
    if status == "reserved":
        assert s.ledger.settle_finished_attempt_reservations(run_id="run-one", settled_at=T3) == (new.attempt_id,)
        reconciled = s.ledger.get_reservation("run-one", new.attempt_id)
        assert reconciled.usage_status == "unknown" and reconciled.output_bytes == 0
        assert (reconciled.charged_tokens, reconciled.charged_micro_usd) == (old.charged_tokens, old.charged_micro_usd)


def test_other_document_and_lost_previous_attempt_are_not_credited(lake):
    s = state(lake)
    other = claim(s.auto, s.generation, s.other_job)
    unrelated = reserve(s.ledger, other).record
    finish(s, failure(s))
    assert s.ledger.get_reservation("run-one", unrelated.attempt_id) == unrelated
    assert s.ledger.budget_snapshot("run-one").charged_output_bytes == unrelated.output_bytes_bound


def test_current_failed_attempt_never_refunds_a_lost_predecessor_or_reuses_its_charge(lake):
    s = state(lake, "unknown")
    old = s.ledger.get_reservation("run-one", s.work.attempt.attempt_id)
    assert s.auto.reap_expired_attempts(now=T3, allowed_job_ids=(s.job.job_id,)) == (old.attempt_id,)
    s.auto.promote_ready_jobs(now=T9, allowed_job_ids=(s.job.job_id,))
    s.work = s.auto.claim_next_ready(worker_id="new-model", attempt_id="new-attempt", lease_token="new-lease",
        now=T9, lease_until="2026-10-03T10:10:00Z", expected_generation=s.generation, allowed_job_ids=(s.job.job_id,))
    reserve(s.ledger, s.work, now=T9)
    s.ledger.settle_model_usage(run_id="run-one", attempt_id=s.work.attempt.attempt_id,
        usage=accounting.ModelUsage(30, 10), response_sha256=RESPONSE, error_code=None, settled_at=T9)
    before = s.ledger.budget_snapshot("run-one")
    finish(s, failure(s), now=T9)
    assert s.ledger.get_reservation("run-one", s.work.attempt.attempt_id).output_bytes == 0
    assert s.ledger.get_reservation("run-one", old.attempt_id) == old
    after = s.ledger.budget_snapshot("run-one")
    assert after.charged_output_bytes == old.output_bytes_bound
    assert (after.charged_tokens, after.charged_micro_usd) == (before.charged_tokens, before.charged_micro_usd)


@pytest.mark.parametrize("pending_effect", [False, True])
def test_success_keeps_output_reserved_until_real_artifact_settlement(lake, pending_effect):
    s = state(lake)
    old = s.ledger.get_reservation("run-one", s.work.attempt.attempt_id)
    effects = (_effect(s.job.job_id),) if pending_effect else ()
    result = HandlerResult(HandlerOutcome.SUCCEEDED, {}, (), effects, failure(s).metrics, None)
    finish(s, result)
    assert s.ledger.get_reservation("run-one", old.attempt_id) == old
    assert s.auto.get_job(s.job.job_id).status is (JobStatus.VERIFYING if pending_effect else JobStatus.SUCCEEDED)
    settled = s.ledger.settle_output(run_id="run-one", attempt_id=old.attempt_id,
        output_bytes=37, output_sha256=RESPONSE, settled_at=T3)
    assert settled.charged_output_bytes == 37 and accounting_fields(settled) == accounting_fields(old)


def test_other_worker_job_type_does_not_invoke_summary_accounting(lake):
    s = state(lake, other_type=True)
    old = s.ledger.get_reservation("run-one", s.work.attempt.attempt_id)
    finish(s, failure(s))
    assert s.ledger.get_reservation("run-one", old.attempt_id) == old


def test_unmetered_legacy_summary_can_finish_without_creating_accounting(lake):
    _, auto, ledger, generation, job, _ = setup_run(lake)
    work = claim(auto, generation, job)
    result = HandlerResult(HandlerOutcome.TERMINAL_FAILURE, {}, (), (), HandlerMetrics(0, 0, 0), HandlerError("FAIL", "failure"))
    auto.finish_attempt(attempt_id=work.attempt.attempt_id, lease_token=work.attempt.lease_token,
        runtime_generation=generation, finished_at=T2, result=result)
    assert ledger.reservations_for_run("run-one") == ()


@pytest.mark.parametrize("fence", ["lease", "generation", "expired", "not_latest", "paused"])
def test_existing_attempt_fence_prevents_any_output_or_finish_change(lake, fence):
    s = state(lake)
    overrides, now = {}, T2
    if fence == "lease":
        overrides["lease_token"] = "foreign-lease"
    elif fence == "generation":
        overrides["runtime_generation"] = s.generation - 1
    elif fence == "expired":
        now = T3
    elif fence == "not_latest":
        s.auto.put_attempt(replace(s.work.attempt, attempt_id="newer-attempt", attempt_no=2, lease_token="newer-lease"))
    else:
        s.auto.set_runtime_gate(RuntimeState.PAUSED, updated_at=T2)
    before = _dump(s.auto.db_path)
    with pytest.raises((LeaseLostError, RuntimeGenerationError, RuntimeGateClosedError)):
        finish(s, failure(s), now=now, **overrides)
    assert _dump(s.auto.db_path) == before


def test_crash_with_no_returned_result_keeps_unknown_and_output_reservation(lake):
    s = state(lake, "reserved")
    old = s.ledger.get_reservation("run-one", s.work.attempt.attempt_id)
    assert s.auto.reap_expired_attempts(now=T3, allowed_job_ids=(s.job.job_id,)) == (old.attempt_id,)
    s.ledger.settle_finished_attempt_reservations(run_id="run-one", settled_at=T3)
    new = s.ledger.get_reservation("run-one", old.attempt_id)
    assert new.usage_status == "unknown" and new.output_bytes is None
    assert (new.charged_tokens, new.charged_micro_usd, new.charged_output_bytes) == (
        old.charged_tokens, old.charged_micro_usd, old.charged_output_bytes)


@pytest.mark.parametrize("kind", ["effect", "artifact"])
def test_nonempty_publication_result_cannot_get_a_no_output_credit(lake, kind):
    s = state(lake)
    old = s.ledger.get_reservation("run-one", s.work.attempt.attempt_id)
    if kind == "effect":
        before = _dump(s.auto.db_path)
        with pytest.raises(IntegrityViolationError):
            finish(s, failure(s, effects=(_effect(s.job.job_id),)))
        assert _dump(s.auto.db_path) == before
    else:
        finish(s, failure(s, artifacts=(ArtifactRef("artifacts/diagnostic.json", RESPONSE),)))
    assert s.ledger.get_reservation("run-one", old.attempt_id) == old


@pytest.mark.parametrize("prior_bytes", [0, 30])
def test_existing_output_settlement_is_never_overwritten(lake, prior_bytes):
    s = state(lake)
    old = s.ledger.settle_output(run_id="run-one", attempt_id=s.work.attempt.attempt_id,
        output_bytes=prior_bytes, output_sha256=RESPONSE if prior_bytes else None, settled_at=T1)
    before = _dump(s.auto.db_path)
    if prior_bytes:
        with pytest.raises(accounting.ReservationConflictError):
            finish(s, failure(s))
        assert _dump(s.auto.db_path) == before
    else:
        finish(s, failure(s))
    assert s.ledger.get_reservation("run-one", old.attempt_id) == old


def test_output_finish_transaction_rollback_and_retry_use_one_connection(lake, monkeypatch):
    s = state(lake)
    before = _dump(s.auto.db_path)
    implementation = accounting._settle_output_in_transaction
    connections = []
    def after_update(connection, **kwargs):
        connections.append(connection)
        implementation(connection, **kwargs)
        raise OSError("synthetic after output SQL before COMMIT")
    def no_second_store(*_args, **_kwargs):
        pytest.fail("attempt finish must not open a second ledger write transaction")
    monkeypatch.setattr(accounting.NarrativeRunStore, "_write", no_second_store)
    monkeypatch.setattr(accounting, "_settle_output_in_transaction", after_update)
    with pytest.raises(OSError, match="after output SQL"):
        finish(s, failure(s))
    assert _dump(s.auto.db_path) == before and len(connections) == 1
    monkeypatch.setattr(accounting, "_settle_output_in_transaction", implementation)
    finish(s, failure(s))
    assert s.ledger.get_reservation("run-one", s.work.attempt.attempt_id).output_bytes == 0


def test_lost_commit_ack_has_one_durable_finish_and_no_repeat_credit(lake, monkeypatch):
    s = state(lake)
    original = s.auto._write_transaction
    def lost_ack(operation):
        original(operation)
        raise OSError("synthetic lost COMMIT acknowledgement")
    monkeypatch.setattr(s.auto, "_write_transaction", lost_ack)
    with pytest.raises(OSError, match="lost COMMIT"):
        finish(s, failure(s))
    record = s.ledger.get_reservation("run-one", s.work.attempt.attempt_id)
    assert record.output_bytes == 0 and s.auto.get_attempt(record.attempt_id).finished_at == T2
    after = _dump(s.auto.db_path)
    monkeypatch.setattr(s.auto, "_write_transaction", original)
    with pytest.raises(LeaseLostError, match="already finished"):
        finish(s, failure(s))
    assert _dump(s.auto.db_path) == after


def test_explicit_failed_summary_public_cli_settles_output_and_resumes_with_zero_extra_post(
    tmp_path_factory, loopback_model_server,
):
    content = canonical_json({"draft": {"source_id": "wrong-source", "source_sha256": "0" * 64,
        "language": "en", "claims": []}})
    loopback_model_server.response_body = json.dumps({"model": "stub-model", "choices": [{
        "finish_reason": "stop", "message": {"content": content}}],
        "usage": {"prompt_tokens": 73, "completion_tokens": 19}}).encode()
    with fixtures.isolated_batch_directory(tmp_path_factory) as root:
        source = fixtures.prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            from company_wiki.automation.store import AutomationStore
            source.store = AutomationStore(root / "automation.db")
            source.store.set_runtime_gate(RuntimeState.PAUSED, updated_at=fixtures.T0)
            ref, _, _ = next(iter(source.indexed.values()))
            request = {"schema_version": "narrative-batch-request/1", "run_id": "failed-output-slot",
                "sources": [{"schema_version": ref.schema_version, "document_id": ref.document_id,
                    "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                    "byte_size": ref.byte_size, "mime_type": ref.mime_type}], "profile": "P2",
                "selector_version": "0.8.0", "max_seconds": 40, "max_tokens": 200000, "max_cost_usd": "2",
                "model": {"model_id": "stub-model", "endpoint": loopback_model_server.endpoint,
                    "api_key_env": fixtures.KEY_ENV, "max_output_tokens": 8192,
                    "timeout_seconds": 5, "allow_local_http": True},
                "pricing": {"version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1000000,
                    "output_micro_usd_per_million_tokens": 2000000}}
            (root / "request.json").write_text(json.dumps(request), encoding="utf-8")
            originals = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (root / "companies").rglob("*") if path.is_file()}
            first, result = _invoke(root, source)
            assert first.returncode == 2 and result["status"] == "failed"
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            assert result["documents"][0]["artifact_ref"] is None
            ledger = accounting.NarrativeRunStore(source.store.db_path)
            reservation, = ledger.reservations_for_run(request["run_id"])
            assert reservation.usage_status == "known" and reservation.charged_tokens == 92
            assert reservation.response_sha256 == hashlib.sha256(content.encode()).hexdigest()
            assert reservation.error_code is None  # Successful transport, failed summary.
            assert reservation.output_bytes == 0 and reservation.output_sha256 is None
            assert reservation.output_settled_at is not None
            assert ledger.budget_snapshot(request["run_id"]).charged_output_bytes == 0
            before = _dump(source.store.db_path)
            again, recovered = _invoke(root, source)
            assert again.returncode == 2 and recovered["documents"] == result["documents"]
            assert recovered["budget"] == result["budget"]
            assert _dump(source.store.db_path) == before
            assert len(loopback_model_server.requests) == 1
            assert all((path.read_bytes(), path.stat().st_mtime_ns) == saved for path, saved in originals.items())
        finally:
            source.catalog.close()
