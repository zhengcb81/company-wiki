"""Bounding-box geometry: line bands, cells and column slots.

Near-linear by construction: units are processed per page in sorted order and
cell/cluster comparisons stay local; the shared :class:`WorkBudget` counts the
actual comparisons performed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush

from .contract import Unit, WorkBudget
from .text_evidence import normalize_ws

MIN_BAND_HEIGHT = 6.0
BAND_TOLERANCE = 0.8


def box_of(unit: Unit) -> tuple[float, float, float, float] | None:
    return unit.bbox


def band_height(unit: Unit) -> float:
    if unit.bbox is not None and unit.bbox[3] > unit.bbox[1]:
        return unit.bbox[3] - unit.bbox[1]
    if unit.font_size:
        return unit.font_size * 1.25
    return MIN_BAND_HEIGHT


def unit_text(unit: Unit) -> str:
    return normalize_ws(unit.text)


@dataclass
class Band:
    units: list[Unit] = field(default_factory=list)
    _bbox: tuple | None = field(default=None, init=False, repr=False)
    _y_sum: float = field(default=0.0, init=False, repr=False)
    _height_sum: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self):
        for unit in self.units:
            self._observe(unit)

    def _observe(self, unit):
        box = unit.bbox
        if box is None:
            return
        if self._bbox is None:
            self._bbox = box
        else:
            old = self._bbox
            self._bbox = (
                min(old[0], box[0]),
                min(old[1], box[1]),
                max(old[2], box[2]),
                max(old[3], box[3]),
            )
        self._y_sum += (box[1] + box[3]) / 2.0
        self._height_sum += band_height(unit)

    def append(self, unit):
        self.units.append(unit)
        self._observe(unit)

    @property
    def bbox(self):
        return self._bbox

    @property
    def y_center(self):
        return self._y_sum / len(self.units)

    @property
    def mean_height(self):
        return self._height_sum / len(self.units)

    @property
    def text(self):
        return " ".join(
            unit_text(u)
            for u in sorted(self.units, key=lambda u: (u.bbox[0], u.ordinal))
        )


@dataclass
class Cell:
    members: list[Unit] = field(default_factory=list)
    _bbox: tuple | None = field(default=None, init=False, repr=False)

    def __post_init__(self):
        for unit in self.members:
            self._observe(unit)

    def _observe(self, unit):
        box = unit.bbox
        if self._bbox is None:
            self._bbox = box
        else:
            old = self._bbox
            self._bbox = (
                min(old[0], box[0]),
                min(old[1], box[1]),
                max(old[2], box[2]),
                max(old[3], box[3]),
            )

    def append(self, unit):
        self.members.append(unit)
        self._observe(unit)

    @property
    def bbox(self):
        return self._bbox

    @property
    def text(self):
        return " ".join(
            unit_text(u)
            for u in sorted(self.members, key=lambda u: (u.bbox[0], u.ordinal))
        )

    @property
    def font_size(self):
        sizes = [u.font_size for u in self.members if u.font_size]
        return max(sizes) if sizes else None


@dataclass
class ColumnSlot:
    index: int
    bbox: tuple[float, float, float, float]


def band_geometry_units(units: list[Unit], budget: WorkBudget) -> list[Band]:
    """Cluster geometry-bearing units into visual line bands."""
    usable = [u for u in units if u.bbox is not None and not u.deferred]
    ordered = sorted(
        usable, key=lambda u: ((u.bbox[1] + u.bbox[3]) / 2.0, u.bbox[0], u.ordinal)
    )
    bands: list[Band] = []
    for unit in ordered:
        if not budget.charge(1):
            break
        if not bands:
            bands.append(Band(units=[unit]))
            continue
        band = bands[-1]
        tolerance = BAND_TOLERANCE * max(
            unit.bbox[3] - unit.bbox[1], band.mean_height, MIN_BAND_HEIGHT
        )
        if abs(unit.y_center - band.y_center) <= tolerance:
            band.append(unit)
        else:
            bands.append(Band(units=[unit]))
    for band in bands:
        band.units.sort(key=lambda u: (u.bbox[0], u.ordinal))
    return bands


def _cell_gap_tolerance(a: Unit, b: Unit) -> float:
    sizes = [s for s in (a.font_size, b.font_size) if s]
    reference = max(sizes) if sizes else 10.0
    return max(2.5, 0.5 * reference)


def band_cells(band: Band, budget: WorkBudget) -> list[Cell]:
    """Split one band into cells using whitespace gaps between spans."""
    cells: list[Cell] = []
    for unit in band.units:
        budget.charge(1)
        if cells:
            previous = cells[-1]
            prev_box = previous.bbox
            gap = unit.bbox[0] - prev_box[2]
            if gap <= _cell_gap_tolerance(previous.members[-1], unit):
                previous.append(unit)
                continue
        cells.append(Cell(members=[unit]))
    return cells


def cluster_column_slots(
    data_cells: list[Cell], budget: WorkBudget
) -> list[ColumnSlot]:
    """Sweep only horizontally active cluster intervals; all visits are charged.

    Disjoint columns never enter an all-cluster closure scan. Dense ambiguous
    overlaps are still bounded by the caller's single work budget.
    """
    ordered = sorted(data_cells, key=lambda cell: (cell.bbox[0], cell.bbox[2]))
    clusters = {}
    active = set()
    ends = []
    serial = 0
    for cell in ordered:
        budget.charge()
        box = cell.bbox
        while ends and ends[0][0] <= box[0] + 0.5:
            right, key, version = heappop(ends)
            if key in clusters and clusters[key][1] == version:
                active.discard(key)
        target = None
        for key in sorted(active):
            budget.charge()
            if _intervals_link(box, clusters[key][0]):
                target = key
                break
        if target is None:
            target = serial
            serial += 1
            clusters[target] = [box, 0]
            active.add(target)
        else:
            old = clusters[target][0]
            box = (
                min(old[0], box[0]),
                min(old[1], box[1]),
                max(old[2], box[2]),
                max(old[3], box[3]),
            )
            clusters[target][0] = box
            clusters[target][1] += 1
        changed = True
        while changed:
            changed = False
            for key in sorted(active):
                if key == target:
                    continue
                budget.charge()
                other = clusters[key][0]
                if _intervals_link(box, other):
                    box = (
                        min(box[0], other[0]),
                        min(box[1], other[1]),
                        max(box[2], other[2]),
                        max(box[3], other[3]),
                    )
                    clusters[target][0] = box
                    clusters[target][1] += 1
                    del clusters[key]
                    active.remove(key)
                    changed = True
                    break
        heappush(ends, (box[2], target, clusters[target][1]))
    return [
        ColumnSlot(index=i, bbox=box)
        for i, box in enumerate(
            sorted((c[0] for c in clusters.values()), key=lambda box: (box[0], box[2]))
        )
    ]


def _intervals_link(box_a: tuple, box_b: tuple) -> bool:
    overlap = min(box_a[2], box_b[2]) - max(box_a[0], box_b[0])
    if overlap <= 0.5:
        return False
    width_a = max(box_a[2] - box_a[0], 1.0)
    width_b = max(box_b[2] - box_b[0], 1.0)
    return overlap >= max(2.0, 0.25 * min(width_a, width_b))


def _slot_overlap(slot: ColumnSlot, box: tuple[float, float, float, float]) -> float:
    return min(slot.bbox[2], box[2]) - max(slot.bbox[0], box[0])


def assign_cell_columns(
    cell: Cell, slots: list[ColumnSlot], *, budget=None
) -> tuple[int | None, int | None]:
    """Return (column, column_span).  span covers every slot the cell overlaps."""
    if not slots:
        return None, None
    box = cell.bbox
    covered = []
    for slot in slots:
        if budget is not None:
            budget.charge()
        if _slot_overlap(slot, box) > 0.5:
            covered.append(slot)
    if covered:
        covered.sort(key=lambda slot: slot.index)
        span = len(covered)
        return covered[0].index, (span if span > 1 else 1)
    distances = []
    for slot in slots:
        if budget is not None:
            budget.charge()
        distances.append(
            (
                min(abs(slot.bbox[0] - box[0]), abs(slot.bbox[2] - box[2])),
                slot.index,
                slot,
            )
        )
    nearest = min(distances, key=lambda item: item[:2])[2]
    distance = min(abs(nearest.bbox[0] - box[0]), abs(nearest.bbox[2] - box[2]))
    if distance <= 8.0:
        return nearest.index, 1
    return None, None


def page_band_gap_median(bands: list[Band]) -> float:
    if len(bands) < 2:
        return 0.0
    gaps = []
    for previous, current in zip(bands, bands[1:]):
        gaps.append(max(0.0, current.bbox[1] - previous.bbox[3]))
    gaps.sort()
    return gaps[len(gaps) // 2]
