from hashlib import sha256
import json
from contextlib import closing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from tools.feedback_loop.observations import IDENTITY, digest


ROOT = Path(__file__).resolve().parents[2]
HOST = [sys.executable, "-B", "-m", "tools.feedback_loop.local_host"]


@pytest.mark.parametrize(("body", "code", "expected"), [
    ('raise ImportError("api_key=synthetic-startup-value")\n', 1, "ImportError"),
    ("import os, sys\nprint('forced-stop authorization: Bearer synthetic-startup-value',"
     "file=sys.stderr, flush=True)\nos._exit(23)\n", 23, "forced-stop"),
    ("import os, sys\nsys.stderr.write('Authorization: Ba')\n"
     "sys.stderr.write('sic\\r\\n')\n"
     "print('synthetic-startup-value', file=sys.stderr, flush=True)\n"
     "print('\\tsynthetic-startup-value-second-fold', file=sys.stderr, flush=True)\n"
     "print('failure after folded header', file=sys.stderr, flush=True)\nos._exit(23)\n",
     23, "failure after folded header"),
    ("import os, sys\nprint('validation mode basic', file=sys.stderr)\n"
     "print('Authorization: synthetic-startup-value', file=sys.stderr)\n"
     "print('PermissionError: cause survived', file=sys.stderr)\nos._exit(23)\n",
     23, "PermissionError: cause survived"),
])
def test_detached_background_keeps_diagnostics_before_target_main(tmp_path, monkeypatch, body, code, expected):
    from tools.feedback_loop import hook

    checkout = tmp_path / "checkout"
    package = checkout / "tools/feedback_loop"
    shutil.copytree(ROOT / "tools/feedback_loop", package, ignore=shutil.ignore_patterns("__pycache__"))
    (package / "coordinator.py").write_text(body, encoding="utf-8")
    monkeypatch.setattr(hook, "__file__", str(package / "hook.py"))
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    receipt = tmp_path / "wake.json"
    started = []
    popen = subprocess.Popen

    def launch(*args, **kwargs):
        child = popen(*args, **kwargs)
        started.append(child)
        return child

    monkeypatch.setattr(hook.subprocess, "Popen", launch)
    assert hook.wake(tmp_path / "input.jsonl", str(tmp_path / "config.json"), receipt)["status"] == "scheduled"
    child, = started
    try:
        assert child.wait(timeout=20) == code
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
    text = receipt.with_suffix(".stderr.log").read_text(encoding="utf-8")
    assert expected in text and "synthetic-startup-value" not in text
    assert receipt.read_bytes() == b""


def test_background_argparse_error_is_saved_without_changing_exit_code(tmp_path):
    destination = tmp_path / "host.log"
    completed = subprocess.run(
        [*HOST, "--config", str(tmp_path / "settings.json"), "not-a-command"],
        cwd=ROOT, env={**os.environ, "CWP_F4_ERROR_LOG": str(destination)},
        capture_output=True, timeout=20, check=False,
    )
    assert (completed.returncode, completed.stdout) == (2, b"")
    assert "invalid choice" in destination.read_text(encoding="utf-8")


def test_two_processes_keep_both_diagnostics_while_rotating(tmp_path):
    directory = tmp_path / "logs"
    directory.mkdir()
    active = directory / "host_subprocess_failures.log"
    previous = b"retained prior diagnostics\n" + b"x" * (2 * 1024 * 1024)
    active.write_bytes(previous)
    body = (
        "from pathlib import Path; import sys; "
        "from tools.feedback_loop.local_host import _persist_host_stderr; "
        "_persist_host_stderr(Path(sys.argv[1]), 'action', 1, sys.argv[2].encode())"
    )

    def write(label):
        return subprocess.run(
            [sys.executable, "-B", "-c", body, str(tmp_path / "settings.json"), label],
            cwd=ROOT, capture_output=True, timeout=20, check=True,
        )

    with ThreadPoolExecutor(2) as pool:
        assert all(result.stdout == b"" for result in pool.map(write, ("writer-one", "writer-two")))
    assert active.with_suffix(".log.1").read_bytes() == previous
    current = active.read_text(encoding="utf-8")
    assert "writer-one" in current and "writer-two" in current


def action(kind="triage", owner="company-wiki", payload=None):
    payload = {"observation": {"expected": "present", "actual": "absent"}} if payload is None else payload
    key = digest([owner, kind, "original"])
    return {"schema_version": "feedback-action/1", "method": "submit", "action_id": key,
            "owner": owner, "kind": kind, "payload": payload,
            "request_digest": digest([owner, kind, key, payload])}


def invoke(config, mode, request=None):
    result = subprocess.run([*HOST, "--config", str(config), mode], cwd=ROOT,
                            input=json.dumps(request).encode("ascii"), capture_output=True, timeout=15, check=True)
    return json.loads(result.stdout)


def wait_for(predicate):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if value := predicate():
            return value
        time.sleep(0.05)
    pytest.fail("host did not reach the requested state")


@pytest.fixture
def host_config(tmp_path):
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import json, sys, time\nfrom pathlib import Path\n"
        "with Path('starts').open('a') as stream: stream.write('start\\n')\n"
        "request = json.load(sys.stdin)\n"
        "while not Path('release').exists(): time.sleep(0.02)\n"
        "print(json.dumps({'result': {'decision': 'expected'}, 'native': {'session_id': 'test-thread'}, "
        "'request_digest': 'bad', 'state': 'absent'}))\n",
        encoding="utf-8",
    )
    status = tmp_path / "ff.py"
    status.write_text(
        "import json, sys\nfrom pathlib import Path\n"
        "with Path(sys.argv[1]).open('a', encoding='utf-8') as stream: stream.write(' '.join(sys.argv[2:]) + '\\n')\n"
        "print(Path(sys.argv[2] + '.json').read_text())\n",
        encoding="utf-8",
    )
    config = tmp_path / "host.json"
    config.write_text(json.dumps({"state": "actions.sqlite", "owners": {"company-wiki": {
        "cwd": str(tmp_path), "timeout_seconds": 12, "actions": {"triage": [sys.executable, "-B", str(worker)]}},
        "filing-fetch": {"cwd": str(tmp_path), "ff_status_argv": [sys.executable, "-B", str(status), "ff-calls"]},
    }}), encoding="utf-8")
    return config


