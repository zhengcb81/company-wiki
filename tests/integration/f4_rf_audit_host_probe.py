"""Run the RF/Audit F4 check on isolated copies and a counted loopback provider.

Supply --codex for the real agent host. Without it, only the agent turn is
substituted. RF, Audit, LocalHost and abrupt supervisor recovery still run as
separate native processes. The only external request is the optional triage.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from threading import Thread
import time

from f4_real_host_probe import PY, ROOT, _interrupt_controller, _run, _write
from tools.feedback_loop.observations import digest, read_batch


RF, AUDIT = "revenue-forecast", "revenue-forecast-audit"
ISSUE = "rf-source-dispatch-can-reach-provider-without-download"
FINDING = "PROCESS-F4-01"
RUN = "f4-rf-source-recovery"
DEFECT = """A provider-capable metadata lookup was allowed to resume without terminal
proof because the filing reused existing bytes. Separate source route from
download outcome. Keep an interrupted provider-capable attempt read-only."""

_GATE = """
from pathlib import Path
import sys
import time

scripts, ready, *rf_args = sys.argv[1:]
sys.path.insert(0, scripts)
import rf_job_facade
from rf_job_cli import main

def before_freeze(*args):
    Path(ready).touch()
    time.sleep(45)
    raise RuntimeError("test supervisor did not terminate")

rf_job_facade._freeze_source_artifact = before_freeze
sys.argv[1:] = rf_args
raise SystemExit(main())
"""

_REPLAY = """
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

case = json.loads(Path(sys.argv[1]).read_bytes())
scripts = Path(case["owner"]) / "scripts"
if {p.name: sha256(p.read_bytes()).hexdigest() for p in scripts.glob("*.py")} != case["fixed_sha"]:
    raise SystemExit("RF is not running the reviewed version")
reply = subprocess.check_output([sys.executable, "-B", str(scripts / "rf_job_cli.py"),
                                 "--owner-root", case["job_root"], "get-status",
                                 "--job-id", case["job_id"]], timeout=12)
view = json.loads(reply)["job_view"]
assert view["owner_job_id"] == case["job_id"]
assert view["stages"][0]["attempt_count"] == 1
assert view["stages"][0]["attempts"][0]["attempt_id"] == "source-1"
assert view["status"] == "interrupted" and view["cost_state"] == "unknown" and view["cost"] is None
assert view["budget"]["new_downloads"] == 0 and view["budget"]["paid_model_calls"] == 0
safe = view["allowed_actions"] == ["reconcile"]
print(json.dumps({"verdict": "verified" if safe else "regressed",
                  "verified_version": case["version"], "evidence_ref": case["finding_ref"]}))
"""

_APPLY = """
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

case = json.loads(Path(sys.argv[1]).read_bytes())
action = json.load(sys.stdin)
assert action["payload"] == {"issue_ref": case["issue"], "generation": "f4-source-route-1"}
owner, candidate = Path(case["owner"]) / "scripts", Path(case["fixed"]) / "scripts"
assert {p.name: sha256(p.read_bytes()).hexdigest() for p in owner.glob("*.py")} == case["old_sha"]
assert {p.name: sha256(p.read_bytes()).hexdigest() for p in candidate.glob("*.py")} == case["fixed_sha"]
for name, new_sha in case["fixed_sha"].items():
    if case["old_sha"].get(name) != new_sha:
        shutil.copyfile(candidate / name, owner / name)
