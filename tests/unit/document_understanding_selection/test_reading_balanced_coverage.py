"""Repeated covered themes cannot permanently starve equally valuable themes."""

from dataclasses import replace

import pytest

from company_wiki.source_catalog import narrative_budget as budget
from company_wiki.source_catalog.narrative_semantic_coverage import CoverageSignature

POLICY = "reading_plan/3"


def item(
    uid,
    order,
    *,
    priority=1,
    topics=("detail",),
    value="meaningful_fact",
    required=(),
    context=False,
    chars=100,
    score=10,
    signature=None,
    group=None,
):
    return budget.BudgetItem(
        item_id=uid,
        group_id=group,
        page_key=("page", 1),
        locator=f"loc:{uid}",
        order_key=(order,),
        reasons=(),
        score=score,
        is_heading=False,
        payload=None,
        evidence_chars=chars,
        reading_priority=priority,
        reading_topics=topics,
        required_item_ids=required,
        is_context_only=context,
        value_band=value,
        coverage_signature=signature,
    )


def plan(items, *, limit=3, policy=POLICY, **kwargs):
    return budget.plan_budget_items(tuple(items), limit=limit, policy=policy, **kwargs)


def ids(rows):
    return {row.item_id for row in rows}


def crowd(*, overview_required=()):
    seed = item("seed", 0, topics=("detail", "overall"), score=1000)
    details = tuple(item(f"detail-{i}", i + 1) for i in range(10))
    overall = item(
        "overall", 30, priority=2, topics=("overall",), required=overview_required
    )
    return (seed, *details, overall)


def test_current_fair_policy_and_explicit_previous_value_policy_are_named():
    assert budget.READING_BUDGET_POLICY == POLICY
    assert budget.REPLAY_READING_BUDGET_POLICY == "reading_plan/1"
    assert budget.REPLAY_VALUE_READING_BUDGET_POLICY == "reading_plan/2"


def test_already_covered_sparse_theme_gets_a_turn_after_repeated_detail():
    rows = crowd()
    selected, _ = plan(rows)
    assert ids(selected) == {"seed", "detail-0", "overall"}
    assert [row.item_id for row in selected] == ["seed", "detail-0", "overall"]


def test_same_theme_visits_still_respect_real_scope_priority():
    seed = item("seed", 0, score=1000)
    lower = item("lower", 1, priority=2, score=1000)
    higher = item("higher", 2, priority=1, score=1)
    assert ids(plan((seed, lower, higher), limit=2)[0]) == {"seed", "higher"}
    assert ids(
        plan((seed, lower, replace(higher, reading_priority=3)), limit=2)[0]
    ) == {"seed", "lower"}


def test_equal_normalized_visits_do_not_punish_a_richly_labelled_fact():
    seed = item("seed", 0, topics=("supply", "billing"), score=1000)
    rich = item("rich", 1, topics=("supply", "billing"), priority=1)
    narrow = item("narrow", 2, topics=("supply",), priority=2, score=1000)
    assert ids(plan((seed, rich, narrow), limit=2)[0]) == {"seed", "rich"}


def test_fact_value_always_precedes_even_novel_high_priority_description():
    rows = crowd()
    description = item(
        "new-description", 40, value="description", topics=("new",), score=99999
    )
    assert ids(plan((*rows, description))[0]) == {"seed", "detail-0", "overall"}


def test_shared_heading_cost_is_unique_without_claiming_its_topics_as_coverage():
    head = item("header", 99, context=True, topics=("overall",), chars=50, score=99999)
    rows = crowd(overview_required=("header",))
    rows = (replace(rows[0], required_item_ids=("header",)), *rows[1:])
    selected, _ = plan((*rows, head), limit=4, max_chars=350)
    assert ids(selected) == {"seed", "detail-0", "overall", "header"}
    assert sum(row.evidence_chars for row in selected) == 350


@pytest.mark.parametrize("limit,chars", [(3, 1000), (4, 374)])
def test_sparse_fact_must_pay_full_dependency_slots_and_characters(limit, chars):
    head = item("header", 99, context=True, topics=(), chars=75)
    selected, diagnostics = plan(
        (*crowd(overview_required=("header",)), head), limit=limit, max_chars=chars
    )
    assert not ({"overall", "header"} & ids(selected))
    assert any(
        row.reason in {"budget_full", "character_budget"} and row.item_id == "overall"
        for row in diagnostics
    )


