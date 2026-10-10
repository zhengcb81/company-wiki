"""Per-model-job immutable prompt admission in the existing AUTO ledger.

No source/model implementation dependency and no HTTP. Real persisted runs,
leases and accounting show that mixed prompts share one budget safely.
"""

import hashlib
import json

import pytest

from company_wiki.automation import narrative_run_store as run_module
from company_wiki.automation.models import (
    Event,
    Job,
    JobStatus,
    RiskClass,
    RuntimeState,
    canonical_json,
    make_job_key,
)
from company_wiki.automation.narrative_run_store import (
    NarrativeRunStore,
    RunBudgetExceededError,
    RunConflictError,
    RunScopeError,
)
from company_wiki.automation.store import AutomationStore

T0 = "2026-10-10T10:00:00Z"
T1 = "2026-10-10T10:01:00Z"
T2 = "2026-10-10T10:02:00Z"
SHA = hashlib.sha256(b"immutable-mixed-run").hexdigest()
REQUEST = hashlib.sha256(b"actual-model-request").hexdigest()
RAW_PROMPT = "1.7.0"
PROJECTION_PROMPT = "official-json/1.0.0"
ABSENT = object()


def state(tmp_path):
    auto = AutomationStore(tmp_path / "auto.db")
    jobs = []
    for name, job_type in (
        ("raw-summary", "source.narrative_summarize"),
        ("projection-summary", "source.narrative_summarize"),
        ("raw-select", "source.narrative_select"),
    ):
        event = Event(
            "event-" + name,
            "source.revision_registered",
            "source_revision",
            name,
            SHA,
            "{}",
            "test-policy",
            T0,
            T0,
        )
        auto.put_event(event)
        job = Job(
            job_id=name,
            job_key=make_job_key(
                job_type, "source_revision", name, SHA, "test-policy", "1.0.0"
            ),
            job_type=job_type,
            subject_type="source_revision",
            subject_id=name,
            input_hash=SHA,
            policy_version="test-policy",
            handler_version="1.0.0",
            risk_class=RiskClass.LOW,
            status=JobStatus.READY,
            priority=10,
            not_before=T0,
            max_attempts=2,
            created_from_event_id=event.event_id,
            created_at=T0,
            updated_at=T0,
            last_error_code=None,
            last_error_detail=None,
        )
        auto.put_job(job)
        jobs.append(job)
    generation = auto.set_runtime_gate(
        RuntimeState.ENABLED, updated_at=T0
    ).control_generation
    return auto, NarrativeRunStore(auto.db_path), generation, tuple(jobs)


def create_run(ledger, jobs, *, prompts=ABSENT, **limits):
    binding = {"schema_version": "generic-test-run-binding/1"}
    if prompts is not ABSENT:
        binding["job_prompt_versions"] = prompts
    options = {
        "run_id": "mixed",
        "input_hash": SHA,
        "job_ids": tuple(job.job_id for job in jobs),
        "model_id": "model",
        "prompt_version": RAW_PROMPT,
        "pricing_version": "price",
        "input_micro_usd_per_million_tokens": 300000,
        "output_micro_usd_per_million_tokens": 1200000,
        "max_tokens": 300,
        "max_micro_usd": 180,
        "max_output_bytes": 200,
        "created_at": T0,
        "binding_json": canonical_json(binding),
    }
    options.update(limits)
    return ledger.create_run(**options)


def prompts(jobs):
    return {jobs[0].job_id: RAW_PROMPT, jobs[1].job_id: PROJECTION_PROMPT}


def claim(auto, generation, job):
    return auto.claim_next_ready(
        worker_id="model-worker",
        attempt_id="attempt-" + job.job_id,
        lease_token="lease-" + job.job_id,
        now=T1,
        lease_until=T2,
        expected_generation=generation,
        allowed_job_ids=(job.job_id,),
    )


