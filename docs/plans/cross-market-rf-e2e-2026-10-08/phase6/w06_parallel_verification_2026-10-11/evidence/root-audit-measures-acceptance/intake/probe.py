"""Independent bounded W06 acceptance probes; no providers, source bytes or product writes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

LEAF = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures")
OUT = Path(__file__).resolve().parent

def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

handoff = json.loads((LEAF / "docs/handoffs/w06-audit-measures/handoff.json").read_text(encoding="utf-8"))
manifest = json.loads((LEAF / "docs/handoffs/w06-audit-measures/manifest.json").read_text(encoding="utf-8"))
verified = []
for group, rows in (("changed", handoff["changed_files"]), ("input", handoff["input_evidence"]), ("manifest", manifest["files"])):
    for row in rows:
        data = (LEAF / row["path"]).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        verified.append({"group": group, "path": row["path"], "sha256": actual, "bytes": len(data),
                         "sha_match": actual == row["sha256"],
                         "size_match": "bytes" not in row or row["bytes"] == len(data)})
dump("sha-verification.json", verified)

spec = importlib.util.spec_from_file_location("worker_tests_helpers", LEAF / "tests/test_financial_measure_audit.py")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
obs, flow, rel, res, ledger = helpers.obs, helpers.flow, helpers.rel, helpers.res, helpers.ledger

source = flow("revenue", "1.2", scale="billion")
out = flow("converted", "12", scale="亿")
convert = rel("conversion", "scale_conversion", ["revenue"], out)
valid = ledger([source], [convert])
cases = [("control_scale_conversion", valid, {"PASS"})]

def alter(name, fn, acceptable={"INVALID", "FAIL", "UNRESOLVED"}):
    sample = copy.deepcopy(valid)
    fn(sample)
    cases.append((name, sample, acceptable))

alter("conversion_changes_company_definition_and_time", lambda s: s["relations"][0]["result"].update(
    entity_key="other-company", definition="cash_balance", measure_kind="stock",
    point_date="2025-12-31", period_start=None, period_end=None))
alter("conversion_result_missing_source_ref", lambda s: s["relations"][0]["result"].update(source_ref=None))
alter("conversion_result_missing_window", lambda s: s["relations"][0]["result"].update(period_start=None, period_end=None))
alter("conversion_multiple_operands_ignored", lambda s: s["relations"][0]["inputs"].append("revenue"), {"INVALID"})
alter("unsupported_schema_is_silently_accepted", lambda s: s.update(schema_version="financial-measure-ledger/999"), {"INVALID"})
alter("malformed_as_of_is_silently_accepted", lambda s: s.update(as_of_date="not-a-date"), {"INVALID"})
alter("malformed_observation_id_list", lambda s: s["observations"][0].update(id=[]), {"INVALID"})
alter("malformed_scale_list", lambda s: s["observations"][0].update(scale=[]), {"INVALID"})
alter("malformed_relation_input_object", lambda s: s["relations"][0].update(inputs=[{}]), {"INVALID"})
alter("blank_relation_id_accepted", lambda s: s["relations"][0].update(relation_id=""), {"INVALID"})

sum_ledger = ledger([flow("h1", "100", start="2024-01-01", end="2024-06-30"),
                     flow("h2", "80", start="2024-07-01", end="2024-12-31")],
                    [rel("sum", "sum", ["h1", "h2"], flow("fy", "180"))])
cases.append(("control_contiguous_sum", copy.deepcopy(sum_ledger), {"PASS"}))
sample = copy.deepcopy(sum_ledger)
sample["relations"][0]["result"].update(currency="CNY", entity_key="other-company", definition="net_profit")
cases.append(("sum_output_silently_relabels_currency_entity_definition", sample, {"INVALID", "FAIL"}))
sample = copy.deepcopy(sum_ledger)
sample["observations"][0].update(period_start=None, period_end=None)
cases.append(("missing_flow_anchor_should_diagnose_not_crash", sample, {"UNRESOLVED", "INVALID"}))
sample = ledger([flow("now", "120", start="2024-01-01", end="2024-12-31"),
                 flow("base", "100", start="2023-01-01", end="2023-03-31")],
                [rel("g", "growth_rate", ["now", "base"],
                     res("growth", "20", "percent", None, "growth", period_start="2024-01-01", period_end="2024-12-31"))])
cases.append(("annual_vs_quarter_called_growth", copy.deepcopy(sample), {"INVALID", "FAIL", "UNRESOLVED"}))
sample["observations"][1].update(period_end="2023-12-31", entity_key="other-company")
cases.append(("growth_between_different_companies", sample, {"INVALID", "UNRESOLVED"}))
sample = ledger([flow("a", "120")], [rel("d", "difference", ["a"], flow("delta", "20"))])
cases.append(("difference_one_operand_should_diagnose_not_crash", sample, {"INVALID"}))
sample = ledger([flow("revenue", "20"),
                 obs("cash", "100", "million", "USD", "stock", definition="cash_balance", point_date="2024-12-31")],
                [rel("s", "share", ["revenue", "cash"],
                     res("share", "20", "percent", None, "ratio", period_start="2024-01-01", period_end="2024-12-31"),
                     scope_inclusion="revenue_part_of_cash")])
cases.append(("flow_revenue_divided_by_stock_cash_called_share", sample, {"INVALID", "FAIL", "UNRESOLVED"}))
sample = ledger([flow("tiny", "0.0000001"), flow("whole", "1")],
                [rel("s", "share", ["tiny", "whole"],
                     res("share", "0.49", "decimal", None, "ratio", period_start="2024-01-01", period_end="2024-12-31"),
                     scope_inclusion="tiny_subset_of_whole", absolute_tolerance="0.499")])
cases.append(("subunit_tolerance_masks_multimillion_factor_error", sample, {"INVALID", "FAIL"}))

results = []
for name, sample, acceptable in cases:
    began = time.monotonic()
    try:
        report = helpers.module.audit_measures(sample)
        actual = report["overall"]
        result = {"id": name, "expected_statuses": sorted(acceptable), "actual_status": actual,
                  "passes_expectation": actual in acceptable, "report": report}
    except Exception as exc:
        result = {"id": name, "expected_statuses": sorted(acceptable), "actual_status": "EXCEPTION",
                  "passes_expectation": False, "exception": f"{type(exc).__name__}: {exc}"}
    result["elapsed_seconds"] = round(time.monotonic() - began, 6)
    result["ledger"] = sample
    results.append(result)
dump("counterexamples.json", {"schema_version": "w06-independent-measure-probes/1", "head": "6a50d7ed1b4cf389589c7ca62b4ab161b5dc0ad1",
                              "source_truth_verified": False, "economic_reasonableness": "not_evaluated", "cases": results})

test_runs = []
for pattern in ("test_financial_measure*.py", "test_numeric_audit.py"):
    command = [sys.executable, "-B", "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-p", pattern, "-v"]
    started = time.monotonic()
    proc = subprocess.run(command, cwd=LEAF, capture_output=True, encoding="utf-8", timeout=30)
    log = OUT / ("replay-financial-tests.log" if pattern.startswith("test_financial") else "replay-numeric-tests.log")
    log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    test_runs.append({"command": command, "cwd": str(LEAF), "exit_code": proc.returncode,
                      "elapsed_seconds": round(time.monotonic() - started, 6), "log": log.name,
                      "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
dump("test-replay.json", test_runs)
print(json.dumps({"sha_records": len(verified), "sha_failures": sum(not r["sha_match"] or not r["size_match"] for r in verified),
                  "probe_cases": len(results), "expectation_failures": [r["id"] for r in results if not r["passes_expectation"]],
                  "tests": test_runs}, ensure_ascii=False))
