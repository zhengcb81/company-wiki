"""Real loopback HTTP tests for the single-request narrative model adapter."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import threading
import time
from types import SimpleNamespace

import pytest

from company_wiki.automation.narrative_model import (
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    NarrativeModelRequest,
)


_CONNECT = socket.socket.connect
_CREATE_CONNECTION = socket.create_connection
KEY_ENV = "NARRATIVE_TEST_API_KEY"
KEY = "synthetic-key-never-a-live-credential"
REQUEST = NarrativeModelRequest(
    "prompt/1", "Use source data only.", '{"text":"业务进展"}', "a" * 64
)


def _model(**options):
    from company_wiki.automation.narrative_http_model import NarrativeHTTPModel

    return NarrativeHTTPModel(
        model_id="requested-model",
        api_key_env=KEY_ENV,
        **options,
    )


def _response(**overrides):
    value = {
        "model": "actual-provider-model",
        "choices": [
            {
                "message": {"content": '{"draft":{"text":"业务进展"}}'},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 73, "completion_tokens": 19},
    }
    value.update(overrides)
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


@pytest.fixture
def stub(monkeypatch, hermetic_runtime):
    state = SimpleNamespace(
        body=_response(),
        status=200,
        headers={},
        delay=0,
        calls=[],
        send_length=True,
        drip=False,
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            state.calls.append((self.path, dict(self.headers), body))
            time.sleep(state.delay)
            try:
                self.send_response(state.status)
                if state.send_length:
                    self.send_header("Content-Length", str(len(state.body)))
                for name, value in state.headers.items():
                    self.send_header(name, value)
                self.end_headers()
                if state.drip:
                    for byte in state.body:
                        self.wfile.write(bytes((byte,)))
                        self.wfile.flush()
                        time.sleep(0.01)
                else:
                    self.wfile.write(state.body)
            except (BrokenPipeError, ConnectionResetError):
                pass  # The timeout/cap test already closed its client.

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = False  # server_close joins every request handler.
    address = ("127.0.0.1", server.server_port)

    def connect(sock, target):
        assert target == address, "test may connect only to its own loopback stub"
        return _CONNECT(sock, target)

    def create_connection(target, *args, **kwargs):
        assert target == address, "test may connect only to its own loopback stub"
        return _CREATE_CONNECTION(target, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setenv(KEY_ENV, KEY)
    state.endpoint = f"http://127.0.0.1:{server.server_port}/v1/chat/completions"
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01))
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def test_single_post_preserves_roles_identity_usage_and_original_language(stub):
    model = _model(endpoint=stub.endpoint, allow_local_http=True, max_output_tokens=321)
    response = model.generate(REQUEST)
    assert response.adapter_id == "openai-compatible-http/1"
    assert response.model_id == "actual-provider-model"
    assert response.prompt_version == REQUEST.prompt_version
    assert (response.input_tokens, response.output_tokens) == (73, 19)
    assert isinstance(response.duration_ms, int) and response.duration_ms >= 0
    assert response.response_bytes == '{"draft":{"text":"业务进展"}}'.encode("utf-8")
    assert len(stub.calls) == 1
    path, headers, body = stub.calls[0]
    assert path == "/v1/chat/completions"
    assert headers["Authorization"] == f"Bearer {KEY}"
    assert body == model.request_bytes(REQUEST)
    assert json.loads(body) == {
        "model": "requested-model",
        "messages": [
            {"role": "system", "content": REQUEST.instruction},
            {"role": "user", "content": REQUEST.data_json},
        ],
        "max_tokens": 321,
        "response_format": {"type": "json_object"},
    }
    assert KEY not in repr(model) and KEY.encode() not in body


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"prompt_tokens": True, "completion_tokens": 1},
        {"prompt_tokens": -1, "completion_tokens": 1},
    ],
)
def test_missing_or_invalid_usage_is_unknown_not_zero(stub, usage):
    stub.body = _response(usage=usage)
    response = _model(endpoint=stub.endpoint, allow_local_http=True).generate(REQUEST)
    assert response.input_tokens is None and response.output_tokens is None


def test_key_is_read_at_generate_and_not_cached_in_adapter(stub, monkeypatch):
    from company_wiki.automation.narrative_http_model import ModelCredentialsError

    monkeypatch.delenv(KEY_ENV)
    model = _model(endpoint=stub.endpoint, allow_local_http=True)
    with pytest.raises(ModelCredentialsError, match="MODEL_KEY_MISSING"):
        model.generate(REQUEST)
    assert stub.calls == []
    monkeypatch.setenv(KEY_ENV, "rotated-synthetic-key")
    model.generate(REQUEST)
    assert stub.calls[0][1]["Authorization"] == "Bearer rotated-synthetic-key"
    assert "rotated-synthetic-key" not in repr(model)


@pytest.mark.parametrize(
    "key",
    ["nonascii-密钥", "key\r\ninjected-header", "key\x01control", "key\x7fcontrol"],
)
def test_invalid_header_credentials_are_rejected_before_http(stub, monkeypatch, key):
    from company_wiki.automation.narrative_http_model import ModelCredentialsError

    monkeypatch.setenv(KEY_ENV, key)
    with pytest.raises(ModelCredentialsError, match="^MODEL_KEY_INVALID$") as error:
        _model(endpoint=stub.endpoint, allow_local_http=True).generate(REQUEST)
    assert key not in repr(error.value)
    assert stub.calls == []


def test_complete_response_without_content_length_ends_at_eof(stub):
    stub.send_length = False
    response = _model(endpoint=stub.endpoint, allow_local_http=True).generate(REQUEST)
    assert response.response_bytes == '{"draft":{"text":"业务进展"}}'.encode("utf-8")
    assert len(stub.calls) == 1


def test_empty_response_is_invalid_envelope_not_a_transport_failure(stub):
    stub.body = b""
    with pytest.raises(ModelResponseError, match="MODEL_RESPONSE_INVALID"):
        _model(endpoint=stub.endpoint, allow_local_http=True).generate(REQUEST)
    assert len(stub.calls) == 1


def test_request_cap_stops_before_http(stub):
    model = _model(endpoint=stub.endpoint, allow_local_http=True, max_request_bytes=10)
    with pytest.raises(ModelResponseError, match="MODEL_REQUEST_TOO_LARGE"):
        model.generate(REQUEST)
    assert stub.calls == []


def test_response_cap_stops_large_body_without_echoing_it(stub):
    stub.body = (KEY + REQUEST.data_json).encode() * 100
    model = _model(endpoint=stub.endpoint, allow_local_http=True, max_response_bytes=64)
    with pytest.raises(ModelResponseError, match="MODEL_RESPONSE_TOO_LARGE") as error:
        model.generate(REQUEST)
    assert KEY not in str(error.value) and REQUEST.data_json not in str(error.value)
    assert len(stub.calls) == 1


def test_response_cap_also_applies_without_content_length(stub):
    stub.send_length = False
    stub.body = b"x" * 1000
    model = _model(endpoint=stub.endpoint, allow_local_http=True, max_response_bytes=64)
    with pytest.raises(ModelResponseError, match="MODEL_RESPONSE_TOO_LARGE"):
        model.generate(REQUEST)
    assert len(stub.calls) == 1


@pytest.mark.parametrize("status", [302, 401, 429, 500])
def test_http_errors_do_not_retry_redirect_or_echo_provider_body(stub, status):
    stub.status = status
    stub.headers = {"Location": stub.endpoint + "/would-leak"}
    stub.body = (KEY + REQUEST.data_json).encode()
    model = _model(endpoint=stub.endpoint, allow_local_http=True)
    exception = ModelRateLimitError if status == 429 else ModelResponseError
    with pytest.raises(exception) as error:
        model.generate(REQUEST)
    assert KEY not in str(error.value) and REQUEST.data_json not in str(error.value)
    assert len(stub.calls) == 1


def test_timeout_is_named_and_one_request(stub):
    stub.delay = 0.3
    model = _model(endpoint=stub.endpoint, allow_local_http=True, timeout_seconds=0.1)
    with pytest.raises(ModelTimeoutError, match="MODEL_TIMEOUT"):
        model.generate(REQUEST)
    assert len(stub.calls) == 1


def test_streaming_body_cannot_reset_the_overall_read_deadline(stub):
    stub.send_length = False
    stub.drip = True
    model = _model(endpoint=stub.endpoint, allow_local_http=True, timeout_seconds=0.1)
    with pytest.raises(ModelTimeoutError, match="MODEL_TIMEOUT"):
        model.generate(REQUEST)
    assert len(stub.calls) == 1


@pytest.mark.parametrize(
    "usage,expected_tokens",
    [
        ({"prompt_tokens": 73, "completion_tokens": 19}, (73, 19)),
        (None, (None, None)),
    ],
)
@pytest.mark.parametrize("content", [None, "", KEY + REQUEST.data_json])
def test_truncated_output_carries_metering_without_content_or_secret(
    stub, usage, expected_tokens, content
):
    from company_wiki.automation.narrative_http_model import ModelOutputTruncatedError

    stub.body = _response(
        choices=[{"message": {"content": content}, "finish_reason": "length"}],
        usage=usage,
    )
    with pytest.raises(
        ModelOutputTruncatedError, match="^MODEL_OUTPUT_TRUNCATED$"
    ) as error:
        _model(endpoint=stub.endpoint, allow_local_http=True).generate(REQUEST)
    assert error.value.model_id == "actual-provider-model"
    assert (error.value.input_tokens, error.value.output_tokens) == expected_tokens
    assert type(error.value.duration_ms) is int and error.value.duration_ms >= 0
    assert KEY not in repr(error.value)
    if content:
        assert content not in repr(error.value)
    assert not hasattr(error.value, "response_bytes")
    assert len(stub.calls) == 1


@pytest.mark.parametrize("thinking", ["disabled", "adaptive"])
def test_explicit_thinking_control_reaches_the_one_bounded_post(stub, thinking):
    model = _model(endpoint=stub.endpoint, allow_local_http=True, thinking=thinking)
    result = model.generate(REQUEST)
    assert (result.input_tokens, result.output_tokens) == (73, 19)
    assert len(stub.calls) == 1
    assert json.loads(stub.calls[0][2])["thinking"] == {"type": thinking}
    assert stub.calls[0][2] == model.request_bytes(REQUEST)


@pytest.mark.parametrize("thinking", [False, "none", "", {}, ["disabled"]])
def test_invalid_thinking_control_is_rejected_without_a_request(stub, thinking):
    with pytest.raises(ValueError, match="thinking"):
        _model(endpoint=stub.endpoint, allow_local_http=True, thinking=thinking)
    assert stub.calls == []


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        b"[]",
        b'{"choices":[]}',
        b'{"choices":[{"message":{"content":"cut"},"finish_reason":"length"}]}',
    ],
)
def test_invalid_envelope_or_truncated_output_has_named_static_error(stub, body):
    stub.body = body
    with pytest.raises(ModelResponseError, match="MODEL_") as error:
        _model(endpoint=stub.endpoint, allow_local_http=True).generate(REQUEST)
    assert KEY not in str(error.value) and "not-json" not in str(error.value)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:9/v1/chat/completions",
        "http://198.51.100.1/v1/chat/completions",
        "https://user:secret@example.invalid/v1/chat/completions",
        "https://example.invalid/v1/chat/completions?key=secret",
        "https://example.invalid/v1/chat/completions#secret",
    ],
)
def test_endpoint_refuses_plain_http_or_credentials_query_fragment(endpoint):
    with pytest.raises(ValueError, match="endpoint"):
        _model(endpoint=endpoint)


def test_local_http_override_cannot_admit_non_loopback_host():
    with pytest.raises(ValueError, match="loopback"):
        _model(
            endpoint="http://198.51.100.1/v1/chat/completions", allow_local_http=True
        )


@pytest.mark.parametrize("status", [400, 401, 404])
def test_client_rejection_is_terminal_and_keeps_only_the_integer_status(stub, status):
    from company_wiki.automation.narrative_http_model import ModelHTTPError

    stub.status = status
    stub.headers = {"Location": stub.endpoint + "/would-leak"}
    stub.body = (KEY + REQUEST.data_json).encode()
    with pytest.raises(ModelHTTPError) as error:
        _model(endpoint=stub.endpoint, allow_local_http=True).generate(REQUEST)
    assert error.value.status_code == status
    assert error.value.retryable is False
    assert error.value.error_code == "MODEL_HTTP_CLIENT_ERROR"
    assert str(error.value) == f"MODEL_HTTP_ERROR status={status}"
    assert KEY not in str(error.value) and REQUEST.data_json not in str(error.value)
    assert len(stub.calls) == 1


@pytest.mark.parametrize("status", [500, 502, 503])
def test_server_failure_is_retryable_and_keeps_only_the_integer_status(stub, status):
    from company_wiki.automation.narrative_http_model import ModelHTTPError

    stub.status = status
    stub.headers = {"Location": stub.endpoint + "/would-leak"}
    stub.body = (KEY + REQUEST.data_json).encode()
    with pytest.raises(ModelHTTPError) as error:
        _model(endpoint=stub.endpoint, allow_local_http=True).generate(REQUEST)
    assert error.value.status_code == status
    assert error.value.retryable is True
    assert error.value.error_code == "MODEL_HTTP_SERVER_ERROR"
    assert str(error.value) == f"MODEL_HTTP_ERROR status={status}"
    assert KEY not in str(error.value) and REQUEST.data_json not in str(error.value)
    assert len(stub.calls) == 1


@pytest.mark.parametrize(
    "body",
    [
        b'{"model":"actual-provider-model"}',
        b'{"choices":[{"message":{"content":123}}]}',
        b'{"choices":[{"message":{"content":""},"finish_reason":"stop"}]}',
    ],
)
def test_malformed_2xx_envelope_stays_a_bounded_response_failure_not_an_http_error(
    stub, body
):
    from company_wiki.automation.narrative_http_model import ModelHTTPError

    stub.status = 200
    stub.body = body
    with pytest.raises(ModelResponseError, match="MODEL_RESPONSE_INVALID") as error:
        _model(endpoint=stub.endpoint, allow_local_http=True).generate(REQUEST)
    assert not isinstance(error.value, ModelHTTPError)
    assert KEY not in str(error.value)
    assert len(stub.calls) == 1
