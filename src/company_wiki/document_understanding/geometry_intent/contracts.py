"""Fixed pure-data interfaces, bounded validation and interval helpers for DU9.

Schema constants follow INTERFACES.md. Nothing here reads configuration,
company directories, files, network or clocks; no evidence, locator or
printed-page-offset logic exists in this package by design.
"""
from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
from typing import Any

SCHEMA_POLICY = "du-geometry-policy/1"
SCHEMA_PLAN = "du-geometry-plan/1"
SCHEMA_STATE = "du-geometry-plan-state/1"
SCHEMA_ADMISSION = "du-geometry-admission/1"
SCHEMA_RUN_SUMMARY = "du-geometry-run-summary/1"

DISCOVER_VALUES = frozenset({"on_tabular_evidence", "context_only", "none", "unknown"})
FINE_VALUES = frozenset({"on_candidate", "explicit_only", "unknown"})
# Canonical class order: fair-share remainders and borrowing tie-breaks use it.
DEMAND_CLASSES: tuple[str, ...] = (
    "operating",
    "project",
    "mixed",
    "context",
    "administrative",
    "unknown",
)
DEMAND_VALUES = frozenset(DEMAND_CLASSES)
EVIDENCE_VALUES = frozenset({"observed_candidate", "absent", "unknown"})
NAVIGATION_VALUES = frozenset({"native_destination", "conflict", "unknown"})

ADMISSION_DECISIONS = frozenset(
    {"admitted", "deduplicated", "not_found", "unknown", "exhausted", "cancelled", "rejected"}
)
RUN_REASONS = (
    "admitted",
    "deduplicated",
    "not_found",
    "unknown",
    "exhausted",
    "cancelled",
    "rejected",
)

MAX_STRING = 4096
MAX_DIAGNOSTICS = 256
MAX_DIAGNOSTIC_DETAIL = 160
MAX_WINDOW_KEYS_PER_ADMISSION = 64


def canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


class DiagnosticSink:
    """Bounded diagnostics: rows never exceed MAX_DIAGNOSTICS and each row is
    size-bounded, so adversarial inputs cannot grow the plan without limit."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.dropped = 0

    def add(self, code: str, detail: str, window_keys: Sequence[str] = ()) -> None:
        if len(self.rows) >= MAX_DIAGNOSTICS:
            self.dropped += 1
            return
        self.rows.append(
            {
                "code": code,
                "detail": detail[:MAX_DIAGNOSTIC_DETAIL],
                "window_keys": [str(key)[:64] for key in window_keys][:8],
            }
        )

    def as_plan_rows(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.rows]


def is_int(value: Any) -> bool:
    """Real integers only; ``bool`` is not a page number."""
    return type(value) is int


def require_nonnegative_int(value: Any, name: str) -> int:
    if not is_int(value):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative, got {value}")
    return value


def bounded_text(value: Any) -> str | None:
    """A usable string field, or None when it is missing/overlong (excluded).

    Length is checked before any strip copy so adversarial megabyte strings
    never allocate proportional work inside the planner.
    """
    if not isinstance(value, str) or not value:
        return None
    if len(value) > MAX_STRING:
        return None
    if value != value.strip():
        return None
    return value


# --- interval helpers (spans only; never invents offsets) -------------------

Interval = tuple[int, int]


def merge_intervals(intervals: Sequence[Interval]) -> list[Interval]:
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged: list[Interval] = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def interval_length(intervals: Sequence[Interval]) -> int:
    return sum(end - start + 1 for start, end in merge_intervals(intervals))


def insert_interval(merged: list[Interval], interval: Interval) -> None:
    """Insert one interval into a sorted, coalesced list in place.

    Keeps the invariant of :func:`merge_intervals` with amortized
    O(log n + absorbed) work, so streaming many windows never re-sorts.
    """
    start, end = interval
    index = bisect_left(merged, start - 1, key=lambda iv: iv[1])
    while index < len(merged) and merged[index][0] <= end + 1:
        start = min(start, merged[index][0])
        end = max(end, merged[index][1])
        del merged[index]
    merged.insert(index, (start, end))


def subtract_intervals(base: Interval, covered: Sequence[Interval]) -> list[Interval]:
    """Pages of ``base`` not inside any interval of ``covered``.

    ``covered`` must already be sorted and coalesced (output of
    :func:`merge_intervals` / :func:`insert_interval`); binary search then
    costs O(log k + overlaps) instead of re-sorting per window.
    """
    start, end = base
    pieces: list[Interval] = [(start, end)]
    index = bisect_left(covered, start, key=lambda iv: iv[1])
    while index < len(covered) and pieces:
        cov_start, cov_end = covered[index]
        if cov_start > end:
            break
        next_pieces: list[Interval] = []
        for piece_start, piece_end in pieces:
            if cov_end < piece_start or cov_start > piece_end:
                next_pieces.append((piece_start, piece_end))
                continue
            if cov_start > piece_start:
                next_pieces.append((piece_start, cov_start - 1))
            if cov_end < piece_end:
                next_pieces.append((cov_end + 1, piece_end))
        pieces = next_pieces
        index += 1
    return pieces
