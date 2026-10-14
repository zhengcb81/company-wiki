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
    CANDIDATE_KEYS,
    COMPONENT_KEYS,
    NON_CONTENT_FIELD_NAMES,
    SCOPE_KEYS,
    TRACE_KEYS,
    TRACE_SCHEMA_VERSION,
)

_SHA256_HEX = frozenset("0123456789abcdef")

#: The one optional field of a declared ``du-decision-trace/1``.
OPTIONAL_TRACE_KEYS = frozenset({"inventory_complete"})
REQUIRED_TRACE_KEYS = TRACE_KEYS - OPTIONAL_TRACE_KEYS


class DecisionTraceError(ValueError):
    """A real input error: reject rather than guess."""


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


def _rows(value: Any, where: str) -> list[Mapping[str, Any]]:
    if value is None:
        raise DecisionTraceError(f"{where} is missing")
    if not _is_sequence(value):
        raise DecisionTraceError(f"{where} must be an array, got {type(value).__name__}")
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise DecisionTraceError(f"{where}[{index}] must be a mapping, got {type(item).__name__}")
    return list(value)


def _unique_by(
    rows: Sequence[Mapping[str, Any]], key: str, where: str
) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        identifier = _text(row.get(key), f"{where}.{key}")
        if identifier in indexed:
            raise DecisionTraceError(
                f"duplicate {key} {identifier!r} in {where}; each identity must appear once, "
                f"including every losing participant and every inspected component"
            )
        indexed[identifier] = row
    return indexed


def _reference_list(value: Any, where: str) -> list[str]:
    """A list of references. Repeats are a caller error, never silently collapsed."""
    if not _is_sequence(value):
        raise DecisionTraceError(f"{where} must be an array of strings, got {type(value).__name__}")
    seen: list[str] = []
    for index, item in enumerate(value):
        text = _text(item, f"{where}[{index}]")
        if text in seen:
            raise DecisionTraceError(f"{where}[{index}] repeats reference {text!r}")
        seen.append(text)
    return seen


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
    ) -> None:
        self.scopes: list[Mapping[str, Any]] = list(scopes)
        self.components: list[Mapping[str, Any]] = list(components)
        self.candidates: list[Mapping[str, Any]] = list(candidates)
        self.versions: dict[str, Any] = dict(versions)
        self.inventory_complete = inventory_complete
        self.wire_ok = wire_ok
        self.diagnostics: list[dict[str, Any]] = [dict(item) for item in diagnostics]
        # A decision domain with no candidate at all recorded nothing that could be
        # reused and nothing that could be compared, so it must never read as "complete".
        self.can_be_complete = bool(wire_ok and inventory_complete and candidates)


def _degraded(detail: str, code: str) -> DecisionTrace:
    """A trace we cannot interpret: identity is empty, and it is never complete."""
    return DecisionTrace(
        scopes=[],
        components=[],
        candidates=[],
        versions={},
        inventory_complete=False,
        wire_ok=False,
        diagnostics=[{"code": code, "detail": detail}],
    )


