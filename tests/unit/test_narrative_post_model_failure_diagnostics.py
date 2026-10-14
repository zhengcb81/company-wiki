"""Completed model transport failures retain native usage and a bounded final."""
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import time

import pytest

from company_wiki.automation.models import HandlerMetrics, HandlerOutcome, HandlerResult, canonical_json
from company_wiki.automation.narrative_model import (
    FailedFinalDiagnostic, ModelResponseError, NarrativeModelRequest, NarrativeModelResponse,
)
from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller
from company_wiki.automation import narrative_summarize as summary
from support.narrative_model_request_fixture import selection, response_draft
from unit.test_narrative_reading_transport import with_reading
from unit.test_narrative_summarize_handler import _context
from unit.test_narrative_failed_final import _Ledger, _http


NATIVE = HandlerMetrics(tokens=321, cost_usd=0.002, duration_ms=17, reasoning_tokens=0)


@pytest.fixture(autouse=True)
def isolated_original_and_config(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    protected = {path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, path.stat().st_mtime_ns)
                 for path in (root / "config.yaml", root / "config/source_catalog.yaml")}
    def no_external_transport(*_args, **_kwargs):
        pytest.fail("post-model diagnostics must not contact an external supplier")
    monkeypatch.setattr(socket, "create_connection", no_external_transport)
    monkeypatch.setattr(socket.socket, "connect", no_external_transport)
    with tempfile.TemporaryDirectory(prefix="cw-post-model-final-") as name:
        test_root = Path(name)
        original = test_root / "original.txt"
        original.write_bytes(b"synthetic immutable original")
        sentinel = test_root / "existing.txt"
        sentinel.write_bytes(b"restore unchanged existing fixture")
        try:
            yield test_root
        finally:
            assert original.read_bytes() == b"synthetic immutable original"
            assert sentinel.read_bytes() == b"restore unchanged existing fixture"
            assert all((hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, path.stat().st_mtime_ns) == saved
                       for path, saved in protected.items())
    assert not test_root.exists()


def valid_body(selected):
    data = json.loads(NarrativeModelRequest.from_selection(selected).data_json)
    value = response_draft(data)
    value["draft"]["claims"][0]["modality"] = "actual"
    return value


def failed_body(selected, condition, *, physical_path=None):
    value = valid_body(selected)
    draft = value["draft"]
    claim = draft["claims"][0]
    prompt = NarrativeModelRequest.from_selection(selected).prompt_version
    if condition == "invalid_json":
        return b'{"draft":', prompt
    if condition == "duplicate_json":
        return b'{"draft":{},"draft":{}}', prompt
    if condition == "non_json_number":
        return b'{"draft":NaN}', prompt
    if condition == "missing_draft":
        return b'{"opaque-provider-field":"opaque-provider-body"}', prompt
    if condition == "wrong_prompt":
        prompt = "older-unavailable-prompt"
    elif condition == "translation":
        draft["translate"] = True
    elif condition == "identity":
        draft["source_sha256"] = "0" * 64
    elif condition == "language":
        draft["language"] = "en"
    elif condition == "claims_empty":
        draft["claims"] = []
    elif condition == "citation":
        claim["evidence_ids"] = ["not-in-selected-evidence"]
    elif condition == "group_declaration":
        claim["evidence_group_ids"] = ["not-in-selected-groups"]
    elif condition == "group_closure":
        claim["evidence_group_ids"] = ["g1"]
        claim["evidence_ids"] = ["e1"]
    elif condition == "path":
        if physical_path is None:
            raise ValueError("physical-path control requires its owned test original")
        # An explicit filesystem reference has the same meaning on every host;
        # a bare POSIX string also overlaps valid JSON-pointer/source notation.
        claim["text"] = physical_path.as_uri()
    elif condition == "size":
        claim["claim_id"] = "claim-" + "a" * 70000
    return canonical_json(value).encode("utf-8"), prompt


def run_response(selected, body, *, prompt=None, metrics=NATIVE):
    request = NarrativeModelRequest.from_selection(selected)
    response = NarrativeModelResponse("fixture", "fixture-model", prompt or request.prompt_version,
        body, input_tokens=222, output_tokens=99, duration_ms=17, reasoning_tokens=0)
    calls = []
    class Caller:
        def generate(self, context, sent):
            calls.append(sent)
            assert context.attempt.attempt_id
            return response, metrics
    result = summary.NarrativeSummarizeHandler(model=None, model_caller=Caller())(_context(selected))
    assert len(calls) == 1
    return result


