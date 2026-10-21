"""Plan and admission for one parse round: fair reservations, hard balance.

Semantics frozen by INTERFACES.md / construction_card.md:

* ``plan_geometry_requests`` turns a compiled ``du-geometry-policy/1`` and
  ROOT-bound windows into finite per-section reservations. Demand classes get
  fair shares of the tighter page/request capacity with plan-time borrowing and a global
  hard balance (sum of class quotas never exceeds the limit). Reservations are
  atomic: an exhausted :class:`WorkBudget` yields a partial plan with no
  allocation rows ("not done stays unknown") instead of fabricated claims.
* ``admit_geometry_request`` admits actual page observations: only
  ``observed_candidate`` requests heavy discover/fine work; ``absent`` never
  consumes budget and ``unknown`` never claims no-table. The caller's
  ``remaining`` is an extra gate only — the state's counters, not the caller,
  bound the run, so re-passing a fresh remaining value cannot reset the limit.
* Same-page acknowledgements deduplicate per ``(scope_id, page)`` once; parent
  scopes never share that ledger. Reasons stay separate: exhausted / cancelled
  / not_arrived (summary) / not_found / unknown / deduplicated / rejected.
* No heading re-interpretation, no ``_match_rule``, no role merging, no
  printed-page-offset guessing, no evidence or body locators, no IO, no
  threads, no persistence: the state is an in-call JSON-compatible value.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from itertools import islice
from typing import Any

from company_wiki.document_understanding.layout_hints.contract import (
    WorkBudget,
    WorkBudgetExceeded,
)

from .contracts import (
    DEMAND_CLASSES,
    DEMAND_VALUES,
    DISCOVER_VALUES,
    EVIDENCE_VALUES,
    FINE_VALUES,
    MAX_STRING,
    MAX_WINDOW_KEYS_PER_ADMISSION,
    NAVIGATION_VALUES,
    RUN_REASONS,
    SCHEMA_ADMISSION,
    SCHEMA_PLAN,
    SCHEMA_POLICY,
    SCHEMA_RUN_SUMMARY,
    SCHEMA_STATE,
    DiagnosticSink,
    bounded_text,
    canonical_digest,
    insert_interval,
    is_int,
    interval_length,
    require_nonnegative_int,
    subtract_intervals,
)


def _canonical_window_key(window: Mapping[str, Any]) -> tuple[str, int, str]:
    """Canonical order: parent scope, then physical position, then key."""
    return (window["scope_id"], window["physical_start"], window["window_key"])


def _limits_out(limits: Mapping[str, Any]) -> dict[str, int]:
    # Only the two planner bounds are part of this contract; caller extras are
    # deliberately not echoed so the plan stays canonical.
    return {
        "max_pages": require_nonnegative_int(limits.get("max_pages"), "limits.max_pages"),
        "max_requests": require_nonnegative_int(limits.get("max_requests"), "limits.max_requests"),
    }


def _profile_identity(policy: Mapping[str, Any]) -> tuple[str, str]:
    profile_id = policy.get("profile_id")
    profile_version = policy.get("profile_version")
    return (
        profile_id if isinstance(profile_id, str) and profile_id else "unknown",
        profile_version if isinstance(profile_version, str) and profile_version else "unknown",
    )


# --- policy consumption -----------------------------------------------------

def _intent_value(
    intent: Mapping[str, Any],
    field: str,
    allowed: frozenset[str],
    rule_key: str,
    sink: DiagnosticSink,
) -> str:
    """Resolve one intent field conservatively.

    ``default_intent`` is deliberately NOT consulted: INTERFACES freezes
    missing fields as conservative ``unknown``, so a rule omitting a field can
    never silently inherit heavy-request capability from a policy default.
    Present-but-invalid values are likewise unknown, with a diagnostic.
    """
    if field not in intent or intent[field] is None:
        sink.add(
            "POLICY_INTENT_MISSING",
            f"{rule_key}.{field} absent; conservative unknown per interface",
            [rule_key],
        )
        return "unknown"
    value = intent[field]
    if isinstance(value, str) and value in allowed:
        return value
    sink.add(
        "POLICY_INTENT_INVALID",
        f"{rule_key}.{field} not in enum; conservative unknown",
        [rule_key],
    )
    return "unknown"


def _reading_priority(rule: Mapping[str, Any], rule_key: str, sink: DiagnosticSink) -> int:
    value = rule.get("reading_priority")
    if is_int(value) and value in (1, 2, 3):
        return value
    if value is not None:
        sink.add("POLICY_PRIORITY_INVALID", f"{rule_key}.reading_priority not 1..3; using 3", [rule_key])
    return 3


def _parse_rules(
    policy: Mapping[str, Any], sink: DiagnosticSink, budget: WorkBudget
) -> tuple[dict[str, dict[str, Any]], str, str]:
    raw_rules = policy.get("rules", ())
    if isinstance(raw_rules, (str, bytes)) or not isinstance(raw_rules, Sequence):
        raise ValueError("policy.rules must be a sequence")
    rules: dict[str, dict[str, Any]] = {}
    for rule in raw_rules:
        budget.charge()
        if not isinstance(rule, Mapping):
            raise ValueError("each policy rule must be a mapping")
        rule_key = bounded_text(rule.get("rule_key"))
        if rule_key is None:
            raise ValueError("each policy rule needs a bounded non-empty rule_key")
        if rule_key in rules:
            raise ValueError(f"duplicate rule_key in policy: {rule_key!r}")
        intent = rule.get("geometry_intent")
        if not isinstance(intent, Mapping):
            intent = {}
        rules[rule_key] = {
            "demand_class": _intent_value(intent, "demand_class", DEMAND_VALUES, rule_key, sink),
            "discover": _intent_value(intent, "discover", DISCOVER_VALUES, rule_key, sink),
            "fine": _intent_value(intent, "fine", FINE_VALUES, rule_key, sink),
            "reading_priority": _reading_priority(rule, rule_key, sink),
        }
    profile_id, profile_version = _profile_identity(policy)
    return rules, profile_id, profile_version


# --- window validation ------------------------------------------------------

def _parse_navigation(window_key: str, raw: Mapping[str, Any], sink: DiagnosticSink) -> str:
    nav = raw.get("navigation_status")
    if not isinstance(nav, str) or len(nav) > 64 or nav not in NAVIGATION_VALUES:
        sink.add("WINDOW_NAVIGATION_INVALID", f"navigation_status {nav!r} -> unknown", [window_key])
        return "unknown"
    if nav == "conflict":
        sink.add(
            "WINDOW_NAVIGATION_CONFLICT",
            "native destination conflict kept as diagnostic; no printed-page offset guessed",
            [window_key],
        )
    elif nav == "unknown":
        sink.add(
            "WINDOW_NAVIGATION_UNKNOWN",
            "native destination unknown kept as diagnostic",
            [window_key],
        )
    return nav


def _validate_windows(
    windows: Sequence[Any],
    rules: Mapping[str, Mapping[str, Any]],
    page_count: int,
    sink: DiagnosticSink,
    budget: WorkBudget,
) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for raw in windows:
        budget.charge()
        if not isinstance(raw, Mapping):
            raise ValueError("each window must be a mapping")
        window_key = bounded_text(raw.get("window_key"))
        scope_id = bounded_text(raw.get("scope_id"))
        rule_key = bounded_text(raw.get("rule_key"))
        if window_key is None or scope_id is None or rule_key is None:
            sink.add(
                "WINDOW_INVALID_FIELD",
                "window_key/scope_id/rule_key missing, untrimmed or overlong",
                [value for value in (window_key, scope_id) if value is not None][:2],
            )
            continue
        start = raw.get("physical_start")
        end = raw.get("physical_end")
        if not is_int(start) or not is_int(end):
            sink.add(
                "WINDOW_BAD_PAGE_VALUE",
                f"physical_start/end must be real ints, got {type(start).__name__}/{type(end).__name__}",
                [window_key],
            )
            continue
        if start > end:
            sink.add("WINDOW_INVALID_SPAN", f"{start}..{end} start after end", [window_key])
            continue
        navigation_status = _parse_navigation(window_key, raw, sink)
        bounded_start, bounded_end = max(1, start), min(page_count, end)
        if (bounded_start, bounded_end) != (start, end):
            sink.add(
                "WINDOW_CLAMPED",
                f"{start}..{end} bounded to {bounded_start}..{bounded_end} by page_count",
                [window_key],
            )
        if bounded_start > bounded_end:
            sink.add(
                "WINDOW_OUT_OF_RANGE",
                f"{start}..{end} outside 1..{page_count}; nothing to request",
                [window_key],
            )
            continue
        rule = rules.get(rule_key)
        if rule is None:
            sink.add(
                "WINDOW_UNKNOWN_RULE",
                f"rule_key {rule_key} not in policy; conservative unknown intent",
                [window_key],
            )
            demand_class, priority = "unknown", 3
            requestable = {"discover": False, "fine": False}
        else:
            demand_class = rule["demand_class"]
            priority = rule["reading_priority"]
            requestable = {
                "discover": rule["discover"] == "on_tabular_evidence",
                # priority-1 administrative sections never auto-trigger fine work.
                "fine": rule["fine"] == "on_candidate" and demand_class != "administrative",
            }
        valid.append(
            {
                "window_key": window_key,
                "scope_id": scope_id,
                "rule_key": rule_key,
                "physical_start": bounded_start,
                "physical_end": bounded_end,
                "navigation_status": navigation_status,
                "demand_class": demand_class,
                "reading_priority": priority,
                "requestable": requestable,
                "consumable": requestable["discover"] or requestable["fine"],
            }
        )
    return valid


def _canonicalize(
    valid: list[dict[str, Any]], sink: DiagnosticSink, budget: WorkBudget
) -> list[dict[str, Any]]:
    if not valid:
        return []
    budget.charge(1 + len(valid))
    canonical = sorted(valid, key=_canonical_window_key)
    if [row["window_key"] for row in canonical] != [row["window_key"] for row in valid]:
        sink.add(
            "WINDOW_INPUT_OUT_OF_ORDER",
            "input windows differ from canonical (scope_id, physical_start, window_key) order; plan stays canonical",
        )
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in canonical:
        groups.setdefault(row["window_key"], []).append(row)
    survivors: list[dict[str, Any]] = []
    for window_key in sorted(groups):
        group = groups[window_key]
        survivor = min(
            group,
            key=lambda row: (
                row["scope_id"],
                row["physical_start"],
                row["physical_end"],
                row["rule_key"],
                row["navigation_status"],
                row["demand_class"],
            ),
        )
        for _ in range(len(group) - 1):
            sink.add(
                "WINDOW_DUPLICATE_KEY",
                "duplicate window_key; canonical-first survivor kept, duplicate dropped",
                [window_key],
            )
        survivors.append(survivor)
    survivors.sort(key=_canonical_window_key)
    return survivors


# --- quota computation ------------------------------------------------------

def _class_desired(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, int]]:
    """Union page demand per demand class; parent scopes never merge."""
    by_scope: dict[tuple[str, str], list[tuple[int, int]]] = {}
    priority: dict[str, int] = {}
    for row in rows:
        by_scope.setdefault((row["demand_class"], row["scope_id"]), []).append(
            (row["physical_start"], row["physical_end"])
        )
        current = priority.get(row["demand_class"])
        priority[row["demand_class"]] = (
            row["reading_priority"] if current is None else min(current, row["reading_priority"])
        )
    desired = {cls: 0 for cls in priority}
    for (cls, _scope), intervals in by_scope.items():
        desired[cls] += interval_length(intervals)
    return desired, priority


def _fair_quotas(
    consumable_classes: list[str],
    desired: dict[str, int],
    min_priority: dict[str, int],
    max_pages: int,
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Equal shares with plan-time borrowing; sum never exceeds max_pages."""
    count = len(consumable_classes)
    base = max_pages // count if count else 0
    remainder = max_pages - base * count
    held = {
        cls: base + (1 if index < remainder else 0)
        for index, cls in enumerate(consumable_classes)
    }
    surplus = sum(max(0, held[cls] - desired[cls]) for cls in consumable_classes)
    borrowed = {cls: 0 for cls in consumable_classes}
    # Borrow order is frozen by the hand calculation: urgent reading priority
    # first, then the stable demand-class name (never input order).
    over_demanded = sorted(
        (cls for cls in consumable_classes if desired[cls] > held[cls]),
        key=lambda cls: (min_priority[cls], cls),
    )
    for cls in over_demanded:
        gift = min(desired[cls] - held[cls], surplus)
        borrowed[cls] = gift
        surplus -= gift
    quotas = {cls: min(desired[cls], held[cls] + borrowed[cls]) for cls in consumable_classes}
    return quotas, held, borrowed


