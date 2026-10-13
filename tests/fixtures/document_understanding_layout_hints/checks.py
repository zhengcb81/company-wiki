"""Shared assertion helpers for DU2-LAYOUT tests (test-side only)."""

from __future__ import annotations

HINTS_SCHEMA = "du2-layout-hints/1"


def wire_keys(result: dict) -> set:
    return set(result.keys())


def unit_hint(result: dict, unit_id: str) -> dict:
    for hint in result["unit_hints"]:
        if hint["unit_id"] == unit_id:
            return hint
    raise AssertionError(f"no unit_hints entry for {unit_id}")


def group(result: dict, group_id: str) -> dict:
    for item in result["groups"]:
        if item["group_id"] == group_id:
            return item
    raise AssertionError(f"no group {group_id}")


def groups_of_kind(result: dict, kind: str) -> list[dict]:
    return [item for item in result["groups"] if item["kind"] == kind]


def relations_of_kind(result: dict, kind: str) -> list[dict]:
    return [item for item in result["relations"] if item["kind"] == kind]


def group_containing(result: dict, unit_id: str, kind: str | None = None) -> list[dict]:
    out = []
    for item in result["groups"]:
        if kind is not None and item["kind"] != kind:
            continue
        if unit_id in item["member_unit_ids"]:
            out.append(item)
    return out


def all_unit_ids(observation: dict) -> set:
    ids: set = set()
    for page in observation["pages"]:
        for unit in page["units"]:
            ids.add(unit["unit_id"])
    return ids


def find_keys(obj, key: str) -> list:
    """Collect every value stored under ``key`` anywhere in a JSON structure."""
    found: list = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                found.append(v)
            found.extend(find_keys(v, key))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(find_keys(item, key))
    return found


def row_index_map(result: dict) -> dict:
    """Map table_row group_id -> parent_table_id for quick checks."""
    return {item["group_id"]: item["parent_table_id"] for item in result["groups"] if item["kind"] == "table_row"}
