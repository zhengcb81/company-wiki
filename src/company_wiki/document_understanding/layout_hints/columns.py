"""Body text column lanes (multi-column / bilingual layouts).

Cuts are learned from the whole document's lane candidates so a sparse page
can reuse the gutter evidence of its siblings; lane *groups* stay per page.
Full-width running headers, edge furniture and cross-column tables never
split a lane and are never forced into one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from bisect import bisect_right
from typing import Any

from .contract import Page, Unit, require_bbox


@dataclass
class LaneLayout:
    lanes: list[list[Unit]] = field(default_factory=list)  # left to right
    spanning: list[Unit] = field(default_factory=list)
    confidence: str = "unknown"
    basis: list = field(default_factory=list)
    cuts: list[float] = field(default_factory=list)


def _in_edge_zone(unit: Unit) -> bool:
    """Running head/foot zone: never column evidence, even without repetition."""
    if not unit.page_height:
        return False
    return (
        require_bbox(unit)[3] <= unit.page_height * 0.08
        or require_bbox(unit)[1] >= unit.page_height * 0.90
    )


def _usable(unit: Unit) -> bool:
    return unit.bbox is not None and not unit.deferred and not _in_edge_zone(unit)


def compute_cuts(units: list[Unit], page_width: float, budget) -> list[float]:
    if len(units) < 4 or not page_width:
        return []
    gap_min = max(10.0, 0.02 * page_width)
    ordered = sorted(units, key=lambda u: (require_bbox(u)[0], require_bbox(u)[2], u.ordinal))
    islands: list[list[Any]] = []
    for unit in ordered:
        budget.charge()
        box = require_bbox(unit)
        if islands and box[0] <= islands[-1][1] + gap_min:
            islands[-1][1] = max(islands[-1][1], box[2])
            islands[-1][2] += 1
        else:
            islands.append([box[0], box[2], 1])
    cuts = []
    pending = 0
    remaining = len(ordered)
    for current, next_island in zip(islands, islands[1:]):
        budget.charge()
        pending += current[2]
        remaining -= current[2]
        if pending >= 2 and remaining >= 2:
            cuts.append((current[1] + next_island[0]) / 2.0)
            pending = 0
    return cuts


def usable_units(units: list[Unit]) -> list[Unit]:
    return [unit for unit in units if _usable(unit)]


def detect_document_lanes(
    page_units: list[tuple[Page, list[Unit]]], budget
) -> list[LaneLayout]:
    pooled = [unit for _page, units in page_units for unit in units if _usable(unit)]
    widths = [page.width for page, _units in page_units if page.width]
    page_width = max(widths) if widths else 595.0
    cuts = compute_cuts(pooled, page_width, budget)

    layouts: list[LaneLayout] = []
    for page, units in page_units:
        layout = LaneLayout(cuts=list(cuts))
        candidates = [unit for unit in units if _usable(unit)]
        if not cuts:
            layout.basis = [
                "no_column_gap" if len(candidates) >= 4 else "insufficient_geometry"
            ]
            layouts.append(layout)
            continue
        for unit in candidates:
            budget.charge(1)
            left = bisect_right(cuts, require_bbox(unit)[0])
            right = bisect_right(cuts, require_bbox(unit)[2] - 1e-9)
            if right > left:
                layout.spanning.append(unit)
                continue
            bucket = left
            while len(layout.lanes) <= bucket:
                layout.lanes.append([])
            layout.lanes[bucket].append(unit)
        layout.lanes = [
            sorted(members, key=lambda u: (require_bbox(u)[1], require_bbox(u)[0], u.ordinal))
            for members in layout.lanes
            if members
        ]
        layout.basis = ["lane_gap", "document_wide_cuts"]
        if _parallel_bands(layout, budget):
            layout.basis.append("parallel_bands")
        layout.confidence = "high" if len(cuts) == 1 else "medium"
        layouts.append(layout)
    return layouts


def _parallel_bands(layout: LaneLayout, budget) -> bool:
    if len(layout.lanes) != 2:
        return False

    def tops(units):
        return [(require_bbox(u)[1] + require_bbox(u)[3]) / 2.0 for u in units]

    left = tops(layout.lanes[0])
    right = tops(layout.lanes[1])
    if not left or not right:
        return False
    left.sort()
    right.sort()
    shared = 0
    cursor = 0
    for value in left:
        budget.charge()
        while cursor < len(right) and right[cursor] < value - 6.0:
            budget.charge()
            cursor += 1
        if cursor < len(right) and right[cursor] <= value + 6.0:
            shared += 1
    return shared >= max(1, int(0.5 * min(len(left), len(right))))