def _decode_scopes(raw: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(raw):
        where = f"scopes[{index}]"
        _exact_keys(row, SCOPE_KEYS, where)
        rows.append(
            {
                "scope_id": _text(row["scope_id"], f"{where}.scope_id"),
                "regime": _text(row["regime"], f"{where}.regime"),
                "family": _text(row["family"], f"{where}.family"),
                "form_type": _optional_text(row["form_type"], f"{where}.form_type"),
                "purpose": _text(row["purpose"], f"{where}.purpose"),
            }
        )
    return rows


def _decode_components(raw: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(raw):
        where = f"components[{index}]"
        _exact_keys(row, COMPONENT_KEYS, where)
        rows.append(
            {
                "component_id": _text(row["component_id"], f"{where}.component_id"),
                "version": _text(row["version"], f"{where}.version"),
                "content_digest": _digest(row["content_digest"], f"{where}.content_digest"),
                "matcher_digest": _digest(row["matcher_digest"], f"{where}.matcher_digest"),
                "scope_ids": _reference_list(row["scope_ids"], f"{where}.scope_ids"),
            }
        )
    return rows


def _decode_candidates(raw: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(raw):
        where = f"candidates[{index}]"
        _exact_keys(row, CANDIDATE_KEYS, where)
        eligible = row["eligible"]
        if not isinstance(eligible, bool):
            raise DecisionTraceError(
                f"{where}.eligible must be a boolean, got {type(eligible).__name__}"
            )
        rows.append(
            {
                "candidate_id": _text(row["candidate_id"], f"{where}.candidate_id"),
                "scope_id": _text(row["scope_id"], f"{where}.scope_id"),
                "component_ids": _reference_list(row["component_ids"], f"{where}.component_ids"),
                "eligible": eligible,
            }
        )
    return rows


def _decode_versions(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DecisionTraceError(
            f"versions must be a mapping of algorithm name to adopted version, "
            f"got {type(value).__name__}"
        )
    versions: dict[str, Any] = {}
    for key, item in value.items():
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
        versions[name] = item
    return versions


def _link(
    scopes: dict[str, Mapping[str, Any]],
    components: dict[str, Mapping[str, Any]],
    candidates: dict[str, Mapping[str, Any]],
) -> None:
    """Reject dangling references; the input must be internally closed."""
    for component_id, component in components.items():
        for scope_id in component["scope_ids"]:
            if scope_id not in scopes:
                raise DecisionTraceError(
                    f"component {component_id!r} references unknown scope {scope_id!r}"
                )
    for candidate_id, candidate in candidates.items():
        if candidate["scope_id"] not in scopes:
            raise DecisionTraceError(
                f"candidate {candidate_id!r} references unknown scope {candidate['scope_id']!r}"
            )
        for component_id in candidate["component_ids"]:
            if component_id not in components:
                raise DecisionTraceError(
                    f"candidate {candidate_id!r} references unknown component {component_id!r}"
                )


def _shape_diagnostics(
    scopes: dict[str, Mapping[str, Any]],
    components: dict[str, Mapping[str, Any]],
    candidates: dict[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Diagnostics for inputs that are legal but cannot show a decision was inspected.

    These are the anti-laundering checks available *inside* the input. They cannot prove
    the caller omitted an external fact -- see the package docstring and the handoff --
    but they do catch the shapes that say "I only recorded what won".
    """
    diagnostics: list[dict[str, Any]] = []
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
    referenced = {cid for candidate in candidates.values() for cid in candidate["component_ids"]}
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
    return diagnostics


def decode_trace(trace: Any) -> DecisionTrace:
    """Decode a caller trace into an order-normalized domain.

    Raises :class:`DecisionTraceError` for real data errors. Returns a
    ``DecisionTrace`` whose ``diagnostics`` carry everything that was unknown or missing,
    and whose ``can_be_complete`` is ``False`` whenever the input cannot support a
    ``complete`` freeze.
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

    # Declared ``du-decision-trace/1``: the structure is now a contract, not a hint.
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

    scope_rows = _decode_scopes(_rows(trace["scopes"], "scopes"))
    component_rows = _decode_components(_rows(trace["components"], "components"))
    candidate_rows = _decode_candidates(_rows(trace["candidates"], "candidates"))
    versions = _decode_versions(trace["versions"])

    scopes = _unique_by(scope_rows, "scope_id", "scopes")
    components = _unique_by(component_rows, "component_id", "components")
    candidates = _unique_by(candidate_rows, "candidate_id", "candidates")
    _link(scopes, components, candidates)

    diagnostics.extend(_shape_diagnostics(scopes, components, candidates))

    return DecisionTrace(
        scopes=[scopes[key] for key in sorted(scopes)],
        components=[components[key] for key in sorted(components)],
        candidates=[candidates[key] for key in sorted(candidates)],
        versions={key: versions[key] for key in sorted(versions)},
        inventory_complete=inventory_complete,
        wire_ok=True,
        diagnostics=diagnostics,
    )
