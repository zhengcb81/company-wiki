"""Source-text boundaries shared by structural readers, without rewriting text.

This only observes the end of one supplied source string. It does not decide
whether the statement is true, join fragments, or infer a heading or actor.
"""
from __future__ import annotations

TEXT_BOUNDARY_FEATURE_VERSION = "source-text-boundaries/1"

_HARD_TERMINALS = frozenset("。！？.!?；;")
_CLOSING_WRAPPERS = frozenset("\"'”’»›)]}）］｝】〕〉》」』〗〙〛")


def terminal_punctuation(text: str) -> str | None:
    """Return a final hard terminator before closing wrappers and whitespace.

    A single backward scan avoids allocating normalized copies or stripping
    real trailing content. Opening wrappers, colons and commas do not close a
    source sentence. The caller remains responsible for its source boundary.
    """
    index = len(text) - 1
    while index >= 0 and (text[index].isspace() or text[index] in _CLOSING_WRAPPERS):
        index -= 1
    return text[index] if index >= 0 and text[index] in _HARD_TERMINALS else None


def ends_complete_sentence(text: str) -> bool:
    """Whether the supplied text ends at an observed hard sentence boundary."""
    return terminal_punctuation(text) is not None

__all__ = [
    'ends_complete_sentence',
]
