"""Budgeted freeze of a decision domain into a ``du-decision-dependencies/1`` manifest.

Two properties drive the design:

* **Work is charged on every pass.** A budget that only counted the input size would not
  stop an implementation that walks the inventory repeatedly, so every pass over a scope,
  a component or a candidate is charged again against ``max_work_units``.
* **A truncated walk never becomes a complete graph.** When a limit stops the freeze, the
  result is ``partial`` with a diagnostic naming the limit. It keeps whatever identity it
  legitimately saw, and it can never be the basis of a ``same`` verdict.

The manifest holds identity only: full SHA-256 digests, ids, versions and the algorithm
versions actually adopted. No path, run id, timestamp, cost, timeout or API-key name is
representable -- the key set is closed -- and no document text, policy body, DOM or unit
list is stored.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .contract import (
    BYTES_PER_ROW_ENVELOPE,
    FROZEN_SCHEMA_VERSION,
    FROZEN_STATUS_COMPLETE,
    FROZEN_STATUS_PARTIAL,
    WORK_PER_SCOPE,
    WORK_UNIT,
    resolve_limits,
)
from .trace import DecisionTrace, decode_trace

_DIGEST_MARKER = "du-decision-dependencies/1"


class Budget:
    """Charges work units and canonical bytes; reports the first limit it hit."""

    __slots__ = ("bytes_used", "limits", "stopped_by", "work_used")

    def __init__(self, limits: Mapping[str, int]) -> None:
        self.limits = limits
        self.work_used = 0
        self.bytes_used = 0
        self.stopped_by: str | None = None

    def charge(self, units: int = WORK_UNIT) -> bool:
        """Charge work; return False once the budget is exhausted."""
        if self.stopped_by is not None:
            return False
        self.work_used += units
        if self.work_used > self.limits["max_work_units"]:
            self.stopped_by = "max_work_units"
            return False
        return True

    def charge_text(self, text: str) -> bool:
        """Charge canonical bytes for a string the manifest will have to carry."""
        if self.stopped_by is not None:
            return False
        self.bytes_used += len(text.encode("utf-8"))
        if self.bytes_used > self.limits["max_input_bytes"]:
            self.stopped_by = "max_input_bytes"
            return False
        return True

    def charge_bytes(self, count: int) -> bool:
        if self.stopped_by is not None:
            return False
        self.bytes_used += count
        if self.bytes_used > self.limits["max_input_bytes"]:
            self.stopped_by = "max_input_bytes"
            return False
        return True

    @property
    def exhausted(self) -> bool:
        return self.stopped_by is not None


_LIMIT_CODES: dict[str, str] = {
    "max_work_units": "WORK_LIMIT_REACHED",
    "max_input_bytes": "BYTES_LIMIT_REACHED",
    "max_scopes": "SCOPES_LIMIT_REACHED",
    "max_components": "COMPONENTS_LIMIT_REACHED",
    "max_candidates": "CANDIDATES_LIMIT_REACHED",
}


def _limit_diagnostic(limit: str, allowed: int, observed: int) -> dict[str, Any]:
    code = _LIMIT_CODES.get(limit, f"{limit.upper()}_REACHED")
    return {
        "code": code,
        "detail": (
            f"{limit}={allowed} reached ({observed} observed); the freeze stopped here and "
            "the manifest is partial, so it is not reuse evidence"
        ),
    }


def canonical_json(value: Any) -> str:
    """The one canonical encoding used for digests and byte accounting."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _digest_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _freeze_scopes(trace: DecisionTrace, budget: Budget) -> tuple[list[dict[str, Any]], bool]:
    allowed = budget.limits["max_scopes"]
    kept: list[dict[str, Any]] = []
    complete = True
    for scope in trace.scopes:
        if len(kept) >= allowed:
            budget.charge()
            complete = False
            budget.stopped_by = budget.stopped_by or "max_scopes"
            break
        budget.charge(WORK_PER_SCOPE)
        if budget.exhausted:
            complete = False
            break
        if not budget.charge_text(scope["scope_id"] + scope["regime"] + scope["family"] + scope["purpose"]):
            complete = False
            break
        if not budget.charge_bytes(BYTES_PER_ROW_ENVELOPE):
            complete = False
            break
        kept.append(
            {
                "scope_id": scope["scope_id"],
                "regime": scope["regime"],
                "family": scope["family"],
                "form_type": scope["form_type"],
                "purpose": scope["purpose"],
            }
        )
    return kept, complete


def _freeze_components(trace: DecisionTrace, budget: Budget) -> tuple[list[dict[str, Any]], bool]:
    allowed = budget.limits["max_components"]
    kept: list[dict[str, Any]] = []
    complete = True
    for component in trace.components:
        if len(kept) >= allowed:
            complete = False
            budget.stopped_by = budget.stopped_by or "max_components"
            break
        budget.charge()
        if budget.exhausted:
            complete = False
            break
        if not budget.charge_text(component["component_id"] + component["version"]):
            complete = False
            break
        if not budget.charge_bytes(BYTES_PER_ROW_ENVELOPE):
            complete = False
            break
        kept.append(
            {
                "component_id": component["component_id"],
                "version": component["version"],
                "content_digest": component["content_digest"],
                "matcher_digest": component["matcher_digest"],
                "scope_ids": list(component["scope_ids"]),
            }
        )
    return kept, complete


