from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

from tools.feedback_loop.process_launch import BACKGROUND_CREATION_FLAGS


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


def configuration(tmp_path, *, owner=OWNER):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"state": "actions.sqlite", "owners": {
        owner: {"cwd": str(tmp_path), "observation_dir": "observations"}
    }}), encoding="utf-8")
    hosts = tmp_path / "hosts.json"
    hosts.write_text(json.dumps({owner: [*PYTHON, "-m", "tools.feedback_loop.local_host",
                                         "--config", str(settings), "rpc"]}), encoding="utf-8")
    command = [*PYTHON, "-m", "tools.feedback_loop.intake", "--settings", str(settings),
               "--hosts", str(hosts), "--wait-seconds", "0"]
    return command, hosts


@pytest.mark.parametrize("case", ["complete", "invalid-item", "interrupted", "replaced-marker", "positive-wait"])
def test_recovery_batches_exact_reconcile_requests_and_preserves_original_receipts(tmp_path, case):
    invalid_item = case == "invalid-item"
    command, _ = configuration(tmp_path)
    owner_script = tmp_path / "lookup.py"
    owner_script.write_text(
        """
import json
from pathlib import Path
import sys

request = json.load(sys.stdin)
requests = request if isinstance(request, list) else [request]
with Path("lookup-count.jsonl").open("a", encoding="utf-8") as stream:
    stream.write(json.dumps([sys.argv[1], len(requests)]) + "\\n")
if sys.argv[1] == "batch-replace":
    (Path("native") / ("feedback-" + "0" * 32 + ".ready")).write_text('{"owner": "other"}', encoding="utf-8")
results = []
for item in requests:
    assert item["method"] == "lookup" and item["kind"] == "reconcile"
    original = item["payload"]["observation"]["evidence_ref"]
    unknown = original == "example/unknown-usage"
    result = {
        "state": "done",
        "result": {
            "evidence_ref": original,
            "status": "cost_unknown" if unknown else "known",
            "job_status": "failed" if unknown else "succeeded",
            "cost_state": "unknown" if unknown else "not_applicable",
        },
    }
    if isinstance(request, list):
        result.update(action_id=item["action_id"], request_digest=item["request_digest"])
        if unknown and sys.argv[1] == "batch-bad":
            result["request_digest"] = "0" * 64
    results.append(result)
print(json.dumps(results if isinstance(request, list) else results[0]))
""",
        encoding="utf-8",
    )
    p = tmp_path / "settings.json"
    settings = json.loads(p.read_bytes())
    settings["owners"][OWNER].update(
        native_observation_dirs=["native"], timeout_seconds=10,
        actions={
            "reconcile": [*PYTHON, str(owner_script), "single"],
            "reconcile-batch": [*PYTHON, str(owner_script), {
                "invalid-item": "batch-bad", "replaced-marker": "batch-replace",
            }.get(case, "batch")],
        },
    )
    p.write_text(json.dumps(settings), encoding="utf-8")
    inbox = tmp_path / "native"
    inbox.mkdir()
    for index, reference in enumerate(("example/known-a", "example/unknown-usage", "example/known-b")):
        packet = inbox / f"feedback-{index:032x}.jsonl"
        packet.write_text(json.dumps({
            "schema_version": "feedback-observation/1", "owner": OWNER,
            "run_id": "original", "attempt_id": "first", "step_id": f"read/{index}",
            "check_id": "job-usage", "expected": "known", "actual": "unknown", "disposition": "unknown",
            "evidence_ref": reference,
        }) + "\n", encoding="utf-8")
        packet.with_suffix(".ready").write_text("{}", encoding="utf-8")
    originals = {packet.name: packet.read_bytes() for packet in inbox.glob("*.jsonl")}

    if case == "interrupted":
        abort = (
            "import os; from tools.feedback_loop.local_host import LocalHost; "
            "from tools.feedback_loop.intake import main; "
            "LocalHost.reconcile_batch = lambda *a, **kw: os._exit(86); main()"
        )
        outcome = subprocess.run(
            [*PYTHON, "-c", abort, *command[len(PYTHON) + 2:], "drain"], cwd=ROOT, timeout=20,
            stdin=subprocess.DEVNULL, capture_output=True, creationflags=BACKGROUND_CREATION_FLAGS,
        )
        assert outcome.returncode == 86
        assert len(list(inbox.glob("*.ready"))) == 3
        with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
            assert connection.execute("SELECT json_extract(request, '$.kind'), count(*) FROM actions GROUP BY 1").fetchall() == [
                ("observe", 3),
            ]

    if case == "positive-wait":
        command[-1] = "3"
    result = json.loads(subprocess.check_output(
        [*command, "drain"], cwd=ROOT, timeout=30, stdin=subprocess.DEVNULL, stderr=subprocess.PIPE,
        creationflags=BACKGROUND_CREATION_FLAGS,
    ))

    calls = [json.loads(line) for line in (tmp_path / "lookup-count.jsonl").read_text().splitlines()]
    assert calls == {
        "invalid-item": [["batch-bad", 3], ["single", 1]],
        "replaced-marker": [["batch-replace", 3]],
        "positive-wait": [["single", 1]] * 3,
    }.get(case, [["batch", 3]])
    replaced = case == "replaced-marker"
    assert result["processed"] == 3 and result["remaining"] == 1 + int(replaced) and result["woken"] == 0
    observation, = result["unsettled"][0]["observations"]
    assert (observation["step"], observation["job_status"], observation["cost_state"]) == ("reconcile", "failed", "unknown")
    assert {p.stem for p in inbox.glob("*.ready")} == {
        f"feedback-{i:032x}" for i in ([0, 1] if replaced else [1])
    }
    if replaced:
        assert result["diagnostics"] == [{"owner": OWNER, "code": "native_marker_changed"}]
    assert {packet.name: packet.read_bytes() for packet in inbox.glob("*.jsonl")} == originals
    if case == "positive-wait":
        assert "reconcile" not in result
    else:
        assert result["reconcile"][OWNER]["requests"] == 3
        assert result["reconcile"][OWNER]["batch_calls"] == 1
        assert result["reconcile"][OWNER]["fallback_calls"] == int(invalid_item)
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
        assert connection.execute("SELECT count(*) FROM actions").fetchone() == (3,)


