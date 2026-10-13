"""ROOT orchestration: route + structure -> atomic evidence packages.

This is the integration step from ``implementation.md`` step 5.  It does not
replace the existing selector; it produces, next to it, the *dependency-closed*
view that the selector's flat candidate list cannot express:

* which section a unit belongs to, and what that section is for;
* which units must travel together for a claim to stay true
  (a project row without its subject and unit caption is not evidence);
* which units carry a negation or a plan/actual distinction that must survive.

The output is a planning artefact.  Whether a package is finally sent to a
model remains the existing budget's decision, so this module never raises a
paid limit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

# Package kinds this layer emits, mirroring the structure lane's vocabulary.
PACKAGE_KINDS = (
    "project",
    "qa_exchange",
    "operating_table",
    "paragraph_event",
    "risk",
    "background",
)

# A package must never be split below its required context: a number without a
# unit/period is the classic "true quote, false claim" failure.
_NEVER_DROPPABLE = ("required_context_unit_ids", "anchor_unit_ids")


def build_dependency_packages(
    structure: Mapping[str, Any],
    *,
    route: Mapping[str, Any] | None = None,
    max_packages: int = 400,
    max_members: int = 64,
) -> dict[str, Any]:
    """Turn a ``du-structure/1`` result into budgetable atomic packages.

    ``route`` is optional.  When present it only prioritises: routing never
    removes a unit, and an unknown route still yields packages.
    """
    sections = {section["section_id"]: section for section in structure.get("sections", ())}
    role_priority = _role_priority(route)

    packages: list[dict[str, Any]] = []
    for semantic in structure.get("semantic_units", ()):
        members = list(semantic.get("member_unit_ids", ()))
        if not members:
            continue
        required = [
            unit_id
            for unit_id in semantic.get("required_context_unit_ids", ())
            if unit_id in members
        ]
        anchors = [unit_id for unit_id in semantic.get("anchor_unit_ids", ()) if unit_id in members]
        section_ids = [
            section_id
            for section_id in semantic.get("section_ids", ())
            if section_id in sections
        ]
        role = _dominant_role(sections, section_ids)
        truncated = len(members) > max_members
        if truncated:
            # Never truncate below the required context; drop the tail instead
            # and say so, so a package is never silently incomplete.
            keep = list(dict.fromkeys(required + anchors))
            for unit_id in members:
                if len(keep) >= max_members:
                    break
                if unit_id not in keep:
                    keep.append(unit_id)
            members = keep

        packages.append(
            {
                "package_id": semantic["semantic_id"],
                "kind": semantic["kind"],
                "section_ids": section_ids,
                "section_role": role,
                "member_unit_ids": members,
                "anchor_unit_ids": anchors,
                "required_context_unit_ids": required,
                "completeness": semantic.get("completeness", "unknown"),
                "priority": role_priority.get(role, role_priority["unknown"]),
                "diagnostics": [item.get("code") for item in semantic.get("diagnostics", ())],
                "truncated": truncated,
            }
        )

    packages.sort(
        key=lambda package: (
            -int(package["priority"]),
            0 if package["completeness"] == "complete" else 1,
            package["package_id"],
        )
    )
    if len(packages) > max_packages:
        packages = packages[:max_packages]

    return {
        "schema_version": "du-packages/1",
        "source_ref": structure.get("source_ref", {}),
        "packages": packages,
        "package_count": len(packages),
        "coverage": structure.get("coverage", {}),
        "diagnostics": _package_diagnostics(packages, structure),
    }


def _dominant_role(sections: Mapping[str, Any], section_ids: Sequence[str]) -> str:
    if not section_ids:
        return "unknown"
    counts: dict[str, int] = {}
    for section_id in section_ids:
        role = str(sections[section_id].get("section_role") or "unknown")
        counts[role] = counts.get(role, 0) + 1
    return max(sorted(counts), key=lambda role: counts[role])


def _role_priority(route: Mapping[str, Any] | None) -> dict[str, int]:
    """Priorities are a preference order only; they never delete a package."""
    base = {
        "business": 3,
        "management_discussion": 3,
        "operating_metrics": 3,
        "fundraising": 3,
        "questions": 3,
        "industry": 2,
        "outlook": 2,
        "risk": 2,
        "financial_notes": 1,
        "administrative": 1,
        "unknown": 2,
    }
    if not route:
        return base
    for entry in route.get("section_priorities", ()) or ():
        role = entry.get("section_role")
        priority = entry.get("priority")
        if isinstance(role, str) and isinstance(priority, int) and role in base:
            # Higher route priority (1 is most important) must map to a higher
            # selection score, so invert it.
            base[role] = 4 - max(1, min(3, priority))
    return base


def _package_diagnostics(
    packages: Sequence[Mapping[str, Any]], structure: Mapping[str, Any]
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    truncated = [package["package_id"] for package in packages if package["truncated"]]
    if truncated:
        diagnostics.append(
            {
                "code": "PACKAGE_TRUNCATED",
                "package_ids": truncated,
                "detail": "member list was bounded; required context was preserved",
            }
        )
    if not packages and structure.get("semantic_units"):
        diagnostics.append(
            {
                "code": "NO_PACKAGES",
                "package_ids": [],
                "detail": "structure produced semantic units but no package survived",
            }
        )
    return diagnostics


def package_units_for_prompt(
    packages: Mapping[str, Any],
    texts: Mapping[str, str],
    *,
    max_packages: int = 40,
) -> list[dict[str, Any]]:
    """Materialise selected packages with their text, dependency-closed.

    ``texts`` maps ``unit_id -> text`` and is supplied by the caller from the
    already-loaded observation, so no second copy of the document is created
    here.
    """
    selected: list[dict[str, Any]] = []
    for package in packages.get("packages", ())[:max_packages]:
        members = [
            {"unit_id": unit_id, "text": texts.get(unit_id, "")}
            for unit_id in package["member_unit_ids"]
        ]
        if not any(member["text"] for member in members):
            continue
        selected.append(
            {
                "package_id": package["package_id"],
                "kind": package["kind"],
                "section_role": package["section_role"],
                "completeness": package["completeness"],
                "members": members,
            }
        )
    return selected


__all__ = [
    "PACKAGE_KINDS",
    "build_dependency_packages",
    "package_units_for_prompt",
]
