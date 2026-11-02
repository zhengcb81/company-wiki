"""R7: observations retain evidence without vetoing successful work by volume."""
from __future__ import annotations

from copy import deepcopy
import gzip
import hashlib
import json
import sys
from types import SimpleNamespace

import pytest

from company_wiki._bounded_process import ChildFailed, ChildTimeout, run_bounded
from tools import pre_push_gate as gate
from tools.cross_market_suite import runtime_evidence
from tools.document_understanding_benchmark import phase_c_observer as observer
from tools.holdout_replay import producer
from tools.identity_audit import core as identity
from tools.narrative_g2_replay import report as g2_report
from tools.raw_duplicate_audit import report as duplicate_report
from tools.source_root_portability import report as portability_report
from tools.storage_footprint import core as footprint_core
from tools.storage_footprint import report as footprint_report


@pytest.mark.parametrize("pipe", ["stdout", "stderr"])
def test_log_tail_captures_volume_without_changing_success(pipe):
    body = b"x" * 131072 + b"final-log-message"
    code = f"import sys;sys.{pipe}.buffer.write(b'x'*131072+b'final-log-message');sys.{pipe}.flush()"
    result = run_bounded([sys.executable, "-B", "-c", code], timeout_seconds=10,
                         stdout_cap_bytes=512, stderr_cap_bytes=512, log_tail=True)
    assert result["returncode"] == 0
    assert result[pipe] == body[-512:]
    assert result[pipe + "_bytes_read"] == len(body)


def test_log_tail_preserves_actual_nonzero_exit_and_timeout():
    command = [sys.executable, "-B", "-c",
               "import sys;sys.stdout.write('x'*10000+'failure-tail');sys.exit(17)"]
    with pytest.raises(ChildFailed) as caught:
        run_bounded(command, timeout_seconds=10, stdout_cap_bytes=128,
                    stderr_cap_bytes=128, log_tail=True)
    assert caught.value.returncode == 17
    assert caught.value.stdout.endswith(b"failure-tail")
    with pytest.raises(ChildTimeout):
        run_bounded([sys.executable, "-B", "-c", "import time;time.sleep(30)"],
                    timeout_seconds=0.3, log_tail=True)


def test_push_runner_chooses_log_capture_not_payload_rejection(monkeypatch):
    seen = []
    def child(*args, **kwargs):
        # Do not include the inherited process environment in assertion reprs.
        seen.append(kwargs.get("log_tail"))
        return {"stdout": b"3 passed\n", "stderr": b"", "returncode": 0}
    monkeypatch.setattr(gate, "run_bounded", child)
    assert gate._run(["synthetic"], "controlled check") == 0
    assert seen == [True]


def test_large_generation_checkpoint_is_complete_and_still_immutable(tmp_path):
    generation = {"required_evidence": "exact-original-context" * 40000}
    pin = observer.capture_generation_checkpoint(generation, tmp_path, "large-generation")
    assert json.loads(gzip.decompress((tmp_path / pin["file"]).read_bytes())) == generation
    assert pin["bytes"] > 512 * 1024
    with pytest.raises(ValueError, match="CHANGED"):
        observer.capture_generation_checkpoint({**generation, "changed": True}, tmp_path, "large-generation")


def test_large_prepared_bytes_follow_successful_owner_and_keep_actual_binding(tmp_path):
    from unit.test_phase_c_read_capture import prepared_materials
    _, store, draft, config = prepared_materials(tmp_path)
    payload = json.dumps({"required_evidence": "x" * (2 * 1024 * 1024)}).encode()
    wrapped = observer.prepared_artifact_observer(type(store).prepare, config)
    version = wrapped(store, draft, payload)
    files = list((tmp_path / "materials").glob("*.prepared.bundle.json.gz"))
    assert len(files) == 1 and gzip.decompress(files[0].read_bytes()) == payload
    assert version.content_sha256 == hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize("failure", [OSError("synthetic disk error"), ValueError("synthetic encoding error")])
def test_prepare_observation_failure_keeps_real_owner_result_once(tmp_path, monkeypatch, failure):
    from unit.test_phase_c_read_capture import prepared_materials
    _, store, draft, config = prepared_materials(tmp_path)
    config["events"] = str(tmp_path / "events.jsonl")
    calls = []
    original = type(store).prepare
    def owner(*args):
        calls.append(1)
        return original(*args)
    def broken(*args):
        raise failure
    monkeypatch.setattr(observer, "capture_prepared_checkpoint", broken)
    version = observer.prepared_artifact_observer(owner, config)(store, draft, b"actual owner bytes")
    assert version.status == "prepared" and calls == [1]
    event = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8"))
    assert event["observation_status"] == "incomplete" and event["owner_returned"] is True
    assert event["error_type"] == type(failure).__name__
    assert event["owner_artifact_version_id"] == version.artifact_version_id
    assert not list((tmp_path / "materials").iterdir())


def test_unwritable_observer_event_is_unknown_not_fake_saved_or_owner_retry(tmp_path, monkeypatch, capsys):
    version = SimpleNamespace(status="prepared", artifact_version_id="existing-owner-result")
    config = {"events": str(tmp_path / "unwritable"), "activation_run_id": "synthetic"}
    def broken(*args):
        raise OSError("synthetic observer unavailable")
    monkeypatch.setattr(observer, "capture_prepared_checkpoint", broken)
    monkeypatch.setattr(observer, "_append", broken)
    calls = []
    def owner(*args):
        calls.append(1)
        return version
    assert observer.prepared_artifact_observer(owner, config)(None, None, b"payload") is version
    assert calls == [1] and not list(tmp_path.iterdir())
    failure = config["observer_errors"][0]
    assert failure["observation_status"] == "incomplete" and failure["event_saved"] is False
    assert json.loads(capsys.readouterr().err)["event_saved"] is False


