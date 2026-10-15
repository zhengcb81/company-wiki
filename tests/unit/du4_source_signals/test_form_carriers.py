"""Semantic counterexamples for source form evidence (DU4-FORM card §A).

Every case here is synthetic control unless a docstring names a retained real
observation fixture.  Nothing reads an owner original, a parser, a config or
the network.
"""

from __future__ import annotations

import copy

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

from company_wiki.document_understanding.source_signals import collect_source_signals

FORM_UNIT = "u-form"
TOC_UNIT = "u-toc"


def _lead_units(count: int) -> list[dict]:
    return [
        unit(f"u-lead-{i}", f"Ordinary lead paragraph {i}.", locator=f"loc:v1/paragraph:{i}")
        for i in range(count)
    ]


def _vrsk_shaped_observation() -> dict:
    """Real failure shape: FORM at the fourth unit, many ordinary units after."""
    units = _lead_units(3)
    units.append(unit(FORM_UNIT, "FORM 10-Q", locator="loc:v1/paragraph:4"))
    units.extend(
        unit(f"u-body-{i}", f"Ordinary body paragraph {i}.", locator=f"loc:v1/paragraph:{5 + i}")
        for i in range(40)
    )
    units.append(unit(TOC_UNIT, "Table of Contents", locator="loc:v1/paragraph:3"))
    carriers = [
        carrier(
            "visible_own_form_label",
            [FORM_UNIT],
            [ref(FORM_UNIT, 0, 9)],
        ),
        carrier(
            "visible_inline_xbrl_document_type",
            [FORM_UNIT],
            [ref(FORM_UNIT, 5, 9)],
            attributes={"concept": "dei:DocumentType", "visibility": "visible"},
        ),
    ]
    return observation(units, carriers)


def test_real_nine_char_form_and_inline_dei_are_scoped_evidence():
    result = collect_source_signals(_vrsk_shaped_observation(), work_budget=budget())
    evidence = result["source_form_evidence"]
    assert [entry["value"] for entry in evidence] == ["FORM 10-Q", "10-Q"]
    assert [entry["origin"] for entry in evidence] == [
        "visible_own_form_label",
        "visible_inline_xbrl_document_type",
    ]
    for entry in evidence:
        assert entry["carrier_unit_ids"] == [FORM_UNIT]
        assert entry["parent_id"] == DEFAULT_PARENT
        assert entry["normalized_value"] == "10-Q"
    assert evidence[0]["value_refs"] == [ref(FORM_UNIT, 0, 9)]
    assert evidence[1]["value_refs"] == [ref(FORM_UNIT, 5, 9)]
    assert evidence[1]["concept"] == "dei:DocumentType"


def test_real_carriers_reserved_not_cover_fallback_units():
    result = collect_source_signals(_vrsk_shaped_observation(), work_budget=budget())
    assert result["reserved_unit_ids"] == [FORM_UNIT]
    cited = {
        unit_id
        for entry in result["source_form_evidence"]
        for unit_id in entry["carrier_unit_ids"]
    }
    assert cited == {FORM_UNIT}
    assert TOC_UNIT not in cited
    assert not any(unit_id.startswith("u-lead") for unit_id in cited)


@pytest.mark.parametrize(
    "literal",
    ["10-Q", "10-Q/A", "10-K", "20-F", "40-F", "8-K", "6-K", "S-1", "F-1"],
)
def test_printed_form_literals_are_preserved_without_family(literal):
    text = f"FORM {literal}"
    units = [unit(FORM_UNIT, text)]
    obs = observation(
        units,
        [carrier("visible_own_form_label", [FORM_UNIT], [ref(FORM_UNIT, 0, len(text))])],
    )
    result = collect_source_signals(obs, work_budget=budget())
    evidence = result["source_form_evidence"]
    assert [entry["value"] for entry in evidence] == [text]
    assert evidence[0]["normalized_value"] == literal
    assert "UNRECOGNIZED_FORM_LITERAL" not in code_set(result)
    # observation is not family classification: no route/family may appear.
    forbidden = {"family", "route", "profile_id", "confidence", "subtype", "regime"}
    assert forbidden.isdisjoint(result.keys())
    for entry in evidence:
        assert forbidden.isdisjoint(entry.keys())


