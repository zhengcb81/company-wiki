"""Contract, budget and determinism controls (DU4-FORM card §A/§B).

Structural malformation raises ``ValueError``; recoverable evidence problems
stay per-item diagnostics; the caller-owned ``WorkBudget`` is the only work
account and exhaustion keeps determined results instead of claiming reads.
"""

from __future__ import annotations

import copy
import json

import pytest

from .builders import (
    DEFAULT_PARENT,
    budget,
    carrier,
    code_set,
    observation,
    ref,
    unit,
)

from company_wiki.document_understanding.source_signals import (
    SCHEMA_OUT,
    collect_source_signals,
)


def _simple_form_observation() -> dict:
    return observation(
        [unit("u-form", "FORM 10-Q")],
        [carrier("visible_own_form_label", ["u-form"], [ref("u-form", 0, 9)])],
    )


def test_wrong_schema_version_raises():
    obs = _simple_form_observation()
    obs["schema_version"] = "du4-source-signal-observation/2"
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())


def test_structural_shape_errors_raise():
    with pytest.raises(ValueError):
        collect_source_signals({"schema_version": "du4-source-signal-observation/1"}, work_budget=budget())
    obs = _simple_form_observation()
    obs["units"] = []
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())
    obs = _simple_form_observation()
    obs["carriers"] = {}
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())


def test_missing_unit_field_raises():
    obs = _simple_form_observation()
    del obs["units"]["u-form"]["parent_id"]
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())


def test_illegal_reference_indices_raise():
    obs = _simple_form_observation()
    obs["carriers"][0]["value_refs"] = [ref("u-form", -1, 4)]
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())
    obs = _simple_form_observation()
    obs["carriers"][0]["value_refs"] = [ref("u-form", 6, 3)]
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())
    obs = _simple_form_observation()
    obs["carriers"][0]["value_refs"] = [{"unit_id": "u-form", "char_start": True, "char_end": 3}]
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())


def test_duplicate_carrier_unit_id_raises():
    obs = _simple_form_observation()
    obs["carriers"][0]["unit_ids"] = ["u-form", "u-form"]
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())


def test_unknown_carrier_kind_raises():
    obs = _simple_form_observation()
    obs["carriers"][0]["kind"] = "provider_form_type"
    with pytest.raises(ValueError):
        collect_source_signals(obs, work_budget=budget())


