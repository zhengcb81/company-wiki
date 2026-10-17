"""Node B concentrated regression: adversarial inputs against the fixed contract.

Covers the card's required counterexamples against the existing WorkBudget
protocol: zero budget, tail exhaustion, request cap of 1, huge window lists,
overlaps, negative/bool page numbers, megabyte scopes and bounded diagnostics.
Every test goes through the public entries only.
"""
from __future__ import annotations

import json
import random

import pytest

from company_wiki.document_understanding.geometry_intent import (
    admit_geometry_request,
    new_admission_state,
    plan_geometry_requests,
    summarize_admission_state,
)
from company_wiki.document_understanding.layout_hints.contract import WorkBudget

from . import helpers


def _big_budget() -> WorkBudget:
    return WorkBudget(max_work_units=2_000_000)


def _fixture_plan(fixture: dict, *, limits=None, budget=None):
    return plan_geometry_requests(
        fixture["policy"],
        fixture["windows"],
        page_count=fixture["page_count"],
        limits=limits or fixture["limits"],
        work_budget=budget or _big_budget(),
    )


def _stream(plan, state, fixture, *, evidence="observed_candidate", remaining=None):
    decisions = []
    cap = plan["limits"]["max_pages"]
    for page, keys in helpers.all_candidate_events(fixture):
        decision, state = admit_geometry_request(
            plan,
            state,
            page=page,
            window_keys=keys,
            tabular_evidence=evidence,
            remaining=cap if remaining is None else remaining,
        )
        decisions.append(decision)
    return decisions, state


# --- WorkBudget protocol ----------------------------------------------------

def test_zero_work_budget_yields_partial_plan_without_claims():
    fixture = helpers.load_fixture()
    budget = WorkBudget(max_work_units=0)
    plan = _fixture_plan(fixture, budget=budget)

    assert plan["summary"]["partial"] is True
    assert plan["summary"]["partial_reason"] == "work_budget_exhausted"
    assert plan["allocations"] == []
    assert plan["summary"]["windows_unplanned"] == len(fixture["windows"])
    assert plan["summary"]["pages_reserved"] == 0
    assert budget.exhausted is True
    assert budget.used == 0, "no charge may succeed on a zero budget"
    # Diagnostics stay bounded even in the partial path.
    assert len(plan["diagnostics"]) <= 256
    assert plan["diagnostics_dropped"] == 0

    # An unplanned window is honestly not-in-plan, never silently admitted.
    state = new_admission_state(plan)
    decision, state = admit_geometry_request(
        plan, state, page=10, window_keys=["w-risk"],
        tabular_evidence="observed_candidate", remaining=64,
    )
    assert decision["decision"] == "rejected"
    assert decision["reason"] == "window_not_in_plan"
    assert state["spent"]["pages"] == 0


def test_small_budget_fails_before_any_traversal_charge():
    fixture = helpers.load_fixture()
    # Exactly the prepaid assembly charge: 1 + 2 * (windows + rules).
    prepay = 1 + 2 * (len(fixture["windows"]) + len(fixture["policy"]["rules"]))
    budget = WorkBudget(max_work_units=prepay)
    plan = _fixture_plan(fixture, budget=budget)

    assert plan["summary"]["partial"] is True
    assert plan["allocations"] == []
    assert budget.exhausted is True
    assert budget.used == prepay, "only the prepaid assembly may be charged"


def test_budget_only_never_resets_between_plans():
    fixture = helpers.load_fixture()
    budget = WorkBudget(max_work_units=41)
    first = _fixture_plan(fixture, budget=budget)
    assert first["summary"]["partial"] is True
    used_after_first = budget.used
    second = _fixture_plan(fixture, budget=budget)
    assert second["summary"]["partial"] is True
    assert budget.used >= used_after_first, "a second call must not reset the budget"
    assert budget.max_work_units == 41


# --- fair quotas, tail exhaustion, hard balance -----------------------------

