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


def test_direct_owner_outbox_retries_unavailable_payload_from_a_cold_process(tmp_path):
    command, _ = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    config["owners"][OWNER]["native_observation_dirs"] = ["native", "native"]
    settings.write_text(json.dumps(config), encoding="utf-8")
    directory = tmp_path / "native"
    directory.mkdir()
    prefix = directory / ("feedback-" + "a" * 32)
    context = {"owner": OWNER, "run_id": "direct", "attempt_id": "one", "step_id": "read"}
    marker = prefix.with_suffix(".ready")
    marker.write_text(json.dumps(context), encoding="utf-8")

    def cold():
        return json.loads(subprocess.check_output([*command, "drain", "--owner", OWNER], cwd=ROOT, timeout=25))

    missing = cold()
    assert missing["remaining"] == 1 and marker.is_file()
    assert "native_observation_missing" in {item["code"] for item in missing["diagnostics"]}
    row = {**context, "schema_version": "feedback-observation/1", "check_id": "result",
           "expected": "refused", "actual": "refused", "disposition": "expected"}
    source = prefix.with_suffix(".jsonl")
    source.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert cold()["processed"] == 1 and not marker.exists()
    assert cold()["processed"] == 0 and source.exists()


def test_primary_inbox_outage_preserves_the_original_exit_without_reexecuting(tmp_path, monkeypatch):
    from tools.feedback_loop import intake

    command, _ = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    (tmp_path / "observations").write_text("temporarily unavailable", encoding="utf-8")
    monkeypatch.setattr(intake, "wake", lambda *args, **kwargs: None)
    monkeypatch.setenv("RESEARCH_FEEDBACK_RUN_ID", "outage-run")
    monkeypatch.setenv("RESEARCH_FEEDBACK_ATTEMPT_ID", "first")
    business = "from pathlib import Path; p=Path('calls'); p.write_text(p.read_text()+'x' if p.exists() else 'x'); raise SystemExit(19)"
    assert intake.run_observed(settings, tmp_path / "hosts.json", OWNER, [*PYTHON, "-c", business], 0) == 19
    summary = json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT, timeout=25))
    assert summary["processed"] >= 1 and (tmp_path / "calls").read_text() == "x"
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
        found = [json.loads(row[0])["payload"]["observation"] for row in connection.execute(
            "SELECT request FROM actions WHERE json_extract(request,'$.kind')='observe'")]
    assert any((row["run_id"], row["attempt_id"], row["actual"]) == ("outage-run", "first", "exit:19") for row in found)


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
    config["owners"]["unrelated"] = {"observation_dir": "unrelated"}
    settings.write_text(json.dumps(config), encoding="utf-8")
    unrelated = tmp_path / "unrelated" / ("feedback-" + "e" * 32 + ".ready")
    unrelated.parent.mkdir()
    unrelated.write_text(json.dumps({"owner": "unrelated"}))
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
    assert unrelated.exists()
    assert (tmp_path / "business-count.txt").read_text() == "entered\n"
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
        rows = connection.execute("SELECT action_id, json_extract(request, '$.kind'), state FROM actions").fetchall()
    assert {kind: state for _, kind, state in rows} == dict.fromkeys(
        ("observe", "triage", "repair", "replay", "report"), "done",
    )
    assert (tmp_path / "reports.txt").read_text().splitlines() == [key for key, kind, _ in rows if kind == "report"]


