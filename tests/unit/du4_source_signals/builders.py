"""Factories for DU4-FORM observation fixtures (synthetic controls only)."""

from __future__ import annotations

from typing import Any
from pathlib import Path


from company_wiki.document_understanding.layout_hints.contract import WorkBudget

PWF_FIXTURES = Path(__file__).resolve().parents[3] / "docs/plans/du4-form-2026-10-15/fixtures"

DEFAULT_PARENT = "urn:company-wiki:source:sha256:synthetic-parent"


def unit(
    unit_id: str,
    text: str,
    *,
    parent_id: str = DEFAULT_PARENT,
    role: str = "company_filing",
    kind: str = "html_paragraph",
    locator: str = "loc:v1/paragraph:0",
    **extra: Any,
) -> dict:
    record = {
        "unit_id": unit_id,
        "text": text,
        "parent_id": parent_id,
        "role": role,
        "kind": kind,
        "locator": locator,
    }
    record.update(extra)
    return record


def ref(unit_id: str, start: int, end: int) -> dict:
    return {"unit_id": unit_id, "char_start": start, "char_end": end}


def whole_ref(unit_id: str, text: str) -> dict:
    return ref(unit_id, 0, len(text))


def carrier(
    kind: str,
    unit_ids: list[str],
    value_refs: list[dict],
    *,
    parent_id: str = DEFAULT_PARENT,
    attributes: dict | None = None,
) -> dict:
    return {
        "kind": kind,
        "unit_ids": list(unit_ids),
        "value_refs": list(value_refs),
        "parent_id": parent_id,
        "attributes": dict(attributes or {}),
    }


def observation(
    units: list[dict],
    carriers: list[dict],
    *,
    declared_form: str | None = None,
    extra: dict | None = None,
) -> dict:
    payload = {
        "schema_version": "du4-source-signal-observation/1",
        "units": {record["unit_id"]: record for record in units},
        "carriers": list(carriers),
    }
    if declared_form is not None:
        payload["declared_form"] = declared_form
    if extra:
        payload.update(extra)
    return payload


def budget(max_work_units: int = 100_000) -> WorkBudget:
    return WorkBudget(max_work_units=max_work_units)


def code_set(result: dict) -> set[str]:
    return {item["code"] for item in result["diagnostics"]}