print(json.dumps({"result": {"fixed_version": case["version"]}}))
"""


def _scripts(repo, version, destination):
    data = subprocess.check_output(["git", "-C", str(repo), "archive", version, "scripts"], timeout=25)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(destination, filter="data")


def _script_shas(root):
    return {file.name: sha256(file.read_bytes()).hexdigest() for file in (root / "scripts").glob("*.py")}


def _revision(repo, revision):
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", revision], text=True, timeout=10).strip()


def _kill_at_marker(argv, marker, *, env=None, request=None):
    child = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=request or subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline and child.poll() is None:
            if marker.is_file():
                child.kill()
                child.wait(timeout=10)
                return
            time.sleep(0.05)
        raise RuntimeError(("no native start marker", child.poll(), child.communicate(timeout=3) if child.poll() is not None else None))
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)


def _start_rf(repo, ff_repo, owner, case_root, port, *, sidecar=None):
    sys.path.insert(0, str(repo / "tests"))
    from test_rf_job_facade_cli import _deployment, _request

    case_root.mkdir()
    deployment, body = _deployment(case_root)
    original_hash = sha256(body.read_bytes()).hexdigest()
    config = json.loads(deployment.read_bytes())
    config["stages"]["source"]["request_template"].update(
        mode="latest_as_of", fiscal_year=None,
        acquisition_limits={"max_bytes": 4096, "timeout_seconds": 8, "max_cost_usd": "0.00"},
    )
    _write(deployment, config)
    connector = case_root / "ff/scripts/fetch_filing.py"
    existing = connector.read_text(encoding="utf-8")
    connector.write_text(
        existing.replace("sys.stdout.buffer.write", f"sys.path.insert(0, {str(ff_repo / 'scripts')!r})\n"
                         "from filing_contracts import validate_request\n"
                         "validate_request(request)\n"
                         "assert request['mode'] == 'latest_as_of'\n"
                         "from urllib.request import urlopen\n"
                         f"with urlopen('http://127.0.0.1:{port}/listing', timeout=8) as body:\n"
                         "    assert body.read() == b'listing'\n"
                         "sys.stdout.buffer.write"), encoding="utf-8",
    )
    gate = case_root / "gate.py"
    gate.write_text(_GATE, encoding="utf-8")
    marker, job_root = case_root / "ready", case_root / "jobs"
    job_root.mkdir()
    request_path = _write(case_root / "request.json", _request())
    env = dict(os.environ, PYTHON_DOTENV_DISABLED="1")
    if sidecar:
        env["RESEARCH_FEEDBACK_OUT"] = str(sidecar)
    with Path(request_path).open("rb") as request:
        _kill_at_marker([*PY, str(gate), str(owner / "scripts"), str(marker), "--owner-root",
                         str(job_root), "--deployment-config", str(deployment), "submit"],
                        marker, env=env, request=request)
    assert sha256(body.read_bytes()).hexdigest() == original_hash
    status = [*PY, str(owner / "scripts/rf_job_cli.py"), "--owner-root", str(job_root)]
    jobs = _run([*status, "list-jobs"])["jobs"]
    assert len(jobs) == 1 and jobs[0]["status"] == "interrupted"
    return job_root, status, jobs[0]


def _audit_capture(audit, run, tmp):
    release, ready = tmp / "audit-release", tmp / "audit-ready"
    task = tmp / "held-audit.py"
    task.write_text(
        "from pathlib import Path\nimport sys, time\n"
        "ready, release = map(Path, sys.argv[1:])\n"
        "with ready.open('a') as out: out.write('start\\n')\n"
        "deadline = time.monotonic() + 12\n"
        "while not release.exists() and time.monotonic() < deadline: time.sleep(.03)\n",
        encoding="utf-8",
    )
    sidecar = tmp / "audit-start.jsonl"
    env = dict(os.environ, RESEARCH_FEEDBACK_OUT=str(sidecar))
    try:
        _kill_at_marker([*audit, "capture", "--run", str(run), "--role", "process", "--",
                         *PY, str(task), str(ready), str(release)], ready, env=env)
    finally:
        release.touch()
    batch = read_batch([sidecar])
    assert len(batch.unfinished_starts()) == 1
    return sidecar, next(iter(batch.observations.values())), ready


def _probe(args, tmp, provider, port):
    before, after = _revision(args.rf_repo, args.before), _revision(args.rf_repo, args.after)
    old, fixed = tmp / "old", tmp / "fixed"
    _scripts(args.rf_repo, before, old)
    _scripts(args.rf_repo, after, fixed)
    job_root, status, original = _start_rf(args.rf_repo, args.ff_repo, old, tmp / "initial", port)
    assert original["allowed_actions"] == ["resume", "reconcile"] and provider == {"/listing": 1}
    job_id = original["owner_job_id"]
    rf_start = tmp / "rf-start.jsonl"
    fixed_root, _, existing = _start_rf(args.rf_repo, args.ff_repo, fixed, tmp / "corrected", port, sidecar=rf_start)
    assert existing["allowed_actions"] == ["reconcile"] and provider == {"/listing": 2}
    audit_scripts = args.audit_repo / "skills/revenue-forecast-audit/scripts"
    audit = [*PY, str(audit_scripts / "audit_run.py")]
    run = Path(_run([*audit, "init", "--root", str(tmp / "audit"), "--company", "Test Co",
                     "--as-of", "2025-07-01", "--run-id", RUN])["run"])
    capture_path, capture_row, audit_starts = _audit_capture(audit, run, tmp)
    audit_owner = [*PY, str(audit_scripts / "feedback_owner.py"), "--run", str(run)]
    capture_id = capture_row["attempt_id"]
    audit_status = [*audit_owner, "get-capture", "--role", "process", "--capture-id", capture_id]
    assert _run(audit_status) == {"status": "unconfirmed", "cost_state": "unknown"}
    evidence = [{"artifact": f"rf-job/1/{job_id}/source-1", "locator": "job_view.allowed_actions"}]
    _write(run / "reports/process.json", {
        "schema_version": json.loads((run / "run.json").read_bytes())["schema_version"],
        "run_id": RUN, "role": "process", "executor_completion": "partial",
        "checks": [{"check_id": "source-resume", "status": "FAIL", "detail": DEFECT, "evidence": evidence}],
        "findings": [{"issue_id": FINDING, "severity": "P1", "category": "code", "summary": DEFECT,
                      "expected": "reconcile only", "actual": "+".join(original["allowed_actions"]),
                      "root_cause_hypothesis": DEFECT, "recommendation": "test original resume decision",
                      "evidence": evidence}],
    })
    finding = _run([*audit_owner, "observe-finding", "--role", "process", "--issue", FINDING, "--issue-owner", RF,
                    "--issue-key", ISSUE, "--version", before])
    sidecar = tmp / "issue.jsonl"
    sidecar.write_text(json.dumps(finding) + "\n", encoding="ascii")
    case = _write(tmp / "case.json", {"owner": str(old), "fixed": str(fixed), "issue": ISSUE, "version": after,
        "old_sha": _script_shas(old), "fixed_sha": _script_shas(fixed), "job_root": str(job_root),
        "job_id": job_id, "finding_ref": finding["evidence_ref"]})
    apply, replay = tmp / "apply.py", tmp / "replay.py"
    apply.write_text(_APPLY, encoding="utf-8")
    replay.write_text(_REPLAY, encoding="utf-8")
    answer = {"decision": "repair", "issue_ref": ISSUE, "generation": "f4-source-route-1"}
    instruction = (
        "Classify this isolated RF feedback observation. Do not use tools. Metadata dispatch can run even when "
        "download count is zero. Public status proves the same original source attempt is interrupted; "
        "native usage is unknown and allowed_actions contains resume. If this identifies unsafe resubmission, "
        "return this JSON unchanged: " + json.dumps(answer) + ". Otherwise return {\"decision\":\"needs_evidence\"}."
    )
    if args.codex:
        triage = {"mode": "codex-jsonl", "instruction": instruction,
                  "argv": [args.codex, "-a", "never", "exec", "--sandbox", "read-only", "--skip-git-repo-check",
                           "--ephemeral", "--json", "--color", "never", "-"]}
    else:
        stub = tmp / "triage.py"
        stub.write_text(f"print({json.dumps({'result': answer})!r})\n", encoding="ascii")
        triage = [*PY, str(stub)]

    reports = [*PY, str(fixed / "scripts/rf_job_feedback.py")]
    settings = tmp / "host.json"
    _write(settings, {"state": "host.sqlite", "owners": {
        RF: {"cwd": str(old), "timeout_seconds": 120, "actions": {
            "triage": triage, "repair": [*PY, str(apply), case],
            "report": [*reports, "report", "--reports-dir", str(tmp / "reports")],
            "reconcile": [*reports, "reconcile", "--owner-root", str(fixed_root)],
        }},
        AUDIT: {"cwd": str(run), "timeout_seconds": 35, "actions": {
            "replay": [*audit_owner, "replay", "--", *PY, str(replay), case],
            "reconcile": [*audit_owner, "reconcile"],
        }},
    }})
    command = [*PY, "-m", "tools.feedback_loop.local_host", "--config", str(settings)]
    ports = _write(tmp / "ports.json", {owner: command + ["rpc"] for owner in (RF, AUDIT)})
    recover = [*command, "recover", "--hosts", ports, "--sidecar", str(sidecar),
               "--sidecar", str(rf_start), "--sidecar", str(capture_path)]
    key, observed = next(iter(read_batch([sidecar]).observations.items()))
    native_session = None
    if args.codex:
        payload = {"occurrence_id": key, "observation": observed}
        triage_key = digest(["triage", RF, key])
        lookup = {"schema_version": "feedback-action/1", "method": "lookup", "kind": "triage", "owner": RF,
                  "action_id": triage_key, "request_digest": digest([RF, "triage", triage_key, payload]),
                  "payload": payload}
        # Keep the kill probe's child on the defect only. Recovery adds both
        # original interrupted observations in the same, reused host database.
        initial = [*command, "recover", "--hosts", ports, "--sidecar", str(sidecar), "--wait-seconds", "145"]
        native_session = _interrupt_controller(initial, settings, lookup)
        print("Controller force-stopped after the native triage started", file=sys.stderr, flush=True)
    wait = 110 if args.codex else 30
    found = _run([*recover, "--wait-seconds", str(wait)], timeout=wait + 25)["feedback"]
    assert not found["diagnostics"], found
    outcomes = found["observations"]
    verified = next(row for row in outcomes if row["occurrence_id"] == key)
    assert verified["status"] == "verified" and verified["fixed_version"] == after, outcomes
    recovery = {row.get("job_status"): row for row in outcomes if row.get("step") == "reconcile"}
    assert recovery["interrupted"]["evidence_ref"] == f"rf-job/1/{existing['owner_job_id']}/source-1"
    assert recovery["unconfirmed"]["evidence_ref"] == capture_row["evidence_ref"]
    assert all(row["status"] == row["cost_state"] == "unknown" for row in recovery.values())
    report_id = digest(["report", RF, key, RF, ISSUE, after, "verified"])
    report = _run([*reports, "get-report", "--reports-dir", str(tmp / "reports"), report_id])["report"]
    assert report["payload"]["origin_owner"] == AUDIT and report["payload"]["original_occurrence_id"] == key
    assert report["payload"]["evidence_ref"] == verified["evidence_ref"]
    replay_capture = verified["evidence_ref"].split("/")[-1]
    assert _run([*audit_owner, "get-capture", "--role", "process", "--capture-id", replay_capture])["status"] == "succeeded"
    assert _run(recover)["feedback"] == found
    assert _run(audit_status)["status"] == "unconfirmed" and audit_starts.read_text().splitlines() == ["start"]
    old_jobs = _run([*status, "list-jobs"])["jobs"]
    assert len(old_jobs) == 1 and old_jobs[0]["owner_job_id"] == job_id
    assert old_jobs[0]["allowed_actions"] == ["reconcile"] and old_jobs[0]["stages"][0]["attempt_count"] == 1
    assert old_jobs[0]["cost_state"] == "unknown" and old_jobs[0]["cost"] is None
    with closing(sqlite3.connect(tmp / "host.sqlite")) as db:
        rows = [(json.loads(request), state, json.loads(receipt)) for request, state, receipt
                in db.execute("SELECT request, state, receipt FROM actions")]
    actions = Counter(request["kind"] for request, _, _ in rows)
    assert actions == {"observe": 3, "triage": 1, "repair": 1, "replay": 1, "report": 1}
    assert all(state == "done" for _, state, _ in rows)
    native = next(receipt.get("native") for request, _, receipt in rows if request["kind"] == "triage")
    if native_session:
        assert native["session_id"] == native_session and native["terminal"] and native["usage"]
    assert provider == {"/listing": 2}, provider
    return {"base": before, "fixed_version": after, "issue_ref": ISSUE, "original_rf_job_id": job_id,
            "ff_request_validator": _revision(args.ff_repo, "HEAD"),
            "original_rf_status": old_jobs[0]["status"], "original_rf_cost": None,
            "original_native_rf_attempts": 1, "original_allowed_actions_before": original["allowed_actions"],
            "original_allowed_actions_after": old_jobs[0]["allowed_actions"],
            "native_rf_recovery": recovery["interrupted"], "native_audit_recovery": recovery["unconfirmed"],
            "replay": verified, "owner_receipt_action": report_id, "control_actions": actions, "triage": native,
            "controller_force_stopped": bool(native_session), "new_agent_turns_after_restart": 0 if native_session else None,
            "loopback_metadata_before_recovery": 2, "loopback_metadata_during_recovery": 0,
            "downloads_during_recovery": 0, "paid_provider_calls_during_recovery": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rf-repo", type=Path, required=True)
    parser.add_argument("--ff-repo", type=Path, required=True)
    parser.add_argument("--audit-repo", type=Path, required=True)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--codex")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    counts = Counter()

    class Provider(BaseHTTPRequestHandler):
        def do_GET(self):
            counts[self.path] += 1
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"listing")

        def log_message(self, *args):
            pass

    with TemporaryDirectory(prefix="f4ra-") as root, ThreadingHTTPServer(("127.0.0.1", 0), Provider) as server:
        provider = Thread(target=server.serve_forever, daemon=True)
        provider.start()
        try:
            result = _probe(args, Path(root), counts, server.server_port)
        finally:
            server.shutdown()
            provider.join()
    result["temporary_directory_cleaned"] = not Path(root).exists()
    if args.receipt:
        _write(args.receipt, result)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
