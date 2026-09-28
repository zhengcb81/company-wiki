"""Replay and bundle handler for selected narrative evidence."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_PARSER_NAME,
    NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_NAME,
    NARRATIVE_SELECTOR_VERSION,
    verify_pdf_evidence_spans_bytes,
    verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.provider_use_policy import (
    ProviderUsePolicy,
    ProviderUsePolicyError,
)
from company_wiki.source_catalog.source_reader import SourceReadError, VerifiedContent
from company_wiki.source_catalog.transcript_text_extract import (
    TranscriptMaterialError,
    TranscriptTextLine,
    extract_transcript_material,
)
from company_wiki.source_catalog.transcript_use_policy import (
    authorize_transcript_actions,
)
from company_wiki.source_contract import EvidenceSpan

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
from .narrative_contracts import (
    BUNDLE_SCHEMA,
    ContractSizeError,
    NarrativeBundle,
    NarrativeContractError,
    NarrativeSelectResult,
    NarrativeSummaryResult,
    PhysicalPathLeakError,
    PromptReviewValue,
    SourceRevisionEventPayload,
    TranscriptActionPolicyValue,
)
from .narrative_model import NARRATIVE_PROMPT_VERSION
from .narrative_source_guard import (
    NarrativeSourceGuardError,
    NarrativeSourceReader,
    prompt_review_value,
    source_ref,
    validate_opened_identity,
    validate_source_metadata,
)


BUNDLE_PRODUCER_VERSION = "1.0.0"
EFFECT_TYPE = "narrative_bundle.publish"
ProviderPolicyLoader = Callable[[], ProviderUsePolicy | None]


class PdfEvidenceReplayer(Protocol):
    def __call__(
        self,
        data: bytes,
        *,
        source_id: str,
        source_sha256: str,
        evidence_spans: Sequence[EvidenceSpan],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]: ...


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
    return _failure(
        "SOURCE_UNAVAILABLE", HandlerOutcome.BLOCKED_HUMAN, error.reason
    )


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
) -> None:
    if (
        selected.source_ref.to_dict() != payload.source_ref.to_dict()
        or selected.source_metadata.to_dict() != payload.source_metadata.to_dict()
        or selected.expected_read_policy_sha256
        != payload.expected_read_policy_sha256
        or summary.source_ref != selected.source_ref
    ):
        raise _VerifyFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "dependency identity differs from the source event",
        )
    if (
        selected.parser.name != NARRATIVE_PARSER_NAME
        or selected.parser.version != NARRATIVE_PARSER_VERSION
        or selected.selector.name != NARRATIVE_SELECTOR_NAME
        or selected.selector.version != NARRATIVE_SELECTOR_VERSION
        or (
            summary.model is not None
            and summary.model.prompt_version != NARRATIVE_PROMPT_VERSION
        )
    ):
        raise _VerifyFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "dependency component version is not the active version",
        )
    if payload.source_metadata.source_class == "transcript":
        _validate_transcript_dependency_policy(payload, selected, summary)


def _validate_transcript_dependency_policy(
    payload: SourceRevisionEventPayload,
    selected: NarrativeSelectResult,
    summary: NarrativeSummaryResult,
) -> None:
    pin = payload.transcript_policy
    selected_policy = selected.transcript_action_policy
    summary_policy = summary.transcript_action_policy
    if (
        pin is None
        or selected_policy is None
        or selected_policy.policy_sha256 != pin.expected_provider_policy_sha256
        or (
            summary.status == "completed"
            and (
                summary_policy is None
                or summary_policy.policy_sha256
                != pin.expected_provider_policy_sha256
            )
        )
    ):
        raise _VerifyFailure(
            "DEPENDENCY_INVALID",
            HandlerOutcome.TERMINAL_FAILURE,
            "transcript dependency policy differs from the source event",
        )


class NarrativeVerifyHandler:
    """Replay all locators and emit one logical publication effect."""

    def __init__(
        self,
        *,
        reader: NarrativeSourceReader,
        provider_policy_loader: ProviderPolicyLoader | None,
        current_date: Callable[[], str],
        pdf_replayer: PdfEvidenceReplayer | None = None,
    ) -> None:
        self._reader = reader
        self._provider_policy_loader = provider_policy_loader
        self._current_date = current_date
        self._pdf_replayer = pdf_replayer or verify_pdf_evidence_spans_bytes

    def __call__(self, context: JobExecutionContext) -> HandlerResult:
        try:
            return self._execute(context)
        except SourceReadError as exc:
            return _read_error_result(exc)
        except NarrativeSourceGuardError as exc:
            return _failure(exc.code, HandlerOutcome.TERMINAL_FAILURE, exc.detail)
        except _VerifyFailure as exc:
            return _failure(exc.code, exc.outcome, exc.detail)
        except ProviderUsePolicyError:
            return _failure(
                "POLICY_DENIED",
                HandlerOutcome.TERMINAL_FAILURE,
                "provider use policy is unavailable or invalid",
            )
        except TranscriptMaterialError:
            return _failure(
                "LOCATOR_REPLAY_FAILED",
                HandlerOutcome.BLOCKED_HUMAN,
                "transcript material cannot be replayed",
            )

    def _execute(self, context: JobExecutionContext) -> HandlerResult:
        context.checkpoint()
        payload = self._payload(context)
        selected, summary = _dependencies(context)
        _validate_dependency_identity(payload, selected, summary)
        ref = source_ref(payload)
        opened = self._reader.open_version(
            ref,
            purpose="narrative_derivation",
            expected_read_policy_sha256=payload.expected_read_policy_sha256,
        )
        validate_opened_identity(payload, opened)
        validate_source_metadata(payload, self._reader.describe_version(ref))
        review = self._current_review(opened, selected, summary)
        action_policy = self._current_transcript_policy(payload, summary)
        context.checkpoint()
        self._replay(opened.data, selected)
        bundle = self._bundle(selected, summary, review, action_policy)
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
        opened: VerifiedContent,
        selected: NarrativeSelectResult,
        summary: NarrativeSummaryResult,
    ) -> PromptReviewValue:
        try:
            current = prompt_review_value(opened)
        except (NarrativeSourceGuardError, NarrativeContractError) as exc:
            raise _VerifyFailure(
                "PROMPT_REVIEW_REQUIRED",
                HandlerOutcome.BLOCKED_HUMAN,
                "current prompt review is missing or invalid",
            ) from exc
        if (
            current.status == "not_reviewed"
            or current != selected.prompt_review
            or current != summary.prompt_review
        ):
            raise _VerifyFailure(
                "PROMPT_REVIEW_REQUIRED",
                HandlerOutcome.BLOCKED_HUMAN,
                "current prompt review differs from narrative dependencies",
            )
        return current

    def _current_transcript_policy(
        self,
        payload: SourceRevisionEventPayload,
        summary: NarrativeSummaryResult,
    ) -> TranscriptActionPolicyValue | None:
        if payload.source_metadata.source_class != "transcript":
            return None
        pin = payload.transcript_policy
        if pin is None or self._provider_policy_loader is None:
            raise _VerifyFailure(
                "POLICY_DENIED",
                HandlerOutcome.TERMINAL_FAILURE,
                "transcript verify policy configuration is missing",
            )
        policy = self._provider_policy_loader()
        if policy is None or policy.policy_sha256 != pin.expected_provider_policy_sha256:
            raise _VerifyFailure(
                "POLICY_DENIED",
                HandlerOutcome.TERMINAL_FAILURE,
                "current transcript policy differs from the event pin",
            )
        actions = ["derive_text", "select_evidence"]
        if summary.status == "completed":
            actions.append("generate_summary")
        decision = authorize_transcript_actions(
            rights_policy=policy,
            provider_id=pin.provider_id,
            source_url=pin.source_url,
            actions=tuple(actions),
            on_date=self._current_date(),
        )
        if not decision.allowed or decision.rights_policy_sha256 != policy.policy_sha256:
            raise _VerifyFailure(
                "POLICY_DENIED",
                HandlerOutcome.TERMINAL_FAILURE,
                "current transcript actions are not permitted",
            )
        return TranscriptActionPolicyValue.from_dict(
            {
                "policy_sha256": policy.policy_sha256,
                "evidence_sha256_by_action": [
                    list(item) for item in decision.evidence_sha256_by_action
                ],
            }
        )

    def _replay(self, data: bytes, selected: NarrativeSelectResult) -> None:
        if selected.source_metadata.source_class == "filing":
            self._replay_pdf(data, selected)
            return
        self._replay_transcript(data, selected)

    def _replay_pdf(self, data: bytes, selected: NarrativeSelectResult) -> None:
        try:
            verified, failed = self._pdf_replayer(
                data,
                source_id=selected.source_ref.source_id,
                source_sha256=selected.source_ref.content_sha256,
                evidence_spans=selected.evidence_spans,
            )
        except (RuntimeError, ValueError) as exc:
            raise _VerifyFailure(
                "LOCATOR_REPLAY_FAILED",
                HandlerOutcome.BLOCKED_HUMAN,
                "PDF evidence replay could not complete",
            ) from exc
        self._require_full_replay(selected.evidence_spans, verified, failed)

    @staticmethod
    def _replay_transcript(data: bytes, selected: NarrativeSelectResult) -> None:
        material = extract_transcript_material(
            data,
            mime_type=selected.source_ref.mime_type,
        )
        material.verify(data)
        if (
            selected.transcript_lineage is None
            or material.lineage_dict() != selected.transcript_lineage.to_dict()
        ):
            raise _VerifyFailure(
                "LOCATOR_REPLAY_FAILED",
                HandlerOutcome.BLOCKED_HUMAN,
                "transcript material lineage differs from selection",
            )
        NarrativeVerifyHandler._verify_transcript_bindings(material.lines, selected)
        try:
            verified, failed = verify_transcript_evidence_spans(
                material.text_utf8,
                source_id=selected.source_ref.source_id,
                source_sha256=selected.source_ref.content_sha256,
                evidence_spans=selected.evidence_spans,
                language=selected.source_metadata.language,
            )
        except (RuntimeError, ValueError) as exc:
            raise _VerifyFailure(
                "LOCATOR_REPLAY_FAILED",
                HandlerOutcome.BLOCKED_HUMAN,
                "transcript evidence replay could not complete",
            ) from exc
        NarrativeVerifyHandler._require_full_replay(
            selected.evidence_spans, verified, failed
        )

    @staticmethod
    def _verify_transcript_bindings(
        lines: Sequence[TranscriptTextLine],
        selected: NarrativeSelectResult,
    ) -> None:
        spans = {span.span_id: span for span in selected.evidence_spans}
        for binding in selected.transcript_byte_bindings:
            span = spans[binding.evidence_id]
            start = span.structured_value.get("line_start")
            end = span.structured_value.get("line_end")
            bound_lines = tuple(
                line
                for line in lines
                if binding.material_line_start
                <= line.line_number
                <= binding.material_line_end
            )
            actual = tuple(
                (line.source_byte_start, line.source_byte_end) for line in bound_lines
            )
            if (
                start != binding.material_line_start
                or end != binding.material_line_end
                or actual != binding.source_byte_ranges
            ):
                raise _VerifyFailure(
                    "LOCATOR_REPLAY_FAILED",
                    HandlerOutcome.BLOCKED_HUMAN,
                    "transcript byte binding differs from original bytes",
                )

    @staticmethod
    def _require_full_replay(
        spans: Sequence[EvidenceSpan],
        verified: Sequence[str],
        failed: Sequence[str],
    ) -> None:
        expected = {span.span_id for span in spans}
        if failed or set(verified) != expected or len(verified) != len(expected):
            raise _VerifyFailure(
                "LOCATOR_REPLAY_FAILED",
                HandlerOutcome.BLOCKED_HUMAN,
                "not every selected locator replayed exactly",
            )

    @staticmethod
    def _bundle(
        selected: NarrativeSelectResult,
        summary: NarrativeSummaryResult,
        review: PromptReviewValue,
        action_policy: TranscriptActionPolicyValue | None,
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
            "transcript_action_policy": (
                action_policy.to_dict() if action_policy is not None else None
            ),
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
    def _effect(context: JobExecutionContext, bundle: NarrativeBundle) -> Effect:
        bundle_hash = canonical_json_hash(bundle.to_dict())
        target = (
            "urn:company-wiki:narrative-bundle:"
            f"{bundle.source_ref.document_id}:{bundle.source_ref.content_sha256}"
        )
        effect_key = make_effect_key(
            EFFECT_TYPE,
            target,
            bundle_hash,
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