def reserve(ledger, work, prompt, **changes):
    options = {
        "run_id": "mixed",
        "job_id": work.job.job_id,
        "attempt_id": work.attempt.attempt_id,
        "lease_token": work.attempt.lease_token,
        "runtime_generation": work.attempt.runtime_generation,
        "request_sha256": REQUEST,
        "model_id": "model",
        "prompt_version": prompt,
        "pricing_version": "price",
        "input_tokens_bound": 100,
        "max_output_tokens": 50,
        "output_bytes_bound": 100,
        "now": T1,
    }
    options.update(changes)
    return ledger.reserve_model_attempt(**options)


def test_mixed_prompts_reserve_once_in_same_run_and_share_exact_caps(tmp_path):
    auto, ledger, generation, jobs = state(tmp_path)
    run = create_run(ledger, jobs, prompts=prompts(jobs))
    assert run.prompt_version == RAW_PROMPT
    raw, projected = (claim(auto, generation, j) for j in jobs[:2])
    a = reserve(ledger, raw, RAW_PROMPT)
    b = reserve(ledger, projected, PROJECTION_PROMPT)
    assert a.may_send_http and b.may_send_http
    assert a.record.run_id == b.record.run_id == "mixed"
    replay = reserve(ledger, projected, PROJECTION_PROMPT)
    assert replay.record == b.record and not replay.may_send_http and not replay.created
    snapshot = ledger.budget_snapshot("mixed")
    assert snapshot.charged_tokens == 300
    assert snapshot.charged_micro_usd == 180
    assert snapshot.charged_output_bytes == 200


@pytest.mark.parametrize("which", ["raw", "projection", "model", "pricing"])
def test_incorrect_frozen_prompt_or_model_pricing_never_inserts_reservation(
    tmp_path, which
):
    auto, ledger, generation, jobs = state(tmp_path)
    create_run(ledger, jobs, prompts=prompts(jobs))
    index = 0 if which == "raw" else 1
    work = claim(auto, generation, jobs[index])
    expected = RAW_PROMPT if index == 0 else PROJECTION_PROMPT
    wrong = PROJECTION_PROMPT if index == 0 else RAW_PROMPT
    changes = (
        {"model_id": "other"}
        if which == "model"
        else {"pricing_version": "other"}
        if which == "pricing"
        else {}
    )
    before = ledger.budget_snapshot("mixed")
    with pytest.raises(RunConflictError):
        reserve(ledger, work, wrong if not changes else expected, **changes)
    assert ledger.get_reservation("mixed", work.attempt.attempt_id) is None
    assert ledger.budget_snapshot("mixed") == before
    assert auto.get_attempt(work.attempt.attempt_id) == work.attempt


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        "wrong",
        {"raw-summary": True},
        {"raw-summary": 1},
        {"raw-summary": ""},
        {"raw-summary": " padded"},
    ],
)
def test_invalid_map_or_version_is_typed_and_does_not_create_run(tmp_path, bad):
    auto, ledger, _, jobs = state(tmp_path)
    with pytest.raises(RunConflictError):
        create_run(ledger, jobs, prompts=bad)
    assert ledger.get_run("mixed") is None
    assert auto.list_attempts(jobs[0].job_id) == ()


@pytest.mark.parametrize("change", ["missing", "extra", "non_model_job", "empty"])
def test_prompt_map_keys_exactly_match_scoped_model_jobs(tmp_path, change):
    _, ledger, _, jobs = state(tmp_path)
    mapping = prompts(jobs)
    if change == "missing":
        del mapping[jobs[1].job_id]
    elif change == "extra":
        mapping["outside-job"] = RAW_PROMPT
    elif change == "non_model_job":
        mapping[jobs[2].job_id] = RAW_PROMPT
    else:
        mapping = {}
    with pytest.raises(RunScopeError):
        create_run(ledger, jobs, prompts=mapping)
    assert ledger.get_run("mixed") is None


def test_model_map_does_not_default_non_model_job_to_run_prompt(tmp_path):
    auto, ledger, generation, jobs = state(tmp_path)
    create_run(ledger, jobs, prompts=prompts(jobs))
    work = claim(auto, generation, jobs[2])
    with pytest.raises(RunScopeError):
        reserve(ledger, work, RAW_PROMPT)
    assert ledger.get_reservation("mixed", work.attempt.attempt_id) is None
    assert ledger.budget_snapshot("mixed").charged_tokens == 0


