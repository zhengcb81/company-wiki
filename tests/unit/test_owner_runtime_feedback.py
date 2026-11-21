"""Ordinary product invocations retain failures independently of their caller."""
import json
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
