"""N6-BUDGET selection: fixed cap, whole groups, diversity, diagnostics."""

from __future__ import annotations

import builtins

import pytest

from company_wiki.source_catalog.narrative_budget import (
    BudgetItem,
    budget_diagnostics,
    select_budget_items,
)
from company_wiki.source_contract import EvidenceCoordinates


def _item(
    item_id: str,
    *,
    page: int,
    paragraph: int = 0,
    group_id: str | None = None,
    reasons: tuple[str, ...] = ("specific_business_event",),
    score: int = 5,
    is_heading: bool = False,
) -> BudgetItem[str]:
    coordinates = EvidenceCoordinates(page_number=page, paragraph_index=paragraph)
    return BudgetItem(
        item_id=item_id,
        group_id=group_id,
        page_key=("page", page),
        locator=coordinates.locator(),
        order_key=(page, paragraph, -1, -1, -1, -1, -1),
        reasons=reasons,
        score=score,
        is_heading=is_heading,
        payload=item_id,
    )


def _specific_business_mix(limit: int) -> tuple[BudgetItem[str], ...]:
    """60 pages of high-frequency generic risk plus four specific categories."""
    items: list[BudgetItem[str]] = []
    for page in range(1, 61):
        for member in range(2):
            items.append(
                _item(
                    f"risk-{page}-{member}",
                    page=page,
                    paragraph=member,
                    group_id=f"risk:{page}",
                    reasons=("business_risk_or_constraint",),
                    score=40,
                )
            )
    items.append(
        _item(
            "capacity",
            page=71,
            group_id="capacity",
            reasons=("direct_capacity_constraint",),
            score=12,
        )
    )
    for index in range(2):
        items.append(
            _item(
                f"product-{index}",
                page=70,
                paragraph=index + 1,
                group_id="product",
                reasons=("named_product_milestone_context",),
                score=10,
            )
        )
    for index in range(3):
        items.append(
            _item(
                f"industry-{index}",
                page=72,
                paragraph=index + 1,
                group_id="industry",
                reasons=("current_industry_context",),
                score=8,
            )
        )
    for index in range(2):
        items.append(
            _item(
                f"project-{index}",
                page=73,
                paragraph=index + 1,
                group_id="project",
                reasons=("project_plan_or_status",),
                score=9,
            )
        )
    assert len(items) > limit
    return tuple(items)


def test_generic_risk_cannot_crowd_out_specific_business_categories() -> None:
    limit = 96
    items = _specific_business_mix(limit)

    selected = select_budget_items(items, limit=limit)
    selected_ids = {item.item_id for item in selected}

    assert len(selected) <= limit
    assert {"capacity"} <= selected_ids
    assert {"product-0", "product-1"} <= selected_ids
    assert {"industry-0", "industry-1", "industry-2"} <= selected_ids
    assert {"project-0", "project-1"} <= selected_ids
    risk_spans = sum(1 for item in selected if item.item_id.startswith("risk-"))
    assert risk_spans < limit


def test_selection_is_stable_for_ties_and_input_order_changes() -> None:
    items = tuple(
        _item(
            f"tie-{index}",
            page=page,
            paragraph=paragraph,
            group_id=None if index % 2 else f"group:{index % 3}",
            reasons=("specific_business_event",),
            score=7,
        )
        for index, (page, paragraph) in enumerate(
            (page, paragraph) for page in range(1, 6) for paragraph in range(3)
        )
    )
    assert len(items) == 15
    limit = 7

    baseline = select_budget_items(items, limit=limit)
    reversed_order = select_budget_items(tuple(reversed(items)), limit=limit)
    interleaved = select_budget_items(items[::2] + items[1::2], limit=limit)

    assert baseline == reversed_order
    assert baseline == interleaved
    assert len(baseline) <= limit
    assert {item.item_id for item in baseline} == {
        item.item_id for item in reversed_order
    }


