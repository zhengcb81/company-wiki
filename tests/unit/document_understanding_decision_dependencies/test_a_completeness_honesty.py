"""A-node RED: honesty about incomplete inventories and unavailable reuse evidence.

The card's rule is asymmetric on purpose: an incomplete input may report
``partial``/``unavailable``, and may never report ``same``. A component that cannot prove
it saw the whole decision inventory must not hand the cache a green light.
"""

from __future__ import annotations

import pytest
from fixtures.document_understanding_decision_dependencies import builders as b

from .wire_contract import (
    assert_comparison_shape,
    assert_frozen_shape,
    import_decision_module,
)


def _freeze(trace_value, **limits):
    frozen = import_decision_module().freeze_decision_dependencies(
        trace_value, limits=limits or None
    )
    assert_frozen_shape(frozen)
    return frozen


def _compare(frozen, current, **limits):
    result = import_decision_module().compare_decision_dependencies(
        frozen, current, limits=limits or None
    )
    assert_comparison_shape(result)
    return result


# --- the explicit incompleteness flag --------------------------------------------------


def test_an_incomplete_inventory_freezes_partial():
    frozen = _freeze(b.trace(**{**b.base_trace(), "inventory_complete": False}))
    assert frozen["status"] == "partial"
    assert frozen["diagnostics"], "partial must say why"
    assert "INVENTORY_NOT_COMPLETE" in {item.get("code") for item in frozen["diagnostics"]}


def test_an_incomplete_inventory_can_never_compare_same():
    complete = _freeze(b.base_trace())
    incomplete = _freeze(b.trace(**{**b.base_trace(), "inventory_complete": False}))
    cases = (
        (incomplete, b.base_trace()),
        (complete, {**b.base_trace(), "inventory_complete": False}),
        (incomplete, {**b.base_trace(), "inventory_complete": False}),
    )
    for frozen, current in cases:
        result = _compare(frozen, current)
        assert result["status"] != "same", result
        assert result["diagnostics"], result


def test_partial_is_not_valid_reuse_evidence():
    """``partial`` may carry a digest for lineage, but never a reusable verdict."""
    frozen = _freeze(b.trace(**{**b.base_trace(), "inventory_complete": False}))
    assert frozen["status"] == "partial"
    result = _compare(frozen, {**b.base_trace(), "inventory_complete": False})
    assert result["status"] == "unavailable"


def test_missing_inventory_complete_is_treated_as_incomplete():
    """Absence must not be read as "yes, everything is here"."""
    trace_value = b.base_trace()
    del trace_value["inventory_complete"]
    frozen = _freeze(trace_value)
    assert frozen["status"] == "partial"
    assert "INVENTORY_UNKNOWN" in {item.get("code") for item in frozen["diagnostics"]}


def test_a_non_boolean_inventory_flag_is_rejected():
    trace_value = b.base_trace()
    trace_value["inventory_complete"] = "yes"
    with pytest.raises((ValueError, TypeError)):
        import_decision_module().freeze_decision_dependencies(trace_value)


# --- empty and degenerate inputs -------------------------------------------------------


def test_an_empty_decision_domain_is_not_automatic_reuse_evidence():
    """A trace with no scopes and no candidates cannot prove a decision was inspected."""
    empty = b.trace(scopes=[], components=[], candidates=[])
    frozen = _freeze(empty)
    assert frozen["status"] == "partial"
    assert "EMPTY_DECISION_DOMAIN" in {item.get("code") for item in frozen["diagnostics"]}
    result = _compare(frozen, empty)
    assert result["status"] == "unavailable"


def test_no_candidate_inventory_blocks_complete_status():
    """A decision domain that recorded no candidate cannot be a complete inventory.

    Whatever the caller attests, a domain with zero candidate membership shows nothing
    that could be reused and nothing that could be compared, so it must not freeze as
    ``complete`` -- that is the shape a "winners only" trace would take.
    """
    trace_value = b.trace(
        scopes=[b.scope("scope_parent")],
        components=[b.component("c1", content={"policy": "x"}, matcher={"s": ["y"]},
                                scope_ids=["scope_parent"])],
        candidates=[],
        versions=b.VERSIONS,
    )
    frozen = _freeze(trace_value)
    assert frozen["status"] == "partial"
    codes = {item.get("code") for item in frozen["diagnostics"]}
    assert "MISSING_CANDIDATES" in codes
    assert "NO_PARTICIPATING_COMPONENT" in codes
    assert frozen["candidates"] == []
    assert _compare(frozen, trace_value)["status"] == "unavailable"


# --- legacy / missing trace ------------------------------------------------------------


def test_a_legacy_trace_without_the_new_schema_is_unavailable():
    legacy = {"schema_version": "du-reading-plan/1", "policy_components": [{"id": "c1"}]}
    frozen = _freeze(legacy)
    assert frozen["status"] == "partial"
    result = _compare(frozen, legacy)
    assert result["status"] == "unavailable"
    assert frozen["decision_digest"], "even an unusable freeze keeps a lineage digest"


