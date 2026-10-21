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
* header rows come only from scope-compatible shared ``header_for`` groups;
  current PDF row-0 wire kinds do not prove observed native header roles;
* current DU2 has no observed row-label relation: preserve all native values
  and report unknown labels instead of promoting the leading slot;
* caption/footnote context refs come from shared ``caption_for``/``footnote_for``
  relations and are dropped with a diagnostic when their unit belongs to a
  different parent;
* ``row_span``/``column_span`` are always ``None`` here: the upstream dropped
  merged spans, and guessing them is forbidden.  Presence is ``present`` for an
  observed whole value (even when its exact location is unknown); partial or
  unproven multi-carrier whole values are ``unavailable`` while refs remain; ``empty``
  presence is only for a slot actually observed as empty, which the PDF
  upstream does not retain — lost slots are simply absent from ``cells``.

Work accounting (the shared logical ``WorkBudget``; no wall-clock claim):

* 1 charge before any input traversal,
* 1 per observation unit examined and 1 per fine-cell entry examined,
* ``(char_end - char_start) // 64`` extra whenever a candidate range is
  actually sliced for comparison (0 for ordinary short values),
* 1 per shared relation record / group member examined,
* native-row indexing/relations/materialization are charged before each item;
  sorting is prepaid n*max(1, n.bit_length()), copies by actual ref count.
  Partial-cell refs remain locatable but whole values are unavailable.

The budget is never created or reset here; exhaustion keeps the tables already
closed and reports ``partial`` instead of a half-built table.  Structural wire
errors (wrong schema, duplicate unit ids, illegal types) raise ``ValueError``;
recoverable evidence gaps become per-item diagnostics.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypeGuard

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
        "CELL_SCOPE_MISMATCH",
        "PARTIAL_CELL_VALUE_UNAVAILABLE",
        "FOREIGN_HEADER_RELATION_DROPPED",
        "HEADER_ROLE_UNCONFIRMED",
        "TABLE_CELLS_UNAVAILABLE",
        "TABLE_ROW_SLOTS_UNAVAILABLE",
        "FOREIGN_CONTEXT_REF_DROPPED",
        "CONTEXT_REF_UNAVAILABLE",
        "ROW_LABEL_UNAVAILABLE",
    }
)


def _is_index(value: Any) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


class _Slot:
    """One observed native slot, gathering the real refs of every carrier unit."""

    __slots__ = ("row", "column", "text_refs", "ref_keys", "locatable", "partial")

    def __init__(self, row: int, column: int) -> None:
        self.row = row
        self.column = column
        self.text_refs: list[dict] = []
        self.ref_keys: set[tuple] = set()
        self.partial = False
        self.locatable = 0  # observed values whose exact location stayed unknown

    @property
    def cell_id(self) -> str:
        return f"r{self.row}c{self.column}"


class _Scope:
    __slots__ = ("parent_id", "table_id", "page", "unit_ids", "row_claims", "slots", "order", "bad_slots")

    def __init__(self, parent_id: Any, table_id: str, page: Any) -> None:
        self.parent_id = parent_id
        self.table_id = table_id
        self.page = page
        self.unit_ids: list[str] = []
        self.row_claims: dict[int, list[str]] = {}
        self.slots: dict[tuple[int, int], _Slot] = {}
        self.order: list[tuple[int, int]] = []
        self.bad_slots = False


class _SharedEvidence:
    def __init__(self) -> None:
        self.header_units: set[str] = set()
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
        work_budget.charge(len(diagnostics))
        degrading = degrading or any(item.get("code") in DEGRADING_CODES for item in diagnostics)
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
        scope.bad_slots = True
        diagnostics.append({"code": "CELL_SLOT_UNAVAILABLE", "unit_id": fact["unit_id"]})
        return
    row = entry.get("row")
    column = entry.get("column")
    entry_table = entry.get("table_id")
    if not _is_index(row) or not _is_index(column):
        scope.bad_slots = True
        diagnostics.append({"code": "CELL_SLOT_UNAVAILABLE", "unit_id": fact["unit_id"]})
        return
    if (("page" in entry and entry["page"] != scope.page)
            or ("source_id" in entry and entry["source_id"] != scope.parent_id)):
        scope.bad_slots = True
        diagnostics.append({"code": "CELL_SCOPE_MISMATCH", "unit_id": fact["unit_id"]})
        return
    if entry_table != scope.table_id or (
        _is_index(row_claim) and int(row) != int(row_claim)
    ):
        scope.bad_slots = True
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
    ref_key = (ref["unit_id"], ref["char_start"], ref["char_end"])
    if ref_key not in slot.ref_keys:
        slot.ref_keys.add(ref_key)
        slot.text_refs.append(ref)
    if entry.get("partial_cell") is True or len(slot.text_refs) > 1:
        slot.partial = True
        diagnostics.append({"code": "PARTIAL_CELL_VALUE_UNAVAILABLE", "unit_id": fact["unit_id"], "row": row, "column": column})


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
        raise ValueError(f"unsupported layout hints schema: {layout_hints.get('schema_version')!r}")
    groups = {}
    for group in layout_hints.get("groups") or ():
        work_budget.charge(1)
        if isinstance(group, Mapping) and isinstance(group.get("group_id"), str):
            groups[group["group_id"]] = group
    scope_by_unit = {}
    for scope in scopes.values():
        work_budget.charge(1)
        for unit_id in scope.unit_ids:
            work_budget.charge(1)
            scope_by_unit[unit_id] = (scope.parent_id, scope.table_id, scope.page)

    def members(group_id):
        group = groups.get(group_id)
        ids = group.get("member_unit_ids") if isinstance(group, Mapping) else None
        ids = ids if isinstance(ids, Sequence) and not isinstance(ids, (str, bytes)) else ()
        for unit_id in ids:
            work_budget.charge(1)
            yield unit_id

    for relation in layout_hints.get("relations") or ():
        work_budget.charge(1)
        if not isinstance(relation, Mapping):
            continue
        kind = relation.get("kind")
        if kind not in ("header_for", "caption_for", "footnote_for"):
            continue
        target_scopes = set()
        for uid in members(relation.get("to_group_id")):
            if uid in scope_by_unit:
                target_scopes.add(scope_by_unit[uid])
        if kind == "header_for":
            for uid in members(relation.get("from_group_id")):
                source_scope = scope_by_unit.get(uid)
                if source_scope is not None and source_scope in target_scopes:
                    evidence.header_units.add(uid)
                elif source_scope is not None and target_scopes:
                    diagnostics.append({"code": "FOREIGN_HEADER_RELATION_DROPPED", "unit_id": uid})
        else:
            context = list(members(relation.get("from_group_id")))
            for scope_key in target_scopes:
                work_budget.charge(1)
                for uid in context:
                    work_budget.charge(1)
                    if uid in facts:
                        evidence.context.setdefault(scope_key, []).append(uid)
    return evidence