def test_tiny_tail_budget_keeps_back_windows_alive():
    """max_pages=3: the deep project/operating windows must still get a page."""
    fixture = helpers.load_fixture()
    limits = helpers.tiny_limits(3, 3)
    plan = _fixture_plan(fixture, limits=limits)

    quotas = {cls: row["quota"] for cls, row in plan["class_quotas"].items()}
    assert sum(quotas.values()) <= 3
    # Remaining pages go to the canonical-first classes; administrative yields.
    assert quotas["operating"] == 1 and quotas["project"] == 1 and quotas["context"] == 1
    assert quotas["administrative"] == 0

    by_window = {row["window_key"]: row for row in plan["allocations"]}
    assert by_window["w-attach-op"]["quota_pages"] == 1
    assert by_window["w-proj-a"]["quota_pages"] == 1
    assert by_window["w-admin"]["status"] == "cancelled"
    assert by_window["w-admin"]["reason"] == "class_quota_zero"
    assert by_window["w-toc"]["reason"] == "not_requestable"

    state = new_admission_state(plan)
    decisions, state = _stream(plan, state, fixture, remaining=3)
    admitted_pages = [d["page"] for d in decisions if d["decision"] == "admitted"]
    assert admitted_pages == [31, 71, 89], "only front notes + both deep segments serve, in stream order"
    assert state["spent"]["pages"] == 3


def test_request_limit_of_one_fires_before_pages_do():
    # One consumable class isolates the request cap from inter-class fairness.
    # The effective reservation must be one even though the page cap is 64.
    rule = helpers.tiny_rule("rk_op", "operating")
    limits = helpers.tiny_limits(64, 1)
    plan = plan_geometry_requests(
        helpers.tiny_policy(rule), [helpers.tiny_window("w1", "rk_op", 1, 10)],
        page_count=10, limits=limits, work_budget=_big_budget(),
    )
    assert plan["summary"]["pages_reserved"] == 1
    state = new_admission_state(plan)

    first, state = admit_geometry_request(
        plan, state, page=4, window_keys=["w1"],
        tabular_evidence="observed_candidate", remaining=64,
    )
    assert first["decision"] == "admitted"
    second, state = admit_geometry_request(
        plan, state, page=5, window_keys=["w1"],
        tabular_evidence="observed_candidate", remaining=64,
    )
    assert second["decision"] == "exhausted"
    # This window's sole executable reservation is already consumed.
    assert second["reason"] == "window_quota_exhausted"
    assert state["spent"] == {"pages": 1, "requests": 1}


@pytest.mark.parametrize("max_pages", [0, 1, 2, 3, 5, 8, 64, 1000])
def test_global_hard_balance_always_holds(max_pages):
    fixture = helpers.load_fixture()
    limits = helpers.tiny_limits(max_pages, max_pages)
    plan = _fixture_plan(fixture, limits=limits)
    reserved = sum(row["quota_pages"] for row in plan["allocations"] if row["status"] == "reserved")
    class_total = sum(row["quota"] for row in plan["class_quotas"].values())
    assert reserved <= max_pages
    assert class_total <= max_pages

    if max_pages:
        state = new_admission_state(plan)
        decisions, state = _stream(plan, state, fixture)
        assert state["spent"]["pages"] <= max_pages


def test_caller_remaining_gates_but_never_resets_state_limit():
    rule = helpers.tiny_rule("rk_op", "operating")
    policy = helpers.tiny_policy(rule)
    windows = [helpers.tiny_window("w1", "rk_op", 1, 10)]
    limits = helpers.tiny_limits(2, 10)
    plan = plan_geometry_requests(
        policy, windows, page_count=10, limits=limits, work_budget=_big_budget()
    )
    state = new_admission_state(plan)

    # remaining=0 gates the very first page although quota exists.
    decision, state = admit_geometry_request(
        plan, state, page=1, window_keys=["w1"],
        tabular_evidence="observed_candidate", remaining=0,
    )
    assert decision["decision"] == "exhausted"
    assert decision["reason"] == "caller_remaining_exhausted"
    assert state["spent"]["pages"] == 0

    # A fresh remaining value each call can never reopen spent pages.
    admitted = 0
    for page in range(1, 11):
        for _attempt in range(3):  # caller keeps claiming remaining=64
            decision, state = admit_geometry_request(
                plan, state, page=page, window_keys=["w1"],
                tabular_evidence="observed_candidate", remaining=64,
            )
            if decision["decision"] == "admitted":
                admitted += 1
    assert admitted == 2
    assert state["spent"]["pages"] == 2, "state budget, not caller remaining, is authoritative"

    # Invalid remaining values are rejected, never coerced.
    decision, state = admit_geometry_request(
        plan, state, page=3, window_keys=["w1"],
        tabular_evidence="observed_candidate", remaining=-1,
    )
    assert decision["decision"] == "rejected" and decision["reason"] == "bad_remaining"
    decision, state = admit_geometry_request(
        plan, state, page=3, window_keys=["w1"],
        tabular_evidence="observed_candidate", remaining=True,
    )
    assert decision["decision"] == "rejected" and decision["reason"] == "bad_remaining"


