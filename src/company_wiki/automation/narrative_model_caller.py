"""Durable admission and metering around exactly one model attempt."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import time
from typing import Protocol, TYPE_CHECKING

from .execution_context import JobExecutionContext
from .models import HandlerMetrics, HandlerOutcome, canonical_json_hash
from .narrative_http_model import (
    ModelCredentialsError,
    ModelEnvelopeError,
    ModelHTTPError,
    ModelOutputTruncatedError,
    ModelRequestTooLargeError,
    NarrativeHTTPModel,
)
from .narrative_model import (
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    NarrativeModelRequest,
    NarrativeModelResponse,
)

if TYPE_CHECKING:
    from .narrative_run_store import ModelUsage, NarrativeRunStore, ReservationRecord


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class NarrativeModelCaller(Protocol):
    def generate(
        self, context: JobExecutionContext, request: NarrativeModelRequest
    ) -> tuple[NarrativeModelResponse, HandlerMetrics]: ...


@dataclass(frozen=True)
class NarrativeBudgetCallError(Exception):
    code: str
    outcome: HandlerOutcome
    metrics: HandlerMetrics
    http_status: int | None = None
    response_stage: str | None = None
    provider_code: int | None = None

    def __post_init__(self) -> None:
        if self.http_status is not None and (
            type(self.http_status) is not int or not 100 <= self.http_status <= 599
        ):
            raise ValueError(
                "http_status must be an integer between 100 and 599 or None"
            )
        if self.response_stage is not None and self.response_stage not in ModelEnvelopeError.stages:
            raise ValueError("invalid response diagnostic stage")
        if self.provider_code is not None and (type(self.provider_code) is not int or not 0 < self.provider_code < 1_000_000):
            raise ValueError("invalid numeric provider code")

    def __str__(self) -> str:
        return self.code


def _metrics(record: ReservationRecord, duration_ms: int) -> HandlerMetrics:
    # Unknown requests report their conservative reservation; the ledger keeps
    # usage_status so nobody mistakes this estimate for provider billing.
    return HandlerMetrics(
        tokens=record.charged_tokens,
        cost_usd=record.charged_micro_usd / 1_000_000,
        duration_ms=duration_ms,
    )


_ZERO = HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0)


class BudgetedNarrativeCaller:
    def __init__(
        self,
        *,
        store: NarrativeRunStore,
        run_id: str,
        model: NarrativeHTTPModel,
        final_output_bytes_bound: int = 2 * 1024 * 1024,
        clock: Callable[[], str] = _utc_now,
    ) -> None:
        if type(final_output_bytes_bound) is not int or final_output_bytes_bound <= 0:
            raise ValueError("final output bound must be a positive integer")
        self._store, self._run_id, self._model = store, run_id, model
        self._output_bound, self._clock = final_output_bytes_bound, clock

    def generate(
        self, context: JobExecutionContext, request: NarrativeModelRequest
    ) -> tuple[NarrativeModelResponse, HandlerMetrics]:
        from .narrative_run_store import ModelUsage

        try:
            body = self._model.request_bytes(request)
        except ModelRequestTooLargeError:
            raise NarrativeBudgetCallError(
                "MODEL_REQUEST_TOO_LARGE", HandlerOutcome.TERMINAL_FAILURE, _ZERO
            ) from None
        context.checkpoint()
        attempt = context.attempt
        try:
            run = self._store.get_run(self._run_id)
            if run is None:
                raise ValueError("narrative run is missing")
            admission = self._store.reserve_model_attempt(
                run_id=self._run_id,
                job_id=context.job.job_id,
                attempt_id=attempt.attempt_id,
                lease_token=attempt.lease_token,
                runtime_generation=attempt.runtime_generation,
                request_sha256=canonical_json_hash({
                    "schema_version": "narrative-model-attempt/2",
                    "model_input_sha256": request.input_sha256,
                    "http_body_sha256": hashlib.sha256(body).hexdigest(),
                }),
                model_id=self._model.model_id,
                prompt_version=request.prompt_version,
                pricing_version=run.pricing_version,
                input_tokens_bound=len(body) + 128,
                max_output_tokens=self._model.max_output_tokens,
                output_bytes_bound=self._output_bound,
                now=self._clock(),
            )
        except Exception:
            raise NarrativeBudgetCallError(
                "MODEL_BUDGET_DENIED", HandlerOutcome.TERMINAL_FAILURE, _ZERO
            ) from None
        if not admission.may_send_http:
            raise NarrativeBudgetCallError(
                "MODEL_REQUEST_ALREADY_RESERVED",
                HandlerOutcome.TERMINAL_FAILURE,
                _metrics(admission.record, 0),
            )
        started = time.monotonic()
        try:
            context.checkpoint()
        except Exception:
            # This process knows generate has not started; unlike a crash, that
            # is enough evidence to settle the unspent attempt at zero.
            self._settle(
                context,
                fallback=admission.record,
                usage=ModelUsage(0, 0),
                response_sha256=None,
                error_code="LEASE_LOST",
                duration_ms=0,
                no_output=True,
            )
            raise NarrativeBudgetCallError(
                "LEASE_LOST", HandlerOutcome.RETRYABLE, _ZERO
            ) from None
        try:
            response = self._model.generate(request)
        except Exception as error:
            code, outcome = "MODEL_RESPONSE_INVALID", HandlerOutcome.TERMINAL_FAILURE
            usage = None
            http_status = None
            response_stage = provider_code = None
            duration_ms = max(0, int((time.monotonic() - started) * 1000))
            if isinstance(error, ModelTimeoutError):
                code, outcome = "MODEL_TIMEOUT", HandlerOutcome.RETRYABLE
            elif isinstance(error, ModelRateLimitError):
                code, outcome = "MODEL_RATE_LIMIT", HandlerOutcome.RETRYABLE
            elif isinstance(error, ModelHTTPError):
                # The status alone is a safe diagnostic; the settled attempt
                # still has no verified provider usage, so its reservation
                # bound remains the charge.
                code, outcome = (
                    error.error_code,
                    (
                        HandlerOutcome.RETRYABLE
                        if error.retryable
                        else HandlerOutcome.TERMINAL_FAILURE
                    ),
                )
                http_status = error.status_code
            elif isinstance(error, ModelCredentialsError):
                code, usage = "MODEL_CREDENTIALS_INVALID", ModelUsage(0, 0)
            elif isinstance(error, ModelEnvelopeError):
                http_status, response_stage, provider_code = error.http_status, error.response_stage, error.provider_code
                duration_ms = error.duration_ms
                if error.input_tokens is not None and error.output_tokens is not None:
                    usage = ModelUsage(error.input_tokens, error.output_tokens)
            elif isinstance(error, ModelOutputTruncatedError):
                code, duration_ms = "MODEL_OUTPUT_TRUNCATED", error.duration_ms
                if error.input_tokens is not None and error.output_tokens is not None:
                    usage = ModelUsage(error.input_tokens, error.output_tokens)
            elif not isinstance(error, ModelResponseError):
                code = "MODEL_TRANSPORT_FAILED"
            metrics = self._settle(
                context,
                fallback=admission.record,
                usage=usage,
                response_sha256=None,
                error_code=code,
                duration_ms=duration_ms,
                no_output=True,
            )
            raise NarrativeBudgetCallError(
                code, outcome, metrics, http_status=http_status,
                response_stage=response_stage, provider_code=provider_code,
            ) from None
        usage = None
        if response.input_tokens is not None and response.output_tokens is not None:
            usage = ModelUsage(response.input_tokens, response.output_tokens)
        metrics = self._settle(
            context,
            fallback=admission.record,
            usage=usage,
            response_sha256=response.response_sha256,
            error_code=None,
            duration_ms=response.duration_ms,
            no_output=False,
        )
        try:
            if response.model_id != run.model_id:
                self._store.block_run(
                    self._run_id,
                    error_code="MODEL_ID_CHANGED",
                    updated_at=self._clock(),
                )
                raise NarrativeBudgetCallError(
                    "MODEL_ID_CHANGED", HandlerOutcome.TERMINAL_FAILURE, metrics
                )
            current_run = self._store.get_run(self._run_id)
            if current_run is None:
                raise ValueError("narrative run disappeared")
            if current_run.blocked:
                raise NarrativeBudgetCallError(
                    "MODEL_USAGE_EXCEEDED", HandlerOutcome.TERMINAL_FAILURE, metrics
                )
        except NarrativeBudgetCallError:
            raise
        except Exception:
            raise NarrativeBudgetCallError(
                "MODEL_BUDGET_STORE_FAILURE", HandlerOutcome.TERMINAL_FAILURE, metrics
            ) from None
        return response, metrics

    def _settle(
        self,
        context: JobExecutionContext,
        *,
        fallback: ReservationRecord,
        usage: ModelUsage | None,
        response_sha256: str | None,
        error_code: str | None,
        duration_ms: int,
        no_output: bool,
    ) -> HandlerMetrics:
        try:
            record = self._store.settle_model_usage(
                run_id=self._run_id,
                attempt_id=context.attempt.attempt_id,
                usage=usage,
                response_sha256=response_sha256,
                error_code=error_code,
                settled_at=self._clock(),
            )
            if no_output:
                self._store.settle_output(
                    run_id=self._run_id,
                    attempt_id=context.attempt.attempt_id,
                    output_bytes=0,
                    output_sha256=None,
                    settled_at=self._clock(),
                )
            return _metrics(record, duration_ms)
        except Exception:
            # The original reservation remains if SQLite fails; do not leak a
            # provider exception or pretend the request was free.
            raise NarrativeBudgetCallError(
                "MODEL_BUDGET_STORE_FAILURE",
                HandlerOutcome.TERMINAL_FAILURE,
                _metrics(fallback, duration_ms),
            ) from None


__all__ = [
    "BudgetedNarrativeCaller",
    "NarrativeBudgetCallError",
    "NarrativeModelCaller",
]
