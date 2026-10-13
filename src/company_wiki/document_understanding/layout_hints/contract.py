"""du2-layout-input/1 parsing, limits and work accounting.

Pure and deterministic: no configuration, filesystem, network or clock access.
Structural data errors raise ``ValueError``; recoverable evidence problems (bad
geometry, coordinates outside the page) become diagnostics plus deferred units.
The module never assigns source locators and never mutates the input mapping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

SCHEMA_IN = "du2-layout-input/1"
SCHEMA_OUT = "du2-layout-hints/1"

DEFAULT_LIMITS = {"max_units": 50000, "max_groups": 10000, "max_work_units": 2000000}

GEOMETRY_EPS = 0.01


@dataclass
class WorkBudget:
    """Accumulates *actual* work units; never raises external budgets."""

    max_work_units: int
    used: int = 0
    exhausted: bool = False

    def charge(self, n: int = 1) -> bool:
        """Count ``n`` units of work.  False once the ceiling is passed."""
        if self.exhausted:
            return False
        self.used += n
        if self.used > self.max_work_units:
            self.exhausted = True
            return False
        return True


@dataclass(frozen=True)
class Unit:
    unit_id: str
    ordinal: int
    locator: Any
    text: str
    bbox: tuple[float, float, float, float] | None
    font_size: float | None
    font_weight: str | None
    bold: bool
    kind: str
    hints: Mapping[str, Any]
    page_value: int | None
    page_index: int
    page_width: float | None
    page_height: float | None
    deferred_reason: str | None = None

    @property
    def deferred(self) -> bool:
        return self.deferred_reason is not None

    @property
    def has_geometry(self) -> bool:
        return self.bbox is not None

    @property
    def height(self) -> float | None:
        if self.bbox is None:
            return None
        return self.bbox[3] - self.bbox[1]

    @property
    def y_center(self) -> float | None:
        if self.bbox is None:
            return None
        return (self.bbox[1] + self.bbox[3]) / 2.0

    @property
    def x_center(self) -> float | None:
        if self.bbox is None:
            return None
        return (self.bbox[0] + self.bbox[2]) / 2.0


@dataclass
class Page:
    page_value: int | None
    page_index: int
    width: float | None
    height: float | None
    units: list[Unit] = field(default_factory=list)


@dataclass
class Doc:
    source_ref: Mapping[str, Any]
    coverage: Mapping[str, Any]
    pages: list[Page]
    units: list[Unit]
    limits: dict
    budget: WorkBudget
    diagnostics: list[dict] = field(default_factory=list)
    deferred_ids: list[str] = field(default_factory=list)
    processed_ids: list[str] = field(default_factory=list)

    def add_diagnostic(self, code: str, unit_ids, detail: str) -> None:
        self.diagnostics.append({"code": code, "unit_ids": sorted(set(unit_ids)), "detail": detail})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def resolve_limits(limits: Mapping[str, None] | None) -> dict:
    """Caller limits may TIGHTEN the defaults, never widen them."""
    resolved = dict(DEFAULT_LIMITS)
    if limits is not None:
        _require(isinstance(limits, Mapping), "limits must be a mapping")
        for key in ("max_units", "max_groups", "max_work_units"):
            if key in limits and limits[key] is not None:
                value = limits[key]
                _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"limits[{key}] must be an int >= 0")
                resolved[key] = min(int(value), DEFAULT_LIMITS[key])
    return resolved


def parse_observation(observation: Mapping[str, Any], *, limits: Mapping[str, None] | None = None) -> Doc:
    _require(isinstance(observation, Mapping), "observation must be a mapping")
    _require(observation.get("schema_version") == SCHEMA_IN, f"schema_version must be {SCHEMA_IN}")
    source_ref = observation.get("source_ref")
    _require(isinstance(source_ref, Mapping), "source_ref must be a mapping (opaque passthrough)")
    coverage = observation.get("coverage")
    _require(isinstance(coverage, Mapping), "coverage must be a mapping")
    pages_raw = observation.get("pages")
    _require(isinstance(pages_raw, list), "pages must be a list")

    resolved = resolve_limits(limits)
    budget = WorkBudget(max_work_units=resolved["max_work_units"])
    doc = Doc(
        source_ref=dict(source_ref),
        coverage=dict(coverage),
        pages=[],
        units=[],
        limits=resolved,
        budget=budget,
    )

    seen_ids: set = set()
    seen_ordinals: set = set()

    for page_index, page_raw in enumerate(pages_raw):
        _require(isinstance(page_raw, Mapping), f"pages[{page_index}] must be a mapping")
        width = page_raw.get("width")
        height = page_raw.get("height")
        _require(width is None or _is_number(width), f"pages[{page_index}].width must be a number or null")
        _require(height is None or _is_number(height), f"pages[{page_index}].height must be a number or null")
        width = float(width) if width is not None else None
        height = float(height) if height is not None else None
        units_raw = page_raw.get("units")
        _require(isinstance(units_raw, list), f"pages[{page_index}].units must be a list")
        page = Page(
            page_value=page_raw.get("page"),
            page_index=page_index,
            width=width,
            height=height,
        )
        ordered = []
        for pos, unit_raw in enumerate(units_raw):
            _require(isinstance(unit_raw, Mapping), f"units[{pos}] must be a mapping")
            unit_id = unit_raw.get("unit_id")
            _require(isinstance(unit_id, str) and unit_id, f"units[{pos}].unit_id must be a non-empty string")
            _require(unit_id not in seen_ids, f"duplicate unit_id: {unit_id}")
            seen_ids.add(unit_id)
            ordinal = unit_raw.get("ordinal")
            _require(isinstance(ordinal, int) and not isinstance(ordinal, bool) and ordinal >= 0, f"{unit_id}.ordinal must be an int >= 0")
            _require(ordinal not in seen_ordinals, f"duplicate ordinal: {ordinal}")
            seen_ordinals.add(ordinal)
            text = unit_raw.get("text")
            _require(isinstance(text, str), f"{unit_id}.text must be a string")
            locator = unit_raw.get("locator")
            _require(locator is None or isinstance(locator, str), f"{unit_id}.locator must be a string or null")
            font_size = unit_raw.get("font_size")
            _require(font_size is None or _is_number(font_size), f"{unit_id}.font_size must be a number or null")
            font_weight = unit_raw.get("font_weight")
            _require(font_weight is None or isinstance(font_weight, str), f"{unit_id}.font_weight must be a string or null")
            kind = unit_raw.get("kind")
            _require(isinstance(kind, str), f"{unit_id}.kind must be a string")
            hints = unit_raw.get("upstream_hints")
            _require(hints is None or isinstance(hints, Mapping), f"{unit_id}.upstream_hints must be a mapping or null")
            bbox_raw = unit_raw.get("bbox")
            ordered.append((ordinal, unit_id, locator, text, bbox_raw, font_size, font_weight, kind, hints or {}))

        for ordinal, unit_id, locator, text, bbox_raw, font_size, font_weight, kind, hints in sorted(ordered, key=lambda item: item[0]):
            bbox: tuple[float, float, float, float] | None = None
            deferred_reason: str | None = None
            if bbox_raw is not None:
                _require(
                    isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 4 and all(_is_number(v) for v in bbox_raw),
                    f"{unit_id}.bbox must be four numbers or null",
                )
                x0, y0, x1, y1 = (float(v) for v in bbox_raw)
                if x0 > x1 or y0 > y1:
                    doc.add_diagnostic("BAD_GEOMETRY", [unit_id], "bbox bounds are inverted")
                    deferred_reason = "bad_geometry"
                elif (
                    (width is not None and (x1 > width + GEOMETRY_EPS or x0 < -GEOMETRY_EPS))
                    or (height is not None and (y1 > height + GEOMETRY_EPS or y0 < -GEOMETRY_EPS))
                ):
                    doc.add_diagnostic("COORDINATE_OUT_OF_BOUNDS", [unit_id], "bbox falls outside the declared page")
                    deferred_reason = "coordinate_out_of_bounds"
                else:
                    bbox = (x0, y0, x1, y1)
            else:
                doc.add_diagnostic("MISSING_GEOMETRY", [unit_id], "unit carries no bbox")

            size_value = float(font_size) if font_size is not None and _is_number(font_size) else None
            if size_value is not None and size_value <= 0:
                size_value = None
            weight_norm = (font_weight or "").strip().lower()
            bold = any(
                token in weight_norm
                for token in ("bold", "black", "heavy", "semibold", "demibold", "b")
            ) or any(
                token in weight_norm for token in ("600", "700", "800", "900")
            )

            unit = Unit(
                unit_id=unit_id,
                ordinal=ordinal,
                locator=locator,
                text=text,
                bbox=bbox,
                font_size=size_value,
                font_weight=font_weight,
                bold=bold,
                kind=kind,
                hints=hints,
                page_value=page.page_value,
                page_index=page_index,
                page_width=width,
                page_height=height,
                deferred_reason=deferred_reason,
            )
            page.units.append(unit)
            doc.units.append(unit)
        doc.pages.append(page)

    # caller unit ceiling: units beyond it are deferred deterministically
    over_limit = doc.units[doc.limits["max_units"]:]
    if over_limit:
        for unit in over_limit:
            if unit.deferred_reason is None:
                object.__setattr__(unit, "deferred_reason", "unit_limit_exceeded")
        doc.add_diagnostic("UNIT_LIMIT_EXCEEDED", [u.unit_id for u in over_limit], f"more than max_units={doc.limits['max_units']} units")

    for unit in doc.units:
        if unit.deferred:
            doc.deferred_ids.append(unit.unit_id)
        else:
            doc.processed_ids.append(unit.unit_id)
    return doc