def test_oversized_group_is_dropped_whole_and_diagnosed() -> None:
    limit = 4
    oversized = tuple(
        _item(f"big-{index}", page=1, paragraph=index, group_id="big", score=10)
        for index in range(5)
    )
    smalls = tuple(
        _item(f"small-{index}", page=index + 2, score=3) for index in range(3)
    )
    items = oversized + smalls

    selected = select_budget_items(items, limit=limit)
    selected_ids = {item.item_id for item in selected}

    assert selected_ids.isdisjoint({item.item_id for item in oversized})
    assert len(selected) <= limit
    assert selected_ids == {item.item_id for item in smalls}

    diagnostics = budget_diagnostics(items, limit=limit)
    oversized_diagnostics = [row for row in diagnostics if row.group_id == "big"]
    assert oversized_diagnostics
    assert {row.reason for row in oversized_diagnostics} == {"group_exceeds_limit"}
    assert oversized_diagnostics[0].item_count == 5
    assert oversized_diagnostics[0].item_ids == tuple(
        item.item_id for item in oversized
    )
    assert oversized_diagnostics[0].locator == oversized[0].locator


def test_diagnostics_only_describe_unselected_items_and_cover_the_rest() -> None:
    limit = 5
    exact_group = tuple(
        _item(
            f"exact-{index}",
            page=1,
            paragraph=index,
            group_id="exact",
            score=10,
        )
        for index in range(limit)
    )
    singleton = (_item("late", page=2, paragraph=0, score=10),)
    items = exact_group + singleton

    selected = select_budget_items(items, limit=limit)
    diagnostics = budget_diagnostics(items, limit=limit)

    assert {item.item_id for item in selected} == {item.item_id for item in exact_group}
    assert len(selected) == limit
    diagnosed = {item_id for row in diagnostics for item_id in row.item_ids}
    assert diagnosed == {"late"}
    assert diagnostics[0].reason == "budget_full"
    assert diagnostics[0].item_count == 1
    assert {item.item_id for item in selected} | diagnosed == {
        item.item_id for item in items
    }


def test_group_cost_is_the_real_span_count() -> None:
    limit = 6
    group = tuple(
        _item(f"g-{index}", page=1, paragraph=index, group_id="g", score=9)
        for index in range(limit)
    )
    other = (_item("o-0", page=2, score=9), _item("o-1", page=3, score=9))

    selected = select_budget_items((*group, *other), limit=limit)

    assert {item.item_id for item in selected} == {item.item_id for item in group}


def test_reserved_reason_is_still_reserved_before_rotation() -> None:
    items = (
        _item("event", page=1, score=100),
        _item(
            "extension",
            page=9,
            reasons=("downstream_business_extension",),
            score=1,
        ),
        _item("risk", page=2, reasons=("business_risk_or_constraint",), score=20),
    )

    selected = select_budget_items(items, limit=2)
    selected_ids = {item.item_id for item in selected}

    assert "extension" in selected_ids
    assert len(selected_ids) == 2


def test_invalid_limit_is_rejected() -> None:
    items = (_item("only", page=1),)

    with pytest.raises(ValueError, match="limit must be positive"):
        select_budget_items(items, limit=0)
    with pytest.raises(ValueError, match="limit must be positive"):
        budget_diagnostics(items, limit=0)


def test_duplicate_item_ids_are_rejected() -> None:
    duplicate = _item("same", page=1)

    with pytest.raises(ValueError, match="item_id values must be unique"):
        select_budget_items((duplicate, duplicate), limit=1)


def test_budget_uses_only_the_current_input(monkeypatch) -> None:
    items = _specific_business_mix(limit=12)

    def blocked(*_args, **_kwargs):
        raise AssertionError("budget must not read files or open sockets")

    monkeypatch.setattr(builtins, "open", blocked)

    selected = select_budget_items(items, limit=12)
    diagnostics = budget_diagnostics(items, limit=12)

    assert len(selected) <= 12
    assert {row.reason for row in diagnostics} <= {"group_exceeds_limit", "budget_full"}
