"""Offline N4C readiness facts; no downloads, provider HTTP or model requests."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from zipfile import ZipFile

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / name) for name in ("src", "tests", "scripts")]
from config import Config  # noqa: E402 -- CLI bootstrap uses the existing project loader.
from company_wiki.automation.narrative_http_model import model_options_from_config  # noqa: E402
from company_wiki.automation.narrative_run_store import NarrativeRunStore  # noqa: E402

RESULTS = PROJECT / "docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/results"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prior_budget() -> dict:
    """Existing read-only AUTO ledger plus subsequent saved usage facts."""
    store = NarrativeRunStore(PROJECT / "tmp/n4c-20261004-pilot-a/automation.sqlite3")
    old = asdict(store.budget_snapshot("n4c-20261004-wave1"))
    entries = [{"origin": "original_auto_ledger", **old}]
    seen = {old["run_id"]}
    for path in sorted(RESULTS.glob("n4c_live_*_run*.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        budget = receipt["final_budget"]
        if budget["run_id"] in seen:
            raise ValueError("duplicate saved run accounting")
        seen.add(budget["run_id"])
        if any(type(budget[key]) is not int or budget[key] < 0 for key in
               ("charged_tokens", "charged_micro_usd", "unknown_reservations", "unsettled_reservations")):
            raise ValueError("invalid saved run accounting")
        entries.append({"origin": path.name, **budget})
    return {"entries": entries,
            **{key: sum(item[key] for item in entries) for key in
               ("charged_tokens", "charged_micro_usd", "unknown_reservations", "unsettled_reservations")}}


def campaign_budget_facts(budget: dict, token_cap: int, cost_cap: int) -> dict:
    """Report explicit limits, retaining historical unknown usage and FX guard.

    This read-only calculation does not authorize an external request. Negative
    balances remain visible when inspecting an older, already exceeded limit.
    """
    return {"current_campaign_token_cap": token_cap,
            "current_campaign_cost_cap_micro_usd": cost_cap,
            "tokens_remaining": token_cap - budget["charged_tokens"],
            "micro_usd_remaining_after_fx_guard": cost_cap - budget["charged_micro_usd"] - 2764}


def consumer_bootstrap(rf: Path, head: str, root: Path) -> list[str]:
    """Run the public RF CLI with its exact committed scripts in scratch."""
    windowless = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        ["git", "-C", str(rf), "archive", "--format=zip", head, "scripts"],
        capture_output=True, check=True, timeout=20, creationflags=windowless,
    )
    with ZipFile(BytesIO(result.stdout)) as snapshot:
        snapshot.extractall(root)
        exported = [name for name in snapshot.namelist() if name.endswith(".py")]
    env = {**os.environ, "PYTHONPATH": str(PROJECT / "src"), "PYTHONUTF8": "1",
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHON_DOTENV_DISABLED": "1"}
    result = subprocess.run(
        [sys.executable, "-B", str(root / "scripts/narrative_source_preparation.py"), "--help"],
        cwd=root, env=env, capture_output=True, timeout=20, creationflags=windowless,
    )
    if result.returncode != 0:
        raise ValueError(f"RF committed CLI bootstrap failed (exit {result.returncode})")
    if b"--company-wiki-catalog-config" not in result.stdout:
        raise ValueError("RF committed CLI missing narrative transport option")
    return sorted(exported)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rf-root", type=Path, required=True)
    parser.add_argument("--rf-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--campaign-token-cap", type=int, required=True,
                        help="Explicit cumulative token limit for this read-only report")
    parser.add_argument("--campaign-cost-cap-micro-usd", type=int, required=True,
                        help="Explicit cumulative USD limit in millionths, not new spending authority")
    args = parser.parse_args()
    if args.campaign_token_cap < 1 or args.campaign_cost_cap_micro_usd < 1:
        parser.error("campaign limits must be positive integers")
    if len(args.rf_head) != 40 or any(c not in "0123456789abcdef" for c in args.rf_head):
        parser.error("rf-head requires an exact lowercase commit SHA")
    if args.output.exists():
        parser.error("output already exists; do not overwrite earlier evidence")
    fixtures = runpy.run_path(str(PROJECT / "tests/integration/test_narrative_runtime_e2e.py"))
    _, paths = fixtures["_e6_source_paths"]()
    before = {name: (sha(path), path.stat().st_size, path.stat().st_mtime_ns) for name, path in paths.items()}
    production_before = fixtures["_e6_production_fingerprint"]()
    protected = [PROJECT / "config/source_acquisition.yaml",
                 args.rf_root / "assurance/runs/weekly_alert.jsonl",
                 args.rf_root / "assurance/runs/weekly_manifest.json"]
    protected_before = {str(path): sha(path) for path in protected}
    samples = []
    for sample in fixtures["_E6_REAL_SAMPLES"]:
        actual = before[sample["sample_id"]]
        if actual[0] != sample["sha256"]:
            raise ValueError("sample bytes differ from pinned source")
        samples.append({"sample_id": sample["sample_id"], "kind": sample["document_kind"],
                        "language": sample["language"], "sha256": actual[0], "byte_size": actual[1]})
    budget = prior_budget()
    options = {}
    for provider in ("mimo", "deepseek"):
        config = model_options_from_config(Config.load(llm_provider=provider).llm)
        options[provider] = {key: config[key] for key in
                             ("model_id", "endpoint", "api_key_env", "max_output_tokens", "temperature")}
    temp_parent = PROJECT / "tmp"
    with tempfile.TemporaryDirectory(prefix="n4pf", dir=temp_parent) as name:
        root = Path(name)
        modules = consumer_bootstrap(args.rf_root, args.rf_head, root)
    checks = {"originals_unchanged": before == {
        name: (sha(path), path.stat().st_size, path.stat().st_mtime_ns) for name, path in paths.items()},
        "production_unchanged": production_before == fixtures["_e6_production_fingerprint"](),
        "owner_and_user_config_unchanged": protected_before == {str(path): sha(path) for path in protected},
        "test_root_restored_absent": not root.exists()}
    if not all(checks.values()):
        raise ValueError("preflight changed a protected input")
    budget_facts = campaign_budget_facts(
        budget, args.campaign_token_cap, args.campaign_cost_cap_micro_usd)
    tokens_remaining = budget_facts["tokens_remaining"]
    report = {"schema_version": "n4c-offline-preflight/2", "status": "verified_offline",
              "rf_head": args.rf_head, "rf_committed_modules": modules, "samples": samples,
              "configured_models": options, "prior_budget": budget,
              **budget_facts,
              "budget_readiness_scope": "output_tokens_only; full request and cost reservation not evaluated",
              "budget_can_reserve_configured_output": all(
                  tokens_remaining >= item["max_output_tokens"] for item in options.values()),
              "calls": {"provider_http": 0, "model_posts": 0, "download": 0},
              "checks": checks, "real_summary_or_consumer_read_claimed": False}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "sample_count": len(samples),
                      "rf_modules": len(modules), "tokens_remaining": tokens_remaining,
                      "budget_can_reserve_configured_output": report["budget_can_reserve_configured_output"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
