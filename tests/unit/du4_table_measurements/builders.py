"""Synthetic ``du4-table-observation/1`` builders for DU4-TABLE tests.

Everything here builds *inputs*; expected outputs live with the individual
semantic counterexamples and were written independently of the
implementation.  Builders never compute bindings — they only lay out units,
text refs and native slots so a test states one fact at a time.
"""

from __future__ import annotations

from typing import Any

DEFAULT_PARENT = "parent-1"


def unit(
    unit_id: str,
    text: str,
    *,
    parent_id: str = DEFAULT_PARENT,
    role: str = "body",
    kind: str = "table_row",
    locator: Any = None,
) -> dict:
    return {
        "unit_id": unit_id,
        "text": text,
        "parent_id": parent_id,
        "role": role,
        "kind": kind,
        "locator": locator if locator is not None else {"page_number": 1, "table_index": 0},
    }


def text_ref(unit_id: str, text: str, needle: str, *, occurrence: int = 1) -> dict:
    """Locate ``needle`` inside ``text`` and return its real char range."""
    start = -1
    pos = 0
    for _ in range(occurrence):
        start = text.find(needle, pos)
        if start < 0:
            raise AssertionError(f"needle {needle!r} occurrence {occurrence} not in unit text")
        pos = start + 1
    return {"unit_id": unit_id, "char_start": start, "char_end": start + len(needle)}


def cell(
    cell_id: str,
    row: int,
    column: int,
    *,
    presence: str = "present",
    text_refs: list[dict] | None = None,
    header_refs: list[dict] | None = None,
    row_span: int | None = None,
    column_span: int | None = None,
) -> dict:
    return {
        "cell_id": cell_id,
        "row": row,
        "column": column,
        "row_span": row_span,
        "column_span": column_span,
        "presence": presence,
        "text_refs": list(text_refs or []),
        "header_refs": list(header_refs or []),
    }


def observation(
    units: dict[str, dict],
    cells: list[dict],
    *,
    parent_id: str = DEFAULT_PARENT,
    table_id: str = "t1",
    page: int | None = 1,
    header_rows: list[int] | None = None,
    provenance: list[dict] | None = None,
    truncated: bool = False,
) -> dict:
    obs: dict[str, Any] = {
        "schema_version": "du4-table-observation/1",
        "scope": {"parent_id": parent_id, "table_id": table_id, "page": page},
        "units": units,
        "cells": cells,
        "truncated": truncated,
    }
    if header_rows is not None:
        obs["header_rows"] = list(header_rows)
    if provenance is not None:
        obs["provenance"] = list(provenance)
    return obs


def period_fields(period: dict | None) -> dict | None:
    """Comparable projection of a period dict (drops raw_label_refs)."""
    if period is None:
        return None
    return {
        "kind": period["kind"],
        "start": period["start"],
        "end": period["end"],
        "duration_months": period["duration_months"],
        "fiscal_label": period["fiscal_label"],
    }


def measurement_for(result: dict, value_ref: dict) -> dict:
    for m in result["measurements"]:
        if m["value_ref"] == value_ref:
            return m
    raise AssertionError(f"no measurement for value_ref {value_ref}")


def column_for(result: dict, column_id: str) -> dict:
    for c in result["columns"]:
        if c["column_id"] == column_id:
            return c
    raise AssertionError(f"no column {column_id}")


def column_by_native(result: dict, native_column: int) -> dict:
    for c in result["columns"]:
        if c["native_column"] == native_column:
            return c
    raise AssertionError(f"no native column {native_column}")


def diagnostic_codes(result: dict) -> list[str]:
    return [d["code"] for d in result["diagnostics"]]
