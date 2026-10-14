"""Causal comparison of two decision domains.

``compare_decision_dependencies`` answers exactly one question -- *is the decision this
source's local selection was made from still the same decision?* -- under the same
budget discipline as :func:`~.freeze.freeze_decision_dependencies`.

It is deliberately unable to answer "may I reuse the cached result". ``same`` means the
decision identity matched inside the input it was given. The caller's inventory
completeness, the original bytes and the locator read check remain ROOT's responsibility;
nothing here reads a catalog, a file, a clock or the network.

Error handling mirrors :mod:`.trace` exactly: real data errors -- wrong types, duplicate
ids, dangling references, malformed digests -- propagate as
:class:`~.trace.DecisionTraceError`, while unknown or missing inputs become an explicit
``unavailable`` verdict with diagnostics. Neither can ever be laundered into ``same``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contract import (
    COMPARISON_SCHEMA_VERSION,
    COMPARISON_STATUS_CHANGED,
    COMPARISON_STATUS_SAME,
    COMPARISON_STATUS_UNAVAILABLE,
    FROZEN_SCHEMA_VERSION,
    FROZEN_STATUS_COMPLETE,
    resolve_limits,
)
from .freeze import Budget, freeze_decision_dependencies


def _identity_rows(manifest: Mapping[str, Any]) -> dict[str, Any] | None:
    """Read the identity rows out of a frozen manifest, or None if it is not one."""
    if manifest.get("schema_version") != FROZEN_SCHEMA_VERSION:
        return None
    if manifest.get("status") not in {FROZEN_STATUS_COMPLETE, "partial"}:
        return None
    for key in ("scopes", "components", "candidates"):
        if not isinstance(manifest.get(key), list):
            return None
    if not isinstance(manifest.get("versions"), Mapping):
        return None
    return {
        "status": manifest["status"],
        "scopes": manifest["scopes"],
        "components": manifest["components"],
        "candidates": manifest["candidates"],
        "versions": manifest["versions"],
    }


def _index(rows: list[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    return {str(row.get(key)): row for row in rows}


def _row_identity(row: Mapping[str, Any], key: str) -> str:
    """Everything about a row except its position in an array."""
    payload = {name: value for name, value in row.items() if name != key}
    for name in ("scope_ids", "component_ids"):
        values = payload.get(name)
        if isinstance(values, list):
            payload[name] = sorted(str(item) for item in values)
    return repr(sorted(payload.items(), key=lambda item: str(item[0])))


def _result(
    status: str,
    components: list[str],
    added: list[str],
    removed: list[str],
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "status": status,
        "changed_component_ids": components,
        "added_candidate_ids": added,
        "removed_candidate_ids": removed,
        "diagnostics": diagnostics,
    }


def _unavailable(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    return _result(COMPARISON_STATUS_UNAVAILABLE, [], [], [], diagnostics)


def compare_decision_dependencies(
    frozen: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    limits: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare a frozen decision manifest with the current decision domain.

    ``frozen`` is a ``du-decision-dependencies/1`` manifest. ``current`` is either a
    ``du-decision-dependencies/1`` manifest (for example a compact trace stored with an
    earlier generation) or a ``du-decision-trace/1`` trace from the live router. The two
    are told apart by ``schema_version``, never by guessing at the content.

    The result is ``same``, ``changed`` or ``unavailable``. ``changed`` lists the
    component ids whose inspected content or matcher digest moved, plus the candidate
    membership delta; reordering an array is not a change. ``unavailable`` means the
    question cannot be answered honestly -- a legacy artefact, an incomplete inventory or
    an exhausted budget -- and it never degrades into ``same``.
    """
    diagnostics: list[dict[str, Any]] = []

    if not isinstance(frozen, Mapping):
        return _unavailable(
            [
                {
                    "code": "FROZEN_NOT_A_MAPPING",
                    "detail": f"frozen must be a mapping, got {type(frozen).__name__}",
                }
            ]
        )

    frozen_identity = _identity_rows(frozen)
    if frozen_identity is None:
        return _unavailable(
            [
                {
                    "code": "FROZEN_NOT_A_DECISION_MANIFEST",
                    "detail": (
                        f"frozen must be a {FROZEN_SCHEMA_VERSION} manifest; an artefact of an "
                        "earlier scheme (for example a read-policy fingerprint or an adopted "
                        "component list) may be replayed elsewhere but cannot support a decision "
                        "comparison, so it is never read as 'unchanged'"
                    ),
                }
            ]
        )

    if frozen_identity["status"] != FROZEN_STATUS_COMPLETE:
        diagnostics.append(
            {
                "code": "FROZEN_PARTIAL",
                "detail": (
                    "the frozen manifest is partial, so it carries lineage only and is not reuse "
                    "evidence"
                ),
            }
        )

    # Which side is which is decided by schema_version alone.
    if isinstance(current, Mapping) and current.get("schema_version") == FROZEN_SCHEMA_VERSION:
        current_identity = _identity_rows(current)
        if current_identity is None:
            return _unavailable(
                diagnostics
                + [
                    {
                        "code": "CURRENT_MALFORMED_MANIFEST",
                        "detail": "current claims the frozen schema but is not a valid manifest",
                    }
                ]
            )
        if current_identity["status"] != FROZEN_STATUS_COMPLETE:
            diagnostics.append(
                {
                    "code": "CURRENT_PARTIAL",
                    "detail": (
                        "the current manifest is partial, so it carries lineage only and is not "
                        "reuse evidence"
                    ),
                }
            )
    else:
        # A trace (or the absence of one) on the current side. Real data errors inside a
        # declared du-decision-trace/1 propagate; an absent or legacy trace is reported.
        current_manifest = freeze_decision_dependencies(current, limits=limits)
        if current_manifest["status"] != FROZEN_STATUS_COMPLETE:
            codes = [
                item.get("code")
                for item in current_manifest.get("diagnostics", ())
                if isinstance(item, Mapping)
            ]
            diagnostics.append(
                {
                    "code": "CURRENT_TRACE_NOT_FREEZABLE",
                    "detail": (
                        "the current trace froze as "
                        f"{current_manifest.get('status')} ({codes or 'no diagnostic'}), so no "
                        "reuse verdict is issued"
                    ),
                }
            )
        current_identity = {
            "status": current_manifest["status"],
            "scopes": current_manifest["scopes"],
            "components": current_manifest["components"],
            "candidates": current_manifest["candidates"],
            "versions": current_manifest["versions"],
        }

    # Any blocking condition means the honest answer is "cannot say", never "same".
    if diagnostics:
        return _unavailable(diagnostics)

    effective, limits_error = resolve_limits(limits)
    if limits_error is not None:
        raise ValueError(f"{limits_error['code']}: {limits_error['detail']}")
    budget = Budget(effective)

    frozen_components = _index(frozen_identity["components"], "component_id")
    current_components = _index(current_identity["components"], "component_id")

    changed: list[str] = []
    for component_id in sorted(set(frozen_components) | set(current_components)):
        budget.charge()
        if budget.exhausted:
            return _unavailable([_budget_diagnostic(budget, effective)])
        before = frozen_components.get(component_id)
        after = current_components.get(component_id)
        if before is None or after is None:
            changed.append(component_id)
        elif _row_identity(before, "component_id") != _row_identity(after, "component_id"):
            changed.append(component_id)

    frozen_candidates = _index(frozen_identity["candidates"], "candidate_id")
    current_candidates = _index(current_identity["candidates"], "candidate_id")
    added = sorted(set(current_candidates) - set(frozen_candidates))
    removed = sorted(set(frozen_candidates) - set(current_candidates))

    membership_changed: list[dict[str, Any]] = []
    for candidate_id in sorted(set(frozen_candidates) & set(current_candidates)):
        budget.charge()
        if budget.exhausted:
            return _unavailable([_budget_diagnostic(budget, effective)])
        before = frozen_candidates[candidate_id]
        after = current_candidates[candidate_id]
        if _row_identity(before, "candidate_id") != _row_identity(after, "candidate_id"):
            membership_changed.append(
                {
                    "code": "CANDIDATE_MEMBERSHIP_CHANGED",
                    "candidate_ids": [candidate_id],
                    "detail": (
                        "this candidate's scope, component membership or eligibility changed, so "
                        "the decision could select differently even though no component moved"
                    ),
                }
            )

    frozen_scopes = _index(frozen_identity["scopes"], "scope_id")
    current_scopes = _index(current_identity["scopes"], "scope_id")
    scope_changed: list[dict[str, Any]] = []
    for scope_id in sorted(set(frozen_scopes) | set(current_scopes)):
        budget.charge()
        if budget.exhausted:
            return _unavailable([_budget_diagnostic(budget, effective)])
        before = frozen_scopes.get(scope_id)
        after = current_scopes.get(scope_id)
        if (
            before is None
            or after is None
            or _row_identity(before, "scope_id") != _row_identity(after, "scope_id")
        ):
            scope_changed.append(
                {
                    "code": "SCOPE_CHANGED",
                    "scope_ids": [scope_id],
                    "detail": (
                        "this decision scope was added, removed or changed; it is part of the "
                        "decision identity even when no component digest moved"
                    ),
                }
            )

    versions_changed: list[dict[str, Any]] = []
    frozen_versions = dict(frozen_identity["versions"])
    current_versions = dict(current_identity["versions"])
    if frozen_versions != current_versions:
        budget.charge()
        if budget.exhausted:
            return _unavailable([_budget_diagnostic(budget, effective)])
        moved = sorted(
            key
            for key in set(frozen_versions) | set(current_versions)
            if frozen_versions.get(key, object()) != current_versions.get(key, object())
        )
        versions_changed.append(
            {
                "code": "ALGORITHM_VERSION_CHANGED",
                "detail": f"adopted algorithm versions differ for {moved}",
            }
        )

    if changed or added or removed or membership_changed or scope_changed or versions_changed:
        return _result(
            COMPARISON_STATUS_CHANGED,
            changed,
            added,
            removed,
            membership_changed + scope_changed + versions_changed,
        )

    return _result(COMPARISON_STATUS_SAME, [], [], [], [])


def _budget_diagnostic(budget: Budget, limits: Mapping[str, int]) -> dict[str, Any]:
    limit = budget.stopped_by or "max_work_units"
    return {
        "code": "WORK_LIMIT_REACHED" if limit == "max_work_units" else "BYTES_LIMIT_REACHED",
        "detail": (
            f"{limit}={limits[limit]} reached while diffing the decision inventory; the comparison "
            "stopped here and no verdict is issued"
        ),
    }
