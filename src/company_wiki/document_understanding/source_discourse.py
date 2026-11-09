"""Public, immutable discourse observations for source-reading consumers.

This module exposes observations, not the phrase patterns used to produce
them. Offsets refer to the supplied fragment's Python string positions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .operating_states import patterns as _patterns


_TRAILING_PUNCTUATION = " .。!?！?;；"


@dataclass(frozen=True, slots=True)
class SourceDiscourseObservation:
    courtesy_start: int | None
    courtesy_only: bool


def observe_source_discourse(text: str) -> SourceDiscourseObservation:
    """Observe a courtesy marker without exposing the matching regex table."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    match = _patterns.COURTESY.search(text)
    if match is None:
        return SourceDiscourseObservation(courtesy_start=None, courtesy_only=False)

    prefix = text[:match.start()].strip()
    courtesy_only = (
        (not prefix or _patterns.ISSUER_WORD.fullmatch(prefix) is not None)
        and not text[match.end():].strip(_TRAILING_PUNCTUATION)
    )
    return SourceDiscourseObservation(
        courtesy_start=match.start(),
        courtesy_only=courtesy_only,
    )


__all__ = ["SourceDiscourseObservation", "observe_source_discourse"]
