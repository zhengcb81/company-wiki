"""Pathless select handler for the narrative automation DAG."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from company_wiki.source_catalog.narrative_document import (
    NarrativeEvidencePackage,
    NarrativeParseResult,
)
from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_PARSER_NAME,
    NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_NAME,
    NARRATIVE_SELECTOR_VERSION,
    parse_pdf_bytes,
    parse_transcript_text,
    select_narrative_evidence,
)
from company_wiki.source_catalog.provider_use_policy import (
    ProviderUsePolicy,
    ProviderUsePolicyError,
)
from company_wiki.source_catalog.source_reader import (
    SourceReadError,
)
from company_wiki.source_catalog.transcript_text_extract import (
    TRANSCRIPT_MIME_TYPES,
    TranscriptMaterial,
    TranscriptMaterialError,
    extract_transcript_material,
)
from company_wiki.source_catalog.transcript_use_policy import (
    authorize_transcript_actions,
)
from company_wiki.source_contract import EvidenceSpan

from .execution_context import JobExecutionContext
from .models import (
    HandlerError,
    HandlerMetrics,
    HandlerOutcome,
    HandlerResult,
)
from .narrative_contracts import (
    ContractSizeError,
    NarrativeContractError,
    NarrativeSelectResult,
    PhysicalPathLeakError,
    PromptReviewValue,
    SELECT_RESULT_SCHEMA,
    SelectionValue,
    SourceRevisionEventPayload,
    TranscriptActionPolicyValue,
    TranscriptByteBinding,
    TranscriptLineageValue,
)
from .narrative_source_guard import (
    NarrativeSourceGuardError,
    NarrativeSourceReader,
    prompt_review_value,
    source_ref,
    validate_opened_identity,
    validate_source_metadata,
)


class PdfBytesParser(Protocol):
    def __call__(
        self,
        data: bytes,
        *,
        source_id: str,
        source_sha256: str,
        parser_version: str = NARRATIVE_PARSER_VERSION,
        language: str = "zh",
        full_table_scan: bool = False,
        table_pages: Sequence[int] | None = None,
    ) -> NarrativeParseResult: ...


class NarrativeSelector(Protocol):
    def __call__(
        self,
        parsed: NarrativeParseResult,
        *,
        title: str,
        existing_kind: str = "unknown",
    ) -> NarrativeEvidencePackage: ...


ProviderPolicyLoader = Callable[[], ProviderUsePolicy | None]


@dataclass(frozen=True)
class _SelectFailure(Exception):
    code: str
    outcome: HandlerOutcome
    detail: str


@dataclass(frozen=True)
class _SelectionWork:
    parsed: NarrativeParseResult
    package: NarrativeEvidencePackage
    material: TranscriptMaterial | None
    action_policy: TranscriptActionPolicyValue | None


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
        return _failure(
            "POLICY_DENIED", HandlerOutcome.TERMINAL_FAILURE, error.reason
        )
    if error.reason in {"expected_version_mismatch", "source_ref_changed"}:
        return _failure(
            "SOURCE_HASH_MISMATCH", HandlerOutcome.TERMINAL_FAILURE, error.reason
        )
    return _failure(
        "SOURCE_UNAVAILABLE", HandlerOutcome.BLOCKED_HUMAN, error.reason
    )


def _selection_value(
    parsed: NarrativeParseResult, package: NarrativeEvidencePackage
) -> SelectionValue:
    table_pages_total = len(parsed.table_scan_pages) + len(
        parsed.deferred_table_pages
    )
    return SelectionValue.from_dict(
        {
            "status": package.status,
            "coverage_complete": package.coverage_complete,
            "source_units": package.source_units,
            "candidate_count": package.candidate_count,
            "selected_count": len(package.evidence_spans),
            "omitted_candidate_count": package.omitted_candidate_count,
            "dropped_financial_count": package.dropped_financial_count,
            "pages_total": parsed.page_count,
            "pages_read": parsed.pages_read,
            "lines_total": parsed.line_count,
            "tables_total": table_pages_total,
            "tables_scanned": len(parsed.table_scan_pages),
        }
    )


def _transcript_bindings(
    material: TranscriptMaterial, evidence_spans: Sequence[EvidenceSpan]
) -> tuple[TranscriptByteBinding, ...]:
    bindings: list[TranscriptByteBinding] = []
    for span in evidence_spans:
        start = span.structured_value.get("line_start")
        end = span.structured_value.get("line_end")
        if type(start) is not int or type(end) is not int or end < start:
            raise _SelectFailure(
                "PARSER_INCOMPLETE",
                HandlerOutcome.BLOCKED_HUMAN,
                "selected transcript evidence has no stable line range",
            )
        lines = tuple(
            line for line in material.lines if start <= line.line_number <= end
        )
        if len(lines) != end - start + 1:
            raise _SelectFailure(
                "PARSER_INCOMPLETE",
                HandlerOutcome.BLOCKED_HUMAN,
                "selected transcript line range cannot be replayed",
            )
        bindings.append(
            TranscriptByteBinding(
                evidence_id=span.span_id,
                material_line_start=start,
                material_line_end=end,
                source_byte_ranges=tuple(
                    (line.source_byte_start, line.source_byte_end) for line in lines
                ),
            )
        )
    return tuple(bindings)


class NarrativeSelectHandler:
    """Read one pinned source and persist only selected narrative evidence."""

    def __init__(
        self,
        *,
        reader: NarrativeSourceReader,
        provider_policy_loader: ProviderPolicyLoader | None,
        current_date: Callable[[], str],
        pdf_parser: PdfBytesParser = parse_pdf_bytes,
        selector: NarrativeSelector | None = None,
    ) -> None:
        self._reader = reader
        self._provider_policy_loader = provider_policy_loader
        self._current_date = current_date
        self._pdf_parser = pdf_parser
        self._selector = selector or select_narrative_evidence

    def __call__(self, context: JobExecutionContext) -> HandlerResult:
        try:
            return self._execute(context)
        except SourceReadError as exc:
            return _read_error_result(exc)
        except ContractSizeError:
            return _failure(
                "RESULT_TOO_LARGE",
                HandlerOutcome.TERMINAL_FAILURE,
                "select result exceeds its byte budget",
            )
        except PhysicalPathLeakError:
            return _failure(
                "INPUT_SCHEMA_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "select result contains a forbidden physical path",
            )
        except _SelectFailure as exc:
            return _failure(exc.code, exc.outcome, exc.detail)
        except NarrativeSourceGuardError as exc:
            return _failure(
                exc.code,
                HandlerOutcome.TERMINAL_FAILURE,
                exc.detail,
            )
        except ProviderUsePolicyError:
            return _failure(
                "POLICY_DENIED",
                HandlerOutcome.TERMINAL_FAILURE,
                "provider use policy is unavailable or invalid",
            )
        except TranscriptMaterialError:
            return _failure(
                "PARSER_INCOMPLETE",
                HandlerOutcome.BLOCKED_HUMAN,
                "transcript material is not replayable",
            )
        except NarrativeContractError:
            return _failure(
                "INPUT_SCHEMA_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "select result violates its strict contract",
            )

    def _execute(self, context: JobExecutionContext) -> HandlerResult:
        context.checkpoint()
        payload = self._payload(context)
        ref = source_ref(payload)
        opened = self._reader.open_version(
            ref,
            purpose="narrative_derivation",
            expected_read_policy_sha256=payload.expected_read_policy_sha256,
        )
        validate_opened_identity(payload, opened)
        validate_source_metadata(payload, self._reader.describe_version(ref))
        review = prompt_review_value(opened)
        context.checkpoint()
        work = self._select(payload, opened.data, context)
        raw = self._result_dict(payload, review, work)
        result = NarrativeSelectResult.from_dict(raw)
        context.checkpoint()
        return HandlerResult(
            outcome=HandlerOutcome.SUCCEEDED,
            result=result.to_dict(),
            artifacts=(),
            effects=(),
            metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0),
            error=None,
        )

    @staticmethod
    def _payload(context: JobExecutionContext) -> SourceRevisionEventPayload:
        if (
            context.job.job_type != "source.narrative_select"
            or context.source_revision is None
            or context.dependency_results
        ):
            raise _SelectFailure(
                "INPUT_SCHEMA_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "select context identity or dependencies are invalid",
            )
        return context.source_revision

    def _select(
        self,
        payload: SourceRevisionEventPayload,
        data: bytes,
        context: JobExecutionContext,
    ) -> _SelectionWork:
        if payload.source_metadata.source_class == "filing":
            return self._select_pdf(payload, data, context)
        return self._select_transcript(payload, data, context)

    def _select_pdf(
        self,
        payload: SourceRevisionEventPayload,
        data: bytes,
        context: JobExecutionContext,
    ) -> _SelectionWork:
        if payload.source_ref.mime_type != "application/pdf":
            raise _SelectFailure(
                "UNSUPPORTED_SOURCE_TYPE",
                HandlerOutcome.TERMINAL_FAILURE,
                "filing source is not a PDF",
            )
        parsed = self._parse_pdf(payload, data)
        context.checkpoint()
        package = self._run_selector(payload, parsed)
        if not package.evidence_spans and parsed.deferred_table_pages:
            parsed = self._parse_pdf(payload, data, full_table_scan=True)
            context.checkpoint()
            package = self._run_selector(payload, parsed)
        self._require_usable_selection(parsed, package)
        return _SelectionWork(parsed, package, None, None)

    def _parse_pdf(
        self,
        payload: SourceRevisionEventPayload,
        data: bytes,
        *,
        full_table_scan: bool = False,
    ) -> NarrativeParseResult:
        try:
            return self._pdf_parser(
                data,
                source_id=payload.source_ref.source_id,
                source_sha256=payload.source_ref.content_sha256,
                language=payload.source_metadata.language,
                full_table_scan=full_table_scan,
            )
        except (RuntimeError, ValueError) as exc:
            raise _SelectFailure(
                "PARSER_INCOMPLETE",
                HandlerOutcome.BLOCKED_HUMAN,
                "verified PDF cannot be parsed completely",
            ) from exc

    def _select_transcript(
        self,
        payload: SourceRevisionEventPayload,
        data: bytes,
        context: JobExecutionContext,
    ) -> _SelectionWork:
        if payload.source_ref.mime_type not in TRANSCRIPT_MIME_TYPES:
            raise _SelectFailure(
                "UNSUPPORTED_SOURCE_TYPE",
                HandlerOutcome.TERMINAL_FAILURE,
                "transcript MIME type is unsupported",
            )
        action_policy = self._transcript_policy(payload)
        material = extract_transcript_material(
            data, mime_type=payload.source_ref.mime_type
        )
        material.verify(data)
        parsed = parse_transcript_text(
            material.text_utf8,
            source_id=payload.source_ref.source_id,
            source_sha256=payload.source_ref.content_sha256,
            language=payload.source_metadata.language,
        )
        context.checkpoint()
        package = self._run_selector(payload, parsed)
        self._require_usable_selection(parsed, package)
        return _SelectionWork(parsed, package, material, action_policy)

    def _transcript_policy(
        self, payload: SourceRevisionEventPayload
    ) -> TranscriptActionPolicyValue:
        pin = payload.transcript_policy
        if pin is None or self._provider_policy_loader is None:
            raise _SelectFailure(
                "POLICY_DENIED",
                HandlerOutcome.TERMINAL_FAILURE,
                "transcript policy configuration is missing",
            )
        policy = self._provider_policy_loader()
        if policy is None or policy.policy_sha256 != pin.expected_provider_policy_sha256:
            raise _SelectFailure(
                "POLICY_DENIED",
                HandlerOutcome.TERMINAL_FAILURE,
                "transcript policy differs from the event pin",
            )
        decision = authorize_transcript_actions(
            rights_policy=policy,
            provider_id=pin.provider_id,
            source_url=pin.source_url,
            actions=("derive_text", "select_evidence"),
            on_date=self._current_date(),
        )
        if not decision.allowed or decision.rights_policy_sha256 != policy.policy_sha256:
            raise _SelectFailure(
                "POLICY_DENIED",
                HandlerOutcome.TERMINAL_FAILURE,
                "transcript actions are not currently permitted",
            )
        return TranscriptActionPolicyValue.from_dict(
            {
                "policy_sha256": policy.policy_sha256,
                "evidence_sha256_by_action": [
                    list(item) for item in decision.evidence_sha256_by_action
                ],
            }
        )

    def _run_selector(
        self,
        payload: SourceRevisionEventPayload,
        parsed: NarrativeParseResult,
    ) -> NarrativeEvidencePackage:
        return self._selector(
            parsed,
            title=payload.source_metadata.title or "untitled",
            existing_kind=payload.source_metadata.document_kind,
        )

    @staticmethod
    def _require_usable_selection(
        parsed: NarrativeParseResult, package: NarrativeEvidencePackage
    ) -> None:
        if parsed.errors or parsed.opaque_pages or package.status == "blocked":
            raise _SelectFailure(
                "PARSER_INCOMPLETE",
                HandlerOutcome.BLOCKED_HUMAN,
                "source parsing is incomplete",
            )
        if not package.evidence_spans and not package.coverage_complete:
            raise _SelectFailure(
                "PARSER_INCOMPLETE",
                HandlerOutcome.BLOCKED_HUMAN,
                "empty selection does not have complete coverage",
            )
        if not package.evidence_spans and package.status != "skipped_no_narrative":
            raise _SelectFailure(
                "PARSER_INCOMPLETE",
                HandlerOutcome.BLOCKED_HUMAN,
                "valuable source has no replayable selected evidence",
            )

    @staticmethod
    def _result_dict(
        payload: SourceRevisionEventPayload,
        review: PromptReviewValue,
        work: _SelectionWork,
    ) -> dict[str, Any]:
        material = work.material
        bindings = (
            _transcript_bindings(material, work.package.evidence_spans)
            if material is not None
            else ()
        )
        return {
            "schema_version": SELECT_RESULT_SCHEMA,
            "source_ref": payload.source_ref.to_dict(),
            "expected_read_policy_sha256": payload.expected_read_policy_sha256,
            "source_metadata": payload.source_metadata.to_dict(),
            "parser": {
                "name": NARRATIVE_PARSER_NAME,
                "version": NARRATIVE_PARSER_VERSION,
            },
            "selector": {
                "name": NARRATIVE_SELECTOR_NAME,
                "version": NARRATIVE_SELECTOR_VERSION,
            },
            "selection": _selection_value(work.parsed, work.package).to_dict(),
            "evidence_spans": [
                span.to_dict() for span in work.package.evidence_spans
            ],
            "prompt_review": review.to_dict(),
            "transcript_lineage": (
                TranscriptLineageValue.from_dict(material.lineage_dict()).to_dict()
                if material is not None
                else None
            ),
            "transcript_byte_bindings": [item.to_dict() for item in bindings],
            "transcript_action_policy": (
                work.action_policy.to_dict() if work.action_policy is not None else None
            ),
            "summary_scope": "selected_evidence_only",
        }


__all__ = ["NarrativeSelectHandler", "NarrativeSourceReader"]
