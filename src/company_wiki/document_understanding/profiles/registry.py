"""The single installed reading-policy catalog and its legacy wire projections.

One packaged asset is loaded at import. All calls thereafter are pure: no docs, directory,
network, model, configuration, or clock reads. Legacy IDs are data bindings, not separate
handwritten profiles. Full family sections retain their individual hierarchy and priority;
the flattened old wire is a compatibility view, not the new ReadingPlan's rule source.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from importlib.resources import files
import json
import re
from typing import Any, Iterator
import unicodedata

from . import vocabulary as v
from .model import Profile, SectionPriority
from .observation import Limits, Observation, UnitRef, parse_observation

_CATALOG = json.loads(files(__package__).joinpath("reading_catalog.json").read_text(encoding="utf-8"))
if _CATALOG.get("schema_version") != "du-reading-catalog/1":
    raise RuntimeError("unsupported installed reading catalog")


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _fold(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def _binding(profile_id: str) -> dict:
    if not isinstance(profile_id, str):
        raise TypeError("profile_id must be a string")
    if not profile_id:
        raise ValueError("profile_id must be nonempty")
    for binding in _CATALOG["legacy_bindings"]:
        if binding["profile_id"] == profile_id:
            return binding
    raise KeyError(f"unknown profile_id: {profile_id!r}")


def _family_records(ids: Sequence[str]) -> list[dict]:
    index = {record["id"]: record for record in _CATALOG["families"]}
    return [index[identifier] for identifier in ids]


def _unique(values: Sequence[Any]) -> list[Any]:
    output = []
    seen = set()
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            output.append(deepcopy(value))
    return output


def _flatten(sections: Sequence[Mapping], supplements: Mapping | None = None) -> list[dict]:
    """Legacy projection only; this intentionally never replaces full section_rules."""
    roles: dict[str, dict] = {}
    for section in sections:
        role = str(section["role"])
        entry = roles.setdefault(role, {"section_role": role, "aliases": [], "priority": 3})
        entry["priority"] = min(entry["priority"], int(section["priority"]))
        for alias in section["aliases"]:
            if alias not in entry["aliases"]:
                entry["aliases"].append(alias)
    for role, aliases in (supplements or {}).items():
        entry = roles.setdefault(role, {"section_role": role, "aliases": [], "priority": 2})
        entry["aliases"] = list(dict.fromkeys(entry["aliases"] + list(aliases)))
    return list(roles.values())


def _sections(records: Sequence[Mapping]) -> list[dict]:
    return [deepcopy(section) for record in records for section in record["sections"]]


def _questions(records: Sequence[Mapping]) -> list[str]:
    return _unique([question for record in records for question in record["reading_questions"]])


def _focus(records: Sequence[Mapping]) -> str:
    return " ".join([str(_CATALOG["shared_focus"]), *_questions(records)])


def _negative(records: Sequence[Mapping]) -> list[str]:
    return _unique([hint for record in records for hint in record.get("negative_hints", ())] +
                   [f"{item['content']}；例外：{item['unless']}"
                    for record in records for item in record.get("deprioritize", ())])


def profile_by_id(profile_id: str) -> Profile:
    """Typed compatibility view from the same installed data, not another rule registry."""
    binding = _binding(profile_id)
    records = _family_records(binding["family_ids"])
    if not records:
        records = [_CATALOG["fallback"]]
    rows = _flatten(_sections(records), binding.get("legacy_alias_supplements"))
    return Profile(profile_id=profile_id, family=binding["family"], regime=binding["regime"],
                   section_priorities=tuple(SectionPriority(row["section_role"], tuple(row["aliases"]), row["priority"]) for row in rows),
                   semantic_units=tuple(binding["semantic_units"]), summary_focus=_focus(records),
                   negative_hints=tuple(_negative(records)))


def profile_wire(profile_id: str) -> dict:
    """Fresh JSON-compatible old profile shape."""
    return profile_by_id(profile_id).to_wire()


def iter_profiles() -> Iterator[Profile]:
    """Iterate the installed legacy bindings in deterministic declaration order."""
    return (profile_by_id(binding["profile_id"]) for binding in _CATALOG["legacy_bindings"])


def listed_profiles() -> list[dict]:
    """Each returned mapping is fresh and cannot mutate shared policy data."""
    return [profile.to_wire() for profile in iter_profiles()]


def _component(record: Mapping, kind: str) -> dict:
    return {"kind": kind, "id": record["id"], "version": record["version"],
            "content_digest": _digest(record)}


def _base_form(value: Any) -> str:
    form = _fold(value or "").removesuffix("/a")
    return "" if form == "unknown" else form


def _signal_matches(phrase: str, text: str) -> bool:
    return _matches_folded(_fold(phrase), _fold(text))


def _matches_folded(needle: str, haystack: str) -> bool:
    if not needle or needle not in haystack:
        return False
    if re.fullmatch(r"[a-z0-9 _-]+", needle):
        return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", haystack) is not None
    return needle in haystack


def configured_table_signal(text: str) -> bool:
    """Triage a possible operating table using the one installed policy asset.

    This never turns a whole page into a row or asserts any operating fact.
    Expensive extraction is indicated only by configured strong row evidence;
    weak region/amount signals still retain their ordinary facet meaning.
    """
    if not isinstance(text, str):
        raise TypeError("table signal text must be a string")
    folded = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", _fold(text))
    matched = False
    for facet in _CATALOG["facets"]:
        for evidence in facet["positive_evidence"]:
            enabled = evidence.get("table_scan", False)
            if type(enabled) is not bool:
                raise ValueError("table_scan must be a boolean")
            if not enabled or "pdf_table_row" not in evidence["unit_kinds"]:
                continue
            matched = matched or any(_matches_folded(_fold(signal), folded) for signal in evidence["signals"])
    return matched


def _policy_score(record: Mapping, parsed: Observation) -> tuple[int, int]:
    """Recognition hints rank applicable policies; they do not assert business facts."""
    metadata = {"title": parsed.title, "regime": parsed.regime_claim, "form_type": parsed.form_type,
                "declared_kind": parsed.declared_kind, "mime_type": parsed.mime_type,
                "language": parsed.language, "revision": parsed.revision}
    score = matched = 0
    for item in record["recognition"]["positive"]:
        signal = item["signal"]
        if signal["kind"] == "metadata_equals":
            actual = metadata.get(signal["field"])
            hit = actual is not None and (_base_form(actual) == _base_form(signal["value"])
                                         if signal["field"] == "form_type" else _fold(actual) == _fold(signal["value"]))
            weight = 6
        else:
            location = item["location"]
            if location == "metadata":
                texts = [parsed.title or ""]
            elif location == "cover":
                texts = [parsed.title or "", *(u.text for u in parsed.probes[:3] if not u.text_clipped)]
            elif location == "toc":
                texts = [u.text for u in parsed.probes if u.kind == "toc" and not u.text_clipped]
            elif location == "attachment":
                texts = [u.text for u in parsed.probes if u.kind in {"attachment", "heading", "title"} and not u.text_clipped]
            else:
                texts = [u.text for u in parsed.probes if u.kind not in {"toc", "reference", "metadata"} and not u.text_clipped]
            hit = any(_signal_matches(signal["value"], text) for text in texts)
            weight = 3
        if hit:
            score += weight
            matched += 1
    return score, matched


def _bounded_observation(observation: Mapping, route: Mapping, limits: Mapping | None) -> Observation:
    resolved = Limits.from_mapping(limits)
    capped = {"max_probe_units": min(resolved.max_probe_units, v.DEFAULT_MAX_PROBE_UNITS),
              "max_probe_chars": min(resolved.max_probe_chars, v.DEFAULT_MAX_PROBE_CHARS),
              "max_child_routes": min(resolved.max_child_routes, v.DEFAULT_MAX_CHILD_ROUTES)}
    scoped = observation
    if "unit_ids" in route:
        scope = route["unit_ids"]
        if not isinstance(scope, (list, tuple)):
            raise ValueError("policy scope unit_ids must be a sequence")
        scoped = dict(observation)
        scope_ids = set(scope)
        scoped["units"] = [unit for unit in observation.get("units", ()) if unit.get("unit_id") in scope_ids]
    parsed = parse_observation(scoped, capped)
    if "form_type" in route:
        actual = route["form_type"]
        if actual is not None and not isinstance(actual, str):
            raise TypeError("route form_type must be text or None")
        # This is the existing router's resolved signal, not another probe.
        # A present unknown form must not borrow a conflicting metadata claim.
        # An absent field retains the historical wire's metadata interpretation.
        parsed = replace(parsed, form_type=actual if _base_form(actual) else None)
    return parsed


def _choose_family(binding: Mapping, parsed: Observation, route: Mapping) -> tuple[dict | None, list[dict]]:
    family = route.get("family", binding["family"])
    regime = route.get("regime", parsed.regime_claim or binding["regime"])
    form = _base_form(parsed.form_type)
    ranked = []
    for record in _CATALOG["families"]:
        applies = record["applies_to"]
        if "lifecycle_overlay" in applies["purposes"] or applies["family"] != family:
            continue
        if regime not in {None, "unknown"} and regime not in applies["regimes"]:
            continue
        forms = {_base_form(value) for value in applies["forms"]}
        if form and forms and form not in forms:
            continue
        score, hits = _policy_score(record, parsed)
        if family == "unknown" and (score < 6 or hits < 2):
            continue
        # A generic unknown market does not select one market's family by default.
        if regime in {None, "unknown"} and not score and len(applies["regimes"]) == 1:
            continue
        ranked.append((score, record["id"], record))
    if not ranked:
        return None, [{"code": "READING_POLICY_UNKNOWN", "detail": "No applicable evidenced family policy; generic source reading retained."}]
    ranked.sort(key=lambda row: (-row[0], row[1]))
    best_score = ranked[0][0]
    tied = [row for row in ranked if row[0] == best_score]
    if len(tied) > 1:
        return None, [{"code": "READING_POLICY_AMBIGUOUS", "candidate_ids": [row[1] for row in tied],
                       "detail": "Family purpose is ambiguous; do not claim one proposal is source-proven."}]
    return ranked[0][2], []


def _family_state(record: Mapping | None) -> dict:
    if record is None:
        return {"id": None, "design_status": "proposed", "spec_status": "proposed",
                "evidence_status": "missing", "integration_status": "not_integrated",
                "gaps": ["Current purpose not resolved by bounded original evidence."]}
    coverage: Mapping[str, Any] = next((entry for entry in _CATALOG["family_coverage"] if entry["shape"] == record["id"]), {})
    return {"id": record["id"], "design_status": record["evidence_status"]["design"],
            "spec_status": coverage.get("spec_status", "proposed"),
            "evidence_status": coverage.get("evidence_status", "missing"),
            "integration_status": coverage.get("integration_status", "not_integrated"),
            "gaps": deepcopy(coverage.get("gaps", record["evidence_status"]["missing_shapes"]))}


def resolve_reading_profile(profile: Mapping, observation: Mapping, route: Mapping, *, limits: Mapping | None = None) -> dict:
    """Resolve actual family instructions while retaining the existing strong route.

    Only the router's already-bounded original probes participate. Lifecycle values stay
    observational modifiers; allowed-value arrays never set or jointly constrain them.
    Component-local hashes cover adopted instructions, never the entire catalog.
    """
    if not isinstance(profile, Mapping) or not isinstance(route, Mapping):
        raise TypeError("profile and route must be mappings")
    binding = _binding(profile["profile_id"])
    parsed = _bounded_observation(observation, route, limits)
    chosen, diagnostics = _choose_family(binding, parsed, route)
    records = [chosen] if chosen is not None else [_CATALOG["fallback"]]
    modifiers = deepcopy(route.get("modifiers") or {"extent": "unknown", "revision": "unknown"})
    if modifiers.get("extent") == "summary" or modifiers.get("revision") in {"amended", "supplement"}:
        overlay = next(record for record in _CATALOG["families"] if "lifecycle_overlay" in record["applies_to"]["purposes"])
        records.append(overlay)
    components = [_component(record, "modifier" if "lifecycle_overlay" in record.get("applies_to", {}).get("purposes", ())
                             else "family" if "applies_to" in record else "fallback") for record in records]
    sections = _sections(records)
    result = deepcopy(dict(profile))
    result.update({"family": route.get("family", binding["family"]), "regime": route.get("regime", parsed.regime_claim or binding["regime"]),
                   "form_type": parsed.form_type or "unknown",
                   "section_rules": [dict(section, section_role=section["role"]) for section in sections],
                   "section_priorities": _flatten(sections), "summary_focus": _focus(records),
                   "negative_hints": _negative(records), "reading_questions": _questions(records),
                   "context_requirements": _unique([entry for record in records for entry in record["context_requirements"]]),
                   "policy_components": components, "family_policy": _family_state(chosen), "modifiers": modifiers,
                   "policy_probe": {"probed_unit_count": len(parsed.probes), "probed_chars": parsed.probed_chars, "limited": parsed.probe_limited},
                   "policy_diagnostics": diagnostics})
    instruction_payload = {key: result[key] for key in ("section_rules", "summary_focus", "negative_hints",
                                                        "reading_questions", "context_requirements")}
    instruction_payload.update({"components": components, "semantic_units": binding["semantic_units"]})
    result["profile_version"] = f"{binding['profile_id']}/v2+{_digest(instruction_payload)[:16]}"
    return result


def _nonnegative(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def select_business_facets(material: Sequence[Mapping], *, max_facets: int = 4, max_probe_chars: int = 64000) -> list[dict]:
    """Choose reading instructions from actual final original members, never facts.

    Literal signals are hints. Mechanism lists only modify instructions and never infer
    actual billing, stage or quantities. No number is required unless a claim emits it.
    """
    cap = _nonnegative(max_facets, "max_facets")
    budget = min(_nonnegative(max_probe_chars, "max_probe_chars"), v.DEFAULT_MAX_PROBE_CHARS)
    if not isinstance(material, Sequence) or isinstance(material, (str, bytes)):
        raise TypeError("material must be a sequence of original-member mappings")
    if not cap or not budget:
        return []
    originals = []
    for index, member in enumerate(material):
        if not isinstance(member, Mapping):
            raise TypeError("material members must be mappings")
        text = member.get("text", "")
        if text is None:
            text = ""
        if not isinstance(text, str):
            raise TypeError("original member text must be a string")
        originals.append(UnitRef(str(member.get("unit_id") or index), index, member.get("locator"), None,
                                 text, None, None, None, None))
    # Fair bounded materialization reuses the source probe allocator, not a new selector.
    from .observation import _bounded_probe_texts
    probed, _, _ = _bounded_probe_texts(tuple(originals), budget)
    folded_probes = [(unit, _fold(unit.text)) for unit in probed]
    ranked = []
    for facet in _CATALOG["facets"]:
        basis = []
        matches = set()
        signals = [(signal, _fold(signal)) for signal in _unique([signal for evidence in facet["positive_evidence"] for signal in evidence["signals"]])]
        for unit, folded_text in folded_probes:
            hits = [signal for signal, needle in signals if _matches_folded(needle, folded_text)]
            if hits:
                basis.append({"unit_id": unit.unit_id, "matched_signals": hits})
                matches.update(hits)
        if matches:
            ranked.append((-len(matches), facet["id"], facet, basis))
    ranked.sort(key=lambda row: (row[0], row[1]))
    output = []
    for _, _, facet, basis in ranked[:cap]:
        selected = {key: deepcopy(facet[key]) for key in ("id", "version", "business_questions",
                                                        "applicable_mechanisms", "summary_focus",
                                                        "required_context", "absence_rules")}
        # Only universal risk instructions travel; example statements and
        # numbers are not source facts and must never enter a source prompt.
        selected["confusion_checks"] = [
            {"risk": entry["why_wrong"], "required_context_slots": deepcopy(entry["required_context_slots"])}
            for entry in facet.get("confusions", ())]
        selected["content_digest"] = _digest(facet)
        selected["selection_basis"] = basis
        output.append(selected)
    return output


__all__ = ["iter_profiles", "listed_profiles", "profile_by_id", "profile_wire", "resolve_reading_profile", "select_business_facets",
           "configured_table_signal"]
