"""A-node RED: the dependency mutation matrix.

Every case here is a *causal* difference the card demands: a change to content that
actually took part in the decision must surface, and a change that only reorders the
same inventory must not.

The reverse cases matter as much as the forward ones -- a suite that says "changed" to
everything proves nothing, so each positive is paired with a no-op control.
"""

from __future__ import annotations

import copy
import json

import pytest
from fixtures.document_understanding_decision_dependencies import builders as b

from .wire_contract import (
    assert_comparison_shape,
    assert_frozen_shape,
    import_decision_module,
)

# --- helpers --------------------------------------------------------------------------


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


def _frozen_and_current(mutate):
    base = b.base_trace()
    frozen = _freeze(base)
    return frozen, mutate(copy.deepcopy(base))


# --- 1. losing participants change the decision ---------------------------------------


def test_a_losing_candidates_priority_change_changes_the_decision():
    """``c2`` never won ``cand_a``, yet its ranking is part of the decision.

    Hashing only the finally sent winner would answer "same" here and reuse a stale
    selection -- the exact failure the card exists to prevent.
    """
    frozen, current = _frozen_and_current(b.bump_loser_priority)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    assert result["changed_component_ids"] == ["c2"]


def test_a_losing_candidates_matcher_change_changes_the_decision():
    """New/changed matching signals on a participant are causal, even if unused today."""
    def mutate(trace_value):
        current = next(c for c in trace_value["components"] if c["component_id"] == "c2")
        return b.with_component(
            trace_value,
            b.component(
                "c2",
                version=current["version"],
                content={"policy": "financial_notes", "priority": 3},
                matcher={"signals": ["财务报表附注", "分部信息"]},
                scope_ids=current["scope_ids"],
            ),
        )

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    assert result["changed_component_ids"] == ["c2"]


def test_a_zero_match_components_matcher_change_changes_the_decision():
    """``c3`` matches nothing that wins today; a new signal can still create a winner."""
    def mutate(trace_value):
        current = next(c for c in trace_value["components"] if c["component_id"] == "c3")
        return b.with_component(
            trace_value,
            b.component(
                "c3",
                version=current["version"],
                content={"policy": "risk", "priority": 2},
                matcher={"signals": ["风险因素", "重大风险提示"]},
                scope_ids=current["scope_ids"],
            ),
        )

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    assert result["changed_component_ids"] == ["c3"]


def test_a_display_version_change_alone_changes_the_decision():
    """The short version is a real wire field even though the full digest is identity."""
    def mutate(trace_value):
        current = next(c for c in trace_value["components"] if c["component_id"] == "c1")
        updated = b.with_component(trace_value, {**current, "version": "1.0.1"})
        return updated

    frozen, current = _frozen_and_current(mutate)
    assert _compare(frozen, current)["status"] == "changed"


def test_a_pure_content_change_on_a_winner_is_reported():
    def mutate(trace_value):
        return b.with_component(
            trace_value,
            b.component(
                "c1",
                version="1.0.0",
                content={"policy": "core_business", "priority": 1, "note": "renamed policy"},
                matcher={"signals": ["经营情况", "主营业务"]},
                scope_ids=["scope_parent"],
            ),
        )

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    assert result["changed_component_ids"] == ["c1"]


def test_a_component_removed_from_the_inventory_changes_the_decision():
    def mutate(trace_value):
        trace_value["components"] = [
            item for item in trace_value["components"] if item["component_id"] != "c2"
        ]
        for item in trace_value["candidates"]:
            item["component_ids"] = [cid for cid in item["component_ids"] if cid != "c2"]
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    assert result["changed_component_ids"] == ["c2"]


# --- 2. membership changes ------------------------------------------------------------


def test_a_newly_added_candidate_changes_the_decision():
    def mutate(trace_value):
        trace_value["candidates"].append(
            b.candidate("cand_e", scope_id="scope_parent", component_ids=["c3"])
        )
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    assert result["added_candidate_ids"] == ["cand_e"]
    assert result["removed_candidate_ids"] == []


def test_a_removed_candidate_changes_the_decision():
    def mutate(trace_value):
        trace_value["candidates"] = [
            item for item in trace_value["candidates"] if item["candidate_id"] != "cand_c"
        ]
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    assert result["removed_candidate_ids"] == ["cand_c"]
    assert result["added_candidate_ids"] == []


