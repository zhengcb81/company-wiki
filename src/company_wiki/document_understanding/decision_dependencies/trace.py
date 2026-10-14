"""Strict decoding of a ``du-decision-trace/1`` input.

The card draws a hard line between two kinds of bad input, and this module keeps it:

* **Real data errors are rejected.** Wrong types, duplicate ids (including the same id
  carrying two different contents), dangling references, and digests that are not a full
  SHA-256 raise :class:`DecisionTraceError`. They are never silently repaired by
  de-duplicating, dropping a conflicting row or truncating, because a "fixed" inventory
  would let the cache believe it saw a decision it never saw.
* **Unknown or missing items are reported, not guessed.** A trace without the wire id, a
  legacy artefact from an older scheme, and an inventory the caller did not attest as
  complete come back as ``partial`` with an explicit diagnostic. They can be replayed for
  lineage, and they can never become reuse evidence.

One field is deliberately optional inside a declared ``du-decision-trace/1``:
``inventory_complete``. It is the caller's attestation about *external* completeness --
facts this package cannot see -- so its absence is itself the honest signal "not
asserted", not a structural violation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .contract import (
    BYTES_PER_ROW_ENVELOPE,
    CANDIDATE_KEYS,
    COMPONENT_KEYS,
    NON_CONTENT_FIELD_NAMES,
    SCOPE_KEYS,
    TRACE_KEYS,
    TRACE_SCHEMA_VERSION,
    Budget,
    encoded_bytes,
)

_SHA256_HEX = frozenset("0123456789abcdef")

#: The one optional field of a declared ``du-decision-trace/1``.
OPTIONAL_TRACE_KEYS = frozenset({"inventory_complete"})
REQUIRED_TRACE_KEYS = TRACE_KEYS - OPTIONAL_TRACE_KEYS


class DecisionTraceError(ValueError):
    """A real input error: reject rather than guess."""


class _BudgetStop(Exception):
    """Internal: the caller's work/byte budget ran out mid-decode."""


def _spend(
    budget: Budget | None,
    *,
    units: int = 1,
    payload: Any = None,
    texts: tuple[str, ...] = (),
) -> None:
    """Charge work and bytes for one element; stop the decode when the budget runs out.

    Every loop that touches a row, a reference or a large container spends here, so a
    single call cannot do unbounded work while claiming a bounded budget. Bytes are
    charged on the *real* canonical encoding of whatever was walked, plus a small
    per-element envelope -- never a sampled subset, so ``max_input_bytes`` cannot be
    bypassed by growing one row. Stopping is not an input error: it degrades the result to
    ``partial`` and never to ``same``.
    """
    if budget is None:
        return
    if not budget.charge(units):
        raise _BudgetStop
    for text in texts:
        if not budget.charge_text(text):
            raise _BudgetStop
    if payload is not None:
        if not budget.charge_bytes(encoded_bytes(payload)):
            raise _BudgetStop
    if not budget.charge_bytes(BYTES_PER_ROW_ENVELOPE * max(1, units)):
        raise _BudgetStop


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _text(value: Any, where: str) -> str:
    if isinstance(value, bool) or not isinstance(value, str):
        raise DecisionTraceError(f"{where} must be a string, got {type(value).__name__}")
    if not value:
        raise DecisionTraceError(f"{where} must be nonempty")
    return value


def _optional_text(value: Any, where: str) -> str | None:
    if value is None:
        return None
    return _text(value, where)


def _digest(value: Any, where: str) -> str:
    """A full lowercase SHA-256. A short display version is never identity."""
    if isinstance(value, bool) or not isinstance(value, str):
        raise DecisionTraceError(
            f"{where} must be a full lowercase SHA-256 hex string, got {type(value).__name__}"
        )
    if len(value) != 64 or not set(value) <= _SHA256_HEX:
        raise DecisionTraceError(
            f"{where} must be a full 64-character lowercase SHA-256, got {value[:16]!r}"
            + ("..." if len(value) > 16 else "")
        )
    return value


def _exact_keys(value: Mapping[str, Any], allowed: frozenset[str], where: str) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        raise DecisionTraceError(f"{where} carries unsupported fields: {extra}")
    missing = sorted(allowed - set(value))
    if missing:
        raise DecisionTraceError(f"{where} is missing required fields: {missing}")


def _rows(value: Any, where: str, budget: Budget | None) -> list[Mapping[str, Any]]:
    if value is None:
        raise DecisionTraceError(f"{where} is missing")
    if not _is_sequence(value):
        raise DecisionTraceError(f"{where} must be an array, got {type(value).__name__}")
    rows: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        _spend(budget)
        if not isinstance(item, Mapping):
            raise DecisionTraceError(f"{where}[{index}] must be a mapping, got {type(item).__name__}")
        rows.append(item)
    return rows


