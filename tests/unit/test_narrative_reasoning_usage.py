"""Provider usage observation contracts, no live model or production storage."""
import json
import time

import pytest

from company_wiki.automation.models import HandlerMetrics, HandlerResult, HandlerOutcome, HandlerError
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel, ModelEnvelopeError, ModelOutputTruncatedError
from company_wiki.automation.narrative_model import NarrativeModelRequest

REQUEST = NarrativeModelRequest("fixture", "data only", "{}", "a" * 64)


def reply(usage, *, finish="stop", content="{}", choices=True):
    value = {"model": "fixture", "usage": usage}
    if choices:
        value["choices"] = [{"finish_reason": finish, "message": {
            "content": content, "reasoning_content": "hidden text must not be saved",
        }}]
    return json.dumps(value).encode()


def model():
    return NarrativeHTTPModel(model_id="fixture", endpoint="https://fixture.invalid/v1/chat/completions",
                              api_key_env="LOCAL_FIXTURE_KEY", max_output_tokens=8192)


@pytest.mark.parametrize("detail,expected,diagnostic", [
    ({"reasoning_tokens": 0}, 0, None), ({"reasoning_tokens": 20}, 20, None),
    ({}, None, None), (None, None, None),
    ({"reasoning_tokens": True}, None, "reasoning_usage_invalid"),
    ({"reasoning_tokens": -1}, None, "reasoning_usage_invalid"),
    ({"reasoning_tokens": 21}, None, "reasoning_usage_invalid"),
    ({"reasoning_tokens": "7"}, None, "reasoning_usage_invalid"),
    ([1], None, "reasoning_usage_invalid"),
])
def test_success_usage_keeps_valid_totals_and_optional_reasoning(detail, expected, diagnostic):
    usage = {"prompt_tokens": 11, "completion_tokens": 20, "completion_tokens_details": detail}
    response = model()._response(REQUEST, reply(usage), time.monotonic())
    assert (response.input_tokens, response.output_tokens) == (11, 20)
    assert response.reasoning_tokens == expected
    assert response.usage_diagnostic == diagnostic
    assert "hidden text" not in repr(response)


@pytest.mark.parametrize("kind", ["length_empty", "length_mixed", "invalid_envelope"])
def test_paid_failure_retains_actual_completion_and_reasoning(kind):
    usage = {"prompt_tokens": 11, "completion_tokens": 8194,
             "completion_tokens_details": {"reasoning_tokens": 8000}}
    data = reply(usage, finish="length" if kind != "invalid_envelope" else "stop",
                 content=None if kind == "length_empty" else "{partial", choices=kind != "invalid_envelope")
    error_class = ModelEnvelopeError if kind == "invalid_envelope" else ModelOutputTruncatedError
    with pytest.raises(error_class) as caught:
        model()._response(REQUEST, data, time.monotonic())
    error = caught.value
    assert (error.input_tokens, error.output_tokens, error.reasoning_tokens) == (11, 8194, 8000)
    assert error.usage_diagnostic is None
    assert "hidden text" not in str(error)


def test_reasoning_observation_survives_handler_wire_and_old_bytes_remain_identical():
    old = HandlerMetrics(31, 0.001, 5)
    assert old.to_dict() == {"tokens": 31, "cost_usd": 0.001, "duration_ms": 5}
    metrics = HandlerMetrics(31, 0.001, 5, reasoning_tokens=0)
    result = HandlerResult(HandlerOutcome.TERMINAL_FAILURE, {}, (), (), metrics, HandlerError("length", "static"))
    loaded = HandlerResult.from_dict(result.to_dict())
    assert loaded.metrics.reasoning_tokens == 0
    assert loaded.metrics.tokens == 31
    assert HandlerMetrics.from_dict(old.to_dict()).reasoning_tokens is None


@pytest.mark.parametrize("value", [-1, True, "1"])
def test_invalid_reasoning_metrics_are_rejected_without_coercion(value):
    with pytest.raises((TypeError, ValueError), match="reasoning"):
        HandlerMetrics(31, 0.001, 5, reasoning_tokens=value)