# --- overlaps, dedup, parent scopes ----------------------------------------

def test_same_scope_overlap_charges_once_cross_scope_stays_separate():
    rule = helpers.tiny_rule("rk_op", "operating")
    policy = helpers.tiny_policy(rule)
    windows = [
        helpers.tiny_window("w1", "rk_op", 1, 10, scope="main"),
        helpers.tiny_window("w2", "rk_op", 5, 15, scope="main"),
        helpers.tiny_window("w3", "rk_op", 5, 5, scope="attachment"),
    ]
    plan = plan_geometry_requests(
        policy, windows, page_count=20, limits=helpers.tiny_limits(50),
        work_budget=_big_budget(),
    )
    state = new_admission_state(plan)

    first, state = admit_geometry_request(
        plan, state, page=5, window_keys=["w1"],
        tabular_evidence="observed_candidate", remaining=50,
    )
    assert first["decision"] == "admitted" and first["admitted_window_keys"] == ["w1"]

    # Repeated ACK and the overlapping window both dedup on the same ledger.
    repeat, state = admit_geometry_request(
        plan, state, page=5, window_keys=["w1"],
        tabular_evidence="observed_candidate", remaining=50,
    )
    assert repeat["decision"] == "deduplicated"
    overlap, state = admit_geometry_request(
        plan, state, page=5, window_keys=["w2"],
        tabular_evidence="observed_candidate", remaining=50,
    )
    assert overlap["decision"] == "deduplicated"
    both, state = admit_geometry_request(
        plan, state, page=5, window_keys=["w1", "w2"],
        tabular_evidence="observed_candidate", remaining=50,
    )
    assert both["decision"] == "deduplicated"
    assert state["spent"]["pages"] == 1, "one physical page in one parent scope charges once"
    assert state["windows"]["w2"]["admitted"] == 0, "dedup never books another window's quota"

    # A different parent scope keeps its own ledger for the same page number.
    other, state = admit_geometry_request(
        plan, state, page=5, window_keys=["w3"],
        tabular_evidence="observed_candidate", remaining=50,
    )
    assert other["decision"] == "admitted"
    assert state["spent"]["pages"] == 2


def test_scope_crossing_event_is_rejected():
    rule = helpers.tiny_rule("rk_op", "operating")
    policy = helpers.tiny_policy(rule)
    windows = [
        helpers.tiny_window("w1", "rk_op", 1, 10, scope="main"),
        helpers.tiny_window("w3", "rk_op", 1, 10, scope="attachment"),
    ]
    plan = plan_geometry_requests(
        policy, windows, page_count=20, limits=helpers.tiny_limits(50),
        work_budget=_big_budget(),
    )
    state = new_admission_state(plan)
    decision, state = admit_geometry_request(
        plan, state, page=5, window_keys=["w1", "w3"],
        tabular_evidence="observed_candidate", remaining=50,
    )
    assert decision["decision"] == "rejected"
    assert decision["reason"] == "scope_crossing"
    assert state["spent"]["pages"] == 0


def test_nested_window_transparent_quota_requires_covering_key():
    rule = helpers.tiny_rule("rk_proj", "project")
    policy = helpers.tiny_policy(rule)
    windows = [
        helpers.tiny_window("w-child", "rk_proj", 1, 10),
        helpers.tiny_window("w-parent", "rk_proj", 1, 20),
    ]
    plan = plan_geometry_requests(
        policy, windows, page_count=20, limits=helpers.tiny_limits(10),
        work_budget=_big_budget(),
    )
    by_window = {row["window_key"]: row for row in plan["allocations"]}
    # The class quota is split by exclusive pages: the child holds shared
    # pages 1..10, the parent its exclusive tail 11..20.
    assert by_window["w-child"]["quota_pages"] == 5
    assert by_window["w-parent"]["quota_pages"] == 5

    state = new_admission_state(plan)
    decision, state = admit_geometry_request(
        plan, state, page=15, window_keys=["w-child"],
        tabular_evidence="observed_candidate", remaining=10,
    )
    assert decision["decision"] == "rejected" and decision["reason"] == "page_outside_windows"
    decision, state = admit_geometry_request(
        plan, state, page=15, window_keys=["w-parent"],
        tabular_evidence="observed_candidate", remaining=10,
    )
    assert decision["decision"] == "admitted"


