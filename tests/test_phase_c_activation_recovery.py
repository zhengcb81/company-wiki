"""Exercise paid activation recovery through the existing isolated C runner."""
import json

from tools.document_understanding_benchmark import phase_c_runner as runner


def _observer_inputs(tmp_path, rows, *, source_sha256):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    observer_path = tmp_path / "observer.json"
    observer_path.write_text(
        json.dumps(
            {
                "schema_version": "phase-c-observer/1",
                "mode": "live",
                "source_sha256": source_sha256,
                "events": str(events_path),
            }
        ),
        encoding="utf-8",
    )
    return {
        "observer_path": observer_path,
        "observer_env_path": str(observer_path),
        "events_path": events_path,
        "mode": "live",
        "source_sha256": source_sha256,
    }


def test_pre_reservation_refusal_is_not_mistaken_for_paid_activation(tmp_path):
    receipt = {
        "status": "failed",
        "budget": {
            "estimated_micro_usd": 0,
            "tokens": 0,
            "unknown_reservations": 0,
            "unsettled_reservations": 0,
        },
        "documents": [{"status": "dead_letter", "errors": ["PHASE_C_GOLD_SUPPORT_MISSING"]}],
    }
    events = [{
        "event": "pre_reservation_refused",
        "run_id": "run-1",
        "code": "PHASE_C_GOLD_SUPPORT_MISSING",
        "reserved": False,
    }]

    inputs = _observer_inputs(tmp_path, events, source_sha256="a" * 64)
    refusal = runner.pre_reservation_refusal(
        code=2, receipt=receipt, native_usage=[], run_id="run-1", **inputs
    )

    assert refusal == {
        "status": "PRE_RESERVATION_BLOCKED",
        "code": "PHASE_C_GOLD_SUPPORT_MISSING",
        "reserved": False,
        "post_attempts": 0,
        "native_usage_rows": 0,
    }
    post_inputs = _observer_inputs(
        tmp_path,
        [*events, {"event": "http_post_attempt", "run_id": "run-1"}],
        source_sha256="a" * 64,
    )
    assert runner.pre_reservation_refusal(
        code=2,
        receipt=receipt,
        native_usage=[],
        run_id="run-1",
        **post_inputs,
    ) is None
    paid_receipt = {**receipt, "budget": {**receipt["budget"], "unknown_reservations": 1}}
    assert runner.pre_reservation_refusal(
        code=2,
        receipt=paid_receipt,
        native_usage=[],
        run_id="run-1",
        **inputs,
    ) is None
    assert runner.pre_reservation_refusal(
        code=2,
        receipt=receipt,
        native_usage=[{"usage_status": "known"}],
        run_id="run-1",
        **inputs,
    ) is None
    mismatched_observer = {**inputs, "observer_env_path": str(tmp_path / "other.json")}
    assert runner.pre_reservation_refusal(
        code=2, receipt=receipt, native_usage=[], run_id="run-1", **mismatched_observer
    ) is None


def test_pre_reservation_refusal_rejects_ambiguous_or_malformed_evidence(tmp_path):
    receipt = {
        "status": "failed",
        "budget": {
            "estimated_micro_usd": 0,
            "tokens": 0,
            "unknown_reservations": 0,
            "unsettled_reservations": 0,
        },
        "documents": [{"status": "dead_letter", "errors": ["CACHE_WOULD_GENERATE"]}],
    }
    refusal = {
        "event": "pre_reservation_refused",
        "run_id": "run-2",
        "code": "CACHE_WOULD_GENERATE",
        "reserved": False,
    }

    no_events = _observer_inputs(tmp_path, [], source_sha256="b" * 64)
    assert runner.pre_reservation_refusal(
        code=2, receipt=receipt, native_usage=[], run_id="run-2", **no_events
    ) is None
    duplicate = _observer_inputs(tmp_path, [refusal, refusal], source_sha256="b" * 64)
    assert runner.pre_reservation_refusal(
        code=2,
        receipt=receipt,
        native_usage=[],
        run_id="run-2",
        **duplicate,
    ) is None
    malformed_budget = {
        **receipt,
        "budget": {**receipt["budget"], "estimated_micro_usd": False},
    }
    bool_budget = _observer_inputs(tmp_path, [refusal], source_sha256="b" * 64)
    assert runner.pre_reservation_refusal(
        code=2,
        receipt=malformed_budget,
        native_usage=[],
        run_id="run-2",
        **bool_budget,
    ) is None
    bool_budget["observer_path"].write_text("{}", encoding="utf-8")
    assert runner.pre_reservation_refusal(
        code=2, receipt=receipt, native_usage=[], run_id="run-2", **bool_budget
    ) is None


