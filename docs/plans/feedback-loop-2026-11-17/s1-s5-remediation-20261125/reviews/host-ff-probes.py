"""Offline regression probes for the host and filing-fetch candidates."""

from __future__ import annotations

import argparse
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from unittest.mock import patch
import uuid


CWP = Path(__file__).resolve().parents[5]
SCRATCH = CWP / ".planning" / "r25"
FF = SCRATCH / "ff"
OWNER = "fixture-owner"


def probe_host(root: Path, *, native_only: bool) -> dict:
    from tools.feedback_loop import intake

    config = root / "settings.json"
    hosts = root / "hosts.json"
    database = root / "ledger.db"
    inbox = root / "observations"
    triage = "import json; print(json.dumps({'result': {'decision': 'needs_evidence'}}))"
    route = {"cwd": str(root), "timeout_seconds": 10,
             "actions": {"triage": [sys.executable, "-B", "-c", triage]}}
    if native_only:
        inbox.mkdir()
        database.mkdir()
        route["native_observation_dirs"] = [str(inbox)]
    else:
        route["observation_dir"] = str(inbox)
    config.write_text(json.dumps({"state": database.name, "owners": {OWNER: route}}), encoding="utf-8")
    hosts.write_text(json.dumps({
        OWNER: [sys.executable, "-B", "-m", "tools.feedback_loop.local_host", "--config", str(config), "rpc"],
    }), encoding="utf-8")
    target_exit = 0 if native_only else 17
    child = (
        "from pathlib import Path; import os; "
        "Path('original-run').write_text(os.environ['RESEARCH_FEEDBACK_RUN_ID']); "
        f"raise SystemExit({target_exit})"
    )
    env = {key: value for key, value in os.environ.items() if not key.startswith("RESEARCH_FEEDBACK_")}
    with patch.dict(os.environ, env, clear=True), patch.object(intake, "wake"):
        exit_code = intake.run_observed(config, hosts, OWNER, [sys.executable, "-B", "-c", child], 0)
    assert exit_code == target_exit
    run = (root / "original-run").read_text(encoding="utf-8")
    ready_before = len(list(inbox.glob("*.ready")))
    fallback_present = (root / ".intake-recovery").is_dir()
    if native_only:
        database.rmdir()
    else:
        moved = inbox.rename(root / "offline-inbox")
    cli = [sys.executable, "-B", "-m", "tools.feedback_loop.intake", "--settings", str(config)]
    drain = json.loads(subprocess.check_output(
        cli + ["--hosts", str(hosts), "--wait-seconds", "10", "drain"], cwd=CWP, timeout=20,
    ))
    history = json.loads(subprocess.check_output(
        cli + ["history", "--run-id", run], cwd=CWP, timeout=20,
    ))
    receipt = {
        "exit": exit_code,
        "native_only": native_only,
        "initial_ready_markers": ready_before,
        "fallback_present": fallback_present,
        "processed": drain["processed"],
        "remaining": drain["remaining"],
        "history": history["status"],
        "history_exit": next((item.get("exit_code") for item in history["processes"]), None),
    }
    if not native_only:
        moved.rename(inbox)
        second = json.loads(subprocess.check_output(
            cli + ["--hosts", str(hosts), "--wait-seconds", "10", "drain"], cwd=CWP, timeout=20,
        ))
        with closing(sqlite3.connect(database)) as connection:
            receipt["observe_count_after_restore"] = connection.execute(
                "SELECT count(*) FROM actions WHERE json_extract(request, '$.kind') = 'observe'",
            ).fetchone()[0]
        receipt["remaining_after_restore"] = second["remaining"]
    return receipt


