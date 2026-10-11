"""W04 fixed-cap semantic coverage, with real policy-independent counterexamples.

Before the additive API exists, behavioral cases exercise legacy policy to
record the observed failure. API presence is tested separately. No production
fallback is introduced by this test-only baseline adapter.
"""
from dataclasses import fields
import inspect

import pytest

from company_wiki.source_catalog.narrative_budget import (
    BudgetItem, budget_diagnostics, select_budget_items,
)

POLICY = "semantic_coverage/1"
PRODUCT = ("new_product_commercialization_milestone",)
EVENT = ("specific_business_event",)


def item(key, page, *, group=None, score=10, reasons=EVENT, chars=80, paragraph=0):
    kwargs = dict(item_id=key, group_id=group, page_key=("page", page),
        locator=f"page:{page}/paragraph:{paragraph}", order_key=(page, paragraph),
        reasons=reasons, score=score, is_heading=False, payload=key)
    if "evidence_chars" in {field.name for field in fields(BudgetItem)}:
        kwargs["evidence_chars"] = chars
    return BudgetItem(**kwargs)


def choose(items, limit, *, diagnostics=False):
    func = budget_diagnostics if diagnostics else select_budget_items
    kwargs = {"policy": POLICY} if "policy" in inspect.signature(func).parameters else {}
    return func(tuple(items), limit=limit, **kwargs)


def ids(items):
    return {x.item_id for x in items}


def test_business_dense_page_beats_lower_scoring_unvisited_page():
    items = [item("strong-first", 1, score=20, reasons=PRODUCT),
             item("strong-next", 1, score=19, reasons=PRODUCT, paragraph=1),
             item("weaker-elsewhere", 2, score=2, reasons=PRODUCT)]
    assert ids(choose(items, 2)) == {"strong-first", "strong-next"}


def test_complete_context_beats_same_score_short_generic_fragment():
    items = [item("first", 1, score=20, reasons=PRODUCT),
             item("context-a", 1, group="context", reasons=PRODUCT, chars=170, paragraph=1),
             item("context-b", 1, group="context", reasons=PRODUCT, chars=180, paragraph=2),
             item("short", 2, reasons=PRODUCT, chars=12)]
    assert ids(choose(items, 3)) == {"first", "context-a", "context-b"}


def test_content_priority_also_applies_when_fair_share_is_not_active():
    items = [item("first", 1, score=20, reasons=PRODUCT),
             item("second", 1, score=19, reasons=PRODUCT, paragraph=1),
             item("weak", 2, score=1, reasons=PRODUCT),
             item("risk", 3, reasons=("business_risk_or_constraint",))]
    assert ids(choose(items, 2)) == {"first", "second"}


@pytest.mark.parametrize("special,category", [
    ("project_plan_or_status", "project"),
    ("operating_mechanism", "operating_mechanism"),
])
def test_generic_event_does_not_hide_distinct_semantic_family(special, category):
    items = [item(f"event-{i}", i+1, score=90) for i in range(14)]
    items.append(item("distinct", 20, reasons=("specific_business_event", special)))
    selected = choose(items, 6)
    assert "distinct" in ids(selected)
    # Force omission to prove the actual diagnostic uses the semantic category.
    group = [item(f"oversize-{i}", 21, group="oversize", reasons=("specific_business_event", special)) for i in range(7)]
    rows = choose(items + group, 6, diagnostics=True)
    assert next(row.category for row in rows if row.group_id == "oversize") == category


def test_long_text_cannot_outrank_higher_score():
    items = [item("high", 1, score=11, chars=2), item("long", 2, score=10, chars=10_000)]
    assert ids(choose(items, 1)) == {"high"}


def test_character_tiebreak_is_bounded():
    items = [item("earlier", 1, chars=512), item("oversized-text", 2, chars=90_000)]
    assert ids(choose(items, 1)) == {"earlier"}


def test_page_diversity_still_breaks_equal_content_ties():
    items = [item("first", 1, score=20), item("dense", 1, paragraph=1), item("other", 2)]
    assert ids(choose(items, 2)) == {"first", "other"}


