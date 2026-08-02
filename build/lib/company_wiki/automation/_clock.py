"""Injectable clock and ID generator for deterministic testing.

This module is intentionally NOT scanned by the boundary tests — it is the
only place where ``datetime.now`` and ``uuid4`` are called.  All other modules
receive these as injected dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


class Clock:
    """Returns the current UTC time as an ISO 8601 string."""

    def now(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class IDGenerator:
    """Generates unique hex IDs."""

    def new_id(self) -> str:
        return uuid4().hex


__all__ = ["Clock", "IDGenerator"]
