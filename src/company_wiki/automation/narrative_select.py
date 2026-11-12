"""Pathless select handler for the narrative automation DAG."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from company_wiki.document_model.narrative import NarrativeEvidencePackage, NarrativeParseResult
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_evidence import NARRATIVE_SELECTOR_NAME
from company_wiki.source_catalog.narrative_formats import parser_component
from company_wiki.source_catalog.narrative_language import NarrativeLanguageError
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from company_wiki.source_catalog.narrative_pdf_reading import PdfBytesParser, PdfReading
from company_wiki.source_catalog.narrative_selection import (
    NarrativeMaterialError, RawNarrativeSelection, RawNarrativeSelector,
    transcript_byte_bindings, verify_selected_material,
)
from company_wiki.source_catalog.narrative_selection import (
    selection_algorithm_sha256 as narrative_select_algorithm_identity,
)
from company_wiki.source_catalog.narrative_selector_binding import NarrativeSelector, bind_narrative_selector
from company_wiki.source_catalog.official_json_projection import ProjectionError
from company_wiki.source_contract import SourceReadError
from company_wiki.source_catalog.transcript_text_extract import TranscriptMaterialError

from .execution_context import JobExecutionContext
from company_wiki.source_catalog.narrative_official_json import (
    OfficialProjectionAdapterError,
    VerifiedProjectionView,
    open_verified_projection,
    select_verified_projection,
)
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
    PROJECTED_SELECT_RESULT_SCHEMA,
    SELECT_RESULT_SCHEMA,
    SelectionValue,
    SourceRevisionEventPayload,
    TranscriptLineageValue,
)
from .narrative_source_guard import (
    NarrativeSourceGuardError,
    NarrativeSourceReader,
    prompt_review_value,
    open_verified_source,
)


@dataclass
class _SelectFailure(Exception):
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
        return _failure(
            "POLICY_DENIED", HandlerOutcome.TERMINAL_FAILURE, error.reason
        )
    if error.reason in {"expected_version_mismatch", "source_ref_changed"}:
        return _failure(
            "SOURCE_HASH_MISMATCH", HandlerOutcome.TERMINAL_FAILURE, error.reason
        )
    return _failure(
        "SOURCE_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE, error.reason
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


class NarrativeSelectHandler:
    """Read one pinned source and persist only selected narrative evidence."""

    def __init__(
        self,
        *,
        reader: NarrativeSourceReader,
        pdf_parser: PdfBytesParser | None = None,
        pdf_reading: PdfReading | None = None,
        selector: NarrativeSelector | None = None,
        selector_version: str | None = None,
        normalization: NarrativeNormalization | None = None,
        projection_catalog: Any | None = None,
        work_budget_factory: Callable[[], WorkBudget] | None = None,
    ) -> None:
        self._reader = reader
        if pdf_parser is not None and pdf_reading is not None:
            raise ValueError("provide one complete PDF reading implementation")
        self._pdf_reading = pdf_reading or PdfReading(parser=pdf_parser)
        self._selector = bind_narrative_selector(selector, selector_version=selector_version)
        self._selection = RawNarrativeSelector(
            pdf_reading=self._pdf_reading, selector=self._selector, normalization=normalization,
            work_budget_factory=work_budget_factory,
        )
        self._projection_catalog = projection_catalog

    def __call__(self, context: JobExecutionContext) -> HandlerResult:
        try:
            return self._execute(context)
        except SourceReadError as exc:
            return _read_error_result(exc)
        except ProjectionError as exc:
            return _failure(
                "SOURCE_UNAVAILABLE" if exc.code == "projection_not_found" else "PARSER_INCOMPLETE",
                HandlerOutcome.TERMINAL_FAILURE,
                exc.code,
            )
        except OfficialProjectionAdapterError as exc:
            return _failure(
                "SOURCE_HASH_MISMATCH" if str(exc) == "projection_hash_mismatch" else "INPUT_SCHEMA_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                str(exc),
            )
        except NarrativeLanguageError as exc:
            return _failure(exc.code, HandlerOutcome.TERMINAL_FAILURE, str(exc))
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
        except NarrativeMaterialError as exc:
            return _failure(exc.code, HandlerOutcome.TERMINAL_FAILURE, exc.detail)
        except _SelectFailure as exc:
            return _failure(exc.code, exc.outcome, exc.detail)
        except NarrativeSourceGuardError as exc:
            return _failure(
                exc.code,
                HandlerOutcome.TERMINAL_FAILURE,
                exc.detail,
            )
        except TranscriptMaterialError:
            return _failure(
                "PARSER_INCOMPLETE",
                HandlerOutcome.TERMINAL_FAILURE,
                "transcript material is not replayable",
            )
        except NarrativeContractError:
            return _failure(
                "INPUT_SCHEMA_INVALID",
                HandlerOutcome.TERMINAL_FAILURE,
                "select result violates its strict contract",
            )

    def _execute(self, context: JobExecutionContext) -> HandlerResult:
        result = self.select_source(self._payload(context), checkpoint=context.checkpoint)
        return HandlerResult(
            outcome=HandlerOutcome.SUCCEEDED, result=result.to_dict(), artifacts=(), effects=(),
            metrics=HandlerMetrics(tokens=0, cost_usd=0.0, duration_ms=0), error=None,
        )

    def select_source(
        self, payload: SourceRevisionEventPayload, *, checkpoint: Callable[[], None],
    ) -> NarrativeSelectResult:
        """Select through the source owner, without creating AUTO jobs or model calls.

        Worker execution and current-material cache verification use this same
        parsing, source validation and selection path. The caller supplies its
        existing lease or preparation-deadline checkpoint.
        """
        checkpoint()
        if payload.subject.kind == "official_json":
            return self._execute_projection(payload, checkpoint)
        opened = open_verified_source(self._reader, payload)
        review = prompt_review_value(opened)
        checkpoint()
        work = self._selection.select(
            opened, source_ref=payload.source_ref, source_metadata=payload.source_metadata,
            checkpoint=checkpoint,
        )
        raw = self._result_dict(payload, review, work, selector_version=self._selector.selector_version)
        result = NarrativeSelectResult.from_dict(raw)
        verify_selected_material(work.parsed, work.package,
            mime_type=payload.source_ref.mime_type, pdf_reading=self._pdf_reading)
        checkpoint()
        return result

    def _execute_projection(
        self, payload: SourceRevisionEventPayload, checkpoint: Callable[[], None]
    ) -> NarrativeSelectResult:
        if self._projection_catalog is None:
            raise _SelectFailure(
                "SOURCE_UNAVAILABLE", HandlerOutcome.TERMINAL_FAILURE,
                "official projection source port is not configured",
            )
        view = open_verified_projection(
            self._projection_catalog, projection_id=payload.subject.item_key,
            expected_projection_sha256=payload.subject.subject_sha256,
        )
        # The source port already checked all parents' bytes/state/layout. This
        # binds the requested issuer/as-of/coverage to that verified operation.
        if view.subject != payload.subject:
            raise _SelectFailure(
                "SOURCE_HASH_MISMATCH", HandlerOutcome.TERMINAL_FAILURE,
                "event subject differs from the verified projection",
            )
        checkpoint()
        package = select_verified_projection(
            view, title=payload.source_metadata.title or "untitled", selector=self._selector,
        )
        if view.language is None and package.status != "skipped_no_narrative":
            raise _SelectFailure(
                "SOURCE_LANGUAGE_UNDETERMINED", HandlerOutcome.TERMINAL_FAILURE,
                "official projection has no classifiable native-language fields",
            )
        if payload.source_metadata.language != (view.language or "unknown"):
            raise _SelectFailure(
                "INPUT_SCHEMA_INVALID", HandlerOutcome.TERMINAL_FAILURE,
                "event language differs from verified native-language fields",
            )
        if package.status == "blocked" or (
            not package.evidence_spans
            and (not package.coverage_complete or package.status != "skipped_no_narrative")
        ):
            raise _SelectFailure(
                "PARSER_INCOMPLETE", HandlerOutcome.TERMINAL_FAILURE,
                "official projection has no usable selected evidence",
            )
        parser_name, parser_version = self._projection_parser_identity(view)
        review = PromptReviewValue("not_reviewed", None, None, None, None)
        page_count = len(view.subject.parent_source_refs)
        selection = SelectionValue.from_dict({
            "status": package.status, "coverage_complete": package.coverage_complete,
            "source_units": package.source_units, "candidate_count": package.candidate_count,
            "selected_count": len(package.evidence_spans),
            "omitted_candidate_count": package.omitted_candidate_count,
            "dropped_financial_count": package.dropped_financial_count,
            # These count the captured API pages actually opened by the source
            # export; missing provider pages remain explicit partial coverage.
            "pages_total": page_count, "pages_read": page_count,
            "lines_total": 0, "tables_total": 0, "tables_scanned": 0,
        })
        raw: dict[str, Any] = {
            "schema_version": PROJECTED_SELECT_RESULT_SCHEMA,
            "subject_binding": view.subject.to_dict(),
            "source_metadata": payload.source_metadata.to_dict(),
            "parser": {"name": parser_name, "version": parser_version},
            "selector": {"name": NARRATIVE_SELECTOR_NAME, "version": self._selector.selector_version},
            "selection": selection.to_dict(),
            "evidence_spans": [span.to_dict() for span in package.evidence_spans],
            "prompt_review": review.to_dict(), "summary_scope": "selected_evidence_only",
        }
        if package.reading_context is not None:
            raw["reading_context"] = package.reading_context
        if package.reading_dependencies is not None:
            raw["reading_dependencies"] = package.reading_dependencies
        result = NarrativeSelectResult.from_dict(raw)
        checkpoint()
        return result

    @staticmethod
    def _projection_parser_identity(view: VerifiedProjectionView) -> tuple[str, str]:
        producers = {(span.parser_name, span.parser_version) for span in view.evidence_spans}
        if not producers and view.coverage_complete:
            # An empty, verified projection still has its source-owned producer.
            # This is only parser identity, never guessed language or content.
            name, _, version = view.subject.to_dict()["adapter"]["parser"].rpartition("/")
            return name, version
        if len(producers) != 1:
            raise _SelectFailure(
                "PARSER_INCOMPLETE", HandlerOutcome.TERMINAL_FAILURE,
                "official projection has no single source parser identity",
            )
        return next(iter(producers))

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

    @staticmethod
    def _result_dict(
        payload: SourceRevisionEventPayload,
        review: PromptReviewValue,
        work: RawNarrativeSelection,
        *, selector_version: str,
    ) -> dict[str, Any]:
        material = work.material
        bindings = (
            transcript_byte_bindings(material, work.package.evidence_spans)
            if material is not None
            else ()
        )
        parser_name, parser_version = work.parser_identity or parser_component(
            payload.source_ref.mime_type, payload.source_metadata.source_class,
        )
        raw: dict[str, Any] = {
            "schema_version": SELECT_RESULT_SCHEMA,
            "source_ref": payload.source_ref.to_dict(),
            "expected_read_policy_sha256": payload.expected_read_policy_sha256,
            "source_metadata": payload.source_metadata.to_dict(),
            "parser": {
                "name": parser_name,
                "version": parser_version,
            },
            "selector": {
                "name": NARRATIVE_SELECTOR_NAME,
                "version": selector_version,
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
            "summary_scope": "selected_evidence_only",
        }
        if work.package.reading_context is not None:
            raw["reading_context"] = work.package.reading_context
        elif work.package.selection_diagnostics:
            # A source-work refusal can happen before the reading context is
            # built. Keep its bounded cause on the public result instead of
            # reducing a zero-work stop to status alone.
            raw["selection_diagnostics"] = list(work.package.selection_diagnostics)
        if work.package.reading_dependencies is not None:
            raw["reading_dependencies"] = work.package.reading_dependencies
        return raw


__all__ = [
    "NarrativeSelectHandler",
    "NarrativeSourceReader",
    "narrative_select_algorithm_identity",
]
