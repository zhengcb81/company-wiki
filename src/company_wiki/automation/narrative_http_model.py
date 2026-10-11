"""One bounded OpenAI-compatible HTTP request, without SDK retry or fallback."""

from __future__ import annotations

import http.client
import ipaddress
import json
import math
import os
import re
import socket
import time
from typing import Any, Protocol
from urllib.parse import urlsplit

from .narrative_model import (
    MODEL_RESPONSE_MAX_BYTES,
    FailedFinalDiagnostic,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    NarrativeModelRequest,
    NarrativeModelResponse,
    validate_reasoning_observation,
)


class ModelRequestTooLargeError(ModelResponseError):
    """The request exceeds its cap before any network operation."""


class ModelResponseTooLargeError(ModelResponseError):
    """The provider envelope or returned content exceeds its cap."""


class ModelCredentialsError(ModelResponseError):
    """Credential validation failed before opening an HTTP connection."""


class ModelHTTPError(ModelResponseError):
    """HTTP status only; provider error bodies and URLs are never copied.

    ``status_code`` is the only provider diagnostic this exception retains,
    as a bounded integer between 100 and 599.  ``retryable`` and
    ``error_code`` give the stable classification: HTTP 4xx rejections other
    than 429, plus 3xx redirections this single-request adapter never
    follows, are terminal as ``MODEL_HTTP_CLIENT_ERROR``; 5xx responses are
    retryable as ``MODEL_HTTP_SERVER_ERROR``.  HTTP 429 keeps its dedicated
    rate-limit error and never reaches this class.
    """

    def __init__(self, status_code: int):
        if type(status_code) is not int or not 100 <= status_code <= 599:
            raise ValueError("status_code must be an integer between 100 and 599")
        self.status_code = status_code
        self.retryable = 500 <= status_code <= 599
        self.error_code = (
            "MODEL_HTTP_SERVER_ERROR" if self.retryable else "MODEL_HTTP_CLIENT_ERROR"
        )
        super().__init__(f"MODEL_HTTP_ERROR status={status_code}")


class ModelOutputTruncatedError(ModelResponseError):
    """A terminal provider result with metering and an optional bounded final."""

    def __init__(
        self,
        *,
        model_id: str,
        input_tokens: int | None,
        output_tokens: int | None,
        duration_ms: int,
        content_bytes: int | None = 0,
        reasoning_tokens: int | None = None,
        usage_diagnostic: str | None = None,
        failed_final: FailedFinalDiagnostic | None = None,
    ) -> None:
        if content_bytes is not None and (type(content_bytes) is not int or not 0 <= content_bytes <= MODEL_RESPONSE_MAX_BYTES):
            raise ValueError("invalid truncated content byte count")
        validate_reasoning_observation(reasoning_tokens, output_tokens, usage_diagnostic)
        self.reasoning_tokens, self.usage_diagnostic = reasoning_tokens, usage_diagnostic
        self.failed_final = failed_final
        self.finish_reason = "length"
        self.content_bytes = content_bytes
        self.model_id = model_id
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.duration_ms = duration_ms
        super().__init__("MODEL_OUTPUT_TRUNCATED")


def _failed_final_observation(body: bytes, content: str | None) -> FailedFinalDiagnostic | None:
    try:
        return FailedFinalDiagnostic.from_observation(provider_body=body, content=content)
    except Exception:
        # Observability is optional; keep the provider failure and its real usage.
        return None


class ModelEnvelopeError(ModelResponseError):
    """Static response diagnostics and valid usage, without provider text."""

    stages = frozenset({"json", "object", "provider_error", "choices", "message",
                        "content_type", "empty_content", "model_identity"})

    def __init__(self, response_stage: str, *, http_status: int = 200,
                 provider_code: int | None = None, input_tokens: int | None = None,
                 output_tokens: int | None = None, duration_ms: int = 0,
                 reasoning_tokens: int | None = None, usage_diagnostic: str | None = None,
                 failed_final: FailedFinalDiagnostic | None = None):
        if response_stage not in self.stages:
            raise ValueError("invalid response diagnostic stage")
        if type(http_status) is not int or not 100 <= http_status <= 599:
            raise ValueError("invalid response HTTP status")
        if provider_code is not None and (type(provider_code) is not int or not 0 < provider_code < 1_000_000):
            raise ValueError("invalid numeric provider code")
        if (input_tokens, output_tokens) != (None, None) and not all(
            type(value) is int and value >= 0 for value in (input_tokens, output_tokens)
        ):
            raise ValueError("invalid paired response usage")
        validate_reasoning_observation(reasoning_tokens, output_tokens, usage_diagnostic)
        self.reasoning_tokens, self.usage_diagnostic = reasoning_tokens, usage_diagnostic
        self.failed_final = failed_final
        self.response_stage, self.http_status, self.provider_code = response_stage, http_status, provider_code
        self.input_tokens, self.output_tokens, self.duration_ms = input_tokens, output_tokens, duration_ms
        super().__init__("MODEL_RESPONSE_INVALID")



