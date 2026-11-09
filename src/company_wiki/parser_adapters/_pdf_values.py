"""Shared value rules for the versioned PDF adapters."""

from __future__ import annotations

import re


LOW_PAGE_QUALITY_THRESHOLD = 0.30
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n+")


def require_ratio(value: object, field_name: str, *, error: type[ValueError]) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise error(f"{field_name} must be numeric")
    # This also excludes NaN and infinities without casting unbounded ints to float.
    if not 0 <= value <= 1:
        raise error(f"{field_name} must be finite in [0, 1]")
    return value


def paragraph_ranges(text: str) -> tuple[tuple[int, int, str], ...]:
    """Return trimmed paragraphs and their offsets in the supplied text."""
    segments: list[tuple[int, int]] = []
    cursor = 0
    for separator in _PARAGRAPH_BREAK.finditer(text):
        segments.append((cursor, separator.start()))
        cursor = separator.end()
    segments.append((cursor, len(text)))
    ranges: list[tuple[int, int, str]] = []
    for start, end in segments:
        segment = text[start:end]
        left = segment.lstrip(" \t\n")
        if not left:
            continue
        adjusted_start = start + len(segment) - len(left)
        raw_text = left.rstrip(" \t\n")
        ranges.append((adjusted_start, adjusted_start + len(raw_text), raw_text))
    return tuple(ranges)
