"""Build transient visual context groups from replayable PDF text units."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import re

from .narrative_document import NarrativeUnit


PdfContextGroup = tuple[str, tuple[NarrativeUnit, ...], str]


@dataclass(frozen=True)
class PdfGroupRules:
    project_heading: re.Pattern[str]
    business_heading: re.Pattern[str]
    heading_only: re.Pattern[str]


def _is_heading(unit: NarrativeUnit, rules: PdfGroupRules) -> bool:
    return any(
        pattern.search(unit.raw_text) is not None
        for pattern in (
            rules.project_heading,
            rules.business_heading,
            rules.heading_only,
        )
    )


def _bbox(unit: NarrativeUnit) -> tuple[float, float, float, float] | None:
    value = unit.metadata.get("bbox")
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        return (float(value[0]), float(value[1]), float(value[2]), float(value[3]))
    except (TypeError, ValueError):
        return None


def _visually_continues(
    previous: NarrativeUnit,
    current: NarrativeUnit,
    rules: PdfGroupRules,
) -> bool:
    if previous.source_role != current.source_role:
        return False
    if _is_heading(previous, rules) or _is_heading(current, rules):
        return False
    if _same_pdf_block(previous, current):
        return True
    return _has_visual_overlap(previous, current)


def _same_pdf_block(previous: NarrativeUnit, current: NarrativeUnit) -> bool:
    previous_block = previous.metadata.get("pdf_block")
    return previous_block is not None and previous_block == current.metadata.get("pdf_block")


def _has_visual_overlap(previous: NarrativeUnit, current: NarrativeUnit) -> bool:
    previous_bbox = _bbox(previous)
    current_bbox = _bbox(current)
    if previous_bbox is None or current_bbox is None:
        return False
    vertical_gap = current_bbox[1] - previous_bbox[3]
    if vertical_gap < -1.0 or vertical_gap > 16.0:
        return False
    overlap = max(
        0.0,
        min(previous_bbox[2], current_bbox[2])
        - max(previous_bbox[0], current_bbox[0]),
    )
    narrower_width = min(
        previous_bbox[2] - previous_bbox[0],
        current_bbox[2] - current_bbox[0],
    )
    return narrower_width > 0 and overlap / narrower_width >= 0.60


def _page_units(units: Sequence[NarrativeUnit]) -> dict[int, list[NarrativeUnit]]:
    by_page: dict[int, list[NarrativeUnit]] = {}
    for unit in units:
        page = unit.coordinates.page_number
        if unit.unit_kind != "pdf_text_block" or unit.source_role == "qa_text_shadow":
            continue
        if page is not None:
            by_page.setdefault(page, []).append(unit)
    return by_page


def _clusters(
    units: Sequence[NarrativeUnit], rules: PdfGroupRules
) -> tuple[tuple[NarrativeUnit, ...], ...]:
    ordered = sorted(
        units,
        key=lambda unit: (
            unit.coordinates.paragraph_index or 0,
            unit.coordinates.char_start or 0,
        ),
    )
    result: list[list[NarrativeUnit]] = []
    for unit in ordered:
        if result and _visually_continues(result[-1][-1], unit, rules):
            result[-1].append(unit)
        else:
            result.append([unit])
    return tuple(tuple(cluster) for cluster in result)


def _separator(previous: NarrativeUnit, current: NarrativeUnit) -> str:
    same_block = previous.metadata.get("pdf_block") == current.metadata.get("pdf_block")
    contiguous = (
        same_block
        and previous.metadata.get("block_char_end")
        == current.metadata.get("block_char_start")
    )
    return "" if contiguous or current.language.startswith("zh") else " "


def _cluster_text(members: Sequence[NarrativeUnit]) -> str:
    pieces = [members[0].raw_text]
    for previous, current in zip(members, members[1:], strict=False):
        pieces.append(_separator(previous, current) + current.raw_text)
    return "".join(pieces)


def _context_group(page: int, members: tuple[NarrativeUnit, ...]) -> PdfContextGroup:
    member_key = "|".join(unit.unit_id for unit in members)
    identity = hashlib.sha256(
        f"{members[0].source_id}:{page}:{member_key}".encode("utf-8")
    ).hexdigest()
    return (
        f"urn:company-wiki:context-group:sha256:{identity}",
        members,
        _cluster_text(members),
    )


def build_pdf_context_groups(
    units: Sequence[NarrativeUnit], rules: PdfGroupRules
) -> tuple[PdfContextGroup, ...]:
    """Group visual continuations without replacing replayable unit locators."""
    groups: list[PdfContextGroup] = []
    for page, page_units in sorted(_page_units(units).items()):
        groups.extend(_context_group(page, members) for members in _clusters(page_units, rules))
    return tuple(groups)


__all__ = ["PdfContextGroup", "PdfGroupRules", "build_pdf_context_groups"]