def test_host_restart_automatically_consumes_direct_native_packet(tmp_path):
    configuration(tmp_path)
    settings = tmp_path / "settings.json"
    cfg = json.loads(settings.read_bytes())
    cfg["owners"][OWNER]["native_observation_dirs"] = ["native"]
    settings.write_text(json.dumps(cfg), encoding="utf8")
    packet = tmp_path / "native" / ("feedback-" + "f" * 32 + ".jsonl")
    packet.parent.mkdir()
    identity = dict(owner=OWNER, run_id="original", attempt_id="one", step_id="saved")
    row = dict(identity, schema_version="feedback-observation/1", check_id="refused",
               expected="legitimate_refusal", actual="legitimate_refusal", disposition="expected")
    packet.write_text(json.dumps(row) + "\n", encoding="utf8")
    packet.with_suffix(".ready").write_text(json.dumps(identity), encoding="utf8")
    command = [*PYTHON, "-m", "tools.feedback_loop.local_host", "--config", str(settings), "recover", "--save-result"]
    results = []
    for _ in range(2):
        results.append(json.loads(subprocess.check_output(command, cwd=ROOT)))
        saved = json.loads(settings.with_name("last-native-recovery.json").read_bytes())
        assert saved.pop("finished_at") > 0 and saved == results[-1]
    assert [r["processed"] for r in results] == [1, 0]
    assert all(r["remaining"] == 0 for r in results)
    assert not (tmp_path / "business-count.txt").exists()


def test_native_ack_belongs_to_the_occurrence_named_by_its_marker(tmp_path):
    from tools.feedback_loop.observations import read_batch

    command, _ = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    cfg = json.loads(settings.read_bytes())
    cfg["owners"][OWNER]["native_observation_dirs"] = ["native"]
    settings.write_text(json.dumps(cfg), encoding="utf8")
    packet = tmp_path / "native" / ("feedback-" + "6" * 32 + ".jsonl")
    packet.parent.mkdir()
    marker = packet.with_suffix(".ready")
    identity = dict(owner=OWNER, run_id="original", attempt_id="attempt-A", step_id="read")
    row = dict(identity, schema_version="feedback-observation/1", check_id="outcome",
               expected="ok", actual="ok", disposition="expected")
    marker.write_text(json.dumps(identity), encoding="utf8")

    def cold():
        return json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT))

    for changed in ({"owner": "other"}, {"run_id": "wrong"}, {"attempt_id": "attempt-B"}, {"step_id": "wrong"}):
        packet.write_text(json.dumps(row | changed) + "\n", encoding="utf8")
        waiting = cold()
        assert waiting["remaining"] == 1 and waiting["processed"] == 0
        assert marker.is_file()
        assert "native_observation_mismatch" in {d["code"] for d in waiting["diagnostics"]}
    packet.write_text(json.dumps(row) + "\n", encoding="utf8")
    marker.write_text(json.dumps(identity | {"step_id": "intake/" + packet.stem}), encoding="utf8")
    waiting = cold()
    assert waiting["remaining"] == 1 and waiting["processed"] == 0
    occurrence, = read_batch([packet]).observations
    bound = identity | {"origin_owner": OWNER, "check_id": row["check_id"], "occurrence_id": occurrence}
    for changed in ({"origin_owner": "another"}, {"check_id": "unrelated"}, {"occurrence_id": "1" * 64}):
        marker.write_text(json.dumps(bound | changed), encoding="utf8")
        waiting = cold()
        assert waiting["remaining"] == 1 and waiting["processed"] == 0 and marker.exists()
    marker.write_text(json.dumps(bound), encoding="utf8")
    assert cold()["processed"] == 1 and not marker.exists()
    assert cold()["processed"] == 0


@pytest.mark.parametrize("deep", (False, True))
def test_kill_between_native_payload_and_ready_survives_cold_wake(tmp_path, deep, request):
    from shutil import rmtree
    from tools.feedback_loop.local_host import host_path

    command, _ = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    cfg = json.loads(settings.read_bytes())
    relative = Path("native").joinpath(*(["owner-" + "x" * 38] * 7 if deep else []))
    cfg["owners"][OWNER]["native_observation_dirs"] = [str(relative)]
    settings.write_text(json.dumps(cfg), encoding="utf8")
    directory = host_path(tmp_path / relative)
    directory.mkdir(parents=True)
    request.addfinalizer(lambda: rmtree(host_path(tmp_path / "native")))
    packet = directory / ("feedback-" + "2" * 32 + ".jsonl")
    identity = dict(owner=OWNER, run_id="original", attempt_id="one", step_id="read")
    source = (json.dumps(dict(identity, schema_version="feedback-observation/1", check_id="outcome",
                              expected="ok", actual="ok", disposition="expected")) + "\n").encode()
    producer = ("import os,sys; from pathlib import Path; p=Path(sys.argv[1]); "
                "p.write_bytes(sys.stdin.buffer.read()); os._exit(23)")
    run = subprocess.run([*PYTHON, "-c", producer, str(packet)], input=source)
    assert run.returncode == 23 and not packet.with_suffix(".ready").exists()

    def cold():
        return json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT))

    assert [cold()["processed"] for _ in range(2)] == [1, 0]
    assert packet.read_bytes() == source and not (tmp_path / "business-count.txt").exists()
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as conn:
        assert conn.execute("SELECT COUNT(*) FROM actions").fetchone() == (1,)


