from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]
PORT = ROOT / "tests/fixtures/feedback_loop/owner_port.py"


@pytest.mark.parametrize("interrupt", [False, True])
def test_fresh_process_restart_and_concurrent_delivery(tmp_path, interrupt):
    db = tmp_path / "jobs.sqlite"
    port = [sys.executable, "-B", str(PORT), str(db)] + (["--lose-reply"] if interrupt else [])
    config = tmp_path / "hosts.json"
    config.write_text(json.dumps({"company-wiki": port, "revenue-forecast": port}), encoding="utf-8")
    evidence = tmp_path / "source.jsonl"
    row = {"schema_version": "feedback-observation/1", "owner": "company-wiki", "origin_owner": "revenue-forecast",
           "run_id": "original-run", "attempt_id": "initial-review", "step_id": "read/17", "check_id": "subject",
           "expected": "attributed", "actual": "lost", "argv": ["untrusted", "ignored"]}
    evidence.write_text(json.dumps(row) + "\n", encoding="utf-8")
    cli = [sys.executable, "-B", "-m", "tools.feedback_loop"]

    def run(args):
        output = subprocess.run([*cli, *map(str, args)], cwd=ROOT, capture_output=True, check=True, timeout=45)
        return json.loads(output.stdout)

    assert "argv" not in run(["plan", evidence])["observations"][0]
    tick = ["tick", "--hosts", config, evidence]
    if interrupt:
        assert run(tick)["observations"][0]["status"] == "unknown"
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(run, (tick, tick)))
    assert all(r["observations"][0]["status"] == "verified" for r in results)
    with closing(sqlite3.connect(db)) as conn:
        assert dict(conn.execute("SELECT kind, count(*) FROM jobs GROUP BY kind")) == {
            "observe": 1, "triage": 1, "repair": 1, "replay": 1, "report": 1}


def test_configured_completion_wakes_real_control_process(tmp_path):
    from tools.document_understanding_benchmark.phase_c_runner import deliver_feedback

    db = tmp_path / "jobs.sqlite"
    config = tmp_path / "hosts.json"
    config.write_text(json.dumps({"company-wiki": [sys.executable, "-B", str(PORT), str(db)]}), encoding="utf-8")
    env = {"RESEARCH_FEEDBACK_OUT": str(tmp_path / "obs"), "RESEARCH_FEEDBACK_HOSTS": str(config)}
    source = {"states": [{"run_id": "one", "public_replay": {"replay_status": "verified"},
                          "same_run_zero_POST": False}]}
    delivery = deliver_feedback(tmp_path, source, env, "a1")
    assert delivery["dispatch"]["status"] == "scheduled"
    result_file = tmp_path / "feedback-dispatch.json"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            completed = json.loads(result_file.read_bytes())
            break
        except (OSError, ValueError):
            time.sleep(0.05)
    else:
        pytest.fail("configured feedback control process did not publish its terminal receipt")
    assert completed["states"] == {"expected": 1, "verified": 1, "unknown": 1}
    with closing(sqlite3.connect(db)) as conn:
        assert dict(conn.execute("SELECT kind, count(*) FROM jobs GROUP BY kind")) == {
            "observe": 3, "triage": 1, "repair": 1, "replay": 1, "report": 1}
