"""Durable N4 run accounting, including failures and uncertain provider usage."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from company_wiki.automation.models import (
    Event,
    Job,
    JobStatus,
    RiskClass,
    RuntimeState,
    make_job_key,
)
from company_wiki.automation.store import (
    AutomationStore,
    LeaseLostError,
    RuntimeGateClosedError,
)


T0 = "2026-10-03T10:00:00Z"
T1 = "2026-10-03T10:01:00Z"
T2 = "2026-10-03T10:02:00Z"
T3 = "2026-10-03T10:03:00Z"
T9 = "2026-10-03T10:09:00Z"
SHA = hashlib.sha256(b"run-input").hexdigest()
REQUEST = hashlib.sha256(b"request").hexdigest()
RESPONSE = hashlib.sha256(b"response").hexdigest()


def _module():
    assert (
        Path(__file__).resolve().parents[2]
        / "src/company_wiki/automation/narrative_run_store.py"
    ).is_file()
    from company_wiki.automation import narrative_run_store

    return narrative_run_store


def seed_job(store, name):
    event = Event(
        f"event-{name}",
        "source.revision_registered",
        "source_revision",
        name,
        SHA,
        "{}",
        "run-policy",
        T0,
        T0,
    )
    store.put_event(event)
    job = Job(
        job_id=f"job-{name}",
        job_key=make_job_key(
            "source.narrative_summarize",
            "source_revision",
            name,
            SHA,
            "run-policy",
            "1.0.0",
        ),
        job_type="source.narrative_summarize",
        subject_type="source_revision",
        subject_id=name,
        input_hash=SHA,
        policy_version="run-policy",
        handler_version="1.0.0",
        risk_class=RiskClass.LOW,
        status=JobStatus.READY,
        priority=10,
        not_before=T0,
        max_attempts=3,
        created_from_event_id=event.event_id,
        created_at=T0,
        updated_at=T0,
        last_error_code=None,
        last_error_detail=None,
    )
    store.put_job(job)
    return job


def claim(store, generation, job, name=None):
    return store.claim_next_ready(
        worker_id="model-worker",
        attempt_id=f"attempt-{name or job.job_id}",
        lease_token=f"lease-{name or job.job_id}",
        now=T1,
        lease_until=T2,
        expected_generation=generation,
        allowed_job_ids=(job.job_id,),
    )


def create_run(budget, jobs, **overrides):
    options = dict(
        run_id="run-one",
        input_hash=SHA,
        job_ids=tuple(job.job_id for job in jobs),
        model_id="model-one",
        prompt_version="prompt-1",
        pricing_version="price-1",
        input_micro_usd_per_million_tokens=300_000,
        output_micro_usd_per_million_tokens=1_200_000,
        max_tokens=300,
        max_micro_usd=180,
        max_output_bytes=200,
        created_at=T0,
    )
    options.update(overrides)
    return budget.create_run(**options)


def reserve(budget, claimed, **overrides):
    options = dict(
        run_id="run-one",
        job_id=claimed.job.job_id,
        attempt_id=claimed.attempt.attempt_id,
        lease_token=claimed.attempt.lease_token,
        runtime_generation=claimed.attempt.runtime_generation,
        request_sha256=REQUEST,
        model_id="model-one",
        prompt_version="prompt-1",
        pricing_version="price-1",
        input_tokens_bound=100,
        max_output_tokens=50,
        output_bytes_bound=100,
        now=T1,
    )
    options.update(overrides)
    return budget.reserve_model_attempt(**options)


def setup_run(tmp_path, **limits):
    module = _module()
    auto = AutomationStore(tmp_path / "auto.db")
    a, b = seed_job(auto, "a"), seed_job(auto, "b")
    generation = auto.set_runtime_gate(
        RuntimeState.ENABLED, updated_at=T1
    ).control_generation
    budget = module.NarrativeRunStore(auto.db_path)
    create_run(budget, (a, b), **limits)
    return module, auto, budget, generation, a, b


def test_run_identity_and_scope_are_immutable_and_job_has_one_budget(tmp_path):
    module, auto, budget, _, a, b = setup_run(tmp_path)
    first = budget.get_run("run-one")
    assert create_run(budget, (b, a, a), created_at=T1) == first
    assert budget.run_for_job(a.job_id) == first
    assert budget.run_for_job("outside") is None
    for field, value in (
        ("input_hash", REQUEST),
        ("model_id", "other"),
        ("prompt_version", "other"),
        ("pricing_version", "other"),
        ("max_tokens", 301),
        ("job_ids", (a.job_id,)),
    ):
        with pytest.raises(module.RunConflictError):
            create_run(budget, (a, b), **{field: value})
    with pytest.raises(module.RunConflictError):
        create_run(budget, (a,), run_id="another-run")
    assert auto.get_job(a.job_id) == a


def test_reserve_is_atomic_idempotent_and_replay_cannot_send_http(tmp_path):
    _, auto, budget, generation, a, _ = setup_run(tmp_path)
    work = claim(auto, generation, a)
    admission = reserve(budget, work)
    assert admission.created and admission.may_send_http
    assert admission.record.reserved_tokens == 150
    assert admission.record.reserved_micro_usd == 90
    again = reserve(budget, work)
    assert again.record == admission.record
    assert not again.created and not again.may_send_http
    assert budget.budget_snapshot("run-one").charged_tokens == 150


@pytest.mark.parametrize("limit", ["max_tokens", "max_micro_usd", "max_output_bytes"])
def test_budget_exhaustion_does_not_insert_or_touch_outside_attempt(tmp_path, limit):
    module, auto, budget, generation, a, b = setup_run(
        tmp_path,
        **{
            limit: {"max_tokens": 150, "max_micro_usd": 90, "max_output_bytes": 100}[
                limit
            ]
        },
    )
    one, two = claim(auto, generation, a), claim(auto, generation, b)
    reserve(budget, one)
    before = budget.budget_snapshot("run-one")
    with pytest.raises(module.RunBudgetExceededError):
        reserve(budget, two)
    assert budget.get_reservation("run-one", two.attempt.attempt_id) is None
    assert budget.budget_snapshot("run-one") == before
    assert auto.get_attempt(two.attempt.attempt_id) == two.attempt


def test_reserve_rejects_wrong_binding_scope_request_and_inactive_lease(tmp_path):
    module, auto, budget, generation, a, b = setup_run(tmp_path)
    work = claim(auto, generation, a)
    for field, value in (
        ("model_id", "other"),
        ("prompt_version", "other"),
        ("pricing_version", "other"),
        ("job_id", b.job_id),
    ):
        with pytest.raises(module.NarrativeRunError):
            reserve(budget, work, **{field: value})
    with pytest.raises(LeaseLostError):
        reserve(budget, work, lease_token="wrong")
    with pytest.raises(LeaseLostError):
        reserve(budget, work, now=T3)
    reserve(budget, work)
    with pytest.raises(module.ReservationConflictError):
        reserve(budget, work, request_sha256=RESPONSE)
    second = claim(auto, generation, b)
    auto.set_runtime_gate(RuntimeState.PAUSED, updated_at=T1)
    with pytest.raises(RuntimeGateClosedError):
        reserve(budget, second)


def test_known_usage_is_recorded_before_decode_and_output_remains_reserved(tmp_path):
    module, auto, budget, generation, a, _ = setup_run(tmp_path)
    work = claim(auto, generation, a)
    reserve(budget, work)
    usage = module.ModelUsage(30, 10)
    receipt = budget.settle_model_usage(
        run_id="run-one",
        attempt_id=work.attempt.attempt_id,
        usage=usage,
        response_sha256=RESPONSE,
        error_code="MODEL_RESPONSE_INVALID",
        settled_at=T1,
    )
    assert receipt.usage_status == "known"
    assert (
        receipt.charged_tokens,
        receipt.charged_micro_usd,
        receipt.charged_output_bytes,
    ) == (40, 21, 100)
    assert (
        budget.settle_model_usage(
            run_id="run-one",
            attempt_id=work.attempt.attempt_id,
            usage=usage,
            response_sha256=RESPONSE,
            error_code="MODEL_RESPONSE_INVALID",
            settled_at=T2,
        )
        == receipt
    )
    final = budget.settle_output(
        run_id="run-one",
        attempt_id=work.attempt.attempt_id,
        output_bytes=0,
        output_sha256=None,
        settled_at=T2,
    )
    assert final.charged_output_bytes == 0
    assert final.charged_micro_usd == 21


def test_unknown_usage_survives_reopen_pause_and_expiry_and_explicit_late_usage_can_correct_it(
    tmp_path,
):
    module, auto, budget, generation, a, _ = setup_run(tmp_path)
    work = claim(auto, generation, a)
    reserve(budget, work)
    auto.set_runtime_gate(RuntimeState.PAUSED, updated_at=T2)
    receipt = budget.settle_model_usage(
        run_id="run-one",
        attempt_id=work.attempt.attempt_id,
        usage=None,
        response_sha256=None,
        error_code="MODEL_TIMEOUT",
        settled_at=T3,
    )
    assert (
        receipt.charged_tokens,
        receipt.charged_micro_usd,
        receipt.charged_output_bytes,
    ) == (150, 90, 100)
    reopened = module.NarrativeRunStore(auto.db_path)
    assert reopened.get_reservation("run-one", work.attempt.attempt_id) == receipt
    assert reopened.budget_snapshot("run-one").charged_micro_usd == 90
    known = reopened.settle_model_usage(
        run_id="run-one",
        attempt_id=work.attempt.attempt_id,
        usage=module.ModelUsage(30, 10),
        response_sha256=RESPONSE,
        error_code=None,
        settled_at=T9,
    )
    assert known.charged_micro_usd == 21


def test_actual_usage_over_bound_is_stored_and_blocks_further_http(tmp_path):
    module, auto, budget, generation, a, b = setup_run(tmp_path)
    work = claim(auto, generation, a)
    reserve(budget, work)
    receipt = budget.settle_model_usage(
        run_id="run-one",
        attempt_id=work.attempt.attempt_id,
        usage=module.ModelUsage(101, 50),
        response_sha256=RESPONSE,
        error_code=None,
        settled_at=T1,
    )
    assert receipt.charged_tokens == 151 and receipt.charged_micro_usd == 91
    assert budget.get_run("run-one").blocked
    with pytest.raises(module.RunBudgetExceededError):
        reserve(budget, claim(auto, generation, b))


def test_settle_is_run_scoped_and_conflicting_receipt_never_overwrites(tmp_path):
    module, auto, budget, generation, a, _ = setup_run(tmp_path)
    work = claim(auto, generation, a)
    reserve(budget, work)
    with pytest.raises(module.NarrativeRunError):
        budget.settle_model_usage(
            run_id="outside",
            attempt_id=work.attempt.attempt_id,
            usage=module.ModelUsage(0, 0),
            response_sha256=None,
            error_code="NO_HTTP",
            settled_at=T1,
        )
    receipt = budget.settle_model_usage(
        run_id="run-one",
        attempt_id=work.attempt.attempt_id,
        usage=module.ModelUsage(0, 0),
        response_sha256=None,
        error_code="NO_HTTP",
        settled_at=T1,
    )
    with pytest.raises(module.ReservationConflictError):
        budget.settle_model_usage(
            run_id="run-one",
            attempt_id=work.attempt.attempt_id,
            usage=module.ModelUsage(1, 0),
            response_sha256=None,
            error_code="NO_HTTP",
            settled_at=T1,
        )
    assert budget.get_reservation("run-one", work.attempt.attempt_id) == receipt


def test_final_output_is_separate_idempotent_charge_and_over_bound_blocks_run(tmp_path):
    module, auto, budget, generation, a, _ = setup_run(tmp_path)
    work = claim(auto, generation, a)
    reserve(budget, work)
    receipt = budget.settle_output(
        run_id="run-one",
        attempt_id=work.attempt.attempt_id,
        output_bytes=101,
        output_sha256=RESPONSE,
        settled_at=T1,
    )
    assert receipt.charged_output_bytes == 101
    assert budget.get_run("run-one").blocked
    assert (
        budget.settle_output(
            run_id="run-one",
            attempt_id=work.attempt.attempt_id,
            output_bytes=101,
            output_sha256=RESPONSE,
            settled_at=T2,
        )
        == receipt
    )
    with pytest.raises(module.ReservationConflictError):
        budget.settle_output(
            run_id="run-one",
            attempt_id=work.attempt.attempt_id,
            output_bytes=100,
            output_sha256=RESPONSE,
            settled_at=T2,
        )


@pytest.mark.parametrize("counts", [(True, 0), (-1, 0), (0, None), (1.5, 0)])
def test_usage_rejects_non_integer_or_unpaired_counts(counts):
    module = _module()
    with pytest.raises((ValueError, TypeError)):
        module.ModelUsage(*counts)


def test_anomalous_actual_total_is_exact_even_beyond_sqlite_sum_range(tmp_path):
    maximum = (1 << 63) - 1
    module, auto, budget, generation, a, b = setup_run(
        tmp_path,
        max_tokens=maximum,
        input_micro_usd_per_million_tokens=0,
        output_micro_usd_per_million_tokens=0,
    )
    one, two = claim(auto, generation, a), claim(auto, generation, b)
    reserve(budget, one)
    reserve(budget, two)
    budget.settle_model_usage(
        run_id="run-one",
        attempt_id=one.attempt.attempt_id,
        usage=module.ModelUsage(maximum, 0),
        response_sha256=RESPONSE,
        error_code=None,
        settled_at=T1,
    )
    assert budget.get_run("run-one").blocked
    assert budget.budget_snapshot("run-one").charged_tokens == maximum + 150


def _retry_claim(auto, generation, job, name):
    assert auto.reap_expired_attempts(now=T3, allowed_job_ids=(job.job_id,))
    auto.promote_ready_jobs(now=T9, allowed_job_ids=(job.job_id,))
    return auto.claim_next_ready(
        worker_id="replacement-model", attempt_id=name, lease_token=f"lease-{name}",
        now=T9, lease_until="2026-10-03T10:10:00Z", expected_generation=generation,
        allowed_job_ids=(job.job_id,),
    )


@pytest.mark.parametrize("usage_status", ["reserved", "unknown", "known"])
def test_retry_reuses_one_final_output_slot_and_keeps_every_provider_charge(tmp_path, usage_status):
    module, auto, budget, generation, a, _ = setup_run(tmp_path, max_output_bytes=100)
    first = claim(auto, generation, a)
    original = reserve(budget, first).record
    if usage_status != "reserved":
        original = budget.settle_model_usage(
            run_id="run-one", attempt_id=first.attempt.attempt_id,
            usage=module.ModelUsage(30, 10) if usage_status == "known" else None,
            response_sha256=RESPONSE if usage_status == "known" else None,
            error_code="MODEL_WORKER_LOST", settled_at=T2,
        )
    retry = _retry_claim(auto, generation, a, "replacement-a")
    admitted = reserve(budget, retry, now=T9)
    assert admitted.may_send_http and admitted.created
    # A lost response does not prove a free provider call or zero local output.
    assert budget.get_reservation("run-one", first.attempt.attempt_id) == original
    assert original.output_bytes is None
    meter = budget.budget_snapshot("run-one")
    assert meter.charged_output_bytes == 100
    assert meter.charged_tokens == original.charged_tokens + 150
    assert meter.charged_micro_usd == original.charged_micro_usd + 90


def test_retry_slot_growth_and_independent_job_slots_still_obey_output_limit(tmp_path):
    module, auto, budget, generation, a, b = setup_run(tmp_path, max_output_bytes=170)
    first = claim(auto, generation, a)
    reserve(budget, first, output_bytes_bound=80)
    reserve(budget, claim(auto, generation, b), output_bytes_bound=70)
    retry = _retry_claim(auto, generation, a, "larger-a")
    with pytest.raises(module.RunBudgetExceededError):
        reserve(budget, retry, output_bytes_bound=101, now=T9)
    assert budget.get_reservation("run-one", retry.attempt.attempt_id) is None
    reserve(budget, retry, output_bytes_bound=100, now=T9,
            input_tokens_bound=0, max_output_tokens=0)
    assert budget.budget_snapshot("run-one").charged_output_bytes == 170


@pytest.mark.parametrize("limit,cap", [("max_tokens", 150), ("max_micro_usd", 90)])
def test_reusing_output_slot_never_refunds_unknown_tokens_or_cost(tmp_path, limit, cap):
    module, auto, budget, generation, a, _ = setup_run(
        tmp_path, max_output_bytes=100, **{limit: cap})
    first = claim(auto, generation, a)
    reserve(budget, first)
    retry = _retry_claim(auto, generation, a, "still-billed-a")
    before = budget.budget_snapshot("run-one")
    with pytest.raises(module.RunBudgetExceededError):
        reserve(budget, retry, now=T9)
    assert budget.budget_snapshot("run-one") == before
    assert budget.get_reservation("run-one", retry.attempt.attempt_id) is None
