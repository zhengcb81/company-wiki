"""Run FF and CWP through their real CLI, with a controlled HTTP provider."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from . import test_m3_acquisition_usage_cwp as metered_provider


ROOT = Path(__file__).resolve().parents[2]
PY = [sys.executable, "-B", "-X", "utf8"]
loopback = metered_provider.loopback
_AFTER_ENSURE = '''
import json, subprocess, sys, time
from pathlib import Path

ready, release = map(Path, sys.argv[1:3])
result = subprocess.run(sys.argv[3:], capture_output=True, stdin=subprocess.DEVNULL)
if result.returncode == 0 and "ensure" in sys.argv[3:]:
    proof = json.loads(result.stdout)
    if proof.get("source_ref") and proof.get("download_events") == 1:
        stage = ready.with_suffix(".tmp")
        stage.write_bytes(result.stdout)
        stage.replace(ready)
        end = time.monotonic() + 60
        while not release.exists() and time.monotonic() < end:
            time.sleep(.05)
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
raise SystemExit(result.returncode)
'''

_COUNT_OWNER_REPORT = """
from pathlib import Path
import subprocess
import sys

with Path(sys.argv[1]).open("a", encoding="ascii") as stream:
    stream.write("report\\n")
raise SystemExit(subprocess.run(sys.argv[2:], check=False).returncode)
"""

_LOSE_REPORT_REPLY = """
from pathlib import Path
import json
import os
import subprocess
import sys
from tools.feedback_loop.local_host import LocalHost

run = subprocess.run

def lose_reply(*args, **kwargs):
    outcome = run(*args, **kwargs)
    assert outcome.returncode == 0, outcome.stderr
    assert json.loads(outcome.stdout) == {"result": {"recorded": True}}
    os._exit(17)

