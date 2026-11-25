"""Ordinary product invocations retain failures independently of their caller."""
import json
import logging
import os
from pathlib import Path
import subprocess
import sys


def test_unconfigured_public_source_read_keeps_its_cause_after_exit(tmp_path):
    from support.sr_cwp_fixtures import build_catalog

    seeded = build_catalog(tmp_path)
    ref = seeded.refs["annual-report.txt"].to_dict()
    seeded.catalog.close()
    (tmp_path / "companies/Acme/raw/annual-report.txt").write_bytes(b"damaged fixture")
    env = {k: v for k, v in os.environ.items() if not k.startswith("RESEARCH_FEEDBACK_")}
    env.update(LOCALAPPDATA=str(tmp_path / "state"), XDG_STATE_HOME=str(tmp_path / "state"),
               PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    args = [sys.executable, "-B", "-m", "company_wiki.source_catalog.source_reader_cli", "--config",
            str(tmp_path / "config/catalog.json"), "--document-id", ref["document_id"],
            "--source-id", ref["source_id"], "--content-sha256", ref["content_sha256"]]
    run = subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, check=False)
    assert (run.returncode, run.stdout) == (2, b"")
    reason = json.loads(run.stderr)["reason"]
    ready, = (tmp_path / "state").rglob("feedback-*.ready")
    row = json.loads(ready.with_suffix(".jsonl").read_bytes())
    assert row["owner"] == "company-wiki" and row["disposition"] == "deviation"
    details = json.loads((ready.parent / row["details_ref"]).read_bytes())
    assert details["reason"] == reason and details["exceptions"][0]["type"] == "SourceReadError"
    assert ref["source_id"] == details["source_id"]
    assert "damaged fixture" not in str(details)
    local_log = tmp_path / "state/company-wiki/logs/runtime_errors.log"
    text = local_log.read_text(encoding="utf-8")
    assert row["run_id"] in text and "SourceReadError" in text and reason in text


