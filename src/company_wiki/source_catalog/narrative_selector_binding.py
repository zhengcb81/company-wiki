"""Bind actual selector capability once for raw and official runtime paths.

Custom callers declare a policy they have explicitly pinned. No callable
signature probing or retry is needed; the established call shape stays intact.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Protocol
from collections.abc import Callable
from company_wiki.resource_budget import WorkBudget

from company_wiki.document_model.narrative import DocumentStructure, NarrativeEvidencePackage
from .narrative_evidence import (
    NarrativeSelectorVersionError, resolve_narrative_selector_version, select_narrative_evidence,
)

if TYPE_CHECKING:
    from .narrative_reading import ReadingInspection


class NarrativeSelector(Protocol):
    def __call__(self, parsed: DocumentStructure, *, title: str,
                 existing_kind: str = "unknown") -> NarrativeEvidencePackage: ...


class _BudgetedSelector(Protocol):
    def __call__(self, parsed: DocumentStructure, *, title: str, existing_kind: str,
                 work_budget: WorkBudget | None) -> NarrativeEvidencePackage: ...


@dataclass(frozen=True, slots=True)
class BoundNarrativeSelector:
    __select: _BudgetedSelector
    selector_version: str

    def __call__(self, parsed: DocumentStructure, *, title: str,
                 existing_kind: str = "unknown",
                 work_budget: WorkBudget | None = None) -> NarrativeEvidencePackage:
        return self.__select(parsed, title=title, existing_kind=existing_kind, work_budget=work_budget)


def bind_narrative_selector(selector: NarrativeSelector | None = None, *,
                            selector_version: str | None = None) -> BoundNarrativeSelector:
    """Resolve a supported policy and preserve an explicitly declared custom pin."""
    if isinstance(selector, BoundNarrativeSelector):
        effective = resolve_narrative_selector_version(selector.selector_version)
        if selector_version is not None and resolve_narrative_selector_version(selector_version) != effective:
            raise NarrativeSelectorVersionError("NARRATIVE_SELECTOR_VERSION_CONFLICT")
        return selector
    if selector is None or selector is select_narrative_evidence:
        effective = resolve_narrative_selector_version(selector_version)
        return BoundNarrativeSelector(partial(select_narrative_evidence, selector_version=effective), effective)
    if selector_version is None:
        raise NarrativeSelectorVersionError("CUSTOM_SELECTOR_VERSION_REQUIRED")

    def custom(parsed: DocumentStructure, *, title: str, existing_kind: str,
               work_budget: WorkBudget | None) -> NarrativeEvidencePackage:
        return selector(parsed, title=title, existing_kind=existing_kind)

    return BoundNarrativeSelector(custom, resolve_narrative_selector_version(selector_version))


def bind_reading_inspection(observe: Callable[[ReadingInspection], None]) -> BoundNarrativeSelector:
    """Keep offline inspection on the current selector and its original budget."""
    from .narrative_reading import READING_SELECTOR_VERSION, select_reading_evidence

    return BoundNarrativeSelector(partial(select_reading_evidence, observe=observe), READING_SELECTOR_VERSION)


__all__ = ["BoundNarrativeSelector", "NarrativeSelector", "bind_narrative_selector", "bind_reading_inspection"]
