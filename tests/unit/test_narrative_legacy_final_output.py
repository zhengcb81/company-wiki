"""Native output ownership: legacy attempts never overwrite failed receipts.

The finite provider is offline. Catalog, AUTO, verify, outbox, activation,
artifact reads and accounting are real; legacy partial results are assembled
as fixtures because creating new paid coverage-repair work is retired.
"""
from dataclasses import asdict, replace
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.execution_context import JobExecutionContext
from company_wiki.automation.models import (
    HandlerError, HandlerMetrics, HandlerOutcome, HandlerResult, JobStatus,
    RuntimeState, canonical_json, make_job_key,
)
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller
from company_wiki.automation.narrative_model_caller import NarrativeBudgetCallError
from company_wiki.automation.narrative_model_runtime import build_model_request
from company_wiki.automation.narrative_paid_response import PaidResponseArtifacts
from company_wiki.automation.narrative_projection import NarrativeEffectDispatcher
from company_wiki.automation.narrative_run_store import NarrativeRunStore, ReservationConflictError
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactStore, NarrativeArtifactNotVisibleError,
)
from integration.test_narrative_runtime_e2e import _event, _new_catalog
from unit.test_narrative_reading_transport import with_reading
from unit.test_narrative_summarize_handler import _context

T = "2026-09-28T22:01:00Z"
UNTIL = "2026-09-28T22:05:00Z"
V4 = "reading-model-input/4"


class FiniteModel:
    model_id, adapter_id, max_output_tokens = "configured", "offline-w04", 256

    def __init__(self):
        self.requests = []
        self.bodies = []

    def request_bytes(self, request):
        return canonical_json({"prompt": request.prompt_version, "data": request.data_json}).encode()

    def generate(self, request, response_sink=None):
        self.requests.append(request)
        task = json.loads(request.data_json)["material"]["tasks"][0]
        content = canonical_json({"drafts_by_task": {task["key"]: [{
            "text": "We launched a new product overseas.", "basis_parts": ["p1"], "modality": "actual",
        }]}})
        body = canonical_json({"content": content, "input_tokens": 73, "output_tokens": 19}).encode()
        self.bodies.append(body)
        if response_sink is not None:
            response_sink(body, http_status=200, duration_ms=1)
        return self.replay_response(request, body, http_status=200, duration_ms=1)

    def replay_response(self, request, body, *, http_status, duration_ms):
        data = json.loads(body)
        return NarrativeModelResponse(self.adapter_id, self.model_id, request.prompt_version,
            data["content"].encode(), data["input_tokens"], data["output_tokens"], duration_ms)


