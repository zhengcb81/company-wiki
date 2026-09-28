"""Per-attempt lease heartbeat with an explicit, fenced failure boundary."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Protocol

from ._clock import Clock
from .models import Attempt, ClaimedWork


class HeartbeatFailure(RuntimeError):
    """Raised in the execution thread when lease renewal failed."""


class HeartbeatStore(Protocol):
    def heartbeat_attempt(
        self,
        *,
        attempt_id: str,
        lease_token: str,
        runtime_generation: int,
        now: str,
        lease_until: str,
    ) -> Attempt: ...


class AttemptHeartbeat:
    """Renew one claimed attempt from a Store-only helper thread."""

    def __init__(
        self,
        store: HeartbeatStore,
        claimed: ClaimedWork,
        *,
        interval_seconds: float,
        lease_seconds: float,
        clock: Clock | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if lease_seconds <= interval_seconds:
            raise ValueError("lease_seconds must be greater than heartbeat interval")
        self._store = store
        self._attempt = claimed.attempt
        self._interval_seconds = float(interval_seconds)
        self._lease_seconds = float(lease_seconds)
        self._clock = clock or Clock()
        self._stop = threading.Event()
        self._failure: BaseException | None = None
        self._thread = threading.Thread(
            target=self._run,
            name=f"lease-heartbeat-{claimed.attempt.attempt_id}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=max(5.0, self._lease_seconds))
        if self._thread.is_alive() and self._failure is None:
            self._failure = TimeoutError("heartbeat thread did not stop within its bound")

    def raise_if_failed(self) -> None:
        if self._failure is not None:
            raise HeartbeatFailure("attempt heartbeat lost its lease") from self._failure

    def _run(self) -> None:
        while not self._stop.wait(self._interval_seconds):
            now = self._clock.now()
            try:
                self._store.heartbeat_attempt(
                    attempt_id=self._attempt.attempt_id,
                    lease_token=self._attempt.lease_token,
                    runtime_generation=self._attempt.runtime_generation,
                    now=now,
                    lease_until=_add_seconds(now, self._lease_seconds),
                )
            except BaseException as exc:  # thread boundary; re-raised by owner
                self._failure = exc
                self._stop.set()
                return


def _add_seconds(iso_time: str, seconds: float) -> str:
    value = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    return (value + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = ["AttemptHeartbeat", "HeartbeatFailure"]

