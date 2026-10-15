"""Projection adapter: retained real HK table observation -> du4-table-observation/1.

The retained packet (``fixtures/hk-table-observation.json.gz``) keeps a dedup
string table, per-row replay units and the native ``table.extract()`` slot grid
with cell boxes.  This adapter only *projects* those retained facts into the
frozen input contract; it never binds values, never re-parses the original and
never repairs the selection.

Native facts (taken verbatim from the packet):
- unit ids, unit texts (resolved through the string table), native coordinates
  (page / table index / row index), per-row native slots (``raw_rows`` slots or
  unit ``row_cells``) and retained cell boxes.

Adapter-derived (documented, not native):
- ``parent_id`` grouping id (the packet keeps no document id),
- ``role`` placeholder ``"body"`` and ``kind`` ``table_header``/``table_row``,
- ``header_rows = [0, 1, 2, 3]``: the packet's native ``header`` field proves
  row 0; rows 1-3 hold only period/year labels in this fixture's tables,
- ``row_span``/``column_span`` for cells whose retained box was projected onto
  the retained slot grid bands (recorded again in ``provenance`` fine_geometry
  records with the original bbox),
- ``truncated``: set when a table's unit rows are not all covered by the
  captured ``raw_rows`` (the packet-level capture itself is marked truncated).
"""

from __future__ import annotations

import functools
import gzip
import json
from pathlib import Path
from typing import Any

EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "plans"
    / "du4-table-2026-10-15"
    / "fixtures"
    / "hk-table-observation.json.gz"
)
HEADER_ROWS = (0, 1, 2, 3)


