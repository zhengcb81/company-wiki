"""ZR-507: ProcessingDemand API — a deterministic, pure-memory demand
queue (enqueue/dedupe/claim/heartbeat/retry/complete/expire) that gives
schedulers (ZR-508) and consumers (filing-fetch, LLM processing) a single
demand lifecycle.

Semantics:
  - enqueue(key, kind, priority): dedupe by key — a repeated key returns
    the existing demand instead of creating a second one.
  - claim(now): the ready demand (no active lease) with highest priority
    (desc) and earliest creation (asc) gets a lease; priority is IMMUTABLE
    after enqueue, so a consumer can never reorder the global queue.
  - heartbeat(now): extends the lease; rejected without an active lease.
  - complete / fail: terminal transitions; fail increments attempts with
    exponential backoff (retry_at) until the attempt cap, then
    terminal_failed.
  - expire(now): a lease past its deadline returns the demand to ready.

Clock is injected (`now` argument) so every timing path is testable;
the module is pure (no IO/DB/network).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessingDemand:
    """One immutable demand record; priority never changes after enqueue."""

    demand_id: str
    key: str
    kind: str
    priority: int
    status: str = "pending"
    attempts: int = 0
    lease_owner: str | None = None
    lease_until: float | None = None
    retry_at: float | None = None
    created_at: float = 0.0
    updated_at: float = 0.0


_STATUSES = frozenset(
    {"pending", "running", "completed", "failed", "terminal_failed"}
)


class DemandQueueError(RuntimeError):
    """Base class for processing-demand violations."""


class DemandNotFoundError(DemandQueueError):
    """The demand_id does not exist."""


class DemandStateError(DemandQueueError):
    """The transition is invalid for the current state/lease."""


class DemandQueue:
    """Pure-memory demand queue with lease-based claiming."""

    def __init__(
        self,
        *,
        lease_seconds: float = 300.0,
        max_attempts: int = 3,
        backoff_base: float = 60.0,
    ):
        self._demands: dict[str, ProcessingDemand] = {}
        self._lease_seconds = lease_seconds
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base
        self._next_id = 0

    def enqueue(
        self, *, key: str, kind: str, priority: int = 0, now: float = 0.0
    ) -> ProcessingDemand:
        """Insert or return the existing demand for `key` (dedupe)."""
        for demand in self._demands.values():
            if demand.key == key and demand.status in (
                "pending",
                "running",
                "failed",
            ):
                return demand
        demand = ProcessingDemand(
            demand_id=f"pd-{self._next_id}",
            key=key,
            kind=kind,
            priority=priority,
            created_at=now,
            updated_at=now,
        )
        self._next_id += 1
        self._demands[demand.demand_id] = demand
        return demand

    def _demand(self, demand_id: str) -> ProcessingDemand:
        demand = self._demands.get(demand_id)
        if demand is None:
            raise DemandNotFoundError(f"no demand {demand_id!r}")
        return demand

    def claim(
        self, *, owner: str, now: float, demand_id: str | None = None
    ) -> ProcessingDemand:
        """Claim the highest-priority ready demand and grant a lease.

        `demand_id` (additive, ZR-508): claim a specific ready demand —
        used by the scheduler after its own fairness selection; the
        default (None) keeps the strict priority-desc/created-asc order.
        """
        if demand_id is not None:
            chosen = self._demand(demand_id)
            if chosen.status not in ("pending", "failed"):
                raise DemandStateError(f"demand {demand_id!r} is not claimable")
            if chosen.retry_at is not None and chosen.retry_at > now:
                raise DemandStateError(f"demand {demand_id!r} is in backoff")
        else:
            ready = [
                demand
                for demand in self._demands.values()
                if demand.status in ("pending", "failed")
                and (demand.retry_at is None or demand.retry_at <= now)
                and (demand.lease_until is None or demand.lease_until < now)
            ]
            if not ready:
                raise DemandStateError("no ready demand to claim")
            chosen = min(ready, key=lambda item: (-item.priority, item.created_at))
        claimed = ProcessingDemand(
            demand_id=chosen.demand_id,
            key=chosen.key,
            kind=chosen.kind,
            priority=chosen.priority,
            status="running",
            attempts=chosen.attempts,
            lease_owner=owner,
            lease_until=now + self._lease_seconds,
            retry_at=None,
            created_at=chosen.created_at,
            updated_at=now,
        )
        self._demands[claimed.demand_id] = claimed
        return claimed

    def _require_lease(self, demand: ProcessingDemand, owner: str, now: float) -> None:
        if demand.lease_owner != owner:
            raise DemandStateError(f"lease owned by {demand.lease_owner!r}")
        if demand.lease_until is None or demand.lease_until <= now:
            raise DemandStateError("lease expired")

    def heartbeat(self, *, demand_id: str, owner: str, now: float) -> ProcessingDemand:
        demand = self._demand(demand_id)
        self._require_lease(demand, owner, now)
        renewed = ProcessingDemand(
            demand_id=demand.demand_id,
            key=demand.key,
            kind=demand.kind,
            priority=demand.priority,
            status="running",
            attempts=demand.attempts,
            lease_owner=owner,
            lease_until=now + self._lease_seconds,
            retry_at=None,
            created_at=demand.created_at,
            updated_at=now,
        )
        self._demands[renewed.demand_id] = renewed
        return renewed

    def complete(self, *, demand_id: str, owner: str, now: float) -> ProcessingDemand:
        demand = self._demand(demand_id)
        self._require_lease(demand, owner, now)
        finished = ProcessingDemand(
            demand_id=demand.demand_id,
            key=demand.key,
            kind=demand.kind,
            priority=demand.priority,
            status="completed",
            attempts=demand.attempts,
            lease_owner=owner,
            lease_until=None,
            retry_at=None,
            created_at=demand.created_at,
            updated_at=now,
        )
        self._demands[finished.demand_id] = finished
        return finished

    def fail(self, *, demand_id: str, owner: str, now: float) -> ProcessingDemand:
        demand = self._demand(demand_id)
        self._require_lease(demand, owner, now)
        attempts = demand.attempts + 1
        status = "terminal_failed" if attempts >= self._max_attempts else "failed"
        retry_at = (
            None
            if status == "terminal_failed"
            else now + self._backoff_base * (2 ** (attempts - 1))
        )
        failed = ProcessingDemand(
            demand_id=demand.demand_id,
            key=demand.key,
            kind=demand.kind,
            priority=demand.priority,
            status=status,
            attempts=attempts,
            lease_owner=None,
            lease_until=None,
            retry_at=retry_at,
            created_at=demand.created_at,
            updated_at=now,
        )
        self._demands[failed.demand_id] = failed
        return failed

    def expire(self, *, now: float) -> int:
        """Return demands whose lease expired back to ready; count returned."""
        expired = 0
        for demand_id, demand in list(self._demands.items()):
            if (
                demand.status == "running"
                and demand.lease_until is not None
                and demand.lease_until <= now
            ):
                reverted = ProcessingDemand(
                    demand_id=demand.demand_id,
                    key=demand.key,
                    kind=demand.kind,
                    priority=demand.priority,
                    status="pending",
                    attempts=demand.attempts,
                    lease_owner=None,
                    lease_until=None,
                    retry_at=None,
                    created_at=demand.created_at,
                    updated_at=now,
                )
                self._demands[demand_id] = reverted
                expired += 1
        return expired

    def snapshot(self) -> tuple[ProcessingDemand, ...]:
        return tuple(sorted(self._demands.values(), key=lambda item: item.demand_id))


__all__ = [
    "DemandNotFoundError",
    "DemandQueue",
    "DemandQueueError",
    "DemandStateError",
    "ProcessingDemand",
]
