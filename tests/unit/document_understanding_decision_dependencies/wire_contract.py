"""Public wire contract for ``company_wiki.document_understanding.decision_dependencies``.

Frozen by ``docs/plans/document-understanding-2026-10-13/parallel/du3-2026-10-14/
INTERFACES.md`` section "决策依赖组件" (DU3/1). This module states the contract only;
it restates no comparison expectation and computes no digest.

The package under test is obtained through :func:`import_decision_module` rather than a
pytest fixture: an imported fixture whose name is also a test parameter trips ruff's
``F811`` redefinition check, so the import is expressed as an ordinary function.
"""

from __future__ import annotations

from typing import Any

TRACE_SCHEMA = "du-decision-trace/1"
FROZEN_SCHEMA = "du-decision-dependencies/1"
COMPARISON_SCHEMA = "du-decision-comparison/1"

TRACE_KEYS = {"schema_version", "scopes", "components", "candidates", "versions", "inventory_complete"}
SCOPE_KEYS = {"scope_id", "regime", "family", "form_type", "purpose"}
COMPONENT_KEYS = {"component_id", "version", "content_digest", "matcher_digest", "scope_ids"}
CANDIDATE_KEYS = {"candidate_id", "scope_id", "component_ids", "eligible"}

FROZEN_KEYS = {
    "schema_version",
    "status",
    "scopes",
    "components",
    "candidates",
    "versions",
    "decision_digest",
    "diagnostics",
}
FROZEN_SCOPE_KEYS = {"scope_id", "regime", "family", "form_type", "purpose"}
FROZEN_COMPONENT_KEYS = {"component_id", "version", "content_digest", "matcher_digest", "scope_ids"}
FROZEN_CANDIDATE_KEYS = {"candidate_id", "scope_id", "component_ids", "eligible"}

COMPARISON_KEYS = {
    "schema_version",
    "status",
    "changed_component_ids",
    "added_candidate_ids",
    "removed_candidate_ids",
    "diagnostics",
}

STATUSES = {"complete", "partial"}
COMPARISON_STATUSES = {"same", "changed", "unavailable"}

#: Fields that are never content identity, so they must not appear anywhere in the
#: frozen manifest or in a comparison result.
FORBIDDEN_FIELD_NAMES = {
    "timestamp",
    "time",
    "now",
    "run_id",
    "run",
    "job_id",
    "path",
    "absolute_path",
    "file_path",
    "relative_path",
    "cost",
    "cost_usd",
    "price",
    "pricing",
    "timeout",
    "timeout_seconds",
    "api_key",
    "apikey",
    "api_key_env",
    "env",
    "env_name",
    "environment",
    "dom",
    "html",
    "raw_text",
    "text",
    "content",
    "policy_body",
    "all_units",
    "units",
}

DEFAULT_LIMITS = {
    "max_scopes": 64,
    "max_components": 512,
    "max_candidates": 4096,
    "max_input_bytes": 2 * 1024 * 1024,
    "max_work_units": 200_000,
}


def import_decision_module():
    """Return the package under test; a missing entry point is a real RED failure."""
    import company_wiki.document_understanding.decision_dependencies as module

    return module


def assert_frozen_shape(frozen: Any) -> None:
    """Structural assertions shared by every freeze test."""
    assert isinstance(frozen, dict), f"frozen must be a dict, got {type(frozen)!r}"
    missing = FROZEN_KEYS - set(frozen)
    assert not missing, f"frozen missing frozen keys: {sorted(missing)}"
    assert frozen["schema_version"] == FROZEN_SCHEMA
    assert frozen["status"] in STATUSES
    assert isinstance(frozen["decision_digest"], str)
    assert isinstance(frozen["diagnostics"], list)
    for item in frozen["scopes"]:
        assert set(item) == FROZEN_SCOPE_KEYS, item
    for item in frozen["components"]:
        assert set(item) == FROZEN_COMPONENT_KEYS, item
        assert isinstance(item["scope_ids"], list)
    for item in frozen["candidates"]:
        assert set(item) == FROZEN_CANDIDATE_KEYS, item
        assert isinstance(item["eligible"], bool)


def assert_comparison_shape(result: Any) -> None:
    """Structural assertions shared by every compare test."""
    assert isinstance(result, dict), f"comparison must be a dict, got {type(result)!r}"
    missing = COMPARISON_KEYS - set(result)
    assert not missing, f"comparison missing frozen keys: {sorted(missing)}"
    assert result["schema_version"] == COMPARISON_SCHEMA
    assert result["status"] in COMPARISON_STATUSES, result["status"]
    for key in ("changed_component_ids", "added_candidate_ids", "removed_candidate_ids"):
        assert isinstance(result[key], list), key
        assert all(isinstance(value, str) for value in result[key]), key
        assert len(result[key]) == len(set(result[key])), key


def walk_scalars(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Every string scalar in a JSON-shaped value, with a dotted path."""
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            found.extend(walk_scalars(item, f"{prefix}.{key}" if prefix else str(key)))
            found.append((f"{prefix}.{key}@key" if prefix else f"{key}@key", str(key)))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found.extend(walk_scalars(item, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        found.append((prefix, value))
    return found


def keys_of(value: Any) -> set[str]:
    """Every mapping key anywhere in a JSON-shaped value."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(str(key))
            found |= keys_of(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            found |= keys_of(item)
    return found
