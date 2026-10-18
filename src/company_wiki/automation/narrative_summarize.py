"""Selected-evidence-only summarize handler for the narrative DAG."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from importlib.metadata import PackageNotFoundError, version
import logging
from pathlib import Path
from typing import Any
from company_wiki.narrative_subject import NarrativeSubject


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
    FailedFinalDiagnostic,
    ModelCitationError,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    NarrativeModel,
    NarrativeModelResponse,
)
from .narrative_model_runtime import build_model_request, decode_model_draft, resolve_model_boundary
from .narrative_http_model import ModelHTTPError
from .narrative_failed_final import fit_failed_final_result
from .narrative_model_caller import NarrativeBudgetCallError, NarrativeModelCaller


def reading_summary_validation_identity() -> dict[str, Any]:
    """Freeze this summary boundary separately from the model's JSON decoder.

    Source-owned boundaries consume the observer. Old None/v1 retain their exact
    identity and wire. Paths and line endings are installation details.
    """
    from . import narrative_output_language as observer

    try:
        detector = "py3langid/" + version("py3langid")
    except PackageNotFoundError:
        detector = "py3langid/unavailable"
    return {
        "schema_version": "narrative-summary-validation/2",
        "summary_handler_sha256": hashlib.sha256(
            Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "observer_sha256": hashlib.sha256(
            Path(observer.__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "detector_distribution": detector,
        "language_observer": observer.language_observer_identity(),
    }


def _observe_output_language(
    result: NarrativeSummaryResult, selected: NarrativeSelectResult,
) -> NarrativeSummaryResult:
    """Observe canonical claims against their own citations, without translating."""
    from .narrative_output_language import observe_summary_language

    assert result.draft is not None
    observation = observe_summary_language(result.draft.claims,
        evidence_spans=selected.evidence_spans)
    if observation.state == "different":
        raise _SummaryFailure("SUMMARY_INVALID", HandlerOutcome.TERMINAL_FAILURE,
            "model prose differs from its cited original language (rule=OUTPUT_LANGUAGE)")
    if observation.state in {"uncertain", "unavailable"}:
        # Existing quality metadata remains consumable without any human permit.
        # Never log excerpts or presume English when an observer abstains.
        logging.getLogger(__name__).warning(
            "SUMMARY_LANGUAGE_UNCERTAIN" if observation.state == "uncertain"
            else "SUMMARY_LANGUAGE_UNAVAILABLE")
        wire = result.to_dict()
        wire["draft"]["status"] = "needs_review"
        for claim in wire["draft"]["claims"]:
            claim["needs_review"] = True
        result = NarrativeSummaryResult.from_dict(wire)
        result.validate_against(selected)
    return result


@dataclass(frozen=True)
class _SummaryFailure(Exception):
    code: str
    outcome: HandlerOutcome
    detail: str


def _summary_contract_rule(error: NarrativeContractError) -> str:
    """Return only a fixed rule label; never retain a provider key or value."""
    try:
        message = str(error)
    except Exception:
        return "CONTRACT_INVALID"
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
        "summary claims exceed forty": "CLAIMS_LIMIT",
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


def _model_response_rule(error: ModelResponseError) -> str:
    """Name a known validation rule without retaining exception/provider text."""
    if isinstance(error.__cause__, UnicodeDecodeError):
        return "FINAL_UTF8"
    try:
        message = str(error)
    except Exception:
        return "MODEL_RESPONSE_CONTRACT"
    return {
        "model response is not strict UTF-8 JSON": "FINAL_JSON",
        "model response contains duplicate JSON keys": "JSON_DUPLICATE_KEYS",
        "model response contains a non-JSON numeric literal": "JSON_NUMBER",
        "model response must contain a draft": "RESPONSE_SHAPE",
        "model response prompt version differs from request": "PROMPT_IDENTITY",
        "model response contradicts the untranslated source contract": "TRANSLATION",
        "model response contains a physical path": "PHYSICAL_PATH",
    }.get(message, "MODEL_RESPONSE_CONTRACT")


def _post_model_failure(
    response: NarrativeModelResponse, metrics: HandlerMetrics,
    code: str, outcome: HandlerOutcome, detail: str,
) -> HandlerResult:
    """Observe only returned final bytes; optional diagnostics cannot hide usage."""
    diagnostic = None
    try:
        diagnostic = FailedFinalDiagnostic.from_observation(
            provider_body=None, content=response.response_bytes.decode("utf-8"))
    except Exception:
        # Invalid UTF-8 and optional observation failures keep the original
        # failure and native metrics, without replacement text or invented wire.
        pass
    return _failure(code, outcome, detail, metrics, failed_final=diagnostic)


def _failure(
    code: str,
    outcome: HandlerOutcome,
    detail: str,
    metrics: HandlerMetrics | None = None,
    *, failed_final: FailedFinalDiagnostic | None = None,
) -> HandlerResult:
    base = HandlerResult(
        outcome=outcome,
        result={},
        artifacts=(),
        effects=(),
        metrics=metrics or HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
        error=HandlerError(code=code, detail=detail),
    )
    if failed_final is not None:
        try:
            return fit_failed_final_result(base, failed_final)
        except Exception:
            # Optional diagnostic failure cannot hide the primary error/usage.
            pass
    return base


def _success(
    result: NarrativeSummaryResult, metrics: HandlerMetrics | None = None,
    *, execution: Mapping[str, Any] | None = None,
) -> HandlerResult:
    wire = result.to_dict()
    if execution is not None:
        from .narrative_summary_execution import wrap_summary
        wire = wrap_summary(result, execution)
    return HandlerResult(
        outcome=HandlerOutcome.SUCCEEDED,
        result=wire,
        artifacts=(),
        effects=(),
        metrics=metrics or HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
        error=None,
    )




def _uncovered_task_keys(request: Any, summary: NarrativeSummaryResult) -> list[str]:
    """Visible scoped tasks with no claim in this summary, in request order."""
    from .narrative_model_scoped import SCOPED_PROMPT_VERSION
   
    if getattr(request, "prompt_version", None) != SCOPED_PROMPT_VERSION:
        return []
    try:
        data = json.loads(request.data_json)
        tasks = data["material"]["tasks"]
    except (KeyError, TypeError, ValueError):
        return []
    keys = [row["key"] for row in tasks if isinstance(row, dict) and isinstance(row.get("key"), str)]
    draft = summary.draft
    if draft is None:
        return keys
    covered = {str(claim.claim_id).split("-", 1)[0] for claim in draft.claims}
    return [key for key in keys if key not in covered]


def _partial_summary_result(
    summary: NarrativeSummaryResult, metrics: HandlerMetrics, keys: list[str],
    execution: Mapping[str, Any],
) -> HandlerResult:
    """Keep the first-pass summary and ask the worker for its repair attempt."""
    return HandlerResult(
        outcome=HandlerOutcome.RETRYABLE,
        result={"coverage_partial": True, "summary": summary.to_dict(),
                "uncovered_task_keys": keys, "execution": dict(execution)},
        artifacts=(),
        effects=(),
        metrics=metrics,
        error=HandlerError("SUMMARY_COVERAGE_PARTIAL",
                           "partial summary waits for its repair attempt"),
    )


def _merge_repair_summary(
    prior: NarrativeSummaryResult, repair: NarrativeSummaryResult,
) -> NarrativeSummaryResult:
    """Merge a repair draft into the first-pass summary with unique claim ids."""
    wire = prior.to_dict()
    draft = wire["draft"]
    claims = list(draft.get("claims", []))
    seen = {str(claim.get("claim_id")) for claim in claims}
    repair_wire = repair.to_dict()
    for index, claim in enumerate(repair_wire["draft"]["claims"], 1):
        key = str(claim["claim_id"]).split("-", 1)[0]
        claim_id = f"{key}-r{index}"
        while claim_id in seen:
            claim_id += "x"
        claim["claim_id"] = claim_id
        seen.add(claim_id)
        claims.append(claim)
    draft["claims"] = claims
    draft["status"] = "needs_review"
    wire["model"] = repair_wire.get("model")
    return NarrativeSummaryResult.from_dict(wire)

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
        reading_model_projection: Callable[[NarrativeSubject], str | None] | None = None,
        validate_model_execution: Callable[[NarrativeSubject], None] | None = None,
    ) -> None:
        self._model = model
        self._model_caller = model_caller
        self._reading_model_projection = reading_model_projection
        self._validate_model_execution = validate_model_execution

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
                exc.metrics, failed_final=exc.failed_final,
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
        reading_projection_version = (
            self._reading_model_projection(selected.subject)
            if self._reading_model_projection is not None else None
        )
        if self._validate_model_execution is not None:
            try:
                self._validate_model_execution(selected.subject)
            except ModelResponseError as exc:
                raise _SummaryFailure("MODEL_GENERATION_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE,
                                      str(exc)) from exc
        prior_summary: NarrativeSummaryResult | None = None
        uncovered: list[str] = []
        prior_result = context.prior_partial_result
        if (prior_result is not None and isinstance(prior_result.result, Mapping)
                and prior_result.result.get("coverage_partial") is True
                and isinstance(prior_result.result.get("summary"), Mapping)):
            try:
                prior_summary = NarrativeSummaryResult.from_dict(prior_result.result["summary"])
            except NarrativeContractError:
                prior_summary = None
            if prior_summary is not None:
                uncovered = [key for key in prior_result.result.get("uncovered_task_keys", ())
                             if isinstance(key, str)]
        if prior_summary is not None and not uncovered:
            return _success(prior_summary)
        try:
            if prior_summary is not None:
                from .narrative_model_scoped import MAX_SUMMARY_CLAIMS
                prior_draft = prior_summary.draft
                if prior_draft is None:
                    return _success(prior_summary)
                remaining = MAX_SUMMARY_CLAIMS - len(prior_draft.claims)
                if remaining <= 0:
                    return _success(prior_summary)
                request = build_model_request(selected,
                    reading_projection_version=reading_projection_version,
                    only_tasks=frozenset(uncovered),
                    target_claims=min(len(uncovered), remaining))
            else:
                request = build_model_request(selected,
                    reading_projection_version=reading_projection_version)
        except NarrativeContractError as exc:
            raise _SummaryFailure('SUMMARY_PLAN_INVALID', HandlerOutcome.TERMINAL_FAILURE,
                                  'source summary plan exceeds or violates its bounded contract') from exc
        context.checkpoint()
        if self._model_caller is not None:
            try:
                response, metrics = self._model_caller.generate(context, request)
            except NarrativeBudgetCallError as exc:
                if prior_summary is None:
                    raise
                # A repair call is best effort: never lose the first summary.
                return _success(prior_summary, exc.metrics)
        else:
            assert self._model is not None
            response = self._model.generate(request)
            metrics = HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0)
        context.checkpoint()
        execution: dict[str, Any] = {}
        try:
            completed = self._completed_result(selected, review, response,
                reading_projection_version=reading_projection_version,
                execution_report=execution)
        except _SummaryFailure as exc:
            if prior_summary is not None:
                return _success(prior_summary, metrics)
            return _post_model_failure(response, metrics, exc.code, exc.outcome, exc.detail)
        except ModelResponseError as exc:
            if prior_summary is not None:
                return _success(prior_summary, metrics)
            return _post_model_failure(
                response, metrics,
                "MODEL_RESPONSE_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "model response violates its transport contract "
                f"(rule={_model_response_rule(exc)})",
            )
        except UnicodeError:
            if prior_summary is not None:
                return _success(prior_summary, metrics)
            return _post_model_failure(
                response, metrics,
                "MODEL_RESPONSE_INVALID", HandlerOutcome.TERMINAL_FAILURE,
                "model response cannot form a UTF-8 summary (rule=FINAL_UTF8)",
            )
        if prior_summary is not None:
            try:
                merged = _merge_repair_summary(prior_summary, completed)
                merged.validate_against(selected)
                merged = _observe_output_language(merged, selected)
            except (_SummaryFailure, NarrativeContractError):
                return _success(prior_summary, metrics)
            return _success(merged, metrics)
        uncovered_keys = _uncovered_task_keys(request, completed)
        if (uncovered_keys
                and context.attempt.attempt_no < context.job.max_attempts
                and os.environ.get("CW_SUMMARY_COVERAGE_REPAIR") == "1"):
            return _partial_summary_result(completed, metrics, uncovered_keys, execution)
        return _success(completed, metrics, execution=execution or None)

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
        *, reading_projection_version: str | None = None,
        execution_report: dict[str, Any] | None = None,
    ) -> NarrativeSummaryResult:
        try:
            from .narrative_model_extractive import (
                EXTRACTIVE_MODEL_PROJECTION_VERSION, decode_extractive_result,
            )
            if reading_projection_version == EXTRACTIVE_MODEL_PROJECTION_VERSION:
                decoded = decode_extractive_result(response, selected=selected)
                draft = decoded.draft
                if execution_report is not None:
                    execution_report.update(decoded.execution)
            else:
                draft = decode_model_draft(response, selected=selected,
                    reading_projection_version=reading_projection_version)
        except ModelCitationError as exc:
            raise _SummaryFailure("SUMMARY_INVALID", HandlerOutcome.TERMINAL_FAILURE,
                                  "model draft cites evidence outside its selection "
                                  "(rule=EVIDENCE_REFERENCE)") from exc
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
            if resolve_model_boundary(
                reading_projection_version, projected=selected.subject.kind == "official_json",
            ).source_owned:
                result = _observe_output_language(result, selected)
            return result
        except ContractSizeError as exc:
            raise _SummaryFailure(
                "RESULT_TOO_LARGE",
                HandlerOutcome.TERMINAL_FAILURE,
                "summary result exceeds its byte budget (rule=RESULT_SIZE)",
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