# --- invalid values: windows, pages, evidence -------------------------------

def test_negative_and_bool_window_pages_keep_diagnostics():
    fixture = helpers.load_fixture()
    policy = fixture["policy"]
    windows = [
        helpers.tiny_window("w-bool", "rk_mda", True, 10),          # bool excluded
        helpers.tiny_window("w-span", "rk_mda", 30, 10),            # reversed excluded
        helpers.tiny_window("w-out", "rk_mda", 500, 600),           # beyond page_count excluded
        helpers.tiny_window("w-neg", "rk_mda", -5, 6),              # clamped to 1..6
        helpers.tiny_window("w-hi", "rk_mda", 90, 200),             # clamped to 90..96
        helpers.tiny_window("w-ok", "rk_mda", 7, 8),
    ]
    plan = plan_geometry_requests(
        policy, windows, page_count=fixture["page_count"],
        limits=helpers.tiny_limits(64), work_budget=_big_budget(),
    )
    codes = [row["code"] for row in plan["diagnostics"]]
    assert "WINDOW_BAD_PAGE_VALUE" in codes
    assert "WINDOW_INVALID_SPAN" in codes
    assert "WINDOW_OUT_OF_RANGE" in codes
    assert codes.count("WINDOW_CLAMPED") == 3  # w-out, w-neg, w-hi
    built = {row["window_key"] for row in plan["allocations"]}
    assert built == {"w-neg", "w-hi", "w-ok"}
    neg_row = next(row for row in plan["allocations"] if row["window_key"] == "w-neg")
    assert (neg_row["physical_start"], neg_row["physical_end"]) == (1, 6), "clamp bounds, never guesses an offset"

    state = new_admission_state(plan)
    for bad_page in (True, 0, -7, 1.5, "10", None):
        decision, state = admit_geometry_request(
            plan, state, page=bad_page, window_keys=["w-ok"],
            tabular_evidence="observed_candidate", remaining=64,
        )
        assert decision["decision"] == "rejected"
        assert decision["reason"] in {"bad_page", "page_out_of_range"}
        assert len(decision["diagnostics"]) <= 256
    assert state["spent"]["pages"] == 0


def test_unknown_rule_and_invalid_intent_stay_conservative():
    policy = helpers.tiny_policy(helpers.tiny_rule("rk_known", "operating"))
    windows = [
        helpers.tiny_window("w-known", "rk_known", 1, 5),
        helpers.tiny_window("w-unknown-rule", "rk_missing", 6, 10),
    ]
    plan = plan_geometry_requests(
        policy, windows, page_count=10, limits=helpers.tiny_limits(10),
        work_budget=_big_budget(),
    )
    codes = [row["code"] for row in plan["diagnostics"]]
    assert "WINDOW_UNKNOWN_RULE" in codes
    by_window = {row["window_key"]: row for row in plan["allocations"]}
    assert by_window["w-unknown-rule"]["status"] == "cancelled"
    assert by_window["w-unknown-rule"]["reason"] == "not_requestable"
    assert by_window["w-unknown-rule"]["demand_class"] == "unknown"

    broken_intent = dict(helpers.tiny_rule("rk_bad", "operating"))
    broken_intent["geometry_intent"] = {"discover": "always", "fine": {}, "demand_class": "operating"}
    policy2 = helpers.tiny_policy(broken_intent)
    plan2 = plan_geometry_requests(
        policy2, [helpers.tiny_window("w-bad", "rk_bad", 1, 5)],
        page_count=10, limits=helpers.tiny_limits(10), work_budget=_big_budget(),
    )
    codes2 = [row["code"] for row in plan2["diagnostics"]]
    assert "POLICY_INTENT_INVALID" in codes2
    row = plan2["allocations"][0]
    assert row["status"] == "cancelled" and row["reason"] == "not_requestable"
    assert row["requestable"] == {"discover": False, "fine": False}


