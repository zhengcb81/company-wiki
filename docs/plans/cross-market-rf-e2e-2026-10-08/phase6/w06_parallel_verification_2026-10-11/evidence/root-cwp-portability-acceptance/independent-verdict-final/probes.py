"""Non-author, bounded replay of the W06 finding outcome aggregation repair.

Reads frozen synthetic evidence and product source only. Does not rerun the
catalog/CLI scenes, access real originals, or mutate author products.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
WORKTREE = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-portability-root")
CANONICAL = Path("C:/Users/郑曾波/Projects/company-wiki")
FREEZE_PATH = BASE / "fix/verdict-aggregation/product-freeze.json"
EXPECTED_FREEZE = "ede6ae471e17ad5a77adb5a16c409b2b62617e53311bc96dd0e54083bb341bc3"
PRIOR = BASE / "independent-final"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canon_sha(value: object) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot(entries):
    return {entry["path"]: {"sha256": sha(WORKTREE / entry["path"]),
                            "byte_size": (WORKTREE / entry["path"]).stat().st_size}
            for entry in entries}


assert sha(FREEZE_PATH) == EXPECTED_FREEZE
freeze = load(FREEZE_PATH)
final_path = BASE / "fix/verdict-aggregation/final-node.json"
real_path = BASE / "fix/verdict-aggregation/real-run-report.json"
assert sha(final_path) == freeze["final_node_sha256"]
assert sha(real_path) == freeze["real_report_sha256"]
assert sha(PRIOR / "report.json") == freeze["independent_fail_sha256"]
previous_freeze_path = BASE / "fix/product-freeze.json"
assert sha(previous_freeze_path) == freeze["previous_freeze_sha256"]
previous_freeze = load(previous_freeze_path)
old_product_shas = {item["path"]: item["sha256"] for item in previous_freeze["files"]}
changed_products = [item["path"] for item in freeze["files"]
                    if old_product_shas[item["path"]] != item["sha256"]]
assert changed_products == freeze["changed_within_original_11"]
assert set(changed_products) == {"tools/source_root_portability/oracle.py",
                                "tools/source_root_portability/run.py",
                                "tests/unit/test_w06_root_portability_oracle.py"}
final = load(final_path)
new_record = load(real_path)
vectors = load(PRIOR / "counterexamples.json")
old_record_path = BASE / "fix/final-refresh/real-run-report.json"
assert sha(old_record_path) == vectors["base_report_sha256"]
old_record = load(old_record_path)
assert load(PRIOR / "report.json")["verdict"] == "FAIL_NEW_ORACLE_EXPECTATION_CLASSIFICATION"
products_before = snapshot(freeze["files"])
producer_before = snapshot(final["production_before"])
assert len(products_before) == 11 and len(producer_before) == 8
assert all(products_before[e["path"]]["sha256"] == e["sha256"]
           and products_before[e["path"]]["byte_size"] == e["byte_size"]
           for e in freeze["files"])
assert all(producer_before[e["path"]]["sha256"] == e["sha256"]
           for e in final["production_before"])
historical_before = {str(p.relative_to(BASE)): sha(p)
                     for p in PRIOR.rglob("*") if p.is_file()}
historical_before[str(old_record_path.relative_to(BASE))] = sha(old_record_path)

sys.path[:0] = [str(WORKTREE / "src"), str(WORKTREE)]
from tools.source_root_portability import oracle
executed_oracle = Path(oracle.__file__).resolve()
assert executed_oracle == (WORKTREE / "tools/source_root_portability/oracle.py").resolve()
assert sha(executed_oracle) == products_before["tools/source_root_portability/oracle.py"]["sha256"]

started = time.monotonic()
results = []


def observe(name: str, verdict, expected: str, *, scenario: str | None = None,
            expected_scenario: str | None = None, input_sha: str | None = None):
    item = {"name": name, "expected": expected, "actual": verdict.overall,
            "statuses": verdict.statuses,
            "findings": [{"code": f.code, "scenario_id": f.scenario_id,
                          "detail": f.detail, "outcome": f.outcome}
                         for f in verdict.findings],
            "as_expected": verdict.overall == expected}
    if scenario is not None:
        item.update(scenario_id=scenario, expected_scenario=expected_scenario,
                    actual_scenario=verdict.statuses.get(scenario))
        item["as_expected"] &= verdict.statuses.get(scenario) == expected_scenario
    if input_sha is not None:
        item["canonical_effective_input_sha256"] = input_sha
    results.append(item)


def scene(record, scene_id):
    return next(item for item in record["scenarios"] if item["id"] == scene_id)


scratch_parent = CANONICAL / ".tmp"
assert scratch_parent.is_dir()
scratch = Path(tempfile.mkdtemp(prefix="w6-vind-", dir=scratch_parent)).resolve()
assert scratch.parent == scratch_parent.resolve() and scratch.name.startswith("w6-vind-")
try:
    (scratch / "owned-only.txt").write_text("independent verdict scratch", encoding="utf-8")
    # The exact prior inputs, not regenerated from the author's new passing run.
    for vector in vectors["counterexamples"]:
        value = copy.deepcopy(old_record)
        for action in vector["json_patch"]:
            assert action["op"] == "replace"
            path = action["path"].strip("/").split("/")
            cursor = value
            for token in path[:-1]:
                cursor = cursor[int(token)] if isinstance(cursor, list) else cursor[token]
            last = int(path[-1]) if isinstance(cursor, list) else path[-1]
            assert cursor[last] == vector["original_value"]
            cursor[last] = action["value"]
        effective_sha = canon_sha(value)
        assert effective_sha == vector["canonical_effective_input_sha256"]
        observe(vector["name"], oracle.evaluate_run(value), "FAIL",
                scenario="S2", expected_scenario="FAIL", input_sha=effective_sha)

    # Legitimate existing evidence remains passing under the current oracle.
    observe("old_frozen_7_scene_positive", oracle.evaluate_run(old_record), "PASS")
    observe("current_frozen_7_scene_positive", oracle.evaluate_run(new_record), "PASS")

    # Both public Finding constructor and the check helper default to failure;
    # their names are unrelated to the formerly whitelisted prefixes.
    for name, finding in (
        ("Finding_constructor_default", oracle.Finding("contract-zeta", "S1", "mandatory violation")),
        ("finding_helper_default", oracle._finding("entirely-new-rule", "S1", "mandatory violation")),
    ):
        assert finding.outcome == "FAIL"
        observe(name, oracle._aggregate_verdict({"S1": "PASS"}, [finding]),
                "FAIL", scenario="S1", expected_scenario="FAIL")

    # Independent priority model covers every base state and explicit outcome,
    # including None diagnostics. Adding a finding must never weaken a state.
    priority = {"PASS": 0, "UNKNOWN": 1, "PARTIAL": 2, "FAIL": 3, "INVALID_RECORD": 4}
    for status, outcome in itertools.product(priority, (None, *priority)):
        original = {"S1": status}
        preserved = copy.deepcopy(original)
        expected = status if outcome is None else max((status, outcome), key=priority.__getitem__)
        finding = oracle.Finding("no-special-prefix", "S1", "typed observation", outcome)
        verdict = oracle._aggregate_verdict(original, [finding])
        assert original == preserved
        assert verdict.findings == (finding,)
        observe(f"priority_{status}_plus_{outcome}", verdict, expected,
                scenario="S1", expected_scenario=expected)

    for index, order in enumerate(itertools.permutations(("UNKNOWN", "PARTIAL", "FAIL"))):
        findings = [oracle.Finding("arbitrary-name", "S1", "observation", value)
                    for value in order]
        verdict = oracle._aggregate_verdict({"S1": "PASS", "S2": "UNKNOWN"}, findings)
        assert verdict.statuses["S2"] == "UNKNOWN"
        observe(f"order_independent_{index}", verdict, "FAIL",
                scenario="S1", expected_scenario="FAIL")

    # Public entry point receives a newly named mandatory check: no code-list
    # registration is required. A false_pass title with explicit None remains
    # only a diagnostic, and invalid outcome types become structured invalid.
    for name, outcome, code, expected in (
        ("public_unfamiliar_mandatory_check", "FAIL", "new-contract-9", "FAIL"),
        ("public_diagnostic_false_pass_title", None, "false_pass_just_a_note", "PASS"),
        ("public_unknown_outcome", "UNRECOGNIZED", "new-contract-9", "INVALID_RECORD"),
        ("public_wrong_outcome_type", {}, "new-contract-9", "INVALID_RECORD"),
    ):
        def check(scenario, record, findings, outcome=outcome, code=code):
            findings.append(oracle.Finding(code, "S1", "injected independent contract", outcome))
        with patch.dict(oracle._SCENARIO_CHECKS, {"S1": check}):
            observe(name, oracle.evaluate_run(copy.deepcopy(new_record)), expected)

    value = copy.deepcopy(new_record)
    value["findings"] = [{"code": name, "detail": "observation only"} for name in
                         ("document_id_relation", "policy_sha_changed", "blocked_socket_bind",
                          "host_symlink_skip", "disabled_asyncio_plugin_warning")]
    observe("ordinary_report_diagnostics_not_permission_gates", oracle.evaluate_run(value), "PASS")
    value = copy.deepcopy(new_record)
    scene(value, "S3")["status"] = "UNKNOWN"
    observe("honest_UNKNOWN", oracle.evaluate_run(value), "UNKNOWN",
            scenario="S3", expected_scenario="UNKNOWN")
    value = copy.deepcopy(new_record)
    scene(value, "S2").update(status="PARTIAL", failure={"code": "coverage-gap", "detail": "not complete"})
    observe("honest_PARTIAL", oracle.evaluate_run(value), "PARTIAL",
            scenario="S2", expected_scenario="PARTIAL")
    value = copy.deepcopy(new_record)
    value["cleanup"]["restored"] = False
    observe("cleanup_not_complete_without_lost_bytes", oracle.evaluate_run(value), "PARTIAL")
    observe("global_contract_failure", oracle._aggregate_verdict(
        {"S1": "PASS"}, [oracle.Finding("global-new-rule", None, "mandatory failure")]), "FAIL",
        scenario="S1", expected_scenario="PASS")

    # Receipt checks support only the author's bounded synthetic run; they are
    # not a new native execution or a claim of real financial-document coverage.
    assert final["tests"]["exit"] == 0
    assert final["tests"]["summary"] == ["69 passed, 1 skipped, 1 warning in 9.07s"]
    assert final["runner"]["exit"] == 0 and final["runner"]["seconds"] == 4.051
    assert final["runner_oracle"]["overall"] == "PASS"
    assert final["runner_oracle"]["statuses"] == {f"S{i}": "PASS" for i in range(1, 8)}
    assert final["products"] == final["products_after"]
    assert final["production_before"] == final["production_after"]
    assert final["sentinels_before"] == final["sentinels_after"]
    assert final["existing_empty_directories_preserved"] is True
    assert final["temporary_restored_absent"] is True
    assert final["owned_new_children_remaining"] == []
    assert all(final[k] == 0 for k in ("network_calls", "provider_calls", "LLM_calls",
                                       "fees_usd", "real_raw_accessed"))
finally:
    assert scratch.resolve().parent == scratch_parent.resolve()
    assert scratch.name.startswith("w6-vind-")
    shutil.rmtree(scratch)

products_after = snapshot(freeze["files"])
producer_after = snapshot(final["production_before"])
historical_after = {str(p.relative_to(BASE)): sha(p)
                    for p in PRIOR.rglob("*") if p.is_file()}
historical_after[str(old_record_path.relative_to(BASE))] = sha(old_record_path)
assert products_before == products_after
assert producer_before == producer_after
assert historical_before == historical_after
assert not scratch.exists()
unexpected = [item for item in results if not item["as_expected"]]
payload = {"schema_version": "w06-portability-independent-verdict-final/1",
           "status": "PASS_WITH_SCOPE" if not unexpected else "BLOCKER",
           "results": results, "case_count": len(results), "unexpected": unexpected,
           "seconds": round(time.monotonic() - started, 3),
           "original_four_input_shas_match": True,
           "freeze_sha256": EXPECTED_FREEZE,
           "executed_oracle_file": str(executed_oracle),
           "executed_oracle_sha256": sha(executed_oracle),
           "changed_products_from_previous_freeze": changed_products,
           "products_before": products_before, "products_after": products_after,
           "producer_before": producer_before, "producer_after": producer_after,
           "old_independent_fail_before": historical_before,
           "old_independent_fail_after": historical_after,
           "scratch_path": str(scratch), "scratch_restored_absent": True,
           "author_receipts": {"final_node_sha256": sha(final_path),
                               "real_run_report_sha256": sha(real_path),
                               "test_summary": final["tests"]["summary"],
                               "synthetic_runner_seconds": final["runner"]["seconds"],
                               "native_scenes_not_rerun": True},
           "scope": "Pure finding aggregation replay and frozen Windows synthetic receipts only",
           "network_calls": 0, "provider_calls": 0, "LLM_calls": 0,
           "fees_usd": 0, "real_originals_accessed": 0}
(HERE / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": payload["status"], "cases": len(results),
                  "unexpected": len(unexpected), "seconds": payload["seconds"],
                  "products_and_producers_unchanged": True,
                  "original_FAIL_preserved": True, "scratch_restored_absent": True}))
raise SystemExit(bool(unexpected))
