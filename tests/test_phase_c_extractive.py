"""Tool/real local HTTP assembly only; no Phase C worker, PDF, or paid model."""

from __future__ import annotations
import gzip
import hashlib
import json
import socket

import pytest

from tools.document_understanding_benchmark import phase_c_runner as runner
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_model_runtime import build_model_request
from company_wiki.automation.narrative_model_extractive import decode_extractive_result
from unit.test_narrative_extractive_runtime import selected

_CONNECT = socket.socket.connect
_CREATE_CONNECTION = socket.create_connection
VERSION = "reading-model-input/5"


def test_default_projection_uses_v5_and_explicit_v4_and_legacy_stay_separate():
    assert runner.reading_projection_for("0.9.0", None) == VERSION
    assert (
        runner.reading_projection_for("0.9.0", "reading-model-input/4")
        == "reading-model-input/4"
    )
    assert runner.reading_projection_for("0.9.0", VERSION) == VERSION
    assert runner.reading_projection_for("0.8.0", VERSION) is None
    with pytest.raises(ValueError):
        runner.reading_projection_for("0.9.0", "unregistered-version")


@pytest.mark.parametrize("invalid", [False, True])
def test_v5_loopback_returns_only_finite_known_id_decisions_and_no_source_prose(
    invalid,
):
    source = selected(3)
    request = build_model_request(source, reading_projection_version=VERSION)
    material = json.loads(request.data_json)
    value = runner.loopback_draft(material, invalid_summary=invalid)
    assert set(value) == {"decisions"}
    assert len(value["decisions"]) <= len(material["material"]["tasks"])
    assert all(
        set(row) == {"task", "priority", "disposition"} for row in value["decisions"]
    )
    assert {row["task"] for row in value["decisions"]} <= {
        row["key"] for row in material["material"]["tasks"]
    }
    assert not any(
        span.raw_text in canonical_json(value) for span in source.evidence_spans
    )


def test_v4_loopback_draft_contract_is_unchanged():
    source = selected(2)
    request = build_model_request(
        source, reading_projection_version="reading-model-input/4"
    )
    value = runner.loopback_draft(json.loads(request.data_json))
    assert set(value) == {"drafts_by_task"}


@pytest.mark.parametrize("invalid", [False, True])
def test_existing_http_adapter_uses_local_v5_loopback_and_actual_core_keeps_original_cards(
    monkeypatch, invalid
):
    from company_wiki.automation.narrative_http_model import NarrativeHTTPModel

    source = selected(3)
    request = build_model_request(source, reading_projection_version=VERSION)
    with runner.Loopback(invalid_summary=invalid) as server:
        address = ("127.0.0.1", server.server.server_port)

        def connect(sock, target):
            assert target == address, "only owned loopback may connect"
            return _CONNECT(sock, target)

        def create(target, *args, **kwargs):
            assert target == address, "only owned loopback may connect"
            return _CREATE_CONNECTION(target, *args, **kwargs)

        monkeypatch.setattr(socket.socket, "connect", connect)
        monkeypatch.setattr(socket, "create_connection", create)
        monkeypatch.setenv("PHASE_C_OWNED_FAKE_KEY", "not-a-live-key")
        model = NarrativeHTTPModel(
            model_id="stub-model",
            endpoint=server.endpoint,
            api_key_env="PHASE_C_OWNED_FAKE_KEY",
            allow_local_http=True,
            max_output_tokens=8192,
            timeout_seconds=3,
        )
        response = model.generate(request)
        decoded = decode_extractive_result(response, selected=source)
        assert len(server.requests) == 1
        assert decoded.execution["model_diagnostic"] == (
            "RANK_INVALID" if invalid else None
        )
        assert {c["text"] for c in decoded.draft["claims"]} == {
            s.raw_text for s in source.evidence_spans
        }
        assert all(c["modality"] == "uncertain" for c in decoded.draft["claims"])
        assert all(c["needs_review"] for c in decoded.draft["claims"])
    assert not server.thread.is_alive()


