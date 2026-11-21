"""Replay seven ordinary IQS failures against a committed revision, entirely offline.

    python probes/iqs.py ../invest-quick-scan --revision master

Run with the IQS test Python (including pytest). Read the JSON observations and
native outcomes together. A green native control verifies the previously
supported F4 scenario. Missing failure observations are findings of this probe.
"""

import argparse
import errno
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from zipfile import ZipFile


SELF = Path(__file__).resolve()
CONTROL_REPO = SELF.parents[4]
PYTHON = [sys.executable, "-B", "-X", "utf8"]
FIXTURE_PRIVATE_TEXT = "iqs-fixture-private-message-do-not-export"
JOB_SUFFIX = "1" * 32
SNAPSHOT_PATHS = (
    "pytest.ini", "schemas", "scripts/iqs_scan", "scripts/scan_result_check.py",
    "scripts/iqs_feedback_owner.py", "scripts/company_result_feedback.py",
    "scripts/dashboard_jobs.py", "scripts/dashboard_service.py",
    "tests/test_iqs_feedback_owner.py", "tests/fixtures/company_coverage",
)


def snapshot(checkout, revision, destination):
    git_env = dict(os.environ, GIT_ALLOW_PROTOCOL="file", GIT_NO_LAZY_FETCH="1",
                   GIT_TERMINAL_PROMPT="0")
    commit = subprocess.check_output(
        ["git", "rev-parse", "--verify", "--end-of-options", revision + "^{commit}"],
        cwd=checkout, text=True, env=git_env,
    ).strip()
    archive = subprocess.check_output(
        ["git", "archive", "--format=zip", commit, "--", *SNAPSHOT_PATHS], cwd=checkout, env=git_env,
    )
    with ZipFile(io.BytesIO(archive)) as files:
        for member in files.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError("Source archive member escapes the temporary checkout")
        files.extractall(destination)
    return commit


def offline_environment(scratch, source):
    # All children, including nested pytest CLI probes, inherit the same local-only
    # environment. None of the fault ports use a live owner or a model client.
    inherited = {"PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC"}
    env = {key: value for key, value in os.environ.items() if key.upper() in inherited}
    for key in ("HOME", "USERPROFILE", "TMP", "TEMP", "TMPDIR", "LOCALAPPDATA", "APPDATA"):
        env[key] = str(scratch)
    guard = scratch / "offline"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        'import sys\n'
        'def deny_network(event, args):\n'
        '    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:\n'
        '        raise RuntimeError("network disabled in the offline IQS probe")\n'
        'sys.addaudithook(deny_network)\n', encoding="utf8",
    )
    return dict(env, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
                PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                PYTHONPATH=os.pathsep.join(map(str, (guard, source / "scripts"))))


def python(args, cwd, env, *, check=True, timeout=45):
    return subprocess.run(
        [*PYTHON, *map(str, args)], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf8", timeout=timeout, check=check,
    )


def fault(*unused):
    try:
        raise PermissionError(errno.EACCES, FIXTURE_PRIVATE_TEXT)
    except PermissionError as cause:
        raise RuntimeError("fixture adapter stopped") from cause


def job_process(folder, mode):
    from dashboard_jobs import PreparationJobs

    marker = folder / "apply-count"

    class OfflinePreparer:
        def validate_selection(self, selection):
            pass

        def apply(self, selection):
            with marker.open("a", encoding="utf8") as stream:
                stream.write("started\n")
            if mode == "kill":
                time.sleep(120)
            fault()

    jobs = PreparationJobs(OfflinePreparer(), folder / "jobs", lambda result: {})
    selection = {"preview_id": "prepare_" + JOB_SUFFIX, "preview_token": "a" * 64}
    job_id = "prepjob_" + JOB_SUFFIX
    if mode == "fail":
        jobs.submit(selection)
        deadline = time.monotonic() + 8
        while jobs.get(job_id)["state"] in {"preparing", "registration_in_progress"}:
            if time.monotonic() >= deadline:
                raise RuntimeError("Fixture worker did not publish a terminal state")
            time.sleep(0.02)
    elif mode == "kill":
        jobs.submit(selection)
        time.sleep(120)
    result = jobs.get(job_id)
    text = json.dumps(result)
    return {
        "job_id": result["job_id"], "state": result["state"],
        "error_code": result.get("error_code"),
        "permission_cause_in_job": "PermissionError" in text,
        "private_fixture_text_in_job": FIXTURE_PRIVATE_TEXT in text,
        "apply_calls": len(marker.read_text(encoding="utf8").splitlines()),
    }


def http_process(folder):
    from dashboard_service import DashboardService

    instance = DashboardService(root=folder, prepare_factory=fault)
    status, reply = instance.dispatch("GET", "/api/product/prepare/status")
    return {"http": status, "code": reply["error"]["code"],
            "details_keys": sorted(reply["error"].get("details", {})),
            "private_fixture_text_in_response": FIXTURE_PRIVATE_TEXT in json.dumps(reply)}


def interrupt_after_apply(folder, source, env):
    command = [*PYTHON, str(SELF), "_job", str(folder), "kill"]
    with subprocess.Popen(command, cwd=source, env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as process:
        try:
            deadline = time.monotonic() + 10
            while not (folder / "apply-count").is_file():
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("Test worker did not reach the offline apply port")
                time.sleep(0.02)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)


