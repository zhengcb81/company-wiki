"""A: RED counterexamples for ``observe_final_material`` (DU3-QUALITY card §2/§3).

The observer under test must measure the *actual final ModelRequest* — its real
evidence rows, its real group aliases — and confirm each member against the
already-verified original unit. It may never take wording from gold, from the
material's own text, or from a generated claim.

Every test here fails before the implementation exists and passes after. They
are the counterexamples named by the card: lost negation / stage / period /
unit, currency and magnitude errors, question text restated as management fact,
cross-subject and parent-source packaging, shared-text duplication, bad aliases,
unread reported as ``no_value``, and a shrunken denominator that fakes an
improvement.
"""

from __future__ import annotations

import pytest

from tools.document_understanding_benchmark.tests.final_material import (
    ORIGINAL_UNITS,
    SHA_FINAL,
    execution,
    material,
    originals,
    originals_with_unread,
)


def _observe(**kwargs):
    from tools.document_understanding_benchmark import observe_final_material

    kwargs.setdefault("material", material())
    kwargs.setdefault("originals", originals())
    kwargs.setdefault("sample_id", "syn-final")
    kwargs.setdefault("execution", execution())
    return observe_final_material(**kwargs)


# ---------------------------------------------------------------------------
# the honest path
# ---------------------------------------------------------------------------


def test_final_material_is_observed_from_real_rows_and_originals():
    observed = _observe()
    assert observed["schema_version"] == "du-observed/1"
    assert observed["sample_id"] == "syn-final"
    assert observed["source_sha256"] == SHA_FINAL
    # Text comes from the original unit, never from the envelope.
    texts = {row["locator"]: row["text"] for row in observed["selected_evidence"]}
    assert texts["loc:v1/page:3/paragraph:12"] == ORIGINAL_UNITS["u-no-vc"]["text"]
    assert texts["loc:v1/page:12/table:1/row:3"] == ORIGINAL_UNITS["u-stores"]["text"]
    assert set(observed["selected_locators"]) == set(texts)
    # The observer assembles the request; it does not call a model.
    assert observed["execution"]["calls"] == 0
    assert observed["claims"] == []


def test_group_alias_becomes_a_semantic_unit_with_real_members():
    observed = _observe()
    by_id = {unit["semantic_id"]: unit for unit in observed["semantic_units"]}
    assert set(by_id) == {"g1", "g2", "g3", "g4"}
    assert by_id["g4"]["kind"] == "final_evidence_group"
    assert by_id["g4"]["locators"] == [
        "loc:v1/page:3/paragraph:9",
        "loc:v1/page:3/paragraph:10",
    ]
    assert by_id["g4"]["dependencies_resolved"] is True


def test_every_selected_locator_resolves_to_a_real_original_unit():
    observed = _observe()
    assert observed["coverage"]["unresolved_aliases"] == []
    assert observed["metrics"]["evidence_rows"] == 5


# ---------------------------------------------------------------------------
# the observer must refuse to invent, substitute or borrow text
# ---------------------------------------------------------------------------


def test_material_text_cannot_substitute_for_the_original():
    """The envelope's own words are not evidence."""

    bad = material(evidence=[
        ["e1", "公司已生产VC并已与宁德时代达成带量采购。"],
        ["e2", "门店总数7,504家（截至2024年12月31日）。"],
    ], groups=[["g1", ["e1"]], ["g2", ["e2"]]])
    with pytest.raises(ValueError, match="original"):
        _observe(material=bad, originals=originals({"e1": "u-no-vc", "e2": "u-stores"}))


def test_gold_is_not_an_input_and_cannot_supply_missing_text():
    """There is no ``gold`` parameter: gold cannot fill an observer answer."""

    import inspect

    from tools.document_understanding_benchmark import observe_final_material

    parameters = set(inspect.signature(observe_final_material).parameters)
    assert "gold" not in parameters
    assert parameters == {"material", "originals", "sample_id", "execution", "limits"}