def capture_fixture(tmp_path):
    from company_wiki.automation.narrative_model import NarrativeModelResponse

    source = selected(3)
    request = build_model_request(source, reading_projection_version=VERSION)
    raw = canonical_json({"decisions": []}).encode()
    response = NarrativeModelResponse("offline", "fixture", request.prompt_version, raw)
    execution = decode_extractive_result(response, selected=source).execution
    receipt = {
        "documents": [
            {"model_diagnostics": [{"attempt_id": "attempt", "execution": execution}]}
        ]
    }
    path = tmp_path / "run.attempt.response.json.gz"
    path.write_bytes(gzip.compress(raw))
    sha = hashlib.sha256(raw).hexdigest()
    native = [
        {
            "attempt_id": "attempt",
            "response_sha256": sha,
            "usage_status": "known",
            "charged_tokens": 80,
            "charged_micro_usd": 110,
        }
    ]
    events = [
        {
            "event": "model_final_observed",
            "run_id": "run",
            "attempt_id": "attempt",
            "final_sha256": sha,
            "final_bytes": len(raw),
        }
    ]
    return source, receipt, native, events, path


def test_success_observation_retains_real_execution_and_capture_hashes_only(tmp_path):
    source, receipt, native, events, path = capture_fixture(tmp_path)
    result = runner.successful_model_observation(
        receipt, native, events, tmp_path, "run", reading_model_projection=VERSION
    )
    audit = result["source_card_execution"]
    assert audit["task_count"] == 3 and audit["source_dispositions"] == {"admitted": 3}
    assert audit["model_dispositions"] == {"unprocessed": 3}
    assert audit["model_diagnostic"] == "RANK_INCOMPLETE"
    assert audit["source_coverage_complete"] and not audit["model_coverage_complete"]
    assert result["paid_response_capture"][0]["sha256"] == native[0]["response_sha256"]
    assert (
        result["paid_response_capture"][0]["status"]
        == "CAPTURED_AND_NATIVE_HASH_MATCHED"
    )
    assert not any(s.raw_text in canonical_json(result) for s in source.evidence_spans)
    assert "not-a-live-key" not in canonical_json(result)
    assert path.exists()


@pytest.mark.parametrize(
    "fault", ["tampered", "missing", "event_hash", "native_hash", "missing_report"]
)
def test_success_observation_cannot_fake_capture_or_execution(tmp_path, fault):
    _, receipt, native, events, path = capture_fixture(tmp_path)
    if fault == "tampered":
        path.write_bytes(gzip.compress(b'{"other":"bytes"}'))
    elif fault == "missing":
        path.unlink()
    elif fault == "event_hash":
        events[0]["final_sha256"] = "e" * 64
    elif fault == "native_hash":
        native[0]["response_sha256"] = "e" * 64
    else:
        receipt["documents"][0]["model_diagnostics"] = []
    with pytest.raises(ValueError):
        runner.successful_model_observation(
            receipt, native, events, tmp_path, "run", reading_model_projection=VERSION
        )


def test_v4_success_does_not_invent_an_extractive_report(tmp_path):
    _, receipt, native, events, _ = capture_fixture(tmp_path)
    receipt["documents"][0]["model_diagnostics"] = []
    result = runner.successful_model_observation(
        receipt,
        native,
        events,
        tmp_path,
        "run",
        reading_model_projection="reading-model-input/4",
    )
    assert result["source_card_execution"] is None


def test_real_cli_parser_selects_v5_default_and_v4_compatibility_without_io(tmp_path):
    parser = runner.argument_parser()
    output = tmp_path / "not-created"
    base = ["--output", str(output)]
    assert parser.parse_args(base).reading_model_projection == VERSION
    for mode in [VERSION, "reading-model-input/4"]:
        assert (
            parser.parse_args(
                base + ["--reading-model-projection", mode]
            ).reading_model_projection
            == mode
        )
    with pytest.raises(SystemExit):
        parser.parse_args(base + ["--reading-model-projection", "unsupported"])
    assert not output.exists()
