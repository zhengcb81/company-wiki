"""Pure, deterministic evidence-budget selection for narrative candidates.

A bundle is one atomic event group and costs exactly its span count. Reserved
reasons are placed first, then every page keeps proposing its best remaining
bundle in rounds so page coverage survives a tight cap, while a soft
per-category fair share stops one high-frequency reason class (generic risk or
vague commitment language) from spending the whole budget before industry,
project, product or capacity evidence gets its turn. The planner reads only
the items it is given.

The additive semantic_coverage/1 policy ranks content before page rotation
within the same reason family and keeps plans/mechanisms distinct from generic
events. Its context-length tie-breaker is bounded; the hard cost remains the
actual span count. The default legacy policy stays replayable.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import heapq
from typing import Any, Generic, Literal, TypeVar

from .narrative_semantic_coverage import CoverageSignature, softly_repeats


PayloadT = TypeVar("PayloadT")
OrderKey = tuple[int, ...]
Priority = tuple[int, int, OrderKey, str]
PageKey = tuple[str, int | str]
LEGACY_BUDGET_POLICY = "legacy"
SEMANTIC_BUDGET_POLICY = "semantic_coverage/1"
READING_BUDGET_POLICY = "reading_plan/3"
REPLAY_READING_BUDGET_POLICY = "reading_plan/1"
REPLAY_VALUE_READING_BUDGET_POLICY = "reading_plan/2"

_REASON_PRIORITY = (
    ("downstream_center_certification_timeline", -2),
    ("direct_capacity_constraint", -1),
    ("long_customer_qualification_cycle", -1),
    ("downstream_business_extension", -1),
    ("quantified_market_coverage_target", -1),
    ("named_product_milestone_context", -1),
    ("project_certification_timeline", 0),
    ("project_execution_timeline", 0),
    ("permit_acquired_milestone", 0),
    ("new_product_commercialization_milestone", 0),
    ("applied_operating_milestone", 1),
    ("customer_adoption_milestone", 1),
    ("corporate_development", 1),
    ("concrete_fundraising_project", 2),
    ("incremental_project_capacity", 2),
    ("quantified_industry_outlook", 2),
    ("quantified_industry_change", 2),
    ("business_risk_or_constraint", 1),
    ("specific_project_rationale", 2),
    ("specific_business_event", 3),
    ("quantified_operating_status", 3),
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
    ("project_execution_timeline", "project_timeline"),
    ("named_product_milestone_context", "named_product_milestone"),
    ("new_product_commercialization_milestone", "product_milestone"),
    ("customer_adoption_milestone", "customer_adoption"),
    ("applied_operating_milestone", "operating_milestone"),
    ("corporate_development", "corporate_development"),
    ("concrete_fundraising_project", "fundraising_project"),
    ("incremental_project_capacity", "fundraising_project"),
    ("quantified_industry_outlook", "quantified_industry"),
    ("quantified_industry_change", "quantified_industry"),
    ("business_risk_or_constraint", "risk"),
    ("specific_project_rationale", "rationale"),
    ("specific_business_event", "event"),
    ("quantified_operating_status", "operating_status"),
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
    "customer_adoption",
    "operating_milestone",
    "corporate_development",
    "fundraising_project",
    "quantified_industry",
    "risk",
    "rationale",
    "event",
    "operating_status",
    "positioning",
    "project",
    "industry",
    "other",
)
_SEMANTIC_REASON_CATEGORY = (
    ("specific_operating_constraint", "critical_risk"),
    *((reason, "product_milestone" if category == "named_product_milestone" else category)
      for reason, category in _REASON_CATEGORY[:18]),
    ("project_plan_or_status", "project"),
    ("operating_mechanism", "operating_mechanism"),
    *tuple(row for row in _REASON_CATEGORY[18:] if row[0] != "project_plan_or_status"),
)
_SEMANTIC_CATEGORY_ORDER = (
    *tuple(category for category in CATEGORY_ORDER[:14] if category != "named_product_milestone"),
    "project",
    "operating_mechanism",
    *tuple(category for category in CATEGORY_ORDER[14:] if category != "project"),
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
    evidence_chars: int = 0
    semantic_tokens: tuple[str, ...] = ()
    coverage_signature: CoverageSignature | None = None
    reading_priority: int = 2
    reading_topics: tuple[str, ...] = ()
    required_item_ids: tuple[str, ...] = ()
    is_context_only: bool = False
    value_band: Literal["meaningful_fact", "description"] = "description"


@dataclass(frozen=True)
class _Bundle(Generic[PayloadT]):
    key: str
    items: tuple[BudgetItem[PayloadT], ...]
    page_key: PageKey
    category: str
    priority: Priority
    score: int
    evidence_chars: int
    semantic_strength: int
    quality_band: int
    semantic_tokens: frozenset[str]
    coverage_signature: CoverageSignature | None

    @property
    def cost(self) -> int:
        return len(self.items)


def _reason_value(reasons: frozenset[str], choices: tuple[tuple[str, int], ...]) -> int:
    for reason, value in choices:
        if reason in reasons:
            return value
    return 7


def _category(
    reasons: frozenset[str], policy: str = LEGACY_BUDGET_POLICY
) -> str:
    choices = _SEMANTIC_REASON_CATEGORY if policy == SEMANTIC_BUDGET_POLICY else _REASON_CATEGORY
    for reason, category in choices:
        if reason in reasons:
            return category
    return "other"


def _priority(item: BudgetItem[Any]) -> Priority:
    rank = _reason_value(frozenset(item.reasons), _REASON_PRIORITY)
    if item.is_heading:
        rank += 2
    return (rank, -item.score, item.order_key, item.item_id)


def _make_bundle(
    key: str, items: list[BudgetItem[PayloadT]], policy: str = LEGACY_BUDGET_POLICY
) -> _Bundle[PayloadT]:
    ordered = tuple(sorted(items, key=_priority))
    first = ordered[0]
    categories = {_category(frozenset(item.reasons), policy) for item in ordered}
    category_order = _SEMANTIC_CATEGORY_ORDER if policy == SEMANTIC_BUDGET_POLICY else CATEGORY_ORDER
    category = min(categories, key=category_order.index)
    signature = (first.coverage_signature if all(
        item.coverage_signature == first.coverage_signature for item in ordered) else None)
    return _Bundle(
        key=key,
        items=ordered,
        page_key=first.page_key,
        category=category,
        priority=min(_priority(item) for item in ordered),
        score=max(item.score for item in ordered),
        evidence_chars=sum(item.evidence_chars for item in ordered),
        semantic_strength=_semantic_strength(ordered, category),
        quality_band=_quality_band(ordered, signature),
        semantic_tokens=frozenset(token for item in ordered for token in item.semantic_tokens),
        coverage_signature=signature,
    )


_SPECIFIC_FACT_REASONS = frozenset({
    "specific_operating_constraint", "direct_capacity_constraint",
    "long_customer_qualification_cycle", "quantified_industry_change",
})
_CONCRETE_CONTEXT_REASONS = frozenset({
    "project_certification_timeline", "project_execution_timeline",
    "downstream_center_certification_timeline", "downstream_business_extension",
    "quantified_market_coverage_target", "concrete_fundraising_project",
    "incremental_project_capacity", "quantified_industry_outlook",
    "quantified_operating_status", "customer_adoption_milestone",
    "applied_operating_milestone", "permit_acquired_milestone",
    "corporate_development", "specific_project_rationale",
})
_CONTEXT_REASONS = frozenset({
    "project_plan_or_status", "operating_mechanism",
    "specific_emerging_business_positioning",
})
_PLAN_DIAGNOSTICS = frozenset({
    "planned_or_conditional", "conditional", "prerequisite_or_preparation",
})


def _quality_band(
    items: tuple[BudgetItem[Any], ...], signature: CoverageSignature | None
) -> int:
    """Internal ranking only: source facts outrank same-level category quotas.

    Concrete constraints/industry changes are classified by their source
    owner. A commercial label alone is insufficient: the shared whole-group
    predicate proof must actually be realized. A dated/quantified plan remains
    valuable context, never a realized stage. The planner does not open text
    payloads or invent a second classifier for those source-owned categories.
    """
    reasons = frozenset(reason for item in items for reason in item.reasons)
    signals = signature.stage_signals if signature is not None else ()
    if reasons & _SPECIFIC_FACT_REASONS or any(realized for _, _, realized, _ in signals):
        return 0
    if "new_product_commercialization_milestone" in reasons:
        if reasons & _CONCRETE_CONTEXT_REASONS and any(
            diagnostic in _PLAN_DIAGNOSTICS for _, _, _, diagnostic in signals
        ):
            return 1
        # Unknown/negated stages cannot become realized because an earlier
        # enrichment attached a commercial reason or a large numeric score.
        return 2
    if reasons & _CONCRETE_CONTEXT_REASONS:
        return 1
    return 2 if reasons & _CONTEXT_REASONS else 3


def _semantic_strength(items: tuple[BudgetItem[Any], ...], category: str) -> int:
    if category != "product_milestone":
        return 0
    reasons = frozenset(reason for item in items for reason in item.reasons)
    if "new_product_commercialization_milestone" in reasons:
        return 0 if "quantified_operating_status" in reasons else 1
    return 2  # Name/adjacent context without an asserted operating stage.



def _bundles(
    items: tuple[BudgetItem[PayloadT], ...], policy: str = LEGACY_BUDGET_POLICY
) -> tuple[_Bundle[PayloadT], ...]:
    grouped: dict[str, list[BudgetItem[PayloadT]]] = {}
    for item in items:
        key = f"group:{item.group_id}" if item.group_id is not None else f"item:{item.item_id}"
        grouped.setdefault(key, []).append(item)
    return tuple(_make_bundle(key, values, policy) for key, values in grouped.items())


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
    bundles: tuple[_Bundle[PayloadT], ...], limit: int, *, semantic: bool = False
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
        options.sort(key=(lambda bundle: (bundle.quality_band, bundle.semantic_strength, -bundle.score,
            -min(bundle.evidence_chars, 512), bundle.priority[2:], bundle.key))
            if semantic else _bundle_sort_key)
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
    items: tuple[BudgetItem[PayloadT], ...], limit: int, policy: str = LEGACY_BUDGET_POLICY,
    *, max_chars: int | None = None, max_work_units: int = 2_000_000,
) -> tuple[tuple[BudgetItem[PayloadT], ...], tuple[BudgetDiagnostic, ...]]:
    if policy in {READING_BUDGET_POLICY, REPLAY_READING_BUDGET_POLICY, REPLAY_VALUE_READING_BUDGET_POLICY}:
        return _reading_plan(items, limit, max_chars=max_chars, max_work_units=max_work_units,
                             value_coverage=policy != REPLAY_READING_BUDGET_POLICY,
                             balanced_coverage=policy == READING_BUDGET_POLICY)
    if max_chars is not None or max_work_units != 2_000_000:
        raise ValueError("reading budget limits require a reading_plan policy")
    if policy not in {LEGACY_BUDGET_POLICY, SEMANTIC_BUDGET_POLICY}:
        raise ValueError(f"unknown budget policy: {policy}")
    semantic = policy == SEMANTIC_BUDGET_POLICY
    if semantic and any(type(item.evidence_chars) is not int or item.evidence_chars < 0 for item in items):
        raise ValueError("evidence_chars must be a nonnegative integer")
    if semantic and any(not isinstance(item.semantic_tokens, tuple)
            or len(item.semantic_tokens) > 512
            or any(not isinstance(token, str) or not token for token in item.semantic_tokens)
            for item in items):
        raise ValueError("semantic_tokens must be a bounded tuple of nonempty strings")
    if limit < 1:
        raise ValueError("limit must be positive")
    item_ids = [item.item_id for item in items]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("item_id values must be unique")
    if len(items) <= limit:
        return (tuple(sorted(items, key=_priority)) if semantic else items), ()

    bundles = _bundles(items, policy)
    category_order = _SEMANTIC_CATEGORY_ORDER if semantic else CATEGORY_ORDER
    selected, reserved_keys = _reserve(bundles, limit, semantic=semantic)
    counts: dict[str, int] = {}
    page_visits: dict[tuple[str, PageKey], int] = {}
    for bundle in selected:
        counts[bundle.category] = counts.get(bundle.category, 0) + bundle.cost
        key = (bundle.category, bundle.page_key)
        page_visits[key] = page_visits.get(key, 0) + 1
    spent = sum(bundle.cost for bundle in selected)
    fair_share = _fair_share(limit, {bundle.category for bundle in bundles})

    remaining: dict[PageKey, list[_Bundle[PayloadT]]] = {}
    for bundle in bundles:
        if bundle.key not in reserved_keys:
            remaining.setdefault(bundle.page_key, []).append(bundle)
    for values in remaining.values():
        values.sort(key=lambda bundle: (bundle.priority, bundle.cost, bundle.key))

    def repeats_selected(bundle: _Bundle[PayloadT]) -> bool:
        # The finalizer owns full-group/native-order construction; this pure
        # planner only reads the supplied metadata, never its payload text.
        return any(old.category == bundle.category
            and softly_repeats(bundle.coverage_signature, old.coverage_signature)
            for old in selected)

    def offer_key(page_key: PageKey, bundle: _Bundle[PayloadT]) -> tuple[object, ...]:
        taken = counts.get(bundle.category, 0)
        if semantic:
            # A whole business context competes on content before physical page
            # rotation. The bounded tie-breaker never outranks a higher score
            # or changes the actual number of spans charged to the hard cap.
            return (
                bundle.quality_band,
                _over_share(taken, fair_share),
                category_order.index(bundle.category),
                int(bundle.category == "product_milestone" and bundle.semantic_strength == 2),
                repeats_selected(bundle),
                bundle.semantic_strength,
                -bundle.score,
                -min(bundle.evidence_chars, 512),
                page_visits.get((bundle.category, page_key), 0),
                bundle.priority[2:],
                bundle.key,
                _page_sort_key(page_key),
            )
        return (
            _over_share(taken, fair_share),
            CATEGORY_ORDER.index(bundle.category),
            bundle.priority[0],
            page_visits.get((bundle.category, page_key), 0) if fair_share else 0,
            bundle.priority[1:],
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
                key = (bundle.category, page_key)
                page_visits[key] = page_visits.get(key, 0) + 1
                spent += bundle.cost
            else:
                reason = "group_exceeds_limit" if bundle.cost > limit else "budget_full"
                dropped.append((bundle, reason))
            if fair_share is not None or semantic:
                # Re-offer a busy page immediately: its next category must
                # compete before unrelated pages exhaust the whole budget.
                # Per-category page visits still rotate equally ranked facts.
                offer = best_offer(page_key)
                if offer is not None:
                    pending.append((page_key, offer))

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
    items: tuple[BudgetItem[PayloadT], ...], *, limit: int,
    policy: str = LEGACY_BUDGET_POLICY,
    max_chars: int | None = None, max_work_units: int = 2_000_000,
) -> tuple[BudgetItem[PayloadT], ...]:
    """Select whole context groups within a hard span budget."""
    return plan_budget_items(items, limit=limit, policy=policy,
                             max_chars=max_chars, max_work_units=max_work_units)[0]


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
    used: int | None = None
    requested: int | None = None
    limit: int | None = None
    closure_size: int | None = None


def budget_diagnostics(
    items: tuple[BudgetItem[PayloadT], ...], *, limit: int,
    policy: str = LEGACY_BUDGET_POLICY,
    max_chars: int | None = None, max_work_units: int = 2_000_000,
) -> tuple[BudgetDiagnostic, ...]:
    """Explain every bundle left outside the budget for the same inputs."""
    return plan_budget_items(items, limit=limit, policy=policy,
                             max_chars=max_chars, max_work_units=max_work_units)[1]


def plan_budget_items(
    items: tuple[BudgetItem[PayloadT], ...], *, limit: int,
    policy: str = LEGACY_BUDGET_POLICY,
    max_chars: int | None = None, max_work_units: int = 2_000_000,
) -> tuple[tuple[BudgetItem[PayloadT], ...], tuple[BudgetDiagnostic, ...]]:
    """Return selection and its diagnostics from one deterministic planning pass."""
    return _plan(items, limit, policy, max_chars=max_chars, max_work_units=max_work_units)


def _reading_plan(
    items: tuple[BudgetItem[PayloadT], ...], limit: int, *,
    max_chars: int | None, max_work_units: int, value_coverage: bool = False,
    balanced_coverage: bool = False,
) -> tuple[tuple[BudgetItem[PayloadT], ...], tuple[BudgetDiagnostic, ...]]:
    """Rank caller-owned reading intent and charge unique, closed original IDs.

    Context belongs to the dependency graph, not to an independent value anchor.
    A shared header never unions unrelated projects into one atomic group. Old
    reason reservations and raw payload strings do not influence this policy.
    Work is bounded across indexing, graph expansion and dynamic offers; an
    interrupted closure is never admitted, even when every anchor fits the cap.
    """
    if type(limit) is not int or limit < 1:
        raise ValueError("limit must be a positive integer")
    if max_chars is not None and (type(max_chars) is not int or max_chars < 0):
        raise ValueError("max_chars must be a nonnegative integer")
    if type(max_work_units) is not int or max_work_units < 0:
        raise ValueError("max_work_units must be a nonnegative integer")
    used = 0

    def charge(amount: int = 1) -> bool:
        nonlocal used
        if used + amount > max_work_units:
            return False
        used += amount
        return True

    def diagnostic(members: tuple[BudgetItem[PayloadT], ...], key: str,
                   reason: str, *, used: int | None = None,
                   requested: int | None = None, limit_value: int | None = None,
                   closure_size: int | None = None) -> BudgetDiagnostic:
        first = min(members, key=lambda item: (item.order_key, item.item_id))
        return BudgetDiagnostic(first.item_id, key, first.group_id, "reading",
            len(members), tuple(item.item_id for item in members), first.locator, reason,
            used, requested, limit_value, closure_size)

    def work_stop() -> BudgetDiagnostic:
        # A global limit is not evidence that a specific group was omitted:
        # some of its members may already have entered through another closure.
        return BudgetDiagnostic("", "reading-work", None, "reading", 0, (),
                                "", "work_budget_exhausted")

    # Reserve indexing work before traversing the input. A low work cap reports
    # one global stop instead of allocating an unbounded per-item diagnostic.
    if not charge(2 * len(items)):
        return (), ((work_stop(),) if items else ())
    by_id: dict[str, BudgetItem[PayloadT]] = {}
    grouped: dict[str, list[BudgetItem[PayloadT]]] = {}
    group_for: dict[str, str] = {}
    signature_costs: dict[str, int] = {}
    # The producer already shares frozen CoverageSignature objects for repeated
    # original text. All items keep those objects alive for this call; reference
    # identity can share validation work without merging any original IDs.
    validated_signatures: dict[int, int] = {}
    for item in items:
        if not isinstance(item.item_id, str) or not item.item_id:
            raise ValueError("item_id must be a nonempty string")
        if item.item_id in by_id:
            raise ValueError("item_id values must be unique")
        if (not isinstance(item.order_key, tuple) or len(item.order_key) > 16
                or any(type(value) is not int for value in item.order_key)):
            raise ValueError("order_key must contain integer source coordinates")
        if item.group_id is not None and (not isinstance(item.group_id, str) or not item.group_id):
            raise ValueError("group_id must be a nonempty string or None")
        if type(item.score) is not int:
            raise ValueError("score must be an integer")
        if type(item.reading_priority) is not int or item.reading_priority < 1:
            raise ValueError("reading_priority must be a positive integer")
        if type(item.evidence_chars) is not int or item.evidence_chars < 0:
            raise ValueError("evidence_chars must be a nonnegative integer")
        if type(item.is_context_only) is not bool:
            raise ValueError("is_context_only must be a boolean")
        if value_coverage and (not isinstance(item.value_band, str)
                              or item.value_band not in {"meaningful_fact", "description"}):
            raise ValueError("value_band must be meaningful_fact or description")
        for name, values, bound in (("reading_topics", item.reading_topics, 64),
                                    ("required_item_ids", item.required_item_ids, 4096)):
            if not isinstance(values, tuple) or len(values) > bound:
                raise ValueError(f"{name} must be a bounded tuple of nonempty strings")
            if not charge(len(values)):
                return (), (work_stop(),)
            if any(not isinstance(value, str) or not value for value in values):
                raise ValueError(f"{name} must be a bounded tuple of nonempty strings")
        signature = item.coverage_signature
        signature_costs[item.item_id] = 0
        if signature is not None:
            reference = id(signature)
            if value_coverage and reference in validated_signatures:
                if not charge():
                    return (), (work_stop(),)
                signature_costs[item.item_id] = validated_signatures[reference]
            else:
                if not isinstance(signature, CoverageSignature) or type(signature.complete) is not bool:
                    raise ValueError("coverage_signature must be finite CoverageSignature metadata")
                if (not isinstance(signature.tokens, tuple) or len(signature.tokens) > 512
                        or not isinstance(signature.protected_sentences, tuple)
                        or len(signature.protected_sentences) > 512
                        or not isinstance(signature.stage_signals, tuple) or len(signature.stage_signals) > 512):
                    raise ValueError("coverage_signature sequences must be bounded tuples")
                cost = 1 + len(signature.tokens) + len(signature.protected_sentences) + 4 * len(signature.stage_signals)
                if not charge(cost):
                    return (), (work_stop(),)
                strings = (*signature.tokens, *signature.protected_sentences)
                if any(not isinstance(value, str) or not value for value in strings):
                    raise ValueError("coverage_signature text must be nonempty strings")
                for signal in signature.stage_signals:
                    if (not isinstance(signal, tuple) or len(signal) != 4 or type(signal[2]) is not bool
                            or any(not isinstance(signal[index], str) or not signal[index] for index in (0, 1))
                            or not isinstance(signal[3], str)):
                        raise ValueError("coverage_signature stages must be typed four-tuples")
                if (sum(len(value) for value in strings)
                        + sum(len(signal[0]) + len(signal[1]) + len(signal[3])
                              for signal in signature.stage_signals) > 65536):
                    raise ValueError("coverage_signature text exceeds its finite bound")
                signature_costs[item.item_id] = cost
                if value_coverage:
                    validated_signatures[reference] = cost
        by_id[item.item_id] = item
        key = f"group:{item.group_id}" if item.group_id is not None else f"item:{item.item_id}"
        grouped.setdefault(key, []).append(item)
        group_for[item.item_id] = key

    for group_members in grouped.values():
        group_members.sort(key=lambda item: (item.order_key, item.item_id))

    anchors = {key: tuple(sorted(members, key=lambda item: (item.order_key, item.item_id)))
               for key, members in grouped.items() if any(not item.is_context_only for item in members)}
    closures: dict[str, frozenset[str]] = {}
    dropped: list[BudgetDiagnostic] = []
    stopped = False
    for key, members in sorted(anchors.items(), key=lambda row: (row[1][0].order_key, row[0])):
        if stopped:
            dropped.append(diagnostic(members, key, "work_budget_exhausted"))
            continue
        pending = [item.item_id for item in members]
        visited: set[str] = set()
        reason = None
        while pending:
            if not charge():
                reason, stopped = "work_budget_exhausted", True
                break
            uid = pending.pop()
            if uid in visited:
                continue
            dependency = by_id.get(uid)
            if dependency is None:
                reason = "missing_required_context"
                break
            visited.add(uid)
            siblings = grouped[group_for[uid]]
            if not charge(len(siblings) + len(dependency.required_item_ids)):
                reason, stopped = "work_budget_exhausted", True
                break
            pending.extend(sibling.item_id for sibling in siblings if sibling.item_id not in visited)
            pending.extend(dep for dep in sorted(set(dependency.required_item_ids)) if dep not in visited)
        if reason is not None:
            dropped.append(diagnostic(members, key, reason))
        else:
            closures[key] = frozenset(visited)

    if stopped:
        return (), tuple(sorted((*dropped, work_stop()), key=lambda row: (row.locator, row.bundle_key)))

    # Dynamic ranks have three independent causes: topic visits, repetition,
    # and newly shared original context. Index those causes once. A two-level
    # topic/signature heap changes only the affected offers, rather than
    # scanning every candidate against every previously selected signature.
    selected_ids: set[str] = set()
    topic_visits: dict[str, int] = {}
    unlabelled_selection_visits = 0
    spent_chars = 0
    remaining = set(closures)
    costs = {key: len(ids) for key, ids in closures.items()}
    chars: dict[str, int] = {}
    dependents: dict[str, set[str]] = {}
    signatures: list[CoverageSignature] = []
    signature_weights: list[int] = []
    signature_intern: dict[CoverageSignature, int] = {}
    interned_objects: dict[int, int | None] = {}
    item_signature: dict[str, int] = {}
    guards: dict[tuple[Any, ...], set[int]] = {}
    for uid, item in by_id.items():
        signature = item.coverage_signature
        if item.is_context_only or signature is None:
            continue
        reference = id(signature)
        if value_coverage and reference in interned_objects:
            if not charge():
                return (), tuple((*dropped, work_stop()))
            shared_index = interned_objects[reference]
            if shared_index is not None:
                item_signature[uid] = shared_index
            continue
        # Reserve the membership/insert/lookup operations of this finite tuple
        # interning step. Hashing tuples traverses their members on each lookup;
        # it is not a free replacement for the previous nested comparisons.
        if not charge(3 * signature_costs[uid]):
            return (), tuple((*dropped, work_stop()))
        if not signature.complete or len(frozenset(signature.tokens)) < 12:
            if value_coverage:
                interned_objects[reference] = None
            continue
        if signature not in signature_intern:
            index = len(signatures)
            signature_intern[signature] = index
            signatures.append(signature)
            signature_weights.append(signature_costs[uid])
            guard = (signature.protected_sentences, signature.stage_signals)
            guards.setdefault(guard, set()).add(index)
        item_signature[uid] = signature_intern[signature]
        if value_coverage:
            interned_objects[reference] = item_signature[uid]

    candidate_class: dict[str, int] = {}
    revisions = {key: 0 for key in closures}
    class_ids: dict[tuple[Any, ...], int] = {}
    class_heaps: dict[int, list[tuple[Any, ...]]] = {}
    class_bucket: dict[int, int] = {}
    class_repeated: dict[int, bool] = {}
    class_versions: dict[int, int] = {}
    signature_classes: dict[int, set[int]] = {}
    bucket_ids: dict[tuple[int, int, tuple[str, ...]], int] = {}
    bucket_heaps: dict[int, list[tuple[Any, ...]]] = {}
    bucket_topics: dict[int, tuple[str, ...]] = {}
    bucket_priorities: dict[int, int] = {}
    bucket_values: dict[int, int] = {}
    bucket_versions: dict[int, int] = {}
    topic_buckets: dict[str, set[int]] = {}
    unlabelled_buckets: set[int] = set()
    top_heap: list[tuple[Any, ...]] = []

    for key, ids in closures.items():
        members = anchors[key]
        value_items = tuple(item for item in members if not item.is_context_only)
        if not charge(1 + 2 * len(ids) + len(members) + sum(len(item.reading_topics) for item in value_items)):
            return (), tuple((*dropped, work_stop()))
        chars[key] = sum(by_id[uid].evidence_chars for uid in ids)
        for uid in ids:
            dependents.setdefault(uid, set()).add(key)
        topics = tuple(sorted({topic for item in value_items for topic in item.reading_topics}))
        priority = min(item.reading_priority for item in value_items)
        # Value is an explicit source assessment, never inferred from payload,
        # headings, a topic name or a high numeric score by the budget planner.
        value = (min(0 if item.value_band == "meaningful_fact" else 1 for item in value_items)
                 if value_coverage else 0)
        bucket_key = (value, priority, topics)
        if bucket_key not in bucket_ids:
            bid = len(bucket_ids)
            bucket_ids[bucket_key] = bid
            bucket_heaps[bid] = []
            bucket_topics[bid] = topics
            bucket_priorities[bid] = priority
            bucket_values[bid] = value
            bucket_versions[bid] = 0
            for topic in topics:
                topic_buckets.setdefault(topic, set()).add(bid)
            if balanced_coverage and not topics:
                unlabelled_buckets.add(bid)
        bid = bucket_ids[bucket_key]
        sigs = tuple(sorted({item_signature[item.item_id] for item in value_items if item.item_id in item_signature}))
        class_key = (bid, sigs)
        if class_key not in class_ids:
            cid = len(class_ids)
            class_ids[class_key] = cid
            class_heaps[cid] = []
            class_bucket[cid] = bid
            class_repeated[cid] = False
            class_versions[cid] = 0
            for index in sigs:
                signature_classes.setdefault(index, set()).add(cid)
        cid = class_ids[class_key]
        candidate_class[key] = cid
        first = members[0]
        class_heaps[cid].append((-max(item.score for item in value_items), costs[key],
                                first.order_key, first.item_id, key, 0))

    def heap_work(size: int) -> bool:
        return charge(1 + size.bit_length())

    def class_best(cid: int) -> tuple[Any, ...] | None:
        heap = class_heaps[cid]
        while heap and (heap[0][4] not in remaining or heap[0][5] != revisions[heap[0][4]]):
            if not heap_work(len(heap)):
                return None
            heapq.heappop(heap)
        return heap[0] if heap else None

    def bucket_best(bid: int) -> tuple[Any, ...] | None:
        heap = bucket_heaps[bid]
        while heap and heap[0][-1] != class_versions[heap[0][-2]]:
            if not heap_work(len(heap)):
                return None
            heapq.heappop(heap)
        return heap[0] if heap else None

    def refresh_class(cid: int, dirty: set[int]) -> bool:
        best = class_best(cid)
        # None can mean a real empty heap or a work stop while pruning.
        if best is None and class_heaps[cid]:
            return False
        class_versions[cid] += 1
        bid = class_bucket[cid]
        dirty.add(bid)
        if best is not None:
            if not heap_work(len(bucket_heaps[bid]) + 1):
                return False
            heapq.heappush(bucket_heaps[bid], (class_repeated[cid], *best[:5], cid, class_versions[cid]))
        return True

    def refresh_bucket(bid: int) -> bool:
        best = bucket_best(bid)
        if best is None and bucket_heaps[bid]:
            return False
        bucket_versions[bid] += 1
        if best is not None:
            topics = bucket_topics[bid]
            if not charge(1 + 2 * len(topics)) or not heap_work(len(top_heap) + 1):
                return False
            visits = sum(topic_visits.get(topic, 0) for topic in topics)
            if value_coverage:
                # A missing label is not proof of novelty. Normalize actual
                # topic visits so a richly labelled fact is not punished merely
                # for explaining several operating mechanisms in the same span.
                novelty = int(not topics or all(topic in topic_visits for topic in topics))
                mean_visits = (Fraction(unlabelled_selection_visits, 1)
                               if balanced_coverage and not topics
                               else Fraction(visits, max(1, len(topics))))
                if balanced_coverage:
                    # Among equally valuable, already seen themes, many
                    # high-priority details cannot permanently starve a less
                    # visited theme. Real scope priority still decides equal
                    # visitation; cost, signature work and closure are shared.
                    rank = (bucket_values[bid], novelty, mean_visits,
                            bucket_priorities[bid], best[0], *best[1:6])
                else:
                    rank = (bucket_values[bid], novelty, bucket_priorities[bid],
                            best[0], mean_visits, *best[1:6])
            else:
                rank = (bucket_priorities[bid], int(bool(topics) and all(topic in topic_visits for topic in topics)),
                        best[0], visits, *best[1:6])
            heapq.heappush(top_heap, (rank, bid, bucket_versions[bid]))
        return True

    # Linear heap construction avoids n log n re-insertion for a new document.
    if not charge(2 * (len(closures) + len(class_heaps) + len(bucket_heaps))):
        return (), tuple((*dropped, work_stop()))
    for cid, heap in class_heaps.items():
        heapq.heapify(heap)
        bucket_heaps[class_bucket[cid]].append((False, *heap[0][:5], cid, 0))
    for bid, heap in bucket_heaps.items():
        heapq.heapify(heap)
        if not refresh_bucket(bid):
            return (), tuple((*dropped, work_stop()))

    covered_signatures: set[int] = set()
    repeated_signatures: set[int] = set()
    while remaining and top_heap:
        if not heap_work(len(top_heap)):
            stopped = True
            break
        rank, bid, version = heapq.heappop(top_heap)
        if version != bucket_versions[bid]:
            continue
        key = rank[-1]
        remaining.remove(key)
        cid = candidate_class[key]
        dirty_classes = {cid}
        dirty_buckets: set[int] = set()
        reason = None
        if len(selected_ids) + costs[key] > limit:
            reason = "group_exceeds_limit" if len(closures[key]) > limit else "budget_full"
        elif max_chars is not None and spent_chars + chars[key] > max_chars:
            reason = "character_budget"
        if reason is not None:
            is_character_budget = reason == "character_budget"
            dropped.append(diagnostic(anchors[key], key, reason,
                used=spent_chars if is_character_budget else len(selected_ids),
                requested=chars[key] if is_character_budget else costs[key],
                limit_value=max_chars if is_character_budget else limit,
                closure_size=len(closures[key])))
        else:
            # Only an accepted offer expands its actual original set again.
            # Every accepted package is complete even if later index updates
            # consume the remaining work budget.
            if not charge(len(closures[key])):
                remaining.add(key)
                stopped = True
                break
            added = closures[key] - selected_ids
            if not charge(sum(1 + len(by_id[uid].reading_topics) for uid in added)):
                remaining.add(key)
                stopped = True
                break
            selected_ids.update(added)
            spent_chars += chars[key]
            changed_topics: set[str] = set()
            new_signatures: set[int] = set()
            for uid in sorted(added):
                item = by_id[uid]
                if not item.is_context_only:
                    for topic in set(item.reading_topics):
                        topic_visits[topic] = topic_visits.get(topic, 0) + 1
                        changed_topics.add(topic)
                    if uid in item_signature and item_signature[uid] not in covered_signatures:
                        new_signatures.add(item_signature[uid])
                if not charge(len(dependents[uid])):
                    stopped = True
                    break
                for other_key in dependents[uid]:
                    if other_key not in remaining:
                        continue
                    costs[other_key] -= 1
                    chars[other_key] -= item.evidence_chars
                    other_cid = candidate_class[other_key]
                    dirty_classes.add(other_cid)
                    if costs[other_key] == 0:
                        remaining.remove(other_key)
                    else:
                        revisions[other_key] += 1
                        first = anchors[other_key][0]
                        value_items = tuple(row for row in anchors[other_key] if not row.is_context_only)
                        if not charge(len(value_items)) or not heap_work(len(class_heaps[other_cid]) + 1):
                            stopped = True
                            break
                        heapq.heappush(class_heaps[other_cid], (-max(row.score for row in value_items), costs[other_key],
                            first.order_key, first.item_id, other_key, revisions[other_key]))
                if stopped:
                    break
            if stopped:
                break
            # Once the hard span cap is full, no positive-cost closure can fit.
            # Diagnose the rest without doing another repetition/ranking pass.
            if len(selected_ids) == limit:
                dropped.extend(diagnostic(anchors[other], other, "group_exceeds_limit"
                    if len(closures[other]) > limit else "budget_full",
                    used=len(selected_ids), requested=costs[other], limit_value=limit,
                    closure_size=len(closures[other])) for other in remaining)
                break
            if balanced_coverage and not bucket_topics[bid]:
                # Missing labels are not proof that every subsequent table or
                # operating fact is a new theme. Count the accepted value bundle
                # once, while all of its original rows still pay their real
                # span/character costs. Only this finite index needs re-ranking.
                unlabelled_selection_visits += 1
                if not charge(len(unlabelled_buckets)):
                    stopped = True
                    break
                dirty_buckets.update(unlabelled_buckets)
            for topic in changed_topics:
                if not charge(len(topic_buckets[topic])):
                    stopped = True
                    break
                dirty_buckets.update(topic_buckets[topic])
            if stopped:
                break
            for index in sorted(new_signatures):
                covered_signatures.add(index)
                signature = signatures[index]
                guard = (signature.protected_sentences, signature.stage_signals)
                if not charge(1 + len(signature.protected_sentences) + 4 * len(signature.stage_signals)):
                    stopped = True
                    break
                for other_index in sorted(guards[guard]):
                    if not charge():
                        stopped = True
                        break
                    if other_index in repeated_signatures:
                        continue
                    if not charge(1 + signature_weights[index] + signature_weights[other_index]):
                        stopped = True
                        break
                    if softly_repeats(signatures[other_index], signature):
                        repeated_signatures.add(other_index)
                        if not charge(len(signature_classes.get(other_index, ()))):
                            stopped = True
                            break
                        for other_cid in signature_classes.get(other_index, ()):
                            class_repeated[other_cid] = True
                            dirty_classes.add(other_cid)
                if stopped:
                    break
            if stopped:
                break
        for other_cid in sorted(dirty_classes):
            if not refresh_class(other_cid, dirty_buckets):
                stopped = True
                break
        if stopped:
            break
        for other_bid in sorted(dirty_buckets):
            if not refresh_bucket(other_bid):
                stopped = True
                break
        if stopped:
            break
    if stopped:
        dropped.append(work_stop())
    selected = tuple(sorted((by_id[uid] for uid in selected_ids),
                            key=lambda item: (item.order_key, item.item_id)))
    return selected, tuple(sorted(dropped, key=lambda row: (row.locator, row.bundle_key)))


__all__ = [
    "BudgetDiagnostic",
    "BudgetItem",
    "CATEGORY_ORDER",
    "LEGACY_BUDGET_POLICY",
    "SEMANTIC_BUDGET_POLICY",
    "READING_BUDGET_POLICY",
    "REPLAY_READING_BUDGET_POLICY",
    "REPLAY_VALUE_READING_BUDGET_POLICY",
    "budget_diagnostics",
    "select_budget_items",
    "plan_budget_items",
]
