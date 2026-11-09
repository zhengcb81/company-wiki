"""Public, bounded signals for operating-state qualifiers.

The detailed regex grammar stays private to this package. Consumers receive
immutable flags and remain responsible for their own source scope and context.
These flags nominate temporal/polarity restrictions; they do not prove an
operating event or decide whether a claim is true.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import patterns as _patterns


@dataclass(frozen=True, slots=True)
class OperatingQualifiers:
    planned: bool
    negated: bool
    conditional: bool


def classify_qualifiers(text: str) -> OperatingQualifiers:
    """Return narrow qualifier-presence signals for one text fragment."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return OperatingQualifiers(
        planned=_patterns.PLANNED_QUAL.search(text) is not None,
        negated=_patterns.NEGATION_TOKENS.search(text) is not None,
        conditional=_patterns.CONDITIONAL.search(text) is not None,
    )


__all__ = ["OperatingQualifiers", "classify_qualifiers"]
