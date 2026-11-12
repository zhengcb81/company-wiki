"""Carrier routing, material selection and source-exact proof for verified originals."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from company_wiki.document_model.narrative import NarrativeEvidencePackage, NarrativeParseResult
from company_wiki.document_normalization.replay import verify_parsed_evidence_spans
from company_wiki.document_normalization.units import PARSER_NAME as NORMALIZATION_PARSER_NAME
from company_wiki.implementation_identity import code_sha256
from company_wiki.resource_budget import (
    WorkBudget,
    WorkBudgetExceeded,
    document_work_budget_factory,
)
from company_wiki.source_contract import EvidenceSpan, ParseStatus
from company_wiki.source_contract.source_version import SourceRefMismatchError, VerifiedContent

from .narrative_contracts import SourceMetadataValue, SourceRefValue, TranscriptByteBinding
from .narrative_evidence import parse_transcript_text
from .narrative_formats import NORMALIZED_MIME_TYPES
from .narrative_normalization import NarrativeNormalization
from .narrative_pdf_reading import PdfReading, PdfReadingError, PdfReadingRequest
from .narrative_replay import verify_replayed_pdf_spans
from .narrative_selector_binding import BoundNarrativeSelector, bind_narrative_selector
from .transcript_text_extract import (
    TRANSCRIPT_MIME_TYPES, TranscriptMaterial, extract_transcript_material,
)


@dataclass
class NarrativeMaterialError(Exception):
    code: str
    detail: str


@dataclass(frozen=True)
class RawNarrativeSelection:
    parsed: NarrativeParseResult
    package: NarrativeEvidencePackage
    material: TranscriptMaterial | None
    parser_identity: tuple[str, str] | None = None


class RawNarrativeSelector:
    """Own format routing and coverage without job, lease, or model knowledge."""

    def __init__(
        self, *, pdf_reading: PdfReading | None = None,
        normalization: NarrativeNormalization | None = None,
        selector: BoundNarrativeSelector | None = None,
        work_budget_factory: Callable[[], WorkBudget] | None = None,
    ) -> None:
        self._pdf_reading = pdf_reading or PdfReading()
        self._normalization = normalization or NarrativeNormalization()
        self._selector = selector or bind_narrative_selector()
        if work_budget_factory is not None and not callable(work_budget_factory):
            raise TypeError("work budget factory must be callable")
        self._work_budget_factory = work_budget_factory
        self._default_budget_factory: Callable[[], WorkBudget] | None = None

    def select(
        self, data: bytes | VerifiedContent, *, source_ref: SourceRefValue, source_metadata: SourceMetadataValue,
        checkpoint: Callable[[], None],
    ) -> RawNarrativeSelection:
        """Select from a buffer already verified by the source reader."""
        if isinstance(data, VerifiedContent):
            try:
                if (data.document_id, data.source_id, data.content_sha256, data.byte_size) != (
                    source_ref.document_id, source_ref.source_id, source_ref.content_sha256, source_ref.byte_size,
                ):
                    raise SourceRefMismatchError("verified identity differs from the source reference")
                data = VerifiedContent.verified_observation(data)
            except SourceRefMismatchError as exc:
                raise NarrativeMaterialError("SOURCE_HASH_MISMATCH", str(exc)) from exc
        if source_metadata.source_class == "filing" and source_ref.mime_type in NORMALIZED_MIME_TYPES:
            return self._select_normalized(data, source_ref, source_metadata, checkpoint)
        raw = data.data if isinstance(data, VerifiedContent) else data
        if source_metadata.source_class == "filing":
            return self._select_pdf(raw, source_ref, source_metadata, checkpoint)
        return self._select_transcript(raw, source_ref, source_metadata, checkpoint)

    def _select_normalized(
        self, data: bytes | VerifiedContent, source_ref: SourceRefValue, source_metadata: SourceMetadataValue,
        checkpoint: Callable[[], None],
    ) -> RawNarrativeSelection:
        try:
            normalize_verified = getattr(self._normalization, "normalize_verified", None)
            if isinstance(data, VerifiedContent) and callable(normalize_verified):
                document = normalize_verified(data, mime_type=source_ref.mime_type)
            else:
                document = self._normalization.normalize(
                    data.data if isinstance(data, VerifiedContent) else data,
                    source_id=source_ref.source_id, source_sha256=source_ref.content_sha256,
                    mime_type=source_ref.mime_type, document_id=source_ref.document_id,
                )
        except (RuntimeError, ValueError) as exc:
            raise NarrativeMaterialError(
                "PARSER_INCOMPLETE",
                "verified filing format cannot be parsed completely",
            ) from exc
        language = source_metadata.language
        parsed = self._normalization.language_structure(document, language)
        checkpoint()
        package = self._run_selector(parsed, source_ref, source_metadata)
        package = self._require_usable_selection(parsed, package)
        return RawNarrativeSelection(parsed, package, None, (document.parser_name, document.parser_version))

    def _work_budget(self) -> WorkBudget:
        """The one account this document read spends.

        An injected factory is the caller's explicit ceiling.  Without one the
        selector resolves the policy once for its own lifetime instead of on
        every document, so one read never re-reads a configuration file.
        """
        if self._work_budget_factory is not None:
            return self._work_budget_factory()
        if self._default_budget_factory is None:
            self._default_budget_factory = document_work_budget_factory()
        return self._default_budget_factory()

    def _select_pdf(
        self, data: bytes, source_ref: SourceRefValue, source_metadata: SourceMetadataValue,
        checkpoint: Callable[[], None],
    ) -> RawNarrativeSelection:
        if source_ref.mime_type != "application/pdf":
            raise NarrativeMaterialError(
                "UNSUPPORTED_SOURCE_TYPE",
                "filing source is not a PDF",
            )
        work_budget = self._work_budget()
        try:
            parsed, package = self._pdf_reading.select(
                data, self._pdf_request(source_ref, source_metadata), selector=self._selector,
                work_budget=work_budget, checkpoint=checkpoint,
            )
        except (WorkBudgetExceeded, PdfReadingError) as exc:
            raise NarrativeMaterialError("PARSER_INCOMPLETE", str(exc)) from exc
        package = self._require_usable_selection(parsed, package)
        return RawNarrativeSelection(parsed, package, None, self._pdf_reading.parser_identity())

    @staticmethod
    def _pdf_request(source_ref: SourceRefValue, source_metadata: SourceMetadataValue) -> PdfReadingRequest:
        return PdfReadingRequest(
            source_id=source_ref.source_id,
            source_sha256=source_ref.content_sha256,
            language=source_metadata.language,
            title=source_metadata.title or "",
            document_kind=source_metadata.document_kind,
        )

    def _select_transcript(
        self, data: bytes, source_ref: SourceRefValue, source_metadata: SourceMetadataValue,
        checkpoint: Callable[[], None],
    ) -> RawNarrativeSelection:
        if source_ref.mime_type not in TRANSCRIPT_MIME_TYPES:
            raise NarrativeMaterialError(
                "UNSUPPORTED_SOURCE_TYPE",
                "transcript MIME type is unsupported",
            )
        material = extract_transcript_material(
            data, mime_type=source_ref.mime_type
        )
        material.verify(data)
        parsed = parse_transcript_text(
            material.text_utf8,
            source_id=source_ref.source_id,
            source_sha256=source_ref.content_sha256,
            language=source_metadata.language,
        )
        checkpoint()
        package = self._run_selector(parsed, source_ref, source_metadata)
        package = self._require_usable_selection(parsed, package)
        return RawNarrativeSelection(parsed, package, material)

    def _run_selector(
        self,
        parsed: NarrativeParseResult,
        source_ref: SourceRefValue,
        source_metadata: SourceMetadataValue,
    ) -> NarrativeEvidencePackage:
        return self._selector(
            replace(parsed, mime_type=source_ref.mime_type),
            title=source_metadata.title or "untitled",
            existing_kind=source_metadata.document_kind,
        )

    @staticmethod
    def _require_usable_selection(
        parsed: NarrativeParseResult, package: NarrativeEvidencePackage
    ) -> NarrativeEvidencePackage:
        """Admit source-proven excerpts, independently of carrier completeness.

        Opaque/unread material stays visible in coverage. It does not invalidate
        independent closed source excerpts; no selected text is repaired or
        assigned a new source here. Media/open failures remain the parser's
        responsibility before this boundary.
        """
        if package.status == "blocked":
            raise NarrativeMaterialError(
                "PARSER_INCOMPLETE",
                "source parsing is incomplete",
            )
        if not parsed.coverage_complete and package.coverage_complete:
            package = replace(package, coverage_complete=False)
        if package.evidence_spans and not package.coverage_complete and package.status == "selected":
            package = replace(package, status="partial")
        if not package.evidence_spans and not package.coverage_complete:
            raise NarrativeMaterialError(
                "PARSER_INCOMPLETE",
                "empty selection does not have complete coverage",
            )
        if not package.evidence_spans and package.status != "skipped_no_narrative":
            raise NarrativeMaterialError(
                "PARSER_INCOMPLETE",
                "valuable source has no replayable selected evidence",
            )
        return package


def verify_selected_material(parsed: NarrativeParseResult, package: NarrativeEvidencePackage,
                              *, mime_type: str | None = None,
                              pdf_reading: PdfReading | None = None) -> None:
    """Match bounded canonical evidence to this parse before any model call.

    Canonical shape/path/size checks run once in the result constructor
    first. Material proof must not mask those existing precise diagnostics.
    """
    spans = package.evidence_spans
    if not spans:
        return
    if (package.source_id != parsed.source_id
        or package.source_sha256 != parsed.source_sha256
        or any(span.source_id != parsed.source_id or span.parse_status != ParseStatus.PARSED
               or {"low_ocr_confidence", "locator_unstable"}.intersection(span.quality_flags)
               for span in spans)):
        raise NarrativeMaterialError(
            "PARSER_INCOMPLETE", "selected material is not reliable parsed source evidence",
        )
    try:
        if (mime_type or parsed.mime_type) == "application/pdf":
            (pdf_reading or PdfReading()).verify_material(parsed, spans)
        elif parsed.units and all(unit.parser_name == NORMALIZATION_PARSER_NAME for unit in parsed.units):
            verify_parsed_evidence_spans(parsed.units, source_id=parsed.source_id, evidence_spans=spans)
        else:
            verified, failed = verify_replayed_pdf_spans(spans, parsed.units)
            if failed or len(verified) != len(spans):
                raise ValueError("selected evidence differs from parsed material")
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        raise NarrativeMaterialError(
            "PARSER_INCOMPLETE", "selected evidence cannot be matched to the parsed original",
        ) from exc


def transcript_byte_bindings(
    material: TranscriptMaterial, evidence_spans: Sequence[EvidenceSpan]
) -> tuple[TranscriptByteBinding, ...]:
    """Bind selected transcript lines to their exact original byte ranges."""
    bindings: list[TranscriptByteBinding] = []
    for span in evidence_spans:
        start = span.structured_value.get("line_start")
        end = span.structured_value.get("line_end")
        if type(start) is not int or type(end) is not int or end < start:
            raise NarrativeMaterialError(
                "PARSER_INCOMPLETE",
                "selected transcript evidence has no stable line range",
            )
        lines = tuple(
            line for line in material.lines if start <= line.line_number <= end
        )
        if len(lines) != end - start + 1:
            raise NarrativeMaterialError(
                "PARSER_INCOMPLETE",
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


def selection_algorithm_sha256() -> str:
    """Return the portable fingerprint of the carrier and proof implementation."""
    return code_sha256(__file__)


__all__ = [
    "NarrativeMaterialError", "RawNarrativeSelection", "RawNarrativeSelector",
    "selection_algorithm_sha256", "transcript_byte_bindings", "verify_selected_material",
]
