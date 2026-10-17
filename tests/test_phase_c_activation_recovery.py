"""Exercise paid activation recovery through the existing isolated C runner."""
import json

from tools.document_understanding_benchmark import phase_c_runner as runner


def test_actual_paid_outbox_resumes_same_run_without_new_post(tmp_path):
    metadata = runner.loopback_preparation()
    output = tmp_path / "recovery"
    output.mkdir()
    with runner.Loopback() as server:
        result = runner.run_pair(
            {"sample_id": "loopback-fixture"}, metadata["providers"][0], metadata,
            mode="loopback", output=output, fixture_endpoint=server.endpoint,
            selected_versions="0.9.0", activation_recovery=True,
        )
        assert result["status"] == "PASS", result
        assert len(server.requests) == 1
    state = result["states"][0]
    recovered = state["activation_recovery"]
    assert recovered["status"] == "PASS"
    assert recovered["held_status"] == "activation_pending"
    assert recovered["same_run_id"] == state["run_id"]
    assert recovered["native_attempts_before"] == recovered["native_attempts_after"] == 1
    assert recovered["charged_tokens_before"] == recovered["charged_tokens_after"] == 80
    assert recovered["charged_micro_usd_before"] == recovered["charged_micro_usd_after"] > 0
    assert recovered["POSTs_before"] == recovered["POSTs_after"] == 1
    assert recovered["paid_generation_unchanged"]
    assert recovered["response_identity_unchanged"]
    assert state["same_run_zero_POST"] and state["cross_run_zero_POST"]
    assert state["public_replay"]["replay_status"] == "verified"
    events = runner.read_rows(output / "events.jsonl")
    assert any(row["event"] == "activation_held" for row in events)
    assert result["sentinel_unchanged"] and result["protected_unchanged"]
    assert result["temporary_lake_removed"]
    assert json.loads((output / "receipt.json").read_text(encoding="utf-8"))["status"] == "PASS"
