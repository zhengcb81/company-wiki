"""Two real model processes cannot overspend; a killed caller keeps its hold."""

from __future__ import annotations

import multiprocessing
from pathlib import Path


def _reserve_in_child(
    database,
    job_id,
    attempt_id,
    lease_token,
    generation,
    barrier,
    queue,
    wait_event=None,
):
    from company_wiki.automation.narrative_run_store import (
        NarrativeRunStore,
        RunBudgetExceededError,
    )

    store = NarrativeRunStore(Path(database))
    if barrier is not None:
        barrier.wait(timeout=15)
    try:
        receipt = store.reserve_model_attempt(
            run_id="run-one",
            job_id=job_id,
            attempt_id=attempt_id,
            lease_token=lease_token,
            runtime_generation=generation,
            request_sha256="a" * 64,
            model_id="model-one",
            prompt_version="prompt-1",
            pricing_version="price-1",
            input_tokens_bound=100,
            max_output_tokens=50,
            output_bytes_bound=100,
            now="2026-10-03T10:01:00Z",
        )
    except RunBudgetExceededError:
        queue.put(("denied", attempt_id))
    else:
        queue.put(("admitted" if receipt.may_send_http else "replayed", attempt_id))
        if wait_event is not None:
            wait_event.wait(30)


def _stop(children, queue):
    for child in children:
        if child.is_alive():
            child.terminate()
        child.join(timeout=5)
        assert not child.is_alive(), "budget test leaked a child process"
    queue.close()
    queue.join_thread()


def test_two_processes_compete_for_one_atomic_reservation(tmp_path):
    from unit.test_narrative_run_store import setup_run, claim

    _, auto, budget, generation, a, b = setup_run(
        tmp_path, max_tokens=150, max_micro_usd=90, max_output_bytes=100
    )
    works = (claim(auto, generation, a), claim(auto, generation, b))
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    queue = context.Queue()
    children = [
        context.Process(
            target=_reserve_in_child,
            args=(
                str(auto.db_path),
                work.job.job_id,
                work.attempt.attempt_id,
                work.attempt.lease_token,
                generation,
                barrier,
                queue,
            ),
        )
        for work in works
    ]
    try:
        for child in children:
            child.start()
        outcomes = [queue.get(timeout=25), queue.get(timeout=25)]
        for child in children:
            child.join(timeout=5)
            assert child.exitcode == 0
    finally:
        _stop(children, queue)
    assert sorted(value[0] for value in outcomes) == ["admitted", "denied"]
    assert len(budget.reservations_for_run("run-one")) == 1
    receipt = budget.budget_snapshot("run-one")
    assert (
        receipt.charged_tokens,
        receipt.charged_micro_usd,
        receipt.charged_output_bytes,
    ) == (150, 90, 100)


def test_killed_caller_and_expired_lease_never_release_its_reservation(tmp_path):
    from unit.test_narrative_run_store import setup_run, claim, reserve

    module, auto, budget, generation, a, b = setup_run(
        tmp_path, max_tokens=150, max_micro_usd=90, max_output_bytes=100
    )
    work = claim(auto, generation, a)
    other = auto.claim_next_ready(
        worker_id="other-worker",
        attempt_id="attempt-other",
        lease_token="lease-other",
        now="2026-10-03T10:01:00Z",
        lease_until="2026-10-03T10:09:00Z",
        expected_generation=generation,
        allowed_job_ids=(b.job_id,),
    )
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    hold = context.Event()
    child = context.Process(
        target=_reserve_in_child,
        args=(
            str(auto.db_path),
            a.job_id,
            work.attempt.attempt_id,
            work.attempt.lease_token,
            generation,
            None,
            queue,
            hold,
        ),
    )
    try:
        child.start()
        assert queue.get(timeout=25)[0] == "admitted"
        child.terminate()
        child.join(timeout=5)
    finally:
        _stop([child], queue)
    auto.reap_expired_attempts(now="2026-10-03T10:03:00Z", allowed_job_ids=(a.job_id,))
    reopened = module.NarrativeRunStore(auto.db_path)
    assert reopened.budget_snapshot("run-one").charged_tokens == 150
    import pytest

    with pytest.raises(module.RunBudgetExceededError):
        reserve(reopened, other, now="2026-10-03T10:03:00Z")
    assert reopened.reservations_for_run("run-one")[0].usage_status == "reserved"