def test_activation_recovery_requires_a_durable_held_paid_response():
    from company_wiki.automation.narrative_paid_response import PaidResponsePin

    dead_letter = {
        "status": "failed",
        "documents": [{"status": "dead_letter", "errors": ["MODEL_HTTP_TRANSPORT"]}],
    }
    assert runner.activation_recovery_precondition(
        code=2,
        receipt=dead_letter,
        native_usage=[{"usage_status": "unknown", "response_sha256": None}],
        events=[{"event": "http_post_attempt", "run_id": "run-3"}],
        run_id="run-3",
    ) == "initial_document_not_activation_pending"

    held = {
        "status": "failed",
        "documents": [{"status": "activation_pending", "errors": ["ACTIVATION_HELD"]}],
    }
    body_sha256 = "a" * 64
    pin = PaidResponsePin(
        request_sha256="b" * 64,
        body_sha256=body_sha256,
        object_key=f"objects/sha256/{body_sha256[:2]}/{body_sha256}.json",
        byte_size=123,
        model_id="test-model",
        adapter_id="test-adapter",
        prompt_version="test-prompt/1",
        http_status=200,
        duration_ms=1,
    ).to_json()
    paid_row = {
        "usage_status": "known",
        "request_sha256": "b" * 64,
        # This is the adapter-decoded response hash, intentionally distinct
        # from pin.body_sha256, which covers the full HTTP response envelope.
        "response_sha256": "c" * 64,
        "paid_response_json": pin,
    }
    assert runner.activation_recovery_precondition(
        code=2,
        receipt=held,
        native_usage=[paid_row],
        events=[{"event": "activation_held", "run_id": "run-3"}],
        run_id="run-3",
    ) is None
    assert runner.activation_recovery_precondition(
        code=2,
        receipt=held,
        native_usage=[{**paid_row, "paid_response_json": None}],
        events=[{"event": "activation_held", "run_id": "run-3"}],
        run_id="run-3",
    ) == "durable_paid_response_unavailable"
    assert runner.activation_recovery_precondition(
        code=2,
        receipt=held,
        native_usage=[{**paid_row, "paid_response_json": "{}"}],
        events=[{"event": "activation_held", "run_id": "run-3"}],
        run_id="run-3",
    ) == "durable_paid_response_unavailable"
    for invalid_hash in ("", "not-a-sha256"):
        assert runner.activation_recovery_precondition(
            code=2,
            receipt=held,
            native_usage=[{**paid_row, "response_sha256": invalid_hash}],
            events=[{"event": "activation_held", "run_id": "run-3"}],
            run_id="run-3",
        ) == "durable_paid_response_unavailable"
    assert runner.activation_recovery_precondition(
        code=2,
        receipt=held,
        native_usage=[{**paid_row, "request_sha256": "d" * 64}],
        events=[{"event": "activation_held", "run_id": "run-3"}],
        run_id="run-3",
    ) == "durable_paid_response_unavailable"
    assert runner.activation_recovery_precondition(
        code=2,
        receipt=held,
        native_usage=[{**paid_row, "usage_status": "unknown"}],
        events=[{"event": "activation_held", "run_id": "run-3"}],
        run_id="run-3",
    ) == "durable_paid_response_unavailable"


def test_public_span_limits_are_read_from_shared_router_configuration():
    from company_wiki.source_catalog.narrative_routing import (
        DEFAULT_SELECTION_LIMIT,
        FINANCIAL_REPORT_SELECTION_LIMIT,
        PROSPECTUS_SELECTION_LIMIT,
    )

    assert runner.public_span_limits() == {
        "default": DEFAULT_SELECTION_LIMIT,
        "financial_reports": FINANCIAL_REPORT_SELECTION_LIMIT,
        "prospectus": PROSPECTUS_SELECTION_LIMIT,
    }


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
        assert result["status"] == "PASS", json.dumps(result, indent=2)
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