def test_source_catalog_status_returns_owned_reason_and_logs_original_cause(tmp_path):
    config = tmp_path / "config/catalog.json"
    config.parent.mkdir()
    (tmp_path / "companies").mkdir()
    config.write_text(json.dumps({
        "schema_version": "1.0", "catalog_dir": "catalog", "roots": [{
            "root_id": "company_raw", "path": "companies", "kind": "company_raw",
            "adapter_id": "company_raw_v1", "read_only": True,
        }],
    }), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("RESEARCH_FEEDBACK_")}
    env.update(LOCALAPPDATA=str(tmp_path / "state"), XDG_STATE_HOME=str(tmp_path / "state"),
               PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    result = subprocess.run(
        [sys.executable, "-B", "-m", "company_wiki.source_catalog.cli", "--config", str(config), "status"],
        cwd=tmp_path, env=env, capture_output=True, timeout=20, check=False,
    )
    assert (result.returncode, result.stdout) == (1, b"")
    assert json.loads(result.stderr)["reason"] == "catalog_missing"
    assert not (tmp_path / "catalog").exists()
    log = (tmp_path / "state/company-wiki/logs/runtime_errors.log").read_text(encoding="utf-8")
    assert "CatalogReaderUnavailable" in log and "FileNotFoundError" in log


def test_missing_profile_for_optional_log_does_not_change_success_or_leak_scope(monkeypatch):
    from company_wiki import runtime_feedback

    for key in ("LOCALAPPDATA", "XDG_STATE_HOME", "RESEARCH_FEEDBACK_DIR", "RESEARCH_FEEDBACK_OUT"):
        monkeypatch.delenv(key, raising=False)

    def missing_home():
        raise RuntimeError("profile not loaded")

    monkeypatch.setattr(Path, "home", missing_home)

    @runtime_feedback.entry("catalog-status")
    def main():
        return 0

    assert main() == 0
    assert runtime_feedback._current.get() is None


def test_native_diagnostic_does_not_propagate_to_a_caller_stdout_logger(tmp_path, monkeypatch, capsys):
    from company_wiki import runtime_feedback

    monkeypatch.setenv("RESEARCH_FEEDBACK_OUT", str(tmp_path / "observations.jsonl"))
    caller_logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    caller_logger.addHandler(handler)

    @runtime_feedback.entry("status")
    def main():
        runtime_feedback.record("status", "failed", error=ValueError("native fixture reason"))
        print('{"status":"failed"}')
        return 1

    try:
        assert main() == 1
        assert capsys.readouterr().out == '{"status":"failed"}\n'
    finally:
        caller_logger.removeHandler(handler)
        handler.close()


def test_accounting_and_one_failed_member_survive_successful_outer_command(tmp_path, monkeypatch):
    from company_wiki.runtime_feedback import document_results

    monkeypatch.setenv("RESEARCH_FEEDBACK_DIR", str(tmp_path))
    monkeypatch.delenv("RESEARCH_FEEDBACK_OUT", raising=False)
    data = {"run_id": "run-1", "items": [
        {"state": "uncertain", "reason_codes": ["source_owner_refused"], "source_ref": {"source_id": "source-A"}},
        {"state": "read", "reason_codes": [], "source_ref": {"source_id": "source-B"}},
    ]}
    document_results("read-incremental", data)
    document_results("read-incremental", data)
    saved, = tmp_path.glob("feedback-*.ready")
    row = json.loads(saved.with_suffix(".jsonl").read_bytes())
    assert row["run_id"] == "run-1" and row["actual"] == "uncertain"
    assert row["step_id"].endswith("source-A")

def test_failed_member_does_not_hide_a_separate_uncaught_error(tmp_path, monkeypatch):
    import pytest
    from company_wiki import runtime_feedback

    monkeypatch.delenv("RESEARCH_FEEDBACK_OUT", raising=False)
    monkeypatch.setenv("RESEARCH_FEEDBACK_DIR", str(tmp_path / "not-a-dir"))
    (tmp_path / "not-a-dir").touch()
    for key in ("LOCALAPPDATA", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / "state"))

    @runtime_feedback.entry("outer")
    def run():
        runtime_feedback.record("member", "failed", item="customer private value")
        raise RuntimeError("decoder failed: API_KEY=customer-private-value")

    with pytest.raises(RuntimeError):
        run()
    entries = [json.loads(p.with_suffix(".jsonl").read_bytes()) for p in tmp_path.rglob("*.ready")]
    assert len(entries) == 2 and len({entry["run_id"] for entry in entries}) == 1
    assert "outer" in {entry["step_id"] for entry in entries} and "customer private" not in str(entries)
    details = [json.loads(p.read_bytes()) for p in tmp_path.rglob("*.diagnostic.json")]
    assert "decoder failed" in str(details)
    assert "customer-private-value" not in str(details)

def test_torn_sidecar_preserves_prior_bytes_and_next_complete_row(tmp_path, monkeypatch):
    from company_wiki.runtime_feedback import record

    out = tmp_path / "existing.jsonl"
    out.write_bytes(b'{"old":')
    monkeypatch.setenv("RESEARCH_FEEDBACK_OUT", str(out))
    record("probe", "failed", reason="read_timeout")
    previous, complete = out.read_bytes().splitlines()
    assert previous == b'{"old":'
    assert json.loads(complete)["actual"] == "failed"


def test_pending_substep_does_not_explain_separate_exit_failure(tmp_path, monkeypatch):
    from company_wiki.runtime_feedback import entry, record

    monkeypatch.delenv("RESEARCH_FEEDBACK_OUT", raising=False)
    monkeypatch.setenv("RESEARCH_FEEDBACK_DIR", str(tmp_path))

    @entry("outer")
    def run():
        record("publish", "activation_pending", explains_invocation=False)
        return 4

    assert run() == 4
    rows = [json.loads(path.read_bytes()) for path in tmp_path.glob("*.jsonl")]
    assert {(row["step_id"], row["actual"]) for row in rows} == {
        ("publish", "activation_pending"), ("outer", "exit:4"),
    }