@pytest.mark.parametrize(("field", "reason", "detail"), [
    (None, "reader_unavailable", "ParserError) at line 2, column 8"),
    ("read_only", "reader_unavailable", "roots[0] read_only must be a boolean, got str"),
    ("adapter_id", "reader_unavailable", "roots[0] adapter_id not registered"),
    ("kind", "invalid_request", "unsupported root kind"),
    ("priority", "invalid_request", "roots[0] priority must be convertible to an integer"),
    ("unknown", "reader_unavailable", "roots[0] unknown fields (1)"),
])
def test_cold_f4_can_recover_a_real_source_config_failure(tmp_path, field, reason, detail):
    owner = "company-wiki"
    secret = "generated-test-value-do-not-retain"
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config = config_dir / "catalog.yaml"
    if field is None:
        contents = f"schema_version: 1.0\nroots: ] # Authorization: Bearer {secret}\n"
    else:
        root = {"root_id": "company_raw", "path": "companies", "kind": "company_raw"}
        if field == "unknown":
            root[secret] = True
        else:
            root[field] = secret
        contents = json.dumps({"schema_version": "1.0", "catalog_dir": "catalog", "roots": [root]})
    config.write_text(contents, encoding="utf-8")
    state = tmp_path / "state"
    env = {key: value for key, value in os.environ.items() if not key.startswith("RESEARCH_FEEDBACK_")}
    env.update(LOCALAPPDATA=str(state), XDG_STATE_HOME=str(state), PYTHONPATH=str(ROOT / "src"),
               RESEARCH_FEEDBACK_RUN_ID="cwp-source-read", RESEARCH_FEEDBACK_ATTEMPT_ID="attempt-1")
    result = subprocess.run(
        [*PYTHON, "-m", "company_wiki.source_catalog.source_reader_cli", "--config", str(config),
         "--document-id", "fixture-document", "--source-id", "fixture-source", "--content-sha256", "0" * 64],
        cwd=tmp_path, env=env, capture_output=True, check=False, timeout=20,
    )
    assert secret.encode() not in result.stdout + result.stderr, "public failure exposed a sensitive input line"
    assert (result.returncode, result.stdout) == (2, b"")
    receipt = json.loads(result.stderr)
    assert receipt["reason"] == reason

    outbox = state / owner / "observations"
    packet, = outbox.glob("*.jsonl")
    for output in outbox.iterdir():
        assert secret.encode() not in output.read_bytes(), "durable failure exposed a sensitive input line"
    plan = [*PYTHON, "-E", "-S", "-m", "tools.feedback_loop", "plan", str(packet)]
    recovered = json.loads(subprocess.check_output(plan, cwd=ROOT, timeout=20))
    assert not recovered["diagnostics"]
    row, = recovered["observations"]
    assert (row["owner"], row["run_id"], row["attempt_id"], row["step_id"], row["actual"]) == (
        owner, "cwp-source-read", "attempt-1", "source-read", receipt["status"],
    )
    details = json.loads((outbox / row["details_ref"]).read_bytes())
    assert details["reason"] == reason
    assert details["package_version"]
    assert "version" not in row
    assert [details[key] for key in ("owner", "run_id", "attempt_id", "step_id")] == [
        row[key] for key in ("owner", "run_id", "attempt_id", "step_id")
    ]
    error, = details["exceptions"]
    assert error["type"] == ("CatalogConfigError" if reason == "reader_unavailable" else "ValueError")
    assert any(detail in message for message in error["messages"])
    assert any(frame[0] == "config.py" for frame in error["locations"])

    command, _ = configuration(tmp_path, owner=owner)
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"state": "actions.sqlite", "owners": {
        owner: {"cwd": str(tmp_path), "native_observation_dirs": [str(outbox)]},
    }}), encoding="utf-8")
    first, second = (json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT, env=env, timeout=20))
                     for _ in range(2))
    assert first == second
    assert not first["diagnostics"]
    assert first["processed"] == 1
    # The offline reader has no automatic triage route. The same observation
    # must remain attributable and no business command should be relaunched.
    assert first["unsettled"][0]["observations"][0]["occurrence_id"] == row["occurrence_id"]
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
        assert connection.execute("SELECT count(*) FROM actions").fetchone() == (1,)


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


