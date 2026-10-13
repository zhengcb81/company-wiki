"""Body text column lanes (multi-column / bilingual layouts).

Cuts are learned from the whole document's lane candidates so a sparse page
can reuse the gutter evidence of its siblings; lane *groups* stay per page.
Full-width running headers, edge furniture and cross-column tables never
split a lane and are never forced into one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contract import Page, Unit


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
    return unit.bbox[3] <= unit.page_height * 0.08 or unit.bbox[1] >= unit.page_height * 0.90


def _usable(unit: Unit) -> bool:
    return unit.bbox is not None and not unit.deferred and not _in_edge_zone(unit)


def compute_cuts(units: list[Unit], page_width: float, budget) -> list[float]:
    if len(units) < 4 or not page_width:
        return []
    gap_min = max(10.0, 0.02 * page_width)
    ordered = sorted(units, key=lambda u: (u.bbox[0], u.bbox[2], u.ordinal))
    free_gaps: list[tuple[float, float]] = []
    current_right = ordered[0].bbox[2]
    for unit in ordered[1:]:
        budget.charge(1)
        if unit.bbox[0] > current_right + gap_min:
            free_gaps.append((current_right, unit.bbox[0]))
            current_right = unit.bbox[2]
        else:
            current_right = max(current_right, unit.bbox[2])

    cuts: list[float] = []
    for left, right in sorted(free_gaps, key=lambda gap: (gap[0] - gap[1], gap[0])):
        candidate = cuts + [(left + right) / 2.0]
        groups: dict = {}
        for unit in usable_units(units):
            bucket = 0
            for cut in sorted(candidate):
                if unit.bbox[0] >= cut:
                    bucket += 1
            groups.setdefault(bucket, []).append(unit)
        if any(len(members) < 2 for members in groups.values()):
            continue
        crossing = [
            unit
            for unit in usable_units(units)
            if any(unit.bbox[0] < cut < unit.bbox[2] for cut in candidate)
        ]
        if len(crossing) < max(1, len(usable_units(units)) // 4):
            cuts = candidate
    cuts.sort()
    return cuts


def usable_units(units: list[Unit]) -> list[Unit]:
    return [unit for unit in units if _usable(unit)]


def detect_document_lanes(page_units: list[tuple[Page, list[Unit]]], budget) -> list[LaneLayout]:
    pooled = [unit for _page, units in page_units for unit in units if _usable(unit)]
    widths = [page.width for page, _units in page_units if page.width]
    page_width = max(widths) if widths else 595.0
    cuts = compute_cuts(pooled, page_width, budget)

    layouts: list[LaneLayout] = []
    for page, units in page_units:
        layout = LaneLayout(cuts=list(cuts))
        candidates = [unit for unit in units if _usable(unit)]
        if not cuts:
            layout.basis = ["no_column_gap" if len(candidates) >= 4 else "insufficient_geometry"]
            layouts.append(layout)
            continue
        for unit in candidates:
            budget.charge(1)
            if any(unit.bbox[0] < cut < unit.bbox[2] for cut in cuts):
                layout.spanning.append(unit)
                continue
            bucket = 0
            for cut in cuts:
                if unit.bbox[0] >= cut:
                    bucket += 1
            while len(layout.lanes) <= bucket:
                layout.lanes.append([])
            layout.lanes[bucket].append(unit)
        layout.lanes = [
            sorted(members, key=lambda u: (u.bbox[1], u.bbox[0], u.ordinal))
            for members in layout.lanes
            if members
        ]
        layout.basis = ["lane_gap", "document_wide_cuts"]
        if _parallel_bands(layout):
            layout.basis.append("parallel_bands")
        layout.confidence = "high" if len(cuts) == 1 else "medium"
        layouts.append(layout)
    return layouts


def _parallel_bands(layout: LaneLayout) -> bool:
    if len(layout.lanes) != 2:
        return False

    def tops(units):
        return [(u.bbox[1] + u.bbox[3]) / 2.0 for u in units]

    left = tops(layout.lanes[0])
    right = tops(layout.lanes[1])
    if not left or not right:
        return False
    shared = 0
    for value in left:
        if any(abs(value - other) <= 6.0 for other in right):
            shared += 1
    return shared >= max(1, int(0.5 * min(len(left), len(right))))
