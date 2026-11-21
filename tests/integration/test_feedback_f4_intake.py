from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]
PYTHON = [sys.executable, "-B", "-X", "utf8"]
OWNER = "fixture-owner"

PRODUCER = """
import json
import os
from pathlib import Path
import sys

run_id = os.environ["RESEARCH_FEEDBACK_RUN_ID"]
mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
record = {"schema_version":"feedback-observation/1", "owner":"fixture-owner",
          "run_id":run_id, "attempt_id":os.environ["RESEARCH_FEEDBACK_ATTEMPT_ID"],
          "step_id":"original-read", "check_id":"result", "actual":"ok", "expected":"ok"}
if mode == "only-child-observed":
    record["owner"] = "downstream-owner"
elif mode == "unrelated-refusal":
    record["refusal_code"] = "fixture_refusal"
elif mode == "process-reported":
    record.update(check_id="process-outcome", actual="exit:7", expected="exit:0",
                  parent_step_id=os.environ["RESEARCH_FEEDBACK_PROCESS_STEP_ID"])
Path(os.environ["RESEARCH_FEEDBACK_OUT"]).write_text(json.dumps(record) + "\\n", encoding="utf-8")
with Path("business-count.txt").open("a") as count:
    count.write("entered\\n")
print("owner result")
print("owner usage", file=sys.stderr)
raise SystemExit(17 if mode in ("only-child-observed", "unrelated-refusal") else 7)
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
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    triage = "import json; print(json.dumps({'result': {'decision': 'needs_evidence'}}))"
    config["intake_hosts"] = "hosts.json"
    config["owners"][OWNER].update(timeout_seconds=10, actions={"triage": [*PYTHON, "-c", triage]})
    settings.write_text(json.dumps(config), encoding="utf-8")
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
        actions = connection.execute("SELECT json_extract(request, '$.kind'), state FROM actions").fetchall()
    # The producer's successful substep and its actual exit 7 are separate facts.
    assert sorted(actions) == [("observe", "done"), ("observe", "done"), ("triage", "done")]


@pytest.mark.parametrize("failure", ["early-exit", "not-installed", "only-child-observed", "unrelated-refusal"])
def test_cold_drain_keeps_unreported_process_failure_for_its_own_owner(tmp_path, monkeypatch, failure):
    from tools.feedback_loop import intake

    # Hold the asynchronous wake to make an actual cold reader the first importer.
    monkeypatch.setattr(intake, "wake", lambda *args, **kwargs: None)
    monkeypatch.setenv("RESEARCH_FEEDBACK_RUN_ID", "original-run")
    monkeypatch.setenv("RESEARCH_FEEDBACK_ATTEMPT_ID", "original-attempt")
    reader, hosts = configuration(tmp_path)
    secret_fixture = "unused-test-secret-42"
    if failure == "not-installed":
        business = [str(tmp_path / "missing-test-program"), secret_fixture]
        expected_exit, expected_actual = 127, "launch:FileNotFoundError"
    else:
        if failure == "early-exit":
            business = [*PYTHON, "-c", "raise SystemExit(17)", secret_fixture]
        else:
            business = [*PYTHON, "-c", PRODUCER, failure]
        expected_exit, expected_actual = 17, "exit:17"
    assert intake.run_observed(tmp_path / "settings.json", hosts, OWNER, business, 0) == expected_exit
    for _ in range(2):
        subprocess.run([*reader, "drain"], cwd=ROOT, check=True, capture_output=True, timeout=30)
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as db:
        requests = [json.loads(row[0]) for row in db.execute("SELECT request FROM actions")]
    observed = [request["payload"]["observation"] for request in requests if request["kind"] == "observe"
                and request["owner"] == OWNER and request["payload"]["observation"]["check_id"] == "process-outcome"]
    assert len(observed) == 1
    row = observed[0]
    assert (row["run_id"], row["attempt_id"], row["actual"], row["disposition"]) == (
        "original-run", "original-attempt", expected_actual, "deviation")
    assert secret_fixture not in json.dumps(row)
    assert "cost" not in row and row["evidence_ref"]
    receipt, = (tmp_path / "observations").glob("*.process")
    assert secret_fixture not in receipt.read_text(encoding="utf-8")
    if failure == "not-installed":
        assert json.loads(receipt.read_bytes())["errno"] is not None


def test_atomic_failure_publication_is_resumed_from_original_attempt(tmp_path, monkeypatch):
    from tools.feedback_loop import intake

    reader, hosts = configuration(tmp_path)
    with monkeypatch.context() as patch:
        patch.setenv("RESEARCH_FEEDBACK_RUN_ID", " ")
        patch.setenv("RESEARCH_FEEDBACK_ATTEMPT_ID", "")
        patch.setattr(intake, "wake", lambda *args, **kwargs: None)
        replace = Path.replace

        def interrupted(source, destination):
            if destination.suffix == ".process":
                raise PermissionError("injected at publication")
            return replace(source, destination)

        patch.setattr(Path, "replace", interrupted)
        assert intake.run_observed(tmp_path / "settings.json", hosts, OWNER,
                                   [*PYTHON, "-c", "raise SystemExit(33)"], 0) == 33
    directory = tmp_path / "observations"
    pending, = directory.glob("*.pending")
    original = json.loads(pending.read_bytes())
    assert original["run_id"].strip() and original["attempt_id"].strip()
    assert pending.with_suffix(".process-tmp").is_file()
    subprocess.run([*reader, "drain"], cwd=ROOT, check=True, capture_output=True, timeout=20)
    recovered = json.loads(pending.with_suffix(".process").read_bytes())
    assert recovered["actual"] == "exit:33"
    assert all(recovered[key] == value for key, value in original.items())


def test_killed_supervisor_has_cold_recovery_identity_without_restarting_child(tmp_path):
    command, _ = configuration(tmp_path)
    child = """
