"""Explicit composition root for the narrative document pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from company_wiki.source_catalog.prompt_injection import (
    PromptInjectionReviewError,
    read_prompt_injection_review,
)
from company_wiki.source_catalog.provider_use_policy import ProviderUsePolicy

from .execution_context import JobExecutionContext
from .models import HandlerResult
from .narrative_contracts import NarrativeContractError, PromptReviewValue
from .narrative_model import NarrativeModel
from .narrative_select import NarrativeSelectHandler
from .narrative_source_guard import NarrativeSourceReader
from .narrative_summarize import NarrativeSummarizeHandler, PromptReviewLoader
from .narrative_verify import NarrativeVerifyHandler


class _CatalogReviewStore(Protocol):
    def fetchone(
        self,
        sql: str,
        params: tuple[object, ...] = (),
    ) -> Any: ...


class HandlerRegistrar(Protocol):
    """Minimum worker surface needed by this composition root."""

    def register(
        self,
        job_type: str,
        handler: Callable[[JobExecutionContext], HandlerResult],
    ) -> None: ...


class CatalogPromptReviewLoader:
    """Project one catalog review receipt into the strict worker value."""

    def __init__(self, store: _CatalogReviewStore) -> None:
        self._store = store

    def __call__(self, document_id: str) -> PromptReviewValue | None:
        try:
            receipt = read_prompt_injection_review(self._store, document_id)
        except PromptInjectionReviewError:
            return None
        if receipt is None:
            return None
        try:
            return PromptReviewValue.from_dict(
                {
                    "status": receipt.get("status"),
                    "source_sha256": receipt.get("source_sha256"),
                    "evidence_sha256": receipt.get("evidence_sha256"),
                    "policy_hash": receipt.get("policy_hash"),
                    "reviewed_at": receipt.get("reviewed_at"),
                }
            )
        except NarrativeContractError:
            return None


@dataclass(frozen=True)
class NarrativeRuntimeDependencies:
    """All stateful ports required by the three narrative handlers."""

    reader: NarrativeSourceReader
    model: NarrativeModel | None
    prompt_review_loader: PromptReviewLoader
    provider_policy_loader: Callable[[], ProviderUsePolicy | None] | None
    current_date: Callable[[], str]


def register_narrative_handlers(
    registrar: HandlerRegistrar,
    dependencies: NarrativeRuntimeDependencies,
) -> None:
    """Register the select, summarize and verify handlers as one unit."""

    registrar.register(
        "source.narrative_select",
        NarrativeSelectHandler(
            reader=dependencies.reader,
            provider_policy_loader=dependencies.provider_policy_loader,
            current_date=dependencies.current_date,
        ),
    )
    registrar.register(
        "source.narrative_summarize",
        NarrativeSummarizeHandler(
            model=dependencies.model,
            prompt_review_loader=dependencies.prompt_review_loader,
            provider_policy_loader=dependencies.provider_policy_loader,
            current_date=dependencies.current_date,
        ),
    )
    registrar.register(
        "source.narrative_verify",
        NarrativeVerifyHandler(
            reader=dependencies.reader,
            provider_policy_loader=dependencies.provider_policy_loader,
            current_date=dependencies.current_date,
        ),
    )


__all__ = [
    "CatalogPromptReviewLoader",
    "HandlerRegistrar",
    "NarrativeRuntimeDependencies",
    "register_narrative_handlers",
]
