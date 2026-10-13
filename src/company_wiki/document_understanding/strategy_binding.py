"""Bind declarative profiles to an existing source structure, without IO or parsing."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any
import unicodedata


def _fold(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _role(text: str, profile: Mapping[str, Any], fallback: str) -> str:
    folded = _fold(text)
    matches = []
    for entry in profile.get("section_priorities", ()):
        for alias in entry.get("aliases", ()):
            needle = _fold(str(alias))
            if needle and needle in folded:
                matches.append((-len(needle), int(entry.get("priority", 3)), str(entry["section_role"])))
    return min(matches)[2] if matches else fallback


def bind_reading_plan(
    observation: Mapping[str, Any], structure: Mapping[str, Any], *,
    route: Mapping[str, Any], profile: Mapping[str, Any],
    child_profiles: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply aliases and the narrowest evidenced child range to source units.

    External links are not read body. Equal-sized conflicting ranges fall back
    to the parent and retain a diagnostic. Original ids, coordinates and input
    mappings are immutable; consumers use this derived reading view.
    """
    units = {u["unit_id"]: u for u in observation.get("units", ())}
    children = child_profiles or {}
    candidates: dict[str, list[tuple[int, str]]] = {}
    diagnostics = []
    for child in route.get("child_routes", ()):
        reason = child.get("reason", "")
        code = reason.get("code", "") if isinstance(reason, Mapping) else str(reason)
        if "EXTERNAL_ATTACHMENT_NOT_READ" in code:
            continue
        pid = child.get("profile_id")
        scope = set(child.get("unit_ids", ()))
        if pid not in children or not scope or not scope <= units.keys():
            diagnostics.append({"code": "CHILD_PROFILE_UNRESOLVED", "profile_id": pid})
            continue
        for uid in scope:
            candidates.setdefault(uid, []).append((len(scope), pid))
    profiles_by_unit = {}
    for uid in units:
        chosen = profile
        matches = sorted(candidates.get(uid, ()))
        if matches:
            best = {pid for size, pid in matches if size == matches[0][0]}
            if len(best) == 1:
                chosen = children[next(iter(best))]
            else:
                diagnostics.append({"code": "CHILD_RANGE_AMBIGUOUS", "unit_ids": [uid]})
        profiles_by_unit[uid] = chosen
    bound = deepcopy(dict(structure))
    roles: dict[str, str] = {}
    for section in bound.get("sections", ()):
        headings = section.get("heading_unit_ids", ())
        heading = " ".join(str(units.get(uid, {}).get("text", "")) for uid in headings)
        section_profile = profiles_by_unit.get(next(iter(headings), None), profile)
        role = _role(heading, section_profile, str(section.get("section_role") or "unknown"))
        section["section_role"] = role
        for uid in list(headings) + list(section.get("body_unit_ids", ())):
            if uid in units:
                roles[uid] = role
    unit_profiles = {}
    for uid, chosen in profiles_by_unit.items():
        role = roles.get(uid, "unknown")
        priority = next((int(e.get("priority", 3)) for e in chosen.get("section_priorities", ())
                         if e.get("section_role") == role), 2)
        unit_profiles[uid] = {"profile_id": chosen.get("profile_id"),
                              "profile_version": chosen.get("profile_version"),
                              "family": chosen.get("family", "unknown"),
                              "section_role": role, "priority": priority,
                              "summary_focus": str(chosen.get("summary_focus") or "")}
    return {"schema_version": "du-reading-plan/1", "structure": bound,
            "unit_profiles": unit_profiles, "diagnostics": diagnostics}
