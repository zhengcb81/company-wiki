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


def _non_selectable_ids(
    packages: Mapping[str, Any], texts: Mapping[str, str]
) -> set[str]:
    """Return the units this bridge must never *add* to a selection.

    Two sources, in order of authority:

    1. ``packages['non_selectable_unit_ids']``, which the packaging stage derives
       from the adapter's role marking.  A non-selectable unit is the text-layer
       copy of a Q&A page: the parser emits the same page twice, once with
       structured ``investor_question``/``management`` roles and once as flat
       ``qa_text_shadow`` fragments.
    2. Duplicate text inside one package.  When two members of the same package
       carry byte-identical text, the later one cannot add evidence -- the model
       would receive the same sentence twice and the budget would pay for it
       twice.  This is a fallback for callers that hand the bridge a packages
       mapping with no marking, and it is deliberately conservative: it only
       ever withholds an exact duplicate.
    """
    marked = packages.get("non_selectable_unit_ids")
    result: set[str] = set()
    if isinstance(marked, Sequence) and not isinstance(marked, (str, bytes)):
        result.update(str(unit_id) for unit_id in marked)

    for package in packages.get("packages", ()):
        by_text: dict[str, str] = {}
        for unit_id in package.get("member_unit_ids", ()):
            text = texts.get(unit_id)
            if not isinstance(text, str) or not text:
                continue
            first = by_text.get(text)
            if first is None:
                by_text[text] = unit_id
            elif first not in result:
                # Keep the earlier occurrence and withhold the later duplicate.
                result.add(unit_id)
    return result


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

    The bridge only ever *adds* units -- it never removes one the caller
    selected.  What it will not add is a non-selectable duplicate: pulling the
    text-layer copy of an answer back in as "required context" would hand the
    model the same statement twice, and it would defeat the point of having
    excluded it during selection.  Each withheld unit is reported through
    ``NOT_SELECTABLE_WITHHELD`` so the omission stays visible.
    """
    selected = list(dict.fromkeys(unit_id for unit_id in selected_unit_ids if unit_id))
    selected_set = set(selected)
    added: list[str] = []
    diagnostics: list[dict[str, Any]] = []
    non_selectable = _non_selectable_ids(packages, texts)
    withheld: set[str] = set()

    def _withhold(package_id: str, unit_id: str) -> None:
        if unit_id in withheld:
            return
        withheld.add(unit_id)
        diagnostics.append(
            {
                "code": "NOT_SELECTABLE_WITHHELD",
                "package_id": package_id,
                "unit_ids": [unit_id],
                "detail": (
                    "not added: this unit is the non-selectable duplicate of a unit "
                    "already in the selection"
                ),
            }
        )

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
            if unit_id in non_selectable:
                _withhold(package["package_id"], unit_id)
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

        # A negation must not be separated from the thing it negates.  The
        # protection still applies when the only copy of the negation is the
        # non-selectable one: the unit is withheld from *addition*, but the
        # caller's own selection is never reduced, and the structured answer
        # carrying the same negation is protected by the loop below.
        negated = [unit_id for unit_id in members if _has_negation(texts.get(unit_id, ""))]
        if negated and present:
            for unit_id in negated:
                if unit_id in selected_set or len(added) >= max_added:
                    continue
                if unit_id in non_selectable:
                    _withhold(package["package_id"], unit_id)
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
    "CODE_NOT_SELECTABLE_WITHHELD",
    "CODE_UNKNOWN_PACKAGE",
    "dependency_closure",
    "package_for_unit",
]