def test_missing_observation_fields_in_an_old_result_do_not_close_the_start(host_config):
    owner = "company-wiki"
    stage = {"schema_version": "feedback-observation/1", "owner": owner, "origin_owner": owner,
             "run_id": "original", "attempt_id": "first", "step_id": "read", "evidence_ref": "source/original"}

    def bind(row):
        occurrence = digest([row[field] for field in IDENTITY])
        payload = {"occurrence_id": occurrence, "observation": row}
        submitted = action("observe", owner, payload)
        key = digest(["observe", owner, occurrence])
        submitted.update(action_id=key, request_digest=digest([owner, "observe", key, payload]))
        return invoke(host_config, "rpc", submitted)

    assert bind({**stage, "check_id": "outcome", "actual": "succeeded"})["state"] == "done"
    start = {**stage, "check_id": "action-started", "terminal_check_id": "outcome",
             "expected": "started", "actual": "started", "disposition": "expected"}
    assert bind(start)["result"] == {"recorded": True}


def test_concurrent_submit_discarded_reply_and_recovery(host_config):
    root = host_config.parent
    req = action()
    look = {**req, "method": "lookup"}
    assert invoke(host_config, "rpc", look)["state"] == "absent"
    with ThreadPoolExecutor(2) as pool:
        assert all(r["state"] == "pending" for r in pool.map(lambda _: invoke(host_config, "rpc", req), range(2)))
    wait_for(lambda: (root / "starts").exists())
    # An independent caller resumes from the original action, without using either submit reply.
    invoke(host_config, "recover")
    assert invoke(host_config, "rpc", look)["state"] == "pending"
    (root / "release").touch()
    done = wait_for(lambda: reply if (reply := invoke(host_config, "rpc", look))["state"] == "done" else None)
    assert done["result"] == {"decision": "expected"}
    assert done["native"] == {"session_id": "test-thread"}
    assert done["request_digest"] == req["request_digest"]
    assert invoke(host_config, "rpc", req) == done
    assert (root / "starts").read_text().splitlines() == ["start"]
    changed = {"observation": {"expected": "different"}}
    collision = {**req, "payload": changed,
                 "request_digest": digest([req["owner"], req["kind"], req["action_id"], changed])}
    assert invoke(host_config, "rpc", collision)["code"] == "action_conflict"


def test_restart_wakes_only_prelaunch_action(tmp_path, host_config, monkeypatch):
    from tools.feedback_loop.local_host import LocalHost

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("lost wake")))
    request = action()
    assert LocalHost(host_config).handle(request)["state"] == "pending"
    assert not (tmp_path / "starts").exists()
    monkeypatch.undo()
    (tmp_path / "release").touch()
    invoke(host_config, "recover")
    wait_for(lambda: invoke(host_config, "rpc", {**request, "method": "lookup"})["state"] == "done")
    assert (tmp_path / "starts").read_text().splitlines() == ["start"]