subprocess.run = lose_reply
LocalHost(Path(sys.argv[1]))._owner_command(sys.argv[2])
"""


def _write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("owner", ["filing-fetch", "revenue-forecast"])
def test_owner_report_survives_lost_reply_before_host_receipt(tmp_path, monkeypatch, owner):
    from tools.feedback_loop.local_host import LocalHost
    from tools.feedback_loop.observations import digest

    env = "FEEDBACK_FF_CODE_ROOT" if owner == "filing-fetch" else "FEEDBACK_RF_CODE_ROOT"
    owner_root = os.environ.get(env)
    if not owner_root:
        pytest.skip(f"set {env} to a compatible {owner} checkout")
    filename = "ff_job_feedback.py" if owner == "filing-fetch" else "rf_job_feedback.py"
    script = Path(owner_root).resolve() / "scripts" / filename
    assert script.is_file()
    reports = tmp_path / "reports"

    def owner_command(kind, *args):
        options = ("--reports-dir", str(reports))
        tail = (*options, kind) if owner == "filing-fetch" else (kind, *options)
        return [*PY, str(script), *tail, *args]

    launcher = tmp_path / "report_once.py"
    launcher.write_text(_COUNT_OWNER_REPORT, encoding="utf-8")
    starts = tmp_path / "report-starts"
    next_worker = tmp_path / "next_action.py"
    next_worker.write_text("""print('{"result":{"decision":"expected"}}')\n""", encoding="ascii")
    config = _write(tmp_path / "host.json", {"state": "host.sqlite", "owners": {
        owner: {"cwd": str(tmp_path), "timeout_seconds": 30, "actions": {
            "report": {
                "argv": [*PY, str(launcher), str(starts), *owner_command("report")],
                "lookup_argv": owner_command("get-report"),
            },
            "triage": [*PY, str(next_worker)],
        }},
    }})
    settings = LocalHost(Path(config))
    monkeypatch.setattr(settings, "_wake", lambda _key: True)
    def action(kind, action_id, payload):
        return {"schema_version": "feedback-action/1", "method": "submit", "action_id": action_id, "owner": owner,
                "kind": kind, "payload": payload, "request_digest": digest([owner, kind, action_id, payload])}

    body = {"occurrence_id": "original", "original_occurrence_id": "original", "origin_owner": "company-wiki",
            "issue_ref": "source-reuse", "fixed_version": "reviewed", "verdict": "verified",
            "evidence_ref": "integration/source-replay"}
    key = digest(["report", owner, body["occurrence_id"], owner, body["issue_ref"], body["fixed_version"], body["verdict"]])
    request = action("report", key, body)
    later = action("triage", digest(["triage", owner, "queued"]), {})
    assert settings.handle(request)["state"] == "pending"
    proc = subprocess.run([*PY, "-c", _LOSE_REPORT_REPLY, config, key], cwd=ROOT, capture_output=True, timeout=30)
    assert proc.returncode == 17, (proc.stdout, proc.stderr)
    assert settings._native_path(key).read_bytes() == b""
    assert settings._get(key)["state"] == "running"
    assert settings.handle(later)["state"] == "pending"

    read_report = owner_command("get-report", key)
    assert json.loads(subprocess.check_output(read_report, timeout=10)) == {"report": request}
    saved = (reports / f"{key}.json").stat().st_mtime_ns
    host = [*PY, "-m", "tools.feedback_loop.local_host", "--config", config]

    def recover(_):
        return json.loads(subprocess.check_output([*host, "recover"], cwd=ROOT, timeout=25))

    with ThreadPoolExecutor(2) as pool:
        wakes = list(pool.map(recover, range(2)))
    recovered = LocalHost(Path(config)).handle({**request, "method": "lookup"})
    assert recovered["state"] == "done" and recovered["action_id"] == key
    assert recovered["result"] == {"recorded": True}
    assert [later["action_id"]] in [reply["woken"] for reply in wakes]
    deadline = time.monotonic() + 10
    lookup_later = {**later, "method": "lookup"}
    while (second := settings.handle(lookup_later))["state"] == "pending" and time.monotonic() < deadline:
        time.sleep(.05)
    assert second["state"] == "done"
    assert LocalHost(Path(config)).handle(request) == recovered
    assert starts.read_text().splitlines() == ["report"]
    assert (reports / f"{key}.json").stat().st_mtime_ns == saved
    assert json.loads(subprocess.check_output(read_report, timeout=10)) == {"report": request}


@pytest.mark.parametrize("mode", ["exact", "latest_as_of"])
def test_hard_kill_filing_runner_recovers_same_original_and_preserves_unknown_cost(tmp_path, loopback, monkeypatch, mode):
    ff_code = os.environ.get("FEEDBACK_FF_CODE_ROOT")
    if not ff_code:
        pytest.skip("set FEEDBACK_FF_CODE_ROOT to a compatible filing-fetch checkout")
    ff = Path(ff_code).resolve() / "scripts" / "ff_job.py"
    assert ff.is_file()
    catalog, acquisition, provider_log, _ = metered_provider._fixture_root(tmp_path, "ok")
    from tools.document_understanding_benchmark.phase_c_runner import seed_identity

    seed_identity(tmp_path, "loopback", {"market": "US"})
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    monkeypatch.setenv("M3_LOOPBACK_BASE_URL", f"http://127.0.0.1:{loopback.server_address[1]}")
    http_calls = []
    serve = loopback.RequestHandlerClass.do_GET

    def counted(handler):
        http_calls.append(handler.path)
        serve(handler)

    monkeypatch.setattr(loopback.RequestHandlerClass, "server_mode", "ok")
    monkeypatch.setattr(loopback.RequestHandlerClass, "do_GET", counted)
    ready, release = tmp_path / "first-ensure.json", tmp_path / "release"
    gate = tmp_path / "after_ensure.py"
    gate.write_text(_AFTER_ENSURE, encoding="utf-8")

    def cwp(module):
        return [*PY, "-m", f"company_wiki.source_catalog.{module}", "--config", str(catalog)]

    config = _write(tmp_path / "ff.json", {"schema_version": "1.0", "connection": {
        "cwd": str(ROOT), "acquisition_config": str(acquisition), "commands": {
            "catalog": [*PY, str(gate), str(ready), str(release), *cwp("cli")],
            "query": cwp("source_query_cli"), "open": cwp("source_reader_cli"),
        },
    }})
    jobs = tmp_path / "jobs"
    ff_cli = [*PY, str(ff), "--jobs-dir", str(jobs)]

    def invoke(args, payload=None):
        outcome = subprocess.run(args, cwd=ROOT, input=json.dumps(payload).encode("ascii"),
                                 capture_output=True, timeout=55, check=False)
        assert outcome.returncode == 0, (outcome.stdout.decode(errors="replace"), outcome.stderr.decode(errors="replace"))
        return json.loads(outcome.stdout)

    request = {"schema_version": "2.0", "company_query": "ACME", "market": "US",
               "document_kind": "annual_report", "as_of_date": "2026-10-10", "mode": mode,
               "filing_intent": "fetch_if_missing", "acquisition_limits": {
                   "max_bytes": 20000, "timeout_seconds": 90, "max_cost_usd": "1",
               }}
    if mode == "exact":
        request["fiscal_year"] = 2025
    job_id = invoke([*ff_cli, "submit"], {"schema_version": "ff-job/1", "kind": "filing.acquire",
                    "command_id": "f4-first", "idempotency_key": "f4-first", "request": request})["owner_job_id"]
    sidecar = tmp_path / "observations.jsonl"
    local_host = [*PY, "-m", "tools.feedback_loop.local_host", "--config", _write(tmp_path / "local.json", {
        "state": "feedback.sqlite", "owners": {"filing-fetch": {"cwd": str(ROOT), "ff_status_argv": ff_cli,
                                                                 "ff_reconcile_config": config}},
    })]
    host_map = _write(tmp_path / "hosts.json", {"filing-fetch": {"argv": local_host + ["rpc"], "pass_env": ["PYTHONPATH"]}})
    recover = [*local_host, "recover", "--hosts", host_map, "--sidecar", str(sidecar), "--wait-seconds", "5"]
    status = [*ff_cli, "get_status", "--owner-job-id", job_id]
    proc = subprocess.Popen([*ff_cli, "run", "--owner-job-id", job_id, "--config", config, "--timeout-seconds", "90"],
                            cwd=ROOT, env={**os.environ, "RESEARCH_FEEDBACK_OUT": str(sidecar)},
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    try:
        until = time.monotonic() + 25
        while not ready.is_file() and proc.poll() is None and time.monotonic() < until:
            time.sleep(.05)
        if not ready.is_file():
            release.touch()
            pytest.fail(proc.communicate(timeout=12))
        proof = json.loads(ready.read_bytes())
        assert proof["acquisition_observation"]["cost_usd"] == "0.0009"  # controlled reported fee, no live charge
        assert proof["source_ref"]["content_sha256"] == hashlib.sha256(metered_provider.BODY_ENTITY).hexdigest()
        assert provider_log.read_text().splitlines() == ["discover", "fetch"]
        assert http_calls == ["/meta1", "/meta2", "/body"]
        assert invoke(status)["job"]["status"] == "running"
        only_start = sidecar.read_bytes().splitlines()
        assert len(only_start) == 1 and json.loads(only_start[0])["evidence_ref"] == "ff-job/1/" + job_id
        proc.kill()
        proc.communicate(timeout=10)
        assert proc.returncode
        interrupted = invoke(status)["job"]
        assert (interrupted["status"], interrupted["status_known"], interrupted["cost_state"]) == ("unknown", False, "unknown")
        with ThreadPoolExecutor(2) as pool:
            list(pool.map(invoke, (recover, recover)))
        observed = invoke(recover)["feedback"]["observations"][0]
        assert observed["status"] == "unknown" and observed["job_status"] == "succeeded" and observed["cost_state"] == "unknown"
        assert observed["evidence_ref"] == "ff-job/1/" + job_id
        done = invoke(status)["job"]
        assert done["owner_job_id"] == job_id and done["derived_by"] == "reconcile_read_only"
        assert done["result"]["source_ref"] == proof["source_ref"]
        assert done["result"]["downloads"] == 0 and done["cost"] is None
        assert done["attempts"] == 1 and done["execution_count"] == 0
        assert done["allowed_actions"] == []
        assert invoke([*ff_cli, "list_jobs"])["page"]["total"] == 1
        native_log = [json.loads(row) for row in (jobs / "logs" / f"{job_id}.log").read_bytes().splitlines()]
        assert [line["event"] for line in native_log].count("run_started") == 1
        assert [line["event"] for line in native_log].count("reconciled") == 1
        assert provider_log.read_text().splitlines() == ["discover", "fetch"]
        assert http_calls == ["/meta1", "/meta2", "/body"]
        assert sidecar.read_bytes().splitlines() == only_start
        print(json.dumps({"mode": mode, "owner_job_id": job_id, "hard_killed_exit": proc.returncode,
                          "original_sha256": proof["source_ref"]["content_sha256"], "native_starts": 1,
                          "reconciled": 1, "completion": done["status"], "previous_cost": done["cost_state"],
                          "provider_calls_first": http_calls, "provider_calls_after_restart": [],
                          "mock_fee_before": "0.0009", "additional_mock_fee": "0", "new_jobs": 0}))
    finally:
        release.touch()
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=10)