def test_faulty_optional_exception_properties_do_not_erase_the_native_cause(tmp_path, monkeypatch):
    from company_wiki.runtime_feedback import entry
    import pytest

    monkeypatch.setenv("RESEARCH_FEEDBACK_DIR", str(tmp_path))
    monkeypatch.delenv("RESEARCH_FEEDBACK_OUT", raising=False)

    class BrokenDisk(OSError):
        @property
        def errno(self):
            raise RuntimeError("optional errno failed")

    class BrokenJSON(json.JSONDecodeError):
        def __getattribute__(self, key):
            if key in {"lineno", "colno"}:
                raise RuntimeError("optional position failed")
            return super().__getattribute__(key)

    for exc in (BrokenDisk(5, "disk unavailable"), BrokenJSON("incomplete JSON", "", 0)):
        @entry("native")
        def fail():
            raise exc
        with pytest.raises(type(exc)) as original:
            fail()
        assert original.value is exc
    details = [json.loads(p.read_bytes())["exceptions"][0] for p in tmp_path.glob("*.diagnostic.json")]
    by_type = {detail["type"]: detail for detail in details}
    assert set(by_type) == {"BrokenDisk", "BrokenJSON"}
    assert by_type["BrokenDisk"]["errno"] == 5 and "disk unavailable" in by_type["BrokenDisk"]["messages"]
    assert by_type["BrokenJSON"]["locations"]
    assert len(list(tmp_path.glob("*.ready"))) == 2


def test_document_failure_preserves_each_original_attempt(tmp_path, monkeypatch):
    from company_wiki.runtime_feedback import document_results, entry

    monkeypatch.setenv("RESEARCH_FEEDBACK_DIR", str(tmp_path))
    monkeypatch.delenv("RESEARCH_FEEDBACK_OUT", raising=False)
    member = {"item_key": "source-a", "state": "failed", "reason_codes": ["disk"]}
    native = {"run_id": "daily", "items": [member]}

    @entry("daily-job")
    def invoke():
        document_results("read", native)
        return 0

    for attempt in ("first", "second"):
        monkeypatch.setenv("RESEARCH_FEEDBACK_ATTEMPT_ID", attempt)
        invoke()
    native["attempt_id"] = "frozen-batch"
    invoke()
    member["attempt_id"] = "frozen-member"
    invoke()
    monkeypatch.setenv("RESEARCH_FEEDBACK_ATTEMPT_ID", "reader-after-restart")
    invoke()
    rows = [json.loads(p.read_bytes()) for p in tmp_path.glob("*.jsonl")]
    assert len(rows) == 4
    assert {(r["run_id"], r["attempt_id"]) for r in rows} == {
        ("daily", k) for k in ("first", "second", "frozen-batch", "frozen-member")}


def test_native_feedback_in_deep_state_root(tmp_path, monkeypatch):
    from company_wiki.file_mutex import win32_filesystem_path
    from company_wiki.runtime_feedback import record
    from shutil import rmtree

    state = tmp_path.joinpath(*(["deep-state-" + "x" * 30] * 8))
    monkeypatch.delenv("RESEARCH_FEEDBACK_OUT", raising=False)
    monkeypatch.delenv("RESEARCH_FEEDBACK_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(state))
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    try:
        record("owner-read", "failed", error=OSError(5, "original read failed"))
        packet, = win32_filesystem_path(state).rglob("*.jsonl")
        assert packet.with_suffix(".ready").exists()
        detail = json.loads((packet.parent / json.loads(packet.read_bytes())["details_ref"]).read_bytes())
        assert detail["exceptions"][0]["errno"] == 5
    finally:
        if win32_filesystem_path(state).is_dir():
            rmtree(win32_filesystem_path(state))
        for parent in state.parents:
            if parent == tmp_path:
                break
            if win32_filesystem_path(parent).is_dir():
                win32_filesystem_path(parent).rmdir()
