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
    monkeypatch.setattr(host, "_wake", lambda _key: True)
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
    monkeypatch.setattr(host, "_wake", lambda _key: True)
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
    assert (root / "ff-calls").read_text().splitlines()[2:] == [lines[0]]


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
    monkeypatch.setattr(host, '_wake', lambda _: True)
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


def test_unknown_report_recovers_through_its_original_reader_and_complete_request(host_config, monkeypatch):
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
    settings["owners"]["company-wiki"]["actions"]["report"] = report
    host_config.write_text(json.dumps(settings), encoding="utf-8")
    request = action("report", payload={"fixed_version": "reviewed", "evidence_ref": "audit/replay"})
    lookup = {**request, "method": "lookup"}
    proof = root / "owner-proof.json"
    wrong_payload = {**request["payload"], "fixed_version": "unrelated"}
    proof.write_text(json.dumps({"report": {**request, "payload": wrong_payload}}), encoding="utf-8")
    host = LocalHost(host_config)
    monkeypatch.setattr(host, "_wake", lambda _key: True)
    host.handle(request)
    host.work(request["action_id"])
    assert host.handle(lookup)["state"] == "unknown"
    assert host.handle(request)["state"] == "unknown"

    # A response with the right key but different reviewed evidence cannot
    # resolve the original action. An authentic response can arrive later.
    proof.write_text(json.dumps({"report": request}, indent=2), encoding="utf-8")
    report["lookup_argv"] = [sys.executable, str(root / "wrong-deployment.py")]
    host_config.write_text(json.dumps(settings), encoding="utf-8")
    assert invoke(host_config, "recover")["woken"] == []
    recovered = invoke(host_config, "rpc", lookup)
    assert recovered["state"] == "done" and recovered["result"] == {"recorded": True}
    assert recovered["native"] == {"receipt_source": "owner_report"}
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
