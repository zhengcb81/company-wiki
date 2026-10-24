"""One pure projection from source observations to shared layout and context.

Never reads bytes, opens a source, allocates a raw unit/locator, or changes text.
A missing geometry capability remains a diagnostic; original text stays readable.
"""

from __future__ import annotations
from copy import deepcopy
from math import isfinite
from typing import Any, Mapping
from .layout_hints import derive_layout_hints, LAYOUT_HINTS_VERSION
from .layout_hints.contract import WorkBudget, WorkBudgetExceeded


def _number(value):
    return (
        float(value)
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and value > 0
        else None
    )


def _deferred_layout(observation: Mapping, budget: WorkBudget) -> dict:
    """A thin unknown result: no enumeration to describe work we did not do."""
    return {"schema_version": "du2-layout-hints/1", "feature_version": LAYOUT_HINTS_VERSION,
            "source_ref": dict(observation["source_ref"]), "unit_hints": [], "groups": [],
            "relations": [], "reading_order": [],
            "coverage": {"complete": False, "processed_unit_count": 0,
                         "deferred_unit_ids": [], "unobserved_unit_count": len(observation.get("units", ()))},
            "diagnostics": [{"code": "WORK_BUDGET_EXCEEDED", "unit_ids": [],
                             "detail": "layout enhancement deferred; source text remains available"},
                            {"code": "WORK_UNITS", "unit_ids": [], "detail": str(budget.used)}]}


def _overlay_observation(observation: Mapping, budget: WorkBudget) -> dict:
    budget.charge()
    result = dict(observation)
    result["metadata"] = dict(observation.get("metadata") or {})
    result["units"] = []
    for unit in observation.get("units", ()):
        budget.charge()
        layout, hints = unit.get("layout") or {}, unit.get("hints") or {}
        budget.charge(len(layout) + len(hints))
        result["units"].append({**unit, "layout": dict(layout), "hints": dict(hints)})
    return result


def apply_layout_hints(observation: Mapping, *, limits=None, work_budget: WorkBudget | None = None) -> tuple[Mapping, dict]:
    # Standalone retains the independent mutable return. The composed path
    # borrows source-owned text/fine arrays and overlays only modified fields.
    try:
        result = (deepcopy(dict(observation)) if work_budget is None
                  else _overlay_observation(observation, work_budget))
        return _apply_layout(result, limits=limits, work_budget=work_budget)
    except WorkBudgetExceeded:
        if work_budget is None:
            raise
        return observation, _deferred_layout(observation, work_budget)


def _apply_layout(result, *, limits, work_budget):
    pages: dict[int | None, dict[str, Any]] = {}
    diagnostics = []
    missing = []
    conflicting_dimensions = set()
    for unit in result.get("units", ()):
        if work_budget is not None:
            work_budget.charge()
        layout = unit.get("layout") or {}
        hints = unit.get("hints") or {}
        page = unit.get("page")
        width = _number(layout.get("page_width"))
        height = _number(layout.get("page_height"))
        envelope = pages.setdefault(
            page, {"page": page, "width": width, "height": height, "units": []}
        )
        for key, value in (("width", width), ("height", height)):
            if (page, key) in conflicting_dimensions:
                envelope[key] = None
            elif value is not None and envelope[key] is None:
                envelope[key] = value
            elif value is not None and envelope[key] != value:
                diagnostics.append(
                    {
                        "code": "INCONSISTENT_PAGE_GEOMETRY",
                        "unit_ids": [unit["unit_id"]],
                        "detail": "conflicting source page dimensions; no replacement guessed",
                    }
                )
                envelope[key] = None
                conflicting_dimensions.add((page, key))
        bbox = layout.get("bbox")
        if bbox is None:
            missing.append(unit["unit_id"])
        upstream = dict(hints)
        if "geometry_granularity" in layout:
            upstream["geometry_granularity"] = layout["geometry_granularity"]
        envelope["units"].append(
            {
                "unit_id": unit["unit_id"],
                "ordinal": unit["ordinal"],
                "locator": unit.get("locator"),
                "text": unit["text"],
                "bbox": bbox,
                "font_size": layout.get("font_size"),
                "font_weight": layout.get("font_weight"),
                "kind": unit["kind"],
                "upstream_hints": upstream,
                "layout": {key: deepcopy(value) for key, value in layout.items()
                           if key in {"coordinate_frame", "rotation", "frame_converted", "cropbox", "cropbox_position",
                                      "reading_layout_feature_version", "geometry_granularity"}},
            }
        )
    coverage = result.get("coverage") or {}
    layout = derive_layout_hints(
        {
            "schema_version": "du2-layout-input/1",
            "source_ref": dict(result["source_ref"]),
            "pages": list(pages.values()),
            "coverage": {
                "opaque_pages": list(coverage.get("opaque_pages", ())),
                "deferred_pages": list(coverage.get("deferred_pages", ())),
            },
        },
        limits=limits, work_budget=work_budget,
    )
    if missing:
        diagnostics.append(
            {
                "code": "LAYOUT_GEOMETRY_UNAVAILABLE",
                "unit_ids": missing,
                "detail": "no actual source geometry for these units; text/DOM remains readable",
            }
        )
    if missing or diagnostics:
        layout["coverage"]["complete"] = False
        layout["diagnostics"].extend(diagnostics)
    by_id = {hint["unit_id"]: hint for hint in layout["unit_hints"]}
    for unit in result.get("units", ()):
        if work_budget is not None:
            work_budget.charge()
        hint = by_id.get(unit["unit_id"])
        if hint is None:
            continue
        unit.setdefault("hints", {})
        unit.setdefault("layout", {})
        # Preserve an actual layout exclusion too. A missing heading level by
        # itself is unknown; the explicit table-region basis is positive source
        # evidence that later numbering fallback must not erase.
        if "in_table_region" in hint["basis"]:
            unit["hints"]["table_region"] = True
        # Source DOM/explicit numbering wins over a missing geometry hint.
        if (
            unit["hints"].get("heading_level") is None
            and hint["heading_level"] is not None
        ):
            unit["hints"]["heading_level"] = hint["heading_level"]
            unit["hints"]["heading_level_source"] = "numbering" if "numbered_heading" in hint["basis"] else "layout"
            if unit["kind"] == "paragraph":
                unit["kind"] = "heading"
        if hint["text_column"] is not None and unit["layout"].get("bbox") is not None:
            unit["layout"]["column"] = hint["text_column"]
            unit["hints"]["column_lane"] = hint["text_column"]
    result.setdefault("metadata", {})["layout_feature_version"] = LAYOUT_HINTS_VERSION
    return result, layout


