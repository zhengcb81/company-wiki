"""Validated native character/geometry views inside the existing layout engine.

Views keep original unit IDs and locators. They are temporary spatial inputs,
never new source units, evidence spans, ranking decisions or persisted text.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from math import isfinite
from typing import Any, TypeGuard

from .contract import Doc, Unit, WorkBudget
from .geometry import band_cells, band_geometry_units


@dataclass
class FineViews:
    cells: dict[str, list[Unit]] = field(default_factory=dict)
    words: dict[str, list[Unit]] = field(default_factory=dict)
    partial: bool = False
    count: int = 0
    limit_hit: bool = False


def _integer(value: Any) -> TypeGuard[int]:
    return type(value) is int and value >= 0


def _number(value: Any) -> TypeGuard[int | float]:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
    )


def _diag(doc: Doc, state: FineViews, unit: Unit, code: str, detail: str) -> None:
    state.partial = True
    if len(doc.diagnostics) < 256:
        doc.add_diagnostic(code, [unit.unit_id], detail)


def _take(doc: Doc, state: FineViews, unit: Unit) -> bool:
    doc.budget.charge()
    if state.count >= doc.limits["max_fine_elements"]:
        if not state.limit_hit:
            _diag(
                doc,
                state,
                unit,
                "FINE_ELEMENT_LIMIT_EXCEEDED",
                "native element ceiling reached; no truncated fine context published",
            )
        state.limit_hit = True
        return False
    state.count += 1
    return True


def _frame_valid(unit: Unit, record: Mapping[str, Any]) -> bool:
    frame = unit.geometry_frame
    declared = frame.get("coordinate_frame")
    actual = record.get("coordinate_frame", declared)
    rotation = frame.get("rotation", 0)
    if declared not in {"dict", "page"} or actual != declared:
        return False
    if type(rotation) is not int or rotation not in {0, 90, 180, 270}:
        return False
    # Native dict/page coordinates need no conversion merely because the PDF
    # has rotation. A rotated element must still declare its actual frame;
    # never infer that source frame from aggregate dimensions.
    if rotation and "coordinate_frame" not in record:
        return False
    return True


def _range(
    unit: Unit, record: Mapping[str, Any], budget: WorkBudget
) -> tuple[int, int] | None:
    start, end = record.get("char_start"), record.get("char_end")
    if not _integer(start) or not _integer(end) or not start < end <= len(unit.text):
        return None
    if record.get("char_alignment", "exact") != "exact":
        return None
    # Reserve before slicing/comparing the actual characters, including font
    # and span ranges. A huge declared interval cannot bypass the work ceiling.
    budget.charge(1 + (end - start) // 64)
    text = record.get("text")
    if text is not None and (not isinstance(text, str) or text != unit.text[start:end]):
        return None
    return start, end


def _box(
    unit: Unit, record: Mapping[str, Any]
) -> tuple[float, float, float, float] | None:
    values = record.get("bbox")
    if (
        not isinstance(values, (list, tuple))
        or len(values) != 4
        or not all(_number(v) for v in values)
    ):
        return None
    x0, y0, x1, y1 = map(float, values)
    if not x0 < x1 or not y0 < y1:
        return None
    if (
        x0 < -0.01
        or y0 < -0.01
        or (unit.page_width is not None and x1 > unit.page_width + 0.01)
        or (unit.page_height is not None and y1 > unit.page_height + 0.01)
    ):
        return None
    return x0, y0, x1, y1


def _geometry_view(
    doc: Doc, state: FineViews, unit: Unit, raw: Any, kind: str
) -> Unit | None:
    if not isinstance(raw, Mapping):
        _diag(
            doc, state, unit, "FINE_ELEMENT_INVALID", "native element is not an object"
        )
        return None
    interval = _range(unit, raw, doc.budget)
    if interval is None:
        _diag(
            doc,
            state,
            unit,
            "FINE_CHARACTER_ALIGNMENT_PARTIAL",
            "native range does not exactly locate original characters",
        )
        return None
    if not _frame_valid(unit, raw):
        _diag(
            doc,
            state,
            unit,
            "FINE_FRAME_UNAVAILABLE",
            "native frame/conversion proof missing or inconsistent",
        )
        return None
    box = _box(unit, raw)
    if box is None:
        _diag(
            doc,
            state,
            unit,
            "FINE_GEOMETRY_INVALID",
            "native bbox is absent, inverted or outside its declared page",
        )
        return None
    origin = {"kind": kind, "char_start": interval[0], "char_end": interval[1]}
    if kind == "cell":
        if (
            not _integer(raw.get("row"))
            or not _integer(raw.get("column"))
            or not isinstance(raw.get("table_id"), str)
            or not raw["table_id"]
        ):
            _diag(
                doc,
                state,
                unit,
                "FINE_CELL_PROVENANCE_PARTIAL",
                "cell lacks actual table/row/column identity",
            )
            return None
        origin.update(table_id=raw["table_id"], row=raw["row"], column=raw["column"])
        parent_start = raw.get("native_cell_char_start")
        parent_end = raw.get("native_cell_char_end")
        if parent_start is not None or parent_end is not None:
            if (
                not _integer(parent_start)
                or not _integer(parent_end)
                or not parent_start < parent_end
            ):
                _diag(
                    doc,
                    state,
                    unit,
                    "FINE_CELL_PROVENANCE_PARTIAL",
                    "parent cell fragment does not exactly locate the native characters",
                )
                return None
            if parent_end - parent_start != interval[1] - interval[0]:
                # Native PDF ranges precede NFC/trim; do not move their source
                # coordinates to match normalized unit character offsets.
                _diag(
                    doc,
                    state,
                    unit,
                    "FINE_CELL_CHARACTER_NORMALIZATION_PARTIAL",
                    "native parent and normalized unit have different character extents; native cell coordinates are preserved",
                )
        if raw.get("partial_cell") is True:
            _diag(
                doc,
                state,
                unit,
                "FINE_CELL_CONTEXT_PARTIAL",
                "unit is an actual fragment of a native cell; parent coordinates are preserved without claiming complete context",
            )
    return replace(
        unit,
        text=unit.text[interval[0] : interval[1]],
        bbox=box,
        hints={**unit.hints, "geometry_granularity": kind, "_fine_origin": origin},
    )


def _font_style(doc: Doc, state: FineViews, unit: Unit, records: Sequence[Any]) -> Unit:
    spans = []
    for raw in records:
        if not _take(doc, state, unit):
            return replace(unit, font_size=None, font_weight=None, bold=False)
        interval = _range(unit, raw, doc.budget) if isinstance(raw, Mapping) else None
        size = raw.get("font_size") if isinstance(raw, Mapping) else None
        weight = raw.get("font_weight") if isinstance(raw, Mapping) else None
        if (
            interval is None
            or not _number(size)
            or size <= 0
            or (weight is not None and not isinstance(weight, str))
        ):
            _diag(
                doc,
                state,
                unit,
                "FINE_FONT_COVERAGE_PARTIAL",
                "font range/size is not exact original evidence",
            )
            continue
        spans.append((interval[0], interval[1], float(size), weight))
    spans.sort()
    cursor = 0
    for start, end, _, _ in spans:
        doc.budget.charge()
        if start > cursor and unit.text[cursor:start].strip():
            break
        if start < cursor:
            # Overlapping styles cannot be counted twice or guessed by size.
            break
        cursor = end
    else:
        if not unit.text[cursor:].strip() and spans:
            total = sum(end - start for start, end, _, _ in spans)
            remaining = total / 2
            size = spans[0][2]
            for start, end, value, _weight in sorted(spans, key=lambda item: item[2]):
                remaining -= end - start
                size = value
                if remaining <= 0:
                    break
            weights = [str(weight or "").lower() for _, _, _, weight in spans]
            bold = all(
                weight
                in {
                    "bold",
                    "semibold",
                    "demibold",
                    "black",
                    "heavy",
                    "600",
                    "700",
                    "800",
                    "900",
                }
                for weight in weights
            )
            return replace(
                unit,
                font_size=size,
                font_weight="bold" if bold else "regular",
                bold=bold,
                hints={**unit.hints, "_fine_font_coverage": "exact"},
            )
    _diag(
        doc,
        state,
        unit,
        "FINE_FONT_COVERAGE_PARTIAL",
        "font ranges do not fully and uniquely cover original nonwhitespace characters",
    )
    return replace(unit, font_size=None, font_weight=None, bold=False)


def consume_fine_geometry(doc: Doc) -> FineViews:
    state = FineViews()
    replacements = {}
    for unit in doc.units:
        if unit.deferred:
            continue
        arrays = {
            name: unit.hints.get(name)
            for name in ("cells", "words", "font_runs", "spans")
        }
        declared = unit.hints.get("geometry_granularity")
        if not any(arrays.values()):
            if declared in {"cell", "word"}:
                _diag(
                    doc,
                    state,
                    unit,
                    "FINE_GEOMETRY_UNAVAILABLE",
                    "fine declared without actual native geometry",
                )
            continue
        valid_arrays = {}
        for name, items in arrays.items():
            if items is None:
                continue
            if not isinstance(items, (list, tuple)):
                _diag(
                    doc,
                    state,
                    unit,
                    "FINE_ELEMENT_INVALID",
                    "fine elements must be a native sequence",
                )
                continue
            valid_arrays[name] = items
        styled = (
            _font_style(doc, state, unit, valid_arrays["font_runs"])
            if valid_arrays.get("font_runs")
            else unit
        )
        replacements[unit.unit_id] = styled
        for name, kind in (("cells", "cell"), ("words", "word"), ("spans", "span")):
            views = []
            for raw in valid_arrays.get(name, ()):
                if not _take(doc, state, unit):
                    break
                view = _geometry_view(doc, state, styled, raw, kind)
                if view is not None:
                    views.append(view)
            if name == "cells" and views:
                # An aggregate bbox repeated as several named columns proves
                # neither a cell boundary nor a merged-cell span.
                seen: dict[tuple, int] = {}
                conflict = False
                for view in views:
                    doc.budget.charge()
                    origin = view.hints["_fine_origin"]
                    key = (origin["table_id"], origin["row"], view.bbox)
                    previous = seen.setdefault(key, origin["column"])
                    if previous != origin["column"]:
                        conflict = True
                if conflict:
                    _diag(
                        doc,
                        state,
                        unit,
                        "FINE_CELL_GEOMETRY_CONFLICT",
                        "distinct declared columns repeat the same aggregate bbox",
                    )
                else:
                    state.cells[unit.unit_id] = views
            elif name == "words" and views:
                lines = []
                for band in band_geometry_units(views, doc.budget):
                    for cell in band_cells(band, doc.budget):
                        start = min(
                            v.hints["_fine_origin"]["char_start"] for v in cell.members
                        )
                        end = max(
                            v.hints["_fine_origin"]["char_end"] for v in cell.members
                        )
                        lines.append(
                            replace(
                                styled,
                                text=unit.text[start:end],
                                bbox=cell.bbox,
                                hints={
                                    **styled.hints,
                                    "geometry_granularity": "word",
                                    "_fine_origin": {
                                        "kind": "word_line",
                                        "char_start": start,
                                        "char_end": end,
                                    },
                                },
                            )
                        )
                state.words[unit.unit_id] = lines
    if state.limit_hit:
        # All affected unit context stays coarse/partial; never emit a confident
        # table consisting of an arbitrary prefix of native fine elements.
        state.cells.clear()
        state.words.clear()
    else:
        _validate_cell_geometry(doc, state)
    doc.units = [replacements.get(unit.unit_id, unit) for unit in doc.units]
    for page in doc.pages:
        page.units = [replacements.get(unit.unit_id, unit) for unit in page.units]
    return state


def _validate_cell_geometry(doc: Doc, state: FineViews) -> None:
    """Check shared native cell identities across original units in one page."""
    seen: dict[tuple, int] = {}
    conflicts: set[tuple] = set()
    for views in state.cells.values():
        for view in views:
            doc.budget.charge()
            origin = view.hints["_fine_origin"]
            key = (view.page_index, origin["table_id"], origin["row"], view.bbox)
            previous = seen.setdefault(key, origin["column"])
            if previous != origin["column"]:
                conflicts.add(key)
    if not conflicts:
        return
    for uid, views in list(state.cells.items()):
        invalid = False
        for view in views:
            doc.budget.charge()
            origin = view.hints["_fine_origin"]
            if (
                view.page_index,
                origin["table_id"],
                origin["row"],
                view.bbox,
            ) in conflicts:
                invalid = True
        if invalid:
            _diag(
                doc,
                state,
                views[0],
                "FINE_CELL_GEOMETRY_CONFLICT",
                "distinct original units claim different columns for the same native bbox",
            )
            del state.cells[uid]
