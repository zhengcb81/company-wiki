"""A model attempt has durable admission and accounting around one call."""

from types import SimpleNamespace
from dataclasses import replace

import pytest

from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_http_model import (
    ModelCredentialsError,
    ModelHTTPError,
    ModelOutputTruncatedError,
)
from company_wiki.automation.narrative_model import (
    ModelRateLimitError,
    ModelTimeoutError,
    NarrativeModelRequest,
    NarrativeModelResponse,
)
from company_wiki.automation.narrative_model_caller import NarrativeBudgetCallError


REQUEST = NarrativeModelRequest("1.1.0", "data only", "{}", "a" * 64)


class Ledger:
    def __init__(self):
        self.events = []
        self.may_send = True
        self.fail_reserve = False
        self.settlements = []
        self.fail_settle = False

    def get_run(self, run_id):
        return SimpleNamespace(
            model_id="model",
            prompt_version="1.1.0",
            pricing_version="rates/1",
            blocked=False,
        )

    def reserve_model_attempt(self, **arguments):
        self.events.append(("reserve", arguments))
        if self.fail_reserve:
            raise ValueError("test budget exhausted")
        return SimpleNamespace(
            may_send_http=self.may_send, record=self._record(100, 30)
        )

    def settle_model_usage(self, **arguments):
        if self.fail_settle:
            raise OSError("test SQLite unavailable")
        self.events.append(("settle", arguments))
        self.settlements.append(arguments)
        usage = arguments["usage"]
        return self._record(
            100 if usage is None else usage.total_tokens, 30 if usage is None else 12
        )

    def settle_output(self, **arguments):
        self.events.append(("output", arguments))

    def block_run(self, run_id, **arguments):
        self.events.append(("block", arguments))

    @staticmethod
    def _record(tokens, cost):
        return SimpleNamespace(charged_tokens=tokens, charged_micro_usd=cost)


class Model:
    model_id = "model"
    max_output_tokens = 20

    def __init__(self, ledger, *, error=None, actual_model="model"):
        self.ledger, self.error, self.actual_model = ledger, error, actual_model
        self.calls = 0

    def request_bytes(self, request):
        return b"exact-provider-body"

    def generate(self, request):
        self.calls += 1
        self.ledger.events.append(("http", {}))
        if self.error:
            raise self.error
        return NarrativeModelResponse(
            "http",
            self.actual_model,
            request.prompt_version,
            b"invalid draft JSON",
            50,
            10,
            18,
        )


def _context():
    return SimpleNamespace(
        job=SimpleNamespace(job_id="summary-1"),
        attempt=SimpleNamespace(
            attempt_id="attempt-1",
            lease_token="lease-1",
            runtime_generation=7,
        ),
        checkpoint=lambda: None,
    )


def _caller(ledger, model):
    from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller

    return BudgetedNarrativeCaller(
        store=ledger, run_id="run-1", model=model, clock=lambda: "2026-10-03T16:00:00Z"
    )


def test_reserve_then_http_then_settle_even_when_draft_bytes_are_invalid():
    ledger = Ledger()
    model = Model(ledger)
    response, metrics = _caller(ledger, model).generate(_context(), REQUEST)
    assert [event for event, _ in ledger.events] == ["reserve", "http", "settle"]
    admission = ledger.events[0][1]
    assert (
        admission["attempt_id"] == "attempt-1" and admission["runtime_generation"] == 7
    )
    assert admission["input_tokens_bound"] == len(model.request_bytes(REQUEST)) + 128
    assert admission["max_output_tokens"] == 20
    assert (metrics.tokens, metrics.cost_usd, metrics.duration_ms) == (60, 0.000012, 18)
    assert response.response_bytes == b"invalid draft JSON"
    assert ledger.settlements[0]["response_sha256"] == response.response_sha256


def test_reservation_hash_binds_local_citation_mapping_even_for_identical_http_body():
    hashes = []
    for request in (REQUEST, replace(REQUEST, input_sha256="b" * 64)):
        ledger = Ledger()
        model = Model(ledger)
        _caller(ledger, model).generate(_context(), request)
        hashes.append(ledger.events[0][1]["request_sha256"])
    assert hashes[0] != hashes[1]


def test_malformed_response_still_settles_valid_usage_and_carries_static_diagnostic():
    from company_wiki.automation.narrative_http_model import ModelEnvelopeError

    ledger = Ledger()
    model = Model(ledger, error=ModelEnvelopeError("empty_content", input_tokens=50,
        output_tokens=10, duration_ms=18, http_status=200))
    with pytest.raises(NarrativeBudgetCallError) as caught:
        _caller(ledger, model).generate(_context(), REQUEST)
    error = caught.value
    assert error.code == "MODEL_RESPONSE_INVALID"
    assert ledger.settlements[0]["usage"].total_tokens == 60
    assert (error.metrics.tokens, error.metrics.duration_ms) == (60, 18)
    assert error.http_status == 200 and error.response_stage == "empty_content"
    assert error.provider_code is None and model.calls == 1


@pytest.mark.parametrize("case", ["denied", "duplicate"])
def test_admission_failure_never_calls_model(case):
    ledger = Ledger()
    ledger.fail_reserve = case == "denied"
    ledger.may_send = case != "duplicate"
    model = Model(ledger)
    with pytest.raises(
        NarrativeBudgetCallError,
        match="MODEL_BUDGET_DENIED|MODEL_REQUEST_ALREADY_RESERVED",
    ):
        _caller(ledger, model).generate(_context(), REQUEST)
    assert model.calls == 0
    assert not ledger.settlements