def test_only_finished_lookups_on_the_same_local_host_avoid_a_new_interpreter(tmp_path, monkeypatch):
    from tools.feedback_loop import host as transport
    from tools.feedback_loop.local_host import LocalHost
    from tools.feedback_loop.observations import digest

    _, registry = configuration(tmp_path)
    host = LocalHost(tmp_path / "settings.json")
    routes = json.loads(registry.read_bytes())
    key = "9" * 64
    body = {"occurrence_id": "original"}
    request = dict(schema_version="feedback-action/1", owner=OWNER, kind="observe", action_id=key,
                   method="lookup", payload=body, request_digest=digest([OWNER, "observe", key, body]))
    call = transport.process_host(routes, local=host)
    assert call(OWNER, request)["state"] == "absent"
    assert call(OWNER, request | {"method": "submit"})["state"] == "done"
    with monkeypatch.context() as patch:
        def external(*args, **kwargs):
            raise OSError("external transport called")
        patch.setattr(transport.subprocess, "run", external)
        assert call(OWNER, request)["state"] == "done"
        with pytest.raises(OSError, match="external transport called"):
            call(OWNER, request | {"method": "submit"})
        other = {OWNER: [*routes[OWNER][:-2], str(tmp_path / "another-config.json"), "rpc"]}
        with pytest.raises(OSError, match="external transport called"):
            transport.process_host(other, local=host)(OWNER, request)


def test_scoped_recovery_leaves_parallel_owner_marker_in_shared_inbox(tmp_path):
    from tools.feedback_loop.intake import drain
    from tools.feedback_loop.local_host import LocalHost
    from tools.feedback_loop.observations import digest

    _, registry = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    config["owners"]["parallel"] = {
        "observation_dir": "observations", "cwd": str(tmp_path), "timeout_seconds": 15,
        "actions": {"repair": [*PYTHON, "-c", "from pathlib import Path; Path('parallel-started').touch()"]},
    }
    settings.write_text(json.dumps(config))
    inbox = tmp_path / "observations"
    inbox.mkdir()
    marker = inbox / ("feedback-" + "c" * 32 + ".ready")
    marker.write_text(json.dumps({"owner": "parallel", "run_id": "original", "step_id": "intake/start"}))
    key = "7" * 64
    queued = LocalHost(settings)
    payload = {"issue_ref": "parallel/issue"}
    request = dict(schema_version="feedback-action/1", method="submit", owner="parallel", kind="repair",
                   action_id=key, payload=payload, request_digest=digest(["parallel", "repair", key, payload]))
    # Simulate the original supervisor dying between queue commit and wake.
    queued._wake = lambda _: False
    assert queued.handle(request)["state"] == "pending"
    result = drain(settings, registry, owner=[OWNER], wait_seconds=0)
    assert result["processed"] == result["remaining"] == result["woken"] == 0
    assert marker.exists()
    assert not (tmp_path / "parallel-started").exists()


