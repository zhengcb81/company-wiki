"""ZR-508 acceptance tests: scheduler fairness (aging / deadline / cost
budget) over the ZR-507 ProcessingDemand queue.

  C1  aging: a low-priority demand waiting >= aging_window is scheduled
      despite a continuous high-priority stream (no starvation); equal
      waits still prefer higher priority.
  C2  deadline: urgency bonus near the deadline; past-deadline demands are
      still schedulable with the deadline_expired marker.
  C3  cost budget: per-kind spend cap pauses that kind; reset restores.
  C4  determinism + contract preservation: identical sequences -> same
      decisions; ZR-507 queue contract untouched (priority immutable);
      schedule_once returns a claimed (running, leased) demand or None.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.processing_demand import DemandQueue  # noqa: E402
from company_wiki.source_catalog.scheduler import DemandScheduler  # noqa: E402


def _queue(*, aging_window: float = 120.0) -> DemandScheduler:
    return DemandScheduler(
        DemandQueue(),
        aging_window=aging_window,
        aging_max_bonus=10,
        urgency_window=60.0,
        urgency_bonus=5,
    )


# ---------------------------------------------------------------------------
# C1 — aging fairness (no starvation)
# ---------------------------------------------------------------------------


def test_c1_low_priority_is_not_starved_by_high_priority_stream():
    scheduler = _queue(aging_window=100.0)
    scheduler._queue.enqueue(key="low", kind="normalize", priority=0, now=0.0)
    claimed = []
    # continuous high-priority stream (each round enqueues a fresh high);
    # the low demand waits 100s and then MUST be scheduled (aging 10 > 5).
    for t in range(1, 121):
        scheduler._queue.enqueue(key=f"high{t}", kind="normalize", priority=5, now=float(t))
        decision = scheduler.schedule_once(owner="w1", now=float(t))
        if decision.demand is not None:
            scheduler._queue.complete(
                demand_id=decision.demand.demand_id, owner="w1", now=float(t) + 0.5
            )
            claimed.append(decision.demand.key)
    assert "low" in claimed


def test_c1_equal_wait_prefers_higher_priority():
    scheduler = _queue()
    scheduler._queue.enqueue(key="a", kind="k", priority=1, now=0.0)
    scheduler._queue.enqueue(key="b", kind="k", priority=5, now=0.0)
    first = scheduler.schedule_once(owner="w1", now=1.0)
    assert first.demand.key == "b"
    second = scheduler.schedule_once(owner="w1", now=2.0)
    assert second.demand.key == "a"


def test_c1_raw_priority_remains_immutable():
    scheduler = _queue()
    demand = scheduler._queue.enqueue(key="k", kind="k", priority=2, now=0.0)
    assert demand.priority == 2
    with pytest.raises(Exception):
        demand.priority = 99  # frozen


# ---------------------------------------------------------------------------
# C2 — deadline urgency
# ---------------------------------------------------------------------------


def test_c2_deadline_urgency_lifts_effective_priority():
    scheduler = _queue()
    demand = scheduler._queue.enqueue(key="urgent", kind="k", priority=0, now=0.0)
    scheduler.set_deadline(demand_id=demand.demand_id, deadline=70.0)  # 70 away
    scheduler._queue.enqueue(key="normal", kind="k", priority=5, now=0.0)
    # at now=20 the urgent demand is 50s from deadline (< urgency_window 60)
    decision = scheduler.schedule_once(owner="w1", now=20.0)
    assert decision.demand.key == "urgent"
    assert decision.effective_priority == 6  # 0 + aging(20s)=1 + urgency 5


def test_c2_past_deadline_still_schedulable_with_marker():
    scheduler = _queue()
    demand = scheduler._queue.enqueue(key="late", kind="k", priority=0, now=0.0)
    scheduler.set_deadline(demand_id=demand.demand_id, deadline=10.0)
    decision = scheduler.schedule_once(owner="w1", now=50.0)
    assert decision.demand.key == "late"
    assert decision.deadline_expired is True


def test_c2_no_deadline_no_marker():
    scheduler = _queue()
    scheduler._queue.enqueue(key="plain", kind="k", priority=0, now=0.0)
    decision = scheduler.schedule_once(owner="w1", now=5.0)
    assert decision.deadline_expired is False


# ---------------------------------------------------------------------------
# C3 — cost budget
# ---------------------------------------------------------------------------


def test_c3_budget_exhaustion_pauses_kind():
    scheduler = _queue()
    scheduler.set_budget(kind="llm", limit=2.0)
    scheduler._queue.enqueue(key="a", kind="llm", priority=5, now=0.0)
    scheduler._queue.enqueue(key="b", kind="llm", priority=5, now=0.0)
    scheduler._queue.enqueue(key="c", kind="normalize", priority=0, now=0.0)
    for _ in range(2):
        decision = scheduler.schedule_once(owner="w1", now=1.0)
        assert decision.demand.kind == "llm"
        scheduler.spend(kind="llm", cost=1.0)
        scheduler._queue.complete(
            demand_id=decision.demand.demand_id, owner="w1", now=2.0
        )
    # llm budget exhausted (2/2): only normalize remains
    decision = scheduler.schedule_once(owner="w1", now=3.0)
    assert decision.demand.kind == "normalize"


def test_c3_budget_reset_restores_kind():
    scheduler = _queue()
    scheduler.set_budget(kind="llm", limit=1.0)
    scheduler._queue.enqueue(key="a", kind="llm", priority=5, now=0.0)
    scheduler._queue.enqueue(key="b", kind="llm", priority=5, now=0.0)
    decision = scheduler.schedule_once(owner="w1", now=1.0)
    scheduler.spend(kind="llm", cost=1.0)
    scheduler._queue.complete(demand_id=decision.demand.demand_id, owner="w1", now=2.0)
    assert scheduler.schedule_once(owner="w1", now=3.0).demand is None  # paused
    scheduler.reset_budget(kind="llm")
    decision = scheduler.schedule_once(owner="w1", now=4.0)
    assert decision.demand.key == "b"


# ---------------------------------------------------------------------------
# C4 — determinism + contract preservation
# ---------------------------------------------------------------------------


def test_c4_identical_sequences_produce_identical_decisions():
    def run() -> tuple:
        scheduler = _queue(aging_window=50.0)
        scheduler.set_budget(kind="llm", limit=1.0)
        scheduler._queue.enqueue(key="low", kind="normalize", priority=0, now=0.0)
        scheduler._queue.enqueue(key="llm1", kind="llm", priority=5, now=1.0)
        scheduler.set_deadline(demand_id="pd-1", deadline=80.0)
        decisions = []
        for t in (5.0, 10.0, 30.0, 60.0):
            decision = scheduler.schedule_once(owner="w1", now=t)
            decisions.append(
                (decision.demand.key if decision.demand else None,
                 decision.effective_priority, decision.deadline_expired)
            )
            if decision.demand is not None:
                scheduler.spend(kind=decision.demand.kind, cost=1.0)
                scheduler._queue.complete(
                    demand_id=decision.demand.demand_id, owner="w1", now=t + 1.0
                )
        return tuple(decisions)

    assert run() == run()


def test_c4_schedule_once_returns_none_when_idle():
    scheduler = _queue()
    assert scheduler.schedule_once(owner="w1", now=1.0).demand is None


def test_c4_claimed_demand_has_lease():
    scheduler = _queue()
    scheduler._queue.enqueue(key="k", kind="k", priority=1, now=0.0)
    decision = scheduler.schedule_once(owner="w1", now=1.0)
    assert decision.demand.status == "running"
    assert decision.demand.lease_owner == "w1"
    assert decision.demand.lease_until is not None


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
