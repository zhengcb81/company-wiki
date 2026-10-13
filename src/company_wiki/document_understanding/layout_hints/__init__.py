"""derive_layout_hints: du2-layout-input/1 -> du2-layout-hints/1.

A pure auxiliary capability: it consumes the caller's own units plus optional
font/bbox evidence and returns heading / text-column / table-structure hints,
context relations and an advisory reading-order view.  It never opens a
document, never allocates a source locator, never mutates the input and never
asserts business facts.  ROOT maps the hints onto the existing parser output;
this package is not wired into production on its own.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import Any, Mapping

from . import columns, headings, ordering, relations, tables
from .contract import SCHEMA_IN, SCHEMA_OUT, WorkBudgetExceeded, parse_observation
from .geometry import assign_cell_columns

LAYOUT_HINTS_VERSION = "1.1.0"

__all__ = ["derive_layout_hints", "SCHEMA_IN", "SCHEMA_OUT", "LAYOUT_HINTS_VERSION"]


def derive_layout_hints(
    observation: Mapping[str, Any], *, limits: Mapping[str, Any] | None = None
) -> dict:
    doc = parse_observation(observation, limits=limits)
    try:
        return _derive(doc)
    except WorkBudgetExceeded:
        # Discard partially materialised hints: an interrupted context chain
        # must never be published as a confident, independently usable table.
        return _budget_partial(doc)


def _budget_partial(doc) -> dict:
    ids = [unit.unit_id for unit in doc.units]
    return {
        "schema_version": SCHEMA_OUT,
        "feature_version": LAYOUT_HINTS_VERSION,
        "source_ref": doc.source_ref,
        "unit_hints": [
            {
                "unit_id": unit.unit_id,
                "heading_level": None,
                "text_column": None,
                "confidence": "unknown",
                "basis": ["deferred", unit.deferred_reason or "work_budget_exceeded"],
            }
            for unit in doc.units
        ],
        "groups": [],
        "relations": [],
        "reading_order": [],
        "coverage": {
            "processed_unit_count": 0,
            "deferred_unit_ids": ids,
            "opaque_pages": list(doc.coverage.get("opaque_pages", [])),
            "deferred_pages": list(doc.coverage.get("deferred_pages", [])),
            "complete": False,
        },
        "diagnostics": list(doc.diagnostics)
        + [
            {
                "code": "WORK_BUDGET_EXCEEDED",
                "unit_ids": ids,
                "detail": f"analysis interrupted at max_work_units={doc.limits['max_work_units']}; no incomplete hints published",
            },
            {"code": "WORK_UNITS", "unit_ids": [], "detail": str(doc.budget.used)},
        ],
    }


def _derive(doc) -> dict:
    diagnostics: list[dict] = list(doc.diagnostics)
    budget = doc.budget
    declared_coarse = []
    for unit in doc.units:
        if unit.deferred:
            continue
        budget.charge()
        if unit.hints.get("geometry_granularity") in {"row", "block", "table_region"}:
            declared_coarse.append(unit.unit_id)
    if declared_coarse:
        diagnostics.append(
            {
                "code": "NEEDS_UPSTREAM_GRANULARITY",
                "unit_ids": declared_coarse,
                "detail": "parser-declared aggregate boxes cannot prove table cell geometry",
            }
        )

    furniture_ids = headings.detect_repeated_furniture(doc)
    body_font = headings.body_font_size(doc, furniture_ids)

    page_bands_list = []
    drafts_by_page = []
    for page in doc.pages:
        if not budget.charge(1):
            break
        page_units = [unit for unit in page.units if not unit.deferred]
        page_bands = tables.analyse_page(page, page_units, budget, furniture_ids)
        drafts = tables.build_region_drafts(page_bands, budget)
        for draft in drafts:
            tables.analyse_region(draft, page_bands, budget)
            diagnostics.extend(
                {"code": code, "unit_ids": unit_ids, "detail": detail}
                for code, unit_ids, detail in draft.diagnostics
            )
            if draft.granularity:
                diagnostics.append(
                    {
                        "code": "NEEDS_UPSTREAM_GRANULARITY",
                        "unit_ids": sorted(
                            {
                                unit.unit_id
                                for index in draft.member_indices
                                for unit in page_bands.bands[index].units
                            }
                        ),
                        "detail": "whole-row units carry no cell coordinates; columns are not invented",
                    }
                )
        page_bands_list.append(page_bands)
        drafts_by_page.append(drafts)

    # ---- classification sets -------------------------------------------------
    table_member_ids: set = set()
    context_ids: set = set()
    attached_context: set = set()
    for page_bands, drafts in zip(page_bands_list, drafts_by_page):
        for draft in drafts:
            for index in draft.member_indices:
                table_member_ids.update(
                    unit.unit_id for unit in page_bands.bands[index].units
                )
            for index in draft.leading_context + draft.trailing_context:
                context_ids.update(
                    unit.unit_id for unit in page_bands.bands[index].units
                )
                attached_context.add((page_bands.page.page_index, index))

    orphan_context: list[tuple] = []
    for page_bands in page_bands_list:
        for index in sorted(page_bands.meta):
            kind = page_bands.meta[index].get("context")
            if kind and (page_bands.page.page_index, index) not in attached_context:
                orphan_context.append((page_bands, index, kind))

    # ---- lane layout (excludes tables, context lines and running furniture) --
    excluded_lane_ids = furniture_ids | table_member_ids | context_ids
    lane_layouts = columns.detect_document_lanes(
        [
            (
                page_bands.page,
                [
                    unit
                    for unit in page_bands.page.units
                    if not unit.deferred and unit.unit_id not in excluded_lane_ids
                ],
            )
            for page_bands in page_bands_list
        ],
        budget,
    )

    reading_order, rank = ordering.build_reading_order(
        page_bands_list, lane_layouts, diagnostics, budget
    )
    ordinal_by_id = {unit.unit_id: unit.ordinal for unit in doc.units}

    def member_order(unit_ids):
        return sorted(
            set(unit_ids),
            key=lambda uid: (rank.get(uid, 10**9), ordinal_by_id.get(uid, 0)),
        )

    # ---- group assembly -----------------------------------------------------
    groups: list[dict] = []
    relation_items: list[dict] = []
    group_limit_hit = False
    group_limit_dropped: set = set()

    def add_group(
        kind, members, required_context, cells, parent_tmp, confidence, basis
    ):
        nonlocal group_limit_hit
        budget.charge()
        if len(groups) >= doc.limits["max_groups"]:
            group_limit_dropped.update(members)
            if not group_limit_hit:
                group_limit_hit = True
            return None
        tmp_id = f"t{len(groups)}"
        groups.append(
            {
                "group_id": tmp_id,
                "kind": kind,
                "parent_table_id": parent_tmp,
                "member_unit_ids": member_order(members),
                "required_context_unit_ids": member_order(required_context),
                "cells": cells,
                "confidence": confidence,
                "basis": basis,
            }
        )
        return tmp_id

    def band_unit_ids(page_bands, indices):
        out: list = []
        for index in indices:
            out.extend(unit.unit_id for unit in page_bands.bands[index].units)
        return out

    def context_unit_ids(draft, page_bands):
        return band_unit_ids(page_bands, draft.leading_context) + band_unit_ids(
            page_bands, draft.trailing_context
        )

    def build_cells(draft, page_bands, band_indices, row_offset):
        cells_out = []
        for row_position, index in enumerate(band_indices):
            for cell in page_bands.cells[index]:
                column, span = assign_cell_columns(cell, draft.slots, budget=budget)
                cells_out.append(
                    {
                        "member_unit_ids": member_order(
                            unit.unit_id for unit in cell.members
                        ),
                        "row": row_offset + row_position,
                        "column": column,
                        "row_span": None,
                        "column_span": span,
                    }
                )
        return cells_out

    region_tmp_by_draft: dict = {}
    for page_bands, drafts in zip(page_bands_list, drafts_by_page):
        for draft in drafts:
            members = band_unit_ids(page_bands, draft.member_indices)
            context_units = context_unit_ids(draft, page_bands)
            region_basis, region_confidence = _region_confidence(draft)
            region_tmp = add_group(
                "table_region",
                members,
                context_units,
                [],
                None,
                region_confidence,
                region_basis,
            )
            if region_tmp is None:
                continue
            region_tmp_by_draft[id(draft)] = (region_tmp, draft, page_bands)

            header_units = band_unit_ids(page_bands, draft.header_indices)
            row_context = context_units + header_units
            header_tmp = None
            if header_units:
                header_tmp = add_group(
                    "table_row",
                    header_units,
                    context_units,
                    []
                    if draft.granularity
                    else build_cells(draft, page_bands, draft.header_indices, 0),
                    region_tmp,
                    "high" if not draft.granularity else "low",
                    ["header_block"]
                    if len(draft.header_indices) > 1
                    else ["header_row"],
                )
                if header_tmp:
                    relation_items.append(
                        {
                            "from_group_id": header_tmp,
                            "to_group_id": region_tmp,
                            "kind": "header_for",
                            "confidence": "high",
                            "basis": ["header_row_alignment"],
                        }
                    )
            row_offset = 1 if header_tmp else 0
            for position, index in enumerate(draft.row_indices):
                row_units = band_unit_ids(page_bands, [index])
                row_confidence, row_basis = _row_confidence(
                    draft, page_bands, index, budget
                )
                add_group(
                    "table_row",
                    row_units,
                    row_context,
                    []
                    if draft.granularity
                    else build_cells(draft, page_bands, [index], row_offset + position),
                    region_tmp,
                    row_confidence,
                    row_basis,
                )

            caption_units = band_unit_ids(page_bands, draft.leading_context)
            if caption_units:
                caption_basis = ["caption_context"]
                for index in draft.leading_context:
                    caption_basis.append(
                        f"context:{draft.context_kinds.get(index, 'caption')}"
                    )
                caption_tmp = add_group(
                    "caption", caption_units, [], [], None, "high", caption_basis
                )
                if caption_tmp:
                    relation_items.append(
                        {
                            "from_group_id": caption_tmp,
                            "to_group_id": region_tmp,
                            "kind": "caption_for",
                            "confidence": "high",
                            "basis": ["adjacent_to_table_edge"],
                        }
                    )
            footnote_units = band_unit_ids(page_bands, draft.trailing_context)
            if footnote_units:
                # a table note belongs to the table region it explains
                footnote_tmp = add_group(
                    "footnote",
                    footnote_units,
                    [],
                    [],
                    region_tmp,
                    "high",
                    ["footnote_line"],
                )
                if footnote_tmp:
                    relation_items.append(
                        {
                            "from_group_id": footnote_tmp,
                            "to_group_id": region_tmp,
                            "kind": "footnote_for",
                            "confidence": "high",
                            "basis": ["adjacent_to_table_edge"],
                        }
                    )

    # standalone caption/footnote lines (e.g. figure captions and their notes)
    orphan_tmp_by_band: dict = {}
    for page_bands, index, kind in orphan_context:
        units = band_unit_ids(page_bands, [index])
        group_kind = "footnote" if kind == "footnote" else "caption"
        basis = ["footnote_line"] if kind == "footnote" else [f"context:{kind}"]
        tmp = add_group(
            group_kind, units, [], [], None, "medium", basis + ["standalone"]
        )
        if tmp:
            orphan_tmp_by_band[(page_bands.page.page_index, index)] = (
                tmp,
                page_bands,
                index,
                group_kind,
            )

    caption_edges: dict = {}
    for (page_index, index), (
        tmp,
        page_bands,
        _index,
        group_kind,
    ) in orphan_tmp_by_band.items():
        budget.charge()
        if group_kind == "caption":
            caption_edges.setdefault(page_index, []).append(
                (page_bands.bands[index].bbox[3], tmp)
            )
    for entries in caption_edges.values():
        entries.sort()
    for (page_index, index), (tmp, page_bands, _index, group_kind) in sorted(
        orphan_tmp_by_band.items()
    ):
        budget.charge()
        if group_kind != "footnote":
            continue
        edges = caption_edges.get(page_index, [])
        top = page_bands.bands[index].bbox[1]
        cursor = bisect_right(edges, (top, chr(0x10FFFF))) - 1
        if cursor >= 0 and top - edges[cursor][0] <= 30.0:
            relation_items.append(
                {
                    "from_group_id": tmp,
                    "to_group_id": edges[cursor][1],
                    "kind": "footnote_for",
                    "confidence": "medium",
                    "basis": ["below_caption_group"],
                }
            )

    # ---- heading groups and unit hints --------------------------------------
    heading_evidence_by_id: dict = {}
    for page_bands in page_bands_list:
        page_units = [unit for unit in page_bands.page.units if not unit.deferred]
        clearances = headings.vertical_clearances(page_units, budget)
        for unit in page_units:
            budget.charge()
            if unit.unit_id in furniture_ids:
                heading_evidence_by_id[unit.unit_id] = {
                    "level": None,
                    "confidence": "low",
                    "basis": ["repeated_page_furniture"],
                }
                continue
            if unit.unit_id in table_member_ids:
                heading_evidence_by_id[unit.unit_id] = {
                    "level": None,
                    "confidence": "low",
                    "basis": ["in_table_region"],
                }
                continue
            if unit.unit_id in context_ids:
                heading_evidence_by_id[unit.unit_id] = {
                    "level": None,
                    "confidence": "low",
                    "basis": ["context_line"],
                }
                continue
            heading_evidence_by_id[unit.unit_id] = headings.heading_evidence(
                unit, clearances, body_font
            )

    for page_bands in page_bands_list:
        for unit in sorted(
            page_bands.page.units,
            key=lambda u: (u.bbox is None, u.bbox[1] if u.bbox else 0, u.ordinal),
        ):
            budget.charge()
            if unit.deferred:
                continue
            evidence = heading_evidence_by_id[unit.unit_id]
            if evidence["level"] is None:
                continue
            add_group(
                "heading",
                [unit.unit_id],
                [],
                [],
                None,
                evidence["confidence"],
                list(evidence["basis"]),
            )

    # ---- column lane groups --------------------------------------------------
    for page_bands, lane_layout in zip(page_bands_list, lane_layouts):
        for lane in lane_layout.lanes:
            add_group(
                "column_lane",
                [unit.unit_id for unit in lane],
                [],
                [],
                None,
                lane_layout.confidence,
                list(lane_layout.basis),
            )

    # ---- cross-page continuation -------------------------------------------
    continuations: list[tuple] = []
    for page_index in range(len(page_bands_list) - 1):
        prev_page = page_bands_list[page_index]
        next_page = page_bands_list[page_index + 1]
        for prev_draft in drafts_by_page[page_index]:
            prev_box = prev_draft.bbox()
            if prev_page.page.height and prev_box[3] < 0.7 * prev_page.page.height:
                continue
            for next_draft in drafts_by_page[page_index + 1]:
                budget.charge()
                next_box = next_draft.bbox()
                if next_page.page.height and next_box[1] > 0.25 * next_page.page.height:
                    continue
                gap = (next_page.page.page_value or 0) - (
                    prev_page.page.page_value or 0
                )
                if gap < 1:
                    continue
                claim = relations.continuation_claim(
                    _region_descriptor(prev_draft, prev_page, budget),
                    _region_descriptor(next_draft, next_page, budget),
                    page_gap=gap,
                    budget=budget,
                )
                if claim:
                    continuations.append((prev_draft, next_draft, claim))
    # Geometry can fit more than one adjacent table. Preserve ambiguity instead
    # of joining multiple tables or overwriting one predecessor's context.
    targets = {}
    sources = {}
    for prev_draft, next_draft, _claim in continuations:
        budget.charge()
        targets.setdefault(id(prev_draft), set()).add(id(next_draft))
        sources.setdefault(id(next_draft), set()).add(id(prev_draft))
    unique = []
    for prev_draft, next_draft, claim in continuations:
        budget.charge()
        if len(targets[id(prev_draft)]) == 1 and len(sources[id(next_draft)]) == 1:
            unique.append((prev_draft, next_draft, claim))
        else:
            entry = region_tmp_by_draft.get(id(next_draft))
            affected = (
                band_unit_ids(entry[2], next_draft.member_indices) if entry else []
            )
            diagnostics.append(
                {
                    "code": "CONTINUATION_AMBIGUOUS",
                    "unit_ids": affected,
                    "detail": "multiple geometry-compatible neighbours; no continuation or inherited context claimed",
                }
            )
    continuations = unique

    continuation_context: dict = {}
    for prev_draft, next_draft, claim in continuations:
        prev_entry = region_tmp_by_draft.get(id(prev_draft))
        next_entry = region_tmp_by_draft.get(id(next_draft))
        if not prev_entry or not next_entry:
            continue
        relation_items.append(
            {
                "from_group_id": prev_entry[0],
                "to_group_id": next_entry[0],
                "kind": claim["kind"],
                "confidence": claim["confidence"],
                "basis": claim["basis"],
            }
        )
        carry = member_order(
            band_unit_ids(
                prev_entry[2],
                prev_draft.leading_context
                + prev_draft.header_indices
                + prev_draft.trailing_context,
            )
            + continuation_context.get(id(prev_draft), [])
        )
        budget.charge(len(carry))
        continuation_context[id(next_draft)] = carry
        diagnostics.append(
            {
                "code": "CONTINUATION_CLAIMED",
                "unit_ids": band_unit_ids(next_entry[2], next_draft.member_indices),
                "detail": "accepted unique cross-page continuation: "
                + ",".join(claim["basis"]),
            }
        )

        if "repeated_header" not in claim["basis"]:
            # A continued table without header-continuation evidence: its leading
            # bands are continuation rows, not a fresh header claim.
            target_region = next_entry[0]
            demoted = [
                item
                for item in relation_items
                if item["kind"] == "header_for" and item["to_group_id"] == target_region
            ]
            for item in demoted:
                relation_items.remove(item)
                header_group = next(
                    (g for g in groups if g["group_id"] == item["from_group_id"]), None
                )
                if header_group is not None:
                    header_group["confidence"] = "medium"
                    header_group["basis"] = [
                        "visual_row",
                        "continuation_rows_not_header",
                    ]
                diagnostics.append(
                    {
                        "code": "CONTINUATION_ROWS_NOT_HEADER",
                        "unit_ids": list(header_group["member_unit_ids"])
                        if header_group
                        else [],
                        "detail": "continued table has no header-continuation evidence; leading bands kept as rows",
                    }
                )

    # The continuation graph is forward-only. Carry earlier inherited context
    # before publishing any region/row, using one region lookup per group.
    inherited_by_region = {
        region_tmp_by_draft[key][0]: carry
        for key, carry in continuation_context.items()
        if key in region_tmp_by_draft
    }
    for group in groups:
        budget.charge()
        owning = (
            group["group_id"]
            if group["kind"] == "table_region"
            else group["parent_table_id"]
        )
        carry = inherited_by_region.get(owning, [])
        if carry and group["kind"] in ("table_region", "table_row"):
            budget.charge(len(carry))
            group["required_context_unit_ids"] = member_order(
                group["required_context_unit_ids"] + carry
            )

    # ---- numbering, unit hints and final assembly ---------------------------
    kind_rank = {
        "caption": 0,
        "table_region": 1,
        "table_row": 2,
        "footnote": 3,
        "heading": 4,
        "column_lane": 5,
    }

    def group_sort_key(group):
        members = group["member_unit_ids"]
        first = members[0] if members else None
        order = rank.get(first, 10**9) if first else 10**9
        return (order, kind_rank.get(group["kind"], 9), group["kind"])

    ordered_groups = sorted(groups, key=group_sort_key)
    id_map = {
        group["group_id"]: f"g{position + 1}"
        for position, group in enumerate(ordered_groups)
    }
    final_groups = []
    for group in ordered_groups:
        final_groups.append(
            {
                "group_id": id_map[group["group_id"]],
                "kind": group["kind"],
                "parent_table_id": id_map.get(group["parent_table_id"])
                if group["parent_table_id"]
                else None,
                "member_unit_ids": group["member_unit_ids"],
                "required_context_unit_ids": group["required_context_unit_ids"],
                "cells": group["cells"],
                "confidence": group["confidence"],
                "basis": group["basis"],
            }
        )
    final_relations = sorted(
        (
            {
                "from_group_id": id_map[item["from_group_id"]],
                "to_group_id": id_map[item["to_group_id"]],
                "kind": item["kind"],
                "confidence": item["confidence"],
                "basis": item["basis"],
            }
            for item in relation_items
            if item["from_group_id"] in id_map and item["to_group_id"] in id_map
        ),
        key=lambda item: (item["from_group_id"], item["to_group_id"], item["kind"]),
    )

    unit_hints = _build_unit_hints(
        doc,
        heading_evidence_by_id,
        lane_layouts,
        table_member_ids,
        context_ids,
        furniture_ids,
    )

    processed = set(doc.processed_ids)
    complete = (
        not doc.deferred_ids
        and not doc.coverage.get("opaque_pages")
        and not doc.coverage.get("deferred_pages")
        and not budget.exhausted
        and not group_limit_hit
        and not any(diag["code"] == "UNIT_LIMIT_EXCEEDED" for diag in diagnostics)
        and not any(
            diag["code"] in {"NEEDS_UPSTREAM_GRANULARITY", "CONTINUATION_AMBIGUOUS"}
            for diag in diagnostics
        )
    )
    if group_limit_hit:
        diagnostics.append(
            {
                "code": "GROUP_LIMIT_EXCEEDED",
                "unit_ids": sorted(group_limit_dropped),
                "detail": (
                    f"more than max_groups={doc.limits['max_groups']} groups; "
                    "structure stopped early, affected units keep their unit_hints"
                ),
            }
        )
    diagnostics.append(
        {"code": "WORK_UNITS", "unit_ids": [], "detail": str(budget.used)}
    )

    return {
        "schema_version": SCHEMA_OUT,
        "feature_version": LAYOUT_HINTS_VERSION,
        "source_ref": doc.source_ref,
        "unit_hints": unit_hints,
        "groups": final_groups,
        "relations": final_relations,
        "reading_order": reading_order,
        "coverage": {
            "processed_unit_count": len(processed),
            "deferred_unit_ids": list(doc.deferred_ids),
            "opaque_pages": list(doc.coverage.get("opaque_pages", [])),
            "deferred_pages": list(doc.coverage.get("deferred_pages", [])),
            "complete": complete,
        },
        "diagnostics": diagnostics,
    }


def _region_confidence(draft) -> tuple[list[str], str]:
    if draft.granularity:
        return ["grid_rows", "needs_upstream_granularity"], "low"
    basis = ["column_alignment"]
    if draft.header_indices:
        basis.append("header_block")
        return basis, "high"
    basis.append("no_header")
    return basis, "medium"


def _row_confidence(draft, page_bands, index, budget) -> tuple[str, list[str]]:
    basis = ["visual_row"]
    if draft.granularity:
        return "low", basis + ["needs_upstream_granularity"]
    cells = page_bands.cells[index]
    region_box = draft.bbox()
    region_width = max(region_box[2] - region_box[0], 1.0)
    assigned = 0
    wide_single = False
    for cell in cells:
        column, _span = assign_cell_columns(cell, draft.slots, budget=budget)
        if column is not None:
            assigned += 1
    if len(cells) == 1 and (cells[0].bbox[2] - cells[0].bbox[0]) > 0.5 * region_width:
        wide_single = True
    wrapped = bool(
        draft.wrapped_unit_ids.intersection(
            unit.unit_id for unit in page_bands.bands[index].units
        )
    )
    if wide_single:
        return "low", basis + ["wide_row_unsplit"]
    if wrapped:
        return "medium", basis + ["wrapped_row_suspected"]
    if len(cells) >= 2 and assigned >= 2:
        return "high", basis + ["column_alignment"]
    return "medium", basis + ["partial_cells"]


def _region_descriptor(draft, page_bands, budget) -> dict:
    header_texts = []
    for index in draft.header_indices:
        budget.charge()
        header_texts.append(page_bands.bands[index].text)
    return {
        "slots": draft.slots,
        "header_texts": header_texts,
        "has_caption": bool(draft.leading_context),
        "bbox": draft.bbox(),
        "page_width": page_bands.page.width,
    }


def _build_unit_hints(
    doc,
    heading_evidence_by_id,
    lane_layouts,
    table_member_ids,
    context_ids,
    furniture_ids,
):
    lane_by_unit: dict = {}
    for lane_layout in lane_layouts:
        for index, members in enumerate(lane_layout.lanes):
            for unit in members:
                lane_by_unit[unit.unit_id] = (
                    index,
                    lane_layout.confidence,
                    list(lane_layout.basis),
                )
        for unit in lane_layout.spanning:
            lane_by_unit[unit.unit_id] = (None, "medium", ["spanning_lane"])

    hints = []
    for unit in doc.units:
        if unit.deferred:
            hints.append(
                {
                    "unit_id": unit.unit_id,
                    "heading_level": None,
                    "text_column": None,
                    "confidence": "unknown",
                    "basis": ["deferred", unit.deferred_reason or "deferred"],
                }
            )
            continue
        evidence = heading_evidence_by_id.get(
            unit.unit_id,
            {"level": None, "confidence": "unknown", "basis": ["missing_geometry"]},
        )
        lane = lane_by_unit.get(unit.unit_id)
        if lane is not None:
            column, lane_confidence, lane_basis = lane
        elif unit.unit_id in table_member_ids:
            column, lane_confidence, lane_basis = None, "low", ["in_table_region"]
        elif unit.unit_id in context_ids:
            column, lane_confidence, lane_basis = None, "low", ["context_line"]
        elif unit.unit_id in furniture_ids:
            column, lane_confidence, lane_basis = (
                None,
                "low",
                ["repeated_page_furniture"],
            )
        else:
            column, lane_confidence, lane_basis = (
                None,
                evidence["confidence"],
                ["no_lane_split"],
            )

        if evidence["level"] is not None:
            confidence = evidence["confidence"]
        elif column is not None:
            confidence = lane_confidence
        else:
            confidence = evidence["confidence"]
        hints.append(
            {
                "unit_id": unit.unit_id,
                "heading_level": evidence["level"],
                "text_column": column,
                "confidence": confidence,
                "basis": list(dict.fromkeys(evidence["basis"] + lane_basis)),
            }
        )
    return hints