@pytest.mark.parametrize("module", [g2_report, portability_report])
def test_complete_replay_report_survives_old_size_threshold(tmp_path, module):
    evidence = {"required_ids": ["original-unit"], "evidence": "x" * (8 * 1024 * 1024 + 1)}
    target = module.write_report(SimpleNamespace(path=tmp_path), evidence)
    assert json.loads(target.read_text(encoding="utf-8")) == evidence


@pytest.mark.parametrize("module", [g2_report, portability_report])
def test_invalid_report_is_not_published(tmp_path, module):
    with pytest.raises((ValueError, TypeError)):
        module.write_report(SimpleNamespace(path=tmp_path), {"not_json": float("nan")})
    assert not (tmp_path / "report.json").exists()


def test_complete_footprint_preserves_every_error_and_full_locator(tmp_path):
    evidence = {"schema_version": footprint_core.REPORT_SCHEMA,
                "errors": [{"path": "full-path/" + "p" * 2000, "error": "E" * 2000} for _ in range(100)],
                "limitations": [], "required_ids": ["original-unit"]}
    before = deepcopy(evidence)
    value, notes = footprint_report.enforce_report_budget(evidence, max_bytes=1)
    assert value == before and notes == []
    target = footprint_core.write_report(tmp_path / "report.json", value, max_bytes=1)
    assert json.loads(target.read_text(encoding="utf-8")) == before


def test_duplicate_report_retains_all_groups_and_diagnostics_without_row_or_byte_gate():
    groups = [{"group_id": str(i), "locators": [{"location_id": "left"}, {"location_id": "right"}]} for i in range(4)]
    limits = []
    kept, rows, dropped = duplicate_report.apply_detail_row_cap(groups, max_rows=1, limits_hit=limits)
    assert kept == groups and rows == 8 and dropped == 0 and not limits
    report = {"duplicate_groups": groups, "counts": {}, "diagnostics": [{"required": "x" * 4000}] * 300}
    required = deepcopy(report)
    duplicate_report.apply_size_cap(report, max_bytes=1, limits_hit=limits)
    assert report["duplicate_groups"] == required["duplicate_groups"]
    assert report["diagnostics"] == required["diagnostics"] and not limits


@pytest.mark.parametrize("failure", ["json", "io"])
def test_duplicate_report_failure_does_not_claim_written(tmp_path, monkeypatch, failure):
    from tools.raw_duplicate_audit import assessment
    report = {"duplicate_groups": [], "diagnostics": [], "counts": {}}
    if failure == "json":
        report["diagnostics"] = [float("nan")]
    else:
        def broken(*args, **kwargs):
            raise OSError("synthetic output failure")
        monkeypatch.setattr(assessment, "write_json", broken)
    with pytest.raises((OSError, ValueError)):
        assessment._write_report(report, tmp_path / "report.json", overwrite=False)
    assert report["written"] is False and not (tmp_path / "report.json").exists()


def test_identity_receipt_retains_large_audit_results(monkeypatch):
    source = {"source_id": "source", "checks": {key: {"status": "pass"} for key in identity._CHECK_ORDER},
              "required_diagnostic": "x" * (16 * 1024 * 1024 + 1)}
    monkeypatch.setattr(identity, "_input_binding", lambda _: None)
    monkeypatch.setattr(identity, "_validate_request", lambda _: None)
    monkeypatch.setattr(identity, "load_catalog_config", lambda _: object())
    monkeypatch.setattr(identity, "SourceCatalog", lambda _: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(identity, "_audit_source", lambda *args: (source, False))
    result = identity.audit(config_path="unused", request={"source_refs": [{"source_id": "source"}], "evidence_spans": []})
    assert result["status"] == "ok" and result["sources"] == [source]


def test_runtime_evidence_retains_all_documents_and_large_valid_property(tmp_path):
    documents = [{"document_id": "doc-" + str(i), "errors": ["error-" + str(i) + "x" * 3000]} for i in range(15)]
    receipt = {"status": "completed", "documents": documents}
    value = runtime_evidence.capture_runtime_evidence(tmp_path / "absent.sqlite3", receipt, run_id="synthetic")
    observed = value["receipt"]["documents"]
    assert [row["document_id"] for row in observed] == [row["document_id"] for row in documents]
    assert [row["errors"] for row in observed] == [row["errors"] for row in documents]
    large = {"required_evidence": "x" * 40000, "original_ids": ["all-original-ids"]}
    assert runtime_evidence.runtime_properties({"cmrf_runtime_evidence": json.dumps(large)}) == {"runtime_evidence": large}


def test_runtime_file_identity_records_actual_loaded_module_without_clean_tree(monkeypatch, tmp_path):
    local = tmp_path / "src/company_wiki/unseen_module.py"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"actual_runtime = True\n")
    monkeypatch.setattr(producer, "sys", SimpleNamespace(modules={"company_wiki.unseen_module": SimpleNamespace(__file__=str(local))}), raising=False)
    identity_rows = producer.record_runtime_files(tmp_path)
    assert identity_rows["company_wiki.unseen_module"]["sha256"] == hashlib.sha256(local.read_bytes()).hexdigest()
    foreign = tmp_path.parent / "foreign_module.py"
    foreign.write_text("foreign=True", encoding="utf-8")
    monkeypatch.setattr(producer, "sys", SimpleNamespace(modules={"company_wiki.unseen_module": SimpleNamespace(__file__=str(foreign))}))
    with pytest.raises(producer.ProducerError):
        producer.record_runtime_files(tmp_path)
