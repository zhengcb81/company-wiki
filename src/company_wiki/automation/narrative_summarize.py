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
    PROJECTED_SUMMARY_RESULT_SCHEMA,
    SourceRevisionEventPayload,
)
from .narrative_model import (
    ModelCitationError,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    NarrativeModel,
    NarrativeModelRequest,
    NarrativeModelResponse,
    decode_model_draft,
)
from .narrative_http_model import ModelHTTPError
from .narrative_model_caller import NarrativeBudgetCallError, NarrativeModelCaller


@dataclass(frozen=True)
class _SummaryFailure(Exception):
    code: str
    outcome: HandlerOutcome
    detail: str


def _summary_contract_rule(error: NarrativeContractError) -> str:
    """Return only a fixed rule label; never retain a provider key or value."""
    message = str(error)
    exact = {
        "summary draft status is invalid": "DRAFT_STATUS",
        "summary claim type is invalid": "CLAIM_TYPE",
        "summary claim modality is invalid": "CLAIM_MODALITY",
        "summary claim needs_review must be boolean": "CLAIM_REVIEW_TYPE",
        "summary draft source differs from source_ref": "SOURCE_IDENTITY",
        "summary source identity/hash does not match": "SOURCE_IDENTITY",
        "summary subject identity/hash does not match": "SUBJECT_IDENTITY",
        "summary draft subject differs from selection": "SUBJECT_IDENTITY",
        "subject summary status is invalid": "DRAFT_STATUS",
        "summary language must match the selected language": "SOURCE_LANGUAGE",
        "summary draft language differs from result": "SOURCE_LANGUAGE",
        "summary language must match the source language": "SOURCE_LANGUAGE",
        "summary draft must contain at least one claim": "CLAIMS_EMPTY",
        "summary claims must be an array": "CLAIMS_SHAPE",
        "summary claims exceed twenty": "CLAIMS_LIMIT",
        "summary claim text exceeds 280 characters": "CLAIM_TEXT",
        "summary claim evidence IDs exceed the pinned unique set": "EVIDENCE_REFERENCE",
        "summary claim refers to unknown evidence IDs": "EVIDENCE_REFERENCE",
        "every summary claim requires evidence IDs": "EVIDENCE_REFERENCE",
        "non-company evidence cannot support a company statement": "CLAIM_ROLE",
        "analyst-question claims must cite question evidence only": "CLAIM_ROLE",
        "analyst-question claims must preserve question modality": "CLAIM_MODALITY",
        "summary claim IDs are duplicated": "CLAIM_DUPLICATE_ID",
        "summary claim evidence group declaration is invalid": "GROUP_DECLARATION",
        "summary claim evidence group coverage is incomplete": "GROUP_INCOMPLETE",
    }
    if message in exact:
        return exact[message]
    for prefix, rule in (
        ("summary draft unknown fields:", "DRAFT_FIELDS"),
        ("summary draft missing fields:", "DRAFT_FIELDS"),
        ("summary claim unknown fields:", "CLAIM_FIELDS"),
        ("summary claim missing fields:", "CLAIM_FIELDS"),
        ("summary claim text must", "CLAIM_TEXT"),
        ("summary draft source_sha256 must", "SOURCE_HASH_FORMAT"),
        ("subject summary SHA must", "SUBJECT_HASH_FORMAT"),
        ("subject summary draft unknown fields:", "DRAFT_FIELDS"),
        ("subject summary draft missing fields:", "DRAFT_FIELDS"),
    ):
        if message.startswith(prefix):
            return rule
    return "CONTRACT_INVALID"


def _failure(
    code: str,
    outcome: HandlerOutcome,
    detail: str,
    metrics: HandlerMetrics | None = None,
) -> HandlerResult:
    return HandlerResult(
        outcome=outcome,
        result={},
        artifacts=(),
        effects=(),
        metrics=metrics or HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
        error=HandlerError(code=code, detail=detail),
    )


