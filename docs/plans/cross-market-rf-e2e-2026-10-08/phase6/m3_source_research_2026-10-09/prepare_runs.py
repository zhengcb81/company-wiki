"""One-time M3 native initialization; no source acquisition or model call.

Reuses each existing isolated source owner, creates disjoint recorder/AUTO/work
and research paths, and retains old evidence and cumulative native accounting.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

NODE = Path(__file__).resolve().parent
PROJECT = NODE.parents[4]
PHASE = NODE.parent
AUDIT = PROJECT.parent / "revenue-forecast-audit"
SKILLS = Path.home() / ".agents/skills"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def fingerprint(path):
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
            "byte_size": len(data), "mtime_ns": path.stat().st_mtime_ns}


def main():
    assert PROJECT.name == "company-wiki" and AUDIT.is_dir()
    assert not (NODE / "cohort.json").exists(), "inspect existing journal; do not initialize another cohort"
    sys.path[:0] = [str(PROJECT / "src"), str(PROJECT / "scripts")]
    from config import Config
    from company_wiki.automation.narrative_http_model import model_options_from_config

    budget = load(NODE / "budget_observation.json")
    assert not budget["newly_unknown_reservations"]
    assert budget["remaining_tokens"] >= 360000
    assert budget["remaining_micro_usd_after_known_and_FX"] >= 6000000
    options = model_options_from_config(Config.load(llm_provider="deepseek").llm)
    assert options["model_id"] == "deepseek-flash" and os.environ.get(options["api_key_env"])
    started = datetime.now(timezone.utc)
    deadline_monotonic = time.monotonic() + 7200
    tag = started.strftime("%Y%m%dT%H%M%S")
    runtime = {"observed_at": started.isoformat(), "repo_heads": {}, "installed_files": [],
               "normalized_installed_drifts": [], "credential_values_logged": False,
               "actual_model_options": options, "provider": "deepseek"}
    for name in ["company-wiki", "revenue-forecast", "filing-fetch", "revenue-forecast-audit",
                 "earnings-transcripts/earnings-transcripts"]:
        runtime["repo_heads"][name] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT.parent / name, text=True).strip()
    for name in ["revenue-forecast", "filing-fetch", "revenue-forecast-audit"]:
        skill = SKILLS / name
        source = PROJECT.parent / name
        if name == "revenue-forecast-audit":
            source = source / "skills" / name
        paths = [skill / "SKILL.md"]
        for directory in ["scripts", "references", "agents", "schemas"]:
            paths.extend((skill / directory).rglob("*"))
        for path in sorted(set(paths)):
            if not path.is_file() or path.suffix not in {".py", ".md", ".json"} or "__pycache__" in path.parts:
                continue
            row = fingerprint(path)
            relative = path.relative_to(skill)
            counterpart = source / relative
            if counterpart.is_file():
                equal = path.read_bytes().replace(b"\r\n", b"\n") == counterpart.read_bytes().replace(b"\r\n", b"\n")
                row["normalized_repository_match"] = equal
                if not equal:
                    runtime["normalized_installed_drifts"].append(str(path))
            runtime["installed_files"].append(row)
    save(NODE / "runtime_observation.json", runtime)
    assert not runtime["normalized_installed_drifts"], "fix measured selected installation drift before execution"
    runtime["protected_production_configs"] = [fingerprint(PROJECT / p) for p in
        ["config.yaml", "config/source_catalog.yaml", "config/source_acquisition.yaml", "config/local_ocr.json"]]
    save(NODE / "runtime_observation.json", runtime)
    material = load(PHASE / "fresh_root_implementation_2026-10-09/w09_material_coverage/initial_inventory.json")
    companies = material["companies"]
    ledger_by_company = {row["company"]: row for row in budget["existing_reservations"]}
    initial = []
    cohort = {"status": "PREPARING_NOT_EXECUTED", "started_at": started.isoformat(),
              "cohort": [], "provider_model_calls": 0, "old_evidence_overwritten": False}
    save(NODE / "cohort.json", cohort)
    for label, company in [("cn-688012", "中微公司"), ("hk-00700", "腾讯控股"), ("us-msft", "Microsoft")]:
        prior = AUDIT / "runs" / ("fresh-20261009T065028-" + label)
        scope = load(prior / "scope.json")
        owner = Path(scope["isolated_roots"]["root"]).resolve()
        assert owner.is_dir() and owner.parent.name.startswith("mFresh-")
        new = owner / "m3" / tag
        assert not new.exists()
        protected = [fingerprint(p) for p in Path(scope["isolated_roots"]["company_raw"]).rglob("*") if p.is_file()]
        protected.extend(fingerprint(Path(p["path"])) for p in scope["effective_config_refs"])
        initial.append({"company": label, "source_owner": str(owner), "protected_existing_files": protected,
                        "new_execution_root": str(new), "new_execution_root_existed": False,
                        "catalog_policy": "existing isolated public source owner reused; versions append, originals immutable"})
        new.mkdir(parents=True)
        for directory in ["auto", "work", "temp", "rf/output", "rf/registry"]:
            (new / directory).mkdir(parents=True)
        run_id = "m3-" + tag + "-" + label
        run = AUDIT / "runs" / run_id
        assert not run.exists()
        command = [sys.executable, "-X", "utf8", "-B", str(SKILLS / "revenue-forecast-audit/scripts/audit_run.py"),
                   "init", "--root", str(AUDIT / "runs"), "--company", company, "--as-of", "2026-10-08", "--run-id", run_id]
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=30)
        save(NODE / (label + ".init.json"), {"command": command, "exit_code": proc.returncode,
                                            "stdout": proc.stdout, "stderr": proc.stderr})
        proc.check_returncode()
        reservations = ledger_by_company[label]["reservations"]
        spent_tokens = sum(r["input_tokens"] + r["output_tokens"] for r in reservations if r["usage_status"] == "known")
        spent_money = sum(r["estimated_micro_usd"] for r in reservations if r["usage_status"] == "known")
        entry = next(row for row in companies if row["run_id"].endswith(label))
        scope.update(status="READY_FOR_M3_EXECUTOR", run_id=run_id, audit_run=str(run),
                     attempt_id="m3-initial", mode="fresh_revenue_research", storage_only=False,
                     executor_started=False, AUTO_initialized=False, forecast_version=run_id,
                     execution_dir=str(run / "execution"), roles_executor_dir=str(run / "roles/executor"),
                     runtime_manifest=str(NODE / "runtime_observation.json"), repo_heads_observed=runtime["repo_heads"],
                     source_refs=entry["existing_sources"],
                     source_coverage_handoff={"inventory": str(NODE / (label + ".material_handoff.json")),
                                              "state": "discovery not actual acquisition/consumption"},
                     known_source_gaps=entry["bounded_existing_gaps"], future_download_targets=entry["declared_future_targets"])
        scope["isolated_roots"].update(automation_db=str(new / "auto/narrative.sqlite3"), work_dir=str(new / "work"),
            temp=str(new / "temp"), rf_registry=str(new / "rf/registry"), rf_output=str(new / "rf/output"))
        scope["process_environment"].update(TEMP=str(new / "temp"), TMP=str(new / "temp"))
        scope["rf_registry_file"] = str(new / "rf/registry/publication.jsonl")
        scope["narrative_paths"].update(automation_db=scope["isolated_roots"]["automation_db"], work_dir=scope["isolated_roots"]["work_dir"])
        scope["supplier"].update(actual_model_options=options, credential_env_present=True,
            pricing=budget["pricing_conservative_existing"], pricing_primary_rechecked_at=started.isoformat())
        scope["budget_source"] = {"native_mother_snapshot": str(NODE / "budget_observation.json"),
            "company_max_tokens": 120000-spent_tokens, "company_max_micro_usd": 2000000-spent_money,
            "company_prior_tokens": spent_tokens, "company_prior_micro_usd": spent_money,
            "original_company_cap_not_reset": True, "allocation_includes_all_new_paid_calls": True,
            "unknown_calls_not_automatically_retried": True}
        scope["deadline"] = {"started_at": started.isoformat(), "deadline_at": (started+timedelta(seconds=7200)).isoformat(),
                             "deadline_monotonic": deadline_monotonic, "total_seconds": 7200}
        scope["initial_environment_inventory"] = str(NODE / "initial_environment_inventory.json")
        scope["owner_boundary"] = "Own new audit roles/executor/execution and own new M3 AUTO/work/registry/output; existing own CWP source owner via public APIs only; no code/config/old execution/PWF/install/other company writes"
        scope["old_answers"] = "Do not read sealed old forecasts/drafts/reviewer answers to construct new research; use source-only material handoff"
        save(run / "scope.json", scope)
        save(NODE / (label + ".material_handoff.json"), {
            "identity": entry["identity"], "existing_sources": entry["existing_sources"],
            "source_tasks": [row for row in material["work_items"] if row["company"] == entry["identity"]["canonical_name"] or row["id"].startswith(label.split('-')[0].upper())],
            "other_ledger_sources": entry["other_ledger_sources"], "fixed_cutoff": "2026-10-08", "discovery_is_not_import": True})
        cohort["cohort"].append({"company": label, "run_id": run_id, "run": str(run), "scope": str(run / "scope.json"),
                                 "new_execution_root": str(new), "executor_started": False,
                                 "company_remaining_tokens": 120000-spent_tokens, "company_remaining_micro_usd": 2000000-spent_money})
        save(NODE / "initial_environment_inventory.json", initial)
        save(NODE / "cohort.json", cohort)
    cohort["status"] = "THREE_NATIVE_RUNS_READY_EXECUTORS_NOT_STARTED"
    save(NODE / "cohort.json", cohort)
    print(json.dumps(cohort, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
