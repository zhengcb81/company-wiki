"""Frozen JSON wire names and resource limits for the decision-dependency component.

Everything in this module is a constant. It reads no configuration, no catalog and no
environment variable: a caller that wants smaller budgets passes them explicitly, and a
caller that wants larger ones cannot get them from here.

The limits are technical hard bounds, not permissions. Reaching one produces
``partial``/``unavailable`` and never ``same``.
"""

from __future__ import annotations

import json
from typing import Any, Final, Mapping

TRACE_SCHEMA_VERSION: Final = "du-decision-trace/1"
FROZEN_SCHEMA_VERSION: Final = "du-decision-dependencies/1"
COMPARISON_SCHEMA_VERSION: Final = "du-decision-comparison/1"

FROZEN_STATUS_COMPLETE: Final = "complete"
FROZEN_STATUS_PARTIAL: Final = "partial"
FROZEN_STATUSES: Final = frozenset({FROZEN_STATUS_COMPLETE, FROZEN_STATUS_PARTIAL})

COMPARISON_STATUS_SAME: Final = "same"
COMPARISON_STATUS_CHANGED: Final = "changed"
COMPARISON_STATUS_UNAVAILABLE: Final = "unavailable"
COMPARISON_STATUSES: Final = frozenset(
    {COMPARISON_STATUS_SAME, COMPARISON_STATUS_CHANGED, COMPARISON_STATUS_UNAVAILABLE}
)

#: The only keys a legal ``du-decision-trace/1`` input may carry. A stray field is a
#: caller error: additive schema growth must be deliberate, not absorbed silently.
TRACE_KEYS: Final = frozenset(
    {"schema_version", "scopes", "components", "candidates", "versions", "inventory_complete"}
)
SCOPE_KEYS: Final = frozenset({"scope_id", "regime", "family", "form_type", "purpose"})
COMPONENT_KEYS: Final = frozenset(
    {"component_id", "version", "content_digest", "matcher_digest", "scope_ids"}
)
CANDIDATE_KEYS: Final = frozenset({"candidate_id", "scope_id", "component_ids", "eligible"})

#: The complete manifest key set. There is no free-form extension slot, which is what
#: keeps run ids, paths, API-key names, timestamps, costs and timeouts out of identity.
FROZEN_KEYS: Final = frozenset(
    {
        "schema_version",
        "status",
        "scopes",
        "components",
        "candidates",
        "versions",
        "decision_digest",
        "diagnostics",
    }
)
FROZEN_SCOPE_KEYS: Final = SCOPE_KEYS
FROZEN_COMPONENT_KEYS: Final = COMPONENT_KEYS
FROZEN_CANDIDATE_KEYS: Final = CANDIDATE_KEYS

COMPARISON_KEYS: Final = frozenset(
    {
        "schema_version",
        "status",
        "changed_component_ids",
        "added_candidate_ids",
        "removed_candidate_ids",
        "diagnostics",
    }
)

DIAGNOSTIC_KEYS: Final = frozenset({"code", "scope_ids", "component_ids", "candidate_ids", "detail"})

#: Defaults per DU3/1. A caller may lower any of them; none of them may be raised here.
DEFAULT_LIMITS: Final[Mapping[str, int]] = {
    "max_scopes": 64,
    "max_components": 512,
    "max_candidates": 4096,
    "max_input_bytes": 2 * 1024 * 1024,
    "max_work_units": 200_000,
}

#: Work charged per element. Each is charged on *every* pass over the element, so an
#: implementation that walks the inventory repeatedly pays for it repeatedly.
WORK_UNIT: Final = 1
WORK_PER_SCOPE: Final = 4

#: ``max_input_bytes`` is charged on the **real canonical encoding** of every row this
#: walks (decode pass and manifest walk alike), plus this envelope for each row and each
#: standalone element. The envelope covers the bookkeeping around a row that the JSON
#: encoding of the row itself does not carry, so the accounting can only over-count, never
#: under-count what a caller sent. One call's byte use is therefore genuinely bounded and
#: stops early, without re-encoding the whole document just to measure it.
BYTES_PER_ROW_ENVELOPE: Final = 96


def canonical_json(value: Any) -> str:
    """The one canonical encoding used for digests and byte accounting.

    Key order never matters, floats are refused outright, and non-ASCII is written through
    so a digest is a property of the content rather than of this interpreter.
    """
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def encoded_bytes(value: Any) -> int:
    """The exact UTF-8 length of a value's canonical encoding."""
    return len(canonical_json(value).encode("utf-8"))