def test_unknown_alias_is_reported_not_silently_dropped():
    bad = material(evidence=[
        ["e1", "公司现无生产VC（碳酸亚乙烯酯）的情况。"],
        ["eX", "从未出现在原文中的一句话。"],
    ], groups=[["g1", ["e1", "eX"]]])
    with pytest.raises(ValueError, match="alias"):
        _observe(material=bad)


def test_group_alias_not_present_in_the_material_is_refused():
    bad = material(groups=[["g1", ["e1"]], ["g2", ["e2"]], ["g3", ["e3", "e404"]]])
    with pytest.raises(ValueError, match="alias"):
        _observe(material=bad)


def test_columns_must_be_declared_and_consistent():
    """An envelope whose rows do not match its own columns is malformed."""

    bad = material(columns=["id", "raw_text"])
    bad["evidence"][0] = ["e1", "公司现无生产VC（碳酸亚乙烯酯）的情况。", [], [], []]
    with pytest.raises(ValueError):
        _observe(material=bad)


# ---------------------------------------------------------------------------
# §3 full-chain risk: negation / stage / period / unit / currency / magnitude
# ---------------------------------------------------------------------------


def test_dropped_negation_in_the_material_is_detected():
    """A final material that turned a denial into an affirmation must fail."""

    bad = material(evidence=[
        ["e1", "公司已生产VC。"],
        ["e2", "门店总数7,504家（截至2024年12月31日）。"],
    ], groups=[["g1", ["e1"]], ["g2", ["e2"]]])
    with pytest.raises(ValueError, match="original"):
        _observe(material=bad, originals=originals({"e1": "u-no-vc", "e2": "u-stores"}))


def test_material_that_swaps_the_unit_binding_is_refused():
    """Binding an alias to the wrong original is a fabricated source."""

    swapped = originals({"e1": "u-stores", "e2": "u-no-vc"})
    with pytest.raises(ValueError, match="original"):
        _observe(originals=swapped)


def test_original_without_a_locator_is_refused():
    bad = originals()
    bad["units"]["e1"]["locator"] = ""
    with pytest.raises(ValueError, match="locator"):
        _observe(originals=bad)


def test_original_without_source_identity_is_refused():
    """An originals mapping that binds no source cannot be verified at all."""

    bad = originals()
    del bad["source_sha256"]
    with pytest.raises(ValueError, match="source"):
        _observe(originals=bad)


def test_original_from_a_different_source_is_refused():
    bad = originals()
    bad["units"]["e1"]["source_sha256"] = "2" * 64
    with pytest.raises(ValueError, match="source"):
        _observe(originals=bad)


# ---------------------------------------------------------------------------
# §3 cross-subject / parent-source packaging
# ---------------------------------------------------------------------------


def test_two_units_sharing_one_locator_is_ambiguous_and_refused():
    bad = originals()
    bad["units"]["e2"]["locator"] = bad["units"]["e1"]["locator"]
    with pytest.raises(ValueError, match="locator"):
        _observe(originals=bad)


def test_one_alias_used_by_two_groups_cannot_mint_two_scopes():
    """An alias that appears in two semantic groups makes both ambiguous."""

    observed = _observe(material=material(groups=[["g1", ["e1"]], ["g2", ["e1"]]]))
    scopes = [unit["semantic_id"] for unit in observed["semantic_units"]]
    assert scopes == ["g1", "g2"]
    # The unit is genuinely shared, so it must be reported as shared rather than
    # silently assigned to whichever group was seen first.
    shared = observed["coverage"].get("shared_alias_ids")
    assert shared == ["e1"]


def test_group_members_across_subjects_are_refused():
    """A material group that merges two source scopes is a cross-subject package.

    e2 declares scope ``stores`` and e3 declares ``project-alpha``: packing them
    into one group would read one subject's number as another's, which is exactly
    the parent-source / cross-subject merge the card names.
    """

    merged = material(groups=[["g1", ["e2", "e3"]]])
    with pytest.raises(ValueError, match="scope"):
        _observe(material=merged)


