"""Native generation outcomes survive Phase C observer and feedback errors."""
from copy import deepcopy
import gzip
import hashlib
import json

import pytest

from tools.document_understanding_benchmark import phase_c_runner as runner
from tools.document_understanding_benchmark.phase_c_feedback import observations, publish, resolve
from tools.feedback_loop.coordinator import advance
from tools.feedback_loop.observations import read_batch


def test_exact_cache_binding_distinguishes_wrong_result_without_another_post():
    raw = {"source_id": "source", "document_id": "document", "content_sha256": "a" * 64}
    final = {"artifact_version_id": "new", "artifact_sha256": "b" * 64, "byte_size": 30, "source_ref": raw}
    ref = {"artifact_version_id": "new", "content_sha256": "b" * 64, "byte_size": 30,
           "document_id": "document", "source_id": "source", "source_sha256": "a" * 64}
    cached = {"run_id": "new-run", "status": "completed", "documents": [
        {"document_id": "document", "status": "completed", "generation_status": "reused", "artifact_ref": ref},
    ]}
    assert runner.recovered_artifact_ref(cached, final, run_id="new-run", reused=True) == final
    with pytest.raises(AssertionError, match="cache-run-receipt-mismatch"):
        runner.recovered_artifact_ref(cached, final, run_id="old-run", reused=True)
    for field, wrong in (("content_sha256", "c" * 64), ("artifact_version_id", "old"),
                         ("byte_size", 31), ("source_sha256", "d" * 64)):
        changed = {**cached, "documents": [{**cached["documents"][0], "artifact_ref": {**ref, field: wrong}}]}
        with pytest.raises(AssertionError, match="cache-artifact-mismatch"):
            runner.recovered_artifact_ref(changed, final, run_id="new-run", reused=True)
    state = {"run_id": "new-run", "cross_run_zero_POST": True}
    with pytest.raises(AssertionError, match="cache-artifact-mismatch"):
        runner.observe_cache_binding(state, "cross_run", changed, final, run_id="new-run", reused=True)
    checks = {row["check_id"]: row for row in observations({"states": [state]}, {}, "v1")}
    assert checks["cross-run-cache"]["actual"] == "zero-post"
    assert checks["cross-run-cache-binding"]["actual"] == "cache-artifact-mismatch"


def captured(tmp_path, raw):
    path = tmp_path / 'run.attempt.response.json.gz'
    path.write_bytes(gzip.compress(raw))
    digest = hashlib.sha256(raw).hexdigest()
    receipt = {'status': 'completed', 'documents': []}
    native = [{'attempt_id': 'attempt', 'response_sha256': digest,
               'usage_status': 'known', 'charged_tokens': 321, 'charged_micro_usd': 2000}]
    events = [{'event': 'model_final_observed', 'run_id': 'run', 'attempt_id': 'attempt',
               'final_sha256': digest, 'final_bytes': len(raw)}]
    return path, receipt, native, events


def test_complete_capture_over_old_cap_is_streamed_and_hash_bound(tmp_path, monkeypatch):
    raw = json.dumps({'draft': '完整原语言🙂' * 18000}, ensure_ascii=False).encode()
    assert len(raw) > 128 * 1024
    _, receipt, native, events = captured(tmp_path, raw)
    before = deepcopy((receipt, native, events))
    reads = []
    read = gzip.GzipFile.read

    def record_read(stream, size=-1):
        reads.append(size)
        return read(stream, size)

    monkeypatch.setattr(gzip.GzipFile, 'read', record_read)
    observed = runner.successful_model_observation(receipt, native, events, tmp_path, 'run',
        reading_model_projection='reading-model-input/4')
    assert observed['paid_response_capture'] == [{'attempt_id': 'attempt',
        'status': 'CAPTURED_AND_NATIVE_HASH_MATCHED', 'sha256': hashlib.sha256(raw).hexdigest(),
        'bytes': len(raw), 'usage_status': 'known'}]
    assert len(reads) > 2 and all(0 < size <= 65536 for size in reads)
    assert '完整原语言' not in json.dumps(observed, ensure_ascii=False)
    assert (receipt, native, events) == before


