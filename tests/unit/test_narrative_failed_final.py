"""Failed final observations stay honest, bounded and independent of billing."""
from dataclasses import replace
import hashlib
import json
import time
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import HandlerMetrics, HandlerOutcome, HandlerResult, canonical_json
from company_wiki.automation.narrative_http_model import ModelEnvelopeError, ModelOutputTruncatedError, NarrativeHTTPModel
from company_wiki.automation.narrative_model import NarrativeModelRequest
from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller, NarrativeBudgetCallError
from company_wiki.automation.narrative_summarize import _failure

REQUEST = NarrativeModelRequest("1.1.0", "data only", "{}", "a" * 64)
FIELDS = {"schema_version", "provider_response_sha256", "provider_response_bytes", "final_content_sha256", "final_content_bytes", "final_prefix", "prefix_bytes", "clipped"}


def _body(content, *, usage=True, reason=True, finish="length", spaced=False):
    value = {"model": "model", "choices": [{"finish_reason": finish,
        "message": {"content": content, "reasoning_content": "HIDDEN_REASONING_SENTINEL"}}]}
    if usage:
        value["usage"] = {"prompt_tokens": 73, "completion_tokens": 8194}
        if reason:
            value["usage"]["completion_tokens_details"] = {"reasoning_tokens": 7000}
    return json.dumps(value, ensure_ascii=False, indent=2 if spaced else None).encode("utf-8")


def _http():
    return NarrativeHTTPModel(model_id="model", endpoint="https://fixtures.invalid/v1/chat/completions",
        api_key_env="SYNTHETIC_UNUSED_KEY", max_output_tokens=8192)


def _decoded_error(body, expected=ModelOutputTruncatedError):
    with pytest.raises(expected) as caught:
        _http()._response(REQUEST, body, time.monotonic())
    return caught.value


@pytest.mark.parametrize("content", ["营" * 317, "", None, "营" * 6000], ids=["951", "empty", "unobserved", "18000"])
def test_real_decoder_preserves_two_hashes_and_observed_vs_unobserved_final(content):
    body = _body(content)
    error = _decoded_error(body)
    diagnostic = getattr(error, "failed_final", None)
    assert diagnostic is not None, "length response drops its bounded final observation"
    observed = diagnostic.to_dict()
    assert set(observed) == FIELDS
    assert observed["provider_response_sha256"] == hashlib.sha256(body).hexdigest()
    assert observed["provider_response_bytes"] == len(body)
    if content is None:
        assert observed["final_content_sha256"] is None
        assert observed["final_content_bytes"] is None and observed["final_prefix"] is None
        assert error.content_bytes is None
    else:
        original = content.encode("utf-8")
        assert observed["final_content_sha256"] == hashlib.sha256(original).hexdigest()
        assert observed["final_content_bytes"] == len(original)
        assert content.startswith(observed["final_prefix"])
    assert observed["prefix_bytes"] == len((observed["final_prefix"] or "").encode("utf-8"))
    assert observed["clipped"] is (content is not None and observed["prefix_bytes"] < len(content.encode("utf-8")))
    assert "HIDDEN_REASONING_SENTINEL" not in json.dumps(observed)
    assert (error.input_tokens, error.output_tokens, error.reasoning_tokens) == (73, 8194, 7000)


def test_entity_hash_tracks_actual_wire_not_canonical_payload():
    first, second = (_decoded_error(_body("same", spaced=spaced)).failed_final for spaced in (False, True))
    assert first.provider_response_sha256 != second.provider_response_sha256
    assert first.final_content_sha256 == second.final_content_sha256


def test_direct_observation_without_raw_entity_cannot_fabricate_wire_hash():
    from company_wiki.automation.narrative_model import FailedFinalDiagnostic
    observed = FailedFinalDiagnostic.from_observation(provider_body=None, content="已见正文")
    assert observed.provider_response_sha256 is None and observed.provider_response_bytes is None
    assert observed.final_content_sha256 == hashlib.sha256("已见正文".encode()).hexdigest()


def test_explicit_empty_non_length_keeps_original_invalid_response_classification():
    error = _decoded_error(_body("", finish="stop"), ModelEnvelopeError)
    assert error.response_stage == "empty_content"
    assert error.failed_final.final_content_bytes == 0
    assert error.failed_final.final_content_sha256 == hashlib.sha256(b"").hexdigest()


def test_unpaired_surrogate_is_invalid_utf8_not_replacement_final():
    body = json.dumps({
        "choices": [{"finish_reason": "length", "message": {"content": "\ud800"}}]}).encode()
    error = _decoded_error(body, ModelEnvelopeError)
    assert error.response_stage == "content_type"
    assert getattr(error, "failed_final", None) is None