def _freeze_candidates(trace: DecisionTrace, budget: Budget) -> tuple[list[dict[str, Any]], bool]:
    allowed = budget.limits["max_candidates"]
    kept: list[dict[str, Any]] = []
    complete = True
    for candidate in trace.candidates:
        if len(kept) >= allowed:
            complete = False
            budget.stopped_by = budget.stopped_by or "max_candidates"
            break
        budget.charge()
        if budget.exhausted:
            complete = False
            break
        if not budget.charge_text(candidate["candidate_id"] + candidate["scope_id"]):
            complete = False
            break
        for component_id in candidate["component_ids"]:
            budget.charge()
            if budget.exhausted:
                complete = False
                break
            if not budget.charge_text(component_id):
                complete = False
                break
        if not complete:
            break
        if not budget.charge_bytes(BYTES_PER_ROW_ENVELOPE):
            complete = False
            break
        kept.append(
            {
                "candidate_id": candidate["candidate_id"],
                "scope_id": candidate["scope_id"],
                "component_ids": list(candidate["component_ids"]),
                "eligible": candidate["eligible"],
            }
        )
    return kept, complete


def _freeze_versions(trace: DecisionTrace, budget: Budget) -> tuple[dict[str, Any], bool]:
    versions: dict[str, Any] = {}
    complete = True
    for key, value in trace.versions.items():
        budget.charge()
        if budget.exhausted:
            complete = False
            break
        if not budget.charge_text(key + str(value)):
            complete = False
            break
        versions[key] = value
    return versions, complete


def _inventory_error(trace: DecisionTrace) -> dict[str, Any] | None:
    """A freeze that cannot see the whole decision may not be complete.

    The input-level diagnostic explains *why the caller's inventory is short*; this one
    explains *why the manifest is partial*, which is what a consumer must check before
    treating the freeze as reuse evidence.
    """
    if not trace.inventory_complete:
        return {
            "code": "INVENTORY_NOT_COMPLETE",
            "detail": (
                "the caller did not assert a complete inventory; partial freezes carry identity "
                "for lineage but are not reuse evidence"
            ),
        }
    return None


def freeze_decision_dependencies(
    trace: Mapping[str, Any], *, limits: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Freeze one source's decision domain into a stable, order-independent manifest.

    ``trace`` is the caller's ``du-decision-trace/1`` mapping: this source's decision
    scopes, every component it actually inspected (including unmatched and losing ones),
    the full candidate membership with eligibility, and the algorithm versions adopted.

    The result is JSON-serializable and deterministic. ``status`` is ``complete`` only
    when the input declared this contract, was attested complete by the caller, recorded
    at least one candidate, and was walked to the end within the budget. Every other case
    is ``partial`` with diagnostics, and ``partial`` never provides reuse evidence.
    """
    effective, limits_error = resolve_limits(limits)
    if limits_error is not None:
        # A bad limits mapping is a caller error, not a silent downgrade.
        raise ValueError(f"{limits_error['code']}: {limits_error['detail']}")

    trace_domain = decode_trace(trace)

    diagnostics: list[dict[str, Any]] = [dict(item) for item in trace_domain.diagnostics]
    budget = Budget(effective)

    result_scopes, scopes_complete = _freeze_scopes(trace_domain, budget)
    if scopes_complete:
        result_components, components_complete = _freeze_components(trace_domain, budget)
    else:
        result_components, components_complete = [], False
    if scopes_complete and components_complete:
        result_candidates, candidates_complete = _freeze_candidates(trace_domain, budget)
    else:
        result_candidates, candidates_complete = [], False
    if scopes_complete and components_complete and candidates_complete:
        result_versions, versions_complete = _freeze_versions(trace_domain, budget)
    else:
        result_versions, versions_complete = {}, False

    if budget.stopped_by is not None:
        observed = {
            "max_work_units": budget.work_used,
            "max_input_bytes": budget.bytes_used,
            "max_scopes": len(result_scopes),
            "max_components": len(result_components),
            "max_candidates": len(result_candidates),
        }.get(budget.stopped_by, budget.work_used)
        diagnostics.append(
            _limit_diagnostic(
                budget.stopped_by, effective[budget.stopped_by], observed
            )
        )

    walked = (
        len(result_scopes) == len(trace_domain.scopes)
        and len(result_components) == len(trace_domain.components)
        and len(result_candidates) == len(trace_domain.candidates)
        and len(result_versions) == len(trace_domain.versions)
    )
    complete = bool(
        walked
        and scopes_complete
        and components_complete
        and candidates_complete
        and versions_complete
        and trace_domain.can_be_complete
    )

    if not complete:
        inventory_error = _inventory_error(trace_domain)
        if inventory_error is not None:
            diagnostics.append(inventory_error)

    manifest: dict[str, Any] = {
        "schema_version": FROZEN_SCHEMA_VERSION,
        "status": FROZEN_STATUS_COMPLETE if complete else FROZEN_STATUS_PARTIAL,
        "scopes": result_scopes,
        "components": result_components,
        "candidates": result_candidates,
        "versions": result_versions,
        "diagnostics": diagnostics,
    }
    manifest["decision_digest"] = decision_digest(manifest)
    return manifest


def decision_digest(manifest: Mapping[str, Any]) -> str:
    """Digest the identity-bearing part of a manifest.

    Everything except ``status``, ``diagnostics`` and the digest itself. Diagnostics
    describe *why* a freeze stopped, and the same decision reached with a larger budget
    must keep the same identity; the status is a verdict about completeness, not content.
    """
    payload = {
        "schema_version": manifest.get("schema_version"),
        "scopes": manifest.get("scopes", []),
        "components": manifest.get("components", []),
        "candidates": manifest.get("candidates", []),
        "versions": manifest.get("versions", {}),
    }
    return _digest_payload(payload)