def _reasoning_observation(usage: Any, output_tokens: int | None) -> tuple[int | None, str | None]:
    details = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
    if details is None:
        return None, None
    if not isinstance(details, dict):
        return None, "reasoning_usage_invalid"
    value = details.get("reasoning_tokens")
    if value is None:
        return None, None
    if type(value) is not int or value < 0 or output_tokens is None or value > output_tokens:
        return None, "reasoning_usage_invalid"
    return value, None


def _positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


class _LLMConfig(Protocol):
    provider: str
    model: str
    base_url: str
    api_key_env: str
    max_tokens: int
    temperature: float
    reasoning_split: bool


def model_options_from_config(llm: _LLMConfig, *, purpose: str = "narrative") -> dict[str, Any]:
    """Project already loaded its config; copy settings, never credential values.

    This is composition, not another config loader or provider defaults table.
    The token-field and reasoning policy matches the existing LLMClient.
    """
    if llm.provider not in {"minimax", "mimo", "deepseek", "openai"}:
        raise ValueError("configured provider is not OpenAI-compatible")
    options: dict[str, Any] = {
        "model_id": llm.model,
        "endpoint": llm.base_url.rstrip("/") + "/chat/completions",
        "api_key_env": llm.api_key_env,
        "max_output_tokens": llm.max_tokens,
        "temperature": llm.temperature,
        "output_token_field": "max_completion_tokens"
        if llm.provider in {"minimax", "mimo"} else "max_tokens",
    }
    if llm.provider == "minimax" and llm.reasoning_split:
        options["reasoning_split"] = True
    resolver = getattr(llm, "generation_options", None)
    generation = resolver(purpose) if callable(resolver) else {}
    if "thinking" in generation:
        options["thinking"] = generation["thinking"]["type"]
    if "reasoning_effort" in generation:
        options["reasoning_effort"] = generation["reasoning_effort"]
    return options


