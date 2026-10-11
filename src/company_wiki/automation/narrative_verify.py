"""Replay and bundle handler for selected narrative evidence."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
from typing import Any

from company_wiki.narrative_subject import NarrativeSubject, publication_target
from company_wiki.source_catalog.narrative_language import NarrativeLanguageError
from company_wiki.source_catalog.official_json_projection import ProjectionError

from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_SELECTOR_NAME,
    resolve_narrative_selector_version,
)
from company_wiki.source_catalog.source_reader import SourceReadError
from company_wiki.source_catalog.transcript_text_extract import (
    TranscriptMaterialError,
)

from .execution_context import JobExecutionContext
from .models import (
    Effect,
    EffectStatus,
    HandlerError,
    HandlerMetrics,
    HandlerOutcome,
    HandlerResult,
    canonical_json_hash,
    make_effect_key,
)
from .narrative_formats import parser_component
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from .narrative_contracts import (
    BUNDLE_SCHEMA,
    PROJECTED_BUNDLE_SCHEMA,
    ContractSizeError,
    NarrativeBundle,
    NarrativeContractError,
    NarrativeSelectResult,
    NarrativeSummaryResult,
    PhysicalPathLeakError,
    PromptReviewValue,
    SourceRevisionEventPayload,
)
from .narrative_model import NARRATIVE_PROMPT_VERSION, PROJECTION_NARRATIVE_PROMPT_VERSION
from .narrative_official_json import OfficialProjectionAdapterError, open_verified_projection
from .narrative_replay import (
    NarrativeReplayError,
    PdfEvidenceReplayer,
    replay_narrative_evidence,
    replay_verified_projection,
)
from .narrative_source_guard import (
    NarrativeSourceGuardError,
    NarrativeSourceReader,
    source_ref,
    validate_opened_identity,
    validate_source_metadata,
)


BUNDLE_PRODUCER_VERSION = "1.0.0"
EFFECT_TYPE = "narrative_bundle.publish"


@dataclass(frozen=True)
class _VerifyFailure(Exception):
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


def _read_error_result(error: SourceReadError) -> HandlerResult:
    if error.reason == "catalog_unavailable":
        return _failure("IO_TRANSIENT", HandlerOutcome.RETRYABLE, error.reason)
    if error.reason in {
        "read_policy_mismatch",
        "invalid_read_policy_pin",
        "remediation_pending",
        "root_admission_denied",
        "source_not_active",
    }:
        return _failure("POLICY_DENIED", HandlerOutcome.TERMINAL_FAILURE, error.reason)
    if error.reason in {"expected_version_mismatch", "source_ref_changed"}:
        return _failure(
            "SOURCE_HASH_MISMATCH", HandlerOutcome.TERMINAL_FAILURE, error.reason
        )
    return _failure("SOURCE_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE, error.reason)


def _dependencies(
    context: JobExecutionContext,
) -> tuple[NarrativeSelectResult, NarrativeSummaryResult]:
    selected_raw = context.dependency_results.get("source.narrative_select")
    summary_raw = context.dependency_results.get("source.narrative_summarize")
    values = (selected_raw, summary_raw)
    if len(context.dependency_results) != 2 or any(value is None for value in values):
        raise _VerifyFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "verify requires select and summarize dependencies",
        )
    assert selected_raw is not None and summary_raw is not None
    if any(
        value.outcome is not HandlerOutcome.SUCCEEDED
        or value.error is not None
        or value.effects
        for value in (selected_raw, summary_raw)
    ):
        raise _VerifyFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "verify dependency is unsuccessful or effectful",
        )
    try:
        selected = NarrativeSelectResult.from_dict(selected_raw.result)
        summary = NarrativeSummaryResult.from_dict(summary_raw.result)
        summary.validate_against(selected)
    except NarrativeContractError as exc:
        raise _VerifyFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "verify dependency violates its strict contract",
        ) from exc
    return selected, summary


def _validate_dependency_identity(
    payload: SourceRevisionEventPayload,
    selected: NarrativeSelectResult,
    summary: NarrativeSummaryResult,
    normalization=None,
    *, selector_version: str,
) -> None:
    if (
        selected.subject != payload.subject
        or selected.source_metadata.to_dict() != payload.source_metadata.to_dict()
        or selected.expected_read_policy_sha256 != payload.expected_read_policy_sha256
        or summary.subject != selected.subject
    ):
        raise _VerifyFailure(
            "DEPENDENCY_INVALID", HandlerOutcome.TERMINAL_FAILURE,
            "dependency identity differs from the source event",
        )
    projected = selected.subject.kind == "official_json"
    parser_current = True
    if not projected:
        parser_name, parser_version = parser_component(
            selected.source_ref.mime_type, selected.source_metadata.source_class,
            normalization=normalization, parser_version=selected.parser.version,
        )
        parser_current = selected.parser.name == parser_name and selected.parser.version == parser_version
    active_prompt = PROJECTION_NARRATIVE_PROMPT_VERSION if projected else NARRATIVE_PROMPT_VERSION
    if (
        not parser_current
        or selected.selector.name != NARRATIVE_SELECTOR_NAME
        or selected.selector.version != selector_version
        or (summary.model is not None and summary.model.prompt_version != active_prompt)
    ):
        raise _VerifyFailure(
            "DEPENDENCY_INVALID", HandlerOutcome.TERMINAL_FAILURE,
            "dependency component version is not the active version",
        )


class NarrativeVerifyHandler:
    """Replay all locators and emit one logical publication effect."""

    def __init__(
        self,
        *,
        reader: NarrativeSourceReader,
        pdf_replayer: PdfEvidenceReplayer | None = None,
        normalization: NarrativeNormalization | None = None,
        projection_catalog: Any | None = None,
        generation_sha256: Callable[[NarrativeSubject], str] | None = None,
        selector_version: str | None = None,
    ) -> None:
        self._selector_version = resolve_narrative_selector_version(selector_version)
        self._reader = reader
        self._pdf_replayer = pdf_replayer
        self._normalization = normalization or NarrativeNormalization()
        self._projection_catalog = projection_catalog
        self._generation_sha256 = generation_sha256

    def __call__(self, context: JobExecutionContext) -> HandlerResult:
        try:
            return self._execute(context)
        except SourceReadError as exc:
            return _read_error_result(exc)
        except ProjectionError as exc:
            return _failure(
                "SOURCE_UNAVAILABLE" if exc.code == "projection_not_found" else "LOCATOR_REPLAY_FAILED",
                HandlerOutcome.TERMINAL_FAILURE, exc.code,
            )
        except OfficialProjectionAdapterError as exc:
            return _failure(
                "SOURCE_HASH_MISMATCH" if str(exc) == "projection_hash_mismatch" else "LOCATOR_REPLAY_FAILED",
                HandlerOutcome.TERMINAL_FAILURE, str(exc),
            )
        except NarrativeLanguageError as exc:
            return _failure(exc.code, HandlerOutcome.TERMINAL_FAILURE, str(exc))
        except NarrativeSourceGuardError as exc:
            return _failure(exc.code, HandlerOutcome.TERMINAL_FAILURE, exc.detail)
        except _VerifyFailure as exc:
            return _failure(exc.code, exc.outcome, exc.detail)
        except TranscriptMaterialError:
            return _failure(
                "LOCATOR_REPLAY_FAILED",
                HandlerOutcome.TERMINAL_FAILURE,
                "transcript material cannot be replayed",
            )

    def _execute(self, context: JobExecutionContext) -> HandlerResult:
        context.checkpoint()
        payload = self._payload(context)
        selected, summary = _dependencies(context)
        _validate_dependency_identity(payload, selected, summary, self._normalization,
            selector_version=self._selector_version)
        if payload.subject.kind == "official_json":
            return self._execute_projection(context, payload, selected, summary)
        ref = source_ref(payload)
        opened = self._reader.open_version(
            ref,
            purpose="narrative_derivation",
            expected_read_policy_sha256=payload.expected_read_policy_sha256,
        )
        validate_opened_identity(payload, opened)
        validate_source_metadata(payload, self._reader.describe_version(ref))
        review = self._current_review(selected, summary)
        context.checkpoint()
        self._replay(opened.data, selected)
        bundle = self._bundle(selected, summary, review)
        context.checkpoint()
        effect = self._effect(context, bundle)
        return HandlerResult(
            outcome=HandlerOutcome.SUCCEEDED,
            result=bundle.to_dict(),
            artifacts=(),
            effects=(effect,),
            metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
            error=None,
        )

    def _execute_projection(
        self, context: JobExecutionContext, payload: SourceRevisionEventPayload,
        selected: NarrativeSelectResult, summary: NarrativeSummaryResult,
    ) -> HandlerResult:
        if self._projection_catalog is None:
            raise _VerifyFailure(
                "SOURCE_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE,
                "official projection source port is not configured",
            )
        view = open_verified_projection(
            self._projection_catalog, projection_id=payload.subject.item_key,
            expected_projection_sha256=payload.subject.subject_sha256,
        )
        if view.subject != selected.subject:
            raise _VerifyFailure(
                "DEPENDENCY_INVALID", HandlerOutcome.TERMINAL_FAILURE,
                "dependency subject differs from the verified projection",
            )
        if any((span.parser_name, span.parser_version) != (selected.parser.name, selected.parser.version)
               for span in view.evidence_spans):
            raise _VerifyFailure(
                "DEPENDENCY_INVALID", HandlerOutcome.TERMINAL_FAILURE,
                "dependency parser differs from the real official source producer",
            )
        review = self._current_review(selected, summary)
        context.checkpoint()
        try:
            replay_verified_projection(view, selected)
        except NarrativeReplayError as exc:
            raise _VerifyFailure(
                "LOCATOR_REPLAY_FAILED", HandlerOutcome.TERMINAL_FAILURE,
                "selected official fields differ from the verified source view",
            ) from exc
        bundle = self._bundle(selected, summary, review)
        generation = self._projection_generation(selected.subject)
        context.checkpoint()
        effect = self._effect(context, bundle, generation_sha256=generation)
        return HandlerResult(
            outcome=HandlerOutcome.SUCCEEDED, result=bundle.to_dict(), artifacts=(), effects=(effect,),
            metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0), error=None,
        )

    def _projection_generation(self, subject: NarrativeSubject) -> str:
        try:
            if self._generation_sha256 is None:
                raise ValueError("missing generation resolver")
            generation = self._generation_sha256(subject)
            if not isinstance(generation, str) or re.fullmatch(r"[0-9a-f]{64}", generation) is None:
                raise ValueError("invalid generation SHA")
            return generation
        except (KeyError, TypeError, ValueError) as exc:
            raise _VerifyFailure(
                "DEPENDENCY_INVALID", HandlerOutcome.TERMINAL_FAILURE,
                "official projection has no exact frozen generation SHA",
            ) from exc

    @staticmethod
    def _payload(context: JobExecutionContext) -> SourceRevisionEventPayload:
        if (
            context.job.job_type != "source.narrative_verify"
            or context.source_revision is None
        ):
            raise _VerifyFailure(
                "INPUT_SCHEMA_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "verify context identity is invalid",
            )
        return context.source_revision

    @staticmethod
    def _current_review(
        selected: NarrativeSelectResult,
        summary: NarrativeSummaryResult,
    ) -> PromptReviewValue:
        # Prompt review is descriptive metadata; source identity and locator replay
        # provide the automatic acceptance checks for a bundle.
        selected.prompt_review.validate_source(selected.source_ref)
        if summary.prompt_review != selected.prompt_review:
            raise _VerifyFailure(
                "DEPENDENCY_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "summary review metadata differs from selection",
            )
        return selected.prompt_review

    def _replay(self, data: bytes, selected: NarrativeSelectResult) -> None:
        try:
            replay_narrative_evidence(data, selected, pdf_replayer=self._pdf_replayer, normalization=self._normalization)
        except NarrativeReplayError as exc:
            raise _VerifyFailure(
                "LOCATOR_REPLAY_FAILED",
                HandlerOutcome.TERMINAL_FAILURE,
                "selected evidence replay could not complete",
            ) from exc

    @staticmethod
    def _bundle(
        selected: NarrativeSelectResult,
        summary: NarrativeSummaryResult,
        review: PromptReviewValue,
    ) -> NarrativeBundle:
        summary_raw = summary.to_dict()
        quality = (
            "skipped_no_narrative"
            if summary.status == "summary_not_needed"
            else (
                "needs_review"
                if summary.draft is not None and summary.draft.status == "needs_review"
                else "verified"
            )
        )
        raw = {
            "schema_version": BUNDLE_SCHEMA,
            "source_ref": selected.source_ref.to_dict(),
            "expected_read_policy_sha256": selected.expected_read_policy_sha256,
            "source_metadata": selected.source_metadata.to_dict(),
            "quality_status": quality,
            "selection": selected.selection.to_dict(),
            "evidence_spans": [span.to_dict() for span in selected.evidence_spans],
            "summary": {
                "status": summary_raw["status"],
                "translate": summary_raw["translate"],
                "draft": summary_raw["draft"],
                "model": summary_raw["model"],
            },
            "prompt_review": review.to_dict(),
            "transcript_lineage": (
                selected.transcript_lineage.to_dict()
                if selected.transcript_lineage is not None
                else None
            ),
            "transcript_byte_bindings": [
                item.to_dict() for item in selected.transcript_byte_bindings
            ],
            "versions": {
                "parser": selected.parser.version,
                "selector": selected.selector.version,
                "material": (
                    str(selected.transcript_lineage.values["extractor_version"])
                    if selected.transcript_lineage is not None
                    else None
                ),
                "model": summary.model.model_id if summary.model is not None else None,
                "prompt": (
                    summary.model.prompt_version if summary.model is not None else None
                ),
                "bundle_producer": BUNDLE_PRODUCER_VERSION,
            },
            "replay": {
                "required": True,
                "locator_count": len(selected.evidence_spans),
            },
        }
        if selected.subject.kind == "official_json":
            raw["schema_version"] = PROJECTED_BUNDLE_SCHEMA
            raw["subject_binding"] = selected.subject.to_dict()
            for key in ("source_ref", "expected_read_policy_sha256", "transcript_lineage", "transcript_byte_bindings"):
                raw.pop(key)
        try:
            bundle = NarrativeBundle.from_dict(raw)
            bundle.validate_against(selected, summary)
            return bundle
        except ContractSizeError as exc:
            raise _VerifyFailure(
                "RESULT_TOO_LARGE",
                HandlerOutcome.TERMINAL_FAILURE,
                "narrative bundle exceeds its byte budget",
            ) from exc
        except PhysicalPathLeakError as exc:
            raise _VerifyFailure(
                "SUMMARY_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "narrative bundle contains a physical path",
            ) from exc
        except NarrativeContractError as exc:
            raise _VerifyFailure(
                "SUMMARY_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "narrative bundle violates its strict contract",
            ) from exc

    @staticmethod
    def _effect(context: JobExecutionContext, bundle: NarrativeBundle, *, generation_sha256: str | None = None) -> Effect:
        bundle_hash = canonical_json_hash(bundle.to_dict())
        target = publication_target(bundle.subject, generation_sha256)
        effect_key = make_effect_key(
            EFFECT_TYPE,
            target,
            canonical_json_hash({"verification_job_id": context.job.job_id,
                                 "bundle_sha256": bundle_hash}),
            BUNDLE_PRODUCER_VERSION,
        )
        return Effect(
            effect_id=f"eff-{effect_key[:32]}",
            effect_key=effect_key,
            job_id=context.job.job_id,
            effect_type=EFFECT_TYPE,
            target=target,
            before_hash=None,
            intended_after_hash=bundle_hash,
            actual_after_hash=None,
            status=EffectStatus.PENDING,
            created_at=context.event.observed_at,
            verified_at=None,
        )


__all__ = ["BUNDLE_PRODUCER_VERSION", "NarrativeVerifyHandler"]