def test_evidence_semantics_absent_unknown_candidate():
    fixture = helpers.load_fixture()
    plan = _fixture_plan(fixture)
    state = new_admission_state(plan)

    absent, state = admit_geometry_request(
        plan, state, page=10, window_keys=["w-risk"],
        tabular_evidence="absent", remaining=64,
    )
    assert absent["decision"] == "not_found" and absent["reason"] == "evidence_absent"
    assert state["spent"]["pages"] == 0, "absent never consumes a heavy request"
    assert state["reason_counts"]["not_found"] == 1

    unknown, state = admit_geometry_request(
        plan, state, page=11, window_keys=["w-risk"],
        tabular_evidence="unknown", remaining=64,
    )
    assert unknown["decision"] == "unknown" and unknown["reason"] == "evidence_unknown"
    assert state["reason_counts"]["not_found"] == 1, "unknown must not be booked as no-table"
    assert state["reason_counts"]["unknown"] == 1
    assert state["spent"]["pages"] == 0

    candidate, state = admit_geometry_request(
        plan, state, page=12, window_keys=["w-risk"],
        tabular_evidence="observed_candidate", remaining=64,
    )
    assert candidate["decision"] == "admitted"
    assert state["reason_counts"]["not_found"] == 1, "candidate admission does not erase history"

    bad, state = admit_geometry_request(
        plan, state, page=13, window_keys=["w-risk"],
        tabular_evidence="probably", remaining=64,
    )
    assert bad["decision"] == "rejected" and bad["reason"] == "bad_evidence"


def test_administrative_priority1_never_triggers_fine():
    fixture = helpers.load_fixture()
    plan = _fixture_plan(fixture)
    by_window = {row["window_key"]: row for row in plan["allocations"]}
    assert by_window["w-admin"]["reading_priority"] == 1
    assert by_window["w-admin"]["demand_class"] == "administrative"
    assert by_window["w-admin"]["requestable"] == {"discover": True, "fine": False}

    state = new_admission_state(plan)
    decision, state = admit_geometry_request(
        plan, state, page=4, window_keys=["w-admin"],
        tabular_evidence="observed_candidate", remaining=64,
    )
    assert decision["decision"] == "admitted"
    assert decision["request"] == {"discover": True, "fine": False}, (
        "policy said fine=on_candidate but administrative priority-1 must not trigger fine"
    )


def test_mixed_demand_window_admits_candidates_without_being_dropped():
    rule = helpers.tiny_rule("rk_mixed", "mixed")
    plan = plan_geometry_requests(
        helpers.tiny_policy(rule), [helpers.tiny_window("w-mixed", "rk_mixed", 1, 8)],
        page_count=8, limits=helpers.tiny_limits(4), work_budget=_big_budget(),
    )
    assert plan["class_quotas"]["mixed"]["quota"] > 0
    assert plan["allocations"][0]["status"] == "reserved"
    state = new_admission_state(plan)
    decision, state = admit_geometry_request(
        plan, state, page=2, window_keys=["w-mixed"],
        tabular_evidence="observed_candidate", remaining=4,
    )
    assert decision["decision"] == "admitted"


# --- huge inputs and bounded diagnostics ------------------------------------

def test_megabyte_scope_string_stays_bounded():
    fixture = helpers.load_fixture()
    windows = [
        helpers.tiny_window("w-a", "rk_mda", 1, 5),
        helpers.tiny_window("w-huge", "rk_mda", 6, 9, scope="s" * 1_000_000),
        helpers.tiny_window("w-b", "rk_mda", 10, 12),
    ]
    plan = plan_geometry_requests(
        fixture["policy"], windows, page_count=fixture["page_count"],
        limits=helpers.tiny_limits(64), work_budget=_big_budget(),
    )
    codes = [row["code"] for row in plan["diagnostics"]]
    assert "WINDOW_INVALID_FIELD" in codes
    serialized = json.dumps(plan, ensure_ascii=False)
    assert "s" * 4097 not in serialized, "megabyte scope must not be copied into the plan"
    assert len(serialized) < 50_000
    for row in plan["diagnostics"]:
        assert len(row["detail"]) <= 160
    assert plan["summary"]["windows_built"] == 2


