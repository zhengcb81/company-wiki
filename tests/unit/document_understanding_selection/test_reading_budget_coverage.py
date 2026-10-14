"""Independent-review regressions for actual emitted coverage and bounded work."""
from dataclasses import replace

import pytest

from company_wiki.source_catalog import narrative_budget as budget
from company_wiki.source_catalog.narrative_semantic_coverage import coverage_signature


def item(uid, order, *, priority=2, topics=(), required=(), group=None, signature=None):
    return budget.BudgetItem(
        item_id=uid, group_id=group, page_key=("page", 1), locator=f"loc:{uid}",
        order_key=(1, order), reasons=(), score=10, is_heading=False, payload=uid,
        evidence_chars=len(uid), reading_priority=priority, reading_topics=topics,
        required_item_ids=required, coverage_signature=signature,
    )


@pytest.mark.parametrize("with_topics", (True, False))
def test_value_dependency_already_emitted_counts_towards_real_coverage(with_topics):
    shared = coverage_signature(
        "The company product remains in customer qualification with ongoing engineering trials "
        "before any commercial delivery to overseas customers."
    )
    # The existing conservative hint requires at least twelve tokens. A shorter
    # fixture must remain unknown, so it cannot test emitted-signature coverage.
    assert shared.complete and len(shared.tokens) >= 12
    novel = coverage_signature("The supply contract with the new supplier restricts output capacity next year.")
    topics = ("shared",) if with_topics else ()
    items = (
        item("a", 0, priority=1, topics=("a",), required=("b",)),
        item("b", 1, topics=topics, signature=shared),
        item("duplicate", 2, topics=topics, signature=shared),
        item("novel", 3, topics=("new",) if with_topics else (), signature=novel),
    )
    selected = budget.select_budget_items(items, limit=3, policy=budget.READING_BUDGET_POLICY)
    assert {row.item_id for row in selected} == {"a", "b", "novel"}


@pytest.mark.parametrize(("field", "value"), (
    ("tokens", tuple("x" for _ in range(513))),
    ("tokens", ["x"]), ("tokens", iter(["x"])), ("tokens", (1,)), ("tokens", ("",)),
    ("protected_sentences", tuple("x" for _ in range(513))),
    ("protected_sentences", (1,)),
    ("stage_signals", tuple(("stage", "predicate", True, "") for _ in range(513))),
    ("stage_signals", (("stage",),)),
    ("stage_signals", (("stage", "predicate", 1, ""),)),
    ("complete", 1),
))
def test_malformed_signature_is_rejected_before_budget_scoring(field, value):
    signature = replace(coverage_signature("The products have customer contracts."), **{field: value})
    with pytest.raises(ValueError, match="coverage_signature"):
        budget.select_budget_items((item("a", 0, signature=signature),), limit=10,
                                   policy=budget.READING_BUDGET_POLICY)


def test_wrong_signature_object_is_rejected_before_scoring():
    with pytest.raises(ValueError, match="coverage_signature"):
        budget.select_budget_items((item("a", 0, signature=object()),), limit=10,
                                   policy=budget.READING_BUDGET_POLICY)


def test_nested_signature_comparisons_respect_actual_work_cap(monkeypatch):
    items = []
    for group in range(20):
        signature = coverage_signature(
            f"The product project {group} remains in customer qualification before commercial delivery."
        )
        for member in range(10):
            items.append(item(f"{group}-{member}", group * 10 + member,
                              topics=(f"topic-{group}",), group=f"group-{group}", signature=signature))
    calls = 0
    original = budget.softly_repeats

    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(budget, "softly_repeats", counted)
    selected = budget.select_budget_items(tuple(items), limit=200,
                                         policy=budget.READING_BUDGET_POLICY, max_work_units=22000)
    assert calls <= 22000
    assert len(selected) < 200
    assert all(sum(row.group_id == group for row in selected) == 10
               for group in {row.group_id for row in selected})


def test_global_work_stop_does_not_claim_an_emitted_dependency_was_omitted():
    items = (item("a", 0, priority=1, required=("b",)), item("b", 1))
    for cap in range(21):
        selected = budget.select_budget_items(items, limit=2, policy=budget.READING_BUDGET_POLICY,
                                             max_work_units=cap)
        diagnostics = budget.budget_diagnostics(items, limit=2, policy=budget.READING_BUDGET_POLICY,
                                               max_work_units=cap)
        ids = {row.item_id for row in selected}
        for row in diagnostics:
            assert not (row.item_ids and set(row.item_ids) <= ids)
        if cap == 0:
            assert diagnostics == budget.budget_diagnostics(tuple(reversed(items)), limit=2,
                policy=budget.READING_BUDGET_POLICY, max_work_units=cap)
