"""Bounding-box geometry: line bands, cells and column slots.

Near-linear by construction: units are processed per page in sorted order and
cell/cluster comparisons stay local; the shared :class:`WorkBudget` counts the
actual comparisons performed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        boxes = [u.bbox for u in self.units if u.bbox is not None]
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )

    @property
    def y_center(self) -> float:
        ys = [(u.bbox[1] + u.bbox[3]) / 2.0 for u in self.units if u.bbox is not None]
        return sum(ys) / len(ys)

    @property
    def mean_height(self) -> float:
        heights = [band_height(u) for u in self.units]
        return sum(heights) / len(heights)

    @property
    def text(self) -> str:
        return " ".join(unit_text(u) for u in sorted(self.units, key=lambda u: (u.bbox[0], u.ordinal)))


@dataclass
class Cell:
    members: list[Unit] = field(default_factory=list)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        boxes = [u.bbox for u in self.members if u.bbox is not None]
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )

    @property
    def text(self) -> str:
        return " ".join(unit_text(u) for u in sorted(self.members, key=lambda u: (u.bbox[0], u.ordinal)))

    @property
    def font_size(self) -> float | None:
        sizes = [u.font_size for u in self.members if u.font_size]
        return max(sizes) if sizes else None


@dataclass
class ColumnSlot:
    index: int
    bbox: tuple[float, float, float, float]


def band_geometry_units(units: list[Unit], budget: WorkBudget) -> list[Band]:
    """Cluster geometry-bearing units into visual line bands."""
    usable = [u for u in units if u.bbox is not None and not u.deferred]
    ordered = sorted(usable, key=lambda u: ((u.bbox[1] + u.bbox[3]) / 2.0, u.bbox[0], u.ordinal))
    bands: list[Band] = []
    for unit in ordered:
        if not budget.charge(1):
            break
        if not bands:
            bands.append(Band(units=[unit]))
            continue
        band = bands[-1]
        tolerance = BAND_TOLERANCE * max(unit.bbox[3] - unit.bbox[1], band.mean_height, MIN_BAND_HEIGHT)
        if abs(unit.y_center - band.y_center) <= tolerance:
            band.units.append(unit)
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
                previous.members.append(unit)
                continue
        cells.append(Cell(members=[unit]))
    return cells


def cluster_column_slots(data_cells: list[Cell], budget: WorkBudget) -> list[ColumnSlot]:
    """Cluster data cells by horizontal interval overlap into column slots.

    Only cells of quantity-bearing rows seed the slots, so spanning header
    cells can never merge two neighbouring quantity columns.  Merging uses
    cluster intervals only (never cell pairs) to stay near-linear.
    """
    if not data_cells:
        return []
    ordered = sorted(data_cells, key=lambda cell: (cell.bbox[0], cell.bbox[2]))
    cluster_boxes: list[list] = []  # [interval, members]
    for cell in ordered:
        budget.charge(1)
        box = cell.bbox
        placed = False
        for cluster in cluster_boxes:
            budget.charge(1)
            if _intervals_link(box, cluster[0]):
                cluster[1].append(cell)
                cluster[0] = (
                    min(cluster[0][0], box[0]),
                    min(cluster[0][1], box[1]),
                    max(cluster[0][2], box[2]),
                    max(cluster[0][3], box[3]),
                )
                placed = True
                break
        if not placed:
            cluster_boxes.append([box, [cell]])

    merged = True
    while merged:  # transitive closure over cluster interval overlap
        merged = False
        for i in range(len(cluster_boxes)):
            for j in range(i + 1, len(cluster_boxes)):
                budget.charge(1)
                if _intervals_link(cluster_boxes[i][0], cluster_boxes[j][0]):
                    cluster_boxes[i][1].extend(cluster_boxes[j][1])
                    cluster_boxes[i][0] = (
                        min(cluster_boxes[i][0][0], cluster_boxes[j][0][0]),
                        min(cluster_boxes[i][0][1], cluster_boxes[j][0][1]),
                        max(cluster_boxes[i][0][2], cluster_boxes[j][0][2]),
                        max(cluster_boxes[i][0][3], cluster_boxes[j][0][3]),
                    )
                    del cluster_boxes[j]
                    merged = True
                    break
            if merged:
                break

    boxes = [cluster[0] for cluster in cluster_boxes]
    slots: list[ColumnSlot] = []
    for order, box in sorted(enumerate(boxes), key=lambda item: (item[1][0], item[1][2], item[0])):
        slots.append(ColumnSlot(index=order, bbox=box))
    return [ColumnSlot(index=position, bbox=slot.bbox) for position, slot in enumerate(slots)]


def _intervals_link(box_a: tuple, box_b: tuple) -> bool:
    overlap = min(box_a[2], box_b[2]) - max(box_a[0], box_b[0])
    if overlap <= 0.5:
        return False
    width_a = max(box_a[2] - box_a[0], 1.0)
    width_b = max(box_b[2] - box_b[0], 1.0)
    return overlap >= max(2.0, 0.25 * min(width_a, width_b))


def _slot_overlap(slot: ColumnSlot, box: tuple[float, float, float, float]) -> float:
    return min(slot.bbox[2], box[2]) - max(slot.bbox[0], box[0])


def assign_cell_columns(cell: Cell, slots: list[ColumnSlot]) -> tuple[int | None, int | None]:
    """Return (column, column_span).  span covers every slot the cell overlaps."""
    if not slots:
        return None, None
    box = cell.bbox
    covered = [slot for slot in slots if _slot_overlap(slot, box) > 0.5]
    if covered:
        covered.sort(key=lambda slot: slot.index)
        span = len(covered)
        return covered[0].index, (span if span > 1 else 1)
    nearest = min(slots, key=lambda slot: min(abs(slot.bbox[0] - box[0]), abs(slot.bbox[2] - box[2])))
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
