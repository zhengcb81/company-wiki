"""Real POLICY output composed with planner; independent ROOT acceptance anchors."""
from copy import deepcopy
import json

import pytest

from company_wiki.document_understanding.geometry_intent import (
    admit_geometry_request,
    new_admission_state,
    plan_geometry_requests,
    summarize_admission_state,
)
from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.profiles import get_profile, route_document
from company_wiki.document_understanding.profiles.geometry_policy import compile_geometry_policy
from company_wiki.document_understanding.profiles.registry import resolve_reading_profile
from fixtures.document_understanding_profiles.builders import observation, unit


def compiled_offering():
    title = "向不特定对象发行可转换公司债券募集说明书"
    source = observation([unit("cover", 0, title, kind="heading"),
                          unit("body", 1, "本次募集资金运用 主营业务 产能")],
                         title=title, declared_kind="convertible_bond_prospectus", regime="cn_exchange")
    route = route_document(source)
    profile = resolve_reading_profile(get_profile(route["profile_id"]), source, route)
    assert profile["family_policy"]["id"] == "offering_cn_convertible"
    return compile_geometry_policy(profile)


def rule(policy, role):
    return next(r for r in policy["rules"] if r["section_role"] == role)


def window(key, policy_rule, start, end, scope="main"):
    return {"window_key": key, "scope_id": scope, "rule_key": policy_rule["rule_key"],
            "physical_start": start, "physical_end": end,
            "navigation_status": "native_destination", "native_navigation_refs": ["outline:" + key]}


def admit(plan, state, page, keys, evidence="observed_candidate"):
    return admit_geometry_request(plan, state, page=page, window_keys=keys,
                                  tabular_evidence=evidence, remaining=64)


@pytest.mark.parametrize("max_pages,max_requests", [(2, 64), (64, 2), (2, 2)])
def test_fair_reservations_follow_the_tightest_executable_bound(max_pages, max_requests):
    policy = compiled_offering()
    windows = [window("ops", rule(policy, "business"), 1, 50),
               window("project", rule(policy, "fundraising"), 90, 100)]
    budget = WorkBudget(2_000_000)
    budget.charge(37)  # caller's already-consumed shared allowance cannot reset
    plan = plan_geometry_requests(policy, windows, page_count=100,
        limits={"max_pages": max_pages, "max_requests": max_requests}, work_budget=budget)
    assert budget.used > 37 and budget.max_work_units == 2_000_000
    assert plan["summary"]["pages_reserved"] == 2
    assert {k: v["quota"] for k, v in plan["class_quotas"].items()} == {"operating": 1, "project": 1}
    state = new_admission_state(plan)
    decisions = []
    for page, keys in [(1, ["ops"]), (2, ["ops"]), (90, ["project"]), (91, ["project"])]:
        decision, state = admit(plan, state, page, keys)
        decisions.append(decision["decision"])
    assert decisions == ["admitted", "exhausted", "admitted", "exhausted"]
    assert state["spent"] == {"pages": 2, "requests": 2}


def nested_policy(*, inner_class="operating"):
    # Both instructions are actually produced by the compiler. Their page
    # reservation is one class; the inner full-path rule adds fine capability.
    return compile_geometry_policy({"profile_id": "nested", "profile_version": "nested/v1", "section_rules": [
        {"section_role": "business", "priority": 1, "heading_path": [["Business"]],
         "aliases": ["Business"], "geometry_intent": {
             "discover": "on_tabular_evidence", "fine": "explicit_only", "demand_class": "operating"}},
        {"section_role": "operating_metrics", "priority": 1,
         "heading_path": [["Business"], ["Capacity"]], "aliases": ["Capacity"],
         "geometry_intent": {"discover": "on_tabular_evidence", "fine": "on_candidate", "demand_class": inner_class}},
        {"section_role": "risk", "priority": 1, "heading_path": [["Risks"]], "aliases": ["Risks"],
         "geometry_intent": {"discover": "none", "fine": "unknown", "demand_class": "context"}},
    ]})


