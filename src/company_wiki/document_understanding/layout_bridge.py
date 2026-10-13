"""One pure projection from source observations to shared layout and context.

Never reads bytes, opens a source, allocates a raw unit/locator, or changes text.
A missing geometry capability remains a diagnostic; original text stays readable.
"""

from __future__ import annotations
from copy import deepcopy
from math import isfinite
from typing import Mapping
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


def apply_layout_hints(observation: Mapping, *, limits=None) -> tuple[dict, dict]:
    result = deepcopy(dict(observation))
    pages = {}
    diagnostics = []
    missing = []
    conflicting_dimensions = set()
    for unit in result.get("units", ()):
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
        limits=limits,
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
        hint = by_id[unit["unit_id"]]
        unit.setdefault("hints", {})
        unit.setdefault("layout", {})
        # Source DOM/explicit numbering wins over a missing geometry hint.
        if (
            unit["hints"].get("heading_level") is None
            and hint["heading_level"] is not None
        ):
            unit["hints"]["heading_level"] = hint["heading_level"]
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


def bind_layout_context(structure: Mapping, layout_hints: Mapping) -> dict:
    source = structure.get("source_ref") or {}
    layout_source = layout_hints.get("source_ref") or {}
    if any(
        source.get(key) != layout_source.get(key)
        for key in ("source_id", "source_sha256")
    ):
        raise ValueError("layout source differs from structure source")
    result = deepcopy(dict(structure))
    ceiling = (
        (result.get("coverage") or {}).get("limits", {}).get("max_work_units", 2000000)
    )
    if not isinstance(ceiling, int) or isinstance(ceiling, bool) or ceiling < 0:
        raise ValueError("layout binding work ceiling must be a nonnegative integer")
    budget = WorkBudget(min(ceiling, 2000000))
    try:
        return _bind_context(result, layout_hints, budget)
    except WorkBudgetExceeded:
        result.setdefault("diagnostics", []).append(
            {
                "code": "LAYOUT_BIND_WORK_BUDGET_EXCEEDED",
                "unit_ids": sorted(_known_ids(result)),
                "detail": "existing work ceiling interrupted layout context binding; no unfinished requirements published",
            }
        )
        result.setdefault("coverage", {})["complete"] = False
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
    members = {}
    required = {}
    for i, semantic in enumerate(semantics):
        budget.charge()
        required[i] = dict.fromkeys(semantic.get("required_context_unit_ids", ()))
        for uid in semantic.get("member_unit_ids", ()):
            budget.charge()
            members.setdefault(uid, set()).add(i)
    for group in groups.values():
        touched = set()
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
