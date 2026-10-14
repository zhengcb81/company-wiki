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
from typing import Any, Mapping

from .contract import (
    BYTES_PER_ROW_ENVELOPE,
    FROZEN_SCHEMA_VERSION,
    FROZEN_STATUS_COMPLETE,
    FROZEN_STATUS_PARTIAL,
    WORK_PER_SCOPE,
    Budget,
    canonical_json,
    encoded_bytes,
    resolve_limits,
)
from .trace import DecisionTrace, decode_trace


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
        row = {
            "scope_id": scope["scope_id"],
            "regime": scope["regime"],
            "family": scope["family"],
            "form_type": scope["form_type"],
            "purpose": scope["purpose"],
        }
        if not budget.charge_bytes(encoded_bytes(row) + BYTES_PER_ROW_ENVELOPE):
            complete = False
            break
        kept.append(row)
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
        row = {
            "component_id": component["component_id"],
            "version": component["version"],
            "content_digest": component["content_digest"],
            "matcher_digest": component["matcher_digest"],
            "scope_ids": list(component["scope_ids"]),
        }
        if not budget.charge_bytes(encoded_bytes(row) + BYTES_PER_ROW_ENVELOPE):
            complete = False
            break
        kept.append(row)
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
        # Work is charged per reference, but bytes are not: the row's canonical encoding
        # below already carries every reference, and charging an envelope per reference
        # would quietly shrink what fits inside the published byte budget.
        for _ in candidate["component_ids"]:
            budget.charge()
            if budget.exhausted:
                complete = False
                break
        if not complete:
            break
        row = {
            "candidate_id": candidate["candidate_id"],
            "scope_id": candidate["scope_id"],
            "component_ids": list(candidate["component_ids"]),
            "eligible": candidate["eligible"],
        }
        if not budget.charge_bytes(encoded_bytes(row) + BYTES_PER_ROW_ENVELOPE):
            complete = False
            break
        kept.append(row)
    return kept, complete


def _freeze_versions(trace: DecisionTrace, budget: Budget) -> tuple[dict[str, Any], bool]:
    versions: dict[str, Any] = {}
    complete = True
    for key, value in trace.versions.items():
        budget.charge()
        if budget.exhausted:
            complete = False
            break
        if not budget.charge_bytes(encoded_bytes({key: value}) + BYTES_PER_ROW_ENVELOPE):
            complete = False
            break
        versions[key] = value
    return versions, complete


def _inventory_error(trace: DecisionTrace) -> dict[str, Any] | None:
    """A freeze that cannot see the whole decision may not be complete.

    The input-level diagnostic explains *why the caller's inventory is short*; this one
    explains *why the manifest is partial*, which is what a consumer must check before
    treating the freeze as reuse evidence. It is only reported when the caller really did
    fail to attest completeness -- a call stopped by the budget, or an artefact this
    version cannot interpret, already carries the accurate reason and must not be blamed
    on the caller's inventory.
    """
    if not trace.wire_ok or trace.inventory_complete:
        return None
    return {
        "code": "INVENTORY_NOT_COMPLETE",
        "detail": (
            "the caller did not assert a complete inventory; partial freezes carry identity "
            "for lineage but are not reuse evidence"
        ),
    }


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

    budget = Budget(effective)
    trace_domain = decode_trace(trace, budget)

    diagnostics: list[dict[str, Any]] = [dict(item) for item in trace_domain.diagnostics]

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
        # One named reason per call, whether it stopped in decode or in the walk.
        if not any(item.get("code") == budget.diagnostic()["code"] for item in diagnostics):
            diagnostics.append(budget.diagnostic())

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


#: The identity-bearing fields of a manifest. ``status`` and ``diagnostics`` are
#: deliberately excluded: they are a verdict about completeness and a record of why a call
#: stopped, and the same decision reached under a larger budget must keep the same
#: identity. That makes digest equality an **identity** statement only -- it is never a
#: verdict, and a consumer must check ``status == "complete"`` before treating two equal
#: digests as anything at all.
IDENTITY_FIELDS = ("schema_version", "scopes", "components", "candidates", "versions")


def decision_digest(manifest: Mapping[str, Any], *, budget: Budget | None = None) -> str:
    """Digest the identity-bearing part of a manifest, independent of row order.

    Rows are sorted by their id key before hashing, so a manifest whose arrays were
    permuted keeps the same identity as :func:`compare_decision_dependencies` reports.
    Missing identity fields and non-mapping rows are errors rather than empty defaults: a
    digest that treats "absent" or "garbage" as "empty" would let a record with unhashed
    content pass as unchanged.

    ``budget`` is optional and charges one work unit per row; hashing a manifest is work
    like any other walk, so a comparison that re-derives the digest must not do it for
    free. Bytes are deliberately *not* charged here -- the validation pass has already
    measured these rows, and re-charging them would shrink the effective byte budget for
    every extra pass over the same data.
    """
    missing = [name for name in IDENTITY_FIELDS if name not in manifest]
    if missing:
        raise ValueError(f"decision_digest needs the identity fields; missing {missing}")
    payload = {
        "schema_version": manifest["schema_version"],
        "scopes": _sorted_rows(manifest["scopes"], "scope_id", budget),
        "components": _sorted_rows(manifest["components"], "component_id", budget),
        "candidates": _sorted_rows(manifest["candidates"], "candidate_id", budget),
        "versions": manifest["versions"],
    }
    return _digest_payload(payload)


class BudgetExhausted(ValueError):
    """The caller's work or byte budget ran out; raised only from a hashing walk."""


def _sorted_rows(rows: Any, key: str, budget: Budget | None = None) -> list[Mapping[str, Any]]:
    """Order-independent view of a row array.

    A non-array or a non-mapping row is a caller error and is refused rather than
    dropped: silently skipping one would make two materially different manifests share a
    digest, which is exactly the collision this function exists to prevent.

    Only *work* is charged here. Bytes are charged once, in the validation pass that
    inspects these rows first; re-walking them to hash them must not double-count a row
    against ``max_input_bytes`` or a legitimately sized domain would stop fitting.
    """
    if not isinstance(rows, (list, tuple)):
        raise ValueError(f"{key} rows must be an array")
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"{key}[{index}] must be a mapping, got {type(row).__name__}")
        if budget is not None and not budget.charge():
            raise BudgetExhausted("the caller's work budget ran out while hashing the manifest")
    return sorted((dict(row) for row in rows), key=lambda row: str(row.get(key)))