def _unique_by(
    rows: Sequence[Mapping[str, Any]], key: str, where: str, budget: Budget | None
) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        _spend(budget)
        identifier = _text(row.get(key), f"{where}.{key}")
        if identifier in indexed:
            raise DecisionTraceError(
                f"duplicate {key} {identifier!r} in {where}; each identity must appear once, "
                f"including every losing participant and every inspected component"
            )
        indexed[identifier] = row
    return indexed


def _reference_list(value: Any, where: str, budget: Budget | None) -> list[str]:
    """A list of unique references. Repeats are a caller error, never silently collapsed.

    Duplicate detection uses a set so the check stays linear: a quadratic membership scan
    would let a wide list do far more work than the caller's ``max_work_units`` admits.
    """
    if not _is_sequence(value):
        raise DecisionTraceError(f"{where} must be an array of strings, got {type(value).__name__}")
    seen: set[str] = set()
    names: list[str] = []
    for index, item in enumerate(value):
        _spend(budget)
        text = _text(item, f"{where}[{index}]")
        if text in seen:
            raise DecisionTraceError(f"{where}[{index}] repeats reference {text!r}")
        seen.add(text)
        names.append(text)
    return names


class DecisionTrace:
    """A decoded, order-normalized decision domain. Nothing here is business semantics.

    ``wire_ok`` records whether the input actually declared this contract. ``False``
    means the caller gave us something we cannot interpret -- no trace, no wire id, or an
    older scheme -- which is reported as ``partial`` rather than being read as "nothing
    changed".
    """

    __slots__ = (
        "can_be_complete",
        "candidates",
        "components",
        "diagnostics",
        "inventory_complete",
        "participating",
        "scopes",
        "versions",
        "wire_ok",
    )

    def __init__(
        self,
        *,
        scopes: Sequence[Mapping[str, Any]],
        components: Sequence[Mapping[str, Any]],
        candidates: Sequence[Mapping[str, Any]],
        versions: Mapping[str, Any],
        inventory_complete: bool,
        wire_ok: bool,
        diagnostics: Sequence[Mapping[str, Any]],
        participating: int = 0,
    ) -> None:
        self.scopes: list[Mapping[str, Any]] = list(scopes)
        self.components: list[Mapping[str, Any]] = list(components)
        self.candidates: list[Mapping[str, Any]] = list(candidates)
        self.versions: dict[str, Any] = dict(versions)
        self.inventory_complete = inventory_complete
        self.wire_ok = wire_ok
        self.diagnostics: list[dict[str, Any]] = [dict(item) for item in diagnostics]
        self.participating = participating
        # Three shapes record nothing that could be reused or compared, so none of them
        # may read as "complete": no candidate membership at all (the shape a winners-only
        # trace takes), and components that no candidate ever references (the decision
        # links between them are simply absent).
        self.can_be_complete = bool(
            wire_ok
            and inventory_complete
            and candidates
            and (not components or participating)
        )


def _degraded(
    detail: str, code: str, *, diagnostics: Sequence[Mapping[str, Any]] | None = None
) -> DecisionTrace:
    """A trace we cannot interpret: identity is empty, and it is never complete."""
    entries: list[dict[str, Any]] = [dict(item) for item in (diagnostics or ())]
    if not any(item.get("code") == code for item in entries):
        entries.append({"code": code, "detail": detail})
    return DecisionTrace(
        scopes=[],
        components=[],
        candidates=[],
        versions={},
        inventory_complete=False,
        wire_ok=False,
        diagnostics=entries,
    )


def _decode_scopes(raw: list[Mapping[str, Any]], budget: Budget | None) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(raw):
        where = f"scopes[{index}]"
        _spend(budget)
        _exact_keys(row, SCOPE_KEYS, where)
        built = {
            "scope_id": _text(row["scope_id"], f"{where}.scope_id"),
            "regime": _text(row["regime"], f"{where}.regime"),
            "family": _text(row["family"], f"{where}.family"),
            "form_type": _optional_text(row["form_type"], f"{where}.form_type"),
            "purpose": _text(row["purpose"], f"{where}.purpose"),
        }
        _spend(budget, payload=built)
        rows.append(built)
    return rows


def _decode_components(
    raw: list[Mapping[str, Any]], budget: Budget | None
) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(raw):
        where = f"components[{index}]"
        _spend(budget)
        _exact_keys(row, COMPONENT_KEYS, where)
        built = {
            "component_id": _text(row["component_id"], f"{where}.component_id"),
            "version": _text(row["version"], f"{where}.version"),
            "content_digest": _digest(row["content_digest"], f"{where}.content_digest"),
            "matcher_digest": _digest(row["matcher_digest"], f"{where}.matcher_digest"),
            "scope_ids": _reference_list(row["scope_ids"], f"{where}.scope_ids", budget),
        }
        _spend(budget, payload=built)
        rows.append(built)
    return rows