@pytest.mark.parametrize("reason", ["direct_capacity_constraint", "customer_adoption_milestone", "new_product_commercialization_milestone", "specific_project_rationale"])
def test_specific_milestones_and_constraints_keep_their_category(reason):
    items = [item(f"big-{i}", 1, group="big", reasons=(reason, "operating_mechanism", "project_plan_or_status")) for i in range(5)]
    items.append(item("small", 2))
    rows = choose(items, 4, diagnostics=True)
    expected = {"direct_capacity_constraint":"critical_risk", "customer_adoption_milestone":"customer_adoption", "new_product_commercialization_milestone":"product_milestone", "specific_project_rationale":"rationale"}[reason]
    assert next(row.category for row in rows if row.group_id == "big") == expected


@pytest.mark.parametrize("limit", [1, 3, 6, 12, 96])
def test_whole_group_actual_span_cost_determinism_and_diagnostic_partition(limit):
    items = [item(f"g-{g}-{m}", 1+g%4, group=f"g{g}", paragraph=g*3+m,
                  score=20-g%7, reasons=PRODUCT if g%2 else EVENT, chars=45+m)
             for g in range(40) for m in range(1+g%3)]
    selected = choose(items, limit)
    assert len(selected) <= limit
    assert selected == choose(list(reversed(items)), limit)
    assert selected == choose(items[::2]+items[1::2], limit)
    chosen = ids(selected)
    for group in {x.group_id for x in items}:
        members = {x.item_id for x in items if x.group_id == group}
        assert not (members & chosen) or members <= chosen
    rows = choose(items, limit, diagnostics=True)
    omitted = {key for row in rows for key in row.item_ids}
    assert not chosen & omitted
    assert chosen | omitted == ids(items)
    assert sum(row.item_count for row in rows) + len(selected) == len(items)


def test_soft_category_share_preserves_industry_and_mechanism():
    items = [item(f"risk-{i}", i+1, score=50, reasons=("business_risk_or_constraint",)) for i in range(120)]
    items += [item("industry", 121, reasons=("current_industry_context",)),
              item("mechanism", 122, reasons=("operating_mechanism", "specific_business_event")),
              item("project", 123, reasons=("project_plan_or_status", "specific_business_event"))]
    assert {"industry", "mechanism", "project"} <= ids(choose(items, 96))


def test_explicit_legacy_is_default_and_character_count_has_no_legacy_effect():
    items = [item("first", 1, score=20), item("dense", 1, paragraph=1, chars=400), item("other", 2, chars=1)]
    assert "policy" in inspect.signature(select_budget_items).parameters
    assert select_budget_items(tuple(items), limit=2) == select_budget_items(tuple(items), limit=2, policy="legacy")
    assert ids(select_budget_items(tuple(items), limit=2)) == {"first", "other"}


@pytest.mark.parametrize("func", [select_budget_items, budget_diagnostics])
def test_unknown_policy_is_rejected_even_without_budget_pressure(func):
    assert "policy" in inspect.signature(func).parameters
    with pytest.raises(ValueError, match="policy"):
        func((), limit=96, policy="future/unknown")


@pytest.mark.parametrize("chars", [-1, 1.5, True])
def test_semantic_character_metadata_must_be_valid_without_changing_span_cost(chars):
    assert "evidence_chars" in {field.name for field in fields(BudgetItem)}
    with pytest.raises(ValueError, match="evidence_chars"):
        choose([item("bad", 1, chars=chars)], 96)


def test_semantic_selection_does_not_read_files(monkeypatch):
    import builtins
    items = [item(str(i), i, reasons=PRODUCT) for i in range(8)]
    def blocked(*args, **kwargs):
        raise AssertionError("no budget IO")
    monkeypatch.setattr(builtins, "open", blocked)
    assert len(choose(items, 4)) == 4


@pytest.mark.parametrize("score,chars", [(99, 2000), (10, 450)])
def test_actual_product_progress_is_not_outbid_by_generic_named_context(score, chars):
    items = [item("generic", 1, score=score, chars=chars,
                  reasons=("named_product_milestone_context",)),
             item("progress", 8, score=3, chars=50,
                  reasons=("new_product_commercialization_milestone",))]
    assert ids(choose(items, 1)) == {"progress"}


