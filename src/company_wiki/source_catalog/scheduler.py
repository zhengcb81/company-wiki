"""ZR-508: scheduler fairness — a deterministic scheduling decision layer
over the ZR-507 ProcessingDemand queue.

  effective_priority = priority + aging_bonus(wait) + deadline_urgency
    aging_bonus    — waiting longer than `aging_window` adds up to
                     `aging_max_bonus`, so low-priority demands are NEVER
                     starved by a continuous high-priority stream.
    deadline_urgency — demands whose deadline is closer than
                     `urgency_window` get `urgency_bonus`; a demand past
                     its deadline is still schedulable but is returned
                     with the `deadline_expired` marker (honest, never
                     dropped).

  cost budget: per-kind cumulative spend capped by `set_budget`; a kind
  whose spend >= limit is excluded from scheduling until `reset_budget`.

The raw ProcessingDemand priority stays IMMUTABLE (ZR-507 contract); all
fairness is scheduler-side policy.  Pure in-memory, clock injected.
"""

from __future__ import annotations

from dataclasses import dataclass

from .processing_demand import DemandQueue, ProcessingDemand


@dataclass(frozen=True)
class ScheduleDecision:
    """One scheduling decision: the demand to execute (None = idle) and
    the markers computed by the scheduler (scheduler-side only)."""

    demand: ProcessingDemand | None
    effective_priority: int = 0
    deadline_expired: bool = False


class DemandScheduler:
    """Fair scheduling over a DemandQueue: aging + deadline + cost budget."""

    def __init__(
        self,
        queue: DemandQueue,
        *,
        aging_window: float = 120.0,
        aging_max_bonus: int = 10,
        urgency_window: float = 60.0,
        urgency_bonus: int = 5,
    ):
        self._queue = queue
        self._aging_window = aging_window
        self._aging_max_bonus = aging_max_bonus
        self._urgency_window = urgency_window
        self._urgency_bonus = urgency_bonus
        self._budgets: dict[str, float] = {}
        self._spent: dict[str, float] = {}
        # Deadline registry is scheduler-side (ProcessingDemand contract
        # stays untouched per ZR-507); demand_id -> absolute deadline.
        self._deadlines: dict[str, float] = {}

    def set_deadline(self, *, demand_id: str, deadline: float) -> None:
        self._deadlines[demand_id] = deadline

    def set_budget(self, *, kind: str, limit: float) -> None:
        self._budgets[kind] = limit
        self._spent.setdefault(kind, 0.0)

    def reset_budget(self, *, kind: str) -> None:
        self._spent[kind] = 0.0

    def spend(self, *, kind: str, cost: float) -> None:
        self._spent[kind] = self._spent.get(kind, 0.0) + cost

    def _kind_available(self, kind: str) -> bool:
        limit = self._budgets.get(kind)
        return limit is None or self._spent.get(kind, 0.0) < limit

    def _effective_priority(
        self, demand: ProcessingDemand, now: float
    ) -> tuple[int, bool]:
        wait = max(0.0, now - demand.created_at)
        aging = (
            self._aging_max_bonus
            if wait >= self._aging_window
            else int(self._aging_max_bonus * wait / self._aging_window)
        )
        deadline = self._deadlines.get(demand.demand_id)
        deadline_expired = deadline is not None and now > deadline
        urgency = 0
        if deadline is not None and not deadline_expired and (
            deadline - now < self._urgency_window
        ):
            urgency = self._urgency_bonus
        return demand.priority + aging + urgency, deadline_expired

    def schedule_once(self, *, owner: str, now: float) -> ScheduleDecision:
        """Pick the ready demand with the highest effective priority that
        respects per-kind budgets, claim it, and return the decision."""
        ready = []
        for demand in self._queue.snapshot():
            if demand.status not in ("pending", "failed"):
                continue
            if demand.retry_at is not None and demand.retry_at > now:
                continue
            if not self._kind_available(demand.kind):
                continue
            effective, expired = self._effective_priority(demand, now)
            ready.append((effective, demand.created_at, demand.demand_id, expired))
        if not ready:
            return ScheduleDecision(demand=None)
        effective, _created, demand_id, expired = max(ready, key=lambda item: item[0])
        claimed = self._queue.claim(owner=owner, now=now, demand_id=demand_id)
        return ScheduleDecision(demand=claimed, effective_priority=effective, deadline_expired=expired)


__all__ = ["DemandScheduler", "ScheduleDecision"]