def scan_document():
    answers = [
        {"question_id": f"Q{number}", "status": "insufficient_evidence",
         "problems": ["upstream_not_available"]} for number in range(1, 4)
    ]
    return json.dumps({
        "company": "fixture", "bank": {"question_count": len(answers), "package_id": "pkg"},
        "meta": {"calls": 0, "searches": len(answers)}, "answers": answers,
    })


def scan_case(name, run, source, env):
    run.mkdir()
    if name != "missing-files":
        answers = "{" if name == "corrupt-answers" else scan_document()
        (run / "answers.json").write_text(answers, encoding="utf8")
        (run / "run-log.json").write_text("[]", encoding="utf8")
        (run / "index.html").write_text("<html></html>", encoding="utf8")
    response = python(["scripts/scan_result_check.py", "--run", run], source, env, check=False)
    report = json.loads(response.stdout) if response.stdout.strip() else {}
    error_type = response.stderr.splitlines()[-1].split(":")[0] if response.stderr.strip() else None
    return {"exit": response.returncode, "business_ok": report.get("ok"),
            "problems": report.get("problems"), "stderr_type": error_type}


def unavailable_owner(folder, source, env):
    empty = folder / "owner"
    empty.mkdir()
    workspace = folder / "workspace"
    workspace.mkdir()
    sample = source / "tests/fixtures/company_coverage/result-partial-claiming-complete.json"
    entity = json.loads(sample.read_text(encoding="utf8"))["entity_id"]
    command = ["scripts/company_result_feedback.py", "--stockwiki-root", empty,
               "--workspace-root", workspace, "--entity", entity, "--out", env["RESEARCH_FEEDBACK_OUT"],
               "--run-id", env["RESEARCH_FEEDBACK_RUN_ID"]]
    response = python(command, source, env, check=False)
    return {"exit": response.returncode, "reply": json.loads(response.stdout)}


def cold_feedback(sidecar, env):
    response = python(["-m", "tools.feedback_loop", "plan", sidecar], CONTROL_REPO, env)
    plan = json.loads(response.stdout)
    fields = ("occurrence_id", "check_id", "disposition", "actual", "issue_key",
              "run_id", "attempt_id", "evidence_ref", "details_ref")
    return {
        "file_exists": sidecar.is_file(),
        "rows": [{key: observation[key] for key in fields if key in observation}
                 for observation in plan["observations"]],
        "intake_diagnostics": plan["diagnostics"],
        "private_fixture_text_in_feedback": FIXTURE_PRIVATE_TEXT in response.stdout,
    }


def audit(checkout, revision, scratch):
    source = scratch / "pinned"
    commit = snapshot(checkout, revision, source)
    plain = offline_environment(scratch, source)
    runs = scratch / "runs"
    runs.mkdir()
    results = {}
    scans = ("missing-files", "corrupt-answers", "all-failed")
    for name in (*scans, "owner-cannot-start", "prep-fail", "prep-kill", "api-server"):
        folder = scratch / name
        folder.mkdir()
        sidecar = folder / "observations.jsonl"
        env = dict(plain, RESEARCH_FEEDBACK_OUT=str(sidecar), RESEARCH_FEEDBACK_RUN_ID=name,
                   RESEARCH_FEEDBACK_ATTEMPT_ID="attempt-fixture", IQS_FEEDBACK_RUNS_ROOT=str(runs))
        if name in scans:
            native = scan_case(name, runs / name, source, env)
        elif name == "owner-cannot-start":
            native = unavailable_owner(folder, source, env)
        elif name == "api-server":
            native = json.loads(python([SELF, "_http", folder], source, env).stdout)
        else:
            if name == "prep-kill":
                interrupt_after_apply(folder, source, env)
            else:
                python([SELF, "_job", folder, "fail"], source, env)
            # Only read the original job in this new process; never resubmit it.
            native = json.loads(python([SELF, "_job", folder, "get"], source, env).stdout)
        results[name] = {"native": native, "f4": cold_feedback(sidecar, env)}
    control = python(["-m", "pytest", "-q", "--disable-warnings", "-p", "no:cacheprovider",
                      "-c", "pytest.ini", "--confcutdir", source,
                      "--basetemp", scratch / "pytest", "tests/test_iqs_feedback_owner.py"],
                     source, plain, check=False, timeout=90)
    return {"revision": commit, "cases": results, "native_control": {
        "exit": control.returncode, "pytest": control.stdout.strip(),
        "stderr": control.stderr.strip(),
    }}


def main():
    args = sys.argv[1:]
    if args and args[0] == "_job":
        print(json.dumps(job_process(Path(args[1]), args[2])))
        return 0
    if args and args[0] == "_http":
        print(json.dumps(http_process(Path(args[1]))))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", nargs="?", type=Path,
                        default=CONTROL_REPO.parent / "invest-quick-scan")
    parser.add_argument("--revision", default="HEAD", help="Committed IQS revision to audit")
    parser.add_argument("--temp-parent", type=Path, help="Existing short directory for test scratch space")
    options = parser.parse_args(args)
    with TemporaryDirectory(prefix="iqsf4-", dir=options.temp_parent) as temporary:
        report = audit(options.checkout.resolve(), options.revision, Path(temporary).resolve())
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return report["native_control"]["exit"]


if __name__ == "__main__":
    raise SystemExit(main())