def test_nested_request_semantics_merge_without_double_charging_or_cancelled_borrowing():
    policy = nested_policy()
    windows = [window("outer", rule(policy, "business"), 1, 10),
               window("inner", rule(policy, "operating_metrics"), 3, 5),
               window("cancelled", rule(policy, "risk"), 3, 5)]
    plan = plan_geometry_requests(policy, windows, page_count=10,
        limits={"max_pages": 10, "max_requests": 10}, work_budget=WorkBudget(2000))
    rows = {r["window_key"]: r for r in plan["allocations"]}
    assert rows["inner"]["quota_pages"] == 0 and rows["inner"]["status"] == "reserved"
    assert rows["cancelled"]["status"] == "cancelled"
    state = new_admission_state(plan)
    result, state = admit(plan, state, 3, ["outer", "inner", "cancelled"])
    assert result["decision"] == "admitted"
    assert result["request"] == {"discover": True, "fine": True}
    assert result["admitted_window_keys"] == ["outer"]  # attribution is still one reservation
    assert state["spent"] == {"pages": 1, "requests": 1}
    assert state["windows"]["inner"]["admitted"] == 0
    repeated, state = admit(plan, state, 3, ["inner", "outer"])
    assert repeated["decision"] == "deduplicated"
    assert state["spent"] == {"pages": 1, "requests": 1}
    outer_only, _ = admit(plan, state, 2, ["outer"])
    assert outer_only["request"] == {"discover": True, "fine": False}


def test_nonrequestable_administrative_rules_stay_cancelled_under_real_catalog():
    policy = compiled_offering()
    windows = [window("admin", rule(policy, "administrative"), 1, 10),
               window("project", rule(policy, "fundraising"), 90, 100)]
    plan = plan_geometry_requests(policy, windows, page_count=100,
        limits={"max_pages": 2, "max_requests": 2}, work_budget=WorkBudget(2000))
    rows = {r["window_key"]: r for r in plan["allocations"]}
    assert rows["admin"]["requestable"] == {"discover": False, "fine": False}
    assert rows["admin"]["status"] == "cancelled" and rows["project"]["quota_pages"] == 2
    result, state = admit(plan, new_admission_state(plan), 1, ["admin"])
    assert result["decision"] == "cancelled" and state["spent"]["pages"] == 0


def test_cancelled_nested_class_cannot_add_fine_capability_to_covering_request():
    policy = nested_policy(inner_class="project")
    inner = rule(policy, "operating_metrics")
    windows = [window("outer", rule(policy, "business"), 1, 10), window("inner", inner, 3, 5)]
    plan = plan_geometry_requests(policy, windows, page_count=10,
        limits={"max_pages": 1, "max_requests": 1}, work_budget=WorkBudget(2000))
    assert next(r for r in plan["allocations"] if r["window_key"] == "inner")["status"] == "cancelled"
    result, state = admit(plan, new_admission_state(plan), 3, ["outer", "inner"])
    assert result["decision"] == "admitted" and result["request"] == {"discover": True, "fine": False}
    assert state["spent"] == {"pages": 1, "requests": 1}


def test_shared_budget_exhaustion_remains_partial_without_inventing_plan_or_replenishment():
    policy = compiled_offering()
    budget = WorkBudget(5)
    budget.charge(4)
    result = plan_geometry_requests(policy, [window("project", rule(policy, "fundraising"), 90, 100)],
        page_count=100, limits={"max_pages": 64, "max_requests": 64}, work_budget=budget)
    assert result["summary"]["partial"] is True
    assert result["allocations"] == [] and result["summary"]["windows_unplanned"] == 1
    assert budget.used == 4 and budget.exhausted


def test_cross_scope_dedup_and_json_resume_keep_real_policy_request_semantics(tmp_path):
    policy = compiled_offering()
    windows = [window("ops", rule(policy, "business"), 1, 2, "main"),
               window("project", rule(policy, "fundraising"), 1, 2, "attachment")]
    frozen = deepcopy((policy, windows))
    sentinel = tmp_path / "keep"
    sentinel.write_bytes(b"initial contents")
    baseline = (sentinel.read_bytes(), sentinel.stat().st_mtime_ns, set(tmp_path.iterdir()))
    plan = plan_geometry_requests(policy, windows, page_count=2,
        limits={"max_pages": 4, "max_requests": 4}, work_budget=WorkBudget(2000))
    events = [(1, ["ops"]), (1, ["project"]), (1, ["ops"]), (2, ["project"])]
    one_shot = new_admission_state(plan)
    full = []
    for page, keys in events:
        decision, one_shot = admit(plan, one_shot, page, keys)
        full.append(decision)
    resumed = new_admission_state(plan)
    replay = []
    for index, (page, keys) in enumerate(events):
        if index == 2:
            resumed = json.loads(json.dumps(resumed))
            plan = json.loads(json.dumps(plan))
        decision, resumed = admit(plan, resumed, page, keys)
        replay.append(decision)
    assert replay == full and resumed == one_shot
    assert [r["decision"] for r in replay] == ["admitted", "admitted", "deduplicated", "admitted"]
    assert set(resumed["charged"]) == {"main", "attachment"}
    assert summarize_admission_state(plan, resumed)["spent"] == {"pages": 3, "requests": 3}
    assert (policy, windows) == frozen
    assert (sentinel.read_bytes(), sentinel.stat().st_mtime_ns, set(tmp_path.iterdir())) == baseline