@pytest.mark.parametrize("content", ["营" * 6000, "\x00" * 18000, '\"\\' * 9000,
    "😀" * 5000, "e\u0301" * 6000, '营\r\n\x00\"\\😀e\u0301' * 1200], ids=["cjk", "controls", "quotes", "emoji", "combining", "mixed"])
def test_whole_attempt_utf8_limit_includes_json_escapes_and_multibyte(content):
    diagnostic = _decoded_error(_body(content)).failed_final
    metrics = HandlerMetrics(tokens=8267, cost_usd=0.016461, duration_ms=7, reasoning_tokens=7000)
    result = _failure("MODEL_OUTPUT_TRUNCATED", HandlerOutcome.TERMINAL_FAILURE, "static original failure", metrics,
        failed_final=diagnostic)
    wire = canonical_json(result.to_dict()).encode("utf-8")
    assert len(wire) < 16384
    stored = result.result["failed_final"]
    assert content.startswith(stored["final_prefix"])
    assert stored["prefix_bytes"] == len(stored["final_prefix"].encode())
    assert stored["clipped"] is True
    assert stored["final_content_sha256"] == hashlib.sha256(content.encode()).hexdigest()
    assert HandlerResult.from_dict(json.loads(wire)).to_dict() == result.to_dict()
    assert result.metrics == metrics and not result.artifacts and not result.effects
    k = len(stored["final_prefix"])
    one_more = dict(stored, final_prefix=content[:k + 1], prefix_bytes=len(content[:k + 1].encode()))
    bigger = replace(result, result={"failed_final": one_more})
    assert len(canonical_json(bigger.to_dict()).encode()) >= 16384


def test_optional_diagnostic_fit_failure_keeps_primary_error_and_paid_metrics(monkeypatch):
    import company_wiki.automation.narrative_summarize as summary
    diagnostic = _decoded_error(_body("partial")).failed_final
    metrics = HandlerMetrics(tokens=8267, cost_usd=0.016461, duration_ms=3)
    def unavailable(*args, **kwargs):
        raise OSError("diagnostic store unavailable")
    monkeypatch.setattr(summary, "fit_failed_final_result", unavailable)
    result = summary._failure("MODEL_OUTPUT_TRUNCATED", HandlerOutcome.TERMINAL_FAILURE, "primary", metrics,
        failed_final=diagnostic)
    assert result.result == {} and result.error.code == "MODEL_OUTPUT_TRUNCATED"
    assert result.error.detail == "primary" and result.metrics == metrics


def test_optional_decoder_diagnostic_failure_does_not_cover_length_or_meter(monkeypatch):
    from company_wiki.automation.narrative_model import FailedFinalDiagnostic
    def unavailable(**kwargs):
        raise OSError("diagnostic unavailable")
    monkeypatch.setattr(FailedFinalDiagnostic, "from_observation", unavailable)
    error = _decoded_error(_body("partial"))
    assert error.failed_final is None
    assert (error.input_tokens, error.output_tokens) == (73, 8194)


class _Ledger:
    def __init__(self):
        self.settlements, self.outputs = [], []
        self.fail_settle = False
    def get_run(self, run_id):
        return SimpleNamespace(model_id="model", prompt_version=REQUEST.prompt_version, pricing_version="rates/1", blocked=False)
    def reserve_model_attempt(self, **kwargs):
        return SimpleNamespace(may_send_http=True, record=self._record(None))
    @staticmethod
    def _record(usage):
        return SimpleNamespace(charged_tokens=20000 if usage is None else usage.total_tokens,
            charged_micro_usd=100000 if usage is None else usage.input_tokens + 2 * usage.output_tokens)
    def settle_model_usage(self, **kwargs):
        if self.fail_settle:
            raise OSError("actual ledger unavailable")
        self.settlements.append(kwargs)
        return self._record(kwargs["usage"])
    def settle_output(self, **kwargs):
        self.outputs.append(kwargs)