@functools.cache
def load_packet() -> dict:
    with gzip.open(FIXTURE, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _locate(row_text: str, needle: str, cursor: int) -> tuple[int, int] | None:
    idx = row_text.find(needle, cursor)
    if idx < 0:
        idx = row_text.find(needle)
        if idx < 0:
            return None
    return idx, idx + len(needle)


def _bands(boxes_by_row: dict[int, list], slot_counts: dict[int, int]):
    """Column x-bands from the first fully-boxed disjoint grid row, y-bands per row."""
    x_bands: list | None = None
    for row in sorted(boxes_by_row):
        boxes = boxes_by_row[row]
        if slot_counts.get(row) != len(boxes) or any(b is None for b in boxes):
            continue
        ordered = sorted(boxes, key=lambda b: b[0])
        if any(ordered[i][2] > ordered[i + 1][0] for i in range(len(ordered) - 1)):
            continue
        x_bands = [(b[0], b[2]) for b in boxes]  # slot order == native column order
        break
    y_bands: dict[int, tuple[float, float]] = {}
    for row, boxes in boxes_by_row.items():
        live = [b for b in boxes if b is not None]
        if live:
            # tightest interval: a merged tall box must not inflate the row band
            y_bands[row] = (max(b[1] for b in live), min(b[3] for b in live))
    return x_bands, y_bands


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def project_table(page: int, table_index: int) -> tuple[dict, dict]:
    packet = load_packet()
    strings: dict[str, str] = packet["strings"]
    tables = [t for t in packet["tables"] if t["page"] == page and t["table_index"] == table_index]
    if len(tables) != 1:
        raise AssertionError(f"expected one retained table for page {page} index {table_index}")
    table = tables[0]
    raw_by_row = {r["row"]: r for r in table["raw_rows"]}
    replay = [
        u
        for u in packet["actual_replay_units"]
        if u["coordinates"]["page_number"] == page and u["coordinates"]["table_index"] == table_index
    ]
    unit_by_row = {u["coordinates"]["row_index"]: u for u in replay}

    parent_id = f"hk-replay:p{page}:t{table_index}"
    units: dict[str, dict] = {}
    row_text_by_row: dict[int, tuple[str, str]] = {}
    for u in replay:
        text = strings[u["raw_text_ref"]]
        row = u["coordinates"]["row_index"]
        row_text_by_row[row] = (u["unit_id"], text)
        units[u["unit_id"]] = {
            "unit_id": u["unit_id"],
            "text": text,
            "parent_id": parent_id,
            "role": "body",
            "kind": "table_header" if row in HEADER_ROWS else "table_row",
            "locator": dict(u["coordinates"]),
        }

    boxes_by_row: dict[int, list] = {}
    slot_counts: dict[int, int] = {}
    for r in raw_by_row.values():
        boxes_by_row[r["row"]] = list(r["cell_boxes"])
        slot_counts[r["row"]] = r["slot_count"]
    x_bands, y_bands = _bands(boxes_by_row, slot_counts)

    cells: list[dict] = []
    provenance: list[dict] = []
    spans_by_cell: dict[str, tuple[int | None, int | None]] = {}
    coverage: set[tuple[int, int]] = set()

    def add_cell(cell_id: str, row: int, column: int, presence: str, refs: list[dict], box) -> None:
        row_span: int | None = None
        column_span: int | None = None
        if box is not None:
            covered_cols = [
                c
                for c, band in enumerate(x_bands or [])
                if _overlap((box[0], box[2]), band) > 0.5 * (band[1] - band[0])
            ]
            covered_rows = [
                r
                for r, band in y_bands.items()
                if _overlap((box[1], box[3]), band) > 0.5 * (band[1] - band[0])
            ]
            column_span = len(covered_cols) if x_bands is not None else None
            row_span = len(covered_rows) if y_bands else None
            if row_span is not None and row_span > 1 or column_span is not None and column_span > 1:
                provenance.append(
                    {
                        "cell_id": cell_id,
                        "kind": "fine_geometry",
                        "bbox": list(box),
                        "row_span": row_span,
                        "column_span": column_span,
                    }
                )
                for rr in range(row, row + (row_span or 1)):
                    for cc in range(column, column + (column_span or 1)):
                        if (rr, cc) != (row, column):
                            coverage.add((rr, cc))
        spans_by_cell[cell_id] = (row_span, column_span)
        cells.append(
            {
                "cell_id": cell_id,
                "row": row,
                "column": column,
                "row_span": row_span,
                "column_span": column_span,
                "presence": presence,
                "text_refs": refs,
                "header_refs": [],
            }
        )

    all_rows = sorted(set(raw_by_row) | set(unit_by_row))
    for row in all_rows:
        row_text = row_text_by_row.get(row)
        unit_id, text = row_text if row_text else (None, "")
        cursor = 0
        if row in raw_by_row:
            slots = raw_by_row[row]["slots"]
            boxes = raw_by_row[row]["cell_boxes"]
            slot_facts_retained = True
        else:
            # unit row_cells keep no kind/box: '' may be a real empty or a none slot
            slots = [
                {"kind": "text", "text_ref": h} for h in unit_by_row[row]["row_cells"]
            ]
            boxes = [None] * len(slots)
            slot_facts_retained = False
        for column, slot in enumerate(slots):
            cell_id = f"r{row}c{column}"
            box = boxes[column] if column < len(boxes) else None
            if slot["kind"] != "text":
                presence = "merged_unknown" if (row, column) in coverage else "unavailable"
                add_cell(cell_id, row, column, presence, [], box)
                continue
            s = strings[slot["text_ref"]]
            if s == "":
                presence = "empty" if slot_facts_retained else "unavailable"
                add_cell(cell_id, row, column, presence, [], box)
                continue
            span = _locate(text, s, cursor) if unit_id else None
            if span is None:
                add_cell(cell_id, row, column, "present", [], box)
                continue
            cursor = span[1]
            ref = {"unit_id": unit_id, "char_start": span[0], "char_end": span[1]}
            add_cell(cell_id, row, column, "present", [ref], box)

    # kind='none' slots inside a derived merged extent are merged, not missing
    for c in cells:
        if c["presence"] != "unavailable":
            continue
        if (c["row"], c["column"]) in coverage:
            c["presence"] = "merged_unknown"

    truncated = any(r not in raw_by_row for r in unit_by_row)
    obs = {
        "schema_version": "du4-table-observation/1",
        "scope": {"parent_id": parent_id, "table_id": str(table_index), "page": page},
        "units": units,
        "cells": cells,
        "header_rows": [r for r in HEADER_ROWS if r in all_rows],
        "provenance": provenance,
        "truncated": truncated,
    }
    facts = {
        "page": page,
        "table_index": table_index,
        "capture": dict(packet["capture"]),
        "native_units": len(units),
        "cells_by_presence": {
            p: sum(1 for c in cells if c["presence"] == p)
            for p in ("present", "empty", "unavailable", "merged_unknown")
        },
        "merged_extent_cells": sum(1 for c in cells if (c["row_span"] or 1) > 1 or (c["column_span"] or 1) > 1),
        "truncated": truncated,
    }
    return obs, facts


def all_tables() -> list[tuple[int, int]]:
    packet = load_packet()
    return [(t["page"], t["table_index"]) for t in packet["tables"]]


def projection() -> dict[str, Any]:
    """Full projection bundle for reporting: every retained table plus facts."""
    out: dict[str, Any] = {}
    for page, table_index in all_tables():
        obs, facts = project_table(page, table_index)
        out[f"p{page}t{table_index}"] = {"observation": obs, "facts": facts}
    return out