def assert_failure(result, *, body, code, rule, observed=True, metrics=NATIVE):
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code == code and f"rule={rule}" in result.error.detail
    assert result.metrics == metrics and not result.artifacts and not result.effects
    assert "opaque-provider" not in result.error.detail
    wire = canonical_json(result.to_dict()).encode("utf-8")
    assert len(wire) < 16384
    assert HandlerResult.from_dict(json.loads(wire)).to_dict() == result.to_dict()
    if not observed:
        assert result.result == {}
        return
    assert set(result.result) == {"failed_final"}
    diagnostic = FailedFinalDiagnostic.from_dict(result.result["failed_final"])
    assert diagnostic.final_content_sha256 == hashlib.sha256(body).hexdigest()
    assert diagnostic.final_content_bytes == len(body)
    assert body.decode("utf-8").startswith(diagnostic.final_prefix)
    assert diagnostic.prefix_bytes == len(diagnostic.final_prefix.encode("utf-8"))
    assert diagnostic.clipped is (diagnostic.prefix_bytes < len(body))
    # NarrativeModelResponse contains only the final. Full provider wire is not observed here.
    assert diagnostic.provider_response_sha256 is None and diagnostic.provider_response_bytes is None


@pytest.mark.parametrize("condition,code,rule", [
    ("invalid_json", "MODEL_RESPONSE_INVALID", "FINAL_JSON"),
    ("duplicate_json", "MODEL_RESPONSE_INVALID", "JSON_DUPLICATE_KEYS"),
    ("non_json_number", "MODEL_RESPONSE_INVALID", "JSON_NUMBER"),
    ("missing_draft", "MODEL_RESPONSE_INVALID", "RESPONSE_SHAPE"),
    ("wrong_prompt", "MODEL_RESPONSE_INVALID", "PROMPT_IDENTITY"),
    ("translation", "MODEL_RESPONSE_INVALID", "TRANSLATION"),
    ("identity", "SUMMARY_INVALID", "SOURCE_IDENTITY"),
    ("language", "SUMMARY_INVALID", "SOURCE_LANGUAGE"),
    ("claims_empty", "SUMMARY_INVALID", "CLAIMS_EMPTY"),
    ("citation", "SUMMARY_INVALID", "EVIDENCE_REFERENCE"),
    ("group_declaration", "SUMMARY_INVALID", "GROUP_DECLARATION"),
    ("group_closure", "SUMMARY_INVALID", "GROUP_INCOMPLETE"),
    ("path", "MODEL_RESPONSE_INVALID", "PHYSICAL_PATH"),
    ("size", "RESULT_TOO_LARGE", "RESULT_SIZE"),
])
def test_each_real_post_model_validation_failure_has_final_hash_rule_and_native_usage(
    condition, code, rule, isolated_original_and_config,
):
    selected = with_reading(selection(3))
    before = selected.to_dict()
    body, prompt = failed_body(selected, condition,
                               physical_path=isolated_original_and_config / "original.txt")
    if condition == "path":
        assert json.loads(body)["draft"]["claims"][0]["text"].startswith("file://")
    result = run_response(selected, body, prompt=prompt)
    assert_failure(result, body=body, code=code, rule=rule)
    assert selected.to_dict() == before


def test_invalid_utf8_is_not_repaired_or_allowed_to_hide_paid_usage():
    selected = with_reading(selection(3))
    body = b"\xff\xfeinvalid final"
    result = run_response(selected, body)
    assert_failure(result, body=body, code="MODEL_RESPONSE_INVALID", rule="FINAL_UTF8", observed=False)


def test_json_escaped_unpaired_surrogate_preserves_usage_and_rejects_unencodable_summary():
    selected = with_reading(selection(3))
    value = valid_body(selected)
    value["draft"]["claims"][0]["text"] = "\ud800"
    body = json.dumps(value, ensure_ascii=True).encode("utf-8")
    result = run_response(selected, body)
    # The actual final byte string is UTF-8; its decoded summary value is not.
    assert_failure(result, body=body, code="MODEL_RESPONSE_INVALID", rule="FINAL_UTF8")


def test_escaped_multibyte_invalid_final_fits_the_whole_attempt_not_just_raw_prefix():
    selected = with_reading(selection(3))
    body = ('营😀\x00"\\e\u0301' * 3000).encode("utf-8")
    result = run_response(selected, body)
    assert_failure(result, body=body, code="MODEL_RESPONSE_INVALID", rule="FINAL_JSON")
    assert result.result["failed_final"]["clipped"] is True