def _fake_codex_start(monkeypatch):
    starts = []

    def native(argv, **options):
        assert argv == [sys.executable, "exec", "--json", "-"]
        starts.append(argv)
        events = [
            {"type": "thread.started", "thread_id": "original"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": '{"decision":"expected"}'}},
            {"type": "turn.completed", "usage": {}},
        ]
        for event in events:
            options["stdout"].write(json.dumps(event).encode("ascii") + b"\n")
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", native)
    return starts


@pytest.mark.parametrize("installed", [True, False])
def test_codex_launch_resolves_the_current_install_before_starting(host_config, monkeypatch, installed):
    from tools.feedback_loop import codex_cli
    from tools.feedback_loop.local_host import LocalHost

    config = json.loads(host_config.read_bytes())
    config["owners"]["company-wiki"]["actions"]["triage"] = {
        "mode": "codex-jsonl", "argv": ["codex", "exec", "--json", "-"],
    }
    host_config.write_text(json.dumps(config), encoding="utf-8")
    executable = Path(sys.executable) if installed else None
    monkeypatch.setattr(codex_cli, "resolve_codex", lambda: executable)
    starts = _fake_codex_start(monkeypatch)
    host = LocalHost(host_config)
    monkeypatch.setattr(host, "_wake", lambda _key, **_options: True)
    request = action()
    assert host.handle(request)["state"] == "pending"
    host.work(request["action_id"])
    lookup = {**request, "method": "lookup"}
    if not installed:
        pending = host.handle(lookup)
        assert (pending["state"], pending["code"]) == ("pending", "codex_executable_unavailable")
        assert not starts and not host._native_path(request["action_id"]).exists()
        executable = Path(sys.executable)
        assert host.recover(owners={"company-wiki"}) == [request["action_id"]]
        host.work(request["action_id"])
    result = host.handle(lookup)
    assert result["state"] == "done" and result["native"]["session_id"] == "original"
    assert result["request_digest"] == request["request_digest"]
    host.work(request["action_id"])
    assert len(starts) == 1


@pytest.mark.parametrize(("case", "identity_field"), [
    ("native", None), ("same-copies", None), ("missing", None), ("outside", None),
    ("malformed", None), ("conflict", None), ("other-owner-inbox", None),
    ("different-identity", "owner"), ("different-identity", "run_id"),
    ("different-identity", "attempt_id"), ("different-identity", "step_id"),
    ("different-original", "actual"), ("different-original", "expected"), ("different-original", "check_id"),
    ("missing-packet", None), ("link", None), ("packet-link", None), ("repair", None),
])
def test_codex_triage_includes_only_bound_native_diagnostic_facts(
    host_config, monkeypatch, case, identity_field,
):
    from tools.feedback_loop.local_host import LocalHost

    root = host_config.parent
    agent_root, intake, inbox, other_inbox = (root / name for name in
                                             ("agent", "intake", "owner-inbox", "other-inbox"))
    for directory in (agent_root, intake, inbox, other_inbox):
        directory.mkdir()
    native = "feedback-" + "a" * 32 + ".diagnostic.json"
    secret = "sk-EXAMPLE-DO-NOT-SEND"
    opaque_label = "SyntheticOwnerSecret123"
    arbitrary_number = 987654321012345
    identity = {"owner": "company-wiki", "run_id": "saved-run", "attempt_id": "one", "step_id": "worker"}
    observation = identity | {
        "owner": "check-owner", "origin_owner": "company-wiki", "details_ref": native,
        "schema_version": "feedback-observation/1", "check_id": "operation-outcome",
        "expected": "completed", "actual": "failed", "disposition": "deviation",
    }
    diagnostic = identity | {
        "message": str(root / secret),
        "exceptions": [
            {"type": "FileNotFoundError", "errno": 2, "locations": [[str(root / secret), secret, 6]]},
            {"type": "OSError", "errno": arbitrary_number},
            {"type": "KeyError", "errno": True, "messages": [secret]},
            {"type": "sqlite3.OperationalError"},
            {"type": "JSONDecodeError", "messages": [secret]},
            {"type": "CatalogConfigError"},
            {"type": opaque_label},
            {"type": secret, "errno": 5},
            {"type": "ghp_exampleCredentialError"},
        ],
    }
    raw = json.dumps(diagnostic).encode("utf-8")
    packet = native.removesuffix(".diagnostic.json") + ".jsonl"
    original_row = (json.dumps(observation) + "\n").encode("utf-8")

    def publish(folder, detail_bytes=raw):
        (folder / native).write_bytes(detail_bytes)
        (folder / packet).write_bytes(original_row)

    if case in ("native", "same-copies"):
        publish(inbox)
        if case == "same-copies":
            publish(intake)
    elif case in ("outside", "link", "packet-link"):
        publish(root)
        if case == "outside":
            observation = observation | {"details_ref": "../" + native}
        else:
            link, regular = (packet, native) if case == "packet-link" else (native, packet)
            (inbox / regular).write_bytes((root / regular).read_bytes())
            try:
                (inbox / link).symlink_to(root / link)
            except OSError as exc:
                pytest.skip(f"symbolic links unavailable on this host ({type(exc).__name__})")
    elif case == "malformed":
        publish(inbox, b'{"owner":"duplicated",' + raw[1:])
    elif case == "conflict":
        publish(inbox)
        publish(intake, json.dumps(diagnostic | {"message": "second copy"}).encode())
    elif case == "other-owner-inbox":
        publish(other_inbox)
    elif case == "different-identity":
        publish(inbox, json.dumps(diagnostic | {identity_field: "unrelated"}).encode())
    elif case == "different-original":
        publish(inbox)
        observation = observation | {identity_field: "other-outcome"}
    elif case == "missing-packet":
        (inbox / native).write_bytes(raw)
    elif case == "repair":
        publish(inbox)

    events = [{"type": "thread.started", "thread_id": "same-attempt"},
              {"type": "item.completed", "item": {"type": "agent_message", "text": '{"decision":"expected"}'}},
              {"type": "turn.completed", "usage": {}}]
    agent = agent_root / "codex-fixture.py"
    agent.write_text(
        "import json, sys\n"
        "def audit(event, args):\n"
        "    if event == 'open' and args[0] != 'captured.jsonl': raise PermissionError(event)\n"
        "sys.addaudithook(audit)\n"
        "with open('captured.jsonl', 'a', encoding='utf-8') as out:\n"
        "    out.write(json.dumps(sys.stdin.read()) + '\\n')\n"
        f"print({''.join(json.dumps(event) + chr(10) for event in events)!r}, end='')\n",
        encoding="utf-8",
    )
    config = json.loads(host_config.read_bytes())
    kind = "repair" if case == "repair" else "triage"
    config["owners"]["company-wiki"].update(observation_dir="intake", native_observation_dirs=["owner-inbox"])
    config["owners"]["triage-owner"] = {
        "cwd": str(agent_root), "observation_dir": "other-inbox", "timeout_seconds": 10,
        "actions": {kind: {"mode": "codex-jsonl", "argv": [sys.executable, "-B", str(agent)]}},
    }
    host_config.write_text(json.dumps(config), encoding="utf-8")
    request = action(kind, owner="triage-owner", payload={"observation": observation})
    host = LocalHost(host_config)
    monkeypatch.setattr(host, "_wake", lambda _key, **_options: True)
    assert host.handle(request)["state"] == "pending"
    host.work(request["action_id"])
    resumed = LocalHost(host_config)
    result = resumed.handle(request | {"method": "lookup"})
    assert result["state"] == "done"
    assert result["action_id"] == request["action_id"]
    assert result["request_digest"] == request["request_digest"]
    assert resumed.handle(request) == result
    resumed.work(request["action_id"])

    line, = (agent_root / "captured.jsonl").read_text(encoding="utf-8").splitlines()
    prompt, action_json = json.loads(line).rsplit("\n", 1)
    assert json.loads(action_json) == request
    assert all(value not in prompt for value in (secret, opaque_label, str(root), str(arbitrary_number)))
    if case == "repair":
        assert "Native diagnostic facts:" not in prompt
        return
    facts, = [json.loads(line.removeprefix("Native diagnostic facts: "))
              for line in prompt.splitlines() if line.startswith("Native diagnostic facts: ")]
    if case in ("native", "same-copies"):
        assert facts == {"status": "available", "sha256": sha256(raw).hexdigest(),
                         "exceptions": [{"type": "FileNotFoundError", "errno": 2},
                                        {"type": "OSError"}, {"type": "KeyError"},
                                        {"type": "OperationalError"}, {"type": "JSONDecodeError"},
                                        {"type": "CatalogConfigError"}, {"type": "OwnerException"}]}
    else:
        assert facts == {"status": "unavailable"}


def _legacy_codex_failure(host_config, monkeypatch, *, state="failed", code="host_command_or_directory_unavailable"):
    from tools.feedback_loop.local_host import LocalHost

    config = json.loads(host_config.read_bytes())
    config["owners"]["company-wiki"]["actions"]["triage"] = {
        "mode": "codex-jsonl", "argv": ["codex", "exec", "--json", "-"],
    }
    host_config.write_text(json.dumps(config), encoding="utf-8")
    host = LocalHost(host_config)
    wakes = []
    monkeypatch.setattr(host, "_wake", lambda key, **_options: wakes.append(key) or True)
    request = action()
    assert host.handle(request)["state"] == "pending"
    key = request["action_id"]
    with closing(host._connect()) as conn, conn:
        conn.execute("UPDATE actions SET state=?,receipt=?,deadline=? WHERE action_id=?",
                     (state, json.dumps({"code": code}), time.time(), key))
    wakes.clear()
    return host, request, wakes


def test_explicit_prelaunch_retry_claims_the_same_action_once_under_concurrency(host_config, monkeypatch):
    from tools.feedback_loop import codex_cli

    host, request, wakes = _legacy_codex_failure(host_config, monkeypatch)
    key = request["action_id"]
    frozen = host._get(key)
    monkeypatch.setattr(codex_cli, "resolve_codex", lambda: Path(sys.executable))
    with ThreadPoolExecutor(4) as pool:
        replies = list(pool.map(lambda _: host.retry_unstarted(key), range(4)))
    assert wakes == [key]
    assert all(result["state"] == "pending" for result in replies)
    row = host._get(key)
    assert row["state"] == "queued"
    assert all(row[field] == frozen[field] for field in ("action_id", "request_digest", "request", "route", "workspace"))
    assert "host_command_or_directory_unavailable" in (
        host_config.parent / "logs" / "host_subprocess_failures.log"
    ).read_text(encoding="utf-8")
    starts = _fake_codex_start(monkeypatch)
    host.work(key)
    assert host.retry_unstarted(key)["state"] == "done"
    assert host.handle(request)["native"]["session_id"] == "original"
    assert len(starts) == 1 and wakes == [key]


@pytest.mark.parametrize(("state", "code", "capture"), [
    ("failed", "host_command_or_directory_unavailable", b""),
    ("failed", "host_command_or_directory_unavailable", b'{"type":"thread.started","thread_id":"original"}\n'),
    ("running", "host_command_or_directory_unavailable", None),
    ("unknown", "host_command_or_directory_unavailable", None),
    ("failed", "native_outcome_unconfirmed", None),
])
def test_explicit_prelaunch_retry_never_requeues_started_or_unproved_work(host_config, monkeypatch, state, code, capture):
    from tools.feedback_loop import codex_cli

    host, request, wakes = _legacy_codex_failure(host_config, monkeypatch, state=state, code=code)
    key = request["action_id"]
    path = host._native_path(key)
    if capture is not None:
        path.write_bytes(capture)
    before = tuple(host._get(key))
    monkeypatch.setattr(codex_cli, "resolve_codex", lambda: pytest.fail("ineligible retry tried to resolve launcher"))
    assert host.retry_unstarted(key)["state"] == state
    assert tuple(host._get(key)) == before and wakes == []
    assert (path.read_bytes() if path.exists() else None) == capture


def test_explicit_prelaunch_retry_rejects_malformed_id_without_creating_state(host_config):
    process = subprocess.run(
        [*HOST, "--config", str(host_config), "retry-unstarted", "../bad-id"],
        cwd=ROOT, capture_output=True, timeout=10, check=False,
    )
    assert process.returncode == 2 and b"invalid action ID" in process.stderr
    assert not (host_config.parent / "actions.sqlite").exists()


def test_explicit_prelaunch_retry_rechecks_capture_after_discovering_the_launcher(host_config, monkeypatch):
    from tools.feedback_loop import codex_cli

    host, request, wakes = _legacy_codex_failure(host_config, monkeypatch)
    key = request["action_id"]
    path = host._native_path(key)
    before = tuple(host._get(key))

    def launcher():
        path.touch()
        return Path(sys.executable)

    monkeypatch.setattr(codex_cli, "resolve_codex", launcher)
    assert host.retry_unstarted(key)["state"] == "failed"
    assert tuple(host._get(key)) == before and wakes == [] and path.is_file()


@pytest.mark.parametrize("changed", ["workspace", "argv", "digest"])
def test_explicit_prelaunch_retry_preserves_frozen_request_and_current_route(host_config, monkeypatch, changed):
    from tools.feedback_loop import codex_cli

    host, request, wakes = _legacy_codex_failure(host_config, monkeypatch)
    key = request["action_id"]
    if changed == "workspace":
        other = host_config.parent / "other"
        other.mkdir()
        host.owners["company-wiki"]["cwd"] = str(other)
    elif changed == "argv":
        host.owners["company-wiki"]["actions"]["triage"]["argv"].insert(2, "--model=new-default")
    else:
        with closing(host._connect()) as conn, conn:
            conn.execute("UPDATE actions SET request_digest=? WHERE action_id=?", ("0" * 64, key))
    before = tuple(host._get(key))
    monkeypatch.setattr(codex_cli, "resolve_codex", lambda: pytest.fail("retry crossed its original scope"))
    assert host.retry_unstarted(key)["state"] == "failed"
    assert tuple(host._get(key)) == before and wakes == []


@pytest.mark.parametrize("mode", ["owner-json", "codex-jsonl"])
def test_worker_exits_before_native_runner_can_claim_and_restart_uses_original_action(host_config, monkeypatch, mode):
    from tools.feedback_loop.local_host import LocalHost

    root = host_config.parent
    if mode == "codex-jsonl":
        worker = root / "native.py"
        events = [
            {"type": "thread.started", "thread_id": "native-after-restart"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": '{"decision":"expected"}'}},
            {"type": "turn.completed", "usage": {}},
        ]
        worker.write_text(
            "from pathlib import Path\n"
            "with Path('starts').open('a') as stream: stream.write('start\\n')\n"
            f"print({''.join(json.dumps(event) + chr(10) for event in events)!r}, end='')\n",
            encoding="utf-8",
        )
        settings = json.loads(host_config.read_bytes())
        settings["owners"]["company-wiki"]["actions"]["triage"] = {
            "mode": mode, "argv": [sys.executable, str(worker)],
        }
        host_config.write_text(json.dumps(settings), encoding="utf-8")

    request = action()
    host = LocalHost(host_config)
    monkeypatch.setattr(host, "_wake", lambda _key, **_options: True)
    assert host.handle(request)["state"] == "pending"

    # Force the real outer process to exit before it invokes the native route.
    code = (
        "import os, sys\n"
        "from pathlib import Path\n"
        "from tools.feedback_loop.local_host import LocalHost\n"
        "host = LocalHost(Path(sys.argv[1]))\n"
        "host._execute = lambda *args: os._exit(17)\n"
        "host.work(sys.argv[2])\n"
    )
    stopped = subprocess.run([sys.executable, "-B", "-c", code, str(host_config), request["action_id"]],
                             cwd=ROOT, check=False, timeout=12)
    assert stopped.returncode == 17
    assert not (root / "starts").exists()

    (root / "release").touch()
    with ThreadPoolExecutor(2) as pool:
        recoveries = list(pool.map(lambda _: invoke(host_config, "recover")["woken"], range(2)))
    assert [request["action_id"]] in recoveries
    assert all(keys in ([], [request["action_id"]]) for keys in recoveries)
    lookup = {**request, "method": "lookup"}
    done = wait_for(lambda: reply if (reply := invoke(host_config, "rpc", lookup))["state"] == "done" else None)
    assert done["action_id"] == request["action_id"] and done["result"] == {"decision": "expected"}
    assert invoke(host_config, "recover")["woken"] == []
    assert invoke(host_config, "rpc", request) == done
    assert (root / "starts").read_text().splitlines() == ["start"]


def test_failed_owner_launcher_keeps_a_recoverable_action_and_diagnostic(host_config, monkeypatch):
    from tools.feedback_loop.local_host import LocalHost

    root = host_config.parent
    host = LocalHost(host_config)
    request = action()
    lookup = {**request, "method": "lookup"}
    monkeypatch.setattr(host, "_wake", lambda _key, **_options: True)
    assert host.handle(request)["state"] == "pending"

    def launcher_unavailable(*args, **kwargs):
        raise OSError("simulated owner runner startup failure")

    with monkeypatch.context() as failure:
        failure.setattr(subprocess, "run", launcher_unavailable)
        host.work(request["action_id"])

    pending = host.handle(lookup)
    assert pending["state"] == "pending" and pending["code"] == "owner_launcher_failed"
    assert not (root / "starts").exists()
    (root / "release").touch()
    assert invoke(host_config, "recover")["woken"] == [request["action_id"]]
    done = wait_for(lambda: reply if (reply := invoke(host_config, "rpc", lookup))["state"] == "done" else None)
    assert "code" not in done and (root / "starts").read_text().splitlines() == ["start"]


def test_ff_reconcile_checks_the_same_job_and_never_submits(host_config):
    root = host_config.parent
    ref = "ff-job/1/ffjob-123abc123abc"
    req = action("reconcile", "filing-fetch", {"observation": {"evidence_ref": ref}})
    lookup = {**req, "method": "lookup"}
    view = {"schema_version": "ff-job/1", "command": "get_status", "status": "ok", "owner_job_id": "ffjob-123abc123abc",
            "job": {"owner": "filing-fetch", "owner_job_id": "ffjob-123abc123abc", "status_known": True,
                    "status": "succeeded", "cost_state": "unknown"}}
    receipt = root / "get_status.json"
    receipt.write_text(json.dumps(view), encoding="utf-8")
    assert invoke(host_config, "rpc", req)["state"] == "failed"
    assert not (root / "ff-calls").exists()
    assert invoke(host_config, "rpc", lookup)["result"] == {
        "status": "cost_unknown", "evidence_ref": ref, "job_status": "succeeded", "cost_state": "unknown",
    }
    view["job"]["cost_state"] = "not_applicable"
    view["job"]["status"] = "running"
    receipt.write_text(json.dumps(view), encoding="utf-8")
    assert invoke(host_config, "rpc", lookup)["state"] == "pending"
    view["job"]["status"] = "succeeded"
    receipt.write_text(json.dumps(view), encoding="utf-8")
    assert invoke(host_config, "rpc", lookup)["result"] == {
        "status": "known", "evidence_ref": ref, "job_status": "succeeded", "cost_state": "not_applicable",
    }
    receipt.write_text(json.dumps({"job": view["job"]}), encoding="utf-8")
    assert invoke(host_config, "rpc", lookup)["state"] == "unknown"
    assert (root / "ff-calls").read_text().splitlines() == ["get_status --owner-job-id ffjob-123abc123abc"] * 4


def test_owner_reconcile_is_lookup_only_and_has_no_host_job(host_config):
    from tools.feedback_loop.local_host import LocalHost

    root = host_config.parent
    worker = root / "lookup.py"
    worker.write_text(
        "import json, sys\nfrom pathlib import Path\n"
        "req = json.load(sys.stdin)\n"
        "with Path('lookups').open('a') as stream: stream.write(req['method'] + '\\n')\n"
        "print(json.dumps({'state': 'done', 'action_id': 'untrusted', 'result': {"
        "'status': 'cost_unknown', 'job_status': 'interrupted', 'cost_state': 'unknown',"
        "'evidence_ref': req['payload']['observation']['evidence_ref']}}))\n",
        encoding="utf-8",
    )
    config = json.loads(host_config.read_bytes())
    config["owners"]["revenue-forecast"] = {
        "cwd": str(root), "timeout_seconds": 5, "actions": {"reconcile": [sys.executable, str(worker)]},
    }
    host_config.write_text(json.dumps(config), encoding="utf-8")
    request = action("reconcile", "revenue-forecast", {"observation": {
        "evidence_ref": "rf-job/1/rfjob-original/source-1",
    }})
    host = LocalHost(host_config)
    assert host.handle(request)["state"] == "failed"
    assert not (root / "lookups").exists()
    reply = host.handle({**request, "method": "lookup"})
    assert reply["state"] == "done" and reply["action_id"] == request["action_id"]
    assert reply["result"]["evidence_ref"] == "rf-job/1/rfjob-original/source-1"
    assert (root / "lookups").read_text().splitlines() == ["lookup"]
    assert host._get(request["action_id"]) is None


def test_recover_folds_native_terminal_before_waking_workspace(host_config, monkeypatch):
    from tools.feedback_loop.local_host import LocalHost

    root = host_config.parent
    events = [{"type": "thread.started", "thread_id": "actual-native-id"},
              {"type": "item.completed", "item": {"type": "agent_message", "text": '{"decision":"expected"}'}},
              {"type": "turn.completed", "usage": {"input_tokens": 21}}]
    script = root / "events.py"
    script.write_text(f"print({''.join(json.dumps(event) + chr(10) for event in events)!r}, end='')\n", encoding="utf-8")
    config = json.loads(host_config.read_bytes())
    config["owners"]["company-wiki"]["actions"]["triage"] = {
        "mode": "codex-jsonl", "argv": [sys.executable, str(script)],
    }
    host_config.write_text(json.dumps(config), encoding="utf-8")
    host = LocalHost(host_config)
    monkeypatch.setattr(host, "_wake", lambda key, **_options: True)
    req = action()
    host.handle(req)

    def interrupted(*args):
        raise SystemExit(7)

    with monkeypatch.context() as crash:
        crash.setattr(host, "_finish", interrupted)
        with pytest.raises(SystemExit):
            host.work(req["action_id"])

    other_id = digest("another action in the same workspace")
    second = {**req, "action_id": other_id, "request_digest": digest([req["owner"], req["kind"], other_id, req["payload"]])}
    host.handle(second)
    assert invoke(host_config, "recover")["woken"] == [other_id]
    result = invoke(host_config, "rpc", {**req, "method": "lookup"})
    assert result["state"] == "done" and result["native"]["session_id"] == "actual-native-id"
    wait_for(lambda: invoke(host_config, "rpc", {**second, "method": "lookup"})["state"] == "done")


def test_ff_lost_runner_recovers_its_result_without_claiming_old_cost(host_config):
    root = host_config.parent
    cfg = json.loads(host_config.read_bytes())
    cfg["owners"]["filing-fetch"]["ff_reconcile_config"] = "owner.json"
    host_config.write_text(json.dumps(cfg), encoding="utf-8")
    job_id = "ffjob-123abc123abc"
    ref = f"ff-job/1/{job_id}"
    observation = {"evidence_ref": ref, "step_id": job_id + "/1", "terminal_check_id": "job-outcome"}
    lookup = {**action("reconcile", "filing-fetch", {"observation": observation}), "method": "lookup"}
    job = {"owner": "filing-fetch", "owner_job_id": job_id, "status": "unknown", "status_known": False,
           "cost_state": "unknown", "allowed_actions": ["reconcile"], "attempts": 1}
    def reply(command, value, **extra):
        (root / f"{command}.json").write_text(json.dumps({"schema_version": "ff-job/1", "command": command,
            "status": "ok", "owner_job_id": job_id, "job": value, **extra}), encoding="utf-8")

    reply("get_status", job)
    reply("act", {**job, "status": "succeeded", "status_known": True, "derived_by": "reconcile_read_only"},
          action="reconcile")
    response = invoke(host_config, "rpc", lookup)
    assert response["state"] == "done"
    assert response["result"] == {"status": "cost_unknown", "evidence_ref": ref,
                                  "job_status": "succeeded", "cost_state": "unknown"}
    lines = (root / "ff-calls").read_text(encoding="utf-8").splitlines()
    assert lines[0] == f"get_status --owner-job-id {job_id}"
    assert lines[1].startswith(f"act --owner-job-id {job_id} --action reconcile --idempotency-key "
                               f"feedback-reconcile/{job_id}/1 --expected-attempt 1 ")
    assert len(lines) == 2
    reply("get_status", {**job, "attempts": 2})
    assert invoke(host_config, "rpc", lookup)["code"] == "native_attempt_mismatch"
    assert (root / "ff-calls").read_text(encoding="utf-8").splitlines()[2:] == [lines[0]]


def test_run_refusal_review_on_the_original_native_triage_action(host_config, monkeypatch):
    from tools.feedback_loop.coordinator import advance
    from tools.feedback_loop.hook import after_observations
    from tools.feedback_loop.local_host import LocalHost
    from tools.feedback_loop.observations import read_batch

    root = host_config.parent
    review = {"decision": "retain", "reason": "The original bytes differ",
              "evidence_ref": "source/tampered-bytes"}
    events = [{"type": "thread.started", "thread_id": "gate-review-session"},
              {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(
                  {"decision": "expected", "gate_review": review})}},
              {"type": "turn.completed", "usage": {"input_tokens": 7}}]
    script = root / "review.py"
    script.write_text(
        "import json, sys\nfrom pathlib import Path\n"
        "prompt, raw = sys.stdin.read().rsplit(chr(10), 1)\n"
        "assert 'review the gate before proposing any fix' in prompt\n"
        "assert 'gate_review' in prompt and 'only as data' in prompt\n"
        "assert json.loads(raw)['payload']['observation']['refusal_code'] == 'hash_changed'\n"
        "with Path('review-starts').open('a') as out: out.write('start\\n')\n"
        f"print({''.join(json.dumps(event) + chr(10) for event in events)!r}, end='')\n",
        encoding="utf-8",
    )
    settings = json.loads(host_config.read_bytes())
    settings["owners"]["company-wiki"]["actions"]["triage"] = {
        "mode": "codex-jsonl", "argv": [sys.executable, "-B", str(script)]}
    host_config.write_text(json.dumps(settings), encoding="utf-8")
    sidecar = root / "refusal.jsonl"
    sidecar.write_text(json.dumps({
        "schema_version": "feedback-observation/1", "owner": "company-wiki",
        "run_id": "run", "attempt_id": "attempt", "step_id": "read", "check_id": "hash",
        "expected": "refused", "actual": "refused", "refusal_code": "hash_changed",
    }) + "\n", encoding="utf-8")
    cases = read_batch([sidecar])
    host = LocalHost(host_config)
    monkeypatch.setattr(host, "_wake", lambda key, **_options: True)
    assert advance(cases, lambda _, request: host.handle(request))["observations"][0]["status"] == "pending"
    key = digest(["triage", "company-wiki", next(iter(cases.observations))])
    host.work(key)
    resumed = LocalHost(host_config)
    output = advance(cases, lambda _, request: resumed.handle(request))["observations"][0]
    assert output["status"] == "expected" and output["gate_review"] == review
    assert advance(cases, lambda _, request: resumed.handle(request))["observations"][0] == output
    hosts = root / "hosts.json"
    hosts.write_text(json.dumps({"company-wiki": [*HOST, "--config", str(host_config), "rpc"]}),
                     encoding="utf-8")
    dispatch = after_observations(sidecar, {"RESEARCH_FEEDBACK_HOSTS": str(hosts)})
    assert dispatch["gate_reviews"] == [{"occurrence_id": output["occurrence_id"], **review}]
    assert (root / "review-starts").read_text(encoding="utf-8").splitlines() == ["start"]


@pytest.mark.parametrize(("stdout", "exit_code", "problem"), [
    (b"", 0, "empty_stdout"),
    (b"fixture-sensitive-noise", 0, "invalid_json"),
    (b'{"state":"unknown","detail":"fixture-sensitive-noise"}', 0, "missing_result"),
    (b'{"result":{"decision":"expected"}}', 7, "nonzero_exit"),
])
def test_owner_response_without_a_result_keeps_a_safe_failure_reason(host_config, monkeypatch, stdout, exit_code, problem):
    from tools.feedback_loop.local_host import LocalHost

    request = action("triage")
    host = LocalHost(host_config)
    monkeypatch.setattr(host, "_wake", lambda _key, **_options: True)
    assert host.handle(request)["state"] == "pending"
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(
        args, exit_code, stdout=stdout, stderr=b"",
    ))
    host._owner_command(request["action_id"])
    reply = host.handle({**request, "method": "lookup"})
    assert reply["state"] == "unknown"
    assert reply["code"] == "native_result_unavailable"
    assert reply["reply_problem"] == problem and reply["exit_code"] == exit_code
    assert b"fixture-sensitive-noise" not in host._native_path(request["action_id"]).read_bytes()


