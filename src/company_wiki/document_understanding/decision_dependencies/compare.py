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
    BYTES_PER_ROW_ENVELOPE,
    COMPARISON_SCHEMA_VERSION,
    COMPARISON_STATUS_CHANGED,
    COMPARISON_STATUS_SAME,
    COMPARISON_STATUS_UNAVAILABLE,
    FROZEN_CANDIDATE_KEYS,
    FROZEN_COMPONENT_KEYS,
    FROZEN_KEYS,
    FROZEN_SCOPE_KEYS,
    FROZEN_SCHEMA_VERSION,
    FROZEN_STATUS_COMPLETE,
    Budget,
    resolve_limits,
)
from .freeze import decision_digest, freeze_decision_dependencies


_SHA256_HEX = frozenset("0123456789abcdef")


def _full_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and not isinstance(value, bool)
        and len(value) == 64
        and set(value) <= _SHA256_HEX
    )


def _reference_names(value: Any) -> list[str] | None:
    """A list of unique non-empty strings, or None if the value is not one."""
    if not isinstance(value, list):
        return None
    names: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or item in names:
            return None
        names.append(item)
    return names


def _manifest_problem(manifest: Mapping[str, Any]) -> str | None:
    """Everything wrong with a manifest's *content*, as a reason string.

    ``compare`` treats a stored manifest as a record, not as a caller assertion, so a
    problem here is reported rather than raised. It is still never silently repaired:
    duplicate ids, dangling references, repeated references, malformed digests and wrong
    types all make the manifest unusable, and an unusable manifest is ``unavailable`` --
    never ``same``. Left unchecked these would let a malformed record read as unchanged.
    """
    expected = {
        "scopes": FROZEN_SCOPE_KEYS,
        "components": FROZEN_COMPONENT_KEYS,
        "candidates": FROZEN_CANDIDATE_KEYS,
    }
    identifiers: dict[str, set[str]] = {}
    for key, allowed in expected.items():
        rows = manifest[key]
        seen: set[str] = set()
        identity_key = {"scopes": "scope_id", "components": "component_id",
                        "candidates": "candidate_id"}[key]
        for index, row in enumerate(rows):
            where = f"{key}[{index}]"
            for name in allowed:
                if name in (identity_key, "version"):
                    value = row[name]
                    if not isinstance(value, str) or isinstance(value, bool) or not value:
                        return f"{where}.{name} must be a non-empty string"
                elif name in ("content_digest", "matcher_digest"):
                    if not _full_digest(row[name]):
                        return f"{where}.{name} must be a full 64-character lowercase SHA-256"
                elif name in ("scope_ids", "component_ids"):
                    if _reference_names(row[name]) is None:
                        return f"{where}.{name} must be an array of unique non-empty strings"
                elif name == "eligible":
                    if not isinstance(row[name], bool):
                        return f"{where}.eligible must be a boolean"
            identity = row[identity_key]
            if identity in seen:
                return (
                    f"{where} repeats {identity!r}; duplicate ids are a caller error, not "
                    f"something to collapse"
                )
            seen.add(identity)
        identifiers[key] = seen

    for row in manifest["components"]:
        for name in row["scope_ids"]:
            if name not in identifiers["scopes"]:
                return f"component {row['component_id']!r} references unknown scope {name!r}"
    for row in manifest["candidates"]:
        if row["scope_id"] not in identifiers["scopes"]:
            return f"candidate {row['candidate_id']!r} references unknown scope {row['scope_id']!r}"
        for name in row["component_ids"]:
            if name not in identifiers["components"]:
                return f"candidate {row['candidate_id']!r} references unknown component {name!r}"

    seen_versions: set[str] = set()
    for name, value in manifest["versions"].items():
        if not isinstance(name, str) or not name:
            return "versions keys must be non-empty strings"
        if name in seen_versions:
            return f"versions repeats key {name!r}"
        seen_versions.add(name)
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            return f"versions[{name!r}] must be a string or integer version"
    return None