def _exclusive_pages(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Pages each window alone contributes (canonical order inside a class)."""
    covered: dict[str, list[tuple[int, int]]] = {}
    exclusive: dict[str, int] = {}
    for row in rows:
        scope = row["scope_id"]
        merged = covered.setdefault(scope, [])
        base = (row["physical_start"], row["physical_end"])
        pieces = subtract_intervals(base, merged)
        exclusive[row["window_key"]] = interval_length(pieces)
        insert_interval(merged, base)
    return exclusive


def _apportion_windows(
    rows: list[dict[str, Any]],
    class_quota: int,
    desired_total: int,
    exclusive: dict[str, int],
) -> dict[str, int]:
    """Split a class quota by exclusive pages (largest remainder, canonical ties).

    A window fully nested inside earlier canonical windows has zero exclusive
    pages and stays transparent: its reservation already lives under the
    covering windows, so it keeps status reserved with quota 0.
    """
    if class_quota <= 0:
        return {row["window_key"]: 0 for row in rows}
    if class_quota >= desired_total:
        return {row["window_key"]: exclusive[row["window_key"]] for row in rows}
    numerators = [class_quota * exclusive[row["window_key"]] for row in rows]
    floors = [value // desired_total for value in numerators]
    remainders = [value % desired_total for value in numerators]
    awards = class_quota - sum(floors)
    by_remainder = sorted(range(len(rows)), key=lambda index: (-remainders[index], index))
    extra = set(by_remainder[:awards])
    return {
        row["window_key"]: floors[index] + (1 if index in extra else 0)
        for index, row in enumerate(rows)
    }


# --- plan assembly ----------------------------------------------------------

def _plan_core(plan_or_parts: Mapping[str, Any]) -> dict[str, Any]:
    """Digest identity of everything admission decisions depend on."""
    summary = plan_or_parts["summary"]
    return {
        "schema_version": SCHEMA_PLAN,
        "profile_id": plan_or_parts["profile_id"],
        "profile_version": plan_or_parts["profile_version"],
        "page_count": plan_or_parts["page_count"],
        "limits": plan_or_parts["limits"],
        "class_quotas": plan_or_parts["class_quotas"],
        "allocations": plan_or_parts["allocations"],
        "partial": summary["partial"],
        "partial_reason": summary["partial_reason"],
        "windows_unplanned": summary["windows_unplanned"],
    }


def _build_plan(
    profile_id: str,
    profile_version: str,
    page_count: int,
    limits: dict[str, int],
    class_quotas: dict[str, dict[str, Any]],
    allocations: list[dict[str, Any]],
    summary: dict[str, Any],
    sink: DiagnosticSink,
) -> dict[str, Any]:
    core = _plan_core(
        {
            "profile_id": profile_id,
            "profile_version": profile_version,
            "page_count": page_count,
            "limits": limits,
            "class_quotas": class_quotas,
            "allocations": allocations,
            "summary": summary,
        }
    )
    return {
        "schema_version": SCHEMA_PLAN,
        "profile_id": profile_id,
        "profile_version": profile_version,
        "page_count": page_count,
        "limits": limits,
        "class_quotas": class_quotas,
        "allocations": allocations,
        "summary": summary,
        "diagnostics": sink.as_plan_rows(),
        "diagnostics_dropped": sink.dropped,
        "plan_digest": canonical_digest(core),
    }


def _partial_plan(
    profile_id: str,
    profile_version: str,
    page_count: int,
    limits: dict[str, int],
    total_windows: int,
    sink: DiagnosticSink,
) -> dict[str, Any]:
    summary = {
        "windows_total": total_windows,
        "windows_built": 0,
        "windows_reserved": 0,
        "windows_cancelled": 0,
        "windows_unplanned": total_windows,
        "pages_reserved": 0,
        "pages_desired_total": 0,
        "page_budget": limits["max_pages"],
        "requests_budget": limits["max_requests"],
        "partial": True,
        "partial_reason": "work_budget_exhausted",
    }
    return _build_plan(
        profile_id, profile_version, page_count, limits, {}, [], summary, sink
    )


def plan_geometry_requests(
    policy: Mapping[str, Any],
    windows: Sequence[Any],
    *,
    page_count: int,
    limits: Mapping[str, Any],
    work_budget: WorkBudget,
) -> dict[str, Any]:
    """Compile policy + bound windows into ``du-geometry-plan/1``.

    Pure and deterministic: shuffling ``windows`` yields the same canonical
    plan core (digest, allocations, quotas, summary); diagnostics may add the
    out-of-order note for non-canonical input. Charges the caller's single
    :class:`WorkBudget` before each traversal; exhaustion yields a partial plan
    whose unplanned windows make no claims.
    """
    if not isinstance(work_budget, WorkBudget):
        raise TypeError("work_budget must be the existing WorkBudget protocol")
    if not isinstance(policy, Mapping):
        raise TypeError("policy must be a mapping")
    if policy.get("schema_version") != SCHEMA_POLICY:
        raise ValueError(f"unsupported geometry policy: {policy.get('schema_version')!r}")
    if not isinstance(limits, Mapping):
        raise TypeError("limits must be a mapping")
    if isinstance(windows, (str, bytes)) or not isinstance(windows, Sequence):
        raise TypeError("windows must be a sequence of mappings")
    if not is_int(page_count):
        raise TypeError("page_count must be an int")
    if page_count < 0:
        raise ValueError("page_count must be nonnegative")
    limits_out = _limits_out(limits)
    profile_id, profile_version = _profile_identity(policy)
    raw_rules = policy.get("rules", ())
    rule_count = (
        len(raw_rules)
        if isinstance(raw_rules, Sequence) and not isinstance(raw_rules, (str, bytes))
        else 0
    )
    total_windows = len(windows)
    sink = DiagnosticSink()

    try:
        # Prepay the bounded assembly (summary + digest) before any traversal.
        work_budget.charge(1 + 2 * (total_windows + rule_count))
        rules, profile_id, profile_version = _parse_rules(policy, sink, work_budget)
        valid = _validate_windows(windows, rules, page_count, sink, work_budget)
        survivors = _canonicalize(valid, sink, work_budget)

        consumable_rows = [row for row in survivors if row["consumable"]]
        consumable_classes = sorted(
            {row["demand_class"] for row in consumable_rows}, key=DEMAND_CLASSES.index
        )
        present_classes = sorted(
            {row["demand_class"] for row in survivors}, key=DEMAND_CLASSES.index
        )

        # Charge before the demand traversal, not after it.
        work_budget.charge(1 + len(survivors))
        desired, min_priority = _class_desired(consumable_rows)
        # Each admitted physical page spends one page AND one request. Reserving
        # only against max_pages promises capacity that a tighter request limit
        # cannot execute, so early windows would still starve reserved late ones.
        capacity = min(limits_out["max_pages"], limits_out["max_requests"])
        quotas, held, borrowed = _fair_quotas(
            consumable_classes, desired, min_priority, capacity
        )

        class_quotas: dict[str, dict[str, Any]] = {}
        for cls in present_classes:
            if cls in consumable_classes:
                class_quotas[cls] = {
                    "desired": desired[cls],
                    "base": held[cls],
                    "borrowed": borrowed[cls],
                    "quota": quotas[cls],
                    "consumable": True,
                }
            else:
                class_quotas[cls] = {
                    "desired": 0,
                    "base": 0,
                    "borrowed": 0,
                    "quota": 0,
                    "consumable": False,
                }

        # Per-window reservations: exclusive pages inside the class quota.
        work_budget.charge(1 + 2 * len(survivors))
        reservations: dict[str, int] = {}
        reasons: dict[str, str | None] = {}
        statuses: dict[str, str] = {}
        exclusives: dict[str, int] = {}
        for cls in consumable_classes:
            rows_cls = [row for row in consumable_rows if row["demand_class"] == cls]
            exclusive = _exclusive_pages(rows_cls)
            exclusives.update(exclusive)
            if quotas[cls] <= 0:
                reservations.update({row["window_key"]: 0 for row in rows_cls})
                for row in rows_cls:
                    statuses[row["window_key"]] = "cancelled"
                    reasons[row["window_key"]] = "class_quota_zero"
            else:
                reservations.update(
                    _apportion_windows(rows_cls, quotas[cls], desired[cls], exclusive)
                )
                for row in rows_cls:
                    statuses[row["window_key"]] = "reserved"
                    reasons[row["window_key"]] = None
        for row in survivors:
            if not row["consumable"]:
                statuses[row["window_key"]] = "cancelled"
                reasons[row["window_key"]] = "not_requestable"
                reservations.setdefault(row["window_key"], 0)
                exclusives.setdefault(row["window_key"], 0)

        allocations = [
            {
                "window_key": row["window_key"],
                "scope_id": row["scope_id"],
                "rule_key": row["rule_key"],
                "demand_class": row["demand_class"],
                "reading_priority": row["reading_priority"],
                "physical_start": row["physical_start"],
                "physical_end": row["physical_end"],
                "navigation_status": row["navigation_status"],
                "status": statuses[row["window_key"]],
                "reason": reasons[row["window_key"]],
                "desired_pages": exclusives[row["window_key"]],
                "quota_pages": reservations[row["window_key"]],
                "requestable": dict(row["requestable"]),
            }
            for row in survivors
        ]
        reserved_count = sum(1 for row in allocations if row["status"] == "reserved")
        summary = {
            "windows_total": total_windows,
            "windows_built": len(allocations),
            "windows_reserved": reserved_count,
            "windows_cancelled": len(allocations) - reserved_count,
            "windows_unplanned": 0,
            "pages_reserved": sum(class_quotas[cls]["quota"] for cls in class_quotas),
            "pages_desired_total": sum(class_quotas[cls]["desired"] for cls in class_quotas),
            "page_budget": limits_out["max_pages"],
            "requests_budget": limits_out["max_requests"],
            "partial": False,
            "partial_reason": None,
        }
        return _build_plan(
            profile_id,
            profile_version,
            page_count,
            limits_out,
            class_quotas,
            allocations,
            summary,
            sink,
        )
    except WorkBudgetExceeded:
        return _partial_plan(
            profile_id, profile_version, page_count, limits_out, total_windows, sink
        )


# --- admission state --------------------------------------------------------

def _require_plan(plan: Any) -> Mapping[str, Any]:
    """Validate shape AND content binding; the digest is re-derived on every
    use so a plan edited after planning (or corrupted in a replay) can never
    carry an existing state forward."""
    if not isinstance(plan, Mapping):
        raise TypeError("plan must be a mapping")
    if plan.get("schema_version") != SCHEMA_PLAN:
        raise ValueError(f"unsupported geometry plan: {plan.get('schema_version')!r}")
    plan_digest = plan.get("plan_digest")
    if not isinstance(plan_digest, str) or not plan_digest:
        raise ValueError("plan_digest missing; state cannot bind to this plan")
    if not isinstance(plan.get("profile_id"), str) or not isinstance(plan.get("profile_version"), str):
        raise ValueError("plan profile identity must be strings")
    page_count_value = plan.get("page_count")
    if not is_int(page_count_value) or page_count_value < 0:
        raise ValueError("plan.page_count must be a nonnegative int")
    limits = plan.get("limits")
    if not isinstance(limits, Mapping):
        raise ValueError("plan.limits must be a mapping")
    for bound in ("max_pages", "max_requests"):
        bound_value = limits.get(bound)
        if not is_int(bound_value) or bound_value < 0:
            raise ValueError(f"plan.limits.{bound} must be a nonnegative int")
    allocations = plan.get("allocations")
    if not isinstance(allocations, Sequence) or isinstance(allocations, (str, bytes)):
        raise ValueError("plan.allocations must be a sequence")
    for row in allocations:
        if not isinstance(row, Mapping):
            raise ValueError("every allocation must be a mapping")
        for field in ("window_key", "scope_id", "demand_class", "status"):
            if not isinstance(row.get(field), str):
                raise ValueError(f"allocation.{field} must be a string")
        for field in ("physical_start", "physical_end", "quota_pages"):
            if not is_int(row.get(field)):
                raise ValueError(f"allocation.{field} must be an int")
        if row["status"] not in ("reserved", "cancelled"):
            raise ValueError(f"unknown allocation status: {row['status']!r}")
        requestable = row.get("requestable")
        if not isinstance(requestable, Mapping) or not all(
            isinstance(requestable.get(kind), bool) for kind in ("discover", "fine")
        ):
            raise ValueError("allocation.requestable must carry two booleans")
    class_quotas = plan.get("class_quotas")
    if not isinstance(class_quotas, Mapping):
        raise ValueError("plan.class_quotas must be a mapping")
    for cls, row in class_quotas.items():
        if not isinstance(cls, str) or not isinstance(row, Mapping) or not is_int(row.get("quota")):
            raise ValueError("every class quota row must expose an int quota")
    for row in allocations:
        if row["status"] == "reserved" and row["demand_class"] not in class_quotas:
            raise ValueError("reserved allocation references an undeclared demand class")
    summary = plan.get("summary")
    if not isinstance(summary, Mapping):
        raise ValueError("plan.summary must be a mapping")
    for field in ("partial", "partial_reason", "windows_unplanned"):
        if field not in summary:
            raise ValueError(f"plan.summary missing {field}")
    if canonical_digest(_plan_core(plan)) != plan_digest:
        raise ValueError(
            "plan_digest does not match plan content; plan was tampered or corrupted, replan"
        )
    return plan


def new_admission_state(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Fresh ``du-geometry-plan-state/1`` in-call value bound to one plan.

    ``_require_plan`` re-derives the content digest here, so a tampered plan
    can never mint a state; every later admit/summarize re-checks it too.
    """
    plan = _require_plan(plan)
    return {
        "schema_version": SCHEMA_STATE,
        "plan_digest": plan["plan_digest"],
        "page_count": plan["page_count"],
        "limits": {
            "max_pages": plan["limits"]["max_pages"],
            "max_requests": plan["limits"]["max_requests"],
        },
        "spent": {"pages": 0, "requests": 0},
        "class_spent": {cls: 0 for cls in plan["class_quotas"]},
        "windows": {row["window_key"]: {"admitted": 0} for row in plan["allocations"]},
        "charged": {},
        "reason_counts": {reason: 0 for reason in RUN_REASONS},
    }


def _require_state(state: Any, plan: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(state, Mapping):
        raise TypeError("state must be a mapping")
    if state.get("schema_version") != SCHEMA_STATE:
        raise ValueError(f"unsupported admission state: {state.get('schema_version')!r}")
    if state.get("plan_digest") != plan["plan_digest"]:
        raise ValueError("state belongs to a different plan; replan or discard the state")
    for field in ("spent", "class_spent", "windows", "charged", "reason_counts"):
        if not isinstance(state.get(field), Mapping):
            raise ValueError(f"state.{field} must be a mapping")
    spent = state["spent"]
    for field in ("pages", "requests"):
        if not is_int(spent.get(field)) or spent.get(field) < 0:
            raise ValueError(f"state.spent.{field} must be a nonnegative int")
    for scope, pages in state["charged"].items():
        if not isinstance(scope, str) or not isinstance(pages, Mapping):
            raise ValueError("state.charged must map scope -> page ledger")
    for cls, value in state["class_spent"].items():
        if not isinstance(cls, str) or not is_int(value) or value < 0:
            raise ValueError("state.class_spent must map class -> nonnegative int")
    for key, counter in state["windows"].items():
        if not isinstance(key, str) or not isinstance(counter, Mapping):
            raise ValueError("state.windows must map window_key -> counter")
        admitted_value = counter.get("admitted")
        if not is_int(admitted_value) or admitted_value < 0:
            raise ValueError("state.windows counters must hold nonnegative ints")
    return state


def _echo_keys(window_keys: Any) -> list[str]:
    """Bounded echo: at most the admission cap, each entry size-capped, and
    built through islice so a huge caller list is never materialized."""
    if isinstance(window_keys, (str, bytes)) or not isinstance(window_keys, Sequence):
        return []
    echoed: list[str] = []
    for key in islice(window_keys, MAX_WINDOW_KEYS_PER_ADMISSION):
        if isinstance(key, str):
            echoed.append(key[:MAX_STRING])
        else:
            echoed.append(f"<{type(key).__name__}>")
    return echoed


def _echo_page(page: Any) -> Any:
    """Bounded echo: valid ints verbatim, anything else only its type shape —
    a caller object can never inflate the decision envelope."""
    if not is_int(page):
        return f"<{type(page).__name__}>"
    text = str(page)
    if len(text) <= 16:
        return page
    return f"<int:{len(text)}digits>"


def _decision(
    sink: DiagnosticSink,
    *,
    decision: str,
    reason: str,
    page: Any,
    window_keys: Any,
    covered: Sequence[str],
    admitted: Sequence[str],
    request: Mapping[str, bool] | None,
    charged_pages: int,
    charged_requests: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_ADMISSION,
        "decision": decision,
        "reason": reason,
        "page": _echo_page(page),
        "window_keys": _echo_keys(window_keys),
        "covered_window_keys": list(covered),
        "admitted_window_keys": list(admitted),
        "request": dict(request) if request is not None else None,
        "charged": {"pages": charged_pages, "requests": charged_requests},
        "diagnostics": sink.as_plan_rows(),
    }


def admit_geometry_request(
    plan: Mapping[str, Any],
    state: Mapping[str, Any],
    *,
    page: Any,
    window_keys: Any,
    tabular_evidence: Any,
    remaining: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Admit one observed page event; returns ``(decision, next_state)``.

    ``next_state`` is a fresh JSON-compatible value (the input state is never
    mutated) so a caller can stop mid-stream, serialize, and replay without
    changing the outcome. The caller's ``remaining`` only gates this call; it
    can never re-open pages already spent in ``state``.
    """
    plan = _require_plan(plan)
    state = _require_state(state, plan)
    sink = DiagnosticSink()
    page_count = plan["page_count"]
    limits = plan["limits"]
    allocations = plan["allocations"]

    def settle(
        decision: str,
        reason: str,
        *,
        covered: Sequence[str] = (),
        admitted: Sequence[str] = (),
        request: Mapping[str, bool] | None = None,
        charged_pages: int = 0,
        charged_requests: int = 0,
        mutate: Any = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        next_state: dict[str, Any] = deepcopy(dict(state))
        next_state["reason_counts"][decision] = next_state["reason_counts"].get(decision, 0) + 1
        if mutate is not None:
            mutate(next_state)
        return (
            _decision(
                sink,
                decision=decision,
                reason=reason,
                page=page,
                window_keys=window_keys,
                covered=covered,
                admitted=admitted,
                request=request,
                charged_pages=charged_pages,
                charged_requests=charged_requests,
            ),
            next_state,
        )

    # --- structural caller errors: recoverable rejects, never guessed ---------
    if not is_int(page):
        sink.add("ADMISSION_BAD_PAGE", f"page must be a real int, got {type(page).__name__}")
        return settle("rejected", "bad_page")
    if not 1 <= page <= page_count:
        sink.add("ADMISSION_PAGE_OUT_OF_RANGE", f"page {page} outside 1..{page_count}")
        return settle("rejected", "page_out_of_range")
    if not is_int(remaining) or remaining < 0:
        sink.add("ADMISSION_BAD_REMAINING", f"remaining must be a nonnegative int, got {remaining!r}")
        return settle("rejected", "bad_remaining")
    if isinstance(window_keys, (str, bytes)) or not isinstance(window_keys, Sequence):
        sink.add("ADMISSION_BAD_WINDOW_KEYS", "window_keys must be a sequence of strings")
        return settle("rejected", "bad_window_keys")
    if len(window_keys) == 0 or len(window_keys) > MAX_WINDOW_KEYS_PER_ADMISSION:
        sink.add(
            "ADMISSION_BAD_WINDOW_KEYS",
            f"window_keys must be 1..{MAX_WINDOW_KEYS_PER_ADMISSION} strings",
        )
        return settle("rejected", "bad_window_keys")
    keys = list(window_keys)
    if not all(isinstance(key, str) and key for key in keys):
        sink.add("ADMISSION_BAD_WINDOW_KEYS", "window_keys must be nonempty strings")
        return settle("rejected", "bad_window_keys")
    if not isinstance(tabular_evidence, str) or tabular_evidence not in EVIDENCE_VALUES:
        sink.add("ADMISSION_BAD_EVIDENCE", f"tabular_evidence {tabular_evidence!r} not in enum")
        return settle("rejected", "bad_evidence")

    key_set = sorted(set(keys))
    index = {row["window_key"]: (position, row) for position, row in enumerate(allocations)}
    missing = [key for key in key_set if key not in index]
    if missing:
        sink.add(
            "ADMISSION_WINDOW_NOT_IN_PLAN",
            "window_key not in this plan (unknown or unplanned under partial plan)",
            missing,
        )
        return settle("rejected", "window_not_in_plan")
    rows = [index[key][1] for key in key_set]
    rows.sort(key=lambda row: index[row["window_key"]][0])  # canonical allocations order

    scopes = {row["scope_id"] for row in rows}
    if len(scopes) > 1:
        sink.add(
            "ADMISSION_SCOPE_CROSSING",
            f"window_keys span scopes {sorted(scopes)}; parent scopes must not share one page event",
            key_set,
        )
        return settle("rejected", "scope_crossing")
    scope = next(iter(scopes))

    covering = [row for row in rows if row["physical_start"] <= page <= row["physical_end"]]
    if not covering:
        sink.add("ADMISSION_PAGE_OUTSIDE_WINDOWS", f"page {page} outside every given window")
        return settle("rejected", "page_outside_windows")
    outside = [row["window_key"] for row in rows if row not in covering]
    if outside:
        sink.add(
            "ADMISSION_KEY_OUTSIDE_WINDOW",
            f"page {page} outside these windows; only covering keys considered",
            outside,
        )

    # --- dedup once per (scope, page): repeated ACKs never re-charge ----------
    if str(page) in state["charged"].get(scope, {}):
        return settle(
            "deduplicated",
            "page_already_charged",
            covered=[row["window_key"] for row in covering],
        )

    # --- evidence semantics ---------------------------------------------------
    if tabular_evidence == "absent":
        return settle("not_found", "evidence_absent", covered=[row["window_key"] for row in covering])
    if tabular_evidence == "unknown":
        # Unknown never becomes a claim of "no table"; it costs nothing either.
        return settle("unknown", "evidence_unknown", covered=[row["window_key"] for row in covering])

    # --- fair reservation ladder --------------------------------------------
    window_state = state["windows"]
    candidates = [
        row
        for row in covering
        if row["status"] == "reserved"
        and window_state.get(row["window_key"], {}).get("admitted", 0) < row["quota_pages"]
    ]
    if not candidates:
        if all(row["status"] == "cancelled" for row in covering):
            return settle(
                "cancelled",
                covering[0].get("reason") or "not_requestable",
                covered=[row["window_key"] for row in covering],
            )
        return settle(
            "exhausted",
            "window_quota_exhausted",
            covered=[row["window_key"] for row in covering],
        )
    attribution = candidates[0]
    demand_class = attribution["demand_class"]
    class_quota = plan["class_quotas"][demand_class]["quota"]
    if state["class_spent"].get(demand_class, 0) + 1 > class_quota:
        return settle(
            "exhausted",
            "class_quota_exhausted",
            covered=[row["window_key"] for row in covering],
        )
    if state["spent"]["pages"] + 1 > limits["max_pages"]:
        return settle(
            "exhausted",
            "global_pages_exhausted",
            covered=[row["window_key"] for row in covering],
        )
    if state["spent"]["requests"] + 1 > limits["max_requests"]:
        return settle(
            "exhausted",
            "request_limit_exhausted",
            covered=[row["window_key"] for row in covering],
        )
    if remaining <= 0:
        return settle(
            "exhausted",
            "caller_remaining_exhausted",
            covered=[row["window_key"] for row in covering],
        )

    charged_keys = sorted(key_set)

    def _charge(next_state: dict[str, Any]) -> None:
        next_state["spent"]["pages"] += 1
        next_state["spent"]["requests"] += 1
        next_state["class_spent"][demand_class] = (
            next_state["class_spent"].get(demand_class, 0) + 1
        )
        counter = next_state["windows"].setdefault(attribution["window_key"], {"admitted": 0})
        counter["admitted"] = counter.get("admitted", 0) + 1
        next_state["charged"].setdefault(scope, {})[str(page)] = charged_keys

    # One reservation pays for this physical page, but its outer rule is not
    # the sole reading instruction. A nested transparent window can add fine
    # capability without requiring or charging a second page. Cancelled rows
    # never supply capabilities, and scopes were checked before this point.
    request = {
        kind: any(row["requestable"][kind] for row in covering if row["status"] == "reserved")
        for kind in ("discover", "fine")
    }
    return settle(
        "admitted",
        "admitted",
        covered=[row["window_key"] for row in covering],
        admitted=[attribution["window_key"]],
        request=request,
        charged_pages=1,
        charged_requests=1,
        mutate=_charge,
    )


def summarize_admission_state(
    plan: Mapping[str, Any], state: Mapping[str, Any]
) -> dict[str, Any]:
    """Canonical causal run summary; ``not_arrived`` is reserved-but-unused."""
    plan = _require_plan(plan)
    state = _require_state(state, plan)
    not_arrived = 0
    for row in plan["allocations"]:
        if row["status"] == "reserved":
            admitted = state["windows"].get(row["window_key"], {}).get("admitted", 0)
            not_arrived += max(0, row["quota_pages"] - admitted)
    return {
        "schema_version": SCHEMA_RUN_SUMMARY,
        "plan_digest": plan["plan_digest"],
        "reason_counts": {reason: state["reason_counts"].get(reason, 0) for reason in RUN_REASONS},
        "not_arrived": not_arrived,
        "spent": {
            "pages": state["spent"]["pages"],
            "requests": state["spent"]["requests"],
        },
        "class_spent": {cls: state["class_spent"].get(cls, 0) for cls in sorted(state["class_spent"])},
        "window_admissions": {
            key: state["windows"][key]["admitted"] for key in sorted(state["windows"])
        },
    }
