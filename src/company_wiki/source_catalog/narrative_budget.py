"""Pure, atomic evidence-budget selection for narrative candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar


PayloadT = TypeVar("PayloadT")
Priority = tuple[int, int, tuple[int | str, ...], str]
PageKey = tuple[str, str]

_REASON_PRIORITY = (
    ("downstream_center_certification_timeline", -2),
    ("direct_capacity_constraint", -1),
    ("long_customer_qualification_cycle", -1),
    ("downstream_business_extension", -1),
    ("quantified_market_coverage_target", -1),
    ("named_product_milestone_context", -1),
    ("project_certification_timeline", 0),
    ("permit_acquired_milestone", 0),
    ("new_product_commercialization_milestone", 0),
    ("business_risk_or_constraint", 1),
    ("specific_project_rationale", 2),
    ("specific_business_event", 3),
    ("specific_emerging_business_positioning", 4),
    ("project_plan_or_status", 5),
    ("current_industry_context", 6),
)
_REASON_CATEGORY = (
    ("direct_capacity_constraint", "critical_risk"),
    ("long_customer_qualification_cycle", "critical_risk"),
    ("downstream_business_extension", "business_extension"),
    ("quantified_market_coverage_target", "market_coverage_target"),
    ("permit_acquired_milestone", "milestone"),
    ("project_certification_timeline", "project_timeline"),
    ("named_product_milestone_context", "named_product_milestone"),
    ("new_product_commercialization_milestone", "product_milestone"),
    ("business_risk_or_constraint", "risk"),
    ("specific_project_rationale", "rationale"),
    ("specific_business_event", "event"),
    ("specific_emerging_business_positioning", "positioning"),
    ("project_plan_or_status", "project"),
    ("current_industry_context", "industry"),
)
CATEGORY_ORDER = (
    "critical_risk",
    "business_extension",
    "market_coverage_target",
    "milestone",
    "project_timeline",
    "named_product_milestone",
    "product_milestone",
    "risk",
    "rationale",
    "event",
    "positioning",
    "project",
    "industry",
    "other",
)
_RESERVED_REASONS = (
    "downstream_center_certification_timeline",
    "downstream_business_extension",
)


@dataclass(frozen=True)
class BudgetItem(Generic[PayloadT]):
    """One emitted span candidate plus the fields used by budget policy."""

    item_id: str
    group_id: str | None
    page_key: PageKey
    locator: tuple[int | str, ...]
    reasons: tuple[str, ...]
    score: int
    is_heading: bool
    payload: PayloadT


@dataclass(frozen=True)
class _Bundle(Generic[PayloadT]):
    key: str
    items: tuple[BudgetItem[PayloadT], ...]
    page_key: PageKey
    category: str
    priority: Priority
    score: int

    @property
    def cost(self) -> int:
        return len(self.items)


def _reason_value(reasons: frozenset[str], choices: tuple[tuple[str, int], ...]) -> int:
    for reason, value in choices:
        if reason in reasons:
            return value
    return 7


def _category(reasons: frozenset[str]) -> str:
    for reason, category in _REASON_CATEGORY:
        if reason in reasons:
            return category
    return "other"


def _priority(item: BudgetItem[Any]) -> Priority:
    rank = _reason_value(frozenset(item.reasons), _REASON_PRIORITY)
    if item.is_heading:
        rank += 2
    return (rank, -item.score, item.locator, item.item_id)


def _make_bundle(
    key: str, items: list[BudgetItem[PayloadT]]
) -> _Bundle[PayloadT]:
    ordered = tuple(sorted(items, key=_priority))
    first = ordered[0]
    categories = {_category(frozenset(item.reasons)) for item in ordered}
    category = min(categories, key=CATEGORY_ORDER.index)
    return _Bundle(
        key=key,
        items=ordered,
        page_key=first.page_key,
        category=category,
        priority=min(_priority(item) for item in ordered),
        score=max(item.score for item in ordered),
    )


def _bundles(items: tuple[BudgetItem[PayloadT], ...]) -> tuple[_Bundle[PayloadT], ...]:
    grouped: dict[str, list[BudgetItem[PayloadT]]] = {}
    for item in items:
        key = item.group_id or f"item:{item.item_id}"
        grouped.setdefault(key, []).append(item)
    return tuple(_make_bundle(key, values) for key, values in grouped.items())


def _bundle_sort_key(bundle: _Bundle[Any]) -> tuple[object, ...]:
    first = bundle.items[0]
    return (
        bundle.priority[0],
        -bundle.score,
        first.locator,
        first.item_id,
        bundle.key,
    )


def _reserve(
    bundles: tuple[_Bundle[PayloadT], ...], limit: int
) -> tuple[list[_Bundle[PayloadT]], set[str]]:
    reserved: list[_Bundle[PayloadT]] = []
    keys: set[str] = set()
    for reason in _RESERVED_REASONS:
        options = [
            bundle
            for bundle in bundles
            if bundle.key not in keys
            and any(reason in item.reasons for item in bundle.items)
        ]
        options.sort(key=_bundle_sort_key)
        if options and sum(bundle.cost for bundle in reserved) + options[0].cost <= limit:
            reserved.append(options[0])
            keys.add(options[0].key)
    return reserved, keys


def _page_order(by_page: dict[PageKey, list[_Bundle[PayloadT]]]) -> tuple[PageKey, ...]:
    return tuple(sorted(
        by_page,
        key=lambda key: (
            min(CATEGORY_ORDER.index(bundle.category) for bundle in by_page[key]),
            -max(bundle.score for bundle in by_page[key]),
            0 if key[0] == "page" else 1,
            key[1],
        ),
    ))


def _page_queue(bundles: list[_Bundle[PayloadT]]) -> list[_Bundle[PayloadT]]:
    buckets: dict[str, list[_Bundle[PayloadT]]] = {name: [] for name in CATEGORY_ORDER}
    for bundle in bundles:
        buckets[bundle.category].append(bundle)
    for values in buckets.values():
        values.sort(key=lambda item: (item.priority, item.cost, item.key))
    staged = [values[0] for values in buckets.values() if values]
    staged_keys = {bundle.key for bundle in staged}
    remainder = [bundle for bundle in bundles if bundle.key not in staged_keys]
    remainder.sort(
        key=lambda item: (
            CATEGORY_ORDER.index(item.category), item.priority, item.cost, item.key
        )
    )
    return [*staged, *remainder]


def _remaining_by_page(
    bundles: tuple[_Bundle[PayloadT], ...], reserved_keys: set[str]
) -> dict[PageKey, list[_Bundle[PayloadT]]]:
    by_page: dict[PageKey, list[_Bundle[PayloadT]]] = {}
    for bundle in bundles:
        if bundle.key not in reserved_keys:
            by_page.setdefault(bundle.page_key, []).append(bundle)
    return {key: _page_queue(values) for key, values in by_page.items()}


def _fill_round_robin(
    selected: list[_Bundle[PayloadT]],
    by_page: dict[PageKey, list[_Bundle[PayloadT]]],
    limit: int,
) -> None:
    if not by_page:
        return
    for rank in range(max(len(items) for items in by_page.values())):
        for page_key in _page_order(by_page):
            page_items = by_page[page_key]
            if rank < len(page_items) and sum(item.cost for item in selected) + page_items[rank].cost <= limit:
                selected.append(page_items[rank])


def select_budget_items(
    items: tuple[BudgetItem[PayloadT], ...], *, limit: int
) -> tuple[BudgetItem[PayloadT], ...]:
    """Select whole context groups within a hard span budget."""
    if limit < 1:
        raise ValueError("limit must be positive")
    item_ids = [item.item_id for item in items]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("item_id values must be unique")
    if len(items) <= limit:
        return items
    bundles = _bundles(items)
    selected, reserved_keys = _reserve(bundles, limit)
    by_page = _remaining_by_page(bundles, reserved_keys)
    _fill_round_robin(selected, by_page, limit)
    return tuple(item for bundle in selected for item in bundle.items)


__all__ = ["BudgetItem", "CATEGORY_ORDER", "select_budget_items"]
