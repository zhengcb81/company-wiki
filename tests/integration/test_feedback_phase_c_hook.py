"""Public Phase C receipt -> optional sidecar -> automatic ROOT completion hook."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.document_understanding_benchmark.phase_c_feedback import observations, publish
from tools.feedback_loop.hook import after_observations
from tools.feedback_loop.observations import read_batch


def native():
    return {"status": "PASS", "states": [
        {"run_id": "native-1", "version": "v1", "public_replay": {"replay_status": "verified"},
         "same_run_zero_POST": True, "cross_run_zero_POST": True},
        {"run_id": "native-2", "version": "v2", "public_replay": {"replay_status": "verified"},
         "same_run_zero_POST": False}
    ]}


def test_public_receipt_projects_native_truth_and_independent_siblings(tmp_path):
    path = tmp_path / "one.jsonl"
    env = {"RESEARCH_FEEDBACK_OUT": str(path), "RESEARCH_FEEDBACK_RUN_ID": "root-run",
           "RESEARCH_FEEDBACK_ATTEMPT_ID": "a"}
    assert publish(native(), env, "abc")["status"] == "published"
    frozen = path.read_bytes()
    assert publish(native(), env, "abc")["status"] == "reused"
    assert path.read_bytes() == frozen
    cases = read_batch([path, path])
    assert len(cases.observations) == 6 and not cases.diagnostics
    rows = list(cases.observations.values())
    assert {r["version"] for r in rows} == {"abc"}
    assert sorted(r["disposition"] for r in rows) == ["deviation", "expected", "expected", "expected", "expected", "unknown"]
    assert len({r["step_id"] for r in rows}) == 2
    assert all("summary-quality" != r["check_id"] for r in rows)
    assert after_observations(path, {}) is None
    config = tmp_path / "hosts.json"
    config.write_text("{}", encoding="utf-8")
    progress = after_observations(path, {"RESEARCH_FEEDBACK_HOSTS": str(config)})
    assert progress["states"]["host_unconfigured"] == 6
    assert progress["dispositions"]["unknown"] == 1


def test_disabled_or_unwritable_feedback_preserves_original_result(tmp_path):
    source = native()
    before = json.dumps(source)
    assert publish(source, {}, "abc") is None
    dest = tmp_path / "existing"
    dest.write_bytes(b"existing material")
    assert publish(source, {"RESEARCH_FEEDBACK_OUT": str(dest)}, "abc")["status"] == "output_conflict"
    assert dest.read_bytes() == b"existing material"
    assert publish(source, {"RESEARCH_FEEDBACK_OUT": str(tmp_path / "missing" / "out")}, "abc")["status"] == "write_failed"
    assert after_observations(dest, {"RESEARCH_FEEDBACK_HOSTS": str(tmp_path / "missing")})["status"] == "host_config_unavailable"
    assert json.dumps(source) == before


def test_exit_two_alone_does_not_prove_a_structured_source_refusal():
    receipt = {"states": [{"run_id": "source-1", "public_read_exit": 2}]}
    assert next(observations(receipt, {}, None))["actual"] == "unknown"
    receipt["states"][0]["public_replay"] = {
        "schema_version": "narrative-read-receipt/1", "status": "unavailable", "reason": "narrative_reader_unavailable"}
    assert next(observations(receipt, {}, None))["actual"] == "read-refused"


def test_native_reader_positive_claim_and_wrong_bytes_is_a_visible_deviation(tmp_path, monkeypatch):
    from tools.document_understanding_benchmark import phase_c_runner as runner

    ref = {"artifact_sha256": "0" * 64}
    native = {"schema_version": "narrative-read-receipt/1", "replay_status": "verified", "narrative_ref": ref}
    replies = iter([(0, ref, b"", b""), (0, {}, json.dumps(native).encode(), b"different content")])
    monkeypatch.setattr(runner, "_cli", lambda *args, **kwargs: next(replies))
    state = {"run_id": "origin"}
    with pytest.raises(AssertionError):
        runner.public_bundle(tmp_path, tmp_path, {}, tmp_path, {"source_ref": {}}, {}, "test", observed_state=state)
    row = next(observations({"states": [state]}, {}, None))
    assert row["actual"] == "artifact-bytes-mismatch"


def test_diagnostic_fault_or_reserved_alias_cannot_replace_business_output(tmp_path, monkeypatch):
    from tools.document_understanding_benchmark import phase_c_feedback, phase_c_runner

    env = {"RESEARCH_FEEDBACK_OUT": str(tmp_path / "feedback-delivery.json")}
    source = native()
    before = json.dumps(source)
    assert phase_c_runner.deliver_feedback(tmp_path, source, env, "v1")["status"] == "reserved_output"
    env["RESEARCH_FEEDBACK_OUT"] = str(tmp_path / "observations")

    def fail(*args):
        raise PermissionError("test cleanup failure")

    monkeypatch.setattr(phase_c_feedback, "publish", fail)
    answer = phase_c_runner.deliver_feedback(tmp_path, source, env, "v1")
    assert answer["status"] == "diagnostic_failed" and answer["error_type"] == "PermissionError"
    assert json.dumps(source) == before


def test_wake_does_not_wait_for_owner_and_does_not_overwrite_delivery(tmp_path, monkeypatch):
    from tools.feedback_loop import hook

    opened = []

    class Background:
        def __init__(self, argv, **kwargs):
            self.pid = 42
            opened.append((argv, kwargs))

        def wait(self):
            pytest.fail("business result must not wait for a control RPC")

    monkeypatch.setattr(hook.subprocess, "Popen", Background)
    output = tmp_path / "control-result"
    assert hook.wake(tmp_path / "obs", str(tmp_path / "config"), output)["status"] == "scheduled"
    assert hook.wake(tmp_path / "obs", str(tmp_path / "config"), output)["status"] == "previous_wake_receipt"
    assert len(opened) == 1 and "tools.feedback_loop.hook" in opened[0][0]


def test_saved_native_receipt_can_resolve_the_observed_content_and_version(tmp_path):
    root = Path(__file__).resolve().parents[2]
    outcome = native()
    outcome["states"][0]["artifact_ref"] = {"artifact_sha256": "b" * 64}
    outcome["mode"] = "loopback"
    receipt = tmp_path / "overall.json"
    receipt.write_text(json.dumps(outcome), encoding="utf-8")
    (tmp_path / "harness-fingerprint.json").write_text('{"repository_head":"a1b2"}', encoding="utf-8")
    argv = [sys.executable, "-B", "-m", "tools.document_understanding_benchmark.phase_c_feedback", str(receipt)]
    out = tmp_path / "obs"
    assert json.loads(subprocess.check_output([*argv, "--out", str(out)], cwd=root))["status"] == "published"
    ref = json.loads(out.read_bytes().splitlines()[0])["evidence_ref"]
    result = json.loads(subprocess.check_output([*argv, "--ref", ref], cwd=root))
    assert (result["mode"], result["artifact_sha256"], result["selector_version"]) == ("loopback", "b" * 64, "v1")
    assert result["observation"]["version"] == "a1b2"