#: Names that can only describe a runtime setting or a secret handle. They are never an
#: adopted *algorithm version*, so they may not enter the manifest through the one
#: caller-supplied map the wire carries. This is the component's half of the rule that no
#: API-key/env name, path, run id, clock value, cost or timeout is part of content
#: identity; the other half is the closed key set of the manifest itself.
NON_CONTENT_FIELD_NAMES: Final = frozenset(
    {
        "api_key",
        "apikey",
        "api_key_env",
        "access_token",
        "secret",
        "password",
        "token",
        "env",
        "env_name",
        "environment",
        "path",
        "file_path",
        "absolute_path",
        "relative_path",
        "directory",
        "run_id",
        "run",
        "job_id",
        "lease_id",
        "timestamp",
        "time",
        "now",
        "started_at",
        "finished_at",
        "elapsed",
        "cost",
        "cost_usd",
        "price",
        "pricing",
        "timeout",
        "timeout_seconds",
        "budget_usd",
    }
)


def default_limits() -> dict[str, int]:
    """A fresh copy, so a caller cannot mutate the module constant."""
    return dict(DEFAULT_LIMITS)


class Budget:
    """Charges work units and canonical bytes; reports the first limit it hit.

    Every pass over a row, a reference or a large container is charged again, so an
    implementation that walks the inventory repeatedly pays for it repeatedly and a
    single call cannot do unbounded work while claiming a bounded budget. Byte
    accounting uses the real UTF-8 length of each string plus
    :data:`BYTES_PER_ROW_ENVELOPE` per row, which bounds growth without making the
    accounting depend on dict-key spelling.
    """

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
        return self.charge_bytes(len(text.encode("utf-8")))

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

    def diagnostic(self) -> dict[str, Any]:
        """The named reason this call stopped, for the result's diagnostics."""
        limit = self.stopped_by or "max_work_units"
        observed = self.work_used if limit == "max_work_units" else self.bytes_used
        return {
            "code": _LIMIT_CODES.get(limit, f"{limit.upper()}_REACHED"),
            "detail": (
                f"{limit}={self.limits[limit]} reached ({observed} observed); work stopped here "
                "and the result is not reuse evidence"
            ),
        }


_LIMIT_CODES: dict[str, str] = {
    "max_work_units": "WORK_LIMIT_REACHED",
    "max_input_bytes": "BYTES_LIMIT_REACHED",
    "max_scopes": "SCOPES_LIMIT_REACHED",
    "max_components": "COMPONENTS_LIMIT_REACHED",
    "max_candidates": "CANDIDATES_LIMIT_REACHED",
}


def resolve_limits(limits: Mapping[str, Any] | None) -> tuple[dict[str, int], dict[str, Any] | None]:
    """Merge caller limits over the defaults; return ``(effective, error)``.

    A caller may only lower a limit. Raising one is rejected instead of quietly
    honoured, because the frozen defaults are the technical bound DU3/1 published.
    """
    effective = default_limits()
    if limits is None:
        return effective, None
    if not isinstance(limits, Mapping):
        return effective, {
            "code": "LIMITS_NOT_A_MAPPING",
            "detail": f"limits must be a mapping, got {type(limits).__name__}",
        }
    for key, value in limits.items():
        if key not in DEFAULT_LIMITS:
            return effective, {
                "code": "UNKNOWN_LIMIT",
                "detail": f"unsupported limit {key!r}; known: {sorted(DEFAULT_LIMITS)}",
            }
        if isinstance(value, bool) or not isinstance(value, int):
            return effective, {
                "code": "LIMIT_NOT_AN_INTEGER",
                "detail": f"limit {key!r} must be an integer, got {value!r}",
            }
        if value < 0:
            return effective, {
                "code": "LIMIT_NEGATIVE",
                "detail": f"limit {key!r} must not be negative, got {value}",
            }
        if value > DEFAULT_LIMITS[key]:
            return effective, {
                "code": "LIMIT_ABOVE_FROZEN_DEFAULT",
                "detail": (
                    f"limit {key!r}={value} exceeds the frozen default "
                    f"{DEFAULT_LIMITS[key]}; a caller may only lower limits"
                ),
            }
        effective[key] = value
    return effective, None