@pytest.mark.parametrize("headless", [False, True])
def test_observed_owner_launch_preserves_the_callers_console_policy(tmp_path, monkeypatch, headless):
    from tools.feedback_loop import intake, process_launch

    _, hosts = configuration(tmp_path)
    calls = []

    def launch(argv, **options):
        calls.append((argv, options))
        return subprocess.CompletedProcess(argv, 19)

    monkeypatch.setattr(intake, "wake", lambda *args, **kwargs: None)
    flags = BACKGROUND_CREATION_FLAGS if headless else 0
    monkeypatch.setattr(process_launch, "inherit_console_creation_flags", lambda: flags)
    monkeypatch.setattr(intake.subprocess, "run", launch)

    assert intake.run_observed(tmp_path / "settings.json", hosts, OWNER, ["test-owner"], 0) == 19
    assert len(calls) == 1
    options = calls[0][1]
    assert options["creationflags"] == flags
    assert bool({"stdin", "stdout", "stderr"} & options.keys()) is bool(flags)


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
        history = _cold_process_history(command, original["run_id"])
        run, = history["processes"]
        assert run["status"] == "unconfirmed" and "exit_code" not in run
        assert all(run[key] == value for key, value in original.items())
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


def _cold_process_history(command, run_id):
    return json.loads(subprocess.check_output(
        [*command, "history", "--run-id", run_id, "--owner", OWNER], cwd=ROOT, timeout=20,
    ))


def test_success_without_owner_events_is_still_locatable_after_drain(tmp_path, monkeypatch):
    from tools.feedback_loop import intake

    command, hosts = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(intake, "wake", lambda *args, **kwargs: None)
    monkeypatch.setenv("RESEARCH_FEEDBACK_RUN_ID", "successful-process")
    monkeypatch.setenv("RESEARCH_FEEDBACK_ATTEMPT_ID", "original-attempt")
    private_argument = "fixture-secret-input-do-not-persist"
    child = "from pathlib import Path; p = Path('calls'); p.write_text(p.read_text()+'x' if p.exists() else 'x')"
    assert intake.run_observed(settings, hosts, OWNER, [*PYTHON, "-c", child, private_argument], 0) == 0
    drained = json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT, timeout=20))
    assert drained["processed"] == 0
    assert not drained["remaining"]
    first = _cold_process_history(command, "successful-process")
    assert first == _cold_process_history(command, "successful-process")
    assert first["status"] == "found"
    run, = first["processes"]
    assert (run["owner"], run["run_id"], run["attempt_id"], run["status"], run["exit_code"]) == (
        OWNER, "successful-process", "original-attempt", "exited", 0,
    )
    assert run["started_at"] <= run["finished_at"] and run["implementation"]
    assert private_argument not in json.dumps(first)
    assert (tmp_path / "calls").read_text() == "x"
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as db:
        assert db.execute("SELECT COUNT(*) FROM actions").fetchone() == (0,)


@pytest.mark.parametrize("history_blocked", [False, True])
def test_unavailable_inboxes_keep_the_original_identity_and_exit(tmp_path, monkeypatch, caplog, history_blocked):
    from tools.feedback_loop import intake

    command, hosts = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    (tmp_path / "observations").touch()
    (tmp_path / ".intake-recovery").touch()
    config = json.loads(settings.read_bytes())
    triage = "import json; print(json.dumps({'result': {'decision': 'needs_evidence'}}))"
    config["owners"][OWNER].update(timeout_seconds=10, actions={"triage": [*PYTHON, "-c", triage]})
    settings.write_text(json.dumps(config), encoding="utf-8")
    if history_blocked:
        (tmp_path / "actions.sqlite").mkdir()
    monkeypatch.setattr(intake, "wake", lambda *args, **kwargs: None)
    monkeypatch.setenv("RESEARCH_FEEDBACK_RUN_ID", "both-inboxes-down")
    monkeypatch.setenv("RESEARCH_FEEDBACK_ATTEMPT_ID", "original-attempt")
    child = """import os
from pathlib import Path
with Path('child-calls').open('a') as out:
    out.write(os.environ['RESEARCH_FEEDBACK_PROCESS_STEP_ID'] + '\\n')
raise SystemExit(19)
"""
    assert intake.run_observed(settings, hosts, OWNER, [*PYTHON, "-c", child], 0) == 19
    step, = (tmp_path / "child-calls").read_text().splitlines()
    assert step.startswith("intake/feedback-")
    assert all(value in caplog.text for value in ("both-inboxes-down", "original-attempt", step, "19"))
    result = _cold_process_history(command, "both-inboxes-down")
    if history_blocked:
        assert result["status"] == "unavailable"
    else:
        run, = result["processes"]
        assert (run["step_id"], run["exit_code"]) == (step, 19)
        # The real local host settles the offline triage in a separate process.
        drain = [*command[:-1], "10", "drain"]
        first, second = (json.loads(subprocess.check_output(drain, cwd=ROOT, timeout=20))
                         for _ in range(2))
        assert (first["processed"], second["processed"]) == (1, 0)
        with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as db:
            observations = [json.loads(row[0])["payload"]["observation"] for row in db.execute(
                "SELECT request FROM actions WHERE json_extract(request, '$.kind') = 'observe'",
            )]
        origin, = observations
        assert (origin["run_id"], origin["step_id"], origin["actual"]) == ("both-inboxes-down", step, "exit:19")