def _decode_candidates(
    raw: list[Mapping[str, Any]], budget: Budget | None
) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(raw):
        where = f"candidates[{index}]"
        _spend(budget)
        _exact_keys(row, CANDIDATE_KEYS, where)
        eligible = row["eligible"]
        if not isinstance(eligible, bool):
            raise DecisionTraceError(
                f"{where}.eligible must be a boolean, got {type(eligible).__name__}"
            )
        built = {
            "candidate_id": _text(row["candidate_id"], f"{where}.candidate_id"),
            "scope_id": _text(row["scope_id"], f"{where}.scope_id"),
            "component_ids": _reference_list(
                row["component_ids"], f"{where}.component_ids", budget
            ),
            "eligible": eligible,
        }
        _spend(budget, payload=built)
        rows.append(built)
    return rows


def _decode_versions(value: Any, budget: Budget | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DecisionTraceError(
            f"versions must be a mapping of algorithm name to adopted version, "
            f"got {type(value).__name__}"
        )
    versions: dict[str, Any] = {}
    for key, item in value.items():
        _spend(budget)
        name = _text(key, "versions key")
        if name.casefold() in NON_CONTENT_FIELD_NAMES:
            raise DecisionTraceError(
                f"versions[{name!r}] names a runtime setting or a secret handle, not an adopted "
                f"algorithm; content identity may not carry paths, run ids, clock values, costs, "
                f"timeouts or API-key/env names"
            )
        if isinstance(item, bool) or not isinstance(item, (str, int)):
            raise DecisionTraceError(
                f"versions[{name!r}] must be a string or integer version, got {type(item).__name__}"
            )
        if name in versions:
            raise DecisionTraceError(f"versions repeats key {name!r}")
        _spend(budget, payload={name: item})
        versions[name] = item
    return versions


def _link(
    scopes: dict[str, Mapping[str, Any]],
    components: dict[str, Mapping[str, Any]],
    candidates: dict[str, Mapping[str, Any]],
    budget: Budget | None,
) -> None:
    """Reject dangling references; the input must be internally closed."""
    for component_id, component in components.items():
        for scope_id in component["scope_ids"]:
            _spend(budget)
            if scope_id not in scopes:
                raise DecisionTraceError(
                    f"component {component_id!r} references unknown scope {scope_id!r}"
                )
    for candidate_id, candidate in candidates.items():
        _spend(budget)
        if candidate["scope_id"] not in scopes:
            raise DecisionTraceError(
                f"candidate {candidate_id!r} references unknown scope {candidate['scope_id']!r}"
            )
        for component_id in candidate["component_ids"]:
            _spend(budget)
            if component_id not in components:
                raise DecisionTraceError(
                    f"candidate {candidate_id!r} references unknown component {component_id!r}"
                )


def _shape_diagnostics(
    scopes: dict[str, Mapping[str, Any]],
    components: dict[str, Mapping[str, Any]],
    candidates: dict[str, Mapping[str, Any]],
    budget: Budget | None,
) -> tuple[list[dict[str, Any]], int]:
    """Diagnostics for inputs that are legal but cannot show a decision was inspected.

    These are the anti-laundering checks available *inside* the input. They cannot prove
    the caller omitted an external fact -- see the package docstring and the handoff --
    but they do catch the shapes that say "I only recorded what won".

    Also returns how many inspected components some candidate actually references, which
    the caller folds into ``can_be_complete``.
    """
    diagnostics: list[dict[str, Any]] = []
    for _ in scopes.values():
        _spend(budget)
    for _ in components.values():
        _spend(budget)
    for _ in candidates.values():
        _spend(budget)
    if not scopes and not candidates:
        diagnostics.append(
            {
                "code": "EMPTY_DECISION_DOMAIN",
                "detail": "no scope and no candidate: nothing shows this decision was inspected",
            }
        )
    if not candidates:
        diagnostics.append(
            {
                "code": "MISSING_CANDIDATES",
                "detail": (
                    "no candidate membership was recorded, so winners-only traces cannot be "
                    "distinguished from a full inventory and there is nothing to reuse"
                ),
            }
        )
    referenced = set()
    for candidate in candidates.values():
        for cid in candidate["component_ids"]:
            _spend(budget)
            referenced.add(cid)
    inspected = set(components)
    if inspected and not referenced:
        diagnostics.append(
            {
                "code": "NO_PARTICIPATING_COMPONENT",
                "component_ids": sorted(inspected),
                "detail": (
                    "components were inspected but no candidate references any of them; the "
                    "decision links between components and candidates are absent"
                ),
            }
        )
    return diagnostics, len(inspected & referenced)


def decode_trace(trace: Any, budget: Budget | None = None) -> DecisionTrace:
    """Decode a caller trace into an order-normalized domain.

    Raises :class:`DecisionTraceError` for real data errors. Returns a
    ``DecisionTrace`` whose ``diagnostics`` carry everything that was unknown or missing,
    and whose ``can_be_complete`` is ``False`` whenever the input cannot support a
    ``complete`` freeze.

    When a ``budget`` is supplied it is charged for every row, reference and version
    entry this walks; running out stops the decode and degrades the result to
    ``partial``. A budget stop is never an input error and never a ``same``.
    """
    if trace is None:
        return _degraded(
            "no decision trace was supplied; the old path that recorded only adopted "
            "policy components cannot provide reuse evidence",
            "MISSING_TRACE",
        )
    if not isinstance(trace, Mapping):
        raise DecisionTraceError(f"trace must be a mapping, got {type(trace).__name__}")

    schema = trace.get("schema_version")
    if schema is None:
        return _degraded(
            f"the trace declares no wire version; expected {TRACE_SCHEMA_VERSION}",
            "MISSING_SCHEMA_VERSION",
        )
    if schema != TRACE_SCHEMA_VERSION:
        return _degraded(
            f"got {schema!r}, expected {TRACE_SCHEMA_VERSION}; an artefact of another scheme may "
            "be replayed elsewhere but cannot provide reuse evidence here",
            "LEGACY_TRACE_VERSION",
        )

    try:
        return _decode_declared_trace(trace, budget)
    except _BudgetStop:
        assert budget is not None and budget.stopped_by is not None
        return _degraded(
            "the caller's work or byte budget ran out before the decision inventory could be "
            "read in full; nothing here is reuse evidence",
            budget.diagnostic()["code"],
            diagnostics=[budget.diagnostic()],
        )


def _decode_declared_trace(trace: Mapping[str, Any], budget: Budget | None) -> DecisionTrace:
    """Decode a mapping that declared ``du-decision-trace/1``: the structure is a contract."""
    extra = sorted(set(trace) - TRACE_KEYS)
    if extra:
        raise DecisionTraceError(f"trace carries unsupported fields: {extra}")
    missing = sorted(REQUIRED_TRACE_KEYS - set(trace))
    if missing:
        raise DecisionTraceError(f"trace is missing required fields: {missing}")

    diagnostics: list[dict[str, Any]] = []
    raw_flag = trace.get("inventory_complete")
    if raw_flag is None and "inventory_complete" not in trace:
        inventory_complete = False
        diagnostics.append(
            {
                "code": "INVENTORY_UNKNOWN",
                "detail": (
                    "the caller did not assert inventory_complete; absence is not a claim of "
                    "completeness, so this cannot become reuse evidence"
                ),
            }
        )
    elif not isinstance(raw_flag, bool):
        raise DecisionTraceError(
            f"inventory_complete must be a boolean, got {type(raw_flag).__name__}"
        )
    else:
        inventory_complete = raw_flag
        if not inventory_complete:
            diagnostics.append(
                {
                    "code": "INVENTORY_INCOMPLETE",
                    "detail": (
                        "the caller declared the candidate inventory incomplete; a missing row "
                        "must never read as an unchanged decision"
                    ),
                }
            )

    scope_rows = _decode_scopes(_rows(trace["scopes"], "scopes", budget), budget)
    component_rows = _decode_components(_rows(trace["components"], "components", budget), budget)
    candidate_rows = _decode_candidates(_rows(trace["candidates"], "candidates", budget), budget)
    versions = _decode_versions(trace["versions"], budget)

    scopes = _unique_by(scope_rows, "scope_id", "scopes", budget)
    components = _unique_by(component_rows, "component_id", "components", budget)
    candidates = _unique_by(candidate_rows, "candidate_id", "candidates", budget)
    _link(scopes, components, candidates, budget)

    shape_diagnostics, participating = _shape_diagnostics(scopes, components, candidates, budget)
    diagnostics.extend(shape_diagnostics)

    return DecisionTrace(
        scopes=[scopes[key] for key in sorted(scopes)],
        components=[components[key] for key in sorted(components)],
        candidates=[candidates[key] for key in sorted(candidates)],
        versions={key: versions[key] for key in sorted(versions)},
        inventory_complete=inventory_complete,
        wire_ok=True,
        diagnostics=diagnostics,
        participating=participating,
    )
