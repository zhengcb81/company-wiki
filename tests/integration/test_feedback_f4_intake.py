from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
PYTHON = [sys.executable, "-B", "-X", "utf8"]
OWNER = "fixture-owner"

PRODUCER = """
import json
import os
from pathlib import Path
import sys

run_id = os.environ["RESEARCH_FEEDBACK_RUN_ID"]
record = {"schema_version":"feedback-observation/1", "owner":"fixture-owner",
          "run_id":run_id, "attempt_id":os.environ["RESEARCH_FEEDBACK_ATTEMPT_ID"],
          "step_id":"original-read", "check_id":"result", "actual":sys.argv[1] if len(sys.argv) > 1 else "ok",
          "expected":"ok"}
Path(os.environ["RESEARCH_FEEDBACK_OUT"]).write_text(json.dumps(record) + "\\n", encoding="utf-8")
with Path("business-count.txt").open("a") as count:
    count.write("entered\\n")
print("owner result")
print("owner usage", file=sys.stderr)
raise SystemExit(7)
"""

OWNER_PORT = """
import json
import sys
import time

kind = sys.argv[1]
request = json.load(sys.stdin)
if kind == "triage":
    time.sleep(1.5)
result = {
    "triage": {"decision": "repair", "issue_ref": "owner/projection", "generation": "1"},
    "repair": {"fixed_version": "next"},
    "replay": {"verdict": "verified", "verified_version": "next", "evidence_ref": "original/read"},
    "report": {"recorded": True},
}[kind]
if kind == "report":
    from pathlib import Path
    with Path("reports.txt").open("a") as stream:
        stream.write(request["action_id"] + "\\n")
print(json.dumps({"result": result}))
"""


def configuration(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"state": "actions.sqlite", "owners": {
        OWNER: {"cwd": str(tmp_path), "observation_dir": "observations"}
    }}), encoding="utf-8")
    hosts = tmp_path / "hosts.json"
    hosts.write_text(json.dumps({OWNER: [*PYTHON, "-m", "tools.feedback_loop.local_host",
                                         "--config", str(settings), "rpc"]}), encoding="utf-8")
    command = [*PYTHON, "-m", "tools.feedback_loop.intake", "--settings", str(settings),
               "--hosts", str(hosts), "--wait-seconds", "0"]
    return command, hosts


def test_business_completion_wakes_existing_host_without_changing_output(tmp_path):
    command, _ = configuration(tmp_path)
    done = subprocess.run([*command, "run", "--owner", OWNER, "--", *PYTHON, "-c", PRODUCER],
                          cwd=ROOT, capture_output=True, check=False, timeout=20, text=True)
    assert (done.returncode, done.stdout, done.stderr) == (7, "owner result\n", "owner usage\n")
    out, = (tmp_path / "observations").glob("*.jsonl")
    # Wait for the detached wake, which uses the ordinary host path.
    deadline = time.monotonic() + 15
    while out.with_suffix(".ready").exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not out.with_suffix(".ready").exists()
    assert (tmp_path / "business-count.txt").read_text() == "entered\n"
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
        kind, state = connection.execute("SELECT json_extract(request, '$.kind'), state FROM actions").fetchone()
    assert (kind, state) == ("observe", "done")


def test_restart_drains_the_original_marker_and_preserves_incomplete_run(tmp_path):
    command, _ = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_text(encoding="utf-8"))
    # A parent and its provider share the sidecar when the provider inherits
    # the launch environment. The owner's directory should be drained once.
    config["owners"]["caller-owner"] = {"cwd": str(tmp_path), "observation_dir": "observations"}
    settings.write_text(json.dumps(config), encoding="utf-8")
    directory = tmp_path / "observations"
    directory.mkdir()
    original = directory / ("feedback-" + "1" * 32 + ".jsonl")
    row = {"schema_version": "feedback-observation/1", "owner": OWNER,
           "run_id": "original-run", "attempt_id": "original-attempt", "step_id": "original-read",
           "check_id": "action-started", "expected": "started", "actual": "started",
           "terminal_check_id": "result", "evidence_ref": "job-original"}
    original.write_text(json.dumps(row) + "\n", encoding="utf-8")
    pending = original.with_suffix(".pending")
    pending.touch()

    def drain():
        result = subprocess.check_output([*command, "drain"], cwd=ROOT, timeout=20)
        return json.loads(result)

    first = drain()
    assert (first["remaining"], first["processed"]) == (1, 1)
    assert pending.is_file()
    assert not (tmp_path / "business-count.txt").exists()
    # A late native finish remains part of the existing sidecar and original IDs.
    row.update(check_id="result", expected="ok", actual="ok")
    with original.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")
    pending.replace(original.with_suffix(".ready"))
    before = original.read_bytes()
    assert drain()["remaining"] == 0
    assert drain()["remaining"] == 0 and original.read_bytes() == before
    assert not (tmp_path / "business-count.txt").exists()
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
        assert connection.execute("SELECT count(*) FROM actions").fetchone() == (2,)


def test_completed_actions_continue_feedback_after_initial_drain_has_exited(tmp_path):
    command, _ = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_text(encoding="utf-8"))
    config["intake_hosts"] = "hosts.json"
    config["owners"][OWNER].update(timeout_seconds=15, actions={
        kind: [*PYTHON, "-c", OWNER_PORT, kind] for kind in ("triage", "repair", "replay", "report")
    })
    settings.write_text(json.dumps(config), encoding="utf-8")
    done = subprocess.run([*command, "run", "--owner", OWNER, "--", *PYTHON, "-c", PRODUCER, "deviation"],
                          cwd=ROOT, capture_output=True, check=False, timeout=20)
    assert done.returncode == 7
    ready, = (tmp_path / "observations").glob("*.jsonl")
    marker = ready.with_suffix(".ready")
    deadline = time.monotonic() + 30
    while marker.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not marker.exists()
    assert (tmp_path / "business-count.txt").read_text() == "entered\n"
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
        rows = connection.execute("SELECT action_id, json_extract(request, '$.kind'), state FROM actions").fetchall()
    assert {kind: state for _, kind, state in rows} == dict.fromkeys(
        ("observe", "triage", "repair", "replay", "report"), "done",
    )
    assert (tmp_path / "reports.txt").read_text().splitlines() == [key for key, kind, _ in rows if kind == "report"]
