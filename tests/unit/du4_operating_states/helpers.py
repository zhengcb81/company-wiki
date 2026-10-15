"""Shared builders for the DU4-STATE lane tests.

Inputs are synthetic statement strings or the retained real observation that
ROOT copied into this plan's ``fixtures`` directory. Nothing here reads an
owner original, a production config, the network or the clock.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.operating_states import (
    detect_operating_relations,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "docs" / "plans" / "du4-state-2026-10-15" / "fixtures"
REAL_OBSERVATION = FIXTURES / "cn-ir-observation.json"
REAL_MANIFEST = FIXTURES / "manifest.json"

REAL_ANSWER = (
    "urn:company-wiki:narrative-unit:sha256:"
    "bd75a8c377fefb5f82492bb8191c62d815aa2dae2233cdb3e077107a2dc0b087"
)
REAL_QUESTION = (
    "urn:company-wiki:narrative-unit:sha256:"
    "489d4ff2dfd12e5c2c0ef1fd4d050328bc5c168741c0a1fe6d0d72d0bb824975"
)
REAL_SHAREHOLDER = (
    "urn:company-wiki:narrative-unit:sha256:"
    "dd1466bb3d22568392e6199c9976eb12cfc6dd7a9f0409ea8df5ed522e7a7284"
)

OBSERVATION_SCHEMA = "du4-operating-observation/1"
RELATIONS_SCHEMA = "du4-operating-relations/1"
REF_FIELDS = ("assertion_refs", "actor_refs", "object_refs", "predicate_refs", "qualifier_refs")


def load_real_units() -> dict[str, dict[str, Any]]:
    """The retained real parse observation, as immutable unit inputs."""
    data = json.loads(REAL_OBSERVATION.read_text(encoding="utf-8"))
    units: dict[str, dict[str, Any]] = {}
    for unit in data["target_units"]:
        parent = unit.get("metadata", {}).get("qa_group_id") or "unknown-parent"
        units[unit["unit_id"]] = {**unit, "parent_id": parent}
    return units


def make_unit(
    text: str,
    *,
    unit_id: str = "u1",
    parent_id: str = "p1",
    role: str = "management",
    kind: str = "pdf_text_block",
    locator: str = "loc:test/1",
) -> dict[str, Any]:
    return {
        "text": text,
        "parent_id": parent_id,
        "role": role,
        "kind": kind,
        "locator": locator,
    }


def make_observation(
    units: dict[str, dict[str, Any]],
    *,
    target: str,
    context_unit_ids: list[str] | None = None,
    language: str | None = None,
    schema_version: str = OBSERVATION_SCHEMA,
) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "schema_version": schema_version,
        "unit_id": target,
        "units": dict(units),
    }
    if context_unit_ids is not None:
        observation["context_unit_ids"] = list(context_unit_ids)
    if language is not None:
        observation["language"] = language
    return observation


def run(observation: dict[str, Any], *, max_work_units: int = 100_000) -> tuple[dict[str, Any], WorkBudget]:
    budget = WorkBudget(max_work_units)
    result = detect_operating_relations(observation, work_budget=budget)
    return result, budget


def run_text(
    text: str,
    *,
    role: str = "management",
    unit_id: str = "u1",
    parent_id: str = "p1",
    context: list[tuple[str, str]] | None = None,
    language: str | None = None,
    max_work_units: int = 100_000,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], WorkBudget]:
    """Detect over one synthetic unit; ``context`` items are (text, parent_id)."""
    units: dict[str, dict[str, Any]] = {
        unit_id: make_unit(text, unit_id=unit_id, parent_id=parent_id, role=role)
    }
    context_ids: list[str] = []
    for index, (context_text, context_parent) in enumerate(context or ()):
        context_id = f"c{index}"
        units[context_id] = make_unit(
            context_text, unit_id=context_id, parent_id=context_parent, role="management"
        )
        context_ids.append(context_id)
    observation = make_observation(
        units,
        target=unit_id,
        context_unit_ids=context_ids or None,
        language=language,
    )
    result, budget = run(observation, max_work_units=max_work_units)
    return result, units, budget


def ref_texts(
    units: dict[str, dict[str, Any]], relation: dict[str, Any], field: str
) -> list[str]:
    """Exact original-text slices of one relation ref list."""
    return [
        units[ref["unit_id"]]["text"][ref["char_start"] : ref["char_end"]]
        for ref in relation.get(field, [])
    ]


def assert_refs_valid(
    units: dict[str, dict[str, Any]], result: dict[str, Any]
) -> None:
    """Every ref must land inside its own original unit text."""
    for relation in result["relations"]:
        for field in REF_FIELDS:
            for ref in relation[field]:
                assert ref["unit_id"] in units, ref
                text = units[ref["unit_id"]]["text"]
                assert 0 <= ref["char_start"] < ref["char_end"] <= len(text), ref
                assert text[ref["char_start"] : ref["char_end"]], ref


def signature(relation: dict[str, Any]) -> tuple[str, str, str]:
    return (relation["activity"], relation["stage"], relation["modality"])