def probe_statement_detail(root: Path) -> dict:
    spec = importlib.util.spec_from_file_location(
        "ff_fixture", FF / "tests" / "test_ff_runtime_lifecycle.py",
    )
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.SCRIPTS = root / "scripts"
    shutil.copytree(FF / "scripts", fixture.SCRIPTS, ignore=shutil.ignore_patterns("__pycache__"))
    case = fixture.Case(root, "park")
    helper = root / "statements.py"
    helper.write_text(helper.read_text(encoding="utf-8").replace(
        "time.sleep(4)", "while not (root / 'release').is_file(): time.sleep(0.01)",
    ), encoding="utf-8")
    argv = case.argv("fetch_statements.py", "--config", str(case.config), "--timeout-seconds", "12")
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=case.env, cwd=root)
    try:
        assert child.stdin is not None
        child.stdin.write(json.dumps(fixture.REQUEST).encode("utf-8"))
        child.stdin.close()
        child.stdin = None
        case.wait_for_dispatch(child)
        marker, = case.inbox.glob("*.ready")
        observation = json.loads(marker.with_suffix(".jsonl").read_bytes().splitlines()[0])
        keys = ("owner", "run_id", "attempt_id", "step_id")
        terminal = json.dumps(
            [*[observation[key] for key in keys], "complete"], separators=(",", ":"), ensure_ascii=True,
        )
        name = "feedback-" + uuid.uuid5(uuid.NAMESPACE_URL, terminal).hex
        roots = (case.inbox, root / ".ff_jobs" / "observations")
        blocked = [inbox / (name + ".cause.json") for inbox in roots]
        for path in blocked:
            path.mkdir(parents=True)
        (root / "release").touch()
        stdout, stderr = child.communicate(timeout=15)
        for path in blocked:
            path.rmdir()
        pure = case.invoke("ff_job_feedback.py", "get-statement-run", observation["evidence_ref"],
                           "--jobs-dir", str(case.jobs))
        terminal_before_reconcile = any((inbox / (name + ".ready")).is_file() for inbox in roots)
        action = fixture._feedback_request(observation)
        answers = [json.loads(case.invoke(
            "ff_job_feedback.py", "reconcile", "--jobs-dir", str(case.jobs), body=action,
        ).stdout) for _ in range(2)]
        diagnostic = case.diagnostic("ff-diagnostic/1/" + name)
        return {
            "exit": child.returncode,
            "business_status": json.loads(stdout)["status"],
            "warned": b"feedback detail unavailable" in stderr,
            "pure_read_state": json.loads(pure.stdout)["state"],
            "terminal_after_pure_read": terminal_before_reconcile,
            "reconcile_state": answers[0]["state"],
            "same_cold_result": answers[0] == answers[1],
            "trace_has_details": bool(answers[0]["result"]["trace"]["outcome"]["diagnostic"]),
            "native_terminal_exists": any((inbox / (name + ".ready")).is_file() for inbox in roots),
            "get_diagnostic_exit": diagnostic.returncode,
            "calls": case.count(),
        }
    finally:
        (root / "release").touch()
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)


def probe_restart_environment(root: Path) -> dict:
    from tools.feedback_loop.host import process_host
    from tools.feedback_loop.local_host import LocalHost
    from tools.feedback_loop.observations import digest

    config = root / "settings.json"
    route = {"cwd": str(root), "timeout_seconds": 10, "actions": {"triage": [sys.executable, "-c", "pass"]}}
    config.write_text(json.dumps({"state": "ledger.db", "owners": {OWNER: route}}), encoding="utf-8")
    host = LocalHost(config)
    key = "7" * 64
    payload = {"occurrence_id": "offline-fixture"}
    request = {
        "schema_version": "feedback-action/1", "owner": OWNER, "kind": "triage", "action_id": key,
        "method": "submit", "payload": payload, "request_digest": digest([OWNER, "triage", key, payload]),
    }
    routes = {OWNER: {
        "argv": [sys.executable, "-B", "-m", "tools.feedback_loop.local_host", "--config", str(config), "rpc"],
        "pass_env": ["TEST_R25_ALLOWED"],
    }}
    launches = []

    def observe_wake(*_argv, **kwargs):
        launches.append({field: field in kwargs["env"] for field in ("TEST_R25_PRIVATE", "TEST_R25_ALLOWED")})

    with patch.dict(os.environ, {"TEST_R25_PRIVATE": "parent-only", "TEST_R25_ALLOWED": "synthetic"}):
        with patch("tools.feedback_loop.local_host.subprocess.Popen", observe_wake):
            first = process_host(routes, local=host)(OWNER, request)["state"]
            resumed = host.recover(owners=[OWNER])
    return {"submitted": first, "woken": len(resumed), "launch_environment": launches}


