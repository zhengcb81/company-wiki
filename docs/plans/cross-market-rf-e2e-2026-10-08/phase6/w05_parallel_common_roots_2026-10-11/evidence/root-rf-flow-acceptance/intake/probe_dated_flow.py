"""Read-only independent probes against the frozen W05-RF-FLOW leaf."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

LEAF = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow")
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(LEAF / "scripts"), str(LEAF / "tests")]
from revenue_core import run_forecast, validate_document
from revenue_report import validate_forecast_output, validate_published_forecast
from test_w05_dated_contribution_contract import add_window_parameter, parameter, schema_3_10_document
from test_w05_dated_contribution_output import add_acquisition_adjustment


def outcome(name, builder, expectation):
    data = builder()
    try:
        validated = validate_document(data)
        result = run_forecast(data)
        validate_published_forecast(result, data)
        validate_forecast_output(result)
        value = validated["parameter_index"].get("cmp_fy2026_low", {}).get("value")
        return {"case": name, "expected": expectation, "actual": "accepted", "strong_readers": "PASS", "composed_value": value,
                "fy2026_low": result["consolidated_forecast"]["low"]["annual_revenue"]["2026"]}
    except Exception as exc:
        return {"case": name, "expected": expectation, "actual": "rejected", "exception": type(exc).__name__, "detail": str(exc)}


def valid_document():
    data = schema_3_10_document()
    add_acquisition_adjustment(data)
    return data


def annual_alias():
    data = valid_document()
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(time_basis="annual", formula="x0", input_parameter_ids=["cmp_post_2026"], value=1.29190208)
        target.pop("period_start")
        target.pop("period_end")
        target.pop("rationale")
    return data


def outside_window():
    data = valid_document()
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(period="FY2027", period_start="2027-01-01", period_end="2027-12-31",
                      rationale="explicit composition, fixture")
    # Keep these as supporting facts so the annual-adjustment year validator is
    # not the unrelated rejection. The full document still owns all dates.
    data.pop("forecast_adjustments")
    return data


def overlap():
    data = valid_document()
    add_window_parameter(data, "same_revenue_h1", 55.0, "2026-01-01", "2026-06-30", 2026,
                         definition="Segment A recognized revenue")
    add_window_parameter(data, "same_revenue_q2", 30.0, "2026-04-01", "2026-06-30", 2026,
                         definition="Segment A recognized revenue")
    for scenario in ("low", "base", "high"):
        target = parameter(data, f"cmp_fy2026_{scenario}")
        target.update(formula="x0+x1", input_parameter_ids=["same_revenue_h1", "same_revenue_q2"], value=85.0,
                      definition="Segment A recognized revenue", rationale="Q2 is a subset of H1; overlap is intentional")
    return data


def negative_disposal():
    data = valid_document()
    for item in data["parameters"]:
        if item["parameter_id"].startswith("cmp_"):
            item["value"] = -0.01 * item["value"]
    for claim in data["evidence_claims"]:
        if str(claim.get("target_id", "")).startswith("cmp_"):
            claim["extracted_value"] = -0.01 * claim["extracted_value"]
    data["forecast_adjustments"][0]["category"] = "disposal_contribution"
    return data


def manifest_checks():
    handoff = json.loads((LEAF / "docs/handoffs/w05-rf-flow/handoff.json").read_text(encoding="utf-8"))
    manifest = json.loads((LEAF / "docs/handoffs/w05-rf-flow/manifest.json").read_text(encoding="utf-8"))
    rows = manifest.get("files", manifest.get("artifacts", []))
    failures = []
    for item in handoff["changed_files"] + rows:
        path = LEAF / item["path"]
        if not path.is_file():
            failures.append({"path": item["path"], "reason": "absent"})
            continue
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != item["sha256"] or ("bytes" in item and len(content) != item["bytes"]):
            failures.append({"path": item["path"], "reason": "digest/size mismatch", "actual_sha256": digest,
                             "actual_bytes": len(content)})
    return {"checked_records": len(handoff["changed_files"]) + len(rows), "failures": failures}


if __name__ == "__main__":
    deterministic_input = valid_document()
    deterministic = run_forecast(deterministic_input) == run_forecast(deterministic_input)
    payload = {"project_calls": 0, "product_writes": 0, "manifest": manifest_checks(),
               "same_input_outputs_identical": deterministic,
               "probes": [outcome("valid_post_control_bridge", valid_document, "accept"),
                          outcome("annual_alias_of_partial_flow", annual_alias, "reject"),
                          outcome("rationale_cannot_move_2026_amount_to_2027", outside_window, "reject"),
                          outcome("same_perimeter_h1_plus_own_q2", overlap, "reject"),
                          outcome("negative_disposal_window_flow", negative_disposal, "accept")]}
    (OUT / "counterexamples.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
