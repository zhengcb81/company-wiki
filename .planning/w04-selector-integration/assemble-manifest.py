"""Assemble the read-only W04 integration receipt; no product/Git writes."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path

CANON = Path("C:/Users/郑曾波/Projects/company-wiki")
OLD = Path("C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki")
OUT = CANON / ".planning/w04-selector-integration"
PREFIX = "src/company_wiki/source_catalog/"
data = json.loads((OUT / "three-tree-snapshot.json").read_text("utf-8"))


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(CANON), *args])


def evidence(root: Path, rel: str, role: str, lines: str = "") -> dict:
    raw = (root / rel).read_bytes()
    return {"root": str(root), "path": rel, "sha256": digest(raw),
            "bytes": len(raw), "role": role, "lines": lines}


semantic_paths = {x["path"] for x in data["semantic_freeze"]["files"]}
phase2 = json.loads((OLD / ".planning/w04-root-novelty-recall/phase2-real-recall/product-freeze.json").read_text("utf-8"))
selector_paths = semantic_paths | set(phase2["products"])
assert len(selector_paths) == 18
assert sum(p.startswith("src/") for p in selector_paths) == 8
g2_paths = {"scripts/config.py", "scripts/narrative_batch_configured.py",
            "tests/unit/test_narrative_model_config.py", "tests/unit/test_w04_llm_config_scope.py"}
ci_paths = {".github/workflows/ci.yml", "tools/changed_unit_tests.py", "tests/unit/test_ci_push_selection.py"}

sem_frozen = {x["path"]: x["sha256"] for x in data["semantic_freeze"]["files"]}
rows = []
for row in data["rows"]:
    row = dict(row)
    path = row["path"]
    row["content_conflict"] = row["receipt_recommendation"] == "both_sides_changed_requires_three_way_review"
    row["pwf_acceptance_references"] = []
    if path in selector_paths:
        row["package"] = "selector_accept"
        row["action"] = "ADD" if row["current_main"]["sha256"] is None else "REPLACE_EXACT_FROZEN_WORKTREE_BYTES"
        row["pwf_acceptance_references"].append({"root": str(OLD), "path": ".planning/w04-root-selector-recall/semantic-coverage-freeze.json", "locator": "files[path]", "meaning": "prerequisite business/public0.8/stage union"})
        if path in phase2["products"]:
            row["pwf_acceptance_references"].append({"root": str(OLD), "path": ".planning/w04-root-novelty-recall/phase2-real-recall/product-freeze.json", "locator": "products[path]", "meaning": "final authoritative bytes supersede earlier semantic freeze"})
        else:
            assert row["pending_worktree"]["sha256"] == sem_frozen[path]
            row["earlier_semantic_freeze_still_exact"] = True
        row["pwf_acceptance_references"].extend([
            {"root": str(OLD), "path": ".planning/w04-root-novelty-recall/phase2-real-recall/concentrated-attempt3.json", "locator": "nodes[name=concentrated]", "meaning": "all10 test modules/375PASS"},
            {"root": str(CANON), "path": ".planning/w04-root-novelty-recall/phase2-independent/report.json", "locator": "verdict/checks", "meaning": "17 independent engineering checks; reserved prepass boundary"},
            {"root": str(CANON), "path": ".planning/w04-root-novelty-recall/native-novelty-six-quality-v2-execution.json", "locator": "product_freeze_sha256/unchanged_checkpoint_script_sha256", "meaning": "ROOT fixed six originals successful replay"},
        ])
        assert not row["content_conflict"] and row["receipt_recommendation"] == "accept_frozen_target_no_main_content_conflict"
    elif path in g2_paths:
        row["package"] = "g2_configuration_deferred"
        row["action"] = "EXCLUDE_FROM_SELECTOR_RECEIPT"
        row["pwf_acceptance_references"].append({"root": str(OLD), "path": ".planning/w04-g2-config/handoff.json", "locator": "products and concentrated102PASS", "meaning": "independent configuration package"})
    elif path in ci_paths:
        row["package"] = "keep_current_main_ci"
        row["action"] = "KEEP_MAIN_NO_COPY"
        row["pwf_acceptance_references"].append({"root": str(OLD), "path": ".planning/w04-root-novelty-recall/phase2-real-recall/product-freeze.json", "locator": "preserved_initial_non_owned_sha256[path]", "meaning": "non-owned preexisting WIP; not selector dependency"})
        if path == "tests/unit/test_ci_push_selection.py":
            row["conflict_disposition"] = "Exclude old target. Currentmain is oldtarget plus6 OCR resource regression cases in test_ocr_resource_regressions_share_ci_and_local_smoke; old copy would remove accepted main coverage."
        else:
            row["conflict_disposition"] = "Currentmain already equals oldtarget after source checkout CRLF/LF normalization; no content change needed."
    else:
        raise AssertionError(path)
    rows.append(row)

# Read-only direct source and test imports: do not mistake imported helpers for WIP.
dependencies: dict[str, set[str]] = {}
for path in selector_paths:
    module = ast.parse((OLD / path).read_text("utf-8"))
    for node in ast.walk(module):
        if not isinstance(node, ast.ImportFrom):
            continue
        candidates = []
        if path.startswith(PREFIX) and node.level == 1 and node.module:
            candidates.append(PREFIX + node.module.replace(".", "/") + ".py")
        elif node.level == 0 and node.module and node.module.startswith(("company_wiki.", "tests.")):
            dotted = node.module.replace(".", "/")
            candidates.append(("src/" if dotted.startswith("company_wiki/") else "") + dotted + ".py")
        for dep in candidates:
            if dep != path and (OLD / dep).is_file():
                dependencies.setdefault(dep, set()).add(path)

direct_dependency_rows = []
for path, consumers in sorted(dependencies.items()):
    if path in selector_paths:
        disposition = "included_in_18_file_selector_write_set"
        base_raw = main_raw = None
    else:
        base_raw = git("show", data["old_base"] + ":" + path)
        main_raw = git("show", data["current_main"] + ":" + path)
        old_raw = (OLD / path).read_bytes()
        assert main_raw.replace(b"\r\n", b"\n") == old_raw.replace(b"\r\n", b"\n"), path
        disposition = "present_currentmain_eol_equivalent_to_old_dependency_keep_main"
    direct_dependency_rows.append({"path": path, "consumers": sorted(consumers), "disposition": disposition,
                                   "old_base_sha256": digest(base_raw) if base_raw is not None else None,
                                   "current_main_sha256": digest(main_raw) if main_raw is not None else None,
                                   "pending_worktree_sha256": digest((OLD / path).read_bytes())})

evidence_rows = [
    evidence(OLD, ".planning/w04-root-selector-recall/semantic-coverage-freeze.json", "business/stage/public routing15 pre-novelty files", "5-75"),
    evidence(OLD, ".planning/w04-root-selector-recall/BUDGET_INTERFACE.md", "low-level defaultlegacy and public0.8 policy", "3-11"),
    evidence(OLD, ".planning/w04-root-selector-recall/task_plan.md", "historical rootcause/failed recalls; later freeze supersedes pending nextstep"),
    evidence(OLD, ".planning/w04-wp02/task_plan.md", "STOP_PARTIAL historical business leaf; final roots handled by newer phases", "1-43"),
    evidence(OLD, ".planning/w04-wp02/progress.md", "historical247PASS and original replayFAIL retained"),
    evidence(OLD, "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w04_post_pw03_common_roots_2026-10-11/WP02_SELECTOR_INTERFACE_AMENDMENT.md", "public0.8 approved default, legacyexplicit, restored groups", "3-18"),
    evidence(OLD, "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w04_post_pw03_common_roots_2026-10-11/WP02_STAGE_CLASSIFICATION_AMENDMENT.md", "stage meaning, actual vs plan/financial mechanism", "3-13"),
    evidence(OLD, ".planning/w04-root-novelty-recall/phase2-real-recall/product-freeze.json", "final7productsfreeze2db879"),
    evidence(OLD, ".planning/w04-root-novelty-recall/phase2-real-recall/handoff.json", "RED/GREEN375PASS/ruff/mypy/failure history", "11-46"),
    evidence(OLD, ".planning/w04-root-novelty-recall/phase2-real-recall/concentrated-attempt3.json", "10 modules375PASS"),
    evidence(CANON, ".planning/w04-root-novelty-recall/independent-engineering/scope-controls.json", "correctpublicdefault/explicit0.7.1/low-levellegacy controls", "5-33"),
    evidence(CANON, ".planning/w04-root-novelty-recall/phase2-independent/manifest.json", "final independent freeze"),
    evidence(CANON, ".planning/w04-root-novelty-recall/phase2-independent/report.json", "17/17 independent engineering scope acceptance"),
    evidence(CANON, ".planning/w04-root-novelty-recall/phase2-independent/witness-inspection.json", "4/4 completegroup bound factual witnesses"),
    evidence(CANON, ".planning/w04-root-novelty-recall/native-novelty-six-quality-v2-execution.json", "actualfixedsixPASS87.4409sec/no mutation"),
    evidence(CANON, ".planning/w04-root-novelty-recall/native-novelty-six-quality-v2.json.gz", "ROOT actual six raw/golden/cap/completegroup recall"),
    evidence(OLD, ".planning/w04-g2-config/handoff.json", "separate G2 four files102PASS; excluded"),
]

manifest = {
    "schema_version": "w04-selector-integration-manifest/1",
    "status": "READ_ONLY_READY_FOR_ROOT_INTEGRATION_STOP",
    "generated_at": "2026-10-11",
    "base": {"tree": str(OLD), "commit": data["old_base"]},
    "main": {"tree": str(CANON), "commit": data["current_main"]},
    "sha_semantics": "oldbase/currentmain SHA are immutable Git blob bytes; pending SHA is exact current frozen worktree bytes. CRLF/LF normalized SHA is separate and only used for source/test comparison, never raw documents/evidence.",
    "selector_write_set_count": 18,
    "selector_sources_count": 8,
    "selector_tests_count": 10,
    "deferred_g2_count": 4,
    "excluded_ci_count": 3,
    "rows": rows,
    "direct_dependency_reads": direct_dependency_rows,
    "evidence": evidence_rows,
    "currentmain_other_source_changes_preserved": git("diff", "--name-only", data["old_base"], data["current_main"], "--", "src").decode("utf-8").splitlines(),
    "actual_main_conflicts_inside_selector": 0,
    "reserved_contract": "Existing protected reserve minimum-coverage prepass retained; quality ordering is within ordinary and reserved each, not global across channels.",
    "reuse_evidence": ["375PASS/RED evidence", "17 independent engineering checks", "fixed six-original replay and6 legacy package fingerprints", "4 complete-group subject-bound witness inspections"],
    "required_single_integration_batch": [
        "tests/unit/test_w04_selector_version_dispatch.py",
        "tests/integration/test_w04_semantic_budget_finalize.py",
        "tests/integration/test_w04_novelty_finalize.py",
        "tests/integration/test_w04_quality_band_budget.py",
    ],
    "testing_not_performed_by_this_preparation": True,
    "not_evaluated": ["summary semantic quality", "downstream RF forecast/research quality"],
    "git_products_config_raw_mutations": 0,
    "provider_network_llm_calls": 0,
    "cost_usd": 0,
    "integrity_snapshot": "three-tree-snapshot.json",
}
for row in rows:
    assert digest((OLD / row["path"]).read_bytes()) == row["pending_worktree"]["sha256"]
assert git("rev-parse", "HEAD").decode().strip() == data["current_main"]
(OUT / "integration-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"selector": 18, "sources": 8, "tests": 10, "deferred_g2": 4, "excluded_ci": 3,
                  "selector_conflicts": 0, "direct_dependencies": len(direct_dependency_rows),
                  "integration_manifest_sha256": digest((OUT / "integration-manifest.json").read_bytes())}))
