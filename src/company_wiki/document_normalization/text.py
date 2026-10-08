"""Deterministic text normalization shared by parsing and replay.

Every unit text and every replayed text passes through the same function, so
text SHA-256 equality is meaningful across processes and parser runs.
"""

from __future__ import annotations

import re
import unicodedata

# Whitespace runs (including NBSP and newlines) collapse to one space.
_WHITESPACE_RE = re.compile(r"\s+|\u00a0+")


def normalize_text(value: str) -> str:
    """NFC-normalize, collapse whitespace, and trim; returns '' for blank."""
    if not isinstance(value, str):
        raise TypeError("text to normalize must be str")
    replaced = value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    replaced = replaced.replace("\u00a0", " ")
    collapsed = _WHITESPACE_RE.sub(" ", replaced)
    return unicodedata.normalize("NFC", collapsed).strip()


__all__ = ["normalize_text"]
