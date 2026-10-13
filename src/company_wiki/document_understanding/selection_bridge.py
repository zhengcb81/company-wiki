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


def dependency_closure(
    selected_unit_ids: Sequence[str],
    packages: Mapping[str, Any],
    texts: Mapping[str, str],
    *,
    max_added: int = 64,
) -> dict[str, Any]:
    """Return ``selected + required context`` as a dependency-closed selection.

    ``texts`` maps ``unit_id -> text`` so a negation can be detected without
    re-reading the document.
    """
    selected = list(dict.fromkeys(unit_id for unit_id in selected_unit_ids if unit_id))
    selected_set = set(selected)
    added: list[str] = []
    diagnostics: list[dict[str, Any]] = []

    for package in packages.get("packages", ()):
        members = list(package.get("member_unit_ids", ()))
        if not members:
            continue
        present = [unit_id for unit_id in members if unit_id in selected_set]
        if not present:
            continue

        # A package with any member selected must bring its required context.
        for unit_id in package.get("required_context_unit_ids", ()):
            if unit_id in selected_set or unit_id not in members:
                continue
            if len(added) >= max_added:
                diagnostics.append(
                    {
                        "code": "CONTEXT_BUDGET_EXCEEDED",
                        "package_id": package["package_id"],
                        "detail": f"max_added={max_added} reached while closing context",
                    }
                )
                break
            selected.append(unit_id)
            selected_set.add(unit_id)
            added.append(unit_id)
        else:
            if any(
                unit_id in package.get("required_context_unit_ids", ())
                for unit_id in present
            ) or package.get("required_context_unit_ids"):
                restored = [
                    unit_id
                    for unit_id in package.get("required_context_unit_ids", ())
                    if unit_id in added
                ]
                if restored:
                    diagnostics.append(
                        {
                            "code": CODE_CONTEXT_RESTORED,
                            "package_id": package["package_id"],
                            "detail": "restored required context for a partially selected package",
                        }
                    )

        # A negation must not be separated from the thing it negates.
        negated = [unit_id for unit_id in members if _has_negation(texts.get(unit_id, ""))]
        if negated and present:
            for unit_id in negated:
                if unit_id in selected_set or len(added) >= max_added:
                    continue
                selected.append(unit_id)
                selected_set.add(unit_id)
                added.append(unit_id)
                diagnostics.append(
                    {
                        "code": CODE_NEGATION_PROTECTED,
                        "package_id": package["package_id"],
                        "unit_ids": [unit_id],
                        "detail": "kept a negation with the package it belongs to",
                    }
                )

    return {
        "selected_unit_ids": selected,
        "added_unit_ids": added,
        "added_count": len(added),
        "diagnostics": _dedupe(diagnostics),
    }


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
    "CODE_UNKNOWN_PACKAGE",
    "dependency_closure",
    "package_for_unit",
]