class Owned:
    def __init__(self, root, *, paid=False):
        root.mkdir(exist_ok=True)
        self.catalog, self.reader, indexed = _new_catalog(root, [{
            "name": "call.txt", "data": b"Full Conference Call Transcript\nCEO: We launched a new product overseas.\nCEO: We expanded customer qualification capacity overseas.\n",
            "title": "Acme operating update", "document_kind": "investor_call_transcript",
            "sidecar_overrides": {"fiscal_period": "Q2"},
        }])
        _, self.ref = next(iter(indexed.values()))
        event = _event(self.reader, self.ref, event_id="w04-event")
        self.auto = AutomationStore(root / "AUTO.sqlite")
        self.auto.put_event(event)
        # The canonical select context must use the real source event. The
        # initial empty dependency is ignored by the select handler.
        self.jobs = {}
        base = _context(with_reading()).job
        for kind, status in (("select", JobStatus.READY), ("summarize", JobStatus.PLANNED), ("verify", JobStatus.PLANNED)):
            job = replace(base, job_id=kind, job_type="source.narrative_" + kind,
                created_from_event_id=event.event_id, subject_type=event.subject_type,
                subject_id=event.subject_id, input_hash=event.input_hash, policy_version=event.policy_version,
                created_at=T, updated_at=T, not_before=T,
                job_key=make_job_key("source.narrative_" + kind, event.subject_type,
                    event.subject_id, event.input_hash, event.policy_version, base.handler_version), status=status)
            self.auto.put_job(job)
            self.jobs[kind] = job
        self.auto.add_job_dependency("summarize", "select")
        self.auto.add_job_dependency("verify", "select")
        self.auto.add_job_dependency("verify", "summarize")
        self.generation = self.auto.set_runtime_gate(RuntimeState.ENABLED, updated_at=T).control_generation
        self.claim("select", "select-1")
        selected_result = NarrativeSelectHandler(reader=self.reader)(self.context())
        assert selected_result.outcome is HandlerOutcome.SUCCEEDED, selected_result
        self.selected = with_reading(NarrativeSelectResult.from_dict(selected_result.result))
        assert len(build_model_request(self.selected, reading_projection_version=V4).data_json) > 0
        self.finish(replace(selected_result, result=self.selected.to_dict()))
        self.event = event
        self.runs = NarrativeRunStore(self.auto.db_path)
        self.model = FiniteModel()
        request = build_model_request(self.selected, reading_projection_version=V4)
        self.runs.create_run(run_id="w04-owned", input_hash="c" * 64, job_ids=tuple(self.jobs),
            model_id=self.model.model_id, prompt_version=request.prompt_version, pricing_version="fixture/1",
            input_micro_usd_per_million_tokens=300000, output_micro_usd_per_million_tokens=1200000,
            max_tokens=500000, max_micro_usd=1000000, max_output_bytes=2097152, created_at=T)
        self.paid = PaidResponseArtifacts(LocalNarrativeObjectStore(root / "paid"), max_response_bytes=262144)
        self.caller = BudgetedNarrativeCaller(store=self.runs, run_id="w04-owned", model=self.model,
            paid_responses=self.paid if paid else None, clock=lambda: T)
        self.artifacts = NarrativeArtifactStore(self.catalog.store, LocalNarrativeObjectStore(self.catalog.config.catalog_dir))

    def claim(self, kind, attempt_id):
        self.auto.promote_ready_jobs(now=T, allowed_job_ids=(kind,))
        self.current = self.auto.claim_next_ready(worker_id="w04-owned", attempt_id=attempt_id,
            lease_token=attempt_id + "-lease", now=T, lease_until=UNTIL,
            expected_generation=self.generation, allowed_job_ids=(kind,))
        assert self.current is not None

    def context(self):
        return JobExecutionContext.from_snapshot(self.auto.read_execution_snapshot(self.current, now=T), checkpoint=lambda: None)

    def finish(self, result):
        return self.auto.finish_attempt(attempt_id=self.current.attempt.attempt_id,
            lease_token=self.current.attempt.lease_token, runtime_generation=self.generation, finished_at=T,
            result=result, retry_not_before=T if result.outcome is HandlerOutcome.RETRYABLE else None)

    def legacy_two(self, *, fallback=False, finish_second=True):
        """Create historical DTOs through native metering, without old dispatch."""
        self.claim("summarize", "summary-1")
        request = build_model_request(self.selected, reading_projection_version=V4)
        response, metrics = self.caller.generate(self.context(), request)
        first = NarrativeSummarizeHandler._completed_result(self.selected, self.selected.prompt_review,
            response, reading_projection_version=V4)
        partial = HandlerResult(HandlerOutcome.RETRYABLE,
            {"coverage_partial": True, "summary": first.to_dict(), "uncovered_task_keys": ["t2"], "execution": {}},
            (), (), metrics, HandlerError("SUMMARY_COVERAGE_PARTIAL", "historical fixture"))
        self.finish(partial)
        self.first_record = asdict(self.runs.get_reservation("w04-owned", "summary-1"))
        self.claim("summarize", "summary-2")
        request2 = build_model_request(self.selected, reading_projection_version=V4, only_tasks=frozenset({"t2"}), target_claims=1)
        response2, metrics2 = self.caller.generate(self.context(), request2)
        repaired = NarrativeSummarizeHandler._completed_result(self.selected, self.selected.prompt_review,
            response2, reading_projection_version=V4)
        result = first.to_dict()
        if not fallback:
            result["draft"]["claims"] += repaired.to_dict()["draft"]["claims"]
            result["draft"]["claims"][-1]["claim_id"] = "t2-r1"
            result["model"] = repaired.to_dict()["model"]
        result["draft"]["status"] = "needs_review"
        if finish_second:
            self.finish(HandlerResult(HandlerOutcome.SUCCEEDED, result, (), (), metrics2, None))

    def attach_historical_paid_pins(self):
        for index, record in enumerate(self.runs.reservations_for_run("w04-owned")):
            request = self.model.requests[index]
            pin = self.paid.put(self.model.bodies[index], request_sha256=record.request_sha256,
                model_id=self.model.model_id, adapter_id=self.model.adapter_id,
                prompt_version=request.prompt_version, http_status=200, duration_ms=1)
            self.runs.attach_paid_response(run_id="w04-owned", attempt_id=record.attempt_id,
                lease_token=record.attempt_id + "-lease", runtime_generation=self.generation,
                request_sha256=record.request_sha256, paid_response_json=pin.to_json(), recorded_at=T)
        self.first_record = asdict(self.runs.get_reservation("w04-owned", "summary-1"))

    def publish(self, monkeypatch):
        self.claim("verify", "verify-1")
        verified = NarrativeVerifyHandler(reader=self.reader,
            reading_model_projection=lambda _: V4)(self.context())
        assert verified.outcome is HandlerOutcome.SUCCEEDED, verified
        self.finish(verified)
        self.effect_id = verified.effects[0].effect_id
        with monkeypatch.context() as fault:
            def hold(*args, **kwargs):
                raise NarrativeArtifactNotVisibleError("controlled activation gap")
            fault.setattr(self.artifacts, "activate", hold)
            receipt = NarrativeEffectDispatcher(self.auto, self.artifacts).dispatch_next(
                worker_id="w04-publisher", now=T, lease_until=UNTIL, expected_generation=self.generation)
            assert receipt.status == "activation_pending"

    def document(self, **kwargs):
        binding = SimpleNamespace(events=(self.event,), source_facts=(), generation_manifests={}, reused_artifact_pins={}, verified_reuse_keys=())
        request = SimpleNamespace(run_id="w04-owned", schema_version="narrative-batch-request/1")
        return batch._final_documents(request, binding, self.auto, self.runs, self.artifacts, **kwargs)[0]

    def resume(self):
        self.auto = AutomationStore(self.auto.db_path)
        self.runs = NarrativeRunStore(self.auto.db_path)
        assert NarrativeEffectDispatcher(self.auto, self.artifacts).reconcile_prepared(activated_at=T) == (self.effect_id,)

    def records(self):
        return [asdict(row) for row in self.runs.reservations_for_run("w04-owned")]