def test_huge_window_list_completes_with_bounded_diagnostics():
    fixture = helpers.load_fixture()
    windows = [
        helpers.tiny_window(f"w{i}", "rk_mda", (i % 80) + 1, (i % 80) + 2)
        for i in range(20_000)
    ]
    garbage = [
        dict(helpers.tiny_window(f"w{i}", "rk_mda", 1, 2), physical_start="x")
        for i in range(500)
    ]
    plan = plan_geometry_requests(
        fixture["policy"], windows + garbage, page_count=fixture["page_count"],
        limits=helpers.tiny_limits(64), work_budget=WorkBudget(max_work_units=2_000_000),
    )
    assert plan["summary"]["partial"] is False
    assert plan["summary"]["windows_built"] == 20_000
    assert len(plan["diagnostics"]) <= 256
    # 500 bad-page diagnostics plus the single out-of-order note; the dropped
    # counter carries everything past the bound.
    assert len(plan["diagnostics"]) + plan["diagnostics_dropped"] == 501


def test_huge_disjoint_window_list_stays_linear():
    """20k non-overlapping windows exercise the interval search path."""
    fixture = helpers.load_fixture()
    windows = [
        helpers.tiny_window(f"d{i}", "rk_mda", 2 * i + 1, 2 * i + 2)
        for i in range(20_000)
    ]
    plan = plan_geometry_requests(
        fixture["policy"], windows, page_count=40_000,
        limits=helpers.tiny_limits(64), work_budget=WorkBudget(max_work_units=2_000_000),
    )
    assert plan["summary"]["partial"] is False
    assert plan["summary"]["windows_built"] == 20_000
    by_window = {row["window_key"]: row for row in plan["allocations"]}
    assert by_window["d0"]["quota_pages"] == 1
    assert sum(row["quota_pages"] for row in plan["allocations"]) <= 64


def test_duplicate_and_out_of_order_windows_keep_diagnostics():
    fixture = helpers.load_fixture()
    windows = list(reversed(fixture["windows"]))
    windows.append(dict(fixture["windows"][2]))  # exact duplicate
    plan = plan_geometry_requests(
        fixture["policy"], windows, page_count=fixture["page_count"],
        limits=fixture["limits"], work_budget=_big_budget(),
    )
    codes = [row["code"] for row in plan["diagnostics"]]
    assert "WINDOW_INPUT_OUT_OF_ORDER" in codes
    assert "WINDOW_DUPLICATE_KEY" in codes
    keys = [row["window_key"] for row in plan["allocations"]]
    assert len(keys) == len(set(keys)) == len(fixture["windows"])


def test_admission_diagnostic_flood_stays_bounded_per_call():
    fixture = helpers.load_fixture()
    plan = _fixture_plan(fixture)
    state = new_admission_state(plan)
    for i in range(300):
        decision, state = admit_geometry_request(
            plan, state, page=[i],  # deliberately invalid
            window_keys=["w-risk", {}],
            tabular_evidence="observed_candidate", remaining=64,
        )
        assert decision["decision"] == "rejected"
        assert len(decision["diagnostics"]) <= 256
    assert state["reason_counts"]["rejected"] == 300
    # State stays a small value: counts, never an event log.
    assert len(json.dumps(state)) < 5_000


# --- determinism, purity, protocol surface ----------------------------------

def test_plan_is_order_independent_but_causally_sensitive():
    fixture = helpers.load_fixture()
    plan_a = _fixture_plan(fixture)

    shuffled = list(fixture["windows"])
    random.Random(7).shuffle(shuffled)
    fixture_shuffled = dict(fixture, windows=shuffled)
    plan_b = _fixture_plan(fixture_shuffled)

    # Canonical core is identical; only the order-note diagnostic may differ.
    assert plan_a["plan_digest"] == plan_b["plan_digest"]
    assert plan_a["allocations"] == plan_b["allocations"]
    assert plan_a["class_quotas"] == plan_b["class_quotas"]
    assert plan_a["summary"] == plan_b["summary"]

    # Identical input yields identical output including diagnostics.
    assert _fixture_plan(fixture) == plan_a

    # A causally relevant change (window end) must change the plan.
    causal = json.loads(json.dumps(fixture["windows"]))
    for window in causal:
        if window["window_key"] == "w-attach-op":
            window["physical_end"] = 90
    plan_c = _fixture_plan(dict(fixture, windows=causal))
    assert plan_c["plan_digest"] != plan_a["plan_digest"]