def test_a_legacy_production_payload_is_reported_as_a_legacy_diagnostic():
    """The payload production actually has today cannot prove losing candidates.

    ``strategy_binding.bind_reading_plan`` publishes a ``du-reading-plan/1`` mapping whose
    ``policy_components`` list holds only *adopted* components. That is not a decision
    inventory -- it never recorded the candidates that were inspected and lost -- so it
    must be reported as a legacy artefact and must never be certified.
    """
    legacy_production = {
        "schema_version": "du-reading-plan/1",
        "structure": {"sections": []},
        "unit_profiles": {},
        "diagnostics": [],
        "used_profiles": [{"profile_id": "cn_annual", "profile_version": "1.0.0",
                           "reading_profile_key": None, "policy_components": []}],
        "policy_components": [
            {"kind": "family_policy", "id": "cn_annual_report", "version": "1.0.1",
             "content_digest": b.content_digest({"policy": "cn_annual"})}
        ],
    }
    frozen = _freeze(legacy_production)
    assert frozen["status"] == "partial"
    assert "LEGACY_TRACE_VERSION" in {item.get("code") for item in frozen["diagnostics"]}
    assert frozen["decision_digest"]
    assert _compare(frozen, legacy_production)["status"] == "unavailable"


def test_the_adopted_component_list_alone_is_not_a_decision_inventory():
    """A list of adopted components is a winner list, not the decision it came from."""
    adopted_only = {
        "schema_version": "du-decision-trace/1",
        "scopes": [b.scope("scope_parent")],
        "components": [
            b.component("c1", content={"policy": "core_business"}, matcher={"signals": ["x"]},
                        scope_ids=["scope_parent"])
        ],
        "candidates": [],
        "versions": b.VERSIONS,
        "inventory_complete": True,
    }
    frozen = _freeze(adopted_only)
    assert frozen["status"] == "partial"
    assert "MISSING_CANDIDATES" in {item.get("code") for item in frozen["diagnostics"]}
    assert "NO_PARTICIPATING_COMPONENT" in {item.get("code") for item in frozen["diagnostics"]}
    assert _compare(frozen, adopted_only)["status"] == "unavailable"


def test_comparison_of_two_legacy_inputs_is_unavailable_not_same():
    legacy = {"policy_components": [{"id": "c1", "version": "1.0.0"}]}
    frozen = _freeze(legacy)
    result = _compare(frozen, dict(legacy))
    assert result["status"] == "unavailable"


# --- a winner list is not an inventory --------------------------------------------------


def test_a_winners_only_inventory_cannot_be_laundered_into_same():
    """The caller may not pass just the final winner as if it were the whole trace.

    The component must notice the shape it was handed is not a decision domain and must
    refuse to certify reuse.
    """
    winners_only = {
        "schema_version": "du-decision-trace/1",
        "scopes": [b.scope("scope_parent")],
        "components": [
            b.component("c1", content={"policy": "core_business"}, matcher={"signals": ["x"]},
                        scope_ids=["scope_parent"])
        ],
        "candidates": [b.candidate("cand_a", scope_id="scope_parent", component_ids=["c1"])],
        "versions": b.VERSIONS,
        "inventory_complete": False,
    }
    frozen = _freeze(winners_only)
    assert frozen["status"] == "partial"
    assert _compare(frozen, winners_only)["status"] == "unavailable"


def test_a_winners_only_inventory_flagged_complete_still_cannot_match_a_richer_trace():
    base = b.base_trace()
    frozen = _freeze(base)
    winners_only = {
        "schema_version": "du-decision-trace/1",
        "scopes": [b.scope("scope_parent")],
        "components": [base["components"][0]],
        "candidates": [b.candidate("cand_a", scope_id="scope_parent", component_ids=["c1"])],
        "versions": b.VERSIONS,
        "inventory_complete": True,
    }
    result = _compare(frozen, winners_only)
    assert result["status"] == "changed"
    assert result["removed_candidate_ids"] == ["cand_b", "cand_c", "cand_d"]


# --- partial on the current side --------------------------------------------------------


def test_a_current_side_budget_cut_is_not_evidence_of_sameness():
    frozen = _freeze(b.base_trace())
    result = _compare(frozen, b.base_trace(), max_work_units=0)
    assert result["status"] in {"unavailable", "changed"}
    assert result["status"] != "same"
    assert result["diagnostics"]


def test_compare_reports_unavailable_when_limits_block_a_full_freeze():
    current = b.base_trace()
    frozen = _freeze(current)
    result = _compare(frozen, current, max_candidates=1)
    assert result["status"] != "same"
    assert result["diagnostics"]


# --- equal is not a cache hit ----------------------------------------------------------


def test_same_status_does_not_claim_a_cache_hit():
    """``same`` is a statement about this component's input, nothing more."""
    frozen = _freeze(b.base_trace())
    result = _compare(frozen, b.base_trace())
    assert result["status"] == "same"
    for forbidden in ("cache_hit", "cache", "reuse", "reusable", "post_count", "posts"):
        assert forbidden not in result, forbidden
    assert result["schema_version"] == "du-decision-comparison/1"
