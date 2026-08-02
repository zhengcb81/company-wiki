"""AUTO-5 Event sources: read events from the store for planning.

This module depends on the store and models.  It does not import the legacy
scheduler, network, LLM or configuration modules.  Real file watchers and
timers are for a later phase; this module reads events from the store.
"""

from __future__ import annotations

from .models import Event


class EventSource:
    """Reads events from the store for the controller to process."""

    def __init__(self, store) -> None:
        self._store = store

    def get_all_events(self) -> tuple[Event, ...]:
        """Return all events in the store, ordered by occurred_at."""
        conn = self._store._connect()
        try:
            rows = conn.execute(
                "SELECT event_id, event_type, subject_type, subject_id, "
                "input_hash, payload_json, policy_version, occurred_at, "
                "observed_at FROM events ORDER BY occurred_at, event_id"
            ).fetchall()
            from .models import Event as Evt
            return tuple(Evt.from_dict(dict(r)) for r in rows)
        finally:
            conn.close()

    def get_events_by_type(self, event_type: str) -> tuple[Event, ...]:
        """Return events of a specific type."""
        conn = self._store._connect()
        try:
            rows = conn.execute(
                "SELECT event_id, event_type, subject_type, subject_id, "
                "input_hash, payload_json, policy_version, occurred_at, "
                "observed_at FROM events WHERE event_type = ? "
                "ORDER BY occurred_at, event_id",
                (event_type,),
            ).fetchall()
            from .models import Event as Evt
            return tuple(Evt.from_dict(dict(r)) for r in rows)
        finally:
            conn.close()


__all__ = ["EventSource"]