def test_inputs_and_budget_never_mutated():
    fixture = helpers.load_fixture()
    policy_before = json.dumps(fixture["policy"], ensure_ascii=False, sort_keys=True)
    windows_before = json.dumps(fixture["windows"], ensure_ascii=False, sort_keys=True)
    limits_before = json.dumps(fixture["limits"], sort_keys=True)
    budget = WorkBudget(max_work_units=2_000_000)

    plan = plan_geometry_requests(
        fixture["policy"], fixture["windows"],
        page_count=fixture["page_count"], limits=fixture["limits"], work_budget=budget,
    )
    state = new_admission_state(plan)
    state_before = json.dumps(state, sort_keys=True)
    plan_before = json.dumps(plan, ensure_ascii=False, sort_keys=True)

    admit_geometry_request(
        plan, state, page=4, window_keys=["w-admin"],
        tabular_evidence="observed_candidate", remaining=64,
    )
    assert json.dumps(fixture["policy"], ensure_ascii=False, sort_keys=True) == policy_before
    assert json.dumps(fixture["windows"], ensure_ascii=False, sort_keys=True) == windows_before
    assert json.dumps(fixture["limits"], sort_keys=True) == limits_before
    assert json.dumps(state, sort_keys=True) == state_before, "input state must stay untouched"
    assert json.dumps(plan, ensure_ascii=False, sort_keys=True) == plan_before
    assert budget.max_work_units == 2_000_000
    assert 0 <= budget.used <= 2_000_000


def test_only_the_existing_work_budget_protocol_is_accepted():
    fixture = helpers.load_fixture()
    for bad in (None, 1000, "budget", object()):
        with pytest.raises(TypeError):
            plan_geometry_requests(
                fixture["policy"], fixture["windows"],
                page_count=fixture["page_count"], limits=fixture["limits"],
                work_budget=bad,
            )


@pytest.mark.parametrize(
    "limits, error",
    [
        ({"max_pages": -1, "max_requests": 0}, ValueError),
        ({"max_pages": True, "max_requests": 0}, TypeError),
        ({"max_pages": 0}, TypeError),          # missing max_requests
        ({"max_requests": 0}, TypeError),       # missing max_pages
        ({"max_pages": 1.5, "max_requests": 0}, TypeError),
    ],
)
def test_limit_shape_errors_raise(limits, error):
    fixture = helpers.load_fixture()
    with pytest.raises(error):
        plan_geometry_requests(
            fixture["policy"], fixture["windows"],
            page_count=fixture["page_count"], limits=limits, work_budget=_big_budget(),
        )


def test_plan_and_state_are_json_round_trip_compatible():
    fixture = helpers.load_fixture()
    plan = _fixture_plan(fixture)
    plan_again = json.loads(json.dumps(plan, ensure_ascii=False))
    assert plan_again["plan_digest"] == plan["plan_digest"]
    state = new_admission_state(plan)
    decision, state = admit_geometry_request(
        plan, state, page=4, window_keys=["w-admin"],
        tabular_evidence="observed_candidate", remaining=64,
    )
    restored = json.loads(json.dumps(state, ensure_ascii=False))
    assert restored == state
    summary = summarize_admission_state(plan, restored)
    assert json.loads(json.dumps(summary, ensure_ascii=False)) == summary
    assert summary["spent"] == {"pages": 1, "requests": 1}


# --- review findings regressions (F1/F2/F3/F4) ------------------------------

def _tiny_plan(max_pages: int = 2):
    rule = helpers.tiny_rule("rk_op", "operating")
    return plan_geometry_requests(
        helpers.tiny_policy(rule),
        [helpers.tiny_window("w1", "rk_op", 1, 10)],
        page_count=10, limits=helpers.tiny_limits(max_pages), work_budget=_big_budget(),
    )


def test_f1_tampered_plan_after_state_creation_is_refused():
    """Digest must bind plan CONTENT on every use, not just at state mint."""
    plan = _tiny_plan()
    state = new_admission_state(plan)

    tampered = json.loads(json.dumps(plan, ensure_ascii=False))
    tampered["limits"]["max_pages"] = 100
    tampered["class_quotas"]["operating"]["quota"] = 100
    tampered["allocations"][0]["quota_pages"] = 100  # plan_digest left stale
    with pytest.raises(ValueError, match="plan_digest does not match"):
        admit_geometry_request(
            tampered, state, page=1, window_keys=["w1"],
            tabular_evidence="observed_candidate", remaining=100,
        )
    with pytest.raises(ValueError, match="plan_digest does not match"):
        summarize_admission_state(tampered, state)

    # An attacker that also rewrites the digest string is stopped by the
    # content re-derivation itself...
    resigned = json.loads(json.dumps(plan, ensure_ascii=False))
    resigned["allocations"][0]["quota_pages"] = 100
    resigned["plan_digest"] = "0" * 64
    with pytest.raises(ValueError, match="plan_digest does not match"):
        admit_geometry_request(
            resigned, state, page=1, window_keys=["w1"],
            tabular_evidence="observed_candidate", remaining=100,
        )

    # ...and a legitimately different plan (consistent digest) is stopped by
    # the state-to-plan binding instead.
    other_plan = _tiny_plan(max_pages=3)
    assert other_plan["plan_digest"] != plan["plan_digest"]
    with pytest.raises(ValueError, match="different plan"):
        admit_geometry_request(
            other_plan, state, page=1, window_keys=["w1"],
            tabular_evidence="observed_candidate", remaining=3,
        )


