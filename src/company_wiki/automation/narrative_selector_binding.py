"""Bind actual selector capability once for raw and official runtime paths.

Custom callers declare a policy they have explicitly pinned. No callable
signature probing or retry is needed; the established call shape stays intact.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Protocol

from company_wiki.source_catalog.narrative_document import DocumentStructure, NarrativeEvidencePackage
from company_wiki.source_catalog.narrative_evidence import (
    NarrativeSelectorVersionError, resolve_narrative_selector_version, select_narrative_evidence,
)


class NarrativeSelector(Protocol):
    def __call__(self, parsed: DocumentStructure, *, title: str,
                 existing_kind: str = "unknown") -> NarrativeEvidencePackage: ...


@dataclass(frozen=True)
class BoundNarrativeSelector:
    selector: NarrativeSelector
    selector_version: str

    def __call__(self, parsed: DocumentStructure, *, title: str,
                 existing_kind: str = "unknown") -> NarrativeEvidencePackage:
        return self.selector(parsed, title=title, existing_kind=existing_kind)


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
    return BoundNarrativeSelector(selector, resolve_narrative_selector_version(selector_version))