def probe_registry_environment(root: Path, *, direct_rpc: bool) -> dict:
    from tools.feedback_loop.observations import digest

    config = root / "settings.json"
    registry = root / ("hosts.json" if direct_rpc else "explicit-owners.json")
    receipt = root / "seen.json"
    python = [sys.executable, "-B"]
    rpc = [*python, "-m", "tools.feedback_loop.local_host", "--config", str(config), "rpc"]
    owner_program = (
        "from pathlib import Path; import json, os; "
        "seen = {'allowed': 'TEST_R25_ALLOWED' in os.environ, 'private': 'TEST_R25_PRIVATE' in os.environ}; "
        "Path('seen.json').write_text(json.dumps(seen)); "
        "print(json.dumps({'state': 'done', 'result': seen}))"
    )
    action = "reconcile" if direct_rpc else "flush-observations"
    route = {"cwd": str(root), "timeout_seconds": 10, "actions": {action: [*python, "-c", owner_program]}}
    config.write_text(json.dumps({"state": "ledger.db", "owners": {OWNER: route}}), encoding="utf-8")
    registry.write_text(json.dumps({OWNER: {"argv": rpc, "pass_env": ["TEST_R25_ALLOWED"]}}), encoding="utf-8")
    names = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE",
             "HOME", "USERPROFILE", "TEMP", "TMP", "APPDATA", "LOCALAPPDATA", "PYTHONPATH"}
    env = {name: value for name, value in os.environ.items() if name.upper() in names}
    env.update(TEST_R25_PRIVATE="parent-only", TEST_R25_ALLOWED="synthetic")
    if direct_rpc:
        payload = {"occurrence_id": "synthetic"}
        key = "0" * 64
        request = {
            "schema_version": "feedback-action/1", "action_id": key, "owner": OWNER,
            "kind": action, "method": "lookup", "payload": payload,
            "request_digest": digest([OWNER, action, key, payload]),
        }
        completed = subprocess.check_output(rpc, input=json.dumps(request).encode(), env=env, cwd=CWP, timeout=20)
        assert json.loads(completed)["state"] == "done"
    else:
        drain = [*python, "-m", "tools.feedback_loop.intake", "--settings", str(config),
                 "--hosts", str(registry), "drain"]
        completed = subprocess.check_output(drain, env=env, cwd=CWP, timeout=20)
        assert not json.loads(completed)["diagnostics"]
    return {"entry": action, **json.loads(receipt.read_bytes())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=[
        "host-native-only", "host-post-offer", "ff-direct-detail", "host-restart-environment",
        "host-public-rpc-environment", "host-explicit-registry-environment",
    ])
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="r-", dir=SCRATCH) as directory:
        sandbox = Path(directory)
        if args.scenario == "host-restart-environment":
            result = probe_restart_environment(sandbox)
        elif args.scenario in ("host-public-rpc-environment", "host-explicit-registry-environment"):
            result = probe_registry_environment(sandbox, direct_rpc=args.scenario == "host-public-rpc-environment")
        elif args.scenario.startswith("host-"):
            result = probe_host(sandbox, native_only=args.scenario == "host-native-only")
        else:
            result = probe_statement_detail(sandbox)
        print(json.dumps(result))