def test_an_eligibility_flip_changes_the_decision():
    def mutate(trace_value):
        for item in trace_value["candidates"]:
            if item["candidate_id"] == "cand_b":
                item["eligible"] = False
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    assert result["changed_component_ids"] == []
    assert result["added_candidate_ids"] == []
    assert result["removed_candidate_ids"] == []
    assert result["diagnostics"], "an eligibility flip must be explained, not silent"


def test_moving_a_candidate_into_the_deciding_scope_changes_the_decision():
    """A candidate that migrates into this domain was not part of the frozen inventory."""
    def mutate(trace_value):
        for item in trace_value["candidates"]:
            if item["candidate_id"] == "cand_d":
                item["scope_id"] = "scope_parent"
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    # Membership is unchanged in the id sense, so the move must be reported as a
    # membership change rather than being silently absorbed as "same".
    codes = {item.get("code") for item in result["diagnostics"]}
    assert "CANDIDATE_MEMBERSHIP_CHANGED" in codes, result
    assert result["added_candidate_ids"] == []
    assert result["removed_candidate_ids"] == []


def test_moving_a_candidate_into_a_new_scope_is_reported_when_the_scope_is_new():
    def mutate(trace_value):
        trace_value["scopes"].append(b.scope("scope_extra", purpose="risk_review"))
        for item in trace_value["candidates"]:
            if item["candidate_id"] == "cand_c":
                item["scope_id"] = "scope_extra"
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    codes = {item.get("code") for item in result["diagnostics"]}
    assert "SCOPE_CHANGED" in codes
    assert "CANDIDATE_MEMBERSHIP_CHANGED" in codes


def test_a_candidate_component_membership_change_changes_the_decision():
    def mutate(trace_value):
        for item in trace_value["candidates"]:
            if item["candidate_id"] == "cand_b":
                item["component_ids"] = ["c1", "c2"]
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    assert _compare(frozen, current)["status"] == "changed"


# --- 3. scope and algorithm-version changes -------------------------------------------


def test_a_child_scope_change_changes_the_decision():
    def mutate(trace_value):
        for item in trace_value["scopes"]:
            if item["scope_id"] == "scope_child":
                item["purpose"] = "project_review"
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    assert result["changed_component_ids"] == []


def test_an_added_child_scope_changes_the_decision():
    def mutate(trace_value):
        trace_value["scopes"].append(b.scope("scope_child_two", purpose="risk_review"))
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    assert _compare(frozen, current)["status"] == "changed"


def test_a_removed_scope_changes_the_decision():
    def mutate(trace_value):
        trace_value["scopes"] = [
            item
            for item in trace_value["scopes"]
            if item["scope_id"] != "scope_child"
        ]
        trace_value["candidates"] = [
            item for item in trace_value["candidates"] if item["scope_id"] != "scope_child"
        ]
        trace_value["components"] = [
            {**item, "scope_ids": [sid for sid in item["scope_ids"] if sid != "scope_child"]}
            for item in trace_value["components"]
        ]
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "changed"
    codes = {item.get("code") for item in result["diagnostics"]}
    assert "SCOPE_CHANGED" in codes


def test_an_algorithm_version_change_changes_the_decision():
    def mutate(trace_value):
        trace_value["versions"] = {**trace_value["versions"], "selector": "1.1.0"}
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    assert _compare(frozen, current)["status"] == "changed"


def test_a_new_version_key_changes_the_decision():
    def mutate(trace_value):
        trace_value["versions"] = {**trace_value["versions"], "layout": "1.0.0"}
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    assert _compare(frozen, current)["status"] == "changed"


# --- 4. array order is not identity ---------------------------------------------------


def test_reordering_scopes_components_and_candidates_is_not_a_change():
    def mutate(trace_value):
        trace_value["scopes"] = list(reversed(trace_value["scopes"]))
        trace_value["components"] = list(reversed(trace_value["components"]))
        trace_value["candidates"] = list(reversed(trace_value["candidates"]))
        for item in trace_value["components"]:
            item["scope_ids"] = list(reversed(item["scope_ids"]))
        for item in trace_value["candidates"]:
            item["component_ids"] = list(reversed(item["component_ids"]))
        return trace_value

    frozen, current = _frozen_and_current(mutate)
    result = _compare(frozen, current)
    assert result["status"] == "same", result
    assert result["changed_component_ids"] == []
    assert result["added_candidate_ids"] == []
    assert result["removed_candidate_ids"] == []