def test_bundle_ack_is_published_after_all_original_steps_are_recorded(tmp_path):
    from hashlib import sha256

    command, _ = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    config["owners"][OWNER]["native_observation_dirs"] = ["native"]
    settings.write_text(json.dumps(config), encoding="utf8")
    inbox = tmp_path / "native"
    inbox.mkdir()
    packet = inbox / ("feedback-" + "d" * 32 + ".jsonl")
    identity = dict(owner=OWNER, run_id="bundle", attempt_id="first")
    rows = [dict(identity, step_id=step, schema_version="feedback-observation/1",
                 check_id="result", expected="ok", actual="ok", details_ref="proof")
            for step in ("first-doc", "second-doc")]
    packet.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf8")
    marker = packet.with_suffix(".ready")
    detail_bytes = b'{"details_id":"proof","reason":"original"}\n'
    marker.write_text(json.dumps(dict(identity, schema_version="feedback-delivery-ready/1",
                                      step_ids=["first-doc", "second-doc"], observations=2, details=1,
                                      observations_sha256=sha256(packet.read_bytes()).hexdigest(),
                                      details_sha256=sha256(detail_bytes).hexdigest())), encoding="utf8")
    proof = inbox / (packet.name + ".details.jsonl")

    def check():
        return json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT))

    original, advertised, receipt = packet.read_bytes(), marker.read_bytes(), packet.with_suffix(".ack")
    assert check()["remaining"] == 1 and marker.is_file() and not receipt.exists()
    for wrong in (b"", b'{"details_id":"proof"', b'{"details_id":"unrelated"}\n'):
        proof.write_bytes(wrong)
        assert check()["remaining"] == 1 and marker.is_file() and not receipt.exists()
    proof.write_bytes(b'{"details_id":"proof","reason":"old"}\n')
    assert "native_observation_checksum_mismatch" in {row["code"] for row in check()["diagnostics"]}
    proof.write_bytes(detail_bytes)
    assert check()["processed"] == 2 and receipt.is_file() and not marker.exists()
    assert check()["processed"] == 0 and packet.read_bytes() == original
    assert receipt.read_bytes() == advertised


def test_complete_native_bundle_can_ack_without_guessing_the_original_cost(tmp_path):
    command, _ = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    config["owners"][OWNER]["native_observation_dirs"] = ["native"]
    native_lookup = """import json,sys
row=json.load(sys.stdin)["payload"]["observation"]
ref=row["evidence_ref"]
status=ref if ref in ("failed","unconfirmed") else None
if status:
    print(json.dumps({"state":"done","result":{
        "evidence_ref":ref,"job_status":status,"status":"cost_unknown","cost_state":"unknown"}}))
else:
    print('{"state":"unknown"}')
"""
    config["owners"][OWNER].update(timeout_seconds=15, actions={"reconcile": [*PYTHON, "-c", native_lookup]})
    settings.write_text(json.dumps(config), encoding="utf8")
    directory = tmp_path / "native"
    directory.mkdir()
    packets = {}
    for ordinal, name in enumerate(("failed", "unconfirmed", "absent"), 1):
        packet = directory / f"feedback-{ordinal:032x}.jsonl"
        stem = dict(owner=OWNER, run_id=name, attempt_id="attempt", step_id="original")
        packet.write_text(json.dumps(dict(stem, schema_version="feedback-observation/1", check_id="recorded-cost",
                                          expected="known", actual="unknown", disposition="unknown",
                                          evidence_ref=name)) + "\n")
        marker = packet.with_suffix(".ready")
        marker.write_text(json.dumps(dict(stem, schema_version="feedback-delivery-ready/1",
                                          observations=1, details=0, step_ids=["original"])))
        packets[name] = (packet, packet.read_bytes())

    def cold():
        return json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT, timeout=25))

    first = cold()
    assert (first["processed"], first["remaining"]) == (3, 2)
    assert packets["failed"][0].with_suffix(".ack").is_file()
    assert all(packets[key][0].with_suffix(".ready").is_file() for key in ("unconfirmed", "absent"))
    second = cold()
    assert (second["processed"], second["remaining"]) == (2, 2)
    assert all(path.read_bytes() == original for path, original in packets.values())
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as conn:
        assert conn.execute("SELECT count(*) FROM actions WHERE state='done'").fetchone() == (3,)
        assert conn.execute("SELECT count(*) FROM actions WHERE json_extract(request,'$.kind')='observe' "
                            "AND json_extract(request,'$.payload.observation.actual')='unknown'").fetchone() == (3,)
