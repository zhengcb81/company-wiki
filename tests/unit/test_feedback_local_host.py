import json
from pathlib import Path
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from tools.feedback_loop.observations import digest


ROOT = Path(__file__).resolve().parents[2]
HOST = [sys.executable, "-B", "-m", "tools.feedback_loop.local_host"]


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
        "with Path(sys.argv[1]).open('a') as stream: stream.write(' '.join(sys.argv[2:]) + '\\n')\n"
        "print(Path(sys.argv[2] + '.json').read_text())\n",
        encoding="utf-8",
    )
    config = tmp_path / "host.json"
    config.write_text(json.dumps({"state": "actions.sqlite", "owners": {"company-wiki": {
        "cwd": str(tmp_path), "timeout_seconds": 12, "actions": {"triage": [sys.executable, "-B", str(worker)]}},
        "filing-fetch": {"cwd": str(tmp_path), "ff_status_argv": [sys.executable, "-B", str(status), "ff-calls"]},
    }}), encoding="utf-8")
    return config


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
    assert invoke(host_config, "rpc", lookup)["state"] == "unknown"
    view["job"]["cost_state"] = "not_applicable"
    view["job"]["status"] = "running"
    receipt.write_text(json.dumps(view), encoding="utf-8")
    assert invoke(host_config, "rpc", lookup)["state"] == "pending"
    view["job"]["status"] = "succeeded"
    receipt.write_text(json.dumps(view), encoding="utf-8")
    assert invoke(host_config, "rpc", lookup)["result"] == {"status": "known", "evidence_ref": ref}
    receipt.write_text(json.dumps({"job": view["job"]}), encoding="utf-8")
    assert invoke(host_config, "rpc", lookup)["state"] == "unknown"
    assert (root / "ff-calls").read_text().splitlines() == ["get_status --owner-job-id ffjob-123abc123abc"] * 4


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
    monkeypatch.setattr(host, "_wake", lambda key: True)
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