def test_reordering_the_source_inventory_yields_the_same_digest():
    base = b.base_trace()
    shuffled = copy.deepcopy(base)
    shuffled["components"] = list(reversed(shuffled["components"]))
    shuffled["candidates"] = list(reversed(shuffled["candidates"]))
    shuffled["scopes"] = list(reversed(shuffled["scopes"]))
    first = _freeze(base)
    second = _freeze(shuffled)
    assert first["decision_digest"] == second["decision_digest"]
    assert first["components"] == second["components"]
    assert first["candidates"] == second["candidates"]


def test_an_identical_trace_compares_same():
    frozen, current = _frozen_and_current(lambda value: value)
    result = _compare(frozen, current)
    assert result["status"] == "same"
    assert result["diagnostics"] == []


# --- 5. unrelated domains are outside this input --------------------------------------


def test_an_unrelated_domain_is_not_forced_into_this_trace():
    """The caller must not pad this source-domain input with the whole catalog.

    Injected foreign scopes are reported, not silently absorbed as a dependency of this
    decision, and the frozen digest stays the digest of the real decision domain.
    """
    frozen, current = _frozen_and_current(lambda value: value)
    clean_digest = frozen["decision_digest"]

    padded = copy.deepcopy(current)
    padded["scopes"].append(
        b.scope("scope_unrelated", regime="sec", family="sec_10k", form_type="10-K", purpose="annual")
    )
    padded["candidates"].append(
        b.candidate("cand_unrelated", scope_id="scope_unrelated", component_ids=[])
    )
    result = _compare(frozen, padded)
    assert result["status"] == "changed"
    assert "cand_unrelated" in result["added_candidate_ids"]
    codes = {item.get("code") for item in result["diagnostics"]}
    assert "SCOPE_CHANGED" in codes
    # The frozen side is untouched by the padded comparison.
    assert frozen["decision_digest"] == clean_digest


def test_the_manifest_carries_only_this_source_decision_domain():
    frozen = _freeze(b.base_trace())
    assert {scope["scope_id"] for scope in frozen["scopes"]} == {"scope_parent", "scope_child"}
    payload = json.dumps(frozen, ensure_ascii=False, sort_keys=True)
    for foreign in ("sec_10k", "hk_annual", "unrelated"):
        assert foreign not in payload, foreign


# --- 6. hard input errors are rejected, never silently repaired ------------------------


def _expect_rejected(trace_value):
    with pytest.raises((ValueError, TypeError)) as excinfo:
        import_decision_module().freeze_decision_dependencies(trace_value)
    return str(excinfo.value)


def test_duplicate_component_ids_are_rejected():
    def mutate(trace_value):
        trace_value["components"].append(dict(trace_value["components"][0]))
        return trace_value

    message = _expect_rejected(mutate(b.base_trace()))
    assert "c1" in message


def test_duplicate_scope_ids_are_rejected():
    def mutate(trace_value):
        trace_value["scopes"].append(dict(trace_value["scopes"][0]))
        return trace_value

    _expect_rejected(mutate(b.base_trace()))


def test_duplicate_candidate_ids_are_rejected():
    def mutate(trace_value):
        trace_value["candidates"].append(dict(trace_value["candidates"][0]))
        return trace_value

    _expect_rejected(mutate(b.base_trace()))


def test_the_same_id_with_two_different_contents_is_rejected():
    """An identity collision is a real caller error, not something to de-duplicate."""
    trace_value = b.base_trace()
    trace_value["components"].append(
        b.component(
            "c1",
            version="9.9.9",
            content={"policy": "conflicting"},
            matcher={"signals": ["x"]},
            scope_ids=["scope_parent"],
        )
    )
    _expect_rejected(trace_value)


def test_a_dangling_component_reference_is_rejected():
    def mutate(trace_value):
        for item in trace_value["candidates"]:
            if item["candidate_id"] == "cand_a":
                item["component_ids"] = ["c1", "missing_component"]
        return trace_value

    message = _expect_rejected(mutate(b.base_trace()))
    assert "missing_component" in message


