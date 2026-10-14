"""Bind declarative reading policies to source hierarchy; no parsing or IO."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import re
from typing import Any
import unicodedata

STRATEGY_BINDING_VERSION = "reading-strategy-binding/2"

_ITEM_NUMBER = re.compile(r"^item\s+(\d{1,2}[a-z]?)(?![a-z0-9_])")
_BARE_ITEM = re.compile(r"^item\s+(\d{1,2}[a-z]?)\.?$")


def _fold(text: str) -> str:
    # Presentation punctuation only, in this matching view. Chemical/math primes
    # (U+2032 etc.) are distinct and never converted; the source text is untouched.
    normal = unicodedata.normalize("NFKC", text).translate({0x2018: "'", 0x2019: "'"})
    return " ".join(normal.casefold().split())


def _literal_score(text: str, aliases: Sequence[str]) -> int | None:
    """Literal aliases with ASCII identifier boundaries, preserving CJK matching."""
    folded = _fold(text)
    scores = []
    for alias in aliases:
        needle = _fold(str(alias))
        if not needle:
            continue
        left = r"(?<![a-z0-9_])" if needle[0].isascii() and needle[0].isalnum() else ""
        right = r"(?![a-z0-9_])" if needle[-1].isascii() and needle[-1].isalnum() else ""
        if re.search(left + re.escape(needle) + right, folded):
            scores.append(len(needle))
    return max(scores) if scores else None


def _declared_item_number_score(text: str, aliases: Sequence[str]) -> int | None:
    """Interpret an actual bare label using only declared, scoped item identities.

    The producer has already resolved the form. Title-bearing source headings
    never use this fallback: their text must match the configured title. Item
    1A, 10 and 01 retain their complete original number/letter identity.
    """
    actual = _BARE_ITEM.fullmatch(_fold(text))
    if actual is None:
        return None
    for alias in aliases:
        declared = _ITEM_NUMBER.match(_fold(str(alias)))
        if declared is not None and declared.group(1) == actual.group(1):
            return len(actual.group(0))
    return None


def _item_title_conflict(text: str, aliases: Sequence[str]) -> bool:
    actual = _ITEM_NUMBER.match(_fold(text))
    if actual is None or _BARE_ITEM.fullmatch(_fold(text)) is not None:
        return False
    return any((declared := _ITEM_NUMBER.match(_fold(str(alias)))) is not None
               and declared.group(1) == actual.group(1) for alias in aliases)


def _rules(profile: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    # Once scoped rules exist, their failed paths must not retry flattened aliases.
    entries = profile.get("section_rules") if "section_rules" in profile else profile.get("section_priorities", ())
    return [e for e in entries or () if isinstance(e, Mapping)]


def _match_rule(
    sid: str, profile: Mapping[str, Any], parents: Mapping[str, str | None],
    headings: Mapping[str, str], diagnostics: list[dict[str, Any]],
) -> Mapping[str, Any] | None:
    matches: list[tuple[int, int, int, int, Mapping[str, Any]]] = []
    numbered_matches: list[tuple[int, int, int, int, Mapping[str, Any]]] = []
    title_conflict = False
    form = profile.get("form_type")
    actual_form = isinstance(form, str) and bool(_fold(form)) and _fold(form) != "unknown"
    for index, entry in enumerate(_rules(profile)):
        numbered = False
        path = entry.get("heading_path", ())
        if path:
            # Path layers are consecutive ancestors, ending at this heading.
            # Extra deep headings inherit the already bound parent instead.
            chain: list[str] = []
            current: str | None = sid
            seen = set()
            while current is not None and current in headings and current not in seen and len(chain) < len(path):
                seen.add(current)
                chain.append(headings[current])
                current = parents.get(current)
            if len(chain) != len(path):
                continue
            scores = []
            conflicts = False
            for text, aliases in zip(reversed(chain), path):
                score = _literal_score(text, aliases)
                if score is None and actual_form:
                    score = _declared_item_number_score(text, aliases)
                    numbered = numbered or score is not None
                    conflicts = conflicts or _item_title_conflict(text, aliases)
                scores.append(score)
            if any(score is None for score in scores):
                # Only a path otherwise compatible with its actual ancestors
                # can diagnose the same item's contrary explicit title.
                if conflicts and sum(score is None for score in scores) == 1:
                    title_conflict = True
                continue
            specificity = sum(score for score in scores if score is not None)
        else:
            text = headings.get(sid, "")
            aliases = entry.get("aliases", ())
            score = _literal_score(text, aliases)
            if score is None and actual_form:
                score = _declared_item_number_score(text, aliases)
                numbered = score is not None
                title_conflict = title_conflict or _item_title_conflict(text, aliases)
            if score is None:
                continue
            specificity = score
        ranked = (-len(path), -specificity, int(entry.get("priority", 3)), index, entry)
        (numbered_matches if numbered else matches).append(ranked)
    if matches:
        return min(matches, key=lambda match: match[:4])[-1]
    if len(numbered_matches) == 1:
        return numbered_matches[0][-1]
    if numbered_matches or title_conflict:
        diagnostics.append({"code": "SECTION_NUMBER_AMBIGUOUS" if numbered_matches else "SECTION_TITLE_CONFLICT",
                            "section_ids": [sid]})
    return None


def _parent(section: Mapping[str, Any]) -> str | None:
    # parent_id is the actual du-structure/1 wire key; tolerate the older spelling.
    return section.get("parent_id") if "parent_id" in section else section.get("parent_section_id")


def _unique(values: Sequence[Any]) -> list[Any]:
    result = []
    for value in values:
        if value not in result:
            result.append(deepcopy(value))
    return result


def bind_reading_plan(
    observation: Mapping[str, Any], structure: Mapping[str, Any], *,
    route: Mapping[str, Any], profile: Mapping[str, Any],
    child_profiles: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bind current source sections and the narrowest evidenced child policy.

    Scope and source ids are immutable. Equal-sized competing reading keys stay
    ambiguous even when their profile ids coincide. An unmatched deep heading
    inherits the exact parent's policy entry and priority, without a role-only
    lookup that could select another Part's entry.
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
        key = child.get("reading_profile_key") or pid
        scope = set(child.get("unit_ids", ()))
        if key not in children or not scope or not scope <= units.keys():
            diagnostics.append({"code": "CHILD_PROFILE_UNRESOLVED", "profile_id": pid})
            continue
        for uid in scope:
            candidates.setdefault(uid, []).append((len(scope), key))

    chosen_by_unit: dict[str, tuple[str | None, Mapping[str, Any]]] = {}
    for uid in units:
        chosen_key: str | None = None
        chosen = profile
        matches = sorted(candidates.get(uid, ()))
        if matches:
            best = {key for size, key in matches if size == matches[0][0]}
            if len(best) == 1:
                chosen_key = next(iter(best))
                chosen = children[chosen_key]
            else:
                diagnostics.append({"code": "CHILD_RANGE_AMBIGUOUS", "unit_ids": [uid]})
        chosen_by_unit[uid] = (chosen_key, chosen)

    bound = deepcopy(dict(structure))
    sections = {s["section_id"]: s for s in bound.get("sections", ())}
    parents = {sid: _parent(s) for sid, s in sections.items()}
    original_roles = {sid: str(s.get("section_role") or "unknown") for sid, s in sections.items()}
    headings = {sid: " ".join(str(units.get(uid, {}).get("text", ""))
                              for uid in s.get("heading_unit_ids", ())) for sid, s in sections.items()}
    resolved: dict[tuple[tuple[str, str | None], str], dict[str, Any]] = {}
    depths: dict[str, int] = {}

    def resolve(sid: str, key: str | None, chosen: Mapping[str, Any]) -> dict[str, Any]:
        identity: tuple[str, str | None] = ("child", key) if key is not None else ("parent", None)
        trail = []
        current: str | None = sid
        seen: set[str] = set()
        while current is not None and current in sections and (identity, current) not in resolved and current not in seen:
            seen.add(current)
            trail.append(current)
            current = parents.get(current)
        if current in seen:
            diagnostic = {"code": "SECTION_ANCESTRY_CYCLE", "section_ids": sorted(seen)}
            if diagnostic not in diagnostics:
                diagnostics.append(diagnostic)
        default = {"section_role": "unknown", "priority": 2, "questions": [], "matched_section_rule": None}
        inherited = resolved.get((identity, current), default) if current is not None else default
        depth = depths.get(current, 0) if current is not None else 0
        for node in reversed(trail):
            depth += 1
            depths.setdefault(node, depth)
            entry = _match_rule(node, chosen, parents, headings, diagnostics)
            if entry is not None:
                inherited = {"section_role": str(entry.get("role") or entry.get("section_role") or "unknown"),
                             "priority": int(entry.get("priority", 3)), "questions": list(entry.get("questions", ())),
                             "matched_section_rule": deepcopy(dict(entry))}
            elif inherited["section_role"] == "unknown" and inherited["matched_section_rule"] is None:
                native_role = original_roles[node]
                legacy_priority = next((int(e.get("priority", 3)) for e in chosen.get("section_priorities", ())
                                        if e.get("section_role") == native_role), 2) if "section_rules" not in chosen else 2
                inherited = {"section_role": native_role,
                             "priority": legacy_priority, "questions": [], "matched_section_rule": None}
            resolved[(identity, node)] = inherited
        return resolved.get((identity, sid), inherited)

    # Derive section views first; lookup is independent of declaration order.
    for sid, section in sections.items():
        heading = next(iter(section.get("heading_unit_ids", ())), None)
        section_key, section_profile = chosen_by_unit.get(heading, (None, profile)) if heading is not None else (None, profile)
        section["section_role"] = resolve(sid, section_key, section_profile)["section_role"]

    owners: dict[str, str] = {}
    for sid, section in sections.items():
        for uid in list(section.get("heading_unit_ids", ())) + list(section.get("body_unit_ids", ())):
            if uid in units and (uid not in owners or depths.get(sid, 0) > depths.get(owners[uid], 0)):
                owners[uid] = sid

    unit_profiles = {}
    used_profiles = []
    components = []
    used_keys = set()
    for uid, (key, chosen) in chosen_by_unit.items():
        reading = resolve(owners[uid], key, chosen) if uid in owners else {
            "section_role": "unknown", "priority": 2, "questions": [], "matched_section_rule": None}
        questions = _unique(list(chosen.get("reading_questions", ())) + reading["questions"])
        chosen_components = deepcopy(chosen.get("policy_components", []))
        unit_profiles[uid] = {
            "profile_id": chosen.get("profile_id"), "profile_version": chosen.get("profile_version"),
            "reading_profile_key": key, "family": chosen.get("family", "unknown"),
            "regime": chosen.get("regime", "unknown"), "form_type": chosen.get("form_type", "unknown"),
            "section_role": reading["section_role"], "priority": reading["priority"],
            "summary_focus": str(chosen.get("summary_focus") or ""),
            "policy_components": chosen_components, "reading_questions": questions,
            "context_requirements": deepcopy(chosen.get("context_requirements", [])),
            "family_policy": deepcopy(chosen.get("family_policy", {})),
            "negative_hints": deepcopy(chosen.get("negative_hints", [])),
            "semantic_units": deepcopy(chosen.get("semantic_units", [])),
            "matched_section_rule": deepcopy(reading["matched_section_rule"]),
        }
        identity = ("child", key) if key is not None else ("parent", None)
        if identity not in used_keys:
            used_keys.add(identity)
            used_profiles.append({"profile_id": chosen.get("profile_id"), "profile_version": chosen.get("profile_version"),
                                  "reading_profile_key": key, "policy_components": chosen_components,
                                  "family": chosen.get("family", "unknown"),
                                  "regime": chosen.get("regime", "unknown"), "form_type": chosen.get("form_type", "unknown")})
            components.extend(chosen_components)
            diagnostics.extend(deepcopy(chosen.get("policy_diagnostics", [])))
    return {"schema_version": "du-reading-plan/1", "structure": bound,
            "unit_profiles": unit_profiles, "diagnostics": diagnostics,
            "used_profiles": used_profiles, "policy_components": _unique(components)}