def test_process_history_can_check_absence_in_a_read_only_path(tmp_path):
    configuration(tmp_path)
    output = subprocess.check_output([
        *PYTHON, "-m", "tools.feedback_loop.intake", "--settings", str(tmp_path / "settings.json"),
        "history", "--run-id", "absent",
    ], cwd=ROOT, timeout=20)
    assert json.loads(output)["status"] == "absent"
    assert not (tmp_path / "actions.sqlite").exists()


def test_original_failure_stays_queued_until_a_consumer_sees_it(tmp_path, monkeypatch):
    from tools.feedback_loop import intake

    command, hosts = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    triage = "import json; print(json.dumps({'result': {'decision': 'needs_evidence'}}))"
    config["owners"][OWNER].update(timeout_seconds=10, actions={"triage": [*PYTHON, "-c", triage]})
    settings.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(intake, "wake", lambda *args, **kwargs: None)
    monkeypatch.setenv("RESEARCH_FEEDBACK_RUN_ID", "lost-published-inbox")
    assert intake.run_observed(settings, hosts, OWNER, [*PYTHON, "-c", "raise SystemExit(17)"], 0) == 17
    inbox = tmp_path / "observations"
    assert len(list(inbox.glob("*.ready"))) == 1
    moved = inbox.rename(tmp_path / "out-of-reach")
    drain = [*command[:-1], "10", "drain"]
    result = json.loads(subprocess.check_output(drain, cwd=ROOT, timeout=20))
    assert result["processed"] == 1 and not result["remaining"]
    moved.rename(inbox)
    subprocess.check_output(drain, cwd=ROOT, timeout=20)
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as db:
        rows = [json.loads(row[0])["payload"]["observation"] for row in db.execute(
            "SELECT request FROM actions WHERE json_extract(request, '$.kind') = 'observe'",
        )]
        assert db.execute("SELECT count(*) FROM intake_processes WHERE pending_observation IS NOT NULL").fetchone() == (0,)
    row, = rows
    assert (row["run_id"], row["actual"]) == ("lost-published-inbox", "exit:17")


def test_known_success_recovers_a_marker_whose_final_rename_failed(tmp_path, monkeypatch):
    from tools.feedback_loop import intake

    command, hosts = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    original_rename = Path.replace

    def block_ready(path, destination):
        if destination.suffix == ".ready":
            raise PermissionError("injected after process exit")
        return original_rename(path, destination)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", block_ready)
        patch.setattr(intake, "wake", lambda *args, **kwargs: None)
        assert intake.run_observed(settings, hosts, OWNER, [*PYTHON, "-c", "raise SystemExit(0)"], 0) == 0
    marker, = (tmp_path / "observations").glob("*.pending")
    context = json.loads(marker.read_bytes())
    result = json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT, timeout=20))
    assert not result["unconfirmed"] and result["remaining"] == 0
    assert not marker.exists()
    original, = _cold_process_history(command, context["run_id"])["processes"]
    assert (original["step_id"], original["exit_code"]) == (context["step_id"], 0)


@pytest.mark.parametrize("native_only", [False, True])
def test_success_keeps_a_file_recovery_record_when_the_history_database_is_unavailable(
    tmp_path, monkeypatch, native_only,
):
    from tools.feedback_loop import intake

    command, hosts = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    if native_only:
        config = json.loads(settings.read_bytes())
        route = config["owners"][OWNER]
        del route["observation_dir"]
        route["native_observation_dirs"] = ["native"]
        settings.write_text(json.dumps(config), encoding="utf-8")
    database = tmp_path / "actions.sqlite"
    database.mkdir()
    monkeypatch.setattr(intake, "wake", lambda *args, **kwargs: None)
    child = "from pathlib import Path; Path('called').touch()"
    assert intake.run_observed(settings, hosts, OWNER, [*PYTHON, "-c", child], 0) == 0
    inbox = tmp_path / (".intake-recovery" if native_only else "observations")
    marker, = inbox.glob("*.ready")
    context = json.loads(marker.read_bytes())
    assert (tmp_path / "called").is_file()

    database.rmdir()
    summary = json.loads(subprocess.check_output([*command, "drain"], cwd=ROOT, timeout=20))
    assert not summary["remaining"] and not marker.exists()
    assert summary["processed"] == 0 and not (tmp_path / "native").exists()
    recovered, = _cold_process_history(command, context["run_id"])["processes"]
    assert (recovered["step_id"], recovered["exit_code"]) == (context["step_id"], 0)


