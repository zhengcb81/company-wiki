"""Body text column lanes (multi-column / bilingual layouts).

Cuts are learned from the whole document's lane candidates so a sparse page
can reuse the gutter evidence of its siblings; lane *groups* stay per page.
Full-width running headers, edge furniture and cross-column tables never
split a lane and are never forced into one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from bisect import bisect_right
from hashlib import sha256
import json
from typing import Any

from .contract import Page, Unit, require_bbox
from company_wiki.document_normalization.table_shapes import has_unbound_numeric_cells


@dataclass
class LaneLayout:
    lanes: list[list[Unit]] = field(default_factory=list)  # left to right
    spanning: list[Unit] = field(default_factory=list)
    confidence: str = "unknown"
    basis: list = field(default_factory=list)
    cuts: list[float] = field(default_factory=list)
    single_body: list[Unit] = field(default_factory=list)
    single_body_basis: list[str] = field(default_factory=list)


def observe_single_body_lane(page: Page, eligible_ids: set[str], budget
                             ) -> tuple[list[Unit], list[str]]:
    """Positive page-wide body-band evidence; absence of a gutter is insufficient.

    Use original block geometry, never sentence/word multiplicity. Unknown or
    overlapping source geometry cannot certify a single reading lane. This is
    a separate observation, leaving the frozen numeric text_column wire intact.
    """
    if not page.width or not page.height:
        return [], []
    members, boxes, frames, sizes = [], set(), set(), []
    for unit in page.units:
        budget.charge()
        if unit.kind not in {"paragraph", "heading"}:
            continue
        if unit.deferred or unit.bbox is None:
            return [], []
        if _in_edge_zone(unit):
            continue
        frame = unit.geometry_frame
        coordinate, rotation = frame.get("coordinate_frame"), frame.get("rotation")
        if (coordinate not in {"dict", "rawdict", "text", "words", "span"}
                or type(rotation) is not int or rotation not in {0, 90, 180, 270}):
            return [], []
        frames.add((coordinate, rotation))
        budget.charge(1 + len(unit.text))
        if unit.unit_id not in eligible_ids or has_unbound_numeric_cells(unit.text):
            continue
        members.append(unit)
        boxes.add(require_bbox(unit))
        if unit.font_size:
            sizes.append(unit.font_size)
    if len(frames) != 1 or len(boxes) < 4 or not sizes:
        return [], []
    budget.charge(1 + len(boxes) * max(1, len(boxes).bit_length()) + len(sizes))
    ordered = sorted(boxes, key=lambda box: (box[1], box[0], box[3], box[2]))
    wide = [box for box in ordered if box[2] - box[0] >= page.width * 0.5]
    if len(wide) < 4 or wide[-1][3] - wide[0][1] < page.height * 0.4:
        return [], []
    size = sorted(sizes)[len(sizes) // 2]
    left, right = min(box[0] for box in wide), max(box[2] for box in wide)
    # A min/max union always contains its own boxes and proves nothing about a
    # lane. Require a substantial common body band; native nested indentation
    # and ragged right edges need not have identical left/right margins.
    if (min(box[2] for box in wide) - max(box[0] for box in wide)
            < 0.8 * min(box[2] - box[0] for box in wide)):
        return [], []
    bottom = -1.0
    for box in ordered:
        budget.charge()
        if (box[1] < bottom - size * 0.25 or box[0] < left - size
                or box[2] > right + size):
            return [], []
        bottom = max(bottom, box[3])
    budget.charge(1 + 16 * len(ordered))
    digest = sha256(json.dumps({"frame": sorted(frames), "width": page.width,
        "height": page.height, "boxes": ordered}, sort_keys=True).encode()).hexdigest()
    return members, ["observed_single_body_lane", "four_wide_body_blocks",
                     "stable_horizontal_body_band", "nonoverlapping_vertical_body_band",
                     "page_geometry_sha256:" + digest]


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
            budget.charge(1 + len(candidates))
            layout.single_body, layout.single_body_basis = observe_single_body_lane(
                page, {unit.unit_id for unit in candidates}, budget)
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
