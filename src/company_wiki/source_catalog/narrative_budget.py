"""Pure, deterministic evidence-budget selection for narrative candidates.

A bundle is one atomic event group and costs exactly its span count. Reserved
reasons are placed first, then every page keeps proposing its best remaining
bundle in rounds so page coverage survives a tight cap, while a soft
per-category fair share stops one high-frequency reason class (generic risk or
vague commitment language) from spending the whole budget before industry,
project, product or capacity evidence gets its turn. The planner reads only
the items it is given.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar


PayloadT = TypeVar("PayloadT")
OrderKey = tuple[int, ...]
Priority = tuple[int, int, OrderKey, str]
PageKey = tuple[str, int | str]

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
    locator: str
    order_key: OrderKey
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
    return (rank, -item.score, item.order_key, item.item_id)


def _make_bundle(key: str, items: list[BudgetItem[PayloadT]]) -> _Bundle[PayloadT]:
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
        first.order_key,
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
        if (
            options
            and sum(bundle.cost for bundle in reserved) + options[0].cost <= limit
        ):
            reserved.append(options[0])
            keys.add(options[0].key)
    return reserved, keys


def _page_sort_key(key: PageKey) -> tuple[int, int, str]:
    if key[0] == "page" and isinstance(key[1], int):
        return (0, key[1], "")
    return (1, 0, str(key[1]))


def _fair_share(limit: int, categories: set[str]) -> int | None:
    """Span budget one category may claim, or ``None`` when it must not bind.

    The soft quota only exists while the cap can still leave every active
    category two shares of the budget; tighter budgets keep the historical
    priority order plus page rotation untouched.
    """
    if limit < 2 * len(categories):
        return None
    return max(1, -(-limit // len(categories)))


def _over_share(taken: int, fair_share: int | None) -> bool:
    return fair_share is not None and taken >= fair_share


def _plan(
    items: tuple[BudgetItem[PayloadT], ...], limit: int
) -> tuple[tuple[BudgetItem[PayloadT], ...], tuple[BudgetDiagnostic, ...]]:
    if limit < 1:
        raise ValueError("limit must be positive")
    item_ids = [item.item_id for item in items]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("item_id values must be unique")
    if len(items) <= limit:
        return items, ()

    bundles = _bundles(items)
    selected, reserved_keys = _reserve(bundles, limit)
    counts: dict[str, int] = {}
    for bundle in selected:
        counts[bundle.category] = counts.get(bundle.category, 0) + bundle.cost
    spent = sum(bundle.cost for bundle in selected)
    fair_share = _fair_share(limit, {bundle.category for bundle in bundles})

    remaining: dict[PageKey, list[_Bundle[PayloadT]]] = {}
    for bundle in bundles:
        if bundle.key not in reserved_keys:
            remaining.setdefault(bundle.page_key, []).append(bundle)
    for values in remaining.values():
        values.sort(key=lambda bundle: (bundle.priority, bundle.cost, bundle.key))

    def offer_key(page_key: PageKey, bundle: _Bundle[PayloadT]) -> tuple[object, ...]:
        taken = counts.get(bundle.category, 0)
        return (
            _over_share(taken, fair_share),
            CATEGORY_ORDER.index(bundle.category),
            bundle.priority,
            -bundle.cost,
            bundle.key,
            _page_sort_key(page_key),
        )

    def best_offer(page_key: PageKey) -> _Bundle[PayloadT] | None:
        values = remaining[page_key]
        if not values:
            return None
        return min(values, key=lambda bundle: offer_key(page_key, bundle))

    dropped: list[tuple[_Bundle[PayloadT], str]] = []
    ranks = max((len(values) for values in remaining.values()), default=0)
    for _rank in range(ranks):
        pending: list[tuple[PageKey, _Bundle[PayloadT]]] = []
        for page_key in remaining:
            offer = best_offer(page_key)
            if offer is not None:
                pending.append((page_key, offer))
        while pending:
            pending.sort(key=lambda pair: offer_key(pair[0], pair[1]))
            page_key, bundle = pending.pop(0)
            remaining[page_key].remove(bundle)
            if spent + bundle.cost <= limit:
                selected.append(bundle)
                counts[bundle.category] = counts.get(bundle.category, 0) + bundle.cost
                spent += bundle.cost
            else:
                reason = "group_exceeds_limit" if bundle.cost > limit else "budget_full"
                dropped.append((bundle, reason))

    diagnostics = tuple(
        BudgetDiagnostic(
            item_id=bundle.items[0].item_id,
            bundle_key=bundle.key,
            group_id=bundle.items[0].group_id,
            category=bundle.category,
            item_count=bundle.cost,
            item_ids=tuple(item.item_id for item in bundle.items),
            locator=bundle.items[0].locator,
            reason=reason,
        )
        for bundle, reason in sorted(
            dropped, key=lambda row: (row[0].items[0].locator, row[0].key)
        )
    )
    return tuple(item for bundle in selected for item in bundle.items), diagnostics


def select_budget_items(
    items: tuple[BudgetItem[PayloadT], ...], *, limit: int
) -> tuple[BudgetItem[PayloadT], ...]:
    """Select whole context groups within a hard span budget."""
    return _plan(items, limit)[0]


@dataclass(frozen=True)
class BudgetDiagnostic:
    """Why one context group did not enter the selected package."""

    item_id: str
    bundle_key: str
    group_id: str | None
    category: str
    item_count: int
    item_ids: tuple[str, ...]
    locator: str
    reason: str


def budget_diagnostics(
    items: tuple[BudgetItem[PayloadT], ...], *, limit: int
) -> tuple[BudgetDiagnostic, ...]:
    """Explain every bundle left outside the budget for the same inputs."""
    return _plan(items, limit)[1]


__all__ = [
    "BudgetDiagnostic",
    "BudgetItem",
    "CATEGORY_ORDER",
    "budget_diagnostics",
    "select_budget_items",
]
