"""One frozen-source production operation; reuse the existing runner and ledger."""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

PREPARATION = ROOT / ".planning/shared-reading-production/du11/live-prep-current-20261025-formal-v4.json"
USAGE = ROOT / ".planning/shared-reading-production/live/usage.jsonl"
POLICY = ROOT / "config/resource_budget.yaml"
MAX_TOKENS = 100_000
MAX_MICRO_USD = 100_000


def main() -> int:
    from config import Config
    from company_wiki.automation.narrative_http_model import model_options_from_config
    from company_wiki.resource_budget import load_budget_policy
    from tools.document_understanding_benchmark import phase_c_runner as runner

    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--mode", required=True, choices=("preflight", "formal"))
    selected = args.parse_args()
    configured_env = os.environ.get("COMPANY_WIKI_BUDGET_CONFIG")
    if configured_env is not None and Path(configured_env).resolve() != POLICY.resolve():
        raise RuntimeError("CONFLICTING_COMPANY_WIKI_BUDGET_CONFIG")
    os.environ["COMPANY_WIKI_BUDGET_CONFIG"] = str(POLICY)
    metadata = json.loads(PREPARATION.read_text(encoding="utf-8"))
    runner.verify_preparation(metadata, mode="live")
    sample = next(s for s in metadata["samples"] if s["sample_id"] == "us-10k")
    provider = next(p for p in metadata["providers"] if p["provider"] == sample["provider"])
    actual = model_options_from_config(
        Config.load(llm_provider=provider["provider"], validation_scope="llm").llm,
        purpose="narrative",
    )
    if actual != provider["options"]:
        raise RuntimeError("ACTUAL_CONFIGURED_MODEL_DRIFT")
    policy = load_budget_policy(POLICY)
    current_path = ROOT / "docs/plans/du11-source-closure-2026-10-18/CURRENT_STATUS.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    if (current["budget_snapshot"]["cumulative_cap_tokens"] != policy.cumulative_tokens
            or current["budget_snapshot"]["cumulative_cap_usd"] * 1_000_000 != policy.cumulative_micro_usd):
        raise RuntimeError("PWF_AND_CONFIG_BUDGET_DRIFT")
    before = runner.mother_totals(PREPARATION, USAGE, budget_policy_path=POLICY)
    if not runner.mother_budget_fits(before, tokens_bound=MAX_TOKENS, micro_usd_bound=MAX_MICRO_USD):
        raise RuntimeError("MOTHER_BUDGET_PREFLIGHT_FAILED")
    bounded = deepcopy(metadata)
    bounded["candidate_per_paid_request_limits"].update(
        max_tokens=MAX_TOKENS, max_cost_usd="0.10", max_final_bytes=1024 * 1024,
    )
    output = ROOT / f".planning/shared-reading-production/du11/live-us-10k-task-summary-v4-{selected.mode}-20261025"
    output.mkdir(parents=True, exist_ok=False)
    paths = [PREPARATION, POLICY, ROOT / "config.yaml", ROOT / "config/source_catalog.yaml",
             Path(__file__), Path(runner.__file__),
             ROOT / "tools/document_understanding_benchmark/phase_c_observer.py",
             ROOT / "tools/document_understanding_benchmark/phase_c_launcher.py",
             ROOT / "tools/document_understanding_benchmark/phase_c_bootstrap/sitecustomize.py"]
    binding = {p.relative_to(ROOT).as_posix(): runner.fingerprint(p) for p in paths}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    product_hashes = [(p.relative_to(ROOT).as_posix(), sha256(p.read_bytes()).hexdigest())
                      for p in sorted((ROOT / "src/company_wiki").rglob("*.py"))]
    product_hash = sha256(json.dumps(product_hashes, separators=(",", ":")).encode()).hexdigest()
    status_fingerprint = runner.fingerprint(current_path)
    original_write = runner.write_json

    def write_observation(path, value):
        if selected.mode == "preflight" and isinstance(value, dict) and value.get("schema_version") == "phase-c-observer/1":
            value = {**value, "forbid_post": True}
        return original_write(path, value)

    runner.USAGE = USAGE.resolve()
    runner.write_json = write_observation
    try:
        result = runner.run_pair(
            sample, provider, bounded, mode="live", output=output,
            preparation_path=PREPARATION, reading_model_projection="reading-model-input/4",
            consumer_projects=None if selected.mode == "preflight" else ROOT.parent,
            source_mode="registered_readonly", source_catalog_config=ROOT / "config/source_catalog.yaml",
            selected_versions="0.9.0", activation_recovery=True,
        )
    finally:
        runner.write_json = original_write
    after = runner.mother_totals(PREPARATION, USAGE, budget_policy_path=POLICY)
    events = runner.read_rows(output / "events.jsonl")
    posts = sum(e.get("event") == "http_post_attempt" for e in events)
    material = next((e for e in events if e.get("event") == "pre_reservation_material"), {})
    gold = material.get("gold", {})
    refusal_codes = [e.get("code") for e in events if e.get("event") == "pre_reservation_refused"]
    delta_tokens = after["charged_tokens"] - before["charged_tokens"]
    delta_micro_usd = after["charged_micro_usd"] - before["charged_micro_usd"]
    usage_within_limits = (after["charged_tokens"] <= policy.cumulative_tokens
        and after["charged_micro_usd"] <= policy.cumulative_micro_usd
        and 0 <= delta_tokens <= MAX_TOKENS and 0 <= delta_micro_usd <= MAX_MICRO_USD)
    accounting_unknown = result.get("native_usage_reconciliation_required") is True
    if accounting_unknown:
        # A missing ledger write is not a free model operation. Preserve raw
        # ledger observations, but do not present their difference as the bill.
        delta_tokens = delta_micro_usd = None
        usage_within_limits = False
    summary = {
        "schema_version": "production-v4-task-summary-operation/1", "mode": selected.mode,
        "provider": provider["provider"], "model_id": actual["model_id"],
        "projection": "reading-model-input/4", "source_sha256": sample["fingerprint"]["sha256"],
        "gold_sha256": runner.fingerprint(Path(sample["gold"]))["sha256"],
        "source_pre_reservation_gold": gold,
        "pre_reservation_refusal_codes": refusal_codes,
        "operation_fingerprints": binding,
        "git_head": head, "product_tree_sha256": product_hash,
        "pwf_status_fingerprint_observed": status_fingerprint,
        "pwf_cumulative_caps_used": {"tokens": current["budget_snapshot"]["cumulative_cap_tokens"],
                                     "usd": current["budget_snapshot"]["cumulative_cap_usd"]},
        "operation_inputs_unchanged": all(runner.fingerprint(ROOT / p) == fp for p, fp in binding.items()),
        "max_tokens": MAX_TOKENS, "max_micro_usd": MAX_MICRO_USD,
        "charged_delta_tokens": delta_tokens, "charged_delta_micro_usd": delta_micro_usd,
        "accounting_unknown": accounting_unknown,
        "usage_including_unknown_holds_within_limits": usage_within_limits,
        "mother_before": before, "mother_after": after, "posts": posts,
        "result": result, "formal_semantics": "NOT_REVIEWED", "complete_rf_forecast": "OPEN",
    }
    runner.write_json(output / "operation-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    if selected.mode == "preflight":
        ok = (result.get("status") == "PRE_RESERVATION_BLOCKED" and posts == 0
              and refusal_codes == ["PHASE_C_CACHE_WOULD_GENERATE"]
              and gold.get("required_count", 0) > 0
              and gold.get("supported_count") == gold.get("required_count")
              and not gold.get("missing_ids")
              and before == after and result.get("protected_unchanged") is True
              and result.get("temporary_lake_removed") is True)
    else:
        ok = (result.get("status") == "PASS" and result.get("temporary_lake_removed") is True
              and usage_within_limits)
    ok = ok and summary["operation_inputs_unchanged"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