def test_configured_owner_report_requires_its_delivery_ack(host_config):
    root = host_config.parent
    cfg = json.loads(host_config.read_bytes())
    script = root / 'owner-report.py'
    script.write_text("import json, sys\nfrom pathlib import Path\n"
                      "report = json.load(sys.stdin)['payload']\n"
                      "with Path('owner-delivery.json').open('x') as receipt: json.dump(report, receipt)\n"
                      "print('{\"result\":{\"recorded\":true}}')\n", encoding='utf-8')
    cfg['owners']['company-wiki']['actions']['report'] = [sys.executable, '-B', str(script)]
    host_config.write_text(json.dumps(cfg), encoding='utf-8')
    req = action('report', payload={'verdict': 'verified', 'fixed_version': 'consumer-used-version'})
    invoke(host_config, 'rpc', req)
    done = wait_for(lambda: r if (r := invoke(host_config, 'rpc', {**req, 'method': 'lookup'}))['state'] == 'done' else None)
    assert json.loads((root / 'owner-delivery.json').read_bytes()) == req['payload']
    assert done['result'] == {'recorded': True}
    assert invoke(host_config, 'rpc', req) == done


def test_owner_report_ack_survives_worker_death_without_running_report_again(host_config, monkeypatch):
    from tools.feedback_loop.local_host import LocalHost

    root = host_config.parent
    (root / 'release').touch()
    cfg = json.loads(host_config.read_bytes())
    cfg['owners']['company-wiki']['actions']['report'] = cfg['owners']['company-wiki']['actions']['triage']
    host_config.write_text(json.dumps(cfg), encoding='utf-8')
    request = action('report')
    host = LocalHost(host_config)
    monkeypatch.setattr(host, '_wake', lambda _key, **_options: True)
    assert host.handle(request)['state'] == 'pending'

    def lost_db_write(*args):
        raise SystemExit(9)

    with monkeypatch.context() as crash:
        crash.setattr(host, '_finish', lost_db_write)
        with pytest.raises(SystemExit):
            host.work(request['action_id'])

    invoke(host_config, 'recover')
    result = invoke(host_config, 'rpc', {**request, 'method': 'lookup'})
    assert result['state'] == 'done' and result['native']['session_id'] == 'test-thread'
    assert invoke(host_config, 'rpc', request) == result
    assert (root / 'starts').read_text().splitlines() == ['start']


