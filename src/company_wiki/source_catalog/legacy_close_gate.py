"""FC-705: legacy bridge close gate — two >=24h zero-hit windows.

The legacy bridge may only be closed after TWO CONSECUTIVE observation
windows, each at least 24h long, both with ``legacy_bridge_hits == 0``.
The gate is a pure function over the period ledger (the independent audit
state written by ``scripts/legacy_observer.py``): no side effects, no
catalog access — machine-checkable by tests and CI.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

OBSERVATION_WINDOW_MIN_DURATION = timedelta(hours=24)
REQUIRED_CONSECUTIVE_WINDOWS = 2


def _parse_utc(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def close_gate_allowed(periods: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """FC-705: may the legacy bridge be closed now?

    Requires the last two COMPLETED periods (by ``period`` number) to be
    consecutive, each >= 24h long, and each with ``legacy_bridge_hits == 0``.
    An OPEN window (no ``ended_at``) never counts — it is still
    accumulating.  Returns (allowed, reasons).  An empty or malformed
    ledger is NOT allowed (fail closed) with an explicit reason.
    """
    reasons: list[str] = []
    if not isinstance(periods, list) or not periods:
        return False, ["no observation periods recorded — close gate not passed"]
    numbered = [p for p in periods if isinstance(p, dict) and isinstance(p.get("period"), int)]
    completed = [p for p in numbered if p.get("ended_at") is not None]
    if len(completed) < REQUIRED_CONSECUTIVE_WINDOWS:
        return False, [
            f"need {REQUIRED_CONSECUTIVE_WINDOWS} COMPLETED zero-hit observation "
            f"windows, have {len(completed)} (an open window is still "
            "accumulating and never counts)"
        ]
    completed.sort(key=lambda p: p["period"])
    last_two = completed[-REQUIRED_CONSECUTIVE_WINDOWS:]
    if last_two[1]["period"] - last_two[0]["period"] != 1:
        reasons.append(
            f"windows {last_two[0]['period']} and {last_two[1]['period']} "
            "are not consecutive"
        )
    for period in last_two:
        label = f"period {period['period']}"
        hits = period.get("legacy_bridge_hits")
        if hits != 0:
            reasons.append(f"{label}: legacy_bridge_hits={hits} (must be 0)")
        start = _parse_utc(period.get("started_at"))
        end = _parse_utc(period.get("ended_at"))
        if start is None or end is None:
            reasons.append(f"{label}: missing started_at/ended_at (window not completed)")
            continue
        duration = end - start
        if duration < OBSERVATION_WINDOW_MIN_DURATION:
            reasons.append(
                f"{label}: window {duration} is shorter than 24h"
            )
    return not reasons, reasons
