"""Node A/B: frozen root cause plus the independent fairness expectation.

``test_baseline_front_greedy_starves_deep_windows`` permanently documents the
diagnosed production pathology (front monopoly exhausts the shared 64-page
fine-geometry limit before far operating/project windows arrive).
``test_frozen_fairness_expectation_holds_under_planner`` encodes the frozen
hand-calculated expectation against the DU9 planner; it was the first FAIL
(receipts/red_first_fail.txt) before ``geometry_intent`` existed.
"""
from __future__ import annotations

from . import helpers


def _planner():
    from company_wiki.document_understanding.geometry_intent import (  # noqa: PLC0415
        admit_geometry_request,
        new_admission_state,
        plan_geometry_requests,
    )

    return plan_geometry_requests, new_admission_state, admit_geometry_request


def test_baseline_front_greedy_starves_deep_windows():
    """Root cause documentation: the current front-first behavior starves the back."""
    fixture = helpers.load_fixture()
    admitted = helpers.legacy_front_greedy_admissions(fixture)
    total = sum(len(pages) for pages in admitted.values())

    # The shared limit dies inside the front chapters, exactly as diagnosed.
    assert total == fixture["limits"]["max_pages"]
    by_class = helpers.admitted_by_class(fixture, admitted)
    assert by_class.get("project", 0) == 0, "deep 募投 chapters must be starved by the baseline"
    assert len(admitted.get("w-attach-op", [])) == 0, "deepest window must be starved by the baseline"
    # Front context chapters consumed the whole limit.
    assert by_class.get("context", 0) >= 40


def test_frozen_fairness_expectation_holds_under_planner():
    """Independent expectation, hand-calculated in findings.md; no cap raising."""
    from company_wiki.document_understanding.layout_hints.contract import WorkBudget

    plan_geometry_requests, new_admission_state, admit = _planner()
    fixture = helpers.load_fixture()

    plan = plan_geometry_requests(
        fixture["policy"],
        fixture["windows"],
        page_count=fixture["page_count"],
        limits=fixture["limits"],
        work_budget=WorkBudget(max_work_units=2_000_000),
    )
    calc = fixture["hand_calc"]

    quotas = {
        row["window_key"]: row["quota_pages"]
        for row in plan["allocations"]
        if row["status"] == "reserved"
    }
    assert quotas == calc["window_quotas"]
    cancelled = {
        row["window_key"]: row["reason"]
        for row in plan["allocations"]
        if row["status"] == "cancelled"
    }
    assert cancelled == calc["cancelled"]
    class_quotas = {c: row["quota"] for c, row in plan["class_quotas"].items()}
    assert class_quotas == calc["class_quotas"]
    assert sum(class_quotas.values()) <= fixture["limits"]["max_pages"]

    state = new_admission_state(plan)
    by_window: dict[str, int] = {}
    total_admitted = 0
    for page, keys in helpers.all_candidate_events(fixture):
        decision, state = admit(
            plan, state, page=page, window_keys=keys,
            tabular_evidence="observed_candidate",
            remaining=fixture["limits"]["max_pages"],
        )
        if decision["decision"] == "admitted":
            total_admitted += 1
            for key in decision["admitted_window_keys"]:
                by_window[key] = by_window.get(key, 0) + 1

    # The frozen RED expectation: the back must not be starved under the same cap.
    assert by_window.get("w-attach-op", 0) >= 1, "deepest operating window must get a chance"
    assert by_window.get("w-proj-a", 0) + by_window.get("w-proj-parent", 0) >= 1, (
        "project class must get a chance"
    )
    # Boundedness unchanged: never more than the shared limit.
    assert total_admitted == fixture["limits"]["max_pages"]
