"""MAIN one-time observations and native audit initialization, not a permit gate.

Creates three fresh, disjoint research runs. No provider/model/parse operation.
Refuses an existing run rather than overwriting historical evidence.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[5]
PHASE = Path(__file__).resolve().parent.parent
USER = PROJECT.parent.parent
AUDIT_PROJECT = PROJECT.parent / "revenue-forecast-audit"
SKILLS = USER / ".agents/skills"
PY = Path(sys.executable)


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def identity(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_size": len(raw)}


def main():
    sys.path[:0] = [str(PROJECT / "src"), str(PROJECT / "scripts")]
    from company_wiki.automation.narrative_http_model import model_options_from_config
    from config import Config

    budget = load(PHASE / "main_budget_preparation.json")
    assert budget["remaining_tokens"] >= 360000
    assert budget["remaining_micro_usd_after_fx"] >= 6000000
    options = model_options_from_config(Config.load(llm_provider="deepseek").llm)
    assert options["model_id"] == "deepseek-flash"
    assert os.environ.get(options["api_key_env"])
    started = datetime.now(timezone.utc)
    deadline = time.monotonic() + 7200
    repo_heads = {}
    for key, name in [("CWP", "company-wiki"), ("RF", "revenue-forecast"),
                      ("FF", "filing-fetch"), ("ET", "earnings-transcripts/earnings-transcripts")]:
        repo_heads[key] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT.parent / name,
            text=True, encoding="utf-8").strip()
    runtime_files = []
    for name in ["revenue-forecast", "filing-fetch", "revenue-forecast-audit"]:
        package = SKILLS / name
        paths = [package / "SKILL.md"]
        for directory in ["scripts", "references", "agents"]:
            paths.extend((package / directory).rglob("*"))
        for path in sorted(paths):
            if path.is_file() and path.suffix in {".py", ".md"} and "__pycache__" not in path.parts:
                runtime_files.append(identity(path))
    protected = [identity(PROJECT / name) for name in [
        "config.yaml", "config/source_catalog.yaml", "config/source_acquisition.yaml", "config/local_ocr.json"]]
    pricing = {"version": "deepseek-cn-full-peak-fx-floor6-proxy-2026-10-06",
               "input_micro_usd_per_million_tokens": 333334,
               "output_micro_usd_per_million_tokens": 1333334}
    cohort = []
    for label, company, base, currency, fy_end in [
            ("CN-688012", "中微公司", 2025, "CNY", "12-31"),
            ("HK-00700", "腾讯控股", 2025, "CNY", "12-31"),
            ("US-MSFT", "Microsoft", 2026, "USD", "06-30")]:
        draft = load(PHASE / "fresh_cohort_environment/environments" / f"{label}.scope.draft.json")
        root = Path(draft["isolated_roots"]["root"])
        assert root.is_dir() and not Path(draft["isolated_roots"]["automation_db"]).exists()
        for ref in draft["effective_config_refs"]:
            assert identity(Path(ref["path"]))["sha256"] == ref["sha256"]
        run_id = f"fresh-{started.strftime('%Y%m%dT%H%M%S')}-{label.lower()}"
        run = AUDIT_PROJECT / "runs" / run_id
        assert not run.exists()
        p = subprocess.run([str(PY), "-X", "utf8", "-B", str(SKILLS / "revenue-forecast-audit/scripts/audit_run.py"),
            "init", "--root", str(AUDIT_PROJECT / "runs"), "--company", company,
            "--as-of", "2026-10-08", "--run-id", run_id], capture_output=True,
            text=True, encoding="utf-8", timeout=30)
        save(Path(__file__).parent / "launched" / f"{label}.init.json",
             {"argv_role": "native audit init", "exit_code": p.returncode,
              "stdout": p.stdout, "stderr": p.stderr, "run_id": run_id})
        p.check_returncode()
        scope = dict(draft)
        scope.update({"schema_version": "1.0", "status": "READY_FOR_FRESH_EXECUTOR",
                      "storage_only": False, "mode": "fresh_revenue_research",
                      "run_id": run_id, "audit_run": str(run), "attempt_id": "initial",
                      "execution_dir": str(run / "execution"), "roles_executor_dir": str(run / "roles/executor"),
                      "as_of_date": "2026-10-08", "base_year": base,
                      "forecast_years": [base+1, base+2, base+3], "currency": currency,
                      "unit": "million", "fiscal_year_end": fy_end,
                      "forecast_version": run_id, "forecast_horizon": 3,
                      "repo_heads_observed": repo_heads,
                      "rf_registry_file": str(root / "rf/registry/publication.jsonl"),
                      "runtime_manifest": str(Path(__file__).parent / "launched/runtime_observation.json"),
                      "supplier": {"provider": "deepseek", "profile": "P1", "actual_model_options": options,
                                   "credential_env_present": True, "pricing": pricing,
                                   "pricing_provenance": "Existing versioned R3 conservative CNY full peak proxy, not invoice; current primary USD peak rates 0.3/1.2 are below 0.333334/1.333334; no cached/discount/free assumption",
                                   "pricing_primary_url": "https://api-docs.deepseek.com/quick_start/pricing/"},
                      "budget_source": {"native_mother_snapshot": str(PHASE / "main_budget_preparation.json"),
                                        "baseline": budget, "company_max_tokens": 120000,
                                        "company_max_micro_usd": 2000000,
                                        "allocation_includes_all_paid_calls": True,
                                        "unknown_calls_not_automatically_retried": True},
                      "deadline": {"started_at": started.isoformat(),
                                   "deadline_at": (started+timedelta(seconds=7200)).isoformat(),
                                   "deadline_monotonic": deadline, "total_seconds": 7200},
                      "max_log_bytes": 1048576,
                      "acquisition_limits": {"max_bytes": 41943040, "timeout_seconds": 180, "max_cost_usd": "0.00"},
                      "source_reader_receipt_default": "2.1", "availability_receipt_opt_in": "2.2",
                      "narrative_caps": {"max_final_bytes": 2097152, "max_persistent_bytes": 33554432,
                                         "max_scratch_bytes": 67108864},
                      "authority": "Existing permanent source externalization and configured-provider authorization; no further human permit. Normal tool review remains enforced.",
                      "owner_boundary": "Executor owns roles/executor, execution and matching mFresh company; no repository code/config/PWF/install/other-agent writes. No self-review. Retain raw for all four reviews.",
                      "old_answers": "Do not read sealed prior company forecast inputs/reports/reviewer answers to construct fresh research."})
        save(run / "scope.json", scope)
        cohort.append({"company": label, "run_id": run_id, "run": str(run),
                       "scope": str(run / "scope.json"), "executor_started": False})
    save(Path(__file__).parent / "launched/runtime_observation.json",
         {"repo_heads_observed": repo_heads, "installed_files": runtime_files,
          "protected_production_configs": protected, "credential_value_logged": False})
    save(Path(__file__).parent / "launched/cohort.json",
         {"status": "SCOPES_FROZEN_EXECUTORS_NOT_STARTED", "cohort": cohort,
          "baseline": budget, "allocated_tokens": 360000, "allocated_micro_usd": 6000000,
          "provider": "deepseek", "model": options["model_id"], "new_provider_calls": 0})
    print(json.dumps(cohort, ensure_ascii=False))


if __name__ == "__main__":
    main()
