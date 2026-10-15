"""Offset-preserving matching view for operating-relation detection.

Normalization is for matching only. The view mirrors
``matching_reading_text`` (t2s script reading plus native wrapping elision)
while keeping a per-character map back to the original unit text, so every
returned ref is an exact Python slice of the untouched original — never an
offset into the converted/compacted string. Script conversion is applied
character-wise with a length-preserving fallback so the map stays 1:1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from company_wiki.document_normalization.text_matching import matching_script_text

CJK = r"[㐀-鿿]"
_CJK_RE = re.compile(CJK)
# Sentence/clause boundaries for binding. Enumeration comma 、 is NOT a
# boundary: it joins actor conjuncts handled by the subject splitter.
CLAUSE_BREAK = re.compile(r"[。！？!?；;，,]|\.(?:\s|$)")
_ABBREVIATION_END = re.compile(
    r"(?:\b(?:Ltd|Inc|Corp|Co|Mr|Mrs|Ms|Dr|Prof|vs|etc|No)\.)$", re.IGNORECASE
)
CONNECTOR_PREFIX = re.compile(
    r"^(?:並且|并且|并|且|同时|以及|随后|接着|另外|而其|而|该|其|"
    r"and|also|then|while|but|however|moreover|furthermore)\s*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MatchingView:
    """Compacted matching text plus original index per kept character."""

    text: str
    positions: tuple[int, ...]

    def to_original(self, start: int, end: int) -> tuple[int, int]:
        """Map a matching span back to the exact original span."""
        if not 0 <= start < end <= len(self.positions):
            raise ValueError("matching span out of range")
        return self.positions[start], self.positions[end - 1] + 1


def build_matching_view(text: str) -> MatchingView:
    """Length-safe script reading; elide only inter-CJK wrapping whitespace."""
    if not isinstance(text, str):
        raise TypeError("unit text must be a string")
    converted: list[str] = []
    for character in text:
        reading = matching_script_text(character)
        converted.append(reading if len(reading) == 1 else character)
    out_chars: list[str] = []
    out_positions: list[int] = []
    index = 0
    total = len(converted)
    while index < total:
        character = converted[index]
        if character.isspace():
            run_end = index
            while run_end < total and converted[run_end].isspace():
                run_end += 1
            previous_cjk = bool(out_chars) and bool(_CJK_RE.fullmatch(out_chars[-1]))
            next_cjk = run_end < total and bool(_CJK_RE.fullmatch(converted[run_end]))
            if previous_cjk and next_cjk:
                index = run_end
                continue
            for run_index in range(index, run_end):
                out_chars.append(" " if converted[run_index] in "\r\n" else converted[run_index])
                out_positions.append(run_index)
            index = run_end
            continue
        out_chars.append(character)
        out_positions.append(index)
        index += 1
    return MatchingView("".join(out_chars), tuple(out_positions))


def split_clauses(view: MatchingView) -> list[tuple[int, int]]:
    """Clause spans in matching coordinates, abbreviation-aware.

    A trailing ``Ltd.``-style dot is a name suffix, not a sentence boundary.
    """
    spans: list[tuple[int, int]] = []
    start = 0
    text = view.text
    for match in CLAUSE_BREAK.finditer(text):
        boundary = match.start()
        if match.group().startswith(".") and _ABBREVIATION_END.search(text[:boundary + 1]):
            continue
        if boundary > start:
            spans.append((start, boundary))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def strip_connector(text: str) -> tuple[str, int]:
    """Drop a leading continuation connector; return (rest, stripped length)."""
    match = CONNECTOR_PREFIX.match(text)
    if match is None:
        return text, 0
    return text[match.end():], match.end()