def test_ref_past_source_text_is_unresolved_not_clamped():
    obs = observation(
        [unit("u-form", "FORM 10")],
        [carrier("visible_own_form_label", ["u-form"], [ref("u-form", 0, 64)])],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert "REF_EXCEEDS_TEXT" in code_set(result)
    assert result["status"] == "unavailable"


def test_empty_span_ref_is_not_a_value():
    obs = observation(
        [unit("u-form", "FORM 10-Q")],
        [carrier("visible_own_form_label", ["u-form"], [ref("u-form", 0, 0)])],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert "EMPTY_VALUE_REF" in code_set(result)


def test_ref_outside_carrier_units_is_not_borrowed():
    obs = observation(
        [unit("u-form", "FORM 10-Q"), unit("u-cover", "FORM 10-K")],
        [carrier("visible_own_form_label", ["u-form"], [ref("u-cover", 0, 9)])],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert "REF_OUTSIDE_CARRIER" in code_set(result)


def test_zero_budget_is_partial_and_claims_nothing():
    obs = _simple_form_observation()
    ledger = budget(0)
    result = collect_source_signals(obs, work_budget=ledger)
    assert result["status"] == "partial"
    assert result["source_form_evidence"] == []
    assert result["turn_evidence"] == []
    assert result["reserved_unit_ids"] == []
    assert result["work_used"] == 0
    assert "WORK_BUDGET_EXCEEDED" in code_set(result)
    assert result["observed_counts"] == {
        "units_indexed": 0,
        "carriers_seen": 0,
        "carriers_resolved": 0,
        "carriers_dropped": 0,
        "evidence_chars": 0,
        "reserved_unit_chars": 0,
    }


def test_low_budget_keeps_determined_results_and_counts():
    units = [unit("u-a", "FORM 10-Q"), unit("u-b", "FORM 10-K")]
    obs = observation(
        units,
        [
            carrier("visible_own_form_label", ["u-a"], [ref("u-a", 0, 9)]),
            carrier("visible_own_form_label", ["u-b"], [ref("u-b", 0, 9)]),
        ],
    )
    ledger = budget(0)
    result = collect_source_signals(obs, work_budget=ledger)
    assert result["status"] == "partial"
    assert result["source_form_evidence"] == []

    # 2 units + 1 carrier + 1 carrier unit + 1 value ref: the first carrier
    # resolves, the second is honestly not read.
    ledger = budget(5)
    result = collect_source_signals(obs, work_budget=ledger)
    assert result["status"] == "partial"
    assert [entry["value"] for entry in result["source_form_evidence"]] == ["FORM 10-Q"]
    assert result["work_used"] == 5
    assert ledger.used == 5
    assert "WORK_BUDGET_EXCEEDED" in code_set(result)


def test_duplicate_carriers_deduplicate_with_diagnostic():
    unit_a = unit("u-form", "FORM 10-Q")
    entry = carrier("visible_own_form_label", ["u-form"], [ref("u-form", 0, 9)])
    obs = observation([unit_a], [entry, copy.deepcopy(entry)])
    result = collect_source_signals(obs, work_budget=budget())
    assert [e["value"] for e in result["source_form_evidence"]] == ["FORM 10-Q"]
    assert result["reserved_unit_ids"] == ["u-form"]
    assert "DUPLICATE_CARRIER" in code_set(result)


def test_output_is_deterministic_and_json_serialisable():
    obs = observation(
        [unit("u-form", "FORM 10-Q"), unit("u-cell", "Revenues:")],
        [carrier("visible_own_form_label", ["u-form"], [ref("u-form", 0, 9)])],
    )
    first = collect_source_signals(obs, work_budget=budget())
    second = collect_source_signals(copy.deepcopy(obs), work_budget=budget())
    assert first == second
    json.dumps(first)
    assert first["schema_version"] == SCHEMA_OUT


def test_large_observation_work_is_honestly_metered():
    units = [unit(f"u-{i}", f"Paragraph {i}.") for i in range(50)]
    carriers = [
        carrier(
            "native_speaker_turn",
            [f"u-{2 * i}", f"u-{2 * i + 1}"],
            [ref(f"u-{2 * i}", 0, 4)],
            attributes={"speaker": "Voice", "turn_id": f"t-{i}"},
        )
        for i in range(5)
    ]
    obs = observation(units, carriers)
    ledger = budget(100_000)
    result = collect_source_signals(obs, work_budget=ledger)
    # per unit + per carrier + per carrier unit id + per value ref
    assert result["work_used"] == 50 + 5 + 5 * 2 + 5
    assert ledger.used == result["work_used"]
    assert result["status"] == "complete"
    assert len(result["turn_evidence"]) == 5
    counts = result["observed_counts"]
    assert counts["units_indexed"] == 50
    assert counts["carriers_seen"] == 5
    assert counts["carriers_resolved"] == 5
    assert counts["carriers_dropped"] == 0
    # 5 speaker spans of 4 chars + 5 whole body units of 12 chars
    assert counts["evidence_chars"] == 5 * 4 + 5 * 12
    # 10 reserved carrier units of 12 chars each
    assert counts["reserved_unit_chars"] == 10 * 12


def test_status_complete_partial_unavailable():
    clean = collect_source_signals(_simple_form_observation(), work_budget=budget())
    assert clean["status"] == "complete"

    mixed = collect_source_signals(
        observation(
            [unit("u-form", "FORM 10-Q"), unit("u-hidden", "FORM 10-K")],
            [
                carrier("visible_own_form_label", ["u-form"], [ref("u-form", 0, 9)]),
                carrier(
                    "visible_inline_xbrl_document_type",
                    ["u-hidden"],
                    [ref("u-hidden", 5, 9)],
                    attributes={"visibility": "hidden"},
                ),
            ],
        ),
        work_budget=budget(),
    )
    assert mixed["status"] == "partial"
    assert mixed["observed_counts"]["carriers_resolved"] == 1
    assert mixed["observed_counts"]["carriers_dropped"] == 1

    none_obtainable = collect_source_signals(
        observation(
            [unit("u-hidden", "FORM 10-K")],
            [
                carrier(
                    "visible_inline_xbrl_document_type",
                    ["u-hidden"],
                    [ref("u-hidden", 5, 9)],
                    attributes={"visibility": "hidden"},
                )
            ],
        ),
        work_budget=budget(),
    )
    assert none_obtainable["status"] == "unavailable"


def test_never_route_family_or_confidence_fields():
    result = collect_source_signals(_simple_form_observation(), work_budget=budget())
    forbidden = {
        "family",
        "route",
        "profile_id",
        "confidence",
        "subtype",
        "regime",
        "alternatives",
        "disposition_hint",
    }

    def walk(node):
        if isinstance(node, dict):
            assert forbidden.isdisjoint(node.keys())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(result)


def test_value_conflict_among_determined_evidence_survives_exhaustion():
    units = [unit("u-a", "FORM 10-Q"), unit("u-b", "FORM 10-K"), unit("u-c", "FORM 8-K")]
    obs = observation(
        units,
        [
            carrier("visible_own_form_label", ["u-a"], [ref("u-a", 0, 9)]),
            carrier("visible_own_form_label", ["u-b"], [ref("u-b", 0, 9)]),
            carrier("visible_own_form_label", ["u-c"], [ref("u-c", 0, 8)]),
        ],
        declared_form="20-F",
    )
    # 3 unit-index charges + 2 full carriers (3 each) + the third carrier's own
    # charge = 10; the third carrier's unit charge then exhausts the budget.
    ledger = budget(10)
    result = collect_source_signals(obs, work_budget=ledger)
    assert result["work_used"] == 10
    assert [entry["value"] for entry in result["source_form_evidence"]] == [
        "FORM 10-Q",
        "FORM 10-K",
    ]
    codes = code_set(result)
    assert "WORK_BUDGET_EXCEEDED" in codes
    assert "FORM_VALUE_CONFLICT" in codes
    assert "DECLARED_FORM_CONFLICT" in codes
    assert result["status"] == "partial"


def test_second_budget_is_never_created_or_reset():
    ledger = budget(1_000)
    collect_source_signals(_simple_form_observation(), work_budget=ledger)
    used_once = ledger.used
    assert used_once > 0
    collect_source_signals(_simple_form_observation(), work_budget=ledger)
    assert ledger.used > used_once


def test_no_parent_mismatch_is_silently_mixed():
    other = "urn:company-wiki:source:sha256:child"
    units = [
        unit("u-main", "FORM 8-K"),
        unit("u-child", "FORM 10-K", parent_id=other),
    ]
    obs = observation(
        units,
        [
            carrier(
                "visible_own_form_label",
                ["u-main", "u-child"],
                [ref("u-main", 0, 8), ref("u-child", 0, 9)],
            )
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert "CARRIER_PARENT_MISMATCH" in code_set(result)
    assert result["reserved_unit_ids"] == []
    assert DEFAULT_PARENT in {u["parent_id"] for u in units}
