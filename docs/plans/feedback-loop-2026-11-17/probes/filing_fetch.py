"""Compare native filing-fetch failures with F4 observations from fresh processes.

Run with Python and an optional filing-fetch checkout path. Results describe the
code under test, so fixing a missing observation does not invalidate the probe.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


CWP = Path(__file__).resolve().parents[4]
PYTHON = [sys.executable, "-B", "-X", "utf8"]


def census(owner, work):
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE",
    }}
    # Keep user-level fallbacks inside the fixture and prohibit network even if
    # a later implementation attempts to resolve the invented company.
    env.update({name: str(work) for name in ("TEMP", "TMP", "HOME", "USERPROFILE",
                                             "APPDATA", "LOCALAPPDATA", "XDG_STATE_HOME")})
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(work))
    (work / "sitecustomize.py").write_text(
        "import sys\ndef offline(event, args):\n"
        "    if event in ('socket.connect', 'socket.getaddrinfo'):\n"
        "        raise RuntimeError('network disabled in FF failure census')\n"
        "sys.addaudithook(offline)\n", encoding="ascii")
    jobs = ["--jobs-dir", str(work / "jobs")]
    results = []

    def invoke(case, tool, arguments=(), body="", with_sink=True):
        sidecar = work / f"{case}.jsonl"
        labels = {"RESEARCH_FEEDBACK_RUN_ID": case, "RESEARCH_FEEDBACK_ATTEMPT_ID": "first"}
        if with_sink:
            labels["RESEARCH_FEEDBACK_OUT"] = str(sidecar)
        source = subprocess.run(
            [*PYTHON, str(owner / "scripts" / f"{tool}.py"), *arguments], cwd=work,
            input=body.encode("utf-8"), capture_output=True, env={**env, **labels}, timeout=20,
        )
        view = json.loads(source.stdout) if source.stdout.strip() else {}
        plan = subprocess.run(
            [*PYTHON, "-m", "tools.feedback_loop", "plan", str(sidecar)], cwd=CWP,
            env=env, capture_output=True, check=True, timeout=15,
        )
        batch = json.loads(plan.stdout)
        rows = batch["observations"]
        job = view.get("job") or {}
        error = view.get("error") if isinstance(view.get("error"), dict) else {}
        results.append({
            "case": case, "exit": source.returncode, "stderr_present": bool(source.stderr),
            "facade_status": view.get("status"), "facade_code": error.get("code", view.get("error_code")),
            "job_status": job.get("status"), "job_error": (job.get("error") or {}).get("code"),
            "execution_count": job.get("execution_count"), "cost_state": job.get("cost_state"),
            "history_items": len(view["items"]) if "items" in view else None,
            "sidecar": sidecar.is_file(),
            "observations": [[r["check_id"], r["actual"], r["disposition"], r.get("refusal_code")] for r in rows],
            "diagnostics": [d["code"] for d in batch["diagnostics"]],
        })
        return view

    invoke("short-timeout", "fetch_filing", ["--timeout-seconds", "0"])
    invoke("short-invalid-argument", "fetch_filing", ["--not-a-real-option"])
    invoke("short-invalid-json", "fetch_filing", body="{")
    invoke("short-invalid-json-unwrapped", "fetch_filing", body="{", with_sink=False)
    invoke("statements-invalid-json", "fetch_statements", body="{")
    invoke("scheduler-invalid-request", "ff_scheduled_refresh", [*jobs, "configure", "--request-stdin"], "[]")
    invoke("scheduler-history", "ff_scheduled_refresh", [*jobs, "runs"])
    invoke("job-invalid-submit", "ff_job", [*jobs, "submit"], "[]")
    invoke("job-missing", "ff_job", [*jobs, "get_status", "--owner-job-id", "ffjob-000000000000"])

    request = {
        "schema_version": "2.0", "company_query": "Audit Fixture", "document_kind": "annual_report",
        "fiscal_year": 2025, "as_of_date": "2026-07-18", "filing_intent": "reuse_only", "mode": "exact",
    }
    submit = {"schema_version": "ff-job/1", "command_id": "audit-ff", "kind": "filing.acquire",
              "idempotency_key": "audit-ff", "request": request}
    job_id = invoke("job-submit", "ff_job", [*jobs, "submit"], json.dumps(submit))["owner_job_id"]
    invoke("job-run-missing-config", "ff_job", [*jobs, "run", "--owner-job-id", job_id,
                                                "--config", str(work / "missing.json")])
    readback = invoke("job-cold-read", "ff_job", [*jobs, "get_status", "--owner-job-id", job_id])
    observed_job = readback["job"]
    if (readback["owner_job_id"] != job_id or observed_job["status"] != "failed"
            or observed_job["execution_count"] != 1):
        raise RuntimeError("fixture did not reproduce a single failed native job on cold read")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", nargs="?", type=Path, default=CWP.parent / "filing-fetch")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="f4-ff-audit-") as fixture:
        print(json.dumps(census(args.checkout.resolve(), Path(fixture)), indent=2))