def test_timeout_keeps_unknown_usage_and_does_not_erase_the_reservation():
    ledger = Ledger()
    model = Model(ledger, error=ModelTimeoutError("timeout"))
    with pytest.raises(NarrativeBudgetCallError, match="MODEL_TIMEOUT") as error:
        _caller(ledger, model).generate(_context(), REQUEST)
    assert ledger.settlements[0]["usage"] is None
    assert ledger.settlements[0]["error_code"] == "MODEL_TIMEOUT"
    assert error.value.metrics.tokens == 100
    assert model.calls == 1


def test_credentials_failure_is_known_zero_without_saving_error_text():
    ledger = Ledger()
    model = Model(ledger, error=ModelCredentialsError("MODEL_KEY_MISSING"))
    with pytest.raises(NarrativeBudgetCallError, match="MODEL_CREDENTIALS_INVALID"):
        _caller(ledger, model).generate(_context(), REQUEST)
    assert ledger.settlements[0]["usage"].total_tokens == 0
    assert (
        ledger.events[-1][0] == "output" and ledger.events[-1][1]["output_bytes"] == 0
    )


def test_provider_model_change_is_charged_before_blocking_future_calls():
    ledger = Ledger()
    model = Model(ledger, actual_model="unrequested-model")
    with pytest.raises(NarrativeBudgetCallError, match="MODEL_ID_CHANGED"):
        _caller(ledger, model).generate(_context(), REQUEST)
    assert [event for event, _ in ledger.events][-2:] == ["settle", "block"]


def test_truncated_reply_keeps_known_usage_and_only_static_error_metadata():
    ledger = Ledger()
    error = ModelOutputTruncatedError(
        model_id="model", input_tokens=9, output_tokens=20, duration_ms=13
    )
    model = Model(ledger, error=error)
    with pytest.raises(
        NarrativeBudgetCallError, match="MODEL_OUTPUT_TRUNCATED"
    ) as caught:
        _caller(ledger, model).generate(_context(), REQUEST)
    assert ledger.settlements[0]["usage"].total_tokens == 29
    assert caught.value.metrics.duration_ms == 13
    assert ledger.settlements[0]["response_sha256"] is None


def test_settlement_storage_failure_retains_nonzero_reserved_metrics():
    ledger = Ledger()
    ledger.fail_settle = True
    model = Model(ledger)
    with pytest.raises(
        NarrativeBudgetCallError, match="MODEL_BUDGET_STORE_FAILURE"
    ) as caught:
        _caller(ledger, model).generate(_context(), REQUEST)
    assert caught.value.metrics.tokens == 100
    assert caught.value.metrics.cost_usd == 0.000030
    assert model.calls == 1


def test_http_client_error_is_terminal_and_settles_unknown_at_the_reservation_bound():
    ledger = Ledger()
    model = Model(ledger, error=ModelHTTPError(400))
    with pytest.raises(NarrativeBudgetCallError) as caught:
        _caller(ledger, model).generate(_context(), REQUEST)
    error = caught.value
    assert error.code == "MODEL_HTTP_CLIENT_ERROR"
    assert error.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert type(error.http_status) is int and error.http_status == 400
    assert str(error) == "MODEL_HTTP_CLIENT_ERROR"
    assert ledger.settlements[0]["usage"] is None
    assert ledger.settlements[0]["error_code"] == "MODEL_HTTP_CLIENT_ERROR"
    assert ledger.settlements[0]["response_sha256"] is None
    assert (error.metrics.tokens, error.metrics.cost_usd) == (100, 0.000030)
    assert model.calls == 1


def test_http_server_error_is_retryable_and_keeps_unknown_usage_charged():
    ledger = Ledger()
    model = Model(ledger, error=ModelHTTPError(503))
    with pytest.raises(NarrativeBudgetCallError) as caught:
        _caller(ledger, model).generate(_context(), REQUEST)
    error = caught.value
    assert error.code == "MODEL_HTTP_SERVER_ERROR"
    assert error.outcome is HandlerOutcome.RETRYABLE
    assert type(error.http_status) is int and error.http_status == 503
    assert ledger.settlements[0]["usage"] is None
    assert ledger.settlements[0]["error_code"] == "MODEL_HTTP_SERVER_ERROR"
    assert error.metrics.tokens == 100
    assert model.calls == 1


def test_rate_limit_keeps_existing_retryable_unknown_settlement():
    ledger = Ledger()
    model = Model(ledger, error=ModelRateLimitError("MODEL_RATE_LIMIT"))
    with pytest.raises(NarrativeBudgetCallError) as caught:
        _caller(ledger, model).generate(_context(), REQUEST)
    error = caught.value
    assert error.code == "MODEL_RATE_LIMIT"
    assert error.outcome is HandlerOutcome.RETRYABLE
    assert error.http_status is None
    assert ledger.settlements[0]["usage"] is None
    assert ledger.settlements[0]["error_code"] == "MODEL_RATE_LIMIT"
    assert error.metrics.tokens == 100
    assert model.calls == 1
