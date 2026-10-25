"""Explicit composition root for the narrative document pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from company_wiki.narrative_subject import NarrativeSubject

from .execution_context import JobExecutionContext
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from company_wiki.source_catalog.narrative_pdf_reading import PdfReading
from .models import HandlerResult
from .narrative_model import NarrativeModel
from .narrative_model_caller import NarrativeModelCaller
from .narrative_select import NarrativeSelectHandler
from company_wiki.source_catalog.narrative_evidence import resolve_narrative_selector_version
from .narrative_source_guard import NarrativeSourceReader
from .narrative_summarize import NarrativeSummarizeHandler
from .narrative_verify import NarrativeVerifyHandler


class HandlerRegistrar(Protocol):
    """Minimum worker surface needed by this composition root."""

    def register(
        self,
        job_type: str,
        handler: Callable[[JobExecutionContext], HandlerResult],
    ) -> None: ...


@dataclass(frozen=True)
class NarrativeRuntimeDependencies:
    """All stateful ports required by the three narrative handlers."""

    reader: NarrativeSourceReader
    model: NarrativeModel | None
    model_caller: NarrativeModelCaller | None = None
    normalization: NarrativeNormalization | None = None
    pdf_reading: PdfReading | None = None
    projection_catalog: Any | None = None
    generation_sha256: Callable[[NarrativeSubject], str] | None = None
    selector_version: str | None = None
    reading_model_projection: Callable[[NarrativeSubject], str | None] | None = None
    validate_model_execution: Callable[[NarrativeSubject], None] | None = None


def register_narrative_handlers(
    registrar: HandlerRegistrar,
    dependencies: NarrativeRuntimeDependencies,
) -> None:
    """Register the select, summarize and verify handlers as one unit."""

    selector_version = resolve_narrative_selector_version(dependencies.selector_version)
    pdf_reading = dependencies.pdf_reading or PdfReading()
    registrar.register(
        "source.narrative_select",
        NarrativeSelectHandler(reader=dependencies.reader, normalization=dependencies.normalization,
            pdf_reading=pdf_reading,
            projection_catalog=dependencies.projection_catalog, selector_version=selector_version),
    )
    registrar.register(
        "source.narrative_summarize",
        NarrativeSummarizeHandler(model=dependencies.model, model_caller=dependencies.model_caller,
            reading_model_projection=dependencies.reading_model_projection,
            validate_model_execution=dependencies.validate_model_execution),
    )
    registrar.register(
        "source.narrative_verify",
        NarrativeVerifyHandler(reader=dependencies.reader, normalization=dependencies.normalization,
            pdf_reading=pdf_reading,
            projection_catalog=dependencies.projection_catalog, generation_sha256=dependencies.generation_sha256,
            selector_version=selector_version, reading_model_projection=dependencies.reading_model_projection),
    )


__all__ = [
    "HandlerRegistrar",
    "NarrativeRuntimeDependencies",
    "register_narrative_handlers",
]