@pytest.mark.parametrize('fault,reason', [
    ('missing', 'PHASE_C_CAPTURE_UNAVAILABLE'),
    ('broken_gzip', 'PHASE_C_CAPTURE_UNAVAILABLE'),
    ('native_hash', 'PHASE_C_CAPTURE_IDENTITY_DIFFERS'),
    ('event_bytes', 'PHASE_C_CAPTURE_IDENTITY_DIFFERS'),
    ('event_hash', 'PHASE_C_CAPTURE_IDENTITY_DIFFERS'),
    ('utf8', 'PHASE_C_CAPTURE_UTF8_INVALID'),
])
def test_real_capture_errors_remain_explicit_without_size_permission(tmp_path, fault, reason):
    raw = b'\xff\xfe' if fault == 'utf8' else b'{"final":"valid"}'
    path, receipt, native, events = captured(tmp_path, raw)
    if fault == 'missing':
        path.unlink()
    elif fault == 'broken_gzip':
        path.write_bytes(b'not a gzip stream')
    elif fault == 'native_hash':
        native[0]['response_sha256'] = 'e' * 64
    elif fault == 'event_bytes':
        events[0]['final_bytes'] += 1
    elif fault == 'event_hash':
        events[0]['final_sha256'] = 'e' * 64
    with pytest.raises(ValueError, match=reason):
        runner.successful_model_observation(receipt, native, events, tmp_path, 'run',
            reading_model_projection='reading-model-input/4')


@pytest.mark.parametrize('fault', ['missing_capture', 'malformed_events'])
def test_observation_io_or_event_failure_preserves_native_receipt_and_usage(tmp_path, fault):
    path, receipt, native, events = captured(tmp_path, b'{"final":"complete"}')
    event_path = tmp_path / 'events.jsonl'
    if fault == 'missing_capture':
        path.unlink()
        event_path.write_text(json.dumps(events[0]) + '\n', encoding='utf-8')
    else:
        event_path.write_text('{invalid observation detail', encoding='utf-8')
    state = {'exit': 0, 'receipt': receipt, 'native_usage': native}
    before = deepcopy(state)
    runner.record_successful_model_observation(state, receipt, native, event_path, tmp_path, 'run',
        reading_model_projection='reading-model-input/4')
    assert {k: state[k] for k in before} == before
    assert state['model_observation']['status'] == 'INCOMPLETE'
    assert state['model_observation']['native_exit'] == 0
    assert state['model_observation']['native_batch_status'] == 'completed'
    assert state['model_observation']['reason'] == (
        'PHASE_C_CAPTURE_UNAVAILABLE' if fault == 'missing_capture' else 'PHASE_C_OBSERVATION_FAILED')
    assert 'paid_response_capture' not in state
    assert 'invalid observation detail' not in json.dumps(state)