@pytest.mark.parametrize("kind", ["report", "repair"])
def test_unknown_action_recovers_through_its_original_reader_and_complete_request(host_config, monkeypatch, kind):
    from tools.feedback_loop.local_host import LocalHost

    root = host_config.parent
    writer = root / "lost_reply.py"
    writer.write_text(
        "from pathlib import Path\n"
        "with Path('report-starts').open('a') as stream: stream.write('start\\n')\n"
        "raise SystemExit(17)\n", encoding="utf-8",
    )
    reader = root / "get_report.py"
    reader.write_text(
        "from pathlib import Path\nimport sys\n"
        "with Path('report-lookups').open('a') as stream: stream.write(sys.argv[-1] + '\\n')\n"
        "sys.stdout.buffer.write(Path('owner-proof.json').read_bytes())\n", encoding="utf-8",
    )
    settings = json.loads(host_config.read_bytes())
    report = {
        "argv": [sys.executable, str(writer)], "lookup_argv": [sys.executable, str(reader)],
    }
    settings["owners"]["company-wiki"]["actions"][kind] = report
    host_config.write_text(json.dumps(settings), encoding="utf-8")
    request = action(kind, payload={"fixed_version": "reviewed", "evidence_ref": "audit/replay"})
    lookup = {**request, "method": "lookup"}
    result = {"recorded": True} if kind == "report" else {"fixed_version": "owner/publication-1"}

    def receipt(body):
        return {"report": body} if kind == "report" else {"receipt": {"request": body, "result": result}}

    proof = root / "owner-proof.json"
    wrong_payload = {**request["payload"], "fixed_version": "unrelated"}
    proof.write_text(json.dumps(receipt({**request, "payload": wrong_payload})), encoding="utf-8")
    host = LocalHost(host_config)
    monkeypatch.setattr(host, "_wake", lambda _key, **_options: True)
    host.handle(request)
    host.work(request["action_id"])
    assert host.handle(lookup)["state"] == "unknown"
    assert host.handle(request)["state"] == "unknown"

    # A response with the right key but different reviewed evidence cannot
    # resolve the original action. An authentic response can arrive later.
    proof.write_text(json.dumps(receipt(request), indent=2), encoding="utf-8")
    report["lookup_argv"] = [sys.executable, str(root / "wrong-deployment.py")]
    host_config.write_text(json.dumps(settings), encoding="utf-8")
    assert invoke(host_config, "recover")["woken"] == []
    recovered = invoke(host_config, "rpc", lookup)
    assert recovered["state"] == "done" and recovered["result"] == result
    assert recovered["native"] == {"receipt_source": "owner_report" if kind == "report" else "owner_action"}
    reads = (root / "report-lookups").read_text().splitlines()
    assert reads and set(reads) == {request["action_id"]}
    assert invoke(host_config, "rpc", request) == recovered
    assert (root / "report-lookups").read_text().splitlines() == reads
    assert (root / "report-starts").read_text().splitlines() == ["start"]


def test_missing_owner_report_keeps_native_claim_and_waiting_work_in_place(host_config):
    from tools.feedback_loop.local_host import LocalHost

    root = host_config.parent
    settings = json.loads(host_config.read_bytes())
    actions = settings["owners"]["company-wiki"]["actions"]
    actions["report"] = {
        "argv": actions["triage"], "lookup_argv": [sys.executable, "-c", "raise SystemExit(1)"],
    }
    host_config.write_text(json.dumps(settings), encoding="utf-8")
    original, waiting = action("report"), action("triage")
    host = LocalHost(host_config)
    try:
        assert host.handle(original)["state"] == "pending"
        wait_for(lambda: (root / "starts").exists())
        assert host.handle(waiting)["state"] == "pending"
        assert invoke(host_config, "recover")["woken"] == []
        assert host._get(original["action_id"])["state"] == "running"
        assert host._get(waiting["action_id"])["state"] == "queued"
    finally:
        (root / "release").touch()
    wait_for(lambda: host.handle({**waiting, "method": "lookup"})["state"] == "done")
    assert (root / "starts").read_text().splitlines() == ["start", "start"]