def test_quantified_actual_stage_wins_before_score_and_length_in_same_product_family():
    items = [item("general-stage", 1, score=90, chars=500, reasons=PRODUCT),
             item("quantified-stage", 9, score=8, chars=80,
                  reasons=(*PRODUCT, "quantified_operating_status"))]
    assert ids(choose(items, 1)) == {"quantified-stage"}


def test_named_and_actual_product_context_share_one_semantic_quota():
    items = [item(f"generic-{i}", i+1, score=90,
                  reasons=("named_product_milestone_context",)) for i in range(100)]
    items += [item("actual", 101, reasons=PRODUCT),
              item("industry", 102, reasons=("current_industry_context",))]
    rows = choose(items, 8, diagnostics=True)
    assert {row.category for row in rows if row.item_id.startswith("generic-")} == {"product_milestone"}
    assert {"actual", "industry"} <= ids(choose(items, 8))


@pytest.mark.parametrize("reason", ["downstream_center_certification_timeline", "downstream_business_extension"])
def test_reserved_semantic_evidence_uses_same_bounded_context_tie_break(reason):
    items = [item("short", 1, score=10, chars=12, reasons=(reason,)),
             item("whole", 8, score=10, chars=400, reasons=(reason,))]
    assert ids(choose(items, 1)) == {"whole"}
    assert ids(select_budget_items(tuple(items), limit=1)) == {"short"}



def with_text(value, text):
    from dataclasses import replace
    from company_wiki.source_catalog.narrative_semantic_coverage import coverage_signature
    signature = coverage_signature(text)
    return replace(value, semantic_tokens=signature.tokens, coverage_signature=signature)


def test_soft_redundancy_leaves_room_for_another_actual_product_fact():
    common = "公司持续推进工艺研发并完善客户支持，LPCVD设备已经通过客户验证。"
    novel = "医疗设备已经交付客户并开展服务，新型平台已获得客户重复订单。"
    items = [with_text(item("best", 1, score=30, reasons=PRODUCT), common),
             with_text(item("repeat", 2, score=29, reasons=PRODUCT), common),
             with_text(item("distinct", 3, score=8, reasons=PRODUCT), novel)]
    assert ids(choose(items, 2)) == {"best", "distinct"}
    assert ids(select_budget_items(tuple(items), limit=2)) == {"best", "repeat"}
    assert choose(items, 2) == choose(list(reversed(items)), 2)


def test_soft_redundancy_never_prefers_generic_context_over_an_actual_stage():
    common = "公司持续推进工艺研发并完善客户支持，LPCVD设备已经通过客户验证。"
    items = [with_text(item("best", 1, score=30, reasons=PRODUCT), common),
             with_text(item("repeat", 2, score=29, reasons=PRODUCT), common),
             with_text(item("generic", 3, score=100,
                         reasons=("named_product_milestone_context",)), "另一系列产品的技术背景。")]
    assert ids(choose(items, 2)) == {"best", "repeat"}


def test_partial_shared_vocabulary_is_not_treated_as_repetition():
    a = "公司持续推进客户支持服务。"
    one = a + "激光设备在先进制造工艺中完成客户现场验证，扩大技术应用范围。"
    two = a + "医疗平台已经获得追加订单，生产基地持续投入使用，扩大服务业务。"
    items = [with_text(item("first", 1, score=20, reasons=PRODUCT), one),
             with_text(item("second", 2, score=19, reasons=PRODUCT), two),
             with_text(item("weak", 3, score=1, reasons=PRODUCT), "另一系列产品的技术背景。")]
    assert ids(choose(items, 2)) == {"first", "second"}


def test_specific_operating_constraint_is_kept_ahead_of_generic_risk():
    items = [item("generic", 1, score=99, reasons=("business_risk_or_constraint",)),
             item("supply", 8, score=5, reasons=("specific_operating_constraint",))]
    assert ids(choose(items, 1)) == {"supply"}