@pytest.mark.timeout(120)
def test_real_owned_run_keeps_native_success_and_cache_after_observer_failure(tmp_path_factory, monkeypatch):
    # The child batch creates nested worker paths. Use a short pytest-owned root.
    tmp_path = tmp_path_factory.mktemp('pc')
    monkeypatch.setattr(runner.tempfile, 'gettempdir', lambda: str(tmp_path))
    monkeypatch.setattr(runner, 'seed_identity', lambda *args, **kwargs: {})
    observed = []

    def observer_fails(receipt, native, events, *_args, **_kwargs):
        assert receipt['status'] == 'completed' and native
        observed.append(deepcopy(native))
        raise OSError('untrusted observation detail must not enter the report')

    monkeypatch.setattr(runner, 'successful_model_observation', observer_fails)
    metadata = runner.loopback_preparation()
    provider = next(row for row in metadata['providers'] if row['provider'] == 'deepseek')
    output = tmp_path / 'receipts'
    output.mkdir()
    with runner.Loopback() as server:
        result = runner.run_pair({'sample_id': 'loopback-fixture'}, provider, metadata,
            mode='loopback', output=output, fixture_endpoint=server.endpoint,
            selected_versions='0.9.0', reading_model_projection='reading-model-input/5')
        assert len(server.requests) == 1, (
            result.get('error'), [state['receipt'] for state in result['states']],
        )
    assert len(observed) == 1
    assert result['status'] == 'OBSERVATION_INCOMPLETE', result
    state = result['states'][0]
    assert state['exit'] == 0 and state['receipt']['status'] == 'completed'
    assert state['native_usage'] == observed[0]
    assert state['model_observation'] == {'status': 'INCOMPLETE', 'error_type': 'OSError',
        'reason': 'PHASE_C_OBSERVATION_FAILED', 'native_exit': 0, 'native_batch_status': 'completed'}
    assert state['same_run_zero_POST'] and state['cross_run_zero_POST']
    assert state['public_replay']
    assert result['model_post_attempts'] == 1 and result['temporary_lake_removed']
    assert 'untrusted observation detail' not in json.dumps(result)
    assert not list(tmp_path.glob('cwplC-*'))
    assert json.loads((output / 'receipt.json').read_text(encoding='utf-8')) == result


def _native_failed_generation():
    return {"status": "FAIL", "mode": "live", "states": [{
        "run_id": "phase-c-original", "version": "0.9.0", "exit": 2,
        "receipt": {"schema_version": "narrative-batch-result/1", "run_id": "phase-c-original",
                    "status": "failed", "budget": {"unknown_reservations": 1, "unsettled_reservations": 0},
                    "documents": [{"status": "dead_letter", "errors": [
                        "MODEL_PAID_RESPONSE_UNAVAILABLE", "DEPENDENCY_TERMINAL"]}]},
        "native_usage": [{"run_id": "phase-c-original", "attempt_id": "original-model-post",
                          "usage_status": "unknown", "error_code": "MODEL_TIMEOUT"}],
    }]}


def test_native_timeout_reconciles_only_the_original_failed_generation(tmp_path):
    receipt = _native_failed_generation()
    receipt["states"][0]["cache_public_observation"] = {}
    path = tmp_path / "native-feedback.jsonl"
    env = {"RESEARCH_FEEDBACK_OUT": str(path)}
    assert publish(receipt, env, "fixture-version")["status"] == "published"
    batch = read_batch([path, path])
    assert not batch.diagnostics
    rows = {row["check_id"]: row for row in batch.observations.values()}
    assert set(rows) == {"summary-generation", "summary-execution"}
    row = rows["summary-generation"]
    assert (row["actual"], row["disposition"]) == ("failed", "unknown")
    assert (rows["summary-execution"]["actual"], rows["summary-execution"]["disposition"]) == ("failed", "deviation")
    assert row["refusal_code"] == "model_paid_response_unavailable"

    resolved = resolve(receipt, row["evidence_ref"], "fixture-version")
    native_outcome = resolved["native_outcome"]
    assert native_outcome["attempt_ids"] == ["original-model-post"]
    assert {"MODEL_TIMEOUT", "MODEL_PAID_RESPONSE_UNAVAILABLE"} <= set(native_outcome["error_codes"])

    acted = []

    def host(owner, request):
        assert owner == "company-wiki"
        kind, method = request["kind"], request["method"]
        acted.append((kind, method))
        reply = {"schema_version": "feedback-action-result/1", "action_id": request["action_id"],
                 "request_digest": request["request_digest"]}
        if kind == "observe":
            return {**reply, "state": "done", "result": {"recorded": True}}
        if kind == "triage":
            return {**reply, "state": "done", "result": {"decision": "needs_evidence"}}
        assert (kind, method) == ("reconcile", "lookup")
        assert request["payload"]["observation"]["evidence_ref"] == native_outcome["evidence_ref"]
        return {**reply, "state": "done", "result": native_outcome}

    results = advance(batch, host)["observations"]
    settled, = [value for value in results if value.get("step") == "reconcile"]
    assert sorted(acted) == sorted([("observe", "lookup")] * 2 + [("triage", "lookup"), ("reconcile", "lookup")])
    assert (settled["step"], settled["job_status"], settled["cost_state"]) == ("reconcile", "failed", "unknown")
    assert publish(receipt, env, "fixture-version")["status"] == "reused"


