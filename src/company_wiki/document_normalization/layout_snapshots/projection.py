"""``project_layout_snapshot``: bind real layout snapshots onto existing units.

The public product API accepts only an in-memory ``du-layout-snapshot/1`` mapping
and already-read ``du-input/1`` units.  It emits a ``unit_metadata`` patch plus
coverage/diagnostics/feature version.  No file, network, model or OCR access.

Per unit the patch is committed atomically: an interrupted binding is never
published half-done.  The projection never infers column lanes, section /
continuation relations or header/footnote dependence — those remain the shared
``layout_hints`` responsibility.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .contract import (
    FEATURE_VERSION,
    PROJECTION_SCHEMA,
    Binding,
    PageEnvelope,
    in_page_bounds,
    validate_snapshot,
)
from .identity import WorkBudgetExceeded
from .unit_binding import _FineLimit, bind_binding

#: Diagnostic codes that make the projection partial rather than complete.
PARTIAL_CODES = frozenset(
    {
        "MISSING_UNIT",
        "WRONG_PAGE",
        "AMBIGUOUS_BINDING",
        "MISSING_BINDING_BBOX",
        "BAD_ELEMENT_BBOX",
        "FINE_ELEMENT_NO_BASIS",
        "NO_FINE_GEOMETRY",
        "NO_REAL_GEOMETRY",
        "UNKNOWN_COORDINATE_FRAME",
        "COORDINATE_OUT_OF_BOUNDS",
        "FRAME_SIZE_MISMATCH",
        "FRAME_LABEL_MISSING",
        "ROTATION_INVALID",
        "PAGE_SIZE_UNKNOWN",
        "UNIT_LIMIT_EXCEEDED",
        "PAGE_LIMIT_EXCEEDED",
    }
)


def _diag(code: str, unit_ids, detail: str) -> dict:
    return {"code": code, "unit_ids": sorted({u for u in unit_ids if u is not None}), "detail": detail}


def project_layout_snapshot(
    snapshot: Mapping[str, Any],
    units: Sequence[Mapping[str, Any]],
    *,
    limits: Mapping[str, Any] | None = None,
) -> dict:
    if not isinstance(units, Sequence) or isinstance(units, (str, bytes)):
        raise ValueError("units must be a sequence of mappings")
    pages, resolved, budget = validate_snapshot(snapshot, limits=limits)

    unit_index: dict = {}
    unit_order: list = []
    for pos, unit in enumerate(units):
        if not isinstance(unit, Mapping):
            raise ValueError(f"units[{pos}] must be a mapping")
        unit_id = unit.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id:
            raise ValueError(f"units[{pos}].unit_id must be a non-empty string")
        if unit_id not in unit_index:
            unit_index[unit_id] = unit
            unit_order.append(unit_id)

    unit_metadata: dict = {}
    diagnostics: list[dict] = []
    bound_ids: set = set()
    units_with_binding: set = set()
    unknown_frame_ids: set = set()
    fine_state = {"used": 0, "limit": resolved["max_fine_elements"]}
    exhausted = False
    fine_hit = False
    page_limit_hit = False
    unit_limit_hit = len(unit_order) > resolved["max_units"]

    try:
        for pos, unit_id in enumerate(unit_order):
            budget.charge(1)  # indexing every caller unit is bounded work
        pages_seen = 0
        for page in pages:
            if exhausted or fine_hit:
                break
            # max_pages bounds the COUNT of pages processed, not the page number:
            # real originals use high page numbers (e.g. 223) that must still bind.
            if pages_seen >= resolved["max_pages"]:
                page_limit_hit = True
                diagnostics.append(
                    _diag("PAGE_LIMIT_EXCEEDED", [], f"page {page.page_no} beyond max_pages={resolved['max_pages']} page budget")
                )
                continue
            pages_seen += 1
            _process_page(
                page,
                unit_index,
                unit_metadata,
                bound_ids,
                units_with_binding,
                unknown_frame_ids,
                diagnostics,
                budget,
                fine_state,
            )
    except WorkBudgetExceeded:
        exhausted = True
    except _FineLimit:
        fine_hit = True

    all_ids = list(unit_order)
    deferred_ids = [uid for uid in all_ids if uid in units_with_binding and uid not in unit_metadata]
    unbound_ids = [uid for uid in all_ids if uid not in units_with_binding]

    if exhausted:
        diagnostics.append(
            _diag(
                "WORK_BUDGET_EXCEEDED",
                [uid for uid in all_ids if uid not in unit_metadata],
                f"analysis interrupted at max_work_units={resolved['max_work_units']}; no half-done binding published",
            )
        )
    if fine_hit:
        diagnostics.append(
            _diag(
                "FINE_ELEMENT_LIMIT_EXCEEDED",
                [uid for uid in all_ids if uid not in unit_metadata],
                f"fine element ceiling max_fine_elements={resolved['max_fine_elements']} reached",
            )
        )
    if unit_limit_hit:
        diagnostics.append(
            _diag("UNIT_LIMIT_EXCEEDED", all_ids[resolved["max_units"] :], f"more than max_units={resolved['max_units']} units")
        )
    if unknown_frame_ids:
        diagnostics.append(
            _diag("UNKNOWN_COORDINATE_FRAME", unknown_frame_ids, "page coordinate frame unknown; physical size not guessed")
        )
    diagnostics.append(_diag("WORK_UNITS", [], str(budget.used)))

    complete = (
        not deferred_ids
        and not unknown_frame_ids
        and not exhausted
        and not fine_hit
        and not page_limit_hit
        and not unit_limit_hit
        and not any(d["code"] in PARTIAL_CODES for d in diagnostics)
    )

    return {
        "schema_version": PROJECTION_SCHEMA,
        "feature_version": FEATURE_VERSION,
        "unit_metadata": unit_metadata,
        "coverage": {
            "processed_unit_count": len(unit_metadata),
            "bound_unit_count": len(bound_ids),
            "deferred_unit_ids": deferred_ids,
            "unbound_unit_ids": unbound_ids,
            "unknown_frame_unit_ids": sorted(unknown_frame_ids),
            "incomplete_pages": [p.page_no for p in pages if _page_partial(p, unknown_frame_ids)],
            "complete": complete,
        },
        "diagnostics": diagnostics,
    }


def _page_partial(page: PageEnvelope, unknown_frame_ids: set) -> bool:
    return bool(page.frame.problems) or any(b.unit_id in unknown_frame_ids for b in page.bindings)


def _process_page(
    page: PageEnvelope,
    unit_index: dict,
    unit_metadata: dict,
    bound_ids: set,
    units_with_binding: set,
    unknown_frame_ids: set,
    diagnostics: list[dict],
    budget,
    fine_state: dict,
) -> None:
    frame = page.frame
    frame_problems = list(frame.problems)
    for problem in frame_problems:
        diagnostics.append(_diag(problem.upper(), [b.unit_id for b in page.bindings], f"page {page.page_no}: {problem}"))

    for binding in page.bindings:
        budget.charge(1)
        unit_id = binding.unit_id
        unit = unit_index.get(unit_id)
        if unit is None:
            diagnostics.append(_diag("MISSING_UNIT", [unit_id], "binding references a unit not present in units"))
            continue
        units_with_binding.add(unit_id)

        # a unit may be bound at most once: a second binding is an ambiguous match
        if unit_id in unit_metadata or unit_id in bound_ids:
            diagnostics.append(_diag("AMBIGUOUS_BINDING", [unit_id], "unit matched by more than one binding"))
            continue

        # the binding page must match the unit's own page
        unit_page = unit.get("page")
        if page.page_no is not None and unit_page is not None and unit_page != page.page_no:
            diagnostics.append(_diag("WRONG_PAGE", [unit_id], f"binding page {page.page_no} != unit page {unit_page}"))
            continue

        if binding.bbox is None:
            diagnostics.append(_diag("MISSING_BINDING_BBOX", [unit_id], "binding carries no legal bbox"))
        elif not in_page_bounds(binding.bbox, frame):
            diagnostics.append(_diag("COORDINATE_OUT_OF_BOUNDS", [unit_id], "binding bbox outside the declared page"))

        if not frame.known or frame.problems:
            unknown_frame_ids.add(unit_id)

        unit_text = unit.get("text") if isinstance(unit.get("text"), str) else ""
        fine, granularity, element_diags = bind_binding(
            binding,
            unit_text=unit_text,
            frame=frame,
            page_no=page.page_no,
            budget=budget,
            fine_state=fine_state,
        )
        diagnostics.extend(element_diags)

        meta = _assemble_meta(binding, frame, page.page_no, fine, granularity)
        # atomic commit: only after the whole binding is processed
        unit_metadata[unit_id] = meta
        bound_ids.add(unit_id)


def _assemble_meta(
    binding: Binding, frame, page_no, fine: dict, granularity: str
) -> dict:
    sizes = {r["font_size"] for r in fine["font_runs"] if r.get("font_size") is not None}
    weights = {r["font_weight"] for r in fine["font_runs"] if r.get("font_weight") is not None}
    layout = {
        "bbox": list(binding.bbox) if binding.bbox else None,
        "page": page_no,
        "page_width": frame.width,
        "page_height": frame.height,
        "coordinate_frame": frame.label if frame.known else None,
        "rotation": frame.rotation,
        "granularity": granularity,
        "font_size": next(iter(sizes)) if len(sizes) == 1 else None,
        "font_weight": next(iter(weights)) if len(weights) == 1 else None,
        "frame_converted": frame.converted,
    }
    hints = {"geometry_granularity": granularity}
    upstream_hints = {
        "geometry_granularity": granularity,
        "words": fine["words"],
        "cells": fine["cells"],
        "font_runs": fine["font_runs"],
    }
    return {"layout": layout, "hints": hints, "upstream_hints": upstream_hints}


__all__ = ["PARTIAL_CODES", "project_layout_snapshot"]
