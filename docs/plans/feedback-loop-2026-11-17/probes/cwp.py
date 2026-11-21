"""Cold-read CWP failure observations in a throwaway local source catalog.

Run with the company-wiki test interpreter. Optionally pass the deployed CWP
runtime root. The catalog fixture always comes from the source checkout.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


REPO = Path(__file__).resolve().parents[4]
PUBLIC = "company_wiki.source_catalog."
PROJECTOR = "tools.document_understanding_benchmark.phase_c_feedback"


def audit(runtime, root):
    env = {key: os.environ[key] for key in (
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "SYSTEMDRIVE",
        "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "COMSPEC",
    ) if key in os.environ}
    env["PYTHONPATH"] = os.pathsep.join(map(str, (
        runtime / "src", runtime, REPO / "tests", REPO / "tests/unit", REPO)))
    env["PYTHONUTF8"] = "1"
    output = {}

    def run(args, *, payload=None, options=None):
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", *map(str, args)], cwd=root,
            env={**env, **(options or {})}, capture_output=True, encoding="utf-8",
            input=json.dumps(payload) if payload is not None else "", timeout=60,
        )

    def invoke(name, module, args=(), payload=None, sidecar=None):
        sidecar = sidecar or (root / (name + ".jsonl"))
        options = {"RESEARCH_FEEDBACK_OUT": str(sidecar), "RESEARCH_FEEDBACK_RUN_ID": name,
                   "RESEARCH_FEEDBACK_ATTEMPT_ID": "one"}
        result = run(["-m", module, *args], payload=payload, options=options)
        body = {}
        for stream in (result.stdout, result.stderr):
            try:
                body = json.loads(stream)
                break
            except ValueError:
                continue
        plan = run(["-m", "tools.feedback_loop", "plan", sidecar])
        plan.check_returncode()
        rows = json.loads(plan.stdout)["observations"]
        output[name] = {"exit": result.returncode,
                        "native": {k: body[k] for k in ("status", "reason", "error", "schema_version") if k in body},
                        "items": [(item.get("state", item.get("status")), item.get("reason_codes", item.get("errors")))
                                  for item in body.get("items", [])],
                        "observed": [(row["check_id"], row["disposition"]) for row in rows]}
        if not body and result.stderr.strip():
            output[name]["error_type"] = result.stderr.strip().splitlines()[-1].split(":", 1)[0]
        return body

    seed = run(["-c",
                "import json; from pathlib import Path; from support.sr_cwp_fixtures import build_catalog; "
                "s=build_catalog(Path.cwd()); r=s.refs['annual-report.txt'].to_dict(); "
                "s.catalog.close(); print(json.dumps(r))"])
    seed.check_returncode()
    ref = json.loads(seed.stdout.strip().splitlines()[-1])
    config = root / "config/catalog.json"
    # Damage only the test copy after the real catalog has registered its bytes.
    (root / "companies/Acme/raw/annual-report.txt").write_bytes(b"changed bytes")
    invoke("exact-read", PUBLIC + "source_reader_cli", [
        "--config", config, "--document-id", ref["document_id"], "--source-id", ref["source_id"],
        "--content-sha256", ref["content_sha256"]])
    invoke("invalid-query", PUBLIC + "source_query_cli", ["--config", config], [])
    invoke("ensure-missing-config", PUBLIC + "cli", ["--config", root / "absent.json", "ensure",
           "--entity", "fixture", "--document-kind", "annual_report", "--as-of-date", "2026-01-01"])
    read = {"schema_version": "cwp-incremental-read-request/1", "reading_level": "local",
            "run_id": "damaged-original", "sources": [ref], "limits": None}
    scheduled = invoke("scheduled-read", PUBLIC + "cli", [
        "read-incremental", "--config", config, "--request-stdin"], read)
    recovered = invoke("scheduled-status", PUBLIC + "cli", [
        "read-incremental-status", "--config", config, "--request-stdin"],
        {"schema_version": "cwp-incremental-read-status-request/1", "run_id": read["run_id"]})
    output["scheduled-cold-comparison"] = {"same_items": scheduled.get("items") == recovered.get("items"),
                                          "model_requests": recovered.get("usage", {}).get("model_requests")}
    invoke("dayu-input", PUBLIC + "dayu_sdk_cli", ["--market", "US", "--adapter-name", "probe",
           "--adapter-version", "1", "--provider-state-root", root / "provider", "discover"], [])

    worker_dir = root / "worker"
    worker_dir.mkdir()
    worker_out = root / "worker.jsonl"
    fault = run(["-c", "import sys; from pathlib import Path; from test_automation_worker import "
                 "test_worker_handler_exception_dead_letters as inject; inject(Path(sys.argv[1]))", worker_dir],
                options={"RESEARCH_FEEDBACK_OUT": str(worker_out), "RESEARCH_FEEDBACK_RUN_ID": "worker-fault",
                         "RESEARCH_FEEDBACK_ATTEMPT_ID": "one"})
    fault.check_returncode()
    cold = run(["-c", "import json,sys; from pathlib import Path; from company_wiki.automation.store import "
                "AutomationStore; s=AutomationStore(Path(sys.argv[1])); job=s.get_job('job-auto4-001'); "
                "print(json.dumps([job.status.value, job.last_error_code, job.last_error_detail,"
                "len(s.list_attempts(job.job_id))]))", worker_dir / "automation.db"])
    cold.check_returncode()
    worker_plan = run(["-m", "tools.feedback_loop", "plan", worker_out])
    worker_plan.check_returncode()
    output["worker-handler-crash"] = {
        "native": json.loads(cold.stdout), "observed": json.loads(worker_plan.stdout)["observations"]}

    for version in (1, 2):
        run_id = f"batch-v{version}"
        request = {"schema_version": f"narrative-batch-request/{version}", "run_id": run_id, "profile": "P2",
                   "max_seconds": 20, "max_tokens": 1000, "max_cost_usd": "0",
                   "model": {"model_id": "fixture", "endpoint": "http://127.0.0.1:1/v1/chat/completions",
                             "api_key_env": "F4_FIXTURE_UNUSED", "allow_local_http": True},
                   "pricing": {"version": "fixture", "input_micro_usd_per_million_tokens": 1000000,
                               "output_micro_usd_per_million_tokens": 1000000}}
        if version == 1:
            request["sources"] = [ref]
        else:
            request["items"] = [{"kind": "raw", "source_ref": ref}]
        path = root / (run_id + ".json")
        path.write_text(json.dumps(request), encoding="utf8")
        result = invoke(run_id, "company_wiki.automation.narrative_batch_cli", [
            "--project-root", root, "--catalog-config", config, "--automation-db", root / (run_id + ".sqlite"),
            "--work-dir", root / "work", "--request", path])
        if result.get("schema_version") != f"narrative-batch-result/{version}" or result.get("run_id") != run_id:
            raise RuntimeError(f"No matching native receipt for {run_id}")
        for status in ("failed", "storage_exhausted"):
            # Feed the saved native result and a controlled alternate disposition through
            # the public Phase C projection. Keep them distinct in the report.
            label = f"project-{version}-{status}"
            receipt = root / (label + ".json")
            receipt.write_text(json.dumps({"states": [{"run_id": run_id,
                               "receipt": {**result, "status": status}, "native_usage": []}]}), encoding="utf8")
            out = root / (label + ".jsonl")
            invoke(label, PROJECTOR, [receipt, "--out", out], sidecar=out)
            output[label]["status_substituted"] = result.get("status") != status
    return output


if __name__ == "__main__":
    runtime = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO
    with TemporaryDirectory(prefix="cwf4-") as directory:
        print(json.dumps(audit(runtime, Path(directory)), indent=2))
