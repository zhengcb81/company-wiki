"""Pure bridge from actual cover probes and native PDF navigation to DU9.

Navigation is an unconfirmed scheduling hint, never a canonical/body locator.
This bridge does not read originals, parse documents, call models or own state.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..layout_hints.contract import WorkBudget, WorkBudgetExceeded
from ..observation_adapter import build_observation
from ..profiles import get_profile, resolve_reading_profile, route_document
from ..profiles.geometry_policy import compile_geometry_policy
from ..strategy_binding import SectionPolicyMatcher
from .contracts import DiagnosticSink, canonical_digest
from .planner import plan_geometry_requests

BRIDGE_VERSION = "pdf-geometry-reading/1"
MAX_OUTLINE = 4096
MAX_DEPTH = 32
MAX_TITLE = 4096


@dataclass(frozen=True)
class PdfReadingContext:
    title: str = ""
    declared_kind: str = "unknown"
    language: str = "zh"


def _charge_material(value, budget):
    """Prepay bounded policy/probe material before visiting its children."""
    budget.charge()
    if isinstance(value, Mapping):
        budget.charge(len(value))
        for child in value.values():
            _charge_material(child, budget)
    elif isinstance(value, (list, tuple)):
        budget.charge(len(value))
        for child in value:
            _charge_material(child, budget)
    elif isinstance(value, str):
        budget.charge(1 + len(value) // 64)


def _limits(limits):
    if not isinstance(limits, Mapping):
        raise TypeError("limits must be a mapping")
    result = {}
    for key in ("max_pages", "max_requests"):
        value = limits.get(key, 64)
        if type(value) is not int or value < 0:
            raise ValueError(f"{key} must be a nonnegative integer")
        result[key] = min(value, 64)
    return result


def _native_rows(outline, page_count, budget, diagnostics):
    """Validate physical destinations, then close spans with one bounded stack.

    A malformed hierarchy cannot safely establish the unknown intervening
    boundaries. Keep the whole navigation unavailable rather than guessing.
    Native get_toc allocation happened upstream; this bounds Python work only.
    """
    budget.charge()
    if not isinstance(outline, Sequence) or isinstance(outline, (str, bytes)):
        diagnostics.add("NAVIGATION_ENTRY_INVALID", "expected get_toc(simple=True) rows")
        return [], False
    if not outline:
        diagnostics.add("NAVIGATION_MISSING", "no native outline; no synthetic windows")
        return [], True
    if len(outline) > MAX_OUTLINE:
        diagnostics.add("NAVIGATION_ENTRY_LIMIT", "native navigation exceeds 4096 entries")
        return [], False
    rows, stack = [], []
    previous_level, previous_page = 0, 0
    for index in range(len(outline)):
        budget.charge()
        value = outline[index]
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            diagnostics.add("NAVIGATION_ENTRY_INVALID", f"outline {index}: expected three fields; external links not inferred")
            return [], False
        level, title, page = value
        if type(level) is not int or not 1 <= level <= MAX_DEPTH:
            diagnostics.add("NAVIGATION_LEVEL_INVALID", f"outline {index}: level outside 1..32")
            return [], False
        if level > previous_level + 1:
            diagnostics.add("NAVIGATION_LEVEL_JUMP", f"outline {index}: missing ancestor")
            return [], False
        if not isinstance(title, str) or not title or len(title) > MAX_TITLE:
            diagnostics.add("NAVIGATION_ENTRY_INVALID", f"outline {index}: missing or overlong title")
            return [], False
        budget.charge(1 + len(title) // 64)
        if type(page) is not int or not 1 <= page <= page_count:
            diagnostics.add("NAVIGATION_DESTINATION_INVALID", f"outline {index}: invalid physical destination; no offset inferred")
            return [], False
        if page < previous_page:
            diagnostics.add("NAVIGATION_OUT_OF_ORDER", f"outline {index}: reverse physical destination")
            return [], False
        while stack and rows[stack[-1]]["level"] >= level:
            budget.charge()
            rows[stack.pop()]["end"] = page - 1
        rows.append({"index": index, "level": level, "title": title,
                     "start": page, "end": page_count})
        stack.append(index)
        previous_level, previous_page = level, page
    return rows, True


def _windows(rows, profile, policy, source_id, source_sha256, budget, diagnostics, unresolved, blocked):
    matcher = SectionPolicyMatcher(profile, budget)
    rules = profile.get("section_rules", ())
    budget.charge(1 + len(rules))
    compiled_by_material = {canonical_digest(raw): compiled["rule_key"]
                            for raw, compiled in zip(rules, policy["rules"])}
    compiled_rules = {rule["rule_key"]: rule for rule in policy["rules"]}
    stack, resolved = [], []
    for row in rows:
        budget.charge(1 + MAX_DEPTH)
        while stack and stack[-1]["level"] >= row["level"]:
            stack.pop()
        inherited = stack[-1]["effective"] if stack else None
        path = [ancestor["title"] for ancestor in stack] + [row["title"]]
        match = matcher.match(path)
        for diagnostic in matcher.diagnostics:
            diagnostics.add(diagnostic["code"], f"outline {row['index']}: contrary or ambiguous heading")
        # Contrary explicit identity must not acquire a parent business rule.
        if matcher.diagnostics:
            effective = None
        elif match is not None:
            effective = compiled_by_material[canonical_digest(match)]
        else:
            effective = inherited
        current = dict(row, effective=effective, heading_path=path,
                       contrary=bool(matcher.diagnostics))
        resolved.append(current)
        stack.append(current)
    windows = []
    for index, row in enumerate(resolved):
        budget.charge()
        # Last heading at one physical destination determines continuation.
        if index + 1 < len(resolved) and resolved[index + 1]["start"] == row["start"]:
            continue
        end = resolved[index + 1]["start"] - 1 if index + 1 < len(resolved) else row["end"]
        start = row["start"]
        group_start = index
        while group_start and resolved[group_start - 1]["start"] == row["start"]:
            budget.charge()
            group_start -= 1
        # A real parent and its more narrowly scoped child commonly start on
        # the same page. Only a complete, explicitly matched ancestor chain can
        # narrow that page's policy. Siblings, unrelated aliases and contrary
        # risk/context instructions still cannot be merged into business work.
        group = resolved[group_start:index + 1]
        budget.charge(1 + len(group))
        competing = any(other["effective"] != row["effective"] for other in group[:-1])
        if competing and not _same_page_narrowing(group, compiled_rules):
            diagnostics.add("NAVIGATION_SHARED_PAGE_CONFLICT", f"physical page {start}: differing section policies")
            blocked.append({'physical_start': start, 'physical_end': start})
            start += 1
        if row['contrary'] and start <= end:
            blocked.append({'physical_start': start, 'physical_end': end})
        if row['effective'] is None and not row['contrary'] and start <= end:
            unresolved.append({'physical_start': start, 'physical_end': end})
        if row["effective"] is None or start > end:
            continue
        basis = {"source_id": source_id, "source_sha256": source_sha256,
                 "outline_index": row["index"], "level": row["level"],
                 "physical_destination": row["start"]}
        window = {"scope_id": source_id, "rule_key": row["effective"],
                  "physical_start": start, "physical_end": end,
                  "navigation_status": "native_destination", "basis": basis,
                  "heading_path": row["heading_path"],
                  "navigation_span": {"physical_start": row["start"], "physical_end": row["end"]}}
        budget.charge(1 + len(row["heading_path"]))
        window["window_key"] = canonical_digest(window)
        windows.append(window)
    # Native headings are scheduling hints, not independent demand scopes.
    # Do not assign an artificial quota to every unrecognised subheading that
    # inherits the same rule. Keep maximal contiguous runs of one exact policy;
    # gaps, contrary/risk children and different rules always remain boundaries.
    merged = []
    for window in windows:
        budget.charge()
        segment_digest = canonical_digest(window)
        if (merged and merged[-1]['scope_id'] == window['scope_id']
                and merged[-1]['rule_key'] == window['rule_key']
                and merged[-1]['physical_end'] + 1 == window['physical_start']):
            previous = merged[-1]
            previous['physical_end'] = window['physical_end']
            basis = previous['basis']
            basis['navigation_segment_count'] += 1
            basis['navigation_segments_digest'] = canonical_digest(
                [basis['navigation_segments_digest'], segment_digest])
        else:
            window['basis']['navigation_segment_count'] = 1
            window['basis']['navigation_segments_digest'] = segment_digest
            merged.append(window)
    for window in merged:
        budget.charge()
        window.pop('window_key', None)
        window['window_key'] = canonical_digest(window)
    return merged


def _same_page_narrowing(group, rules):
    """Recognize explicit native ancestry, never equality of coarse roles."""
    narrow = rules.get(group[-1]["effective"])
    if narrow is None or len(narrow["heading_path"]) < len(group):
        return False
    previous_level = group[0]["level"] - 1
    for row in group:
        if row["contrary"] or row["level"] != previous_level + 1:
            return False
        previous_level = row["level"]
        prior = rules.get(row["effective"])
        if prior is None or prior["rule_key"] == narrow["rule_key"]:
            continue
        if len(prior["heading_path"]) >= len(narrow["heading_path"]):
            return False
        if prior["section_role"] == "risk" and narrow["section_role"] != "risk":
            return False
        if (prior["geometry_intent"]["discover"] in {"none", "context_only"}
                and narrow["geometry_intent"]["discover"] == "on_tabular_evidence"):
            return False
    return True


def prepare_geometry_reading(units, *, context: PdfReadingContext, source_id: str,
                             source_sha256: str, native_outline: Sequence,
                             page_count: int, limits: Mapping,
                             work_budget: WorkBudget) -> dict:
    """Plan native navigation using actual source probes and one caller budget.

    Callers supply their already-read first-two-page canonical units. This
    function neither produces canonical units nor validates originals again.
    Missing/exhausted budgets return a bounded honest partial plan, never an
    independently renewed work allowance.
    """
    if not isinstance(context, PdfReadingContext):
        raise TypeError("context must be PdfReadingContext")
    if type(page_count) is not int or page_count < 0:
        raise ValueError("page_count must be nonnegative integer")
    if not isinstance(source_id, str) or not source_id or len(source_id) > 4096:
        raise ValueError("source_id must be nonempty bounded text")
    if not isinstance(source_sha256, str) or len(source_sha256) != 64:
        raise ValueError("source_sha256 must be SHA256 text")
    int(source_sha256, 16)
    actual_limits = _limits(limits)
    # No allowance is minted when the caller did not supply its existing one.
    budget = work_budget if isinstance(work_budget, WorkBudget) else WorkBudget(0)
    diagnostics = DiagnosticSink()
    profile = {"profile_id": "unknown", "profile_version": "unknown", "section_rules": []}
    policy = compile_geometry_policy(profile)
    route = {"profile_id": "unknown", "family": "unknown", "confidence": "unknown"}
    windows, native_rows, navigation_complete = [], [], False
    unresolved = []
    blocked = []
    partial = False
    try:
        budget.charge()
        for probe in units:
            budget.charge()
            _charge_material(probe.raw_text, budget)
            _charge_material(probe.metadata, budget)
        _charge_material((context.title, context.declared_kind, context.language), budget)
        observation = build_observation(units, source_id=source_id, source_sha256=source_sha256,
                                        title=context.title, declared_kind=context.declared_kind,
                                        language=context.language, native_scan="partial")
        actual_route = route_document(observation)
        route = {key: actual_route.get(key, "unknown") for key in
                 ("profile_id", "family", "regime", "form_type", "confidence")}
        adopted_route = actual_route
        if not units:
            diagnostics.add("PROFILE_WITHOUT_ORIGINAL_PROBES", "title alone does not establish a reading profile")
            adopted_route = {**actual_route, "profile_id": "generic", "family": "unknown",
                             "regime": "unknown", "form_type": "unknown", "modifiers": {}}
        profile = resolve_reading_profile(get_profile(adopted_route["profile_id"]), observation, adopted_route)
        _charge_material(profile, budget)
        policy = compile_geometry_policy(profile)
        native_rows, navigation_complete = _native_rows(native_outline, page_count, budget, diagnostics)
        partial = not navigation_complete
        if native_rows and native_rows[0]['start'] > 1:
            unresolved.append({'physical_start': 1, 'physical_end': native_rows[0]['start'] - 1})
        windows = _windows(native_rows, profile, policy, source_id, source_sha256, budget, diagnostics, unresolved, blocked)
        # Reserve digest serialization before assembling the external plan.
        _charge_material(windows, budget)
        _charge_material(unresolved, budget)
    except WorkBudgetExceeded:
        diagnostics.add("READING_WORK_BUDGET_EXCEEDED", "preparation incomplete; no renewed budget or guessed windows")
        partial, windows, unresolved, blocked = True, [], [], []
    plan = plan_geometry_requests(policy, windows, page_count=page_count,
                                  limits=actual_limits, work_budget=budget)
    if partial:
        # Keep original PLANNER plan/digest intact. Coverage records the bridge's
        # incomplete navigation independently of PLANNER's empty-input success.
        diagnostics.add("READING_NAVIGATION_PARTIAL", "source navigation is not a complete request plan")
    digest = canonical_digest({"bridge_version": BRIDGE_VERSION, "source_id": source_id,
                               "source_sha256": source_sha256, "page_count": page_count,
                               "policy_digest": policy["content_digest"], "windows": windows,
                               "unresolved_navigation": unresolved,
                               "blocked_navigation": blocked,
                               "limits": actual_limits, "navigation_complete": navigation_complete,
                               "partial": partial})
    return {"schema_version": BRIDGE_VERSION, "resolved_profile": profile, "policy": policy,
            "windows": windows, "plan": plan, "diagnostics": diagnostics.as_plan_rows(),
            "unresolved_navigation": unresolved,
            "blocked_navigation": blocked,
            "request_digest": digest, "route": route, "partial": partial or plan["summary"]["partial"]}


__all__ = ["PdfReadingContext", "prepare_geometry_reading"]
