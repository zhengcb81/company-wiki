"""Six independent minimal W04 probes, actual functions/SQLite, no network."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import stat
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
network_attempts = []
def blocked_network(*args, **kwargs):
    network_attempts.append("network")
    raise RuntimeError("Independent offline probe attempted network")
socket.socket.connect = blocked_network
socket.create_connection = blocked_network

from company_wiki.automation.models import (
    Effect, EffectStatus, Event, HandlerError, HandlerMetrics, HandlerOutcome,
    HandlerResult, Job, JobStatus, RiskClass, RuntimeState, canonical_json,
    make_effect_key, make_job_key,
)
from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_failed_final import fit_failed_final_result
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel, ModelOutputTruncatedError
from company_wiki.automation.narrative_model import FailedFinalDiagnostic, NarrativeModelRequest
from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller, NarrativeBudgetCallError
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore

T0, T1, T2, T9 = ("2026-10-11T00:00:00Z", "2026-10-11T00:01:00Z", "2026-10-11T00:02:00Z", "2026-10-11T00:09:00Z")
SHA = hashlib.sha256(b"independent bounded W04 source").hexdigest()
REQUEST = NarrativeModelRequest("1.1.0", "data only", "{}", "a" * 64)
LIMIT = 16384

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def bytesize(result):
    return len(canonical_json(result.to_dict()).encode("utf-8"))

def failbase(*, detail="primary", result=None):
    return HandlerResult(HandlerOutcome.TERMINAL_FAILURE, result or {}, (), (),
        HandlerMetrics(tokens=1234, cost_usd=0.004321, duration_ms=9, reasoning_tokens=1),
        HandlerError("MODEL_OUTPUT_TRUNCATED", detail))

def body(content, *, usage=None, ascii=False):
    value = {"model": "model", "choices": [{"finish_reason": "length", "message": {
        "content": content, "reasoning_content": "NEVER_STORE_INDEPENDENT_REASONING"}}]}
    if usage is not None:
        value["usage"] = usage
    return json.dumps(value, ensure_ascii=ascii, separators=(",", ":")).encode("utf-8")

def decode(raw):
    http = NarrativeHTTPModel(model_id="model", endpoint="https://fixtures.invalid/chat/completions",
                              api_key_env="NOT_READ_IN_INDEPENDENT_REVIEW", max_output_tokens=64)
    try:
        http._response(REQUEST, raw, time.monotonic())
    except ModelOutputTruncatedError as error:
        return error
    raise AssertionError("length result did not retain original error")

def seed_job(store, name, *, status=JobStatus.READY, kind="source.narrative_summarize"):
    event = Event("event-" + name, "source.revision_registered", "source_revision", name,
                  SHA, "{}", "independent", T0, T0)
    store.put_event(event)
    job = Job("job-" + name, make_job_key(kind, "source_revision", name, SHA, "independent", "1.0.0"),
              kind, "source_revision", name, SHA, "independent", "1.0.0", RiskClass.LOW,
              status, 0, T0, 3, event.event_id, T0, T0, None, None)
    store.put_job(job)
    return job

def create_run(ledger, jobs, name):
    return ledger.create_run(run_id=name, input_hash=SHA, job_ids=tuple(j.job_id for j in jobs),
        model_id="model", prompt_version=REQUEST.prompt_version, pricing_version="independent-price/1",
        input_micro_usd_per_million_tokens=300000, output_micro_usd_per_million_tokens=1200000,
        max_tokens=10000, max_micro_usd=1000000, max_output_bytes=8192, created_at=T0)

def dump(store):
    connection = sqlite3.connect(store.db_path)
    try:
        return tuple(connection.iterdump())
    finally:
        connection.close()

class DecoderOnlyModel:
    model_id, max_output_tokens = "model", 64
    def __init__(self, response_body):
        self.response_body, self.calls = response_body, 0
    def request_bytes(self, request):
        return b"independent bounded request"
    def generate(self, request):
        self.calls += 1
        return decode(self.response_body) if False else self._error()
    def _error(self):
        raise decode(self.response_body)

def actual_caller(root, content, usage, *, with_verify=False):
    auto = AutomationStore(root / "auto.db")
    summary = seed_job(auto, "summary")
    jobs = [summary]
    if with_verify:
        jobs.append(seed_job(auto, "verify", status=JobStatus.PLANNED, kind="source.narrative_verify"))
    ledger = NarrativeRunStore(auto.db_path)
    run = create_run(ledger, jobs, "independent-run")
    gate = auto.set_runtime_gate(RuntimeState.ENABLED, updated_at=T1)
    claimed = auto.claim_next_ready(worker_id="independent", attempt_id="attempt", lease_token="lease",
        now=T1, lease_until=T2, expected_generation=gate.control_generation, allowed_job_ids=(summary.job_id,))
    assert claimed is not None
    context = SimpleNamespace(job=claimed.job, attempt=claimed.attempt, checkpoint=lambda: None)
    raw = body(content, usage=usage)
    model = DecoderOnlyModel(raw)
    caller = BudgetedNarrativeCaller(store=ledger, run_id=run.run_id, model=model,
                                    final_output_bytes_bound=1024, clock=lambda: T1)
    try:
        caller.generate(context, REQUEST)
    except NarrativeBudgetCallError as error:
        assert error.code == "MODEL_OUTPUT_TRUNCATED"
        return auto, ledger, run, model, caller, context, raw, error
    raise AssertionError("length failure became success")


def main():
    expected = json.loads((OUT.parent / "w04-main-reception/FINAL_SHA_RECEIPT.json").read_text(encoding="utf-8"))
    owned_paths = expected["owned_changed_sha256"]
    source_before = {name: sha(ROOT / name) for name in owned_paths}
    assert source_before == owned_paths, "W04 stable source snapshot changed before review"
    w03_paths = ("src/company_wiki/source_catalog/narrative_candidates.py", "src/company_wiki/source_catalog/narrative_evidence.py")
    w03_before = {name: sha(ROOT / name) for name in w03_paths}
    configs = [ROOT / "config/source_catalog.yaml", ROOT / "config.yaml"]
    config_before = {str(p): sha(p) for p in configs if p.exists()}
    handoff_files = ("HANDOFF.md", "OWNED_DIFF.txt", "FINAL_SHA_RECEIPT.json")
    handoff_before = {name: sha(OUT.parent / "w04-main-reception" / name) for name in handoff_files}
    environment_before = dict(os.environ)
    owned = Path(tempfile.mkdtemp(prefix="w04-independent-"))
    receipt = {"schema_version": "w04-independent-review/1", "probes": [], "owned_temp": str(owned),
               "source_before_sha256": source_before, "source_handoff_sha256": handoff_before,
               "provider_calls": 0, "model_calls": 0, "new_cost_usd": 0}
    start = time.monotonic()
    def probe(name, function):
        try:
            result = function()
            receipt["probes"].append({"name": name, "status": "pass", "details": result})
        except BaseException as exc:
            receipt["probes"].append({"name": name, "status": "fail", "error": repr(exc)})
        print(json.dumps(receipt["probes"][-1], ensure_ascii=False), flush=True)

    def existing_envelope():
        content = '\x00"\\😀e\u0301营' * 3000
        diag = FailedFinalDiagnostic.from_observation(provider_body=b"exact independent wire", content=content)
        base = failbase(detail="原错误😀" * 200, result={"previous_observation": '\x00"\\' * 600})
        assert bytesize(base) < LIMIT
        result = fit_failed_final_result(base, diag)
        assert bytesize(result) < LIMIT
        assert result.result["previous_observation"] == base.result["previous_observation"]
        assert result.error == base.error and result.metrics == base.metrics
        saved = FailedFinalDiagnostic.from_dict(result.result["failed_final"])
        assert saved.clipped and content.startswith(saved.final_prefix)
        assert saved.final_content_sha256 == hashlib.sha256(content.encode()).hexdigest()
        assert HandlerResult.from_dict(json.loads(canonical_json(result.to_dict()))).to_dict() == result.to_dict()
        k = len(saved.final_prefix)
        more = replace(saved, final_prefix=content[:k + 1], prefix_bytes=len(content[:k + 1].encode()))
        extended = replace(result, result={**result.result, "failed_final": more.to_dict()})
        assert bytesize(extended) >= LIMIT
        return {"base_bytes": bytesize(base), "saved_bytes": bytesize(result), "one_codepoint_more_bytes": bytesize(extended),
                "saved_prefix_bytes": saved.prefix_bytes, "error_and_meter_unchanged": True}
    probe("existing-envelope-escaping-and-maximal-codepoint", existing_envelope)

    def exact_boundary():
        results = []
        for content in (None, ""):
            diag = FailedFinalDiagnostic.from_observation(provider_body=b"wire", content=content)
            base0 = failbase()
            metadata = replace(base0, result={"failed_final": diag.to_dict()})
            fill = LIMIT - bytesize(metadata)
            exact = replace(base0, error=replace(base0.error, detail=base0.error.detail + "x" * fill))
            exact_candidate = replace(exact, result={"failed_final": diag.to_dict()})
            assert bytesize(exact_candidate) == LIMIT
            rejected = fit_failed_final_result(exact, diag)
            assert rejected == exact and bytesize(rejected) < LIMIT
            one_less = replace(exact, error=replace(exact.error, detail=exact.error.detail[:-1]))
            fitted = fit_failed_final_result(one_less, diag)
            assert bytesize(fitted) == LIMIT - 1
            assert fitted.result["failed_final"] == diag.to_dict()
            assert diag.final_content_bytes is (None if content is None else 0)
            assert diag.final_content_sha256 == (None if content is None else hashlib.sha256(b"").hexdigest())
            results.append({"observed": content is not None, "metadata_exact_rejected_bytes": bytesize(exact_candidate),
                            "one_less_saved_bytes": bytesize(fitted), "meter_unchanged": fitted.metrics == one_less.metrics})
        return results
    probe("exact-16384-metadata-none-versus-empty", exact_boundary)

    def unknown_meter():
        results = []
        for index, content in enumerate((None, "")):
            target = owned / ("unknown-" + str(index));target.mkdir()
            auto, ledger, run, model, caller, context, raw, error = actual_caller(target, content,
                {"prompt_tokens": 73, "completion_tokens": True})
            record, = ledger.reservations_for_run(run.run_id)
            snapshot = ledger.budget_snapshot(run.run_id)
            assert record.usage_status == "unknown"
            assert record.charged_tokens == record.reserved_tokens and record.charged_micro_usd == record.reserved_micro_usd
            assert error.metrics.tokens == record.reserved_tokens
            assert error.metrics.cost_usd == record.reserved_micro_usd / 1000000
            expected_hash = None if content is None else hashlib.sha256(b"").hexdigest()
            assert record.response_sha256 == expected_hash
            assert record.response_sha256 != hashlib.sha256(raw).hexdigest()
            assert record.output_bytes == 0 and record.output_sha256 is None
            assert error.failed_final.final_content_bytes is (None if content is None else 0)
            assert snapshot.unknown_reservations == 1 and snapshot.unsettled_reservations == 0
            before = dump(auto)
            try:
                caller.generate(context, REQUEST)
            except NarrativeBudgetCallError as repeated:
                assert repeated.code == "MODEL_REQUEST_ALREADY_RESERVED"
            else:
                raise AssertionError("same attempt was sent twice")
            assert model.calls == 1 and dump(auto) == before
            results.append({"observed_final": content is not None, "usage_status": record.usage_status,
                "reserved_tokens": record.reserved_tokens, "charged_tokens": record.charged_tokens,
                "reserved_micro_usd": record.reserved_micro_usd, "charged_micro_usd": record.charged_micro_usd,
                "response_sha256": record.response_sha256, "provider_sha256": hashlib.sha256(raw).hexdigest(),
                "output_bytes": 0, "same_attempt_decoder_calls": model.calls, "replay_db_unchanged": True})
        return results
    probe("real-ledger-partial-invalid-usage-none-empty-paid-replay", unknown_meter)

    def exact_hashes():
        content = 'e\u0301\r\n\ufeff营\x00'
        raw_a, raw_b = body(content, ascii=False), body(content, ascii=True)
        a, b = decode(raw_a).failed_final, decode(raw_b).failed_final
        assert a.provider_response_sha256 == hashlib.sha256(raw_a).hexdigest()
        assert b.provider_response_sha256 == hashlib.sha256(raw_b).hexdigest()
        assert a.provider_response_sha256 != b.provider_response_sha256
        assert a.final_content_sha256 == b.final_content_sha256 == hashlib.sha256(content.encode()).hexdigest()
        assert a.final_prefix == b.final_prefix == content and not a.clipped
        normalized = decode(body('é\r\n\ufeff营\x00')).failed_final
        assert normalized.final_content_sha256 != a.final_content_sha256
        assert "NEVER_STORE_INDEPENDENT_REASONING" not in canonical_json(a.to_dict())
        return {"nfd_exact_bytes": a.final_content_bytes, "nfc_hash_distinct": True,
                "different_raw_encodings_same_final_hash": True, "bom_controls_crlf_preserved": True}
    probe("raw-entity-versus-final-utf8-no-normalization", exact_hashes)

    def scoped_delivery():
        results = []
        for mode in ("pending", "failed", "delivered"):
            target = owned / ("outbox-" + mode);target.mkdir()
            auto = AutomationStore(target / "auto.db")
            own_a = seed_job(auto, "own-a", kind="source.narrative_verify")
            own_b = seed_job(auto, "own-b", status=JobStatus.PLANNED, kind="source.narrative_verify")
            foreign = []
            for i in range(25):
                job = seed_job(auto, f"foreign-{i}", kind="source.narrative_verify");foreign.append(job)
                effect = Effect(f"foreign-effect-{i}", make_effect_key("artifact_write", str(i), SHA, "1.0.0"),
                    job.job_id, "artifact_write", str(i), None, SHA, None, EffectStatus.PENDING, T0, None)
                auto.put_effect(effect)
                auto.put_outbox_entry(f"opaque-foreign-{i}", effect.effect_id, "{}", ("pending", "leased", "failed")[i % 3], T0)
            for i, (job, status) in enumerate(((own_a, EffectStatus.FAILED), (own_b, EffectStatus.CANCELLED))):
                effect = Effect(f"own-effect-{i}", make_effect_key("artifact_write", "owned" + str(i), SHA, "1.0.0"),
                    job.job_id, "artifact_write", "owned" + str(i), None, SHA, None, status, T0, None)
                auto.put_effect(effect)
            auto.put_outbox_entry("opaque-owned-later", "own-effect-1", "{}", mode, T9)
            ledger = NarrativeRunStore(auto.db_path)
            own_run = create_run(ledger, (own_a, own_b), "owned-run")
            create_run(ledger, foreign, "foreign-run")
            ledger.block_run(own_run.run_id, error_code="MODEL_USAGE_EXCEEDS_RESERVATION", updated_at=T1)
            gate = auto.set_runtime_gate(RuntimeState.PAUSED, updated_at=T1)
            before = dump(auto)
            rows = auto.list_outbox_entries(status=mode, limit=1, allowed_job_ids=(own_a.job_id, own_b.job_id))
            assert rows[0]["outbox_id"] == "opaque-owned-later"
            idle = batch._blocked_history_is_idle(auto, (own_a, own_b), gate)
            assert idle is (mode == "delivered")
            assert dump(auto) == before
            assert auto.get_job(own_a.job_id) == own_a and auto.get_job(own_b.job_id) == own_b
            results.append({"owned_state": mode, "owned_future_not_before": T9, "foreign_outboxes": 25,
                           "readonly_idle": idle, "actual_fk_scoped_before_limit": True, "db_and_pending_jobs_unchanged": True})
        return results
    probe("multi-job-foreign-run-outbox-future-pending-preserved", scoped_delivery)

    def blocked_status():
        statuses = []
        for reason in ("PERSISTENT_BYTES_EXCEEDED", "SCRATCH_BYTES_EXCEEDED", "FINAL_BYTES_EXCEEDED"):
            target = owned / reason;target.mkdir()
            auto = AutomationStore(target / "auto.db")
            verify = seed_job(auto, "verify", status=JobStatus.PLANNED, kind="source.narrative_verify")
            ledger = NarrativeRunStore(auto.db_path)
            run = create_run(ledger, (verify,), "run")
            ledger.block_run(run.run_id, error_code=reason, updated_at=T1)
            actual = ledger.get_run(run.run_id)
            before = dump(auto)
            assert actual.blocked and batch._blocked_status(actual) == "storage_exhausted"
            assert dump(auto) == before and auto.get_job(verify.job_id) == verify
            statuses.append({"actual_persisted_block_reason": reason, "status": "storage_exhausted"})
        target = owned / "actual-usage-overrun";target.mkdir()
        auto, ledger, run, model, caller, context, raw, error = actual_caller(target, "partial",
            {"prompt_tokens": 73, "completion_tokens": 65}, with_verify=True)
        actual = ledger.get_run(run.run_id)
        assert actual.blocked and actual.block_reason == "MODEL_USAGE_EXCEEDS_RESERVATION"
        assert batch._blocked_status(actual) == "budget_exhausted"
        verify = auto.get_job("job-verify")
        assert verify.status is JobStatus.PLANNED
        before = dump(auto)
        assert ledger.budget_snapshot(run.run_id).charged_tokens == 138
        assert dump(auto) == before and auto.get_job("job-verify") == verify
        statuses.append({"actual_settled_usage": [73, 65], "reserved_output_cap": 64,
                         "actual_persisted_block_reason": actual.block_reason, "status": "budget_exhausted",
                         "pending_verify_unchanged": True, "decoder_calls": model.calls})
        return statuses
    probe("real-persisted-storage-and-actual-usage-budget-status", blocked_status)

    try:
        receipt["status"] = "pass" if all(p["status"] == "pass" for p in receipt["probes"]) else "specific_blocker"
    finally:
        receipt["source_after_sha256"] = {name: sha(ROOT / name) for name in owned_paths}
        receipt["source_unchanged"] = receipt["source_after_sha256"] == source_before
        receipt["handoff_unchanged"] = {name: sha(OUT.parent / "w04-main-reception" / name) for name in handoff_files} == handoff_before
        receipt["production_config_unchanged"] = {p: sha(Path(p)) for p in config_before} == config_before
        receipt["w03_other_owner"] = {"before": w03_before, "after": {name: sha(ROOT / name) for name in w03_paths},
                                       "attribution": "ROOT-authorized concurrent W03 pure ownership, not W04/reviewer write"}
        receipt["environment_unchanged"] = environment_before == dict(os.environ)
        receipt["network_attempts"] = len(network_attempts)
        receipt["seconds"] = time.monotonic() - start
        assert owned.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
        def retry(function, path, error):
            assert Path(path).resolve().is_relative_to(owned.resolve())
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            function(path)
        shutil.rmtree(owned, onexc=retry)
        receipt["owned_temp_removed"] = not owned.exists()
        (OUT / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        assert receipt["source_unchanged"] and receipt["handoff_unchanged"] and receipt["production_config_unchanged"]
        assert receipt["owned_temp_removed"] and receipt["environment_unchanged"] and not network_attempts
        print(json.dumps({"status": receipt["status"], "probes": len(receipt["probes"]), "seconds": receipt["seconds"],
                          "source_unchanged": True, "owned_temp_removed": True, "provider_calls": 0, "model_calls": 0}), flush=True)
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
