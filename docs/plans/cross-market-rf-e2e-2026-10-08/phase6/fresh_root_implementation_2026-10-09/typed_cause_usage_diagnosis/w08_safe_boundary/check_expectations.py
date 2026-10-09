"""Evaluate expected W08 boundary contracts against retained real observations.

Exit 1 is intentional on the unchanged diagnosed code: these are preserved RED
contracts, not green tests weakened to fit implementation. No provider is run.
"""
import json
from pathlib import Path

from reproduce import write_json

HERE = Path(__file__).parent


def main() -> int:
    first = json.loads((HERE / "observations.json").read_text(encoding="utf-8"))
    boundary = json.loads((HERE / "boundary-controls.json").read_text(encoding="utf-8"))
    wire = json.loads((HERE / "wire-controls.json").read_text(encoding="utf-8"))
    cases = {row["mode"]: row for row in first["cases"] + boundary["cases"]}
    controls = {row["name"]: row for row in wire["wire_controls"]}
    checks = []

    def check(name, actual, expected, reference):
        checks.append({"id": name, "passed": actual == expected, "actual": actual,
                       "expected": expected, "reference": reference})

    for mode in ("discover-fail", "bad_receipt", "deadline"):
        case = cases[mode]
        original = case["cwp"]["payload"]["acquisition_failure"]
        ff = case["ff"]["payload"]["filing"]
        check(mode + "_FF_operation_usage_continuity", ff.get("acquisition_failure"), original,
              ("boundary-controls.json" if mode == "deadline" else "observations.json") + "/cases/" + mode)
        check(mode + "_RF_known_cause_continuity", case["rf_prepare"]["payload"].get("upstream_cause"), ff.get("upstream_cause"),
              "retained CLI /" + mode)
    check("malformed_usage_stays_null", cases["malformed_usage"]["cwp"]["payload"]["acquisition_failure"]["acquisition_usage"], None,
          "observations.json/cases/malformed_usage")
    check("malformed_completeness_stays_unknown", cases["malformed_usage"]["rf_prepare"]["payload"]["upstream_cause"]["usage_complete"], None,
          "observations.json/cases/malformed_usage")
    metadata = cases["local_metadata_gap"]
    check("metadata_cause_is_machine_readable_at_FF", metadata["ff"]["payload"]["filing"].get("upstream_cause", {}).get("code"), "local_metadata_gap",
          "boundary-controls.json/cases/local_metadata_gap")
    check("metadata_cause_is_machine_readable_at_RF", metadata["rf_prepare"]["payload"].get("upstream_cause", {}).get("code"), "local_metadata_gap",
          "boundary-controls.json/cases/local_metadata_gap")
    check("RF_actual_subprocess_counts_are_retained", {key: metadata["rf_prepare"]["payload"].get(key) for key in ("calls", "downloads")},
          {"calls": 3, "downloads": 0}, "boundary-controls.json/cases/local_metadata_gap")
    check("FF_v2_stage_is_retained", metadata["ff"]["payload"]["filing"].get("stage"), "local_prepare",
          "boundary-controls.json/cases/local_metadata_gap")
    for name in ("untrusted_top_level_error", "untrusted_stderr", "untrusted_success_exit_reason"):
        check(name + "_never_echo_synthetic_secret", controls[name]["rf_prepare"]["synthetic_sentinel_leaked"], False,
              "wire-controls.json/wire_controls/" + name)
    check("RF_reader_failure_retains_already_observed_counts", {key: controls["post_selection_reader_failure"]["rf_prepare"]["payload"].get(key) for key in ("calls", "downloads")},
          {"calls": 2, "downloads": 1}, "wire-controls.json/wire_controls/post_selection_reader_failure")
    value = {"schema_version": "w08-retained-contract-red/1", "checks": checks,
             "passed": sum(row["passed"] for row in checks), "failed": sum(not row["passed"] for row in checks),
             "skip": 0, "source_not_modified": True}
    write_json(HERE / "contract-red.json", value)
    print(json.dumps({key: value[key] for key in ("passed", "failed", "skip")}))
    return int(bool(value["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
