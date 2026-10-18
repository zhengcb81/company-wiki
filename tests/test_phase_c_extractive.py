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


def test_mother_budget_keeps_unknown_holds_without_a_second_global_stop(tmp_path):
    metadata, ledger = tmp_path / "budget.json", tmp_path / "usage.jsonl"
    metadata.write_text(json.dumps({"mother_budget": {
        "prior_charged_tokens": 100, "prior_charged_micro_usd": 200,
        "retained_fx_hold_micro_usd": 50, "token_limit": 1000, "micro_usd_limit": 2000,
        "old_unknown_hold_count_already_in_baseline": 7}}), encoding="utf-8")
    row = {"kind": "native_model_charge", "mode": "live", "database": "prior/AUTO.sqlite",
           "attempt_id": "failed-transport", "usage_status": "unknown",
           "charged_tokens": 300, "charged_micro_usd": 400}
    ledger.write_text(json.dumps(row) + '\n', encoding="utf-8")
    before = ledger.read_bytes()
    totals = runner.mother_totals(metadata, ledger)
    assert totals["new_unknown_count"] == 1 and totals["prior_unknown7_retained"] == 7
    assert totals["charged_tokens"] == 400 and totals["charged_micro_usd"] == 650
    assert runner.mother_budget_fits(totals, tokens_bound=600, micro_usd_bound=1350)
    assert not runner.mother_budget_fits(totals, tokens_bound=601, micro_usd_bound=1350)
    assert not runner.mother_budget_fits(totals, tokens_bound=600, micro_usd_bound=1351)
    assert ledger.read_bytes() == before, "admission must never refund or rewrite an unknown hold"


@pytest.mark.parametrize("value", [-1, True, 1.5])
def test_mother_budget_rejects_invalid_accounting(value):
    totals = {"charged_tokens": value, "charged_micro_usd": 1, "token_limit": 10,
              "micro_usd_limit": 10, "new_unknown_count": 1}
    with pytest.raises(ValueError):
        runner.mother_budget_fits(totals, tokens_bound=1, micro_usd_bound=1)


@pytest.mark.parametrize("version", ["reading-model-input/4", VERSION])
def test_gold_observer_validates_the_actual_scoped_request_and_rejects_changed_material(version):
    from copy import deepcopy
    from tools.document_understanding_benchmark.phase_c_observer import gold_observation

    source = selected(3)
    request = build_model_request(source, reading_projection_version=version)
    envelope = json.loads(request.data_json)
    gold = {"facts": []}
    report = gold_observation(gold, source, envelope)
    assert report["evidence_count"] == len(source.evidence_spans)
    assert report["evidence_characters"] == sum(len(span.raw_text) for span in source.evidence_spans)
    changed = deepcopy(envelope)
    changed["material"]["tasks"] = []
    with pytest.raises(AssertionError):
        gold_observation(gold, source, changed)


def test_identity_snapshot_uses_explicit_data_catalog_not_code_checkout(tmp_path, monkeypatch):
    """A worktree without production data reads the supplied catalog snapshot."""
    from company_wiki.source_catalog.security_identity import SecurityMasterStore

    data_root = tmp_path / "data-project"
    (data_root / "config").mkdir(parents=True)
    runner.seed_identity(data_root, "loopback", {"market": "US"})
    original = SecurityMasterStore(data_root / "catalog/security_master").path_for("US")
    before = runner.fingerprint(original)
    config = data_root / "config/sources.json"
    config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog",
                                 "roots": [{"root_id": "raw", "path": "companies",
                                            "kind": "company_raw"}]}), encoding="utf-8")
    config_before = config.read_bytes()
    monkeypatch.setattr(runner, "ROOT", tmp_path / "code-only-checkout")
    owned = tmp_path / "owned-test-lake"
    result = runner.seed_identity(owned, "live", {"market": "US"}, source_catalog_config=config)
    copied = SecurityMasterStore(owned / "catalog/security_master").path_for("US")
    assert result["original"] == str(original)
    assert result["fingerprint"] == runner.fingerprint(copied) == runner.fingerprint(original) == before
    assert config.read_bytes() == config_before


def test_missing_selected_identity_never_falls_back_to_another_checkout(tmp_path, monkeypatch):
    from company_wiki.source_catalog.security_identity import SecurityMasterUnavailableError

    decoy = tmp_path / "other-checkout"
    (decoy / "config").mkdir(parents=True)
    runner.seed_identity(decoy, "loopback", {"market": "US"})
    config = tmp_path / "selected/config/sources.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog",
                                 "roots": [{"root_id": "raw", "path": "companies",
                                            "kind": "company_raw"}]}), encoding="utf-8")
    monkeypatch.setattr(runner, "ROOT", decoy)
    with pytest.raises(SecurityMasterUnavailableError):
        runner.seed_identity(tmp_path / "owned", "live", {"market": "US"}, source_catalog_config=config)


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