def test_process_history_uses_the_real_sqlite_path_with_uri_characters(tmp_path, monkeypatch):
    from tools.feedback_loop import intake

    command, hosts = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    config["state"] = "actions #1.sqlite"
    settings.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(intake, "wake", lambda *args, **kwargs: None)
    monkeypatch.setenv("RESEARCH_FEEDBACK_RUN_ID", "run-with-special-path")
    assert intake.run_observed(settings, hosts, OWNER, [*PYTHON, "-c", "raise SystemExit(0)"], 0) == 0
    assert _cold_process_history(command, "run-with-special-path")["status"] == "found"
    assert (tmp_path / config["state"]).is_file() and not (tmp_path / "actions ").exists()


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
    # The initial drain has a zero wait. Each later owner action runs in a
    # separate worker with its own deadline, including on a busy Windows host.
    route = config["owners"][OWNER]
    deadline = time.monotonic() + len(route["actions"]) * route["timeout_seconds"] + 10
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


@pytest.mark.parametrize(("different", "terminal_outcome"), (
    (None, "completed"), ("attempt_id", "completed"), ("evidence_ref", "completed"), (None, "failed"),
    ("packet_ref", "completed"), ("sibling", "completed"),
))
def test_cold_host_uses_recorded_terminal_from_a_separate_native_packet(tmp_path, different, terminal_outcome):
    _, registry = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    cfg = json.loads(settings.read_bytes())
    native = tmp_path / "native"
    native.mkdir()
    probe = tmp_path / "lookup.py"
    probe.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        "row = json.load(sys.stdin)['payload']['observation']\n"
        "with Path('lookups.txt').open('a', encoding='utf-8') as out:\n"
        "    out.write(row['check_id'] + '\\n')\n"
        "if row['check_id'] == 'job-usage':\n"
        "    print(json.dumps({'state':'done','result':{'status':'cost_unknown',"
        "'job_status':'succeeded','cost_state':'unknown','evidence_ref':row['evidence_ref']}}))\n"
        "else:\n"
        "    print(json.dumps({'state':'unknown'}))\n",
        encoding="utf-8",
    )
    cfg["owners"][OWNER].update(
        timeout_seconds=10, native_observation_dirs=["native"], actions={"reconcile": [*PYTHON, str(probe)]},
    )
    settings.write_text(json.dumps(cfg), encoding="utf8")
    recorded = dict(schema_version="feedback-observation/1", owner=OWNER, run_id="run", attempt_id="attempt",
                    step_id="phase", evidence_ref="fixture/1/original", disposition="expected")

    def publish(token, *rows):
        packet = native / ("feedback-" + token * 32 + ".jsonl")
        packet.write_text("".join(json.dumps({**recorded, **row}) + "\n" for row in rows), encoding="utf8")
        packet.with_suffix(".ready").write_text("{}", encoding="utf8")
        return packet

    def recover():
        args = [*PYTHON, "-m", "tools.feedback_loop.local_host", "--config", str(settings),
                "recover", "--hosts", str(registry)]
        return json.loads(subprocess.check_output(args, cwd=ROOT, timeout=20))

    failed = terminal_outcome == "failed"
    related = different == "sibling"
    mismatched = different in ("attempt_id", "evidence_ref", "packet_ref")
    terminal = dict(check_id="stage-outcome", expected="completed", actual=terminal_outcome,
                    disposition="deviation" if failed else "expected")
    opening = dict(check_id="action-started", terminal_check_id="stage-outcome", expected="started", actual="started")
    if mismatched:
        terminal["evidence_ref" if different == "packet_ref" else different] = "other"
    if different == "packet_ref":
        start = end = publish("b", opening, terminal)
    else:
        end = publish("a", terminal)
        assert recover()["remaining"] == int(failed)
        rows = [opening]
        if related:
            rows.insert(0, dict(check_id="input-admission", expected="valid", actual="refused",
                                 disposition="deviation", refusal_code="fixture_refusal"))
        start = publish("b", *rows)
    before = {packet: packet.read_bytes() for packet in {start, end}}
    recovery = recover()
    assert recovery["remaining"] == int(mismatched or failed or related)
    assert start.with_suffix(".ready").exists() == (mismatched or related)
    assert {packet: packet.read_bytes() for packet in before} == before
    calls = tmp_path / "lookups.txt"
    if mismatched:
        assert calls.read_text(encoding="utf-8") == "action-started\n"
        return
    assert not calls.exists()
    if failed or related:
        assert end.with_suffix(".ready").exists() == failed
        observed, = recovery["unsettled"][0]["observations"]
        assert (observed["step"], observed["code"]) == ("triage", "action_unconfigured")
        return
    assert recover()["processed"] == 0
    publish("c", dict(check_id="job-usage", expected="known", actual="unknown", disposition="unknown"))
    usage = recover()
    assert usage["remaining"] == 1 and usage["unsettled"][0]["observations"][0]["cost_state"] == "unknown"
    assert calls.read_text(encoding="utf-8") == "job-usage\n"


