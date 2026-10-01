"""Selected-evidence-only summarize handler for the narrative DAG."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


from .execution_context import JobExecutionContext
from .models import HandlerError, HandlerMetrics, HandlerOutcome, HandlerResult
from .narrative_contracts import (
    ContractSizeError,
    NarrativeContractError,
    NarrativeSelectResult,
    NarrativeSummaryResult,
    PhysicalPathLeakError,
    PromptReviewValue,
    SUMMARY_RESULT_SCHEMA,
    SourceRevisionEventPayload,
)
from .narrative_model import (
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    NarrativeModel,
    NarrativeModelRequest,
    NarrativeModelResponse,
    decode_model_draft,
)


@dataclass(frozen=True)
class _SummaryFailure(Exception):
    code: str
    outcome: HandlerOutcome
    detail: str


def _failure(code: str, outcome: HandlerOutcome, detail: str) -> HandlerResult:
    return HandlerResult(
        outcome=outcome,
        result={},
        artifacts=(),
        effects=(),
        metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
        error=HandlerError(code=code, detail=detail),
    )


def _success(result: NarrativeSummaryResult) -> HandlerResult:
    return HandlerResult(
        outcome=HandlerOutcome.SUCCEEDED,
        result=result.to_dict(),
        artifacts=(),
        effects=(),
        metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
        error=None,
    )


def _dependency_result(context: JobExecutionContext) -> NarrativeSelectResult:
    dependency = context.dependency_results.get("source.narrative_select")
    if (
        len(context.dependency_results) != 1
        or dependency is None
        or dependency.outcome is not HandlerOutcome.SUCCEEDED
        or dependency.error is not None
        or dependency.effects
    ):
        raise _SummaryFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "select dependency is missing or unsuccessful",
        )
    try:
        return NarrativeSelectResult.from_dict(dependency.result)
    except NarrativeContractError as exc:
        raise _SummaryFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "select dependency violates its strict contract",
        ) from exc


def _validate_dependency_identity(
    payload: SourceRevisionEventPayload,
    selected: NarrativeSelectResult,
) -> None:
    if (
        selected.source_ref.to_dict() != payload.source_ref.to_dict()
        or selected.source_metadata.to_dict() != payload.source_metadata.to_dict()
        or selected.expected_read_policy_sha256
        != payload.expected_read_policy_sha256
    ):
        raise _SummaryFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "select dependency identity differs from the source event",
        )


class NarrativeSummarizeHandler:
    """Build a same-language source summary from selected evidence only."""

    def __init__(
        self,
        *,
        model: NarrativeModel | None,
    ) -> None:
        self._model = model

    def __call__(self, context: JobExecutionContext) -> HandlerResult:
        try:
            return self._execute(context)
        except _SummaryFailure as exc:
            return _failure(exc.code, exc.outcome, exc.detail)
        except ModelTimeoutError:
            return _failure(
                "MODEL_TIMEOUT", HandlerOutcome.RETRYABLE, "model request timed out"
            )
        except ModelRateLimitError:
            return _failure(
                "MODEL_RATE_LIMIT",
                HandlerOutcome.RETRYABLE,
                "model request was rate limited",
            )
        except ModelResponseError:
            return _failure(
                "MODEL_RESPONSE_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "model response violates its transport contract",
            )

    def _execute(self, context: JobExecutionContext) -> HandlerResult:
        context.checkpoint()
        payload = self._payload(context)
        selected = _dependency_result(context)
        _validate_dependency_identity(payload, selected)
        if selected.selection.status == "skipped_no_narrative":
            return _success(self._skip_result(selected))
        if self._model is None:
            raise _SummaryFailure(
                "MODEL_NOT_CONFIGURED",
                HandlerOutcome.TERMINAL_FAILURE,
                "narrative model is not configured",
            )
        review = selected.prompt_review
        request = NarrativeModelRequest.from_selection(selected)
        context.checkpoint()
        response = self._model.generate(request)
        context.checkpoint()
        return _success(self._completed_result(selected, review, response))

    @staticmethod
    def _payload(context: JobExecutionContext) -> SourceRevisionEventPayload:
        if (
            context.job.job_type != "source.narrative_summarize"
            or context.source_revision is None
        ):
            raise _SummaryFailure(
                "INPUT_SCHEMA_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "summarize context identity is invalid",
            )
        return context.source_revision

    def _current_review(self, selected: NarrativeSelectResult) -> PromptReviewValue:
        """Return optional quality metadata; it is not permission to call a model."""
        selected.prompt_review.validate_source(selected.source_ref)
        return selected.prompt_review

    @staticmethod
    def _skip_result(selected: NarrativeSelectResult) -> NarrativeSummaryResult:
        raw = {
            "schema_version": SUMMARY_RESULT_SCHEMA,
            "source_ref": selected.source_ref.to_dict(),
            "language": selected.source_metadata.language,
            "translate": False,
            "status": "summary_not_needed",
            "draft": None,
            "model": None,
            "prompt_review": selected.prompt_review.to_dict(),
        }
        try:
            result = NarrativeSummaryResult.from_dict(raw)
            result.validate_against(selected)
            return result
        except NarrativeContractError as exc:
            raise _SummaryFailure(
                "SUMMARY_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "skip summary violates its strict contract",
            ) from exc

    @staticmethod
    def _completed_result(
        selected: NarrativeSelectResult,
        review: PromptReviewValue,
        response: NarrativeModelResponse,
    ) -> NarrativeSummaryResult:
        draft = decode_model_draft(response)
        raw: Mapping[str, Any] = {
            "schema_version": SUMMARY_RESULT_SCHEMA,
            "source_ref": selected.source_ref.to_dict(),
            "language": selected.source_metadata.language,
            "translate": False,
            "status": "completed",
            "draft": draft,
            "model": {
                "adapter_id": response.adapter_id,
                "model_id": response.model_id,
                "prompt_version": response.prompt_version,
                "response_sha256": response.response_sha256,
            },
            "prompt_review": review.to_dict(),
        }
        try:
            result = NarrativeSummaryResult.from_dict(raw)
            result.validate_against(selected)
            return result
        except ContractSizeError as exc:
            raise _SummaryFailure(
                "RESULT_TOO_LARGE",
                HandlerOutcome.TERMINAL_FAILURE,
                "summary result exceeds its byte budget",
            ) from exc
        except PhysicalPathLeakError as exc:
            raise ModelResponseError("model response contains a physical path") from exc
        except NarrativeContractError as exc:
            raise _SummaryFailure(
                "SUMMARY_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "model draft violates the summary contract",
            ) from exc


__all__ = ["NarrativeSummarizeHandler"]
