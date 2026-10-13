"""Conditional required_context invariants (the "必要槽位" checks).

The contract is conditional, not templated: a slot is required only when the
assertion actually carries that content. Quantity assertions need unit (and
denominator for ratios); qualitative progress must not be forced to invent
numbers. These tests check the explicit structural fields only; they never
judge natural-language entailment.
"""

from __future__ import annotations

import pytest

from helpers import (
    EXPECTED_RECORD_IDS,
    MISSING_BEHAVIOR,
    RECORD_REQUIRED_KEYS,
    REQUIRED_WHEN,
    SLOT_NAMES,
    load_record,
)

NUMERIC_SLOTS = {"quantity", "unit", "denominator"}


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_required_context_entries_shape(record_id: str) -> None:
    record = load_record(record_id)
    entries = record["required_context"]
    assert isinstance(entries, list) and entries, "required_context must be non-empty"
    for entry in entries:
        assert RECORD_REQUIRED_KEYS <= set(entry), f"{record_id} required_context keys"
        for key in ("assertion", "reason"):
            assert isinstance(entry[key], str) and entry[key].strip(), f"{record_id} {key}"
        slots = entry["slots"]
        assert isinstance(slots, list) and slots, f"{record_id} slots must be non-empty"
        assert len(set(slots)) == len(slots), f"{record_id} duplicate slots"
        unknown = set(slots) - SLOT_NAMES
        assert not unknown, f"{record_id} unknown slots: {sorted(unknown)}"
        assert entry["required_when"] in REQUIRED_WHEN, f"{record_id} required_when"
        assert entry["missing_behavior"] in MISSING_BEHAVIOR, f"{record_id} missing_behavior"


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_conditional_slot_binding(record_id: str) -> None:
    record = load_record(record_id)
    for entry in record["required_context"]:
        when = entry["required_when"]
        slots = set(entry["slots"])
        if when == "quantity_emitted":
            assert {"quantity", "unit"} <= slots, (
                f"{record_id}: quantity_emitted assertion must require quantity+unit, "
                f"got {sorted(slots)}"
            )
        elif when == "project_emitted":
            assert "project" in slots, f"{record_id}: project_emitted must require project slot"
        elif when == "explicit_condition_present":
            assert "condition" in slots, (
                f"{record_id}: explicit_condition_present must require condition slot"
            )
        elif when == "always_for_assertion":
            assert slots - NUMERIC_SLOTS, (
                f"{record_id}: always_for_assertion must not demand only numbers; "
                f"qualitative progress must not be forced to invent quantities"
            )


@pytest.mark.parametrize("record_id", EXPECTED_RECORD_IDS)
def test_slot_coverage_over_non_numeric_attribution(record_id: str) -> None:
    record = load_record(record_id)
    covered = set()
    for entry in record["required_context"]:
        covered.update(entry["slots"])
    assert covered & {"subject", "role"}, f"{record_id} must require attribution (subject/role)"


def test_ratio_denominator_requirement_exists() -> None:
    """Rate-like facts somewhere in the package must require a denominator slot."""
    covered = set()
    for record_id in EXPECTED_RECORD_IDS:
        for entry in load_record(record_id)["required_context"]:
            if "denominator" in entry["slots"]:
                covered.add(record_id)
    assert covered, "no record requires denominator; ratios/utilization would lose their base"


def test_stage_spec_conditional_coverage() -> None:
    record = load_record("semantic_stage_progression")
    whens = {entry["required_when"] for entry in record["required_context"]}
    assert {"always_for_assertion", "quantity_emitted", "explicit_condition_present"} <= whens, (
        f"stage spec must conditionally require stage/modality/condition and quantities, got {whens}"
    )
    slot_union = set()
    for entry in record["required_context"]:
        slot_union.update(entry["slots"])
    assert {"stage", "modality", "product", "subject"} <= slot_union


def test_capacity_spec_conditional_coverage() -> None:
    record = load_record("semantic_capacity_project")
    whens = {entry["required_when"] for entry in record["required_context"]}
    assert REQUIRED_WHEN == whens or REQUIRED_WHEN <= whens, (
        f"capacity spec must cover all four conditional modes, got {whens}"
    )
    slot_union = set()
    for entry in record["required_context"]:
        slot_union.update(entry["slots"])
    assert {"project", "quantity", "unit", "period", "condition", "modality"} <= slot_union


def test_semantic_specs_have_key_error_counterexamples() -> None:
    for record_id in ("semantic_stage_progression", "semantic_capacity_project"):
        record = load_record(record_id)
        assert len(record["confusions"]) >= 3, (
            f"{record_id} must carry the key error counterexamples (>=3 confusions)"
        )
        wrong = " ".join(entry["wrong_assertion"] for entry in record["confusions"])
        assert wrong.strip(), f"{record_id} confusions need concrete wrong assertions"
