"""Minimal sentence-fragment completion and link boundaries (N6-CANDIDATE).

Completion only joins units that continue the same sentence inside one page,
source, role and language; section headings act as barriers. The two character
windows are the existing section-context budgets, reused here so one visual
group can never swallow a whole page into the selection.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import re

from .narrative_document import NarrativeUnit
from .narrative_visual_units import is_ocr_unit, ocr_continues


PROJECT_CHARACTER_WINDOW = 1_600
BUSINESS_CHARACTER_WINDOW = 1_200
MAX_COMPLETION_UNITS = 8

_ENDS_SENTENCE = re.compile(r"[。！？!?；;.]$")


def ends_sentence(text: str) -> bool:
    return _ENDS_SENTENCE.search(text.strip()) is not None


def linkable(left: NarrativeUnit, right: NarrativeUnit) -> bool:
    if is_ocr_unit(left) or is_ocr_unit(right):
        return ocr_continues(left, right)
    return (
        left.source_id == right.source_id
        and left.source_role == right.source_role
        and left.language == right.language
        and left.parser_name == right.parser_name
        and left.parser_version == right.parser_version
        and left.coordinates.page_number == right.coordinates.page_number
        and all(
            left.metadata.get(key) == right.metadata.get(key)
            for key in (
                "qa_group_id", "qa_parent_id", "qa_question_number",
                "speaker", "speaker_title", "section",
            )
        )
    )


def members_linkable(members: Sequence[NarrativeUnit]) -> bool:
    if not members:
        return False
    first = members[0]
    if any(is_ocr_unit(member) for member in members):
        return all(linkable(a, b) for a, b in zip(members, members[1:], strict=False))
    return all(linkable(first, member) for member in members[1:])


def completion_indices(
    members: Sequence[NarrativeUnit],
    hit_index: int,
    *,
    barrier: Callable[[NarrativeUnit], bool],
) -> tuple[int, ...]:
    """Return the minimal sentence-fragment range around one hit member."""
    count = len(members)
    if not 0 <= hit_index < count:
        return ()
    start = hit_index
    end = hit_index
    while start > 0 and end - start + 1 < MAX_COMPLETION_UNITS:
        prefix = members[start - 1]
        if barrier(prefix) or not linkable(prefix, members[start]):
            break
        if ends_sentence(prefix.raw_text):
            break
        start -= 1
        if end - start + 1 >= MAX_COMPLETION_UNITS:
            break
    while end + 1 < count and end - start + 1 < MAX_COMPLETION_UNITS:
        follower = members[end + 1]
        if barrier(follower) or not linkable(members[end], follower):
            break
        if ends_sentence(members[end].raw_text):
            break
        end += 1
        if end - start + 1 >= MAX_COMPLETION_UNITS:
            break
    return tuple(range(start, end + 1))


__all__ = [
    "BUSINESS_CHARACTER_WINDOW",
    "MAX_COMPLETION_UNITS",
    "PROJECT_CHARACTER_WINDOW",
    "completion_indices",
    "ends_sentence",
    "linkable",
    "members_linkable",
]
