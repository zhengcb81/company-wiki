"""Compile resolved catalog instructions into a pure geometry request policy.

This module has no routing, matching, file access or page/budget allocation. All
reading choices come from the caller's already resolved catalog sections. Geometry
intent describes requests, never evidence that a table or a business fact exists.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
from typing import Any

from .vocabulary import SECTION_ROLES

SCHEMA_VERSION = "du-geometry-policy/1"
_INTENT_VALUES = {
    "discover": frozenset({"on_tabular_evidence", "context_only", "none", "unknown"}),
    "fine": frozenset({"on_candidate", "explicit_only", "unknown"}),
    "demand_class": frozenset({"operating", "project", "mixed", "context", "administrative", "unknown"}),
}


class GeometryPolicyError(ValueError):
    """Malformed policy input with a stable diagnostic code and bounded detail."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail[:160]}")


def normalize_geometry_intent(value: Any = None) -> dict[str, str]:
    """Validate explicit catalog choices, filling missing choices with unknown.

    No role, priority, company, document title or keyword may invent an intent.
    Used by the existing registry and the public compiler, keeping one validator.
    """
    if value is None:
        value = {}
    if not isinstance(value, Mapping) or set(value) - _INTENT_VALUES.keys():
        raise GeometryPolicyError("GEOMETRY_POLICY_BAD_INTENT", "expected only discover, fine, demand_class")
    output = {}
    for key, choices in _INTENT_VALUES.items():
        actual = value.get(key, "unknown")
        if not isinstance(actual, str) or actual not in choices:
            raise GeometryPolicyError("GEOMETRY_POLICY_BAD_INTENT", f"invalid {key}")
        output[key] = actual
    return output


def _sequence(value: Any, code: str) -> Sequence:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise GeometryPolicyError(code, "expected a sequence")
    return value


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeometryPolicyError(code, "expected nonempty text")
    return value


def _texts(value: Any, code: str) -> list[str]:
    return [_text(item, code) for item in _sequence(value, code)]


def _path(value: Any) -> list[list[str]]:
    code = "GEOMETRY_POLICY_BAD_PATH"
    output = []
    for level in _sequence(value, code):
        alternatives = _texts(level, code)
        if not alternatives:
            raise GeometryPolicyError(code, "a heading level cannot be empty")
        output.append(alternatives)
    return output


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def compile_geometry_policy(resolved_profile: Mapping[str, Any]) -> dict[str, Any]:
    """Return fresh ``du-geometry-policy/1`` JSON from the existing resolved profile.

    Missing instructions stay unknown. Full paths and individual same-role rules
    remain separate; only identical normalized rules are rejected as duplicates.
    The rule key hashes its whole semantic payload, including component origin,
    questions and intent. The profile/component lineage is passed through rather
    than recomputed by another resolver or source identity check.
    """
    if not isinstance(resolved_profile, Mapping):
        raise GeometryPolicyError("GEOMETRY_POLICY_BAD_PROFILE", "expected a resolved profile mapping")
    profile_id = _text(resolved_profile.get("profile_id", "unknown"), "GEOMETRY_POLICY_BAD_PROFILE")
    profile_version = _text(resolved_profile.get("profile_version", "unknown"), "GEOMETRY_POLICY_BAD_PROFILE")
    rules = []
    seen = set()
    for section in _sequence(resolved_profile.get("section_rules", ()), "GEOMETRY_POLICY_BAD_RULES"):
        if not isinstance(section, Mapping):
            raise GeometryPolicyError("GEOMETRY_POLICY_BAD_RULES", "expected section mappings")
        role = section.get("section_role", section.get("role", "unknown"))
        if not isinstance(role, str) or role not in SECTION_ROLES:
            raise GeometryPolicyError("GEOMETRY_POLICY_BAD_ROLE", "invalid section role")
        if "role" in section and section["role"] != role:
            raise GeometryPolicyError("GEOMETRY_POLICY_BAD_ROLE", "role and section_role conflict")
        priority = section.get("priority", 3)
        if type(priority) is not int or priority not in {1, 2, 3}:
            raise GeometryPolicyError("GEOMETRY_POLICY_BAD_PRIORITY", "expected priority 1, 2 or 3")
        rule = {
            "family_id": _text(section.get("family_id", "unknown"), "GEOMETRY_POLICY_BAD_PROFILE"),
            "family_version": _text(section.get("family_version", "unknown"), "GEOMETRY_POLICY_BAD_PROFILE"),
            "section_role": role,
            "heading_path": _path(section.get("heading_path", ())),
            "aliases": _texts(section.get("aliases", ()), "GEOMETRY_POLICY_BAD_ALIASES"),
            "reading_priority": priority,
            "questions": _texts(section.get("questions", ()), "GEOMETRY_POLICY_BAD_QUESTIONS"),
            "geometry_intent": normalize_geometry_intent(section.get("geometry_intent")),
        }
        rule_key = _digest(rule)
        if rule_key in seen:
            raise GeometryPolicyError("GEOMETRY_POLICY_DUPLICATE_RULE", rule_key)
        seen.add(rule_key)
        rules.append(dict(rule, rule_key=rule_key))
    components = resolved_profile.get("policy_components", [])
    if not isinstance(components, (list, tuple)) or any(not isinstance(c, Mapping) for c in components):
        raise GeometryPolicyError("GEOMETRY_POLICY_BAD_COMPONENTS", "expected component mappings")
    try:
        components = json.loads(json.dumps(components, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as error:
        raise GeometryPolicyError("GEOMETRY_POLICY_BAD_COMPONENTS", "expected JSON components") from error
    result = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile_id,
        "profile_version": profile_version,
        "default_intent": normalize_geometry_intent(resolved_profile.get("geometry_default_intent")),
        "rules": rules,
        "policy_components": components,
    }
    return dict(result, content_digest=_digest(result))


__all__ = ["GeometryPolicyError", "compile_geometry_policy", "normalize_geometry_intent"]
