"""Explicit composition root for the narrative document pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .execution_context import JobExecutionContext
from .models import HandlerResult
from .narrative_model import NarrativeModel
from .narrative_select import NarrativeSelectHandler
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


def register_narrative_handlers(
    registrar: HandlerRegistrar,
    dependencies: NarrativeRuntimeDependencies,
) -> None:
    """Register the select, summarize and verify handlers as one unit."""

    registrar.register(
        "source.narrative_select",
        NarrativeSelectHandler(reader=dependencies.reader),
    )
    registrar.register(
        "source.narrative_summarize",
        NarrativeSummarizeHandler(model=dependencies.model),
    )
    registrar.register(
        "source.narrative_verify",
        NarrativeVerifyHandler(reader=dependencies.reader),
    )


__all__ = [
    "HandlerRegistrar",
    "NarrativeRuntimeDependencies",
    "register_narrative_handlers",
]