def test_cold_host_distinguishes_an_unconfigured_triage_from_an_unknown_action(tmp_path):
    _, registry = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    native = tmp_path / "observations"
    native.mkdir()
    packet = native / ("feedback-" + "a" * 32 + ".jsonl")
    row = {"schema_version": "feedback-observation/1", "owner": OWNER, "run_id": "run", "attempt_id": "one",
           "step_id": "source", "check_id": "outcome", "expected": "ok", "actual": "failed"}
    original = (json.dumps(row) + "\n").encode("utf8")
    packet.write_bytes(original)
    marker = packet.with_suffix(".ready")
    marker.write_text("{}", encoding="utf8")
    command = [*PYTHON, "-m", "tools.feedback_loop.local_host", "--config", str(settings),
               "recover", "--hosts", str(registry)]
    result = json.loads(subprocess.check_output(command, cwd=ROOT, timeout=20))
    blocked, = result["unsettled"][0]["observations"]
    assert (blocked["status"], blocked["step"], blocked["code"]) == ("unknown", "triage", "action_unconfigured")
    assert result["woken"] == 0 and marker.exists() and packet.read_bytes() == original
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as connection:
        assert connection.execute("SELECT json_extract(request, '$.kind') FROM actions").fetchall() == [("observe",)]


def test_recover_explicit_sidecar_uses_its_owner_registry(tmp_path):
    _, registry = configuration(tmp_path)
    registry = registry.rename(tmp_path / "explicit-hosts.json")
    packet = tmp_path / "original.jsonl"
    raw = json.dumps({"schema_version": "feedback-observation/1", "owner": OWNER,
                      "run_id": "original", "attempt_id": "one", "step_id": "saved",
                      "check_id": "result", "expected": "ok", "actual": "ok"}).encode("ascii") + b"\n"
    packet.write_bytes(raw)
    command = [*PYTHON, "-m", "tools.feedback_loop.local_host", "--config", str(tmp_path / "settings.json"),
               "recover", "--hosts", str(registry), "--sidecar", str(packet)]
    result = json.loads(subprocess.check_output(command, cwd=ROOT, timeout=20))["feedback"]
    observed, = result["observations"]
    assert observed["status"] == "expected" and not result["diagnostics"]
    assert packet.read_bytes() == raw


@pytest.mark.parametrize("flush_exit_code", [0, 13])
def test_cold_host_flushes_only_selected_owner_before_scanning_native_inbox(tmp_path, flush_exit_code, monkeypatch):
    _, registry = configuration(tmp_path)
    routes = json.loads(registry.read_bytes())
    routes[OWNER] = {"argv": routes[OWNER], "pass_env": ["TEST_F4_ROUTE"]}
    explicit = registry.rename(tmp_path / "explicit-owners.json")
    explicit.write_text(json.dumps(routes), encoding="utf8")
    monkeypatch.setenv("TEST_F4_ROUTE", "allowed")
    monkeypatch.setenv("TEST_F4_PRIVATE", "parent-only")
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    native = tmp_path / "native"
    native.mkdir()
    marker = native / ("feedback-" + "e" * 32 + ".ready")
    identity = dict(owner=OWNER, run_id="original", attempt_id="one", step_id="saved")
    row = dict(identity, schema_version="feedback-observation/1", check_id="refused",
               expected="legitimate_refusal", actual="legitimate_refusal", disposition="expected")
    pending = tmp_path / "pending-observation.json"
    pending.write_text(json.dumps(row) + "\n", encoding="utf8")
    script = tmp_path / "flush_observations.py"
    script.write_text(
        "from pathlib import Path\n"
        "import os, sys\n"
        "if os.getenv('TEST_F4_ROUTE') != 'allowed' or 'TEST_F4_PRIVATE' in os.environ: sys.exit(37)\n"
        "source, packet, count = map(Path, sys.argv[1:4])\n"
        "if source.is_file():\n"
        "    packet.write_bytes(source.read_bytes())\n"
        "    source.unlink()\n"
        "with count.open('a') as out:\n"
        "    out.write('flush\\n')\n"
        "raise SystemExit(int(sys.argv[4]))\n",
        encoding="utf8",
    )
    flush = [*PYTHON, str(script), str(pending), str(marker.with_suffix(".jsonl"))]
    config["owners"][OWNER].update(
        timeout_seconds=10, native_observation_dirs=["native"],
        actions={"flush-observations": [*flush, str(tmp_path / "selected.txt"), str(flush_exit_code)]},
    )
    config["owners"]["parallel-owner"] = {
        "cwd": str(tmp_path), "timeout_seconds": 10,
        "actions": {"flush-observations": [*flush, str(tmp_path / "parallel.txt"), "0"]},
    }
    settings.write_text(json.dumps(config), encoding="utf8")
    command = [*PYTHON, "-m", "tools.feedback_loop.local_host", "--config", str(settings),
               "recover", "--owner", OWNER, "--hosts", str(explicit)]
    results = [json.loads(subprocess.check_output(command, cwd=ROOT, timeout=25)) for _ in range(2)]
    assert [result["processed"] for result in results] == [1, 0]
    expected_diagnostics = [{"owner": OWNER, "code": "owner_observation_flush_failed",
                             "exit_code": flush_exit_code}] if flush_exit_code else []
    assert all(result["diagnostics"] == expected_diagnostics and not result["woken"] for result in results)
    assert (tmp_path / "selected.txt").read_text().splitlines() == ["flush", "flush"]
    assert not pending.exists() and not (tmp_path / "parallel.txt").exists()
    assert not (tmp_path / "business-count.txt").exists()