def test_a_candidate_pointing_at_an_unknown_scope_is_rejected():
    def mutate(trace_value):
        for item in trace_value["candidates"]:
            if item["candidate_id"] == "cand_a":
                item["scope_id"] = "scope_missing"
        return trace_value

    _expect_rejected(mutate(b.base_trace()))


def test_a_component_scoped_to_an_unknown_scope_is_rejected():
    def mutate(trace_value):
        for item in trace_value["components"]:
            if item["component_id"] == "c1":
                item["scope_ids"] = ["scope_missing"]
        return trace_value

    _expect_rejected(mutate(b.base_trace()))


def test_an_unsupported_wire_version_is_reported_not_certified():
    """A declared ``/2`` is not this contract: report it, never pretend it is ``/1``.

    The card's rule for unknown or missing items is an explicit diagnostic, not a guess;
    the safety property is that it can never come out ``complete`` or ``same``.
    """
    trace_value = b.base_trace()
    trace_value["schema_version"] = "du-decision-trace/2"
    frozen = _freeze(trace_value)
    assert frozen["status"] == "partial"
    codes = {item.get("code") for item in frozen["diagnostics"]}
    assert "LEGACY_TRACE_VERSION" in codes
    assert _compare(frozen, trace_value)["status"] == "unavailable"


def test_a_missing_wire_version_is_reported_not_certified():
    trace_value = b.base_trace()
    del trace_value["schema_version"]
    frozen = _freeze(trace_value)
    assert frozen["status"] == "partial"
    codes = {item.get("code") for item in frozen["diagnostics"]}
    assert "MISSING_SCHEMA_VERSION" in codes
    assert _compare(frozen, trace_value)["status"] == "unavailable"


def test_a_declared_trace_missing_its_rows_is_a_real_data_error():
    """Inside ``du-decision-trace/1`` the rows are the contract, not a hint."""
    trace_value = {"schema_version": "du-decision-trace/1", "scopes": [], "components": []}
    message = _expect_rejected(trace_value)
    assert "candidates" in message
    assert "versions" in message


def test_a_non_sha256_content_digest_is_rejected():
    def mutate(trace_value):
        trace_value["components"][0]["content_digest"] = "not-a-digest"
        return trace_value

    _expect_rejected(mutate(b.base_trace()))


def test_a_truncated_content_digest_is_rejected():
    """A short profile version must never stand in for full content identity."""
    def mutate(trace_value):
        trace_value["components"][0]["content_digest"] = trace_value["components"][0][
            "content_digest"
        ][:12]
        return trace_value

    _expect_rejected(mutate(b.base_trace()))


def test_wrong_types_are_rejected():
    for mutate in (
        lambda t: t.update({"scopes": {"scope_parent": {}}}),
        lambda t: t.update({"candidates": "cand_a"}),
        lambda t: t.update({"versions": ["router"]}),
        lambda t: t["components"][0].update({"scope_ids": "scope_parent"}),
        lambda t: t["scopes"][0].update({"scope_id": 7}),
    ):
        trace_value = b.base_trace()
        mutate(trace_value)
        _expect_rejected(trace_value)


def test_an_unknown_wire_field_is_rejected():
    """Additive schema changes must be deliberate; a stray field is a caller error."""
    def mutate(trace_value):
        trace_value["components"][0]["unexpected"] = "value"
        return trace_value

    _expect_rejected(mutate(b.base_trace()))


def test_a_non_mapping_trace_is_rejected():
    """A wrong *type* is a real data error and must be refused outright."""
    for bad in ([], "trace", 3, 3.5, True):
        _expect_rejected(bad)


def test_an_absent_trace_is_reported_rather_than_rejected():
    """``缺trace`` is the old path that recorded no decision at all.

    That is an honest absence, not a corrupt input, so it must come back as an unusable
    freeze instead of an exception the legacy caller cannot handle.
    """
    frozen = _freeze(None)
    assert frozen["status"] == "partial"
    assert "MISSING_TRACE" in {item.get("code") for item in frozen["diagnostics"]}
    assert _compare(frozen, None)["status"] == "unavailable"


def test_rejection_does_not_launder_into_same():
    """A rejected input must raise; it may never fall back to a permissive "same"."""
    broken = b.base_trace()
    broken["candidates"][0]["component_ids"] = ["nope"]
    frozen = _freeze(b.base_trace())
    with pytest.raises((ValueError, TypeError)):
        import_decision_module().compare_decision_dependencies(frozen, broken)