import os, json, time
from pathlib import Path
original = {"schema_version": "feedback-observation/1", "owner": "fixture-owner",
            "run_id": os.environ["RESEARCH_FEEDBACK_RUN_ID"], "attempt_id": os.environ["RESEARCH_FEEDBACK_ATTEMPT_ID"],
            "step_id": "early-check", "check_id":"shape", "expected":"ok", "actual":"ok"}
Path(os.environ["RESEARCH_FEEDBACK_OUT"]).write_text(json.dumps(original) + '\\n')
with Path('started').open('a') as output:
    output.write('once\\n')
deadline = time.monotonic() + 20
while not Path('release').exists() and time.monotonic() < deadline:
    time.sleep(0.05)
Path('finished').touch()
"""
    supervisor = subprocess.Popen([*command, "run", "--owner", OWNER, "--", *PYTHON, "-c", child],
                                  cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 15
        while not (tmp_path / "started").exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert (tmp_path / "started").is_file()
        supervisor.kill()
        supervisor.wait(timeout=5)
        reads = [json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT, timeout=15))
                 for _ in range(2)]
        assert reads[0]["unconfirmed"] == reads[1]["unconfirmed"]
        original, = reads[0]["unconfirmed"]
        assert original["owner"] == OWNER and all(original[k] for k in ("run_id", "attempt_id", "step_id"))
        assert (tmp_path / "started").read_text().splitlines() == ["once"]
    finally:
        (tmp_path / "release").touch()
        if supervisor.poll() is None:
            supervisor.kill()
        supervisor.wait(timeout=5)
        deadline = time.monotonic() + 5
        while not (tmp_path / "finished").exists() and time.monotonic() < deadline:
            time.sleep(0.05)


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
    # The native error explicitly accounts for the exit of the monitored process.
    done = subprocess.run([*command, "run", "--owner", OWNER, "--", *PYTHON, "-c", PRODUCER, "process-reported"],
                          cwd=ROOT, capture_output=True, check=False, timeout=20)
    assert done.returncode == 7
    ready, = (tmp_path / "observations").glob("*.jsonl")
    assert not ready.with_suffix(".process").exists()
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