@pytest.mark.parametrize("with_pins", [False, True], ids=["historical-v4-no-pins", "completed-historical-two-pins"])
def test_legacy_two_attempts_resume_real_final_without_overwriting_partial_zero(tmp_path, monkeypatch, with_pins):
    own = Owned(tmp_path)
    try:
        own.legacy_two()
        if with_pins:
            own.attach_historical_paid_pins()
        before_budget = own.runs.budget_snapshot("w04-owned")
        own.publish(monkeypatch)
        assert own.document()["status"] == "activation_pending"
        own.resume()
        result = own.document()
        assert result["status"] == "completed"
        assert own.records()[0] == own.first_record
        final = own.records()[1]
        assert final["output_bytes"] == result["artifact_ref"]["byte_size"]
        assert final["output_sha256"] == result["artifact_ref"]["content_sha256"]
        assert own.runs.budget_snapshot("w04-owned").charged_tokens == before_budget.charged_tokens == 184
        assert own.runs.budget_snapshot("w04-owned").charged_micro_usd == before_budget.charged_micro_usd
        assert own.runs.budget_snapshot("w04-owned").charged_output_bytes == final["output_bytes"]
        before = own.records()
        assert own.document() == result
        assert own.records() == before and len(own.model.requests) == 2
    finally:
        own.catalog.close()


def test_read_only_final_probe_never_settles_or_compacts_legacy_rows(tmp_path, monkeypatch):
    own = Owned(tmp_path)
    try:
        own.legacy_two()
        own.publish(monkeypatch)
        own.resume()
        before = own.records()
        assert own.document(read_only=True)["status"] == "completed"
        assert own.records() == before
    finally:
        own.catalog.close()