@pytest.mark.parametrize("known", [True, False])
def test_real_decoder_caller_settle_and_failure_have_one_paid_no_output_attempt(known):
    body = _body("营" * 317, usage=known, reason=False)
    ledger = _Ledger()
    class Model:
        model_id, max_output_tokens, calls = "model", 8192, 0
        def request_bytes(self, request):
            return b"bounded synthetic request"
        def generate(self, request):
            self.calls += 1
            return _http()._response(request, body, time.monotonic())
    model = Model()
    context = SimpleNamespace(job=SimpleNamespace(job_id="job"), attempt=SimpleNamespace(
        attempt_id="attempt", lease_token="lease", runtime_generation=1), checkpoint=lambda: None)
    caller = BudgetedNarrativeCaller(store=ledger, run_id="run", model=model)
    with pytest.raises(NarrativeBudgetCallError) as caught:
        caller.generate(context, REQUEST)
    error = caught.value
    assert error.code == "MODEL_OUTPUT_TRUNCATED" and error.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert model.calls == 1 and len(ledger.settlements) == len(ledger.outputs) == 1
    assert ledger.settlements[0]["response_sha256"] == hashlib.sha256(("营" * 317).encode()).hexdigest()
    assert ledger.outputs[0]["output_bytes"] == 0 and ledger.outputs[0]["output_sha256"] is None
    assert error.failed_final.provider_response_sha256 == hashlib.sha256(body).hexdigest()
    assert error.metrics.reasoning_tokens is None
    assert error.metrics.tokens == (8267 if known else 20000)
    assert error.metrics.cost_usd == (0.016461 if known else 0.1)
    assert (ledger.settlements[0]["usage"] is not None) is known


def test_old_failure_result_and_direct_error_have_no_backfilled_object():
    error = ModelOutputTruncatedError(model_id="model", input_tokens=None, output_tokens=None, duration_ms=0)
    assert getattr(error, "failed_final", None) is None
    result = _failure("MODEL_OUTPUT_TRUNCATED", HandlerOutcome.TERMINAL_FAILURE, "old receipt")
    assert result.result == {} and "failed_final" not in canonical_json(result.to_dict())


@pytest.mark.parametrize("changed", [
    {"provider_response_bytes": True}, {"provider_response_sha256": None},
    {"final_content_bytes": False}, {"final_content_sha256": "invalid"},
    {"prefix_bytes": 0}, {"clipped": True}, {"clipped": 0},
    {"final_prefix": "different"}, {"extra": "not a protocol field"},
], ids=["bool-wire-size", "unpaired-wire", "bool-final-size", "invalid-sha", "wrong-prefix-size",
    "wrong-clipped", "bool-required", "different-prefix", "extra-field"])
def test_typed_failed_final_rejects_forged_or_inconsistent_observations(changed):
    from company_wiki.automation.narrative_model import FailedFinalDiagnostic
    diagnostic = FailedFinalDiagnostic.from_observation(provider_body=b"original wire", content="x")
    value = {**diagnostic.to_dict(), **changed}
    with pytest.raises((ValueError, TypeError)):
        FailedFinalDiagnostic.from_dict(value)


def test_scalar_diagnostic_dict_cannot_mutate_frozen_observation():
    diagnostic = _decoded_error(_body("partial")).failed_final
    copied = diagnostic.to_dict()
    copied["final_prefix"] = "forged"
    assert diagnostic.final_prefix == "partial"


def test_no_room_for_optional_metadata_keeps_small_original_failure_and_meter():
    diagnostic = _decoded_error(_body("partial")).failed_final
    metrics = HandlerMetrics(tokens=8267, cost_usd=0.016461, duration_ms=7)
    result = _failure("MODEL_OUTPUT_TRUNCATED", HandlerOutcome.TERMINAL_FAILURE, "x" * 16100,
        metrics, failed_final=diagnostic)
    assert len(canonical_json(result.to_dict()).encode()) < 16384
    assert result.result == {} and result.metrics == metrics
    assert result.error.code == "MODEL_OUTPUT_TRUNCATED" and result.error.detail == "x" * 16100


def test_actual_settlement_failure_retains_unknown_charge_and_observed_failure_without_retry():
    body = _body("partial")
    ledger = _Ledger()
    ledger.fail_settle = True
    class Model:
        model_id, max_output_tokens, calls = "model", 8192, 0
        def request_bytes(self, request):
            return b"bounded synthetic request"
        def generate(self, request):
            self.calls += 1
            return _http()._response(request, body, time.monotonic())
    model = Model()
    context = SimpleNamespace(job=SimpleNamespace(job_id="job"), attempt=SimpleNamespace(
        attempt_id="attempt", lease_token="lease", runtime_generation=1), checkpoint=lambda: None)
    with pytest.raises(NarrativeBudgetCallError) as caught:
        BudgetedNarrativeCaller(store=ledger, run_id="run", model=model).generate(context, REQUEST)
    error = caught.value
    assert error.code == "MODEL_BUDGET_STORE_FAILURE" and error.finish_reason == "length"
    assert error.failed_final.final_content_sha256 == hashlib.sha256(b"partial").hexdigest()
    assert (error.metrics.tokens, error.metrics.cost_usd) == (20000, 0.1)
    assert model.calls == 1 and not ledger.settlements and not ledger.outputs


