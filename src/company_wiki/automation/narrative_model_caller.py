"""Durable admission and metering around exactly one model attempt."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import hashlib
import sqlite3
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
    FailedFinalDiagnostic,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    NarrativeModelRequest,
    NarrativeModelResponse,
)
from .narrative_paid_response import PaidResponseArtifacts, PaidResponseError

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
    finish_reason: str | None = None
    content_bytes: int | None = None
    failed_final: FailedFinalDiagnostic | None = None

    def __post_init__(self) -> None:
        if self.failed_final is not None and not isinstance(self.failed_final, FailedFinalDiagnostic):
            raise TypeError("failed_final must be a typed observation or null")
        if self.finish_reason not in {None, "length"}:
            raise ValueError("invalid response finish diagnostic")
        if self.content_bytes is not None and (type(self.content_bytes) is not int
                or not 0 <= self.content_bytes <= 128 * 1024):
            raise ValueError("invalid response content byte diagnostic")
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


def _metrics(record: ReservationRecord, duration_ms: int, *, reasoning_tokens: int | None = None,
             usage_diagnostic: str | None = None) -> HandlerMetrics:
    # Unknown requests report their conservative reservation; the ledger keeps
    # usage_status so nobody mistakes this estimate for provider billing.
    return HandlerMetrics(
        tokens=record.charged_tokens,
        cost_usd=record.charged_micro_usd / 1_000_000,
        duration_ms=duration_ms,
        reasoning_tokens=reasoning_tokens, usage_diagnostic=usage_diagnostic,
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
        paid_responses: PaidResponseArtifacts | None = None,
    ) -> None:
        if type(final_output_bytes_bound) is not int or final_output_bytes_bound <= 0:
            raise ValueError("final output bound must be a positive integer")
        self._store, self._run_id, self._model = store, run_id, model
        self._output_bound, self._clock = final_output_bytes_bound, clock
        self._paid_responses = paid_responses

    def generate(
        self, context: JobExecutionContext, request: NarrativeModelRequest
    ) -> tuple[NarrativeModelResponse, HandlerMetrics]:
        from .narrative_run_store import (
            ModelUsage, RunBudgetExceededError, RunConflictError,
            RunScopeError, ReservationConflictError,
        )
        from .store import LeaseLostError, StoreBusyError

        try:
            body = self._model.request_bytes(request)
        except ModelRequestTooLargeError:
            raise NarrativeBudgetCallError(
                "MODEL_REQUEST_TOO_LARGE", HandlerOutcome.TERMINAL_FAILURE, _ZERO
            ) from None
        context.checkpoint()
        attempt = context.attempt
        recovered = None
        request_sha256 = canonical_json_hash({
            "schema_version": "narrative-model-attempt/2",
            "model_input_sha256": request.input_sha256,
            "http_body_sha256": hashlib.sha256(body).hexdigest(),
        })
        try:
            run = self._store.get_run(self._run_id)
            if run is None:
                raise NarrativeBudgetCallError(
                    "MODEL_RUN_MISSING", HandlerOutcome.TERMINAL_FAILURE, _ZERO
                )
            if self._paid_responses is not None:
                try:
                    self._paid_responses.validate_identity(request_sha256=request_sha256,
                        model_id=self._model.model_id, adapter_id=self._model.adapter_id,
                        prompt_version=request.prompt_version)
                except PaidResponseError:
                    raise NarrativeBudgetCallError("MODEL_PAID_RESPONSE_BINDING_INVALID",
                        HandlerOutcome.TERMINAL_FAILURE, _ZERO) from None
                recovered = self._recover(context, request, request_sha256)
                if recovered is None:
                    try:
                        self._paid_responses.admit()
                    except Exception:
                        raise NarrativeBudgetCallError("MODEL_PAID_RESPONSE_SPACE_DENIED",
                            HandlerOutcome.TERMINAL_FAILURE, _ZERO) from None
            if recovered is not None:
                from .narrative_run_store import ReservationAdmission
                admission = ReservationAdmission(recovered[0], False, False)
            else:
                admission = self._store.reserve_model_attempt(
                    run_id=self._run_id,
                    job_id=context.job.job_id,
                    attempt_id=attempt.attempt_id,
                    lease_token=attempt.lease_token,
                    runtime_generation=attempt.runtime_generation,
                    request_sha256=request_sha256,
                    model_id=self._model.model_id,
                    prompt_version=request.prompt_version,
                    pricing_version=run.pricing_version,
                    input_tokens_bound=len(body) + 128,
                    max_output_tokens=self._model.max_output_tokens,
                    output_bytes_bound=self._output_bound,
                    now=self._clock(),
                )
        except NarrativeBudgetCallError:
            raise
        except Exception as error:
            # Admission failures occur before HTTP. Only genuine cap exhaustion
            # is a budget denial; binding and storage faults keep safe diagnostics.
            code, outcome = "MODEL_ADMISSION_INVALID", HandlerOutcome.TERMINAL_FAILURE
            if isinstance(error, RunBudgetExceededError):
                code = "MODEL_BUDGET_DENIED"
            elif isinstance(error, (RunConflictError, ReservationConflictError)):
                code = ("MODEL_SELECTION_NOT_FROZEN" if str(error) == "MODEL_SELECTION_NOT_FROZEN"
                        else "MODEL_RUN_BINDING_CONFLICT")
            elif isinstance(error, RunScopeError):
                code = "MODEL_RUN_SCOPE_MISMATCH"
            elif isinstance(error, LeaseLostError):
                code, outcome = "LEASE_LOST", HandlerOutcome.RETRYABLE
            elif isinstance(error, (StoreBusyError, sqlite3.Error, OSError)):
                code, outcome = "MODEL_ADMISSION_UNAVAILABLE", HandlerOutcome.RETRYABLE
            raise NarrativeBudgetCallError(code, outcome, _ZERO) from None
        if not admission.may_send_http and recovered is None:
            raise NarrativeBudgetCallError(
                "MODEL_REQUEST_ALREADY_RESERVED",
                HandlerOutcome.TERMINAL_FAILURE,
                _metrics(admission.record, 0),
            )
        started = time.monotonic()
        try:
            context.checkpoint()
        except Exception:
            if recovered is not None:
                raise NarrativeBudgetCallError("LEASE_LOST", HandlerOutcome.RETRYABLE,
                    _metrics(admission.record, 0)) from None
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
            if recovered is not None:
                _, pin, saved_body = recovered
                response = self._model.replay_response(request, saved_body,
                    http_status=pin.http_status, duration_ms=pin.duration_ms)
            elif self._paid_responses is not None:
                paid_responses = self._paid_responses

                def capture(complete_body, *, http_status, duration_ms):
                    try:
                        pin = paid_responses.put(complete_body,
                            request_sha256=request_sha256, model_id=self._model.model_id,
                            adapter_id=self._model.adapter_id, prompt_version=request.prompt_version,
                            http_status=http_status, duration_ms=duration_ms)
                        self._store.attach_paid_response(run_id=self._run_id, attempt_id=attempt.attempt_id,
                            lease_token=attempt.lease_token, runtime_generation=attempt.runtime_generation,
                            request_sha256=request_sha256, paid_response_json=pin.to_json(), recorded_at=self._clock())
                    except Exception as exc:
                        raise PaidResponseError("paid response persistence failed") from exc
                response = self._model.generate(request, response_sink=capture)
            else:
                response = self._model.generate(request)
        except Exception as error:
            code, outcome = "MODEL_RESPONSE_INVALID", HandlerOutcome.TERMINAL_FAILURE
            usage = None
            http_status = None
            response_stage = provider_code = None
            finish_reason = content_bytes = reasoning_tokens = None
            usage_diagnostic = None
            failed_final = None
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
                failed_final = error.failed_final
                duration_ms = error.duration_ms
                reasoning_tokens, usage_diagnostic = error.reasoning_tokens, error.usage_diagnostic
                if error.input_tokens is not None and error.output_tokens is not None:
                    usage = ModelUsage(error.input_tokens, error.output_tokens)
            elif isinstance(error, ModelOutputTruncatedError):
                code, duration_ms = "MODEL_OUTPUT_TRUNCATED", error.duration_ms
                finish_reason, content_bytes = error.finish_reason, error.content_bytes
                failed_final = error.failed_final
                reasoning_tokens, usage_diagnostic = error.reasoning_tokens, error.usage_diagnostic
                if error.input_tokens is not None and error.output_tokens is not None:
                    usage = ModelUsage(error.input_tokens, error.output_tokens)
            elif isinstance(error, PaidResponseError):
                code = "MODEL_PAID_RESPONSE_UNAVAILABLE"
            elif isinstance(error, ModelResponseError) and str(error) in {
                "MODEL_HTTP_TRANSPORT",
                "MODEL_HTTP_INCOMPLETE",
            }:
                # Keep response-free transport failures distinct from a
                # complete provider response that violates the envelope.
                # Neither is retried here: the provider may have processed
                # the request, so usage remains an unknown held reservation.
                code = str(error)
            elif not isinstance(error, ModelResponseError):
                code = "MODEL_TRANSPORT_FAILED"
            try:
                metrics = self._settle(
                    context, fallback=admission.record, usage=usage,
                    response_sha256=failed_final.final_content_sha256 if failed_final is not None else None,
                    error_code=code, duration_ms=duration_ms, no_output=True,
                    reasoning_tokens=reasoning_tokens, usage_diagnostic=usage_diagnostic,
                    paid_attempt_id=admission.record.attempt_id if self._paid_responses is not None else None,
                )
            except NarrativeBudgetCallError as settlement_error:
                raise replace(settlement_error, failed_final=failed_final,
                    finish_reason=finish_reason, content_bytes=content_bytes) from None
            raise NarrativeBudgetCallError(
                code, outcome, metrics, http_status=http_status,
                response_stage=response_stage, provider_code=provider_code,
                finish_reason=finish_reason, content_bytes=content_bytes, failed_final=failed_final,
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
            reasoning_tokens=response.reasoning_tokens, usage_diagnostic=response.usage_diagnostic,
            paid_attempt_id=admission.record.attempt_id if self._paid_responses is not None else None,
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

    def _recover(self, context, request, request_sha256):
        """Reuse this exact operation's original paid attempt, never resend on a miss."""
        from .narrative_paid_response import PaidResponsePin
        records = self._store.model_attempts_for_job(run_id=self._run_id, job_id=context.job.job_id)
        charged = [record for record in records if not (
            record.usage_status == "known" and record.input_tokens == record.output_tokens == 0
            and record.paid_response_json is None and record.response_sha256 is None)]
        if not charged:
            return None
        record = charged[0]
        paid_responses = self._paid_responses
        if paid_responses is None:
            raise ValueError("paid responses are not configured")
        paid_json = record.paid_response_json
        if not isinstance(paid_json, str):
            raise ValueError("paid response has no pinned bytes")
        try:
            if len(charged) != 1 or record.request_sha256 != request_sha256:
                raise ValueError("paid operation identity differs")
            pin = PaidResponsePin.from_json(paid_json)
            if (pin.request_sha256 != request_sha256 or pin.model_id != self._model.model_id
                    or pin.adapter_id != self._model.adapter_id or pin.prompt_version != request.prompt_version):
                raise ValueError("paid response model binding differs")
            saved_body = paid_responses.read(pin)
            context.checkpoint()
            if record.output_bytes == 0:
                current = context.attempt
                record = self._store.reopen_paid_output(run_id=self._run_id,
                    paid_attempt_id=record.attempt_id, current_attempt_id=current.attempt_id,
                    lease_token=current.lease_token, runtime_generation=current.runtime_generation,
                    request_sha256=request_sha256, verified_response_sha256=pin.body_sha256, now=self._clock())
            return record, pin, saved_body
        except Exception:
            raise NarrativeBudgetCallError("MODEL_PAID_RESPONSE_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE,
                _metrics(record, 0)) from None

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
        reasoning_tokens: int | None = None,
        usage_diagnostic: str | None = None,
        paid_attempt_id: str | None = None,
    ) -> HandlerMetrics:
        try:
            record = self._store.settle_model_usage(
                run_id=self._run_id,
                attempt_id=paid_attempt_id or context.attempt.attempt_id,
                usage=usage,
                response_sha256=response_sha256,
                error_code=error_code,
                settled_at=self._clock(),
            )
            if no_output:
                self._store.settle_output(
                    run_id=self._run_id,
                    attempt_id=paid_attempt_id or context.attempt.attempt_id,
                    output_bytes=0,
                    output_sha256=None,
                    settled_at=self._clock(),
                )
            return _metrics(record, duration_ms, reasoning_tokens=reasoning_tokens,
                            usage_diagnostic=usage_diagnostic)
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