def test_unseen_form_literal_keeps_fact_and_reports_diagnostic():
    text = "FORM DEF 14A"
    units = [unit(FORM_UNIT, text)]
    obs = observation(
        units,
        [carrier("visible_own_form_label", [FORM_UNIT], [ref(FORM_UNIT, 0, len(text))])],
    )
    result = collect_source_signals(obs, work_budget=budget())
    evidence = result["source_form_evidence"]
    assert [entry["value"] for entry in evidence] == [text]
    assert evidence[0]["normalized_value"] == "DEF 14A"
    assert "UNRECOGNIZED_FORM_LITERAL" in code_set(result)


def test_same_owner_inline_wrapping_concatenates_within_one_unit():
    # "FORM <ix>10-Q</ix>" normalises to one unit whose spans wrap the label
    # and the inline DEI value; the spans belong to the same DOM owner.
    obs = observation(
        [unit(FORM_UNIT, "FORM 10-Q")],
        [
            carrier(
                "visible_own_form_label",
                [FORM_UNIT],
                [ref(FORM_UNIT, 0, 5), ref(FORM_UNIT, 5, 9)],
            )
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert [entry["value"] for entry in result["source_form_evidence"]] == ["FORM 10-Q"]


def test_split_owner_tokens_are_not_concatenated():
    # "FORM " and "10-Q" live in two different owner units; concatenating them
    # would invent a FORM unit that no native owner produced.
    units = [
        unit("u-owner-a", "FORM ", locator="loc:v1/paragraph:1"),
        unit("u-owner-b", "10-Q", locator="loc:v1/table:1/row:0/column:0", kind="html_table_cell"),
    ]
    obs = observation(
        units,
        [
            carrier(
                "visible_own_form_label",
                ["u-owner-a", "u-owner-b"],
                [ref("u-owner-a", 0, 5), ref("u-owner-b", 0, 4)],
            )
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert "SPLIT_OWNER_VALUE" in code_set(result)


@pytest.mark.parametrize("visibility", ["hidden", "excluded", "external"])
def test_hidden_excluded_external_dei_is_not_visible_fact(visibility):
    obs = observation(
        [unit(FORM_UNIT, "FORM 10-Q")],
        [
            carrier(
                "visible_inline_xbrl_document_type",
                [FORM_UNIT],
                [ref(FORM_UNIT, 5, 9)],
                attributes={"concept": "dei:DocumentType", "visibility": visibility},
            )
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert "NON_VISIBLE_DEI" in code_set(result)
    assert result["reserved_unit_ids"] == []


def test_dei_concept_mismatch_is_not_form_evidence():
    obs = observation(
        [unit(FORM_UNIT, "FORM 10-Q")],
        [
            carrier(
                "visible_inline_xbrl_document_type",
                [FORM_UNIT],
                [ref(FORM_UNIT, 5, 9)],
                attributes={"concept": "dei:EntityRegistrantName", "visibility": "visible"},
            )
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert "DEI_CONCEPT_MISMATCH" in code_set(result)


def test_declared_quarterly_without_observed_carrier_is_not_observed():
    units = _lead_units(6)
    obs = observation(units, [], declared_form="quarterly_report")
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert result["reserved_unit_ids"] == []
    assert "DECLARED_FORM_UNOBSERVED" in code_set(result)


def test_declared_value_conflicting_with_observed_is_diagnostic_only():
    obs = observation(
        [unit(FORM_UNIT, "FORM 10-Q")],
        [
            carrier(
                "visible_own_form_label",
                [FORM_UNIT],
                [ref(FORM_UNIT, 0, 9)],
            )
        ],
        declared_form="10-K",
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert [entry["value"] for entry in result["source_form_evidence"]] == ["FORM 10-Q"]
    assert "DECLARED_FORM_CONFLICT" in code_set(result)


def test_slashed_declared_literal_is_compared_whole():
    text = "FORM 10-Q/A"
    obs = observation(
        [unit(FORM_UNIT, text)],
        [carrier("visible_own_form_label", [FORM_UNIT], [ref(FORM_UNIT, 0, len(text))])],
        declared_form="10-Q/A",
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert [entry["normalized_value"] for entry in result["source_form_evidence"]] == ["10-Q/A"]
    assert "DECLARED_FORM_CONFLICT" not in code_set(result)

    obs = observation(
        [unit(FORM_UNIT, "FORM 10-Q")],
        [carrier("visible_own_form_label", [FORM_UNIT], [ref(FORM_UNIT, 0, 9)])],
        declared_form="10-Q/A",
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert "DECLARED_FORM_CONFLICT" in code_set(result)


def test_many_leading_ordinary_units_do_not_distract_carriers():
    units = _lead_units(120)
    units.append(unit(FORM_UNIT, "FORM 10-Q", locator="loc:v1/paragraph:120"))
    obs = observation(
        units,
        [
            carrier("visible_own_form_label", [FORM_UNIT], [ref(FORM_UNIT, 0, 9)]),
            carrier(
                "visible_inline_xbrl_document_type",
                [FORM_UNIT],
                [ref(FORM_UNIT, 5, 9)],
                attributes={"concept": "dei:DocumentType", "visibility": "visible"},
            ),
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert [entry["value"] for entry in result["source_form_evidence"]] == ["FORM 10-Q", "10-Q"]
    assert result["reserved_unit_ids"] == [FORM_UNIT]


def test_dei_without_visibility_attribute_is_visible_by_kind():
    obs = observation(
        [unit(FORM_UNIT, "FORM 10-Q")],
        [
            carrier(
                "visible_inline_xbrl_document_type",
                [FORM_UNIT],
                [ref(FORM_UNIT, 5, 9)],
                attributes={"concept": "dei:DocumentType"},
            )
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert [entry["value"] for entry in result["source_form_evidence"]] == ["10-Q"]


def test_plain_declared_form_type_can_never_create_observed_evidence():
    obs = observation(
        _lead_units(4),
        [],
        declared_form="10-Q",
        extra={"form_type": "10-Q", "title": "vrsk20250331_10q"},
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert result["reserved_unit_ids"] == []


def test_declarative_attribute_keys_are_ignored_with_diagnostic():
    obs = observation(
        [unit(FORM_UNIT, "FORM 10-Q")],
        [
            carrier(
                "visible_inline_xbrl_document_type",
                [FORM_UNIT],
                [ref(FORM_UNIT, 5, 9)],
                attributes={
                    "concept": "dei:DocumentType",
                    "visibility": "visible",
                    "form_type": "10-K",
                },
            )
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert [entry["value"] for entry in result["source_form_evidence"]] == ["10-Q"]
    assert "DECLARED_ATTRIBUTE_IGNORED" in code_set(result)


def test_same_parent_value_conflict_is_reported_both_values_kept():
    units = [unit("u-a", "FORM 10-Q"), unit("u-b", "FORM 10-K")]
    obs = observation(
        units,
        [
            carrier("visible_own_form_label", ["u-a"], [ref("u-a", 0, 9)]),
            carrier("visible_own_form_label", ["u-b"], [ref("u-b", 0, 9)]),
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    values = [entry["value"] for entry in result["source_form_evidence"]]
    assert values == ["FORM 10-Q", "FORM 10-K"]
    assert "FORM_VALUE_CONFLICT" in code_set(result)


def test_different_parent_values_stay_separate_scoped_facts():
    child_parent = "urn:company-wiki:source:sha256:attachment-10k"
    units = [
        unit("u-main", "FORM 8-K", parent_id=DEFAULT_PARENT),
        unit("u-child", "FORM 10-K", parent_id=child_parent),
    ]
    obs = observation(
        units,
        [
            carrier("visible_own_form_label", ["u-main"], [ref("u-main", 0, 8)]),
            carrier(
                "visible_own_form_label",
                ["u-child"],
                [ref("u-child", 0, 9)],
                parent_id=child_parent,
            ),
        ],
    )
    result = collect_source_signals(obs, work_budget=budget())
    by_parent = {
        entry["parent_id"]: entry["value"] for entry in result["source_form_evidence"]
    }
    assert by_parent == {DEFAULT_PARENT: "FORM 8-K", child_parent: "FORM 10-K"}
    assert "FORM_VALUE_CONFLICT" not in code_set(result)


def test_nonexistent_carrier_cannot_borrow_cover_ids():
    units = _lead_units(3) + [unit(TOC_UNIT, "Table of Contents")]
    obs = observation(
        units,
        [
            carrier(
                "visible_own_form_label",
                ["u-missing"],
                [ref("u-missing", 0, 9)],
            )
        ],
        declared_form="10-Q",
    )
    result = collect_source_signals(obs, work_budget=budget())
    assert result["source_form_evidence"] == []
    assert result["reserved_unit_ids"] == []
    cited = {
        unit_id
        for entry in result["source_form_evidence"]
        for unit_id in entry["carrier_unit_ids"]
    }
    assert TOC_UNIT not in cited
    assert "UNKNOWN_REF_UNIT" in code_set(result)


def test_input_is_never_mutated():
    obs = _vrsk_shaped_observation()
    frozen = copy.deepcopy(obs)
    collect_source_signals(obs, work_budget=budget())
    assert obs == frozen
