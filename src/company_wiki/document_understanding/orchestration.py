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

# Package kinds this layer emits, mirroring the structure lane's vocabulary.  The
# constant is checked against every incoming semantic unit rather than merely
# published, so a structure lane that starts emitting a new kind is reported
# instead of being silently ranked as prose.
PACKAGE_KINDS = (
    "project",
    "qa_exchange",
    "operating_table",
    "paragraph_event",
    "risk",
    "background",
)

#: Ranking bands by semantic kind within one chapter.  Structured, dependency-bearing
#: units come first; free prose fills whatever budget remains.
_KIND_BAND: dict[str, int] = {
    "project": 0,
    "operating_table": 0,
    "qa_exchange": 0,
    "risk": 1,
    "paragraph_event": 2,
    "background": 3,
}


def build_dependency_packages(
    structure: Mapping[str, Any],
    *,
    route: Mapping[str, Any] | None = None,
    profile: Mapping[str, Any] | None = None,
    max_packages: int | None = None,
    max_members: int = 64,
    unit_order: Mapping[str, int] | None = None,
    non_selectable_unit_ids: Sequence[str] = (),
    unit_reading_plan: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Turn a ``du-structure/1`` result into budgetable atomic packages.

    ``route`` and ``profile`` are both optional and only prioritise: routing never
    removes a unit, and an unknown route still yields packages. Pass the profile from
    ``get_profile(route["profile_id"])`` to apply that document type's own reading
    order; passing only the route leaves the generic order in place, which is a valid
    but less informed result.

    ``max_packages`` defaults to ``None``, meaning every semantic unit is packaged. A
    numeric cap truncates the tail of the ranked list, and because the last sort key is
    the package id the tail is the *late pages*: a cap therefore keeps the front of the
    document and drops the back. That is the same fixed-prefix failure this whole layer
    exists to remove, so a cap is only applied when a caller explicitly asks for one and
    it is always reported through ``PACKAGE_LIMIT_REACHED``.

    Ranking within a chapter prefers dependency-bearing kinds (a project, an operating
    table, a QA exchange) over free prose, because those are the units that carry the
    subject, unit, period and footnote a fact needs to stay true.

    ``non_selectable_unit_ids`` carries the observation's non-selectable units (today the
    Q&A text-layer shadow) so the decision reaches the consumers that act on it. The units
    are **not** removed from any package -- the structure lane needs both Q&A copies to pair
    a question with its answer -- they are only labelled so a consumer never *adds* or
    *sends* a duplicate.
    """
    excluded = tuple(dict.fromkeys(str(item) for item in non_selectable_unit_ids))
    sections = {section["section_id"]: section for section in structure.get("sections", ())}
    role_priority = _role_priority(route, profile)
    unknown_kinds: list[str] = []

    packages: list[dict[str, Any]] = []
    for semantic in structure.get("semantic_units", ()):
        members = list(semantic.get("member_unit_ids", ()))
        if not members:
            continue
        kind = str(semantic.get("kind") or "")
        if kind not in PACKAGE_KINDS and kind not in unknown_kinds:
            # An unrecognised kind would still be packaged, but it would rank as
            # prose and no consumer would know it is dependency-bearing. Report
            # it rather than degrade in silence.
            unknown_kinds.append(kind)
        required = [
            unit_id
            for unit_id in semantic.get("required_context_unit_ids", ())
        ]
        anchors = [unit_id for unit_id in semantic.get("anchor_unit_ids", ()) if unit_id in members]
        section_ids = [
            section_id
            for section_id in semantic.get("section_ids", ())
            if section_id in sections
        ]
        role = _dominant_role(sections, section_ids)
        reading = unit_reading_plan or {}
        anchor_plan = next((reading[uid] for uid in anchors + members if uid in reading), {})
        if anchor_plan:
            role = str(anchor_plan.get("section_role") or role)
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

        order = unit_order or {}
        first_ordinal = min(
            (order.get(unit_id, 1 << 30) for unit_id in members), default=1 << 30
        )
        packages.append(
            {
                "package_id": semantic["semantic_id"],
                "kind": semantic["kind"],
                "section_ids": section_ids,
                "section_role": role,
                "member_unit_ids": members,
                "anchor_unit_ids": anchors,
                "required_context_unit_ids": required,
                **({"citation_support_views": [view for view in (anchors, required) if view]}
                   if kind == "qa_exchange" else {}),
                "completeness": semantic.get("completeness", "unknown"),
                "priority": 4 - int(anchor_plan["priority"]) if anchor_plan else role_priority.get(role, role_priority["unknown"]),
                "reading_family": anchor_plan.get("family"),
                "reading_profile_id": anchor_plan.get("profile_id"),
                "reading_profile_version": anchor_plan.get("profile_version"),
                "summary_focus": anchor_plan.get("summary_focus", ""),
                "first_ordinal": first_ordinal,
                "diagnostics": [item.get("code") for item in semantic.get("diagnostics", ())],
                "truncated": truncated,
            }
        )

    packages.sort(
        key=lambda package: (
            # Section priority comes FIRST. The profile's whole purpose is to say which
            # chapters matter for this document type, so a dependency-bearing unit in a
            # low-priority chapter must not jump ahead of the chapter the profile nominated as
            # read-first. Ranking kind ahead of priority would make reading order ignore the
            # document type, which is the fixed-order failure this layer exists to remove.
            -int(package["priority"]),
            # Within one priority band, structured dependency-bearing units beat free prose.
            _KIND_BAND.get(package["kind"], _KIND_BAND["background"]),
            0 if package["completeness"] == "complete" else 1,
            package["first_ordinal"],
            package["package_id"],
        )
    )
    truncated_by_limit = False
    if max_packages is not None and len(packages) > max_packages:
        truncated_by_limit = True
        packages = packages[:max_packages]

    return {
        "schema_version": "du-packages/1",
        "source_ref": structure.get("source_ref", {}),
        "packages": packages,
        "package_count": len(packages),
        "non_selectable_unit_ids": list(excluded),
        "coverage": structure.get("coverage", {}),
        "diagnostics": _package_diagnostics(
            packages,
            structure,
            truncated_by_limit=truncated_by_limit,
            unknown_kinds=unknown_kinds,
        ),
    }


def _dominant_role(sections: Mapping[str, Any], section_ids: Sequence[str]) -> str:
    if not section_ids:
        return "unknown"
    counts: dict[str, int] = {}
    for section_id in section_ids:
        role = str(sections[section_id].get("section_role") or "unknown")
        counts[role] = counts.get(role, 0) + 1
    return max(sorted(counts), key=lambda role: counts[role])


def _role_priority(
    route: Mapping[str, Any] | None,
    profile: Mapping[str, Any] | None = None,
) -> dict[str, int]:
    """Priorities are a preference order only; they never delete a package.

    The section priorities live on the *profile*, not on the route: ``route_document``
    returns which document this is, while ``get_profile`` returns how to read it. Taking
    them from the route (or from a route that has no such key) silently degrades every
    document to the same generic order, so both objects are accepted here and the profile
    wins when present.
    """
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
    entries = _section_priority_entries(profile) or _section_priority_entries(route)
    for entry in entries:
        role = entry.get("section_role")
        priority = entry.get("priority")
        if isinstance(role, str) and isinstance(priority, int) and role in base:
            # Higher route priority (1 is most important) must map to a higher
            # selection score, so invert it.
            base[role] = 4 - max(1, min(3, priority))
    return base


def _section_priority_entries(source: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    """Return a source's section-priority entries, whichever shape it uses."""
    if not source:
        return []
    entries = source.get("section_priorities")
    if isinstance(entries, Sequence) and not isinstance(entries, (str, bytes)):
        return [entry for entry in entries if isinstance(entry, Mapping)]
    return []


def _package_diagnostics(
    packages: Sequence[Mapping[str, Any]],
    structure: Mapping[str, Any],
    *,
    truncated_by_limit: bool = False,
    unknown_kinds: Sequence[str] = (),
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if unknown_kinds:
        diagnostics.append(
            {
                "code": "UNKNOWN_SEMANTIC_KIND",
                "package_ids": [],
                "detail": (
                    "structure emitted kind(s) outside the frozen vocabulary "
                    f"{sorted(unknown_kinds)}; they are packaged but rank as prose"
                ),
            }
        )
    truncated = [package["package_id"] for package in packages if package["truncated"]]
    if truncated:
        diagnostics.append(
            {
                "code": "PACKAGE_TRUNCATED",
                "package_ids": truncated,
                "detail": "member list was bounded; required context was preserved",
            }
        )
    if truncated_by_limit:
        diagnostics.append(
            {
                "code": "PACKAGE_LIMIT_REACHED",
                "package_ids": [],
                "detail": (
                    "max_packages cut the ranked tail, which is the late pages of the "
                    "document; treat the omitted packages as unread, not as absent"
                ),
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
