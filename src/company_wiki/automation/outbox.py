"""AUTO-4 Outbox: transactional effect writing.

Effects are written to the outbox table in the same transaction as the job
status transition.  An outbox executor (AUTO-7) claims and executes entries.
This module provides the data model and helpers; it does not execute effects.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutboxEntry:
    """A single outbox entry awaiting execution."""

    outbox_id: str
    effect_id: str
    payload_json: str
    status: str
    attempt_count: int
    not_before: str
    lease_token: str | None
    lease_until: str | None
    last_error: str | None


__all__ = [
    "OutboxEntry",
]