@pytest.mark.parametrize("binding", [None, {"schema_version": "old/1"}])
def test_old_runs_without_map_keep_strict_single_prompt(tmp_path, binding):
    auto, ledger, generation, jobs = state(tmp_path)
    create_run(
        ledger, jobs, binding_json=None if binding is None else canonical_json(binding)
    )
    raw, projected = (claim(auto, generation, j) for j in jobs[:2])
    assert reserve(ledger, raw, RAW_PROMPT).may_send_http
    with pytest.raises(RunConflictError):
        reserve(ledger, projected, PROJECTION_PROMPT)
    assert ledger.get_reservation("mixed", projected.attempt.attempt_id) is None
    assert reserve(ledger, projected, RAW_PROMPT).may_send_http


def test_frozen_map_is_immutable_across_resume(tmp_path):
    _, ledger, _, jobs = state(tmp_path)
    run = create_run(ledger, jobs, prompts=prompts(jobs))
    assert create_run(ledger, tuple(reversed(jobs)), prompts=prompts(jobs)) == run
    mapping = prompts(jobs)
    mapping[jobs[1].job_id] = "different-prompt"
    with pytest.raises(RunConflictError):
        create_run(ledger, jobs, prompts=mapping)
    assert ledger.get_run("mixed") == run
    assert json.loads(run.binding_json)["job_prompt_versions"] == prompts(jobs)


@pytest.mark.parametrize("cap", ["max_tokens", "max_micro_usd", "max_output_bytes"])
def test_mixed_prompts_cannot_bypass_shared_remaining_budget(tmp_path, cap):
    auto, ledger, generation, jobs = state(tmp_path)
    create_run(
        ledger,
        jobs,
        prompts=prompts(jobs),
        **{cap: {"max_tokens": 150, "max_micro_usd": 90, "max_output_bytes": 100}[cap]},
    )
    raw, projected = (claim(auto, generation, j) for j in jobs[:2])
    reserve(ledger, raw, RAW_PROMPT)
    before = ledger.budget_snapshot("mixed")
    with pytest.raises(RunBudgetExceededError):
        reserve(ledger, projected, PROJECTION_PROMPT)
    assert ledger.get_reservation("mixed", projected.attempt.attempt_id) is None
    assert ledger.budget_snapshot("mixed") == before


def test_zero_model_scope_accepts_empty_frozen_map(tmp_path):
    _, ledger, _, jobs = state(tmp_path)
    run = create_run(ledger, (jobs[2],), prompts={})
    assert run.job_ids == (jobs[2].job_id,)
    assert ledger.budget_snapshot("mixed").charged_tokens == 0


def test_shared_model_prompt_lookup_uses_exact_job_and_preserves_old_fallback():
    binding = canonical_json(
        {"job_prompt_versions": {"raw": RAW_PROMPT, "projected": PROJECTION_PROMPT}}
    )
    assert (
        run_module.model_prompt_version(binding, job_id="raw", default_prompt="unused")
        == RAW_PROMPT
    )
    assert (
        run_module.model_prompt_version(
            binding, job_id="projected", default_prompt=RAW_PROMPT
        )
        == PROJECTION_PROMPT
    )
    for old_binding in (None, "{}", canonical_json({"schema_version": "old/1"})):
        assert (
            run_module.model_prompt_version(
                old_binding, job_id="old-job", default_prompt=RAW_PROMPT
            )
            == RAW_PROMPT
        )


def test_shared_model_prompt_lookup_does_not_default_unbound_job():
    binding = canonical_json({"job_prompt_versions": {"projected": PROJECTION_PROMPT}})
    with pytest.raises(RunScopeError):
        run_module.model_prompt_version(
            binding, job_id="outside", default_prompt=RAW_PROMPT
        )


@pytest.mark.parametrize("value", [None, [], {"projected": True}])
def test_shared_model_prompt_lookup_refuses_malformed_binding(value):
    with pytest.raises(RunConflictError):
        run_module.model_prompt_version(
            canonical_json({"job_prompt_versions": value}),
            job_id="projected",
            default_prompt=RAW_PROMPT,
        )
