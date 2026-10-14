"""Large documents keep the whole candidate domain inside the existing work cap."""

from dataclasses import replace

import pytest

from company_wiki.source_catalog import narrative_budget as budget
from company_wiki.source_catalog.narrative_semantic_coverage import coverage_signature


def candidate(index, *, priority=3, topics=("operations",), signature=None, required=(), context=False):
    return budget.BudgetItem(item_id=f"unit-{index:05}", group_id=None,
        page_key=("page", index // 25 + 1), locator=f"loc:v1/paragraph:{index}",
        order_key=(index // 25 + 1, index % 25), reasons=(), score=10,
        is_heading=False, payload=object(), evidence_chars=85,
        reading_priority=priority, reading_topics=topics, coverage_signature=signature,
        required_item_ids=required, is_context_only=context)


@pytest.mark.parametrize("signatures", ["absent", "distinct", "repeated"])
def test_twenty_thousand_candidates_keep_all_late_priority_one_business_and_fill_cap(signatures, monkeypatch):
    shared = coverage_signature(
        "Our product service expanded to a new operating region during the reporting period."
    )
    items = tuple(candidate(index, priority=1 if index >= 19997 else 3,
        signature=None if signatures == "absent" else shared if signatures == "repeated" else coverage_signature(
            f"Our product {index} service expanded to a new operating region during the reporting period."
        )) for index in range(20000))
    calls = []
    original = budget.softly_repeats

    def observed(current, previous):
        calls.append((current, previous))
        return original(current, previous)

    monkeypatch.setattr(budget, "softly_repeats", observed)
    selected, diagnostics = budget.plan_budget_items(items, limit=96,
        policy=budget.READING_BUDGET_POLICY, max_chars=48000, max_work_units=2_000_000)
    ids = {row.item_id for row in selected}
    assert {row.item_id for row in items[-3:]} <= ids
    assert len(selected) == 96, "the bounded planner must not silently stop after two selections"
    assert not any(row.reason == "work_budget_exhausted" for row in diagnostics)
    assert sum(row.evidence_chars for row in selected) <= 48000
    assert len(ids) == len(selected)
    # The conservative overlap predicate already requires equal protected facts.
    # Comparing all unrelated facts against every selected item wastes the cap.
    assert len(calls) <= 96


def test_twenty_thousand_repeated_topics_leave_slots_for_independent_late_business():
    items = tuple(candidate(index, priority=1) for index in range(19998)) + (
        candidate(19998, priority=1, topics=("supply",)),
        candidate(19999, priority=1, topics=("service",)),
    )
    selected, diagnostics = budget.plan_budget_items(items, limit=3,
        policy=budget.READING_BUDGET_POLICY, max_work_units=2_000_000)
    assert {row.item_id for row in selected} == {"unit-00000", "unit-19998", "unit-19999"}
    assert not any(row.reason == "work_budget_exhausted" for row in diagnostics)


def test_many_independent_topics_do_not_need_an_all_candidate_rescan_each_round():
    items = tuple(candidate(index, priority=1, topics=(f"topic-{index}",)) for index in range(20000))
    selected, diagnostics = budget.plan_budget_items(items, limit=96,
        policy=budget.READING_BUDGET_POLICY, max_work_units=2_000_000)
    assert selected == items[:96]
    assert not any(row.reason == "work_budget_exhausted" for row in diagnostics)


def test_two_thousand_anchors_charge_shared_original_context_once_without_union():
    context = candidate(2000, context=True, topics=())
    items = tuple(candidate(index, priority=1, required=(context.item_id,),
                            topics=(f"topic-{index}",)) for index in range(2000)) + (context,)
    selected, diagnostics = budget.plan_budget_items(items, limit=97,
        policy=budget.READING_BUDGET_POLICY, max_work_units=2_000_000)
    assert len(selected) == 97
    assert {row.item_id for row in selected} == {row.item_id for row in items[:96]} | {context.item_id}
    assert sum(row.evidence_chars for row in selected) == 97 * 85
    assert not any(row.reason == "work_budget_exhausted" for row in diagnostics)


def test_incremental_dependency_cost_can_promote_a_candidate_over_equal_score_peer():
    header = candidate(10, context=True, topics=())
    first = candidate(0, priority=1, required=(header.item_id,), topics=("first",))
    expensive = candidate(1, priority=2, required=("unit-00011",), topics=("shared",))
    recovered = candidate(2, priority=2, required=(header.item_id,), topics=("shared",))
    other_context = candidate(11, context=True, topics=())
    selected, _ = budget.plan_budget_items((first, expensive, recovered, header, other_context),
        limit=3, policy=budget.READING_BUDGET_POLICY)
    assert {row.item_id for row in selected} == {first.item_id, recovered.item_id, header.item_id}


def test_large_work_stop_is_explicit_and_never_returns_half_an_atomic_context_group():
    items = tuple(replace(candidate(index, priority=1), group_id=f"group-{index // 10}")
                  for index in range(20000))
    selected, diagnostics = budget.plan_budget_items(items, limit=96,
        policy=budget.READING_BUDGET_POLICY, max_work_units=50000)
    assert any(row.reason == "work_budget_exhausted" for row in diagnostics)
    assert all(sum(row.group_id == group for row in selected) == 10
               for group in {row.group_id for row in selected})
    assert all(not (row.item_ids and set(row.item_ids) <= {item.item_id for item in selected})
               for row in diagnostics)


def test_combined_public_plan_keeps_existing_legacy_and_semantic_public_results():
    items = tuple(candidate(index) for index in range(8))
    for policy in (budget.LEGACY_BUDGET_POLICY, budget.SEMANTIC_BUDGET_POLICY):
        selected, diagnostics = budget.plan_budget_items(items, limit=3, policy=policy)
        assert selected == budget.select_budget_items(items, limit=3, policy=policy)
        assert diagnostics == budget.budget_diagnostics(items, limit=3, policy=policy)
