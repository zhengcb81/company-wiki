"""One call owns policy preparation; shared work cannot restart its quota."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from company_wiki.document_understanding import strategy_binding as binding
from company_wiki.document_understanding.layout_hints.contract import WorkBudget, WorkBudgetExceeded


def inputs(count=4):
    units = [{"unit_id": f"u{i}", "ordinal": i, "text": "Products"} for i in range(count)]
    observation = {"units": units}
    structure = {"sections": [
        {"section_id": f"s{i}", "parent_id": None, "section_role": "unknown",
         "heading_unit_ids": [unit["unit_id"]], "body_unit_ids": []}
        for i, unit in enumerate(units)], "semantic_units": [], "relations": []}
    profile = {"profile_id": "fixture", "profile_version": "1", "family": "annual",
               "form_type": "10-K", "reading_questions": ["What changed?"],
               "family_policy": {"features": ["native business text"]},
               "section_rules": [{"aliases": ["Products", "Services"], "role": "business",
                                  "priority": 1, "questions": ["Products?"]}]}
    return observation, structure, profile


def run(observation, structure, profile, **kwargs):
    return binding.bind_reading_plan(observation, structure, route={"child_routes": []},
                                     profile=profile, **kwargs)


class Unread(list):
    def __iter__(self):
        raise AssertionError("budget boundary must precede source enumeration")


@pytest.mark.parametrize("tail", ["child_scope", "policy", "rules", "heading_members", "diagnostics"])
def test_large_tail_is_reserved_before_materialization(tail):
    observation, structure, profile = inputs(1)
    route = {"child_routes": []}
    if tail == "child_scope":
        route["child_routes"] = [{"profile_id": "child", "unit_ids": Unread(["u0"] * 20_000)}]
    elif tail == "policy":
        profile["family_policy"]["features"] = Unread(["feature"] * 20_000)
    elif tail == "rules":
        profile["section_rules"] = Unread(profile["section_rules"] * 20_000)
    elif tail == "diagnostics":
        profile["policy_diagnostics"] = Unread(["diagnostic"] * 20_000)
    else:
        structure["sections"][0]["heading_unit_ids"] = Unread(["u0"] * 20_000)
    with pytest.raises(WorkBudgetExceeded):
        binding.bind_reading_plan(observation, structure, profile=profile, route=route,
                                  work_budget=WorkBudget(100))


def test_component_dedup_cannot_hide_quadratic_work_after_material_copy():
    observation, structure, profile = inputs(1)
    profile["policy_components"] = [f"component-{i}" for i in range(1000)]
    budget = WorkBudget(20_000)
    with pytest.raises(WorkBudgetExceeded):
        run(observation, structure, profile, work_budget=budget)
    assert budget.exhausted


def test_shared_zero_is_checked_before_document_enumeration():
    observation, structure, profile = inputs()
    observation["units"] = Unread(observation["units"])
    with pytest.raises(WorkBudgetExceeded):
        run(observation, structure, profile, work_budget=WorkBudget(0))


def test_existing_exhausted_budget_is_not_replaced_and_inputs_stay_exact():
    observation, structure, profile = inputs()
    before = deepcopy((observation, structure, profile))
    budget = WorkBudget(10, used=10)
    with pytest.raises(WorkBudgetExceeded):
        run(observation, structure, profile, work_budget=budget)
    assert budget.used == 10
    assert budget.exhausted
    assert (observation, structure, profile) == before


def test_repeated_heading_and_aliases_are_prepared_once_in_one_call():
    observation, structure, profile = inputs(80)
    before = deepcopy((observation, structure, profile))
    old = run(observation, structure, profile)
    with patch.object(binding, "_fold", wraps=binding._fold) as folded:
        actual = run(observation, structure, profile, work_budget=WorkBudget(2_000_000))
    assert actual == old
    assert max(folded.call_args_list.count(call) for call in folded.call_args_list) == 1
    assert (observation, structure, profile) == before


def test_shared_internal_policy_material_is_single_while_standalone_is_independent():
    observation, structure, profile = inputs()
    actual = run(observation, structure, profile, work_budget=WorkBudget(2_000_000))
    a, b = (actual["unit_profiles"][key] for key in ("u0", "u1"))
    assert a["family_policy"] is b["family_policy"]
    assert a["family_policy"] is not profile["family_policy"]
    old = run(observation, structure, profile)
    old["unit_profiles"]["u0"]["family_policy"]["features"].append("local edit")
    assert old["unit_profiles"]["u1"]["family_policy"] == profile["family_policy"]


def test_preparation_is_not_a_global_cache_across_changed_profiles():
    observation, structure, profile = inputs()
    first = run(observation, structure, profile, work_budget=WorkBudget(2_000_000))
    profile["section_rules"][0]["aliases"] = ["No match"]
    second = run(observation, structure, profile, work_budget=WorkBudget(2_000_000))
    assert first["unit_profiles"]["u0"]["section_role"] == "business"
    assert second["unit_profiles"]["u0"]["section_role"] == "unknown"


def test_pipeline_passes_the_same_work_owner_and_keeps_source_on_strategy_exhaustion():
    from company_wiki.document_understanding import pipeline
    from company_wiki.document_understanding import structure

    budget = WorkBudget(2_000_000)
    original = structure.build_structure
    observed = []

    def build(payload, **kwargs):
        observed.append(kwargs["work_budget"])
        return original(payload, **kwargs)

    def stop(*args, **kwargs):
        observed.append(kwargs["work_budget"])
        budget.charge(budget.max_work_units + 1)

    with patch.object(structure, "build_structure", side_effect=build), \
            patch.object(pipeline, "bind_reading_plan", side_effect=stop):
        result = pipeline.understand_units([], source_id="original", source_sha256="opaque",
                                          work_budget=budget)
    assert observed == [budget, budget]
    assert result["analysis_status"] == "deferred"
    assert result["observation"]["source_ref"]["source_id"] == "original"
    assert result["structure"]["source_ref"]["source_id"] == "original"
    assert result["work"]["exhausted"]
    assert result["work"]["full_pipeline_hard_bound"] is False
