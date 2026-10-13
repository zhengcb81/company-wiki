"""ROOT selection bridge: dependency packages -> existing selector hints.

The existing selector keeps full authority over what is selected and what it
costs.  This module adds one thing it cannot express on its own: the knowledge
that certain units must travel together.  A project row whose unit caption and
period header were dropped is not a cheaper version of the evidence, it is a
different and false claim.

The bridge therefore only ever *adds* units to a selection -- the anchor, its
required context, and the members that keep a negation attached to the answer it
negates.  It never removes a unit the selector chose, and it never raises a
budget.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

# Diagnostic codes the bridge can raise.
CODE_CONTEXT_RESTORED = "CONTEXT_RESTORED"
CODE_NEGATION_PROTECTED = "NEGATION_PROTECTED"
CODE_NOT_SELECTABLE_WITHHELD = "NOT_SELECTABLE_WITHHELD"
CODE_UNKNOWN_PACKAGE = "UNKNOWN_PACKAGE"

_NEGATION_MARKERS = (
    "不生产",
    "未生产",
    "没有生产",
    "尚未",
    "不存在",
    "未与",
    "未取得",
    "未发生",
    "无生产",
    "并无",
    "not produce",
    "does not",
    "did not",
    "no longer",
    "have not",
    "has not",
)


def _has_negation(text: str) -> bool:
    folded = text.casefold()
    return any(marker in folded or marker in text for marker in _NEGATION_MARKERS)


def context_groups(packages: Mapping[str, Any], texts: Mapping[str, str]) -> list[dict[str, Any]]:
    """The shared dependency meaning used before and after output budgeting."""
    return [{"package_id": package.get("package_id"),
             "member_unit_ids": list(dict.fromkeys(package.get("member_unit_ids", ()))),
             "required_unit_ids": sorted(set(package.get("required_context_unit_ids", ())) | {
                 uid for uid in package.get("member_unit_ids", ()) if _has_negation(texts.get(uid, ""))})}
            for package in packages.get("packages", ())]



def build_context_graph(packages: Mapping[str, Any], texts: Mapping[str, str], *,
                        max_work_units: int = 2000000) -> dict[str, Any]:
    """Index the shared original dependency graph once for selection and sending."""
    if isinstance(max_work_units, bool) or not isinstance(max_work_units, int) or max_work_units < 0:
        raise ValueError("max_work_units must be a non-negative integer")
    items = list(packages.get("packages", ()))
    groups = context_groups(packages, texts)
    index: dict[str, list[int]] = {}
    work = 0
    for i, group in enumerate(groups):
        for uid in group["member_unit_ids"]:
            if work >= max_work_units:
                return {"items": items, "groups": groups, "index": index, "work_units": work,
                        "complete": False, "non_selectable": packages.get("non_selectable_unit_ids", ())}
            work += 1
            index.setdefault(uid, []).append(i)
    return {"items": items, "groups": groups, "index": index, "work_units": work,
            "complete": True, "non_selectable": packages.get("non_selectable_unit_ids", ())}


def dependency_closure(
    selected_unit_ids: Sequence[str],
    packages: Mapping[str, Any],
    texts: Mapping[str, str],
    *,
    max_added: int = 64,
    include_members: bool = False,
    max_work_units: int = 2000000,
    context_graph: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute a bounded fixed point; package ranking cannot change dependencies.

    Selectability comes from the adapter's explicit source-role marking. Equal
    wording alone does not prove that two locators represent the same context.
    Summary assembly can request full members as well as required dependencies;
    both traverse this same graph and obey the same bound.
    """
    from collections import deque

    if isinstance(max_added, bool) or not isinstance(max_added, int) or max_added < 0:
        raise ValueError("max_added must be a non-negative integer")
    if isinstance(max_work_units, bool) or not isinstance(max_work_units, int) or max_work_units < 0:
        raise ValueError("max_work_units must be a non-negative integer")
    selected = list(dict.fromkeys(uid for uid in selected_unit_ids if uid))
    present = set(selected)
    queue = deque(selected)
    graph = context_graph if context_graph is not None else build_context_graph(packages, texts, max_work_units=max_work_units)
    non_selectable = set(graph["non_selectable"])
    index = graph["index"]
    items = graph["items"]
    groups = graph["groups"]
    processed: set[int] = set()
    diagnostics: list[dict[str, Any]] = []
    added: list[str] = []
    work = graph["work_units"]
    limited = not graph["complete"] or work > max_work_units
    while queue and not limited:
        uid = queue.popleft()
        touched = [i for i in index.get(uid, ()) if i not in processed]
        # Collect targets before applying them, so arbitrary package order cannot
        # determine which dependencies survive a resource bound.
        targets: dict[str, list[tuple[str, str]]] = {}
        for i in touched:
            processed.add(i)
            package = items[i]
            pid = str(package.get("package_id", ""))
            required = set(groups[i]["required_unit_ids"])
            members = set(package.get("member_unit_ids", ()))
            negated = {member for member in members if _has_negation(texts.get(member, ""))}
            for target in required | negated | (members if include_members else set()):
                work += 1
                if work > max_work_units:
                    limited = True
                    break
                code = CODE_NEGATION_PROTECTED if target in negated else CODE_CONTEXT_RESTORED
                targets.setdefault(target, []).append((pid, code))
            if limited:
                break
        for target in sorted(targets):
            if target in present:
                continue
            if target in non_selectable:
                for pid, _ in targets[target]:
                    diagnostics.append({"code": CODE_NOT_SELECTABLE_WITHHELD,
                                        "package_id": pid, "unit_ids": [target],
                                        "detail": "adapter marked this duplicate non-selectable"})
                continue
            if len(added) >= max_added:
                diagnostics.append({"code": "CONTEXT_BUDGET_EXCEEDED", "unit_ids": [target],
                                    "detail": f"max_added={max_added}; required context remains unresolved"})
                continue
            present.add(target)
            selected.append(target)
            added.append(target)
            queue.append(target)
            for pid, code in targets[target]:
                diagnostics.append({"code": code, "package_id": pid, "unit_ids": [target],
                                    "detail": "restored dependency through the shared closure"})
    if limited:
        diagnostics.append({"code": "CONTEXT_WORK_BUDGET_EXCEEDED",
                            "detail": f"max_work_units={max_work_units}"})
    return {"selected_unit_ids": selected, "added_unit_ids": added,
            "added_count": len(added), "diagnostics": _dedupe(diagnostics),
            "work_units": min(work, max_work_units), "complete": not limited and not any(
                d["code"] == "CONTEXT_BUDGET_EXCEEDED" for d in diagnostics)}


def package_for_unit(packages: Mapping[str, Any], unit_id: str) -> Mapping[str, Any] | None:
    """Return the package that owns ``unit_id``, or ``None``."""
    for package in packages.get("packages", ()):
        if unit_id in package.get("member_unit_ids", ()):
            return package
    return None


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = (item["code"], item.get("package_id", ""), tuple(item.get("unit_ids", ())))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return sorted(result, key=lambda item: (item["code"], item.get("package_id", "")))


__all__ = [
    "CODE_CONTEXT_RESTORED",
    "CODE_NEGATION_PROTECTED",
    "CODE_NOT_SELECTABLE_WITHHELD",
    "CODE_UNKNOWN_PACKAGE",
    "dependency_closure",
    "package_for_unit",
]