def test_confirmed_non_refusal_and_unbound_generation_are_distinct():
    receipt = _native_failed_generation()
    state = receipt["states"][0]
    state["native_usage"] = []
    state["receipt"]["budget"]["unknown_reservations"] = 0
    state["receipt"]["documents"] = []
    state["receipt"]["error"] = "BATCH_PREPARATION_DEADLINE_EXCEEDED"
    row, = observations(receipt, {}, "fixture-version")
    assert row["actual"] == "failed" and "refusal_code" not in row
    outcome = resolve(receipt, row["evidence_ref"], "fixture-version")["native_outcome"]
    assert outcome["cost_state"] == "known"
    assert outcome["error_codes"] == ["BATCH_PREPARATION_DEADLINE_EXCEEDED"]

    state["receipt"]["run_id"] = "unrelated-run"
    assert all(row["actual"] == "unknown" for row in observations(receipt, {}, "fixture-version"))


@pytest.mark.parametrize(("schema", "members"), [
    ("narrative-batch-result/1", "documents"), ("narrative-batch-result/2", "items"),
])
@pytest.mark.parametrize("status", ["failed", "budget_exhausted", "storage_exhausted"])
def test_generation_feedback_preserves_terminal_status_and_original_attempts(tmp_path, schema, members, status):
    receipt = _native_failed_generation()
    state = receipt["states"][0]
    original = state["receipt"]
    original.pop("documents")
    original.update(schema_version=schema, status=status, error="RUN_FAILURE")
    original[members] = [{"status": status, "errors": ["ITEM_FAILURE"]}]
    other_members = "documents" if members == "items" else "items"
    original[other_members] = [{"errors": ["UNRELATED_LAYOUT"]}]
    state["native_usage"].append({"run_id": "other-run", "attempt_id": "unrelated", "error_code": "OTHER_RUN"})
    path = tmp_path / "out.jsonl"
    assert publish(receipt, {"RESEARCH_FEEDBACK_OUT": str(path)}, "code")["status"] == "published"
    batch = read_batch([path, path])
    assert not batch.diagnostics
    rows = {row["check_id"]: row for row in batch.observations.values()}
    row = rows["summary-generation"]
    assert (rows["summary-execution"]["actual"], rows["summary-execution"]["disposition"]) == (status, "deviation")
    assert (row["check_id"], row["actual"], row["disposition"]) == ("summary-generation", status, "unknown")
    if status in ("budget_exhausted", "storage_exhausted"):
        assert row["refusal_code"] == status
    native = resolve(receipt, row["evidence_ref"], "code")["native_outcome"]
    assert native["job_status"] == "failed" and native["cost_state"] == "unknown"
    assert native["attempt_ids"] == ["original-model-post"]
    assert native["error_codes"] == ["ITEM_FAILURE", "MODEL_TIMEOUT", "RUN_FAILURE"]


@pytest.mark.parametrize(("schema", "status", "run_id"), [
    ("narrative-batch-result/2", "completed", "phase-c-original"),
    ("narrative-batch-result/2", "deferred", "phase-c-original"),
    ("narrative-batch-result/99", "failed", "phase-c-original"),
    ([], "failed", "phase-c-original"),
    ("narrative-batch-result/2", "failed", "other"),
])
def test_unbound_or_unrecognized_receipts_do_not_create_generation_failures(schema, status, run_id):
    receipt = _native_failed_generation()
    receipt["states"][0]["receipt"].update(schema_version=schema, status=status, run_id=run_id)
    assert all(row["check_id"] != "summary-generation" for row in observations(receipt, {}, "code"))
