"""Observed PDF fine slots -> frozen ``du4-table-observation/1``.

Pure in-memory adapter between the production ``du-input/1`` wire (units whose
``hints`` carry the DU3 fine cell geometry with exact scalar offsets) plus the
shared ``du2-layout-hints/1`` relations, and the observation contract the
existing ``table_measurements.bind_operating_table`` consumes.  It never
re-parses an original, never re-locates a value by string search, never invents
a text reference, an empty cell, a span or a header, and never rewrites text,
ids or locators.  Facts the upstream never observed stay unknown.

Evidence rules (construction card ``du7-pdf-tables-2026-10-16``):

* one table observation per real ``(parent source, table_id, page)`` identity;
  equal table numbers from different sources are never merged;
* ``row``/``column`` come from the observed native slot of a fine cell and must
  agree with the owning unit's row claim, otherwise the entry is dropped with a
  diagnostic instead of being reassigned;
* a text reference is emitted only when the fine entry's ``char_alignment`` is
  ``exact``, its coordinate frame is known and the unit text at the supplied
  offsets equals the observed cell text completely;
* header rows come from observed relations only — shared ``header_for`` groups,
  or a wire ``table_header`` kind that the shared engine's data-row groups do
  not contradict.  Nothing assumes row 0 or the newest year is a header;
* row labels are the leading native-slot cell of a non-header row with at least
  two observed cells; their verified refs attach to the row's other cells;
* caption/footnote context refs come from shared ``caption_for``/``footnote_for``
  relations and are dropped with a diagnostic when their unit belongs to a
  different parent;
* ``row_span``/``column_span`` are always ``None`` here: the upstream dropped
  merged spans, and guessing them is forbidden.  Presence is ``present`` for an
  observed value (even when its exact location is unknown); the ``empty``
  presence is only for a slot actually observed as empty, which the PDF
  upstream does not retain — lost slots are simply absent from ``cells``.

Work accounting (the shared logical ``WorkBudget``; no wall-clock claim):

* 1 charge before any input traversal,
* 1 per observation unit examined and 1 per fine-cell entry examined,
* ``(char_end - char_start) // 64`` extra whenever a candidate range is
  actually sliced for comparison (0 for ordinary short values),
* 1 per shared relation record / group member examined,
* 1 per table finalized, 1 per provenance record, 1 per attached header ref and
  1 per unit materialized into a table's ``units``.

The budget is never created or reset here; exhaustion keeps the tables already
closed and reports ``partial`` instead of a half-built table.  Structural wire
errors (wrong schema, duplicate unit ids, illegal types) raise ``ValueError``;
recoverable evidence gaps become per-item diagnostics.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from company_wiki.document_understanding.layout_hints.contract import (
    WorkBudget,
    WorkBudgetExceeded,
)

SCHEMA_OBSERVATION = "du-input/1"
SCHEMA_HINTS = "du2-layout-hints/1"
SCHEMA_OUT = "du4-table-observation/1"

#: Fine entries may only position a value while their frame is actually known.
KNOWN_FRAMES = ("dict", "page")

DEGRADING_CODES = frozenset(
    {
        "CELL_TEXT_UNLOCATABLE",
        "CELL_SLOT_UNAVAILABLE",
        "CELL_SLOT_MISMATCH",
        "TABLE_CELLS_UNAVAILABLE",
        "TABLE_ROW_SLOTS_UNAVAILABLE",
        "FOREIGN_CONTEXT_REF_DROPPED",
        "CONTEXT_REF_UNAVAILABLE",
        "ROW_LABEL_UNAVAILABLE",
    }
)


def _is_index(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


class _Slot:
    """One observed native slot, gathering the real refs of every carrier unit."""

    __slots__ = ("row", "column", "text_refs", "locatable")

    def __init__(self, row: int, column: int) -> None:
        self.row = row
        self.column = column
        self.text_refs: list[dict] = []
        self.locatable = 0  # observed values whose exact location stayed unknown

    @property
    def cell_id(self) -> str:
        return f"r{self.row}c{self.column}"


class _Scope:
    __slots__ = ("parent_id", "table_id", "page", "unit_ids", "row_claims", "slots", "order")

    def __init__(self, parent_id: Any, table_id: str, page: Any) -> None:
        self.parent_id = parent_id
        self.table_id = table_id
        self.page = page
        self.unit_ids: list[str] = []
        self.row_claims: dict[int, list[str]] = {}
        self.slots: dict[tuple[int, int], _Slot] = {}
        self.order: list[tuple[int, int]] = []


class _SharedEvidence:
    def __init__(self) -> None:
        self.header_units: set[str] = set()
        self.data_row_units: set[str] = set()
        self.context: dict[tuple, list[str]] = {}


def build_pdf_table_observations(
    observation: Mapping,
    layout_hints: Mapping | None,
    *,
    work_budget: WorkBudget,
) -> dict:
    """Project observed PDF fine slots onto ``du4-table-observation/1`` tables."""
    start = work_budget.used
    tables: list[dict] = []
    diagnostics: list[dict] = []
    degrading = False
    exhausted = False
    try:
        work_budget.charge(1)
        facts, scopes, order = _index_units(observation, work_budget, diagnostics)
        evidence = _shared_evidence(layout_hints, facts, scopes, work_budget, diagnostics)
        for key in order:
            table, degraded = _build_table(
                scopes[key], facts, evidence, work_budget, diagnostics
            )
            degrading = degrading or degraded
            if table is not None:
                tables.append(table)
    except WorkBudgetExceeded:
        exhausted = True
        diagnostics.append({"code": "WORK_BUDGET_EXCEEDED"})

    if exhausted or degrading:
        status = "partial"
    elif not tables:
        status = "unavailable"
    else:
        status = "complete"
    return {
        "status": status,
        "tables": tables,
        "diagnostics": diagnostics,
        "work_used": work_budget.used - start,
    }


def _index_units(observation, work_budget, diagnostics):
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be a mapping")
    if observation.get("schema_version") != SCHEMA_OBSERVATION:
        raise ValueError(
            f"unsupported observation schema: {observation.get('schema_version')!r}"
        )
    source_ref = observation.get("source_ref")
    fallback_parent = (
        source_ref.get("source_id") if isinstance(source_ref, Mapping) else None
    )
    units = observation.get("units") or ()
    if isinstance(units, (str, bytes)) or not isinstance(units, Sequence):
        raise ValueError("observation units must be a sequence")

    facts: dict[str, dict] = {}
    scopes: dict[tuple, _Scope] = {}
    order: list[tuple] = []
    for raw in units:
        work_budget.charge(1)
        if not isinstance(raw, Mapping):
            raise ValueError("each observation unit must be a mapping")
        unit_id = raw.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id:
            raise ValueError("observation units need a non-empty unit_id")
        if unit_id in facts:
            raise ValueError(f"duplicate unit id {unit_id!r}")
        text = raw.get("text")
        if not isinstance(text, str):
            raise ValueError(f"unit {unit_id!r} text must be a string")
        hints = raw.get("hints")
        hints = hints if isinstance(hints, Mapping) else {}
        parent = hints.get("source_id") or fallback_parent
        fact = {
            "unit_id": unit_id,
            "text": text,
            "parent_id": parent,
            "role": raw.get("role"),
            "kind": raw.get("kind"),
            "locator": raw.get("locator"),
            "page": raw.get("page"),
        }
        facts[unit_id] = fact
        table_id = hints.get("table_id")
        if not isinstance(table_id, str) or not table_id:
            continue
        key = (parent, table_id, fact["page"])
        scope = scopes.get(key)
        if scope is None:
            scope = _Scope(parent, table_id, fact["page"])
            scopes[key] = scope
            order.append(key)
        scope.unit_ids.append(unit_id)
        row_claim = hints.get("row")
        if _is_index(row_claim):
            scope.row_claims.setdefault(int(row_claim), []).append(unit_id)
        entries = hints.get("cells")
        if entries is None:
            continue
        if isinstance(entries, (str, bytes)) or not isinstance(entries, Sequence):
            raise ValueError(f"unit {unit_id!r} fine cells must be a sequence")
        for entry in entries:
            work_budget.charge(1)
            _consume_cell_entry(scope, fact, row_claim, entry, work_budget, diagnostics)
    return facts, scopes, order


def _consume_cell_entry(scope, fact, row_claim, entry, work_budget, diagnostics):
    if not isinstance(entry, Mapping):
        diagnostics.append({"code": "CELL_SLOT_UNAVAILABLE", "unit_id": fact["unit_id"]})
        return
    row = entry.get("row")
    column = entry.get("column")
    entry_table = entry.get("table_id")
    if not _is_index(row) or not _is_index(column):
        diagnostics.append({"code": "CELL_SLOT_UNAVAILABLE", "unit_id": fact["unit_id"]})
        return
    if entry_table != scope.table_id or (
        _is_index(row_claim) and int(row) != int(row_claim)
    ):
        diagnostics.append(
            {
                "code": "CELL_SLOT_MISMATCH",
                "unit_id": fact["unit_id"],
                "row": row,
                "column": column,
            }
        )
        return
    key = (int(row), int(column))
    slot = scope.slots.get(key)
    if slot is None:
        slot = _Slot(key[0], key[1])
        scope.slots[key] = slot
        scope.order.append(key)
    ref = _verified_ref(fact, entry, work_budget, diagnostics)
    if ref is None:
        slot.locatable += 1
        return
    if ref not in slot.text_refs:
        slot.text_refs.append(ref)


def _verified_ref(fact, entry, work_budget, diagnostics):
    """The exact ref of one fine entry, or ``None`` when it cannot be proven."""
    text = fact["text"]
    start = entry.get("char_start")
    end = entry.get("char_end")
    reason = None
    if entry.get("char_alignment") != "exact":
        reason = "alignment_not_exact"
    elif entry.get("coordinate_frame") not in KNOWN_FRAMES:
        reason = "frame_unknown"
    elif not (_is_index(start) and _is_index(end) and int(start) < int(end) <= len(text)):
        reason = "offset_out_of_range"
    else:
        work_budget.charge((int(end) - int(start)) // 64)
        if text[int(start) : int(end)] != entry.get("text"):
            reason = "text_slice_mismatch"
    if reason is not None:
        diagnostics.append(
            {
                "code": "CELL_TEXT_UNLOCATABLE",
                "unit_id": fact["unit_id"],
                "reason": reason,
            }
        )
        return None
    return {
        "unit_id": fact["unit_id"],
        "char_start": int(start),
        "char_end": int(end),
    }


def _shared_evidence(layout_hints, facts, scopes, work_budget, diagnostics):
    evidence = _SharedEvidence()
    if layout_hints is None:
        return evidence
    if not isinstance(layout_hints, Mapping):
        raise ValueError("layout_hints must be a mapping or None")
    if layout_hints.get("schema_version") != SCHEMA_HINTS:
        raise ValueError(
            f"unsupported layout hints schema: {layout_hints.get('schema_version')!r}"
        )
    groups = {}
    raw_groups = layout_hints.get("groups") or ()
    for group in raw_groups:
        work_budget.charge(1)
        if isinstance(group, Mapping) and isinstance(group.get("group_id"), str):
            groups[group["group_id"]] = group
    header_from_groups = set()
    scope_by_unit = {
        unit_id: (scope.parent_id, scope.table_id, scope.page)
        for scope in scopes.values()
        for unit_id in scope.unit_ids
    }

    def members(group_id):
        group = groups.get(group_id)
        ids = group.get("member_unit_ids") if isinstance(group, Mapping) else None
        ids = ids if isinstance(ids, Sequence) and not isinstance(ids, (str, bytes)) else ()
        for unit_id in ids:
            work_budget.charge(1)
            yield unit_id

    relations = layout_hints.get("relations") or ()
    relation_items = []
    for relation in relations:
        work_budget.charge(1)
        if not isinstance(relation, Mapping):
            continue
        relation_items.append(relation)
        if relation.get("kind") == "header_for":
            header_from_groups.add(relation.get("from_group_id"))
            for unit_id in members(relation.get("from_group_id")):
                if unit_id in facts and unit_id in scope_by_unit:
                    evidence.header_units.add(unit_id)
    for group_id, group in groups.items():
        if group.get("kind") != "table_row" or group_id in header_from_groups:
            continue
        for unit_id in members(group_id):
            if unit_id in facts and unit_id in scope_by_unit:
                evidence.data_row_units.add(unit_id)

    for relation in relation_items:
        kind = relation.get("kind")
        if kind not in ("caption_for", "footnote_for"):
            continue
        targets = set(members(relation.get("to_group_id")))
        for scope_key in {
            scope_by_unit[unit_id] for unit_id in targets if unit_id in scope_by_unit
        }:
            for unit_id in members(relation.get("from_group_id")):
                if unit_id not in facts:
                    continue
                evidence.context.setdefault(scope_key, []).append(unit_id)
    return evidence


def _build_table(scope, facts, evidence, work_budget, diagnostics):
    """Build one closed table observation; ``None`` when nothing is observable."""
    degraded = False
    header_rows = set()
    contradicted = set()
    for row, unit_ids in scope.row_claims.items():
        for unit_id in unit_ids:
            if unit_id in evidence.header_units:
                header_rows.add(row)
                break
        else:
            for unit_id in unit_ids:
                if facts[unit_id]["kind"] != "table_header":
                    continue
                if unit_id in evidence.data_row_units:
                    contradicted.add(unit_id)
                    continue
                header_rows.add(row)
                break
    if contradicted:
        diagnostics.append(
            {
                "code": "HEADER_EVIDENCE_CONFLICT",
                "unit_ids": sorted(contradicted),
                "detail": "wire row-0 header claim contradicted by shared data rows",
            }
        )

    missing_rows = [
        row
        for row in sorted(scope.row_claims)
        if not any(key[0] == row for key in scope.order)
    ]
    if missing_rows:
        degraded = True
        diagnostics.append(
            {
                "code": "TABLE_ROW_SLOTS_UNAVAILABLE",
                "rows": missing_rows,
                "detail": "observed rows without any captured native slot; table truncated",
            }
        )
    if not scope.slots:
        degraded = True
        diagnostics.append(
            {
                "code": "TABLE_CELLS_UNAVAILABLE",
                "detail": "table claim carries no observed native cell slot",
            }
        )
        return None, degraded

    ordered_keys = sorted(scope.order, key=lambda key: (key[0], key[1]))
    label_by_row: dict[int, _Slot] = {}
    for row in sorted({key[0] for key in ordered_keys}):
        if row in header_rows:
            continue
        row_slots = [scope.slots[key] for key in ordered_keys if key[0] == row]
        if len(row_slots) >= 2:
            label_by_row[row] = row_slots[0]  # leading native slot of the row
    for label in label_by_row.values():
        if not label.text_refs:
            degraded = True
            diagnostics.append({"code": "ROW_LABEL_UNAVAILABLE", "cell_id": label.cell_id})

    context_units = []
    for unit_id in dict.fromkeys(evidence.context.get((scope.parent_id, scope.table_id, scope.page), ())):
        fact = facts[unit_id]
        if fact["parent_id"] != scope.parent_id:
            degraded = True
            diagnostics.append(
                {"code": "FOREIGN_CONTEXT_REF_DROPPED", "unit_id": unit_id}
            )
            continue
        if not fact["text"]:
            degraded = True
            diagnostics.append({"code": "CONTEXT_REF_UNAVAILABLE", "unit_id": unit_id})
            continue
        context_units.append(unit_id)
    context_refs = [
        {"unit_id": unit_id, "char_start": 0, "char_end": len(facts[unit_id]["text"])}
        for unit_id in context_units
    ]

    cells_out = []
    provenance = []
    needed_units: dict[str, None] = {}
    for row, column in ordered_keys:
        work_budget.charge(1)  # one provenance/cell record per observed slot
        slot = scope.slots[(row, column)]
        header_refs = list(context_refs)
        label = label_by_row.get(row)
        if label is not None and label is not slot:
            for ref in label.text_refs:
                if ref not in header_refs:
                    header_refs.append(ref)
        work_budget.charge(len(header_refs))
        for ref in slot.text_refs:
            needed_units[ref["unit_id"]] = None
        for ref in header_refs:
            needed_units[ref["unit_id"]] = None
        if slot.locatable:
            degraded = True
        cells_out.append(
            {
                "cell_id": slot.cell_id,
                "row": row,
                "column": column,
                "row_span": None,
                "column_span": None,
                "presence": "present",
                "text_refs": list(slot.text_refs),
                "header_refs": header_refs,
            }
        )
        provenance.append(
            {
                "kind": "native_slot",
                "cell_id": slot.cell_id,
                "row": row,
                "column": column,
                "row_span": None,
                "column_span": None,
            }
        )

    units_out = {}
    for unit_id in list(needed_units):
        work_budget.charge(1)
        fact = facts[unit_id]
        units_out[unit_id] = {
            "text": fact["text"],
            "parent_id": fact["parent_id"],
            "role": fact["role"],
            "kind": fact["kind"],
            "locator": fact["locator"],
        }
    work_budget.charge(1)  # table finalize
    table = {
        "schema_version": SCHEMA_OUT,
        "scope": {
            "parent_id": scope.parent_id,
            "table_id": scope.table_id,
            "page": scope.page,
        },
        "units": units_out,
        "cells": cells_out,
        "header_rows": sorted(header_rows),
        "provenance": provenance,
        "truncated": bool(missing_rows),
    }
    return table, degraded


__all__ = ["SCHEMA_OUT", "build_pdf_table_observations"]