def test_f2_decision_envelope_is_bounded_against_huge_caller_objects():
    plan = _tiny_plan()
    state = new_admission_state(plan)

    decision, state = admit_geometry_request(
        plan, state, page="p" * 1_000_000, window_keys=["w" + "x" * 1_000_000],
        tabular_evidence="observed_candidate", remaining=2,
    )
    assert decision["decision"] == "rejected"
    assert decision["page"] == "<str>"
    envelope = json.dumps(decision, ensure_ascii=False)
    assert len(envelope) < 16_384, f"decision envelope must stay bounded, got {len(envelope)}"
    assert all(len(key) <= 4096 for key in decision["window_keys"])

    decision, state = admit_geometry_request(
        plan, state, page=1, window_keys=["k" + "y"] * 100_000,
        tabular_evidence="observed_candidate", remaining=2,
    )
    assert decision["decision"] == "rejected" and decision["reason"] == "bad_window_keys"
    assert len(json.dumps(decision, ensure_ascii=False)) < 300_000, (
        "a huge key list must not be materialized into the echo"
    )

    decision, state = admit_geometry_request(
        plan, state, page=10**18, window_keys=["w1"],
        tabular_evidence="observed_candidate", remaining=2,
    )
    assert isinstance(decision["page"], str) and decision["page"].startswith("<int:")


def test_f3_missing_intent_field_stays_unknown_even_with_non_unknown_default():
    """INTERFACES: 缺字段保守unknown — default_intent must never grant capability."""
    rule = {
        "rule_key": "rk_gap",
        "section_role": "business",
        "reading_priority": 1,
        "geometry_intent": {"demand_class": "operating"},  # discover/fine absent
    }
    policy = {
        "schema_version": "du-geometry-policy/1",
        "profile_id": "du9_gap_profile",
        "profile_version": "du9_gap_profile/v1",
        "default_intent": {"discover": "on_tabular_evidence", "fine": "on_candidate",
                           "demand_class": "operating"},
        "rules": [rule],
    }
    plan = plan_geometry_requests(
        policy, [helpers.tiny_window("w-gap", "rk_gap", 1, 6)],
        page_count=6, limits=helpers.tiny_limits(6), work_budget=_big_budget(),
    )
    assert "POLICY_INTENT_MISSING" in [row["code"] for row in plan["diagnostics"]]
    row = plan["allocations"][0]
    assert row["requestable"] == {"discover": False, "fine": False}
    assert row["status"] == "cancelled" and row["reason"] == "not_requestable"


def test_f4_malformed_plan_raises_valueerror_not_keyerror():
    malformed = {
        "schema_version": "du-geometry-plan/1",
        "plan_digest": "abc",
        "allocations": [],
        "class_quotas": {},
        "summary": {},
        "page_count": 1,
        "limits": {"max_pages": 1, "max_requests": 1},
        # profile_id / profile_version intentionally absent
    }
    with pytest.raises(ValueError):
        new_admission_state(malformed)

    plan = _tiny_plan()
    broken_row = json.loads(json.dumps(plan, ensure_ascii=False))
    del broken_row["allocations"][0]["window_key"]
    with pytest.raises(ValueError):
        new_admission_state(broken_row)

    plan2 = _tiny_plan()
    state = new_admission_state(plan2)
    broken_class = json.loads(json.dumps(plan2, ensure_ascii=False))
    del broken_class["class_quotas"]["operating"]
    with pytest.raises(ValueError):
        admit_geometry_request(
            broken_class, state, page=1, window_keys=["w1"],
            tabular_evidence="observed_candidate", remaining=2,
        )
