"""AUTO-5 Event sources: read events from the store for planning.

This module depends on the store and models.  It does not import the legacy
scheduler, network, LLM or configuration modules.  Real file watchers and
timers are for a later phase; this module reads events from the store.
"""

from __future__ import annotations

from typing import Protocol

from .models import Event


class EventReadStore(Protocol):
    def list_events(self, *, event_type: str | None = None) -> tuple[Event, ...]: ...


class EventSource:
    """Reads events from the store for the controller to process."""

    def __init__(self, store: EventReadStore) -> None:
        self._store = store

    def get_all_events(self) -> tuple[Event, ...]:
        """Return all events in the store, ordered by occurred_at."""
        return self._store.list_events()

    def get_events_by_type(self, event_type: str) -> tuple[Event, ...]:
        """Return events of a specific type."""
        return self._store.list_events(event_type=event_type)


__all__ = ["EventSource"]