@pytest.mark.parametrize(("native_code", "expected_code"), [
    ("native_owner_conflict", "native_owner_conflict"),
    ("native_owner_unverified", "native_owner_unverified"),
    ("private directory is inaccessible", None),
    ("sk-" + "x" * 28, None),
    ("opaquevalue" * 3, None),
])
def test_cold_host_keeps_typed_owner_reason_in_unsettled_reconcile(tmp_path, native_code, expected_code):
    configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    native = tmp_path / "native"
    native.mkdir()
    packet = native / ("feedback-" + "d" * 32 + ".jsonl")
    observation = {
        "schema_version": "feedback-observation/1", "owner": OWNER, "run_id": "original",
        "attempt_id": "first", "step_id": "result", "check_id": "job-usage", "disposition": "unknown",
        "expected": "accounted", "actual": "unknown", "evidence_ref": "fixture-job/1/original/first",
    }
    packet.write_text(json.dumps(observation) + "\n", encoding="utf8")
    script = tmp_path / "lookup_original.py"
    script.write_text(
        "import json, sys\n"
        "assert json.load(sys.stdin)['method'] == 'lookup'\n"
        "print(json.dumps({'state':'unknown', 'code':sys.argv[1]}))\n",
        encoding="utf8",
    )
    config["owners"][OWNER].update(timeout_seconds=10, native_observation_dirs=["native"],
                                  actions={"reconcile": [*PYTHON, str(script), native_code]})
    settings.write_text(json.dumps(config), encoding="utf8")
    command = [*PYTHON, "-m", "tools.feedback_loop.local_host", "--config", str(settings),
               "recover", "--owner", OWNER, "--save-result"]
    result = json.loads(subprocess.check_output(command, cwd=ROOT, timeout=25))
    saved = json.loads(settings.with_name("last-native-recovery.json").read_bytes())
    assert result["unsettled"] == saved["unsettled"]
    (record,) = saved["unsettled"][0]["observations"]
    assert record["status"] == "unknown" and record["step"] == "reconcile"
    assert record.get("code") == expected_code
    assert not result["woken"] and result["remaining"] == 1


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


def test_exact_local_route_does_not_start_an_rpc_interpreter(tmp_path, monkeypatch):
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
    with monkeypatch.context() as patch:
        def external(*args, **kwargs):
            raise OSError("external transport called")
        patch.setattr(transport.subprocess, "run", external)
        assert call(OWNER, request)["state"] == "absent"
        assert call(OWNER, request | {"method": "submit"})["state"] == "done"
        assert call(OWNER, request)["state"] == "done"
        other = {OWNER: [*routes[OWNER][:-2], str(tmp_path / "another-config.json"), "rpc"]}
        with pytest.raises(OSError, match="external transport called"):
            transport.process_host(other, local=host)(OWNER, request)


def test_exact_local_route_preserves_the_worker_environment_boundary(tmp_path, monkeypatch):
    from tools.feedback_loop import host as transport
    from tools.feedback_loop.local_host import LocalHost
    from tools.feedback_loop.observations import digest

    _, registry = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    config["owners"][OWNER].update(timeout_seconds=15, actions={"triage": [*PYTHON, "-c", "pass"]})
    settings.write_text(json.dumps(config), encoding="utf8")
    routes = json.loads(registry.read_bytes())
    routes[OWNER] = {"argv": routes[OWNER], "pass_env": ["TEST_F4_ROUTE"]}
    monkeypatch.setenv("TEST_F4_ROUTE", "allowed")
    monkeypatch.setenv("TEST_F4_PRIVATE", "parent-only")
    launched = []

    def wake_only(argv, **options):
        launched.append({name: options["env"][name] for name in ("TEST_F4_ROUTE", "TEST_F4_PRIVATE")
                         if name in options["env"]})

    monkeypatch.setattr(transport.subprocess, "Popen", wake_only)
    call = transport.process_host(routes, local=LocalHost(settings))
    key = "8" * 64
    payload = {"occurrence_id": "original"}
    request = dict(schema_version="feedback-action/1", owner=OWNER, kind="triage", action_id=key,
                   method="submit", payload=payload, request_digest=digest([OWNER, "triage", key, payload]))
    assert call(OWNER, request)["state"] == "pending"
    assert call(OWNER, request | {"method": "lookup"})["state"] == "pending"
    assert call(OWNER, request)["state"] == "pending"
    environment, = launched
    assert environment["TEST_F4_ROUTE"] == "allowed"
    assert "TEST_F4_PRIVATE" not in environment

    # Crash after queue commit. Recovery uses the same declared names without
    # saving the former process's values or reading the unlisted parent env.
    monkeypatch.setenv("TEST_F4_ROUTE", "current-route-value")
    monkeypatch.setenv("TEST_F4_PRIVATE", "unlisted-parent-value")
    LocalHost(settings).recover()
    assert len(launched) == 2
    assert launched[-1]["TEST_F4_ROUTE"] == "current-route-value"
    assert "TEST_F4_PRIVATE" not in launched[-1]
    state = (tmp_path / "actions.sqlite").read_bytes()
    assert b"unlisted-parent-value" not in state and b"current-route-value" not in state