def _success(
    result: NarrativeSummaryResult, metrics: HandlerMetrics | None = None
) -> HandlerResult:
    return HandlerResult(
        outcome=HandlerOutcome.SUCCEEDED,
        result=result.to_dict(),
        artifacts=(),
        effects=(),
        metrics=metrics or HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
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
        selected.subject.to_dict() != payload.subject.to_dict()
        or selected.source_metadata.to_dict() != payload.source_metadata.to_dict()
        or selected.expected_read_policy_sha256 != payload.expected_read_policy_sha256
    ):
        raise _SummaryFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "select dependency identity differs from the source event",
        )


def _summary_identity_wire(selected: NarrativeSelectResult) -> dict[str, Any]:
    if selected.subject.kind == "official_json":
        return {"schema_version": PROJECTED_SUMMARY_RESULT_SCHEMA,
                "subject_binding": selected.subject.to_dict()}
    return {"schema_version": SUMMARY_RESULT_SCHEMA, "source_ref": selected.source_ref.to_dict()}


class NarrativeSummarizeHandler:
    """Build a same-language source summary from selected evidence only."""

    def __init__(
        self,
        *,
        model: NarrativeModel | None,
        model_caller: NarrativeModelCaller | None = None,
    ) -> None:
        self._model = model
        self._model_caller = model_caller

    def __call__(self, context: JobExecutionContext) -> HandlerResult:
        try:
            return self._execute(context)
        except _SummaryFailure as exc:
            return _failure(exc.code, exc.outcome, exc.detail)
        except NarrativeBudgetCallError as exc:
            status = (
                "" if exc.http_status is None else f" (http_status={exc.http_status})"
            )
            if exc.response_stage is not None:
                status += f" (response_stage={exc.response_stage})"
            if exc.provider_code is not None:
                status += f" (provider_code={exc.provider_code})"
            if exc.finish_reason is not None:
                status += f" (finish_reason={exc.finish_reason})"
            if exc.content_bytes is not None:
                status += f" (content_bytes={exc.content_bytes})"
            return _failure(
                exc.code,
                exc.outcome,
                "metered model attempt did not complete" + status,
                exc.metrics,
            )
        except ModelHTTPError as exc:
            return _failure(
                exc.error_code,
                HandlerOutcome.RETRYABLE
                if exc.retryable
                else HandlerOutcome.TERMINAL_FAILURE,
                f"model request failed an HTTP status check (http_status={exc.status_code})",
            )
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
        if not selected.evidence_spans or selected.source_metadata.language not in {"zh", "en", "mixed"}:
            raise _SummaryFailure(
                "SUMMARY_INPUT_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE,
                "selected evidence or original language is unavailable",
            )
        if self._model is None and self._model_caller is None:
            raise _SummaryFailure(
                "MODEL_NOT_CONFIGURED",
                HandlerOutcome.TERMINAL_FAILURE,
                "narrative model is not configured",
            )
        review = selected.prompt_review
        request = NarrativeModelRequest.from_selection(selected)
        context.checkpoint()
        if self._model_caller is not None:
            response, metrics = self._model_caller.generate(context, request)
        else:
            assert self._model is not None
            response = self._model.generate(request)
            metrics = HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0)
        context.checkpoint()
        try:
            completed = self._completed_result(selected, review, response)
        except _SummaryFailure as exc:
            return _failure(exc.code, exc.outcome, exc.detail, metrics)
        except ModelResponseError:
            return _failure(
                "MODEL_RESPONSE_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "model response violates its transport contract",
                metrics,
            )
        return _success(completed, metrics)

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
            **_summary_identity_wire(selected),
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
        try:
            draft = decode_model_draft(response, selected=selected)
        except ModelCitationError as exc:
            raise _SummaryFailure("SUMMARY_INVALID", HandlerOutcome.TERMINAL_FAILURE,
                                  "model draft cites evidence outside its selection") from exc
        except PhysicalPathLeakError as exc:
            raise ModelResponseError("model response contains a physical path") from exc
        except NarrativeContractError as exc:
            raise _SummaryFailure(
                "SUMMARY_INVALID", HandlerOutcome.TERMINAL_FAILURE,
                "model draft violates the summary contract "
                f"(rule={_summary_contract_rule(exc)})",
            ) from exc
        raw: Mapping[str, Any] = {
            **_summary_identity_wire(selected),
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
                "model draft violates the summary contract "
                f"(rule={_summary_contract_rule(exc)})",
            ) from exc


__all__ = ["NarrativeSummarizeHandler"]