@pytest.mark.parametrize("condition,expected", [
    ("ready", True), ("planned", True), ("finished", True),
    ("enabled", False), ("leased", False), ("running", False), ("verifying", False),
    ("unfinished-attempt", False), ("planned-effect", False), ("pending-effect", False),
    ("applied-effect", False), ("pending-outbox", False), ("leased-outbox", False),
    ("delivered-outbox", True), ("failed-outbox", False), ("foreign-outbox", True),
])
def test_real_store_blocked_history_readonly_eligibility_preserves_pending_work(tmp_path, condition, expected):
    import sqlite3
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation.models import (
        Attempt, Effect, EffectStatus, Event, Job, JobStatus, RiskClass, RuntimeState,
        make_effect_key, make_job_key,
    )
    from company_wiki.automation.store import AutomationStore
    t0, t1 = "2026-10-11T00:00:00Z", "2026-10-11T00:01:00Z"
    sha = hashlib.sha256(b"synthetic bounded history").hexdigest()
    store = AutomationStore(tmp_path / "automation.db")
    gate = store.set_runtime_gate(RuntimeState.ENABLED if condition == "enabled" else RuntimeState.PAUSED, updated_at=t0)
    event = Event("event", "source.revision_registered", "source_revision", "source", sha, "{}", "test", t0, t0)
    store.put_event(event)
    status = {"planned": JobStatus.PLANNED, "leased": JobStatus.LEASED,
              "running": JobStatus.RUNNING, "verifying": JobStatus.VERIFYING}.get(condition, JobStatus.READY)
    job = Job("job", make_job_key("source.narrative_verify", "source_revision", "source", sha, "test", "1.0.0"),
        "source.narrative_verify", "source_revision", "source", sha, "test", "1.0.0", RiskClass.LOW,
        status, 0, t0, 3, event.event_id, t0, t0, None, None)
    store.put_job(job)
    if condition in {"unfinished-attempt", "finished"}:
        finished = condition == "finished"
        store.put_attempt(Attempt("attempt", job.job_id, 1, "worker", "lease", t1, t0, t0,
            t0 if finished else None, HandlerOutcome.TERMINAL_FAILURE if finished else None,
            None, "SYNTHETIC_FAILURE" if finished else None, None))
    if condition == "foreign-outbox":
        foreign_event = replace(event, event_id="foreign-event", subject_id="foreign")
        store.put_event(foreign_event)
        foreign_job = replace(job, job_id="foreign-job", subject_id="foreign", created_from_event_id=foreign_event.event_id,
            job_key=make_job_key(job.job_type, job.subject_type, "foreign", sha, "test", "1.0.0"))
        store.put_job(foreign_job)
        foreign_effect = Effect("foreign-effect", make_effect_key("artifact_write", "foreign", sha, "1.0.0"), foreign_job.job_id,
            "artifact_write", "foreign", None, sha, None, EffectStatus.PENDING, t0, None)
        store.put_effect(foreign_effect)
        store.put_outbox_entry("opaque-foreign", foreign_effect.effect_id, "{}", "pending", t0)
    elif condition.endswith("-effect") or condition.endswith("-outbox"):
        effect_status = {"planned-effect": EffectStatus.PLANNED, "pending-effect": EffectStatus.PENDING,
            "applied-effect": EffectStatus.APPLIED}.get(condition, EffectStatus.VERIFIED)
        effect = Effect("effect", make_effect_key("artifact_write", "owned-fixture", sha, "1.0.0"), job.job_id,
            "artifact_write", "owned-fixture", None, sha,
            sha if effect_status is EffectStatus.VERIFIED else None, effect_status, t0,
            t0 if effect_status is EffectStatus.VERIFIED else None)
        store.put_effect(effect)
        if condition.endswith("-outbox"):
            # Query by actual delivery state; do not rely on private outbox ID naming.
            store.put_outbox_entry("opaque-outbox", effect.effect_id, "{}", condition.split("-")[0], t0)
    def dump():
        connection = sqlite3.connect(store.db_path)
        try:
            return tuple(connection.iterdump())
        finally:
            connection.close()
    before = dump()
    assert callable(getattr(batch, "_blocked_history_is_idle", None)), "blocked resume has no idle read-only decision"
    assert batch._blocked_history_is_idle(store, (job,), gate) is expected
    assert dump() == before
    assert store.get_job(job.job_id).status is status