@pytest.mark.parametrize("stage", ["observe", "fit", "serialize"])
def test_optional_diagnostic_failure_preserves_primary_rule_and_native_metrics(monkeypatch, stage):
    selected = with_reading(selection(3))
    body, prompt = failed_body(selected, "identity")
    hits = []
    def unavailable(*_args, **_kwargs):
        hits.append(stage)
        raise OSError("optional-diagnostic-provider-secret")
    if stage == "observe":
        monkeypatch.setattr(FailedFinalDiagnostic, "from_observation", unavailable)
    elif stage == "fit":
        monkeypatch.setattr(summary, "fit_failed_final_result", unavailable)
    else:
        monkeypatch.setattr(FailedFinalDiagnostic, "to_dict", unavailable)
    result = run_response(selected, body, prompt=prompt)
    assert_failure(result, body=body, code="SUMMARY_INVALID", rule="SOURCE_IDENTITY", observed=False)
    assert hits == [stage]


def test_unknown_response_error_has_only_fixed_rule_without_exception_values(monkeypatch):
    selected = with_reading(selection(3))
    body = canonical_json(valid_body(selected)).encode("utf-8")
    def reject(*_args, **_kwargs):
        raise ModelResponseError("opaque-provider-secret-custom-value")
    monkeypatch.setattr(summary, "decode_model_draft", reject)
    result = run_response(selected, body)
    assert_failure(result, body=body, code="MODEL_RESPONSE_INVALID", rule="MODEL_RESPONSE_CONTRACT")


def test_success_does_not_store_a_duplicate_final_diagnostic():
    selected = with_reading(selection(3))
    body = canonical_json(valid_body(selected)).encode("utf-8")
    result = run_response(selected, body)
    assert result.outcome is HandlerOutcome.SUCCEEDED and result.error is None
    assert result.metrics == NATIVE
    assert "failed_final" not in result.result and "final_prefix" not in canonical_json(result.to_dict())
    assert result.result["model"]["response_sha256"] == hashlib.sha256(body).hexdigest()


def test_unknown_pre_response_exception_preserves_the_original_exception_semantics():
    selected = with_reading(selection(3))
    original = RuntimeError("synthetic transport failed before a returned response")
    calls = []
    class Caller:
        def generate(self, *_args):
            calls.append(1)
            raise original
    with pytest.raises(RuntimeError) as caught:
        summary.NarrativeSummarizeHandler(model=None, model_caller=Caller())(_context(selected))
    assert caught.value is original and calls == [1]


def test_real_http_decoder_budget_settlement_and_handler_store_only_final_with_one_charge():
    selected = with_reading(selection(3))
    content, _ = failed_body(selected, "group_closure")
    entity = json.dumps({"model": "model", "choices": [{"finish_reason": "stop", "message": {
        "content": content.decode("utf-8"), "reasoning_content": "HIDDEN_REASONING_SENTINEL"}}],
        "usage": {"prompt_tokens": 73, "completion_tokens": 85,
                  "completion_tokens_details": {"reasoning_tokens": 0}},
        "headers": {"Authorization": "HIDDEN_AUTH_SENTINEL"}}, ensure_ascii=False).encode("utf-8")
    ledger = _Ledger()
    class Model:
        model_id, max_output_tokens, calls = "model", 8192, 0
        def request_bytes(self, request):
            return _http().request_bytes(request)
        def generate(self, request):
            self.calls += 1
            return _http()._response(request, entity, time.monotonic())
    model = Model()
    caller = BudgetedNarrativeCaller(store=ledger, run_id="run", model=model)
    result = summary.NarrativeSummarizeHandler(model=None, model_caller=caller)(_context(selected))
    assert result.outcome is HandlerOutcome.TERMINAL_FAILURE and result.error.code == "SUMMARY_INVALID"
    assert "rule=GROUP_INCOMPLETE" in result.error.detail
    assert result.metrics.tokens == 158 and result.metrics.reasoning_tokens == 0
    assert len(ledger.settlements) == model.calls == 1 and ledger.outputs == []
    settled = ledger.settlements[0]
    assert (settled["usage"].input_tokens, settled["usage"].output_tokens) == (73, 85)
    assert settled["response_sha256"] == hashlib.sha256(content).hexdigest()
    stored = result.result["failed_final"]
    assert stored["final_content_sha256"] == settled["response_sha256"]
    assert stored["provider_response_sha256"] is None
    assert "HIDDEN_REASONING_SENTINEL" not in canonical_json(result.to_dict())
    assert "HIDDEN_AUTH_SENTINEL" not in canonical_json(result.to_dict())
    assert not result.artifacts and not result.effects
