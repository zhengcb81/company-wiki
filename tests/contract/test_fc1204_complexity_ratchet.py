"""FC-1204-b gate: per-file max-cyclomatic-complexity ratchet.

Frozen from the measured 2026-08-12 baseline (findings 60/61 — AST McCabe
over every top-level function).  Two rules:

1. A file IN the table must not exceed its frozen max — the ratchet only
   moves DOWN (a deliberate split updates this table with the lower value).
2. A file NOT in the table (new file) must not exceed 10 — new code stays
   simple, per the FC-1204 contract.

McCabe counts: 1 + decision points (if/for/while/and/or/except/comprehension/
assert/with, BoolOp n-1).
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"

FROZEN_MAX = {
    "acquisition.py": 26,
    "acquisition_config.py": 13,
    "acquisition_journal.py": 9,
    "acquisition_service.py": 15,
    "activation.py": 25,
    "adapter_dispatch.py": 4,
    "adapter_process.py": 21,
    "adapters/common.py": 5,
    "adapters/company_raw.py": 31,
    "adapters/conformance.py": 8,
    "adapters/dayu.py": 58,
    "adapters/interface.py": 5,
    "adapters/parity.py": 13,
    "adapters/registry.py": 1,
    "adapters/sidecar.py": 16,
    "admission.py": 33,
    "architecture_gate.py": 13,
    "archive_retired_evidence.py": 7,
    "artifact_backfill.py": 37,
    "artifact_dag.py": 8,
    "artifact_handle.py": 59,
    "assertion_service.py": 18,
    "authorization.py": 16,
    "backfill_v2.py": 25,
    "canary_registry.py": 17,
    "canonical_writer.py": 21,
    "catalog_size_report.py": 5,
    "cli.py": 140,
    "close_gap.py": 18,
    "code_identity.py": 3,
    "config.py": 46,
    "control.py": 34,
    "dayu_cli_adapter.py": 46,
    "dropbox_governance.py": 15,
    "duplicate_cleanup.py": 34,
    "evidence_query.py": 15,
    "extraction_quality.py": 24,
    "flags.py": 8,
    "focus_cleanup.py": 42,
    "gap_plan.py": 20,
    "identity_cli.py": 6,
    "legacy_close_gate.py": 16,
    "llm_failure_policy.py": 4,
    "llm_summarizer.py": 35,
    "lock.py": 15,
    "migration.py": 23,
    "migration_ledger.py": 21,
    "models.py": 18,
    "normalized_meta.py": 5,
    "normalizer.py": 47,
    "observability.py": 6,
    "policy.py": 5,
    "policy_2x.py": 43,
    "portfolio_promoter.py": 36,
    "producer_events.py": 1,
    "prompt_injection.py": 15,
    "prune_retired_evidence.py": 12,
    "reconcile_retire_state.py": 12,
    "reconciliation.py": 17,
    "remediation.py": 24,
    "resolver.py": 103,
    "restore.py": 13,
    "runtime_policy.py": 30,
    "scanner.py": 140,
    "scheduler_policy.py": 8,
    "section_extractor.py": 22,
    "section_query.py": 12,
    "security_identity.py": 23,
    "service.py": 45,
    "shadow_parity.py": 12,
    "source_bundle.py": 26,
    "startup.py": 13,
    "store.py": 30,
    "summarizer.py": 23,
    "trace_parity.py": 19,
    "url_binding.py": 6,
    "visibility_bridge.py": 7,
    "worker.py": 99
}

NEW_FILE_MAX = 10


def _mccabe(node: ast.AST) -> int:
    if not isinstance(node, ast.AST):
        return 0
    total = 0
    for child in ast.iter_child_nodes(node):
        total += _mccabe(child)
    if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or,
                         ast.ExceptHandler, ast.comprehension, ast.Assert,
                         ast.With)):
        total += 1
    if isinstance(node, ast.BoolOp):
        total += len(node.values) - 1
    return total


def _max_complexity(text: str) -> int:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 0
    top = 0
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_"):
            seg = ast.get_source_segment(text, node) or ""
            top = max(top, 1 + _mccabe(ast.parse(seg)))
    return top


def test_complexity_ratchet_frozen_files_do_not_worsen() -> None:
    for rel, frozen in sorted(FROZEN_MAX.items()):
        path = SRC / rel
        assert path.is_file(), f"ratchet file missing: {rel}"
        actual = _max_complexity(path.read_text(encoding="utf-8"))
        assert actual <= frozen, (
            f"{rel} max complexity {actual} exceeds frozen {frozen} — "
            "complexity must only ratchet DOWN (deliberate split updates "
            "this table), never up"
        )


def test_complexity_ratchet_new_files_stay_simple() -> None:
    for path in sorted(SRC.rglob("*.py")):
        rel = str(path.relative_to(SRC)).replace("\\", "/")
        if rel in FROZEN_MAX:
            continue
        actual = _max_complexity(path.read_text(encoding="utf-8"))
        assert actual <= NEW_FILE_MAX, (
            f"new file {rel} has max complexity {actual} > {NEW_FILE_MAX}"
        )