class NarrativeHTTPModel:
    """Stateless request adapter; a durable caller owns retry and fee accounting."""

    adapter_id = "openai-compatible-http/1"

    def __init__(
        self,
        *,
        model_id: str,
        endpoint: str,
        api_key_env: str,
        max_output_tokens: int = 2400,
        timeout_seconds: float = 60,
        max_request_bytes: int = 262_144,
        max_response_bytes: int = 262_144,
        allow_local_http: bool = False,
        thinking: str | None = None,
        reasoning_effort: str | None = None,
        temperature: float | None = None,
        reasoning_split: bool | None = None,
        output_token_field: str = "max_tokens",
    ) -> None:
        if (
            not isinstance(model_id, str)
            or not model_id.strip()
            or model_id != model_id.strip()
        ):
            raise ValueError("model_id must be nonempty and trimmed")
        if not isinstance(api_key_env, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", api_key_env
        ):
            raise ValueError("api_key_env must name an environment variable")
        if (
            not isinstance(endpoint, str)
            or not endpoint
            or any(char.isspace() for char in endpoint)
        ):
            raise ValueError("endpoint must be a complete URL without whitespace")
        parsed = urlsplit(endpoint)
        if (
            not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or "?" in endpoint
            or "#" in endpoint
        ):
            raise ValueError("endpoint cannot contain userinfo, query or fragment")
        if parsed.scheme != "https":
            if parsed.scheme != "http" or not allow_local_http:
                raise ValueError("endpoint must use HTTPS")
            try:
                loopback = ipaddress.ip_address(parsed.hostname).is_loopback
            except ValueError:
                loopback = False
            if not loopback:
                raise ValueError("HTTP endpoint must be an explicit loopback IP")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be finite and positive")
        self.model_id = model_id
        self.api_key_env = api_key_env
        self.max_output_tokens = _positive_integer(
            max_output_tokens, "max_output_tokens"
        )
        self.max_request_bytes = _positive_integer(
            max_request_bytes, "max_request_bytes"
        )
        self.max_response_bytes = _positive_integer(
            max_response_bytes, "max_response_bytes"
        )
        self.timeout_seconds = float(timeout_seconds)
        if thinking is not None and (
            not isinstance(thinking, str) or thinking not in {"disabled", "adaptive", "enabled"}
        ):
            raise ValueError("thinking must be disabled, adaptive, enabled or omitted")
        self.thinking = thinking
        if reasoning_effort is not None and (
            not isinstance(reasoning_effort, str) or reasoning_effort not in {"low", "high", "max"}
        ):
            raise ValueError("reasoning_effort must be low, high, max or omitted")
        self.reasoning_effort = reasoning_effort
        if temperature is not None and (
            isinstance(temperature, bool)
            or not isinstance(temperature, (float, int))
            or not math.isfinite(temperature)
            or not 0 <= temperature <= 2
        ):
            raise ValueError("temperature must be finite and within [0, 2]")
        if reasoning_split is not None and type(reasoning_split) is not bool:
            raise ValueError("reasoning_split must be boolean or omitted")
        if output_token_field not in {"max_tokens", "max_completion_tokens"}:
            raise ValueError("output_token_field must name a supported token limit")
        self.temperature = temperature
        self.reasoning_split = reasoning_split
        self.output_token_field = output_token_field
        self._scheme = parsed.scheme
        self._host = parsed.hostname
        self._port = parsed.port
        self._path = parsed.path or "/"

    def request_bytes(self, request: NarrativeModelRequest) -> bytes:
        """The exact, secret-free body, also usable for pre-request reservation."""
        if not isinstance(request, NarrativeModelRequest):
            raise ModelResponseError("MODEL_REQUEST_INVALID")
        request = request.with_output_budget(self.max_output_tokens)
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": request.instruction},
                {"role": "user", "content": request.data_json},
            ],
            self.output_token_field: self.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.thinking is not None:
            payload["thinking"] = {"type": self.thinking}
        if self.reasoning_effort is not None:
            payload["reasoning_effort"] = self.reasoning_effort
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.reasoning_split is not None:
            payload["reasoning_split"] = self.reasoning_split
        try:
            body = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        except (ValueError, TypeError, UnicodeError):
            raise ModelResponseError("MODEL_REQUEST_INVALID") from None
        if len(body) > self.max_request_bytes:
            raise ModelRequestTooLargeError("MODEL_REQUEST_TOO_LARGE")
        return body

    def generate(self, request: NarrativeModelRequest) -> NarrativeModelResponse:
        body = self.request_bytes(request)
        # No key is cached in this object, options, request body or model identity.
        raw_key = os.environ.get(self.api_key_env, "")
        key = raw_key.strip()
        if not key:
            raise ModelCredentialsError("MODEL_KEY_MISSING")
        if any(ord(char) < 32 or ord(char) > 126 for char in raw_key):
            raise ModelCredentialsError("MODEL_KEY_INVALID")
        started = time.monotonic()
        deadline = started + self.timeout_seconds
        connection_type = (
            http.client.HTTPSConnection
            if self._scheme == "https"
            else http.client.HTTPConnection
        )
        connection = connection_type(
            self._host, self._port, timeout=self.timeout_seconds
        )
        try:
            connection.request(
                "POST",
                self._path,
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                },
            )
            response_socket = connection.sock
            if response_socket is not None:
                response_socket.settimeout(self._remaining(deadline))
            response = connection.getresponse()
            if response.status == 429:
                raise ModelRateLimitError("MODEL_RATE_LIMIT")
            if not 200 <= response.status < 300:
                raise ModelHTTPError(response.status)
            size = response.getheader("Content-Length")
            if size is not None and int(size) > self.max_response_bytes:
                raise ModelResponseTooLargeError("MODEL_RESPONSE_TOO_LARGE")
            chunks: list[bytes] = []
            total = 0
            # read1 closes its file when the declared body is consumed. Do not
            # touch the socket again after that public response state changes.
            while not response.isclosed():
                remaining = self._remaining(deadline)
                if response_socket is not None:
                    response_socket.settimeout(remaining)
                chunk = response.read1(min(65_536, self.max_response_bytes + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > self.max_response_bytes:
                    raise ModelResponseTooLargeError("MODEL_RESPONSE_TOO_LARGE")
                chunks.append(chunk)
            return self._response(request, b"".join(chunks), started, http_status=response.status)
        except (socket.timeout, TimeoutError):
            raise ModelTimeoutError("MODEL_TIMEOUT") from None
        except (OSError, http.client.HTTPException, ValueError, UnicodeError):
            raise ModelResponseError("MODEL_HTTP_TRANSPORT") from None
        finally:
            connection.close()

    @staticmethod
    def _remaining(deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ModelTimeoutError("MODEL_TIMEOUT")
        return remaining

    def _response(
        self, request: NarrativeModelRequest, body: bytes, started: float, *, http_status: int = 200,
    ) -> NarrativeModelResponse:
        input_tokens = output_tokens = provider_code = reasoning_tokens = None
        usage_diagnostic = None
        stage = "json"
        try:
            payload = json.loads(body.decode("utf-8"))
            stage = "object"
            if not isinstance(payload, dict):
                raise ValueError("invalid object")
            usage = payload.get("usage")
            input_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
            output_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
            if not all(type(value) is int and value >= 0 for value in (input_tokens, output_tokens)):
                input_tokens = output_tokens = None
            reasoning_tokens, usage_diagnostic = _reasoning_observation(usage, output_tokens)
            base = payload.get("base_resp")
            numeric_code = base.get("status_code") if isinstance(base, dict) else None
            if type(numeric_code) is int and 0 < numeric_code < 1_000_000:
                provider_code = numeric_code
            if provider_code is not None or payload.get("error"):
                stage = "provider_error"
                raise ValueError("provider returned an error")
            stage = "choices"
            choice = payload["choices"][0]
            stage = "message"
            content = choice["message"]["content"]
            observed_content = content if isinstance(content, str) else None
            truncated = choice.get("finish_reason") == "length"
            if content is None and truncated:
                content = ""
            stage = "content_type"
            if not isinstance(content, str):
                raise ValueError("invalid content")
            encoded = content.encode("utf-8")
            stage = "model_identity"
            actual_model = payload.get("model", self.model_id)
            if not isinstance(actual_model, str) or not actual_model.strip():
                raise ValueError("invalid model identity")
        except (
            UnicodeError,
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            AttributeError,
            RecursionError,
        ):
            raise ModelEnvelopeError(stage, http_status=http_status, provider_code=provider_code,
                input_tokens=input_tokens, output_tokens=output_tokens,
                reasoning_tokens=reasoning_tokens, usage_diagnostic=usage_diagnostic,
                duration_ms=max(0, int((time.monotonic() - started) * 1000))) from None
        if len(encoded) > MODEL_RESPONSE_MAX_BYTES:
            raise ModelResponseTooLargeError("MODEL_RESPONSE_TOO_LARGE")
        duration_ms = max(0, int((time.monotonic() - started) * 1000))
        if truncated:
            raise ModelOutputTruncatedError(
                model_id=actual_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                content_bytes=len(encoded) if observed_content is not None else None, reasoning_tokens=reasoning_tokens,
                usage_diagnostic=usage_diagnostic,
                failed_final=_failed_final_observation(body, observed_content),
            )
        if not encoded:
            raise ModelEnvelopeError("empty_content", http_status=http_status,
                input_tokens=input_tokens, output_tokens=output_tokens, duration_ms=duration_ms,
                reasoning_tokens=reasoning_tokens, usage_diagnostic=usage_diagnostic,
                failed_final=_failed_final_observation(body, observed_content))
        return NarrativeModelResponse(
            adapter_id=self.adapter_id,
            model_id=actual_model,
            prompt_version=request.prompt_version,
            response_bytes=encoded,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            reasoning_tokens=reasoning_tokens, usage_diagnostic=usage_diagnostic,
        )


__all__ = [
    "ModelCredentialsError",
    "ModelEnvelopeError",
    "ModelHTTPError",
    "ModelOutputTruncatedError",
    "ModelRequestTooLargeError",
    "ModelResponseTooLargeError",
    "NarrativeHTTPModel",
]
