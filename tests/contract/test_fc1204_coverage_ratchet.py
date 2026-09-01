"""FC-1204-a gate: per-module branch-coverage ratchet (frozen 2026-08-12).

Values measured from the full wiki suite with --cov-branch (findings 61).
Three tiers:

- TIER1: the FC-201~906 contract chain, REQUIRED >= 95.
- TIER2: contract-chain modules frozen at measured values; their >=95
  targets are recorded in the FC-1204 WU card (deferred to FC-1205/Phase 13
  with explicit reasons: resolver error paths, worker-adjacent paths).
- FROZEN: everything else — legacy/R9 assets (normalizer, security_identity,
  startup, worker, store, scanner v1 paths) and release-wave assets
  (policy_2x, backfill_v2, portfolio_promoter).  Frozen so a regression
  fails; raises happen only through deliberate FC work.

The test parses coverage.json written by the immediately preceding
`pytest --cov ... --cov-report=json` run — CI runs this test AFTER the
coverage run with the same invocation.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COVERAGE_JSON = REPO_ROOT / "coverage.json"

TIER1 = {
    "policy.py": 95,
    "url_binding.py": 95,
    "admission.py": 95,
    "scheduler_policy.py": 95,
    "flags.py": 95,
    "adapters/sidecar.py": 95,
    "source_bundle.py": 95,
    "service.py": 95,
    "gap_plan.py": 95,
    "migration.py": 95,
    "visibility_bridge.py": 95,
    "dropbox_governance.py": 95,
    "restore.py": 95,
    "producer_events.py": 95,
    "artifact_handle.py": 95,
    "canary_registry.py": 95
}
TIER2 = {
    "acquisition_journal.py": 85,
    "close_gap.py": 85,
    "runtime_policy.py": 84,
    "resolver.py": 86,
    "artifact_dag.py": 44,
    "prompt_injection.py": 73,
    "normalized_meta.py": 65,
    "activation.py": 82
}
FROZEN = {
    "__init__.py": 100,
    "acquisition.py": 78,
    "acquisition_config.py": 73,
    "acquisition_service.py": 82,
    "adapter_dispatch.py": 89,
    "adapter_process.py": 70,
    "adapters/common.py": 86,
    "adapters/company_raw.py": 86,
    "adapters/conformance.py": 100,
    "adapters/dayu.py": 83,
    "adapters/interface.py": 100,
    "adapters/parity.py": 100,
    "adapters/registry.py": 100,
    "architecture_gate.py": 75,
    "archive_retired_evidence.py": 95,
    "artifact_backfill.py": 79,
    "assertion_service.py": 86,
    "authorization.py": 89,
    "backfill_v2.py": 85,
    "canonical_writer.py": 72,
    "catalog_size_report.py": 92,
    "cli.py": 70,
    "code_identity.py": 100,
    "config.py": 81,
    "control.py": 73,
    "dayu_cli_adapter.py": 71,
    "duplicate_cleanup.py": 74,
    "evidence_query.py": 87,
    "extraction_quality.py": 77,
    "focus_cleanup.py": 86,
    "identity_cli.py": 82,
    "legacy_close_gate.py": 85,
    "llm_failure_policy.py": 100,
    "llm_summarizer.py": 82,
    "lock.py": 61,
    "migration_ledger.py": 86,
    "models.py": 85,
    "normalizer.py": 55,
    "observability.py": 91,
    "policy_2x.py": 80,
    "portfolio_promoter.py": 87,
    "prune_retired_evidence.py": 87,
    "reconcile_retire_state.py": 92,
    "reconciliation.py": 91,
    "remediation.py": 79,
    "scanner.py": 91,
    "section_extractor.py": 87,
    "section_query.py": 87,
    "security_identity.py": 77,
    "shadow_parity.py": 87,
    "startup.py": 61,
    "store.py": 83,
    "summarizer.py": 87,
    "trace_parity.py": 82,
    "worker.py": 79
}


def _load() -> dict[str, float]:
    # coverage.json is written at SESSION END by the coverage run — the gate
    # can only judge a FRESH measurement, so it runs as a separate CI step
    # after the coverage invocation (FC1204_COVERAGE_GATE=1).  In-suite it
    # skips honestly: a stale file is never used as evidence.
    import os

    import pytest

    if os.environ.get("FC1204_COVERAGE_GATE") != "1":
        pytest.skip("coverage gate runs as a separate step "
                    "(FC1204_COVERAGE_GATE=1)")
    assert COVERAGE_JSON.is_file(), (
        "coverage.json missing — run the suite with "
        "--cov=src/company_wiki/source_catalog --cov-branch "
        "--cov-report=json first"
    )
    data = json.loads(COVERAGE_JSON.read_text(encoding="utf-8"))
    files = data.get("files", {})
    out: dict[str, float] = {}
    prefix = "src/company_wiki/source_catalog/"
    for path, entry in files.items():
        rel = path.replace("\\", "/")
        if rel.startswith(prefix):
            summary = entry.get("summary", {})
            num = summary.get("num_statements", 0)
            cov = summary.get("covered_lines", 0)
            total = summary.get("num_branches", 0)
            covb = summary.get("covered_branches", 0)
            if num:
                out[rel[len(prefix):]] = round(100.0 * (cov + covb) / (num + total), 1)
    return out


def _check(table: dict[str, float], measured: dict[str, float], required: bool) -> None:
    for rel, floor in sorted(table.items()):
        actual = measured.get(rel)
        assert actual is not None, f"module not measured: {rel}"
        # 0.5pt tolerance: the term report rounds to integers while
        # coverage.json carries decimals (run-to-run variance ~0.3pt).
        assert actual >= floor - 0.5, (
            f"{rel} branch coverage {actual}% < {floor}% "
            f"({'required' if required else 'frozen'})"
        )


def test_tier1_critical_chain_at_95() -> None:
    _check(TIER1, _load(), required=True)


def test_tier2_and_frozen_do_not_regress() -> None:
    _check({**TIER2, **FROZEN}, _load(), required=False)