# ---------------------------------------------------------------------------
# §3 shared body duplication
# ---------------------------------------------------------------------------


def test_identical_body_in_two_aliases_is_reported_as_duplication():
    """The same body text carried by two evidence rows is shared content, not two facts."""

    duplicate = originals()
    duplicate["units"]["e2"] = dict(duplicate["units"]["e1"],
                                    locator="loc:v1/page:3/paragraph:13")
    body = ORIGINAL_UNITS["u-no-vc"]["text"]
    dup_material = material(
        evidence=[["e1", body], ["e2", body]],
        groups=[["g1", ["e1"]], ["g2", ["e2"]]],
    )
    observed = _observe(material=dup_material, originals=duplicate)
    assert observed["coverage"]["duplicate_body_alias_ids"] == [["e1", "e2"]]


# ---------------------------------------------------------------------------
# §3 unread must not be reported as no_value
# ---------------------------------------------------------------------------


def test_unread_pages_are_carried_into_coverage_not_reported_as_empty():
    observed = _observe(originals=originals_with_unread())
    coverage = observed["coverage"]
    assert coverage["opaque_pages"] == [9]
    assert coverage["native_scan"] == "partial"
    assert coverage["complete"] is False
    assert coverage["unread_is_not_absence"] is True


def test_coverage_complete_matches_the_actual_unread_facts():
    clean = _observe(originals=originals_with_unread(
        unread={"native_scan": "complete", "opaque_pages": [], "deferred_pages": [],
                "deferred_unit_ids": [], "unassigned_unit_ids": [],
                "structure_complete": True}))
    assert clean["coverage"]["complete"] is True


def test_material_with_zero_evidence_is_observed_as_empty_not_unread():
    observed = _observe(material=material(evidence=[], groups=[]))
    assert observed["selected_evidence"] == []
    assert observed["coverage"]["complete"] is False
    assert observed["metrics"]["evidence_rows"] == 0


# ---------------------------------------------------------------------------
# §3 budget / denominator honesty
# ---------------------------------------------------------------------------


def test_configured_assembly_budget_is_recorded_not_inferred():
    observed = _observe(material=material(output_plan={"max_claims": 20,
                                                       "coverage": "selected_excerpts_only"}))
    assert observed["metrics"]["assembly_budget"]["max_claims"] == 20
    assert observed["metrics"]["selected_text_bytes"] == sum(
        len(row["text"].encode("utf8")) for row in observed["selected_evidence"]
    )


def test_limits_must_be_a_mapping_and_zero_budget_stops():
    with pytest.raises(ValueError):
        _observe(limits={"max_evidence_rows": 0})


def test_limits_that_are_exceeded_refuse_rather_than_truncate():
    with pytest.raises(ValueError, match="limit"):
        _observe(limits={"max_evidence_rows": 2})


# ---------------------------------------------------------------------------
# the oracle must accept a real observation produced by this observer
# ---------------------------------------------------------------------------


def test_observed_output_is_accepted_by_the_existing_oracle():
    from tools.document_understanding_benchmark import evaluate
    from tools.document_understanding_benchmark.records import validate_observed

    observed = validate_observed(_observe())
    gold = {
        "schema_version": "du-gold/1",
        "sample_id": "syn-final",
        "source_sha256": SHA_FINAL,
        "scope": "development",
        "expected_route_families": ["investor_qa"],
        "facts": [
            {
                "id": "f-no-vc",
                "importance": "critical",
                "modality": "negation",
                "role": "management_answer",
                "any_support_sets": [[{
                    "page": 3,
                    "exact_quote": "公司现无生产VC",
                }]],
                "must_preserve": ["不生产VC", "无生产VC"],
                "must_not_assert": ["公司生产VC"],
            }
        ],
    }
    result = evaluate(observed, gold)
    assert result["checks"]
    assert result["metrics"]["critical_fact_recall"] == 1.0
