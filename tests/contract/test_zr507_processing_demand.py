"""ZR-507 acceptance tests: ProcessingDemand API.

  C1  model + queue API: enqueue dedupes by key; claim orders by priority
      desc + created asc; heartbeat renews; complete/fail/expire behave.
  C2  lifecycle closure: enqueue->claim->complete; lease timeout -> expire
      -> reclaimable; fail backoff gates re-claim; attempt cap -> terminal.
  C3  consumer-priority isolation: priority immutable after enqueue; late
      high-priority demand claims before early low-priority one; FIFO
      within same priority.
  C4  determinism: identical operation sequences yield identical
      snapshots; injected clock drives all timing paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.processing_demand import (  # noqa: E402
    DemandNotFoundError,
    DemandQueue,
    DemandStateError,
)


# ---------------------------------------------------------------------------
# C1 — model + queue API
# ---------------------------------------------------------------------------


def test_c1_enqueue_dedupes_by_key():
    queue = DemandQueue()
    first = queue.enqueue(key="k1", kind="normalize", priority=1, now=0.0)
    second = queue.enqueue(key="k1", kind="normalize", priority=1, now=1.0)
    assert second.demand_id == first.demand_id
    assert len(queue.snapshot()) == 1


def test_c1_claim_orders_by_priority_then_creation():
    queue = DemandQueue()
    queue.enqueue(key="low", kind="k", priority=1, now=0.0)
    queue.enqueue(key="high", kind="k", priority=5, now=1.0)
    first = queue.claim(owner="w1", now=2.0)
    second = queue.claim(owner="w1", now=3.0)
    assert first.key == "high"
    assert second.key == "low"


def test_c1_heartbeat_renews_lease():
    queue = DemandQueue(lease_seconds=100.0)
    queue.enqueue(key="k", kind="k", now=0.0)
    claimed = queue.claim(owner="w1", now=1.0)
    renewed = queue.heartbeat(demand_id=claimed.demand_id, owner="w1", now=50.0)
    assert renewed.lease_until == 150.0
    assert renewed.status == "running"


def test_c1_heartbeat_rejected_without_lease():
    queue = DemandQueue()
    demand = queue.enqueue(key="k", kind="k", now=0.0)
    with pytest.raises(DemandStateError):
        queue.heartbeat(demand_id=demand.demand_id, owner="w1", now=1.0)


# ---------------------------------------------------------------------------
# C2 — lifecycle closure
# ---------------------------------------------------------------------------


def test_c2_enqueue_claim_complete_chain():
    queue = DemandQueue()
    queue.enqueue(key="k", kind="k", now=0.0)
    claimed = queue.claim(owner="w1", now=1.0)
    assert claimed.status == "running"
    assert claimed.lease_owner == "w1"
    finished = queue.complete(demand_id=claimed.demand_id, owner="w1", now=2.0)
    assert finished.status == "completed"
    # completed demands are not claimable again
    with pytest.raises(DemandStateError):
        queue.claim(owner="w2", now=3.0)


def test_c2_expired_lease_is_reclaimable():
    queue = DemandQueue(lease_seconds=10.0)
    queue.enqueue(key="k", kind="k", now=0.0)
    queue.claim(owner="w1", now=1.0)
    # lease expires at 11.0; expire at 12.0 returns it to ready
    assert queue.expire(now=12.0) == 1
    reclaimed = queue.claim(owner="w2", now=13.0)
    assert reclaimed.key == "k"
    assert reclaimed.lease_owner == "w2"


def test_c2_fail_backoff_gates_reclaim():
    queue = DemandQueue(backoff_base=60.0, max_attempts=3)
    queue.enqueue(key="k", kind="k", now=0.0)
    claimed = queue.claim(owner="w1", now=1.0)
    failed = queue.fail(demand_id=claimed.demand_id, owner="w1", now=2.0)
    assert failed.status == "failed"
    assert failed.attempts == 1
    assert failed.retry_at == 62.0  # 2 + 60 * 2**0
    # not claimable before retry_at
    with pytest.raises(DemandStateError):
        queue.claim(owner="w1", now=61.0)
    # claimable at/after retry_at
    reclaimed = queue.claim(owner="w1", now=62.0)
    assert reclaimed.key == "k"


def test_c2_attempt_cap_is_terminal():
    queue = DemandQueue(max_attempts=2, backoff_base=1.0)
    queue.enqueue(key="k", kind="k", now=0.0)
    for claim_at, fail_at in ((1.0, 2.0), (4.0, 5.0)):
        claimed = queue.claim(owner="w1", now=claim_at)
        failed = queue.fail(demand_id=claimed.demand_id, owner="w1", now=fail_at)
    assert failed.status == "terminal_failed"
    assert failed.retry_at is None
    with pytest.raises(DemandStateError):
        queue.claim(owner="w1", now=6.0)


def test_c2_unknown_demand_id_raises():
    queue = DemandQueue()
    with pytest.raises(DemandNotFoundError):
        queue.complete(demand_id="pd-99", owner="w1", now=1.0)


# ---------------------------------------------------------------------------
# C3 — consumer-priority isolation
# ---------------------------------------------------------------------------


def test_c3_late_high_priority_does_not_reorder_claimed():
    queue = DemandQueue()
    queue.enqueue(key="a", kind="k", priority=0, now=0.0)
    first = queue.claim(owner="w1", now=1.0)
    # consumer enqueues a high-priority demand while the first runs
    queue.enqueue(key="b", kind="k", priority=9, now=2.0)
    assert first.key == "a"
    second = queue.claim(owner="w1", now=3.0)
    assert second.key == "b"


def test_c3_priority_is_immutable_after_enqueue():
    queue = DemandQueue()
    queue.enqueue(key="k", kind="k", priority=3, now=0.0)
    claimed = queue.claim(owner="w1", now=1.0)
    assert claimed.priority == 3
    with pytest.raises(Exception):
        claimed.priority = 9  # frozen dataclass


def test_c3_same_priority_fifo():
    queue = DemandQueue()
    queue.enqueue(key="a", kind="k", priority=1, now=0.0)
    queue.enqueue(key="b", kind="k", priority=1, now=1.0)
    first = queue.claim(owner="w1", now=2.0)
    second = queue.claim(owner="w1", now=3.0)
    assert (first.key, second.key) == ("a", "b")


# ---------------------------------------------------------------------------
# C4 — determinism with injected clock
# ---------------------------------------------------------------------------


def test_c4_identical_sequences_produce_identical_snapshots():
    def run() -> tuple:
        queue = DemandQueue(lease_seconds=10.0, max_attempts=2, backoff_base=5.0)
        queue.enqueue(key="a", kind="k", priority=1, now=0.0)
        queue.enqueue(key="b", kind="k", priority=2, now=1.0)
        first = queue.claim(owner="w1", now=2.0)
        queue.fail(demand_id=first.demand_id, owner="w1", now=3.0)
        queue.expire(now=20.0)
        return tuple(
            (d.key, d.status, d.priority, d.attempts, d.lease_owner, d.retry_at)
            for d in queue.snapshot()
        )

    assert run() == run()


def test_c4_expire_count_and_reclaim_deterministic():
    queue = DemandQueue(lease_seconds=5.0)
    queue.enqueue(key="k", kind="k", now=0.0)
    queue.claim(owner="w1", now=1.0)
    assert queue.expire(now=6.0) == 1
    assert queue.expire(now=7.0) == 0  # nothing left running


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