@pytest.mark.parametrize("all_zero", [False, True], ids=["pending-second-slot", "all-slots-zero"])
def test_legacy_fallback_cannot_reassign_first_immutable_zero_to_newer_call(tmp_path, monkeypatch, all_zero):
    own = Owned(tmp_path)
    try:
        own.legacy_two(fallback=True)
        if all_zero:
            own.runs.settle_output(run_id="w04-owned", attempt_id="summary-2", output_bytes=0,
                output_sha256=None, settled_at=T)
        own.publish(monkeypatch)
        own.resume()
        before = own.records()
        result = own.document()
        assert result["status"] == "output_accounting_unresolved"
        assert "LEGACY_FINAL_OUTPUT_OWNER_UNRESOLVED" in result["errors"]
        assert result["artifact_ref"] is not None  # exact final stays readable
        assert own.records() == before and len(own.model.requests) == 2
    finally:
        own.catalog.close()


def test_same_final_pin_is_idempotent_and_different_pin_is_rejected(tmp_path, monkeypatch):
    own = Owned(tmp_path)
    try:
        own.legacy_two()
        own.publish(monkeypatch)
        own.resume()
        own.document()
        from company_wiki.automation.terminal_receipt_contracts import FinalArtifactPin
        version = own.artifacts.visible_version_for_effect(own.effect_id)
        pin = FinalArtifactPin(version.effect_id, version.artifact_version_id, version.content_sha256,
            version.byte_size, own.ref.document_id, own.ref.source_id, own.ref.content_sha256)
        before = own.records()
        own.runs.settle_published_summary_output(run_id="w04-owned", summary_job_id="summarize",
            verify_job_id="verify", final_artifact=pin, settled_at=T)
        with pytest.raises(ReservationConflictError):
            own.runs.settle_published_summary_output(run_id="w04-owned", summary_job_id="summarize",
                verify_job_id="verify", final_artifact=replace(pin, artifact_sha256="f" * 64), settled_at=T)
        assert own.records() == before
    finally:
        own.catalog.close()


def test_ordinary_single_paid_operation_recovers_then_activates_with_no_new_reservation(tmp_path, monkeypatch):
    own = Owned(tmp_path, paid=True)
    try:
        own.claim("summarize", "paid-original")
        request = build_model_request(own.selected, reading_projection_version=V4)
        own.caller.generate(own.context(), request)
        # Paid bytes and usage are durable; only result/activation is missing.
        own.finish(HandlerResult(HandlerOutcome.RETRYABLE, {}, (), (), HandlerMetrics(0, 0, 0),
            HandlerError("IO_TRANSIENT", "controlled post-payment interruption")))
        assert own.runs.get_reservation("w04-owned", "paid-original").output_bytes == 0
        own.claim("summarize", "paid-recovery")
        own.runs = NarrativeRunStore(own.auto.db_path)
        caller = BudgetedNarrativeCaller(store=own.runs, run_id="w04-owned", model=own.model,
            paid_responses=own.paid, clock=lambda: T)
        completed = NarrativeSummarizeHandler(model=None, model_caller=caller,
            reading_model_projection=lambda _: V4)(own.context())
        assert completed.outcome is HandlerOutcome.SUCCEEDED, completed
        own.finish(completed)
        assert len(own.model.requests) == 1 and len(own.records()) == 1
        assert own.records()[0]["attempt_id"] == "paid-original"
        own.publish(monkeypatch)
        assert own.document()["status"] == "activation_pending"
        own.resume()
        assert own.document()["status"] == "completed"
        assert len(own.model.requests) == 1 and len(own.records()) == 1
        assert own.runs.budget_snapshot("w04-owned").charged_tokens == 92
        assert own.records()[0]["output_bytes"] > 0
    finally:
        own.catalog.close()


def test_unfinished_historical_two_paid_pins_remain_named_unavailable_without_new_post(tmp_path):
    own = Owned(tmp_path)
    try:
        own.legacy_two(finish_second=False)
        own.attach_historical_paid_pins()
        before = own.records()
        caller = BudgetedNarrativeCaller(store=own.runs, run_id="w04-owned", model=own.model,
            paid_responses=own.paid, clock=lambda: T)
        with pytest.raises(NarrativeBudgetCallError) as failure:
            caller.generate(own.context(), own.model.requests[1])
        assert failure.value.code == "MODEL_PAID_RESPONSE_UNAVAILABLE"
        assert own.records() == before and len(own.model.requests) == 2
    finally:
        own.catalog.close()