def _identity_rows(manifest: Mapping[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Read the identity rows out of a frozen manifest.

    Returns ``(rows, None)`` for a valid manifest and ``(None, reason)`` otherwise. The
    key sets are checked exactly: an unknown field is an item this version does not
    understand, and DU3/1 requires unknown items to come back as an explicit diagnostic
    rather than being dropped on the floor. Dropping one could hide the very change the
    caller is asking about.
    """
    if manifest.get("schema_version") != FROZEN_SCHEMA_VERSION:
        return None, f"frozen must declare {FROZEN_SCHEMA_VERSION}"
    if manifest.get("status") not in {FROZEN_STATUS_COMPLETE, "partial"}:
        return None, f"frozen status {manifest.get('status')!r} is not complete|partial"
    unknown = sorted(set(manifest) - FROZEN_KEYS)
    if unknown:
        return None, f"frozen carries fields this contract does not define: {unknown}"
    missing = sorted(FROZEN_KEYS - set(manifest))
    if missing:
        return None, f"frozen is missing contract fields: {missing}"
    if not isinstance(manifest.get("diagnostics"), list):
        return None, "frozen diagnostics must be an array"
    expected = {
        "scopes": FROZEN_SCOPE_KEYS,
        "components": FROZEN_COMPONENT_KEYS,
        "candidates": FROZEN_CANDIDATE_KEYS,
    }
    for key, allowed in expected.items():
        rows = manifest.get(key)
        if not isinstance(rows, list):
            return None, f"frozen {key} must be an array"
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                return None, f"frozen {key}[{index}] must be a mapping"
            row_unknown = sorted(set(row) - allowed)
            if row_unknown:
                return None, f"frozen {key}[{index}] carries undefined fields: {row_unknown}"
            row_missing = sorted(allowed - set(row))
            if row_missing:
                return None, f"frozen {key}[{index}] is missing contract fields: {row_missing}"
    if not isinstance(manifest.get("versions"), Mapping):
        return None, "frozen versions must be a mapping"
    problem = _manifest_problem(manifest)
    if problem is not None:
        return None, problem
    # The manifest carries its own identity. A digest that no longer matches its rows is
    # a stale or edited record, and an edited record must never read as unchanged.
    recorded = manifest.get("decision_digest")
    if not _full_digest(recorded):
        return None, "frozen decision_digest must be a full 64-character lowercase SHA-256"
    try:
        recomputed = decision_digest(manifest)
    except (TypeError, ValueError) as error:
        return None, f"frozen decision_digest cannot be recomputed: {error}"
    if recorded != recomputed:
        return None, "frozen decision_digest does not match its own rows; the record is stale or edited"
    return {
        "status": manifest["status"],
        "scopes": manifest["scopes"],
        "components": manifest["components"],
        "candidates": manifest["candidates"],
        "versions": manifest["versions"],
    }, None


def _spend_row(budget: Budget, row: Mapping[str, Any]) -> bool:
    """Charge one row and its nested references against the budget.

    Every row and every element inside a reference list is charged, so diffing a wide
    inventory cannot run past ``max_work_units`` or ``max_input_bytes`` while the caller
    believes the call was bounded.
    """
    if not budget.charge():
        return False
    for value in row.values():
        if isinstance(value, str) and not budget.charge_text(value):
            return False
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and not budget.charge_text(item):
                    return False
    return budget.charge_bytes(BYTES_PER_ROW_ENVELOPE)


def _index(
    rows: list[Mapping[str, Any]],
    key: str,
    budget: Budget,
) -> dict[str, Mapping[str, Any]] | None:
    """Index rows by id, charging every row against the budget.

    Returns ``None`` when the budget runs out: an index built past ``max_work_units`` is
    work the caller never authorised, and a half-built index must not reach a verdict.
    """
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not _spend_row(budget, row):
            return None
        indexed[str(row.get(key))] = row
    return indexed


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

    # Validate the caller's limits before any verdict path, so a malformed limits mapping
    # is a caller error on every route rather than only on the ones that reach the diff.
    effective, limits_error = resolve_limits(limits)
    if limits_error is not None:
        raise ValueError(f"{limits_error['code']}: {limits_error['detail']}")

    if not isinstance(frozen, Mapping):
        return _unavailable(
            [
                {
                    "code": "FROZEN_NOT_A_MAPPING",
                    "detail": f"frozen must be a mapping, got {type(frozen).__name__}",
                }
            ]
        )

    frozen_identity, frozen_reason = _identity_rows(frozen)
    if frozen_identity is None:
        return _unavailable(
            [
                {
                    "code": "FROZEN_NOT_A_DECISION_MANIFEST",
                    "detail": (
                        f"{frozen_reason}; an artefact of an earlier scheme (for example a "
                        "read-policy fingerprint or an adopted component list) may be replayed "
                        "elsewhere but cannot support a decision comparison, so it is never read "
                        "as 'unchanged'"
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
        current_identity, current_reason = _identity_rows(current)
        if current_identity is None:
            return _unavailable(
                diagnostics
                + [
                    {
                        "code": "CURRENT_MALFORMED_MANIFEST",
                        "detail": f"current claims the frozen schema but is not a valid manifest: {current_reason}",
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

    budget = Budget(effective)

    frozen_components = _index(frozen_identity["components"], "component_id", budget)
    if frozen_components is None:
        return _unavailable([_budget_diagnostic(budget, effective)])
    current_components = _index(current_identity["components"], "component_id", budget)
    if current_components is None:
        return _unavailable([_budget_diagnostic(budget, effective)])

    changed: list[str] = []
    component_ids = sorted(set(frozen_components) | set(current_components))
    if not budget.charge(len(component_ids)):
        return _unavailable([_budget_diagnostic(budget, effective)])
    for component_id in component_ids:
        before = frozen_components.get(component_id)
        after = current_components.get(component_id)
        for row in (before, after):
            if row is not None and not _spend_row(budget, row):
                return _unavailable([_budget_diagnostic(budget, effective)])
        if before is None or after is None:
            changed.append(component_id)
        elif _row_identity(before, "component_id") != _row_identity(after, "component_id"):
            changed.append(component_id)

    frozen_candidates = _index(frozen_identity["candidates"], "candidate_id", budget)
    if frozen_candidates is None:
        return _unavailable([_budget_diagnostic(budget, effective)])
    current_candidates = _index(current_identity["candidates"], "candidate_id", budget)
    if current_candidates is None:
        return _unavailable([_budget_diagnostic(budget, effective)])
    added = sorted(set(current_candidates) - set(frozen_candidates))
    removed = sorted(set(frozen_candidates) - set(current_candidates))
    if not budget.charge(len(added) + len(removed) + len(current_candidates) + len(frozen_candidates)):
        return _unavailable([_budget_diagnostic(budget, effective)])

    membership_changed: list[dict[str, Any]] = []
    for candidate_id in sorted(set(frozen_candidates) & set(current_candidates)):
        before = frozen_candidates[candidate_id]
        after = current_candidates[candidate_id]
        for row in (before, after):
            if not _spend_row(budget, row):
                return _unavailable([_budget_diagnostic(budget, effective)])
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

    frozen_scopes = _index(frozen_identity["scopes"], "scope_id", budget)
    if frozen_scopes is None:
        return _unavailable([_budget_diagnostic(budget, effective)])
    current_scopes = _index(current_identity["scopes"], "scope_id", budget)
    if current_scopes is None:
        return _unavailable([_budget_diagnostic(budget, effective)])
    scope_changed: list[dict[str, Any]] = []
    scope_ids = sorted(set(frozen_scopes) | set(current_scopes))
    if not budget.charge(len(scope_ids)):
        return _unavailable([_budget_diagnostic(budget, effective)])
    for scope_id in scope_ids:
        before = frozen_scopes.get(scope_id)
        after = current_scopes.get(scope_id)
        for row in (before, after):
            if row is not None and not _spend_row(budget, row):
                return _unavailable([_budget_diagnostic(budget, effective)])
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
        if not budget.charge():
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
