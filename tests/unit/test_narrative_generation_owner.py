"""Execution ownership ends independently of retained conservative billing."""

from dataclasses import asdict
import json

import pytest

from company_wiki.automation.models import HandlerError, HandlerMetrics, HandlerOutcome, HandlerResult
from company_wiki.automation.narrative_batch import _check_generation_owner, _generation_owner_finished
from company_wiki.automation.narrative_paid_response import PaidResponsePin
from unit.test_narrative_run_store import REQUEST, RESPONSE, T1, T3, claim, reserve, setup_run


def _finished_run(tmp_path, *, usage_settled=True, output_settled=True,
                  known=False, finish=True, paid=False, diagnostic_sha=False,
                  error="MODEL_HTTP_CLIENT_ERROR"):
    module, auto, ledger, generation, a, b = setup_run(tmp_path)
    first = claim(auto, generation, a)
    reserve(ledger, first)
    if paid:
        pin = PaidResponsePin(REQUEST, RESPONSE, f"objects/sha256/{RESPONSE[:2]}/{RESPONSE}.json",
                              2, "model-one", "http-fixture", "prompt-1", 200, 1)
        ledger.attach_paid_response(
            run_id="run-one", attempt_id=first.attempt.attempt_id,
            lease_token=first.attempt.lease_token, runtime_generation=generation,
            request_sha256=REQUEST, paid_response_json=pin.to_json(), recorded_at=T1,
        )
    if usage_settled:
        ledger.settle_model_usage(
            run_id="run-one", attempt_id=first.attempt.attempt_id,
            usage=module.ModelUsage(2, 1) if known else None,
            response_sha256=RESPONSE if paid or diagnostic_sha else None, error_code=error, settled_at=T1,
        )
    if output_settled:
        ledger.settle_output(run_id="run-one", attempt_id=first.attempt.attempt_id,
                             output_bytes=0, output_sha256=None, settled_at=T1)
    for work in (first, claim(auto, generation, b)):
        if finish or work is not first:
            auto.finish_attempt(
                attempt_id=work.attempt.attempt_id, lease_token=work.attempt.lease_token,
                runtime_generation=generation, finished_at=T1,
                result=HandlerResult(HandlerOutcome.TERMINAL_FAILURE, {}, (), (),
                                     HandlerMetrics(0, 0.0, 0), HandlerError(error, "fixture")),
            )
    return auto, ledger


@pytest.mark.parametrize("error", ["MODEL_HTTP_CLIENT_ERROR", "MODEL_HTTP_TRANSPORT"])
def test_explicit_new_run_releases_settled_terminal_owner_without_refunding_unknown(tmp_path, error):
    auto, ledger = _finished_run(tmp_path, error=error)
    before = tuple(asdict(row) for row in ledger.reservations_for_run("run-one"))
    budget = ledger.budget_snapshot("run-one")
    assert budget.unknown_reservations == 1 and budget.charged_tokens == 150
    pointer = tmp_path / "recovery.json"
    pointer.write_text(json.dumps({"schema_version": "narrative-generation-recovery/1",
                                  "automation_db": str(auto.db_path), "run_id": "run-one"}),
                       encoding="utf-8")
    assert _generation_owner_finished(auto.db_path, "run-one")
    _check_generation_owner(pointer, auto.db_path, "explicit-new-run")
    assert not pointer.exists()
    assert tuple(asdict(row) for row in ledger.reservations_for_run("run-one")) == before
    assert ledger.budget_snapshot("run-one") == budget


@pytest.mark.parametrize("options", [
    {"usage_settled": False}, {"output_settled": False, "finish": False}, {"finish": False},
    {"known": True, "output_settled": False, "finish": False}, {"paid": True},
    {"paid": True, "known": True},
])
def test_unfinished_execution_or_recoverable_paid_response_keeps_owner(tmp_path, options):
    auto, ledger = _finished_run(tmp_path, **options)
    before = tuple(asdict(row) for row in ledger.reservations_for_run("run-one"))
    assert not _generation_owner_finished(auto.db_path, "run-one")
    assert tuple(asdict(row) for row in ledger.reservations_for_run("run-one")) == before


def test_known_terminal_no_output_without_paid_response_remains_releasable(tmp_path):
    auto, _ = _finished_run(tmp_path, known=True)
    assert _generation_owner_finished(auto.db_path, "run-one")


@pytest.mark.parametrize("known", [False, True])
def test_native_finish_closes_failed_output_without_requiring_extra_manual_settlement(tmp_path, known):
    auto, ledger = _finished_run(tmp_path, known=known, output_settled=False)
    row, = ledger.reservations_for_run("run-one")
    assert row.output_bytes == 0 and row.output_settled_at is not None
    assert _generation_owner_finished(auto.db_path, "run-one")


@pytest.mark.parametrize("known", [False, True])
def test_diagnostic_final_text_hash_is_not_a_recoverable_complete_response(tmp_path, known):
    auto, ledger = _finished_run(tmp_path, known=known, diagnostic_sha=True)
    row, = ledger.reservations_for_run("run-one")
    assert row.response_sha256 == RESPONSE and row.paid_response_json is None
    before = asdict(row)
    assert _generation_owner_finished(auto.db_path, "run-one")
    assert asdict(ledger.reservations_for_run("run-one")[0]) == before


def test_reaped_attempt_without_native_completion_receipt_requires_origin_recovery(tmp_path):
    from dataclasses import replace
    from company_wiki.automation.models import RuntimeState
    from company_wiki.automation.store import AutomationStore
    from unit.test_narrative_run_store import create_run, seed_job
    from company_wiki.automation.narrative_run_store import NarrativeRunStore

    auto = AutomationStore(tmp_path / "reaped.db")
    job = replace(seed_job(auto, "crashed"), max_attempts=1)
    # Use the native planning API on a fresh database; no state SQL edits.
    other = AutomationStore(tmp_path / "crashed.db")
    other.put_event(auto.get_event(job.created_from_event_id))
    other.put_job(job)
    generation = other.set_runtime_gate(RuntimeState.ENABLED, updated_at=T1).control_generation
    ledger = NarrativeRunStore(other.db_path)
    create_run(ledger, (job,))
    work = claim(other, generation, job)
    reserve(ledger, work)
    ledger.settle_model_usage(run_id="run-one", attempt_id=work.attempt.attempt_id,
                              usage=None, response_sha256=None,
                              error_code="MODEL_HTTP_CLIENT_ERROR", settled_at=T1)
    ledger.settle_output(run_id="run-one", attempt_id=work.attempt.attempt_id,
                         output_bytes=0, output_sha256=None, settled_at=T1)
    assert other.reap_expired_attempts(now=T3, allowed_job_ids=(job.job_id,))
    attempt = other.get_attempt(work.attempt.attempt_id)
    assert attempt.finished_at is not None and attempt.result_json is None
    assert not _generation_owner_finished(other.db_path, "run-one")
