"""Transient script matching, separated from original evidence and locators."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from functools import lru_cache

from .narrative_candidates import EvidenceCandidate
from .narrative_document import DocumentStructure, NarrativeUnit


@lru_cache(maxsize=1)
def _converter():
    import opencc  # Existing catalog dependency, also installed by CI.

    return opencc.OpenCC("t2s.json")


def matching_text(text: str) -> str:
    """Create a match-only representation; no normalized text is persisted."""
    if not any("\u3400" <= char <= "\u9fff" for char in text):
        return text
    return str(_converter().convert(text))


def _matching_unit(unit: NarrativeUnit) -> NarrativeUnit:
    text = matching_text(unit.raw_text)
    metadata = dict(unit.metadata)
    for key in ("table_headers", "row_cells"):
        if key in metadata:
            metadata[key] = tuple(matching_text(str(v)) for v in metadata[key])
    if text == unit.raw_text and metadata == dict(unit.metadata):
        return unit
    return replace(unit, raw_text=text, metadata=metadata)


def matching_document(document: DocumentStructure) -> DocumentStructure:
    """Keep source coordinates/IDs for matching; restore originals before export."""
    return replace(document, units=tuple(_matching_unit(unit) for unit in document.units))


def original_candidates(candidates: Sequence[EvidenceCandidate], document: DocumentStructure):
    """Restore exact parsed text/metadata before hashing, budgeting and publication."""
    originals = {unit.unit_id: unit for unit in document.units}
    return tuple(replace(candidate, unit=originals[candidate.unit.unit_id]) for candidate in candidates)
