"""Independent read-only checks of the recorded W07 real lifecycle; no API calls."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[5]
# The checker lives under docs/plans/<plan>/review/<independent-evidence>/.
if not (ROOT / "src/company_wiki").is_dir():
    raise RuntimeError("checker composition root mismatch")
REVIEW = Path(__file__).resolve().parent
PACKET = REVIEW.parent / "r1-w07-live-20261022"
AUTHOR = json.loads((REVIEW.parent / "r1-w07-live-20261022.json").read_text(encoding="utf-8"))
LIVE = ROOT / ".planning/r1-w07-live/20261022-annual-090-reallocated"
RECEIPTS = LIVE / "receipts"
AUDIT = Path("C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec")
CODE_HEAD = "755e87cd85de7ca02bcb88b8e34f79c35f3763f3"
checks = []
bindings = {}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    data = path.read_bytes()
    result = hashlib.sha256(data).hexdigest()
    bindings[str(path)] = {"bytes": len(data), "sha256": result}
    return result


def check(name, condition, observed=None):
    checks.append({"check": name, "passed": bool(condition), "observed": observed})
    if not condition:
        raise AssertionError(name)


def ro(path):
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


def same_paid(rows):
    fields = ("attempt_id", "run_id", "job_id", "request_sha256", "usage_status",
              "input_tokens", "output_tokens", "estimated_micro_usd",
              "response_sha256", "paid_response_pin")
    return [{field: row[field] for field in fields} for row in rows]


def main():
    check("author_code_head", AUTHOR["code_head"] == CODE_HEAD)
    for item in AUTHOR["artifacts"]:
        path = PACKET / item["path"]
        check("packet_binding:" + item["path"],
              path.stat().st_size == item["bytes"] and sha(path) == item["sha256"])
    ci = load(PACKET / "w07-ci-success.json")
    check("recorded_ci_success", ci["id"] == 39847355377 and ci["head_sha"] == CODE_HEAD
          and ci["status"] == "completed" and ci["conclusion"] == "success", ci)
    sha(PACKET / "w07-ci-success.json")
    # Bind the actual observation implementation to the published commit,
    # without running it or its model/client constructors.
    env = os.environ.copy()
    for key in tuple(env):
        if key.startswith("GIT_"):
            env.pop(key)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    source_paths = [
        "tools/document_understanding_benchmark/holdout_acceptance.py",
        "tools/document_understanding_benchmark/holdout_acceptance_launcher.py",
        "tools/document_understanding_benchmark/holdout_acceptance_observer.py",
        "tools/document_understanding_benchmark/holdout_acceptance_contracts.py",
        "src/company_wiki/automation/narrative_model_caller.py",
        "src/company_wiki/automation/narrative_http_model.py",
        "src/company_wiki/automation/narrative_paid_response.py",
    ]
    for rel in source_paths:
        committed = subprocess.run(["git", "show", CODE_HEAD + ":" + rel], cwd=ROOT,
                                   env=env, check=True, capture_output=True).stdout
        physical = (ROOT / rel).read_bytes()
        check("published_source:" + rel, physical.replace(b"\r\n", b"\n") == committed,
              {"committed_lf_sha256": hashlib.sha256(committed).hexdigest(),
               "physical_sha256": sha(ROOT / rel)})

    spec = load(LIVE / "controller-spec.json")
    frozen_spec = load(PACKET / "controller-spec.json")
    check("live_spec_matches_packet", spec == frozen_spec)
    events = [json.loads(line) for line in (RECEIPTS / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    sha(RECEIPTS / "events.jsonl")
    by_event = {name: [row for row in events if row["event"] == name]
                for name in {row["event"] for row in events}}
    posts = by_event.get("http_post", [])
    check("one_actual_post_observation", len(posts) == 1
          and not by_event.get("post_refused") and not by_event.get("request_preflight_mismatch"))
    body = (RECEIPTS / "model-input.json").read_bytes()
    envelope = json.loads(body)
    request = json.loads(envelope["messages"][1]["content"])
    preflight = load(RECEIPTS / "preflight.json")
    check("preflight_exact_http_body", sha(RECEIPTS / "model-input.json") == preflight["http_body_sha256"]
          == posts[0]["body_sha256"] and len(body) == preflight["http_body_bytes"]
          == posts[0]["body_bytes"] == 73560)
    check("configured_model_and_wire", spec["llm_provider"] == "deepseek"
          and envelope["model"] == "deepseek-flash" and envelope["max_tokens"] == 8192
          and envelope["thinking"] == {"type": "disabled"}
          and request["schema_version"] == "narrative-model-request/6",
          {"model": envelope["model"], "max_tokens": envelope["max_tokens"],
           "thinking": envelope["thinking"], "wire": request["schema_version"],
           "tasks": len(request["material"]["tasks"])})
    old_dir = ROOT / ".planning/r1-w07-live/20261022-annual-090"
    old = load(old_dir / "receipts/controller-result.json")
    old_body = old_dir / "receipts/model-input.json"
    check("prior_preflight_zero_post_same_body", old["status"] == "preflight_budget_exceeded"
          and old["model_post_count"] == 0 and sha(old_body) == sha(RECEIPTS / "model-input.json"))
    check("conservative_bound_not_relaxed", preflight["conservative_token_bound"] == 81880
          and old["preflight"]["conservative_token_bound"] == 81880
          and preflight["max_output_tokens"] == old["preflight"]["max_output_tokens"] == 8192)
    snapshots = [load(RECEIPTS / ("cli-" + label + ".native.json")) for label in
                 ("001-after_paid", "002-activation_pending", "003-complete", "004-cache")]
    for label in ("001-after_paid", "002-activation_pending", "003-complete", "004-cache"):
        sha(RECEIPTS / ("cli-" + label + ".native.json"))
        command = load(RECEIPTS / ("cli-" + label + ".command.json"))
        check("actual_cli_stage:" + label, command["stderr_bytes"] == 0
              and not command["stderr_truncated"] and
              "--allow-local-model-http" not in command["command"])
    first, activation, complete, cache = snapshots
    check("actual_native_stage_outcomes",
          [s["native_exit"] for s in snapshots] == [2, 2, 0, 0]
          and first["receipt"]["status"] == "paused"
          and first["receipt"]["documents"][0]["errors"] == ["IO_TRANSIENT"]
          and activation["receipt"]["documents"][0]["status"] == "activation_pending"
          and complete["receipt"]["status"] == cache["receipt"]["status"] == "completed")
    paid = first["after"]["reservations"]
    check("one_durable_paid_operation", len(paid) == 1 and paid[0]["usage_status"] == "known")
    stable = same_paid(paid)
    check("same_paid_operation_no_new_charge", all(
        same_paid(s["after"]["reservations"]) == stable
        and s["after"]["charged_tokens"] == 17329
        and s["after"]["charged_micro_usd"] == 6701
        for s in (first, activation, complete)))
    check("same_frozen_generation", first["after"]["generations"]
          == activation["after"]["generations"] == complete["after"]["generations"])
    generation = next(iter(complete["after"]["generations"].values()))
    check("frozen_configured_generation", generation["reading_model_projection"] == "reading-model-input/5"
          and generation["execution_versions"]["selector"] == "0.9.0"
          and generation["model"]["model_id"] == "deepseek-flash"
          and generation["model"]["endpoint"] == "https://api.deepseek.com/chat/completions"
          and generation["model"]["max_output_tokens"] == 8192
          and generation["reading_model_boundary"]["request_schema"] == "narrative-model-request/6")

    wiki = Path(spec["project_root"])
    with ro(Path(spec["automation_db"])) as db:
        rows = [dict(row) for row in db.execute(
            "SELECT a.attempt_id,a.job_id,a.attempt_no,a.lease_token,a.runtime_generation,a.outcome,"
            "a.error_code,a.started_at,a.finished_at FROM attempts a JOIN narrative_run_jobs r "
            "ON r.job_id=a.job_id WHERE r.run_id=? ORDER BY a.started_at",
            (spec["batch_run_id"],))]
        native_paid = [dict(row) for row in db.execute(
            "SELECT * FROM narrative_model_reservations WHERE run_id=?", (spec["batch_run_id"],))]
        cache_count = db.execute("SELECT COUNT(*) FROM narrative_model_reservations WHERE run_id=?",
                                 (spec["batch_run_id"] + "-cache",)).fetchone()[0]
    summary_attempts = [row for row in rows if row["job_id"] == paid[0]["job_id"]]
    check("live_auto_retry_and_fence", len(summary_attempts) == 2
          and summary_attempts[0]["outcome"] == "retryable"
          and summary_attempts[0]["error_code"] == "IO_TRANSIENT"
          and summary_attempts[1]["outcome"] == "succeeded"
          and summary_attempts[1]["attempt_no"] > summary_attempts[0]["attempt_no"]
          and summary_attempts[1]["runtime_generation"] > summary_attempts[0]["runtime_generation"]
          and summary_attempts[1]["lease_token"] != summary_attempts[0]["lease_token"],
          [{"attempt_id": a["attempt_id"], "attempt_no": a["attempt_no"],
            "outcome": a["outcome"], "error_code": a["error_code"],
            "fence": a["runtime_generation"],
            "lease_sha256": hashlib.sha256(a["lease_token"].encode()).hexdigest()} for a in summary_attempts])
    recovered = by_event.get("paid_recover", [])
    replay = by_event.get("paid_replay", [])
    after_paid = by_event.get("after_paid", [])
    check("new_pid_native_recover_and_replay", len(after_paid) == len(recovered) == len(replay) == 1
          and posts[0]["pid"] == after_paid[0]["pid"] != recovered[0]["pid"]
          and recovered[0]["paid_attempt_id"] == paid[0]["attempt_id"]
          and recovered[0]["worker_attempt_id"] == summary_attempts[1]["attempt_id"]
          and recovered[0]["request_sha256"] == paid[0]["request_sha256"]
          and recovered[0]["body_sha256"] == replay[0]["body_sha256"]
          == paid[0]["paid_response_pin"]["body_sha256"])
    check("preflight_and_paid_replay_input_binding",
          replay[0]["request_input_sha256"] == preflight["model_input_sha256"]
          and all(row["model_input_sha256"] == preflight["model_input_sha256"]
                  and row["http_body_sha256"] == preflight["http_body_sha256"]
                  and row["http_body_bytes"] == preflight["http_body_bytes"]
                  and row["max_output_tokens"] == preflight["max_output_tokens"]
                  for row in by_event.get("request_preflight", [])))
    native = native_paid[0]
    pin = json.loads(native["paid_response_json"])
    actual_pin_body = wiki / ".source_catalog" / pin["object_key"]
    response = load(actual_pin_body)
    check("durable_response_bytes_and_usage", len(native_paid) == 1
          and sha(actual_pin_body) == pin["body_sha256"]
          and actual_pin_body.stat().st_size == pin["byte_size"] == 4478
          and pin["http_status"] == 200 and response["model"] == "deepseek-flash"
          and response["usage"]["prompt_tokens"] == native["input_tokens"] == 16405
          and response["usage"]["completion_tokens"] == native["output_tokens"] == 924
          and response["usage"]["total_tokens"] == 17329)
    cost = (16405 * spec["pricing"]["input_micro_usd_per_million_tokens"]
            + 924 * spec["pricing"]["output_micro_usd_per_million_tokens"] + 999999) // 1000000
    check("fee_proxy_matches_native", cost == native["estimated_micro_usd"] == 6701)
    artifact = complete["receipt"]["documents"][0]["artifact_ref"]
    check("same_artifact_cache_zero_native", cache["before"]["run"] is None
          and cache["before"]["reservations"] == cache["after"]["reservations"] == []
          and cache_count == 0 and cache["after"]["charged_tokens"] == 0
          and cache["after"]["charged_micro_usd"] == 0
          and cache["receipt"]["documents"][0]["generation_status"] == "reused"
          and cache["receipt"]["documents"][0]["artifact_ref"] == artifact)
    cache_work = Path(spec["work_root"]) / (spec["batch_run_id"] + "-cache")
    check("cache_work_is_new_run_no_scratch_claim", cache["before"]["run"] is None
          and cache["receipt"]["storage"]["scratch_peak_bytes"] == 0,
          {"run_id": cache["after"]["run"]["run_id"], "work_dir": str(cache_work),
           "present_after_run": cache_work.exists()})
    with ro(wiki / ".source_catalog/catalog.sqlite3") as db:
        version = dict(db.execute("SELECT * FROM narrative_artifact_versions WHERE artifact_version_id=?",
                                  (artifact["artifact_version_id"],)).fetchone())
        locations = [dict(row) for row in db.execute(
            "SELECT absolute_path,source_id,observed_size FROM locations WHERE document_id=?",
            (spec["source_ref"]["document_id"],))]
    actual_artifact = wiki / ".source_catalog" / version["object_key"]
    bundle = load(actual_artifact)
    check("actual_visible_artifact_bytes", version["status"] == "visible" and version["activated_at"]
          and bundle["source_ref"] == spec["source_ref"] and bundle["quality_status"] == "needs_review"
          and sha(actual_artifact) == artifact["content_sha256"] == native["output_sha256"]
          and actual_artifact.stat().st_size == artifact["byte_size"] == native["output_bytes"] == 415965)
    originals = [Path(loc["absolute_path"]) for loc in locations
                 if loc["source_id"] == spec["source_ref"]["source_id"]
                 and loc["observed_size"] == spec["source_ref"]["byte_size"]]
    check("original_pdf_preserved", bool(originals) and any(
        p.stat().st_size == 1608226 and sha(p) == spec["source_ref"]["content_sha256"] for p in originals))
    context_path = PACKET / "rf-public-context.json"
    context = load(context_path)
    capture = load(PACKET / "w07-real-rf-read-capture.json")
    actual_stdout = Path(capture["stdout_artifact"])
    check("public_installed_rf_read_bytes", capture["exit_code"] == 0
          and capture["stdout_total_bytes"] == capture["stdout_retained_bytes"] == 418917
          and capture["stderr_total_bytes"] == 0
          and not capture["stdout_truncated"] and not capture["stderr_truncated"]
          and actual_stdout.stat().st_size == 418917
          and sha(actual_stdout) == sha(context_path) == AUTHOR["public_rf_read"]["sha256"]
          and Path(capture["stderr_artifact"]).stat().st_size == 0)
    check("public_context_not_formula_acceptance", context["schema_version"] == "revenue-narrative-context/1"
          and len(context["evidence_spans"]) == 96
          and context["quality_status"] == "needs_review"
          and context["selection"]["status"] == "partial"
          and context["selection"]["coverage_complete"] is False
          and AUTHOR["public_rf_read"]["is_actual_formula_consumption"] is False,
          {"selection": context["selection"], "quality_status": context["quality_status"]})
    coordinator_events = [json.loads(line) for line in
                          (AUDIT / "roles/coordinator/events.jsonl").read_text(encoding="utf-8").splitlines()]
    actual_cmd = next(row["data"] for row in coordinator_events
                     if row["kind"] == "command_finished"
                     and row["data"]["capture_id"] == capture["capture_id"])
    adapter = ROOT / ".planning/r1-w03-join/read_installed_rf_narrative.py"
    check("installed_public_cli_capture_adapter", str(adapter).replace("\\", "/") in
          [str(v).replace("\\", "/") for v in actual_cmd["command"]]
          and actual_cmd["output_complete"] and actual_cmd["input_complete"])
    sha(adapter)
    installed = Path("C:/Users/郑曾波/.agents/skills/revenue-forecast/scripts/narrative_source_preparation.py")
    sha(installed)

    restoration = load(PACKET / "sealed-index-restoration.json")
    manifest_path = AUDIT / "execution/manifest.json"
    manifest = load(manifest_path)
    initial_index = AUDIT / "roles/executor/native_operation_index.json"
    index_entry = next(e for e in manifest["artifacts"] if e["path"] == str(initial_index))
    check("initial_manifest_and_affected_index_exactly_restored",
          sha(manifest_path) == restoration["initial_manifest_sha256"]
          and len(manifest["artifacts"]) == restoration["artifacts_checked"] == 639
          and sha(initial_index) == index_entry["sha256"]
          == restoration["original_index_sha256_restored"]
          and initial_index.stat().st_size == index_entry["byte_size"] == 3763)
    new_index = load(Path(restoration["new_attempt_index"]))
    check("new_attempt_index_retains_initial_plus_new_run",
          all(item in new_index["operations"] for item in load(initial_index)["operations"])
          and any(item["run_id"] == spec["batch_run_id"] for item in new_index["operations"]))

    amendment = load(ROOT / "docs/plans/du11-source-closure-2026-10-18/r1-holdout-20261021/budget-reallocation-20261022.json")
    scope = load(Path(restoration["new_effective_scope"]))
    meta = load(ROOT / ".planning/shared-reading-production/live/metadata.json")
    latest = {}
    for line in (ROOT / ".planning/shared-reading-production/live/usage.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["kind"] == "native_model_charge" and row["mode"] == "live":
            latest[(row["database"], row["attempt_id"])] = row
    baseline = meta["mother_budget"]
    totals = {"charged_tokens": baseline["prior_charged_tokens"] + sum(r["charged_tokens"] for r in latest.values()),
              "charged_micro_usd": baseline["prior_charged_micro_usd"] + baseline["retained_fx_hold_micro_usd"]
                                   + sum(r["charged_micro_usd"] for r in latest.values()),
              "new_unknown_count": sum(r["usage_status"] != "known" for r in latest.values()),
              "prior_unknown7_retained": baseline["old_unknown_hold_count_already_in_baseline"],
              "token_limit": baseline["token_limit"], "micro_usd_limit": baseline["micro_usd_limit"]}
    check("independent_mother_totals_and_unchanged_user_cap", totals ==
          {"charged_tokens": 1561352, "charged_micro_usd": 631959, "new_unknown_count": 4,
           "prior_unknown7_retained": 7, "token_limit": 2000000, "micro_usd_limit": 20000000}, totals)
    unknowns = [r for r in latest.values() if r["usage_status"] != "known"]
    check("unknown_holds_not_forgiven", len(unknowns) == 4
          and all(r["charged_tokens"] > 0 and r["charged_micro_usd"] > 0 for r in unknowns))
    check("root_reallocation_not_user_budget_increase",
          amendment["supersedes_current_execution_only"]["company_total_tokens"] == {"old": 100000, "new": 150000}
          and scope["resource_limits"]["max_tokens"] == 150000
          and spec["limits"]["max_tokens"] == 100000
          and amendment["unchanged"]["parent_tokens"] == 2000000
          and amendment["unchanged"]["parent_usd"] == "20.00")
    company_native = {}
    with ro(Path(spec["automation_db"])) as db:
        for entry in new_index["operations"]:
            for row in db.execute("SELECT * FROM narrative_model_reservations WHERE run_id=?", (entry["run_id"],)):
                record = dict(row)
                company_native[(entry["database"], record["attempt_id"])] = record
    # All indexed company operations share the single explicitly named AUTO DB.
    # Native charged_* keeps unknown reservations in the budget. It does not
    # claim all cumulative company tokens are actual known provider usage.
    known = [r for r in company_native.values() if r["usage_status"] == "known"]
    held = [r for r in company_native.values() if r["usage_status"] != "known"]
    known_tokens = sum(r["input_tokens"] + r["output_tokens"] for r in known)
    known_micro_usd = sum(r["estimated_micro_usd"] for r in known)
    held_tokens = sum(r["input_tokens_bound"] + r["max_output_tokens"] for r in held)
    held_micro_usd = sum(r["reserved_micro_usd"] for r in held)
    check("company_charged_totals_keep_native_unknown_hold",
          known_tokens == 24184 and known_micro_usd == 9693
          and held_tokens == 32171 and held_micro_usd == 6728
          and known_tokens + held_tokens == 56355
          and known_micro_usd + held_micro_usd == 16421,
          {"known_tokens": known_tokens, "known_micro_usd": known_micro_usd,
           "unknown_hold_tokens": held_tokens, "unknown_hold_micro_usd": held_micro_usd})
    check("protected_configs_unchanged_hash_only", all(sha(Path(item["path"])) == item["sha256"]
          for item in scope["config_refs"]))
    # In-memory counterfactuals exercise the critical predicates, not native state.
    check("counterfactual_second_post_fails", not (len(posts + posts) == 1))
    check("counterfactual_new_paid_request_fails", not (
        paid[0]["request_sha256"] == "0" * 64))
    check("counterfactual_cache_other_artifact_fails", not (
        artifact["content_sha256"] == "0" * 64))
    check("counterfactual_zero_usage_fails", not (response["usage"]["total_tokens"] == 0))

    evidence = {"schema_version": "w07-independent-readonly-checks/1",
                "reviewer": "/root/r1_w04_summary_runtime",
                "code_head": CODE_HEAD, "checks": checks, "check_count": len(checks),
                "all_passed": all(row["passed"] for row in checks), "file_bindings": bindings,
                "native_databases_opened": "SQLite URI mode=ro + PRAGMA query_only; no store constructors",
                "paid_calls_by_reviewer": 0, "downloads_by_reviewer": 0,
                "key_values_read": False, "native_mutations": False,
                "temporary_scratch_created": False,
                "scope": "lifecycle/payment-replay/cache/public-byte-read only; not content or RF formula acceptance"}
    (REVIEW / "checks.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks": len(checks), "all_passed": evidence["all_passed"],
                      "evidence": str(REVIEW / "checks.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