def _build_table(scope, facts, evidence, work_budget, diagnostics):
    """One paid native-row index. Unknown roles never become inferred labels."""
    work_budget.charge(1)  # no row/slot traversal with zero remaining work
    degraded = scope.bad_slots
    header_rows = set()
    for row, unit_ids in scope.row_claims.items():
        work_budget.charge(1)
        for uid in unit_ids:
            work_budget.charge(1)
            if uid in evidence.header_units:
                header_rows.add(row)
            elif facts[uid]["kind"] == "table_header":
                # Current PDF wire kind is synthesized from row==0; it is not
                # an observed native TH role and cannot prove a header alone.
                diagnostics.append({"code": "HEADER_ROLE_UNCONFIRMED", "unit_id": uid})
                degraded = True
    count = len(scope.order)
    work_budget.charge(count * max(1, count.bit_length()))
    ordered_keys = sorted(scope.order)
    rows: dict[int, list[Any]] = {}
    for key in ordered_keys:
        work_budget.charge(1)
        rows.setdefault(key[0], []).append(scope.slots[key])
    missing_rows = []
    for row in scope.row_claims:
        work_budget.charge(1)
        if row not in rows:
            missing_rows.append(row)
    if missing_rows:
        degraded = True
        diagnostics.append({"code": "TABLE_ROW_SLOTS_UNAVAILABLE", "rows": missing_rows})
    if not scope.slots:
        diagnostics.append({"code": "TABLE_CELLS_UNAVAILABLE"})
        return None, True
    # DU2 currently exposes header_for, not an observed row-label role.
    # Keep every native value/ref; first column is never a license to drop it.
    for row, slots in rows.items():
        work_budget.charge(1)
        if row not in header_rows and len(slots) > 1:
            degraded = True
            diagnostics.append({"code": "ROW_LABEL_UNAVAILABLE", "row": row})
    context_units: dict[str, None] = {}
    for uid in evidence.context.get((scope.parent_id, scope.table_id, scope.page), ()):
        work_budget.charge(1)
        fact = facts[uid]
        if fact["parent_id"] != scope.parent_id:
            degraded = True
            diagnostics.append({"code": "FOREIGN_CONTEXT_REF_DROPPED", "unit_id": uid})
        elif not fact["text"]:
            degraded = True
            diagnostics.append({"code": "CONTEXT_REF_UNAVAILABLE", "unit_id": uid})
        else:
            context_units[uid] = None
    context_refs: list[dict[str, Any]] = []
    for uid in context_units:
        work_budget.charge(1)
        context_refs.append({"unit_id": uid, "char_start": 0, "char_end": len(facts[uid]["text"])})
    cells_out = []
    provenance = []
    needed_units: dict[str, Any] = {}
    for row, column in ordered_keys:
        work_budget.charge(1)
        slot = scope.slots[(row, column)]
        work_budget.charge(len(context_refs) + len(slot.text_refs))
        header_refs = list(context_refs)
        refs = list(slot.text_refs)
        for ref in refs:
            needed_units[ref["unit_id"]] = None
        for ref in header_refs:
            needed_units[ref["unit_id"]] = None
        if slot.locatable or slot.partial:
            degraded = True
        cells_out.append({"cell_id": slot.cell_id, "row": row, "column": column,
                          "row_span": None, "column_span": None,
                          "presence": "unavailable" if slot.partial else "present",
                          "text_refs": refs, "header_refs": header_refs})
        provenance.append({"kind": "native_slot", "cell_id": slot.cell_id,
                           "row": row, "column": column, "row_span": None, "column_span": None})
    units_out = {}
    for uid in needed_units:
        work_budget.charge(1)
        fact = facts[uid]
        units_out[uid] = {key: fact[key] for key in ("text", "parent_id", "role", "kind", "locator")}
    work_budget.charge(len(header_rows) * max(1, len(header_rows).bit_length()) + 1)
    table = {"schema_version": SCHEMA_OUT,
             "scope": {"parent_id": scope.parent_id, "table_id": scope.table_id, "page": scope.page},
             "units": units_out, "cells": cells_out, "header_rows": sorted(header_rows),
             "provenance": provenance, "truncated": bool(missing_rows or scope.bad_slots)}
    return table, degraded


__all__ = ["SCHEMA_OUT", "build_pdf_table_observations"]