def _known_ids(structure, budget=None):
    known = set()

    def add(ids):
        for uid in ids:
            if budget is not None:
                budget.charge()
            known.add(uid)

    for section in structure.get("sections", ()):
        add(section.get("heading_unit_ids", ()))
        add(section.get("body_unit_ids", ()))
    for semantic in structure.get("semantic_units", ()):
        for field in (
            "member_unit_ids",
            "anchor_unit_ids",
            "required_context_unit_ids",
        ):
            add(semantic.get(field, ()))
    coverage = structure.get("coverage") or {}
    for field in (
        "unassigned_unit_ids",
        "deferred_unit_ids",
        "excluded_furniture_unit_ids",
    ):
        add(coverage.get(field, ()))
    return known


def bind_layout_context(structure: Mapping, layout_hints: Mapping, *, work_budget: WorkBudget | None = None) -> dict:
    source = structure.get("source_ref") or {}
    layout_source = layout_hints.get("source_ref") or {}
    if any(
        source.get(key) != layout_source.get(key)
        for key in ("source_id", "source_sha256")
    ):
        raise ValueError("layout source differs from structure source")
    ceiling = (
        (structure.get("coverage") or {}).get("limits", {}).get("max_work_units", 2000000)
    )
    if not isinstance(ceiling, int) or isinstance(ceiling, bool) or ceiling < 0:
        raise ValueError("layout binding work ceiling must be a nonnegative integer")
    budget = work_budget if work_budget is not None else WorkBudget(min(ceiling, 2000000))
    result = deepcopy(dict(structure)) if work_budget is None else None
    try:
        budget.charge()
        if work_budget is not None:
            result = {**structure, "coverage": dict(structure.get("coverage") or {}),
                      "diagnostics": []}
            prior = structure.get("diagnostics") or ()
            budget.charge(len(prior))
            result["diagnostics"] = list(prior)
            semantics = []
            for semantic in structure.get("semantic_units", ()):
                budget.charge(1 + len(semantic))
                semantics.append(dict(semantic))
            result["semantic_units"] = semantics
        assert result is not None
        return _bind_context(result, layout_hints, budget)
    except WorkBudgetExceeded:
        if result is None:
            result = {**structure, "coverage": dict(structure.get("coverage") or {}),
                      "diagnostics": []}
        result["coverage"]["prior_diagnostic_count"] = len(structure.get("diagnostics") or ())
        result.setdefault("diagnostics", []).append(
            {
                "code": "LAYOUT_BIND_WORK_BUDGET_EXCEEDED",
                "unit_ids": [],
                "detail": "existing work ceiling interrupted layout context binding; no unfinished requirements published",
            }
        )
        result.setdefault("coverage", {})["complete"] = False
        if work_budget is None:
            # Legacy standalone promises a complete independent projection.
            # Its already-materialised result retains the old partial labels;
            # composed calls never enumerate a tail after exhaustion.
            for semantic in result.get("semantic_units", ()):
                semantic["completeness"] = "partial"
        return result


def _bind_context(result, layout_hints, budget):
    known = _known_ids(result, budget)
    groups = {}
    for group in layout_hints.get("groups", ()):
        budget.charge()
        groups[group["group_id"]] = group
        for field in ("member_unit_ids", "required_context_unit_ids"):
            for uid in group.get(field, ()):
                budget.charge()
                if uid not in known:
                    raise ValueError("layout group references unknown source unit")
    semantics = result.get("semantic_units", ())
    members: dict[str, set[int]] = {}
    required = {}
    for i, semantic in enumerate(semantics):
        budget.charge()
        required[i] = dict.fromkeys(semantic.get("required_context_unit_ids", ()))
        for uid in semantic.get("member_unit_ids", ()):
            budget.charge()
            members.setdefault(uid, set()).add(i)
    for group in groups.values():
        touched: set[int] = set()
        for uid in group.get("member_unit_ids", ()):
            budget.charge()
            touched.update(members.get(uid, ()))
        for i in sorted(touched):
            member_ids = set(semantics[i].get("member_unit_ids", ()))
            for uid in group.get("required_context_unit_ids", ()):
                budget.charge()
                if uid not in member_ids:
                    required[i][uid] = None
    # Finish all bounded work before changing any requirement: interruption
    # cannot publish a half-bound dependency graph.
    budget.charge(len(semantics))
    for i, semantic in enumerate(semantics):
        semantic["required_context_unit_ids"] = list(required[i])
    if not (layout_hints.get("coverage") or {}).get("complete", False):
        result.setdefault("coverage", {})["complete"] = False
    result.setdefault("diagnostics", []).extend(
        deepcopy(layout_hints.get("diagnostics", ()))
    )
    result.setdefault("coverage", {})["layout_feature_version"] = LAYOUT_HINTS_VERSION
    return result


__all__ = ["apply_layout_hints", "bind_layout_context"]