def test_old_policies_replay_the_same_previously_observed_crowded_output():
    rows = crowd()
    assert ids(plan(rows, policy="reading_plan/1")[0]) == {
        "seed",
        "detail-0",
        "detail-1",
    }
    assert ids(plan(rows, policy="reading_plan/2")[0]) == {
        "seed",
        "detail-0",
        "detail-1",
    }
    for policy in (budget.LEGACY_BUDGET_POLICY, budget.SEMANTIC_BUDGET_POLICY):
        assert ids(plan(rows, policy=policy)[0]) == {"seed", "detail-0", "detail-1"}


@pytest.mark.parametrize("detail_topics", [("detail",), ()])
def test_twenty_thousand_real_shared_signatures_keep_late_sparse_facts_and_caps(
    detail_topics,
):
    signature = CoverageSignature(tuple(f"word-{i}" for i in range(50)), (), (), True)
    seed = item(
        "seed",
        0,
        topics=("detail", "rare-a", "rare-b", "rare-c"),
        score=1000,
        signature=signature,
    )
    details = tuple(
        item(f"detail-{i}", i + 1, signature=signature, topics=detail_topics)
        for i in range(19996)
    )
    sparse = tuple(
        item(f"sparse-{i}", 19997 + i, priority=2, topics=(topic,))
        for i, topic in enumerate(("rare-a", "rare-b", "rare-c"))
    )
    selected, diagnostics = plan(
        (seed, *details, *sparse), limit=96, max_chars=48000, max_work_units=2000000
    )
    assert ids(sparse) <= ids(selected)
    assert len(selected) == len(ids(selected)) == 96
    assert sum(row.evidence_chars for row in selected) <= 48000
    assert not any(row.reason == "work_budget_exhausted" for row in diagnostics)


def test_work_stop_is_visible_and_never_emits_half_of_a_shared_group():
    rows = tuple(item(f"member-{i}", i, group=f"group-{i // 10}") for i in range(20000))
    selected, diagnostics = plan(rows, limit=96, max_chars=48000, max_work_units=50000)
    assert any(row.reason == "work_budget_exhausted" for row in diagnostics)
    assert all(
        sum(row.group_id == group for row in selected) == 10
        for group in {row.group_id for row in selected}
    )


def test_missing_topic_metadata_is_not_perpetual_zero_visitation_privilege():
    seed = item("seed", 0, topics=("known",), score=1000)
    unlabelled = tuple(item(f"unknown-{i}", i + 1, topics=()) for i in range(12))
    known = item("known-again", 30, priority=2, topics=("known",))
    selected, _ = plan((seed, *unlabelled, known), limit=4)
    # Unknown operating facts can get a real turn. After two such turns, the
    # once-visited known theme must not remain below permanently zero labels.
    assert ids(selected) == {"seed", "unknown-0", "unknown-1", "known-again"}


def test_unlabelled_bundle_is_one_visit_but_still_pays_its_complete_table_cost():
    seed = item("seed", 0, topics=("known",), score=1000)
    table = tuple(
        item(f"table-{i}", i + 1, topics=(), group="actual-table", score=100)
        for i in range(3)
    )
    other = item("other-unknown", 5, topics=())
    known = item("known-again", 8, priority=2, topics=("known",))
    selected, _ = plan((seed, *table, other, known), limit=6, max_chars=600)
    assert ids(selected) == {
        "seed",
        "table-0",
        "table-1",
        "table-2",
        "other-unknown",
        "known-again",
    }
    assert sum(row.evidence_chars for row in selected) == 600
    # Three inseparable rows provide one unlabelled operating mechanism, not
    # three separate theme visits. With one slot left, its peer still wins an
    # equal-visit scope tie before the once-covered lower-priority known theme.
    capped, _ = plan((seed, *table, other, known), limit=5, max_chars=500)
    assert ids(capped) == {"seed", "table-0", "table-1", "table-2", "other-unknown"}


def test_shared_unlabelled_visit_change_refreshes_other_priority_buckets():
    seed = item("seed", 0, topics=("known",), score=1000)
    low = tuple(
        item(f"unknown-low-{i}", i + 1, topics=(), priority=2) for i in range(3)
    )
    high = tuple(
        item(f"unknown-high-{i}", i + 10, topics=(), priority=1) for i in range(3)
    )
    known = item("known-again", 20, topics=("known",), priority=3)
    selected, _ = plan((seed, *low, *high, known), limit=4)
    assert ids(selected) == {"seed", "unknown-high-0", "unknown-high-1", "known-again"}