@pytest.mark.windows_native
@pytest.mark.skipif(sys.platform != "win32", reason="Windows GUI launcher")
def test_windows_recovery_reuses_same_host_and_runs_owner_reader_without_console(tmp_path, monkeypatch):
    from tools.feedback_loop import host as transport
    from tools.feedback_loop.local_host import LocalHost
    from tools.feedback_loop.observations import digest

    _, registry = configuration(tmp_path)
    settings = tmp_path / "settings.json"
    config = json.loads(settings.read_bytes())
    reader = ("import ctypes,json,os,sys; json.load(sys.stdin); "
              "result={'console':bool(ctypes.windll.kernel32.GetConsoleWindow()),"
              "'private':os.getenv('TEST_F4_PRIVATE'),'route':os.getenv('TEST_F4_ROUTE')}; "
              "print(json.dumps({'state':'done','result':result}))")
    config["owners"][OWNER].update(timeout_seconds=15, actions={"reconcile": [*PYTHON, "-c", reader]})
    settings.write_text(json.dumps(config), encoding="utf8")
    host = LocalHost(settings)
    routes = json.loads(registry.read_bytes())
    routes[OWNER] = {"argv": routes[OWNER], "pass_env": ["TEST_F4_ROUTE"]}
    registry.write_text(json.dumps(routes), encoding="utf8")
    route = routes[OWNER]["argv"]
    windows_gui = Path(route[0]).with_name("pythonw.exe")
    if not windows_gui.is_file() or Path(route[0]).name.lower() != "python.exe":
        pytest.skip("matching python.exe and pythonw.exe are required")
    monkeypatch.setattr(transport.sys, "executable", str(windows_gui))
    monkeypatch.setenv("TEST_F4_PRIVATE", "parent-only")
    monkeypatch.setenv("TEST_F4_ROUTE", "allowed")
    original_run = subprocess.run
    launches = []

    def count(argv, **options):
        launches.append((argv, options.get("creationflags", 0)))
        return original_run(argv, **options)

    monkeypatch.setattr(subprocess, "run", count)
    call = transport.process_host(routes, local=host)

    def lookup(kind):
        key = digest([kind, OWNER, "original"])
        body = {"occurrence_id": "original"}
        return dict(schema_version="feedback-action/1", owner=OWNER, kind=kind, action_id=key,
                    method="lookup", payload=body, request_digest=digest([OWNER, kind, key, body]))

    assert call(OWNER, lookup("observe"))["state"] == "absent"
    result = call(OWNER, lookup("reconcile"))
    assert result["result"] == {"console": False, "private": None, "route": "allowed"}
    assert len(launches) == 1 and launches[0][0][-1] == reader
    assert launches[0][1] & subprocess.CREATE_NO_WINDOW
    standalone = subprocess.run(
        [*PYTHON, "-m", "tools.feedback_loop.local_host", "--config", str(settings), "rpc"],
        input=json.dumps(lookup("reconcile")).encode("ascii"), capture_output=True, cwd=ROOT,
        check=True, timeout=20,
    )
    assert json.loads(standalone.stdout)["result"] == result["result"]


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
    queued._wake = lambda _key, **_options: False
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
    waiting = {item["packet_id"]: item["observations"] for item in first["unsettled"]}
    unconfirmed, = waiting[packets["unconfirmed"][0].stem]
    absent, = waiting[packets["absent"][0].stem]
    assert unconfirmed == {
        "occurrence_id": unconfirmed["occurrence_id"], "status": "unknown", "step": "reconcile",
        "job_status": "unconfirmed", "cost_state": "unknown",
    }
    assert absent == {"occurrence_id": absent["occurrence_id"], "status": "unknown", "step": "reconcile"}
    assert len(unconfirmed["occurrence_id"]) == len(absent["occurrence_id"]) == 64
    assert packets["failed"][0].stem not in waiting
    assert packets["failed"][0].with_suffix(".ack").is_file()
    assert all(packets[key][0].with_suffix(".ready").is_file() for key in ("unconfirmed", "absent"))
    second = cold()
    assert (second["processed"], second["remaining"]) == (2, 2)
    assert second["unsettled"] == first["unsettled"]
    assert all(path.read_bytes() == original for path, original in packets.values())
    with closing(sqlite3.connect(tmp_path / "actions.sqlite")) as conn:
        assert conn.execute("SELECT count(*) FROM actions WHERE state='done'").fetchone() == (3,)
        assert conn.execute("SELECT count(*) FROM actions WHERE json_extract(request,'$.kind')='observe' "
                            "AND json_extract(request,'$.payload.observation.actual')='unknown'").fetchone() == (3,)
