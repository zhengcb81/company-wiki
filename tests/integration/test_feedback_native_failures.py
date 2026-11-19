"""Exercise failure observations at Phase C's native CLI and HTTP-observer boundaries."""

import json
from pathlib import Path

import pytest

from tools.document_understanding_benchmark import phase_c_feedback, phase_c_runner
from tools.feedback_loop.observations import read_batch


def _run_loopback(output, monkeypatch):
    # Use the same short, pytest-owned root as the receipts on Windows.
    monkeypatch.setattr(phase_c_runner.tempfile, "tempdir", str(output.parent))
    metadata = phase_c_runner.loopback_preparation()
    with phase_c_runner.Loopback() as server:
        result = phase_c_runner.run_pair(
            {"sample_id": "loopback-fixture"}, metadata["providers"][0], metadata,
            mode="loopback", output=output, fixture_endpoint=server.endpoint, selected_versions="0.9.0",
        )
        assert len(server.requests) == 1, {
            "error": result.get("error"), "error_line": result.get("error_line"),
            "native_documents": [
                state.get("receipt", {}).get("documents") for state in result.get("states", [])
            ],
        }
    assert result["temporary_lake_removed"] and result["protected_unchanged"]
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == result["status"] == "FAIL"
    return receipt


def _feedback_rows(output, receipt):
    sidecar = output / "feedback.jsonl"
    delivery = phase_c_feedback.publish(receipt, {"RESEARCH_FEEDBACK_OUT": str(sidecar)}, "fixture-version")
    assert delivery["status"] == "published"
    cases = read_batch([sidecar])
    assert not cases.diagnostics
    return {row["check_id"]: row for row in cases.observations.values()}


@pytest.mark.parametrize("suffix", ["-restart", "-cross-run"], ids=["same-run", "cross-run"])
def test_cache_post_failure_survives_native_exit(tmp_path, monkeypatch, suffix):
    native_cli = phase_c_runner._cli
    attempted_runs = []

    def failing_cache_command(root, output, label, command, env, *args, **kwargs):
        result = native_cli(root, output, label, command, env, *args, **kwargs)
        if not label.endswith(suffix):
            return result
        assert result[0] == 0
        request_file = Path(command[command.index("--request") + 1])
        run_id = json.loads(request_file.read_text(encoding="utf-8"))["run_id"]
        attempted_runs.append(run_id)
        # Inject the observed extra HTTP attempt and a failed owner exit. The actual
        # loopback service receives only the original generation request.
        event = {"event": "http_post_attempt", "run_id": run_id, "attempt_id": "fixture-cache-attempt"}
        with (output / "events.jsonl").open("a", encoding="utf-8") as trace:
            trace.write(json.dumps(event) + "\n")
        return 2, *result[1:]

    monkeypatch.setattr(phase_c_runner, "_cli", failing_cache_command)
    receipt = _run_loopback(tmp_path, monkeypatch)
    state, = receipt["states"]
    assert receipt["model_post_attempts"] == 2
    rows = _feedback_rows(tmp_path, receipt)
    assert rows["locator-replay"]["disposition"] == "expected"
    if suffix == "-restart":
        assert attempted_runs == [state["run_id"]]
        assert state["same_run_zero_POST"] is False
        assert "cross_run_zero_POST" not in state
        assert rows["same-run-cache"]["actual"] == "extra-post"
        assert rows["same-run-cache"]["disposition"] == "deviation"
        assert rows["cross-run-cache"]["disposition"] == "unknown"
    else:
        assert attempted_runs == [state["run_id"] + "-cache"]
        assert state["same_run_zero_POST"] is True
        assert state["cross_run_zero_POST"] is False
        assert rows["same-run-cache"]["disposition"] == "expected"
        assert rows["cross-run-cache"]["actual"] == "extra-post"
        assert rows["cross-run-cache"]["disposition"] == "deviation"


def test_public_locator_refusal_survives_native_exit(tmp_path, monkeypatch):
    native_cli = phase_c_runner._cli
    refusals = []

    def read_with_wrong_artifact_sha(root, output, label, command, env, payload=None, **kwargs):
        if not label.endswith("-read"):
            return native_cli(root, output, label, command, env, payload, **kwargs)
        reference = {**payload["narrative_ref"], "artifact_sha256": "0" * 64}
        result = native_cli(root, output, label, command, env, {**payload, "narrative_ref": reference}, **kwargs)
        assert result[0] != 0 and result[1] is None
        refusals.append(json.loads(result[2]))
        return result

    monkeypatch.setattr(phase_c_runner, "_cli", read_with_wrong_artifact_sha)
    receipt = _run_loopback(tmp_path, monkeypatch)
    state, = receipt["states"]
    refusal, = refusals
    assert refusal["reason"] and "replay_status" not in refusal
    assert state["public_replay"]["status"] == refusal["status"]
    assert state["public_replay"]["reason"] == refusal["reason"]
    rows = _feedback_rows(tmp_path, receipt)
    assert rows["locator-replay"]["disposition"] == "deviation"
    assert rows["locator-replay"]["actual"] not in {"unknown", "verified"}
    assert rows["locator-replay"]["refusal_code"] == state["refusal_code"] == refusal["reason"]
    assert rows["same-run-cache"]["disposition"] == rows["cross-run-cache"]["disposition"] == "unknown"
