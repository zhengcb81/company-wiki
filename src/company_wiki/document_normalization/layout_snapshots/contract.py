"""``du-layout-snapshot/1`` contract: schema validation and page/frame parsing.

Structural data errors raise ``ValueError``; recoverable evidence problems
(unknown frame, illegal bbox, wrong page, missing unit) become diagnostics that
the projection turns into partial coverage.  The contract never mutates the input
and never rewrites a locator or unit id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .identity import (
    Frame,
    WorkBudget,
    legal_bbox,
    normalize_frame,
    resolve_limits,
)

SNAPSHOT_SCHEMA = "du-layout-snapshot/1"
PROJECTION_SCHEMA = "du-layout-projection/1"
FEATURE_VERSION = "du3-geometry/1"

GEOMETRY_EPS = 0.05


@dataclass
class Binding:
    unit_id: Any
    bbox: tuple[float, float, float, float] | None
    words: list = field(default_factory=list)
    cells: list = field(default_factory=list)
    font_runs: list = field(default_factory=list)
    row_cells: list = field(default_factory=list)
    source: Any = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class PageEnvelope:
    page_no: Any
    frame: Frame
    bindings: list[Binding] = field(default_factory=list)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _optional_size(value: Any) -> float | None:
    from .identity import _is_number

    return float(value) if _is_number(value) and float(value) > 0 else None


def validate_snapshot(snapshot: Mapping[str, Any], *, limits: Mapping[str, Any] | None = None,
                      work_budget: WorkBudget | None = None):
    """Validate the snapshot wire and return ``(pages, resolved_limits, budget)``.

    Raises ``ValueError`` for structural problems (wrong schema, malformed pages).
    Recoverable binding/geometry problems are kept on the returned envelopes and
    surfaced later as diagnostics.
    """
    _require(isinstance(snapshot, Mapping), "snapshot must be a mapping")
    _require(
        snapshot.get("schema_version") == SNAPSHOT_SCHEMA,
        f"schema_version must be {SNAPSHOT_SCHEMA}",
    )
    pages_raw = snapshot.get("pages")
    _require(isinstance(pages_raw, list), "pages must be a list")
    assert isinstance(pages_raw, list)

    resolved = resolve_limits(limits)
    budget = (work_budget.scoped(resolved["max_work_units"]) if work_budget is not None
              else WorkBudget(max_work_units=resolved["max_work_units"]))

    pages: list[PageEnvelope] = []
    for index, page_raw in enumerate(pages_raw):
        _require(isinstance(page_raw, Mapping), f"pages[{index}] must be a mapping")
        width = page_raw.get("width")
        height = page_raw.get("height")

        dict_w = _optional_size(page_raw.get("dict_width"))
        dict_h = _optional_size(page_raw.get("dict_height"))
        dict_size = (dict_w, dict_h) if dict_w is not None and dict_h is not None else None
        rect_w = _optional_size(page_raw.get("rect_width"))
        rect_h = _optional_size(page_raw.get("rect_height"))
        rect_size = (rect_w, rect_h) if rect_w is not None and rect_h is not None else None
        frame = normalize_frame(
            coordinate_frame=page_raw.get("coordinate_frame"),
            rotation=page_raw.get("rotation"),
            width=width,
            height=height,
            dict_size=dict_size,
            rect_size=rect_size,
            has_transform="transform" in page_raw and page_raw.get("transform") is not None,
        )

        bindings_raw = page_raw.get("bindings")
        _require(isinstance(bindings_raw, list), f"pages[{index}].bindings must be a list")
        bindings: list[Binding] = []
        for b_index, binding_raw in enumerate(bindings_raw):
            _require(
                isinstance(binding_raw, Mapping),
                f"pages[{index}].bindings[{b_index}] must be a mapping",
            )
            binding_unit_id = binding_raw.get("unit_id")
            _require(
                isinstance(binding_unit_id, str) and bool(binding_unit_id),
                f"pages[{index}].bindings[{b_index}].unit_id must be a non-empty string",
            )
            assert isinstance(binding_unit_id, str)
            bbox = legal_bbox(binding_raw.get("bbox"))
            bindings.append(
                Binding(
                    unit_id=binding_unit_id,
                    bbox=bbox,
                    words=list(binding_raw.get("words") or []),
                    cells=list(binding_raw.get("cells") or []),
                    font_runs=list(binding_raw.get("font_runs") or []),
                    row_cells=list(binding_raw.get("row_cells") or []),
                    source=binding_raw.get("source"),
                    raw=dict(binding_raw),
                )
            )
        pages.append(PageEnvelope(page_no=page_raw.get("page"), frame=frame, bindings=bindings))
    return pages, resolved, budget


def in_page_bounds(
    bbox: tuple[float, float, float, float], frame: Frame
) -> bool:
    """A bbox is in-bounds only when the frame size is known and it fits."""
    if frame.width is None or frame.height is None:
        return False
    x0, y0, x1, y1 = bbox
    return (
        x0 >= -GEOMETRY_EPS
        and y0 >= -GEOMETRY_EPS
        and x1 <= frame.width + GEOMETRY_EPS
        and y1 <= frame.height + GEOMETRY_EPS
    )


__all__ = [
    "Binding",
    "FEATURE_VERSION",
    "GEOMETRY_EPS",
    "PROJECTION_SCHEMA",
    "PageEnvelope",
    "SNAPSHOT_SCHEMA",
    "in_page_bounds",
    "validate_snapshot",
]
