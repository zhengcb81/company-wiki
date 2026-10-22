"""Independent review counterexamples; no product files or providers mutated."""
import os
from pathlib import Path
import sys
from dataclasses import replace
import json
import sqlite3

import pytest

WT = Path(os.environ["W04_REVIEW_ROOT"])
sys.path.insert(0, str(WT/"src"))
sys.path.insert(0, str(WT/"tests"))
from unit.test_narrative_legacy_final_output import Owned, T, V4
from company_wiki.automation.narrative_run_store import RunScopeError, RunConflictError
from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller, NarrativeBudgetCallError
from company_wiki.automation.narrative_model_runtime import build_model_request
from company_wiki.automation.narrative_paid_response import PaidResponseArtifacts
from company_wiki.source_catalog.narrative_artifact_store import LocalNarrativeObjectStore
from company_wiki.automation.terminal_receipt_contracts import FinalArtifactPin
from company_wiki.automation.models import HandlerResult, HandlerOutcome, HandlerMetrics, HandlerError


def pin_for(owned):
    version = owned.artifacts.visible_version_for_effect(owned.effect_id)
    return FinalArtifactPin(version.effect_id, version.artifact_version_id, version.content_sha256,
        version.byte_size, owned.ref.document_id, owned.ref.source_id, owned.ref.content_sha256)


@pytest.mark.parametrize("wrong_job", ["select", "not-in-run"])
def test_cannot_charge_final_to_an_unrelated_native_job(tmp_path, monkeypatch, wrong_job):
    owned = Owned(tmp_path)
    try:
        owned.legacy_two()
        owned.publish(monkeypatch)
        owned.resume()
        before = owned.records()
        with pytest.raises(RunScopeError):
            owned.runs.settle_published_summary_output(run_id="w04-owned", summary_job_id=wrong_job,
                verify_job_id="verify", final_artifact=pin_for(owned), settled_at=T)
        assert owned.records() == before
        assert len(owned.model.requests) == 2
    finally:
        owned.catalog.close()


def test_successful_model_record_not_equal_to_consumed_verify_is_refused(tmp_path, monkeypatch):
    owned = Owned(tmp_path)
    try:
        owned.legacy_two()
        owned.publish(monkeypatch)
        owned.resume()
        before = owned.records()
        with sqlite3.connect(owned.auto.db_path) as connection:
            row = connection.execute("SELECT result_json FROM attempts WHERE attempt_id='summary-2'").fetchone()
            payload = json.loads(row[0])
            payload["result"]["model"]["response_sha256"] = "e"*64
            connection.execute("UPDATE attempts SET result_json=? WHERE attempt_id='summary-2'", (json.dumps(payload),))
        with pytest.raises(RunConflictError, match="different successful summary"):
            owned.runs.settle_published_summary_output(run_id="w04-owned", summary_job_id="summarize",
                verify_job_id="verify", final_artifact=pin_for(owned), settled_at=T)
        assert owned.records() == before
        assert len(owned.model.requests) == 2
    finally:
        owned.catalog.close()


def test_missing_single_paid_object_cannot_dispatch_or_release_charge(tmp_path):
    owned = Owned(tmp_path, paid=True)
    try:
        owned.claim("summarize", "paid-original")
        request = build_model_request(owned.selected, reading_projection_version=V4)
        owned.caller.generate(owned.context(), request)
        owned.finish(HandlerResult(HandlerOutcome.RETRYABLE, {}, (), (), HandlerMetrics(0,0,0),
            HandlerError("IO_TRANSIENT", "review-controlled interruption")))
        owned.claim("summarize", "paid-recovery")
        before = owned.records()
        budget = owned.runs.budget_snapshot("w04-owned")
        absent = PaidResponseArtifacts(LocalNarrativeObjectStore(tmp_path/"absent-paid-objects"), max_response_bytes=262144)
        caller = BudgetedNarrativeCaller(store=owned.runs, run_id="w04-owned", model=owned.model,
            paid_responses=absent, clock=lambda:T)
        with pytest.raises(NarrativeBudgetCallError) as caught:
            caller.generate(owned.context(), request)
        assert caught.value.code == "MODEL_PAID_RESPONSE_UNAVAILABLE"
        assert owned.records() == before
        assert owned.runs.budget_snapshot("w04-owned").charged_tokens == budget.charged_tokens
        assert len(owned.model.requests) == 1
    finally:
        owned.catalog.close()


def test_final_native_settlement_cannot_exceed_reserved_output(tmp_path, monkeypatch):
    owned = Owned(tmp_path)
    try:
        owned.legacy_two()
        owned.publish(monkeypatch)
        owned.resume()
        before = owned.records()
        # A forged byte size cannot charge a different artifact while keeping
        # the old effect/hash. The rejection must be atomic.
        with pytest.raises(Exception) as caught:
            owned.runs.settle_published_summary_output(run_id="w04-owned", summary_job_id="summarize",
                verify_job_id="verify", final_artifact=replace(pin_for(owned), byte_size=pin_for(owned).byte_size+1), settled_at=T)
        assert type(caught.value).__name__ == "ReservationConflictError"
        assert owned.records() == before
    finally:
        owned.catalog.close()
