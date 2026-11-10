#!/usr/bin/env python3
"""Read-only economic support diagnostics (economic-support-diagnostics/1).

Reads one native forecast input, validates it and reports, for every
segment x year x scenario, whether the revenue-bearing parameters are
covered by a referenced-range calibration. Independent observed-range
endpoints may sit outside the revenue DAG; actual conversions and outputs
must bind to the real native business scope and period.

The CLI performs no forecast computation, never writes the input, sources
or any publication registry, and starts no model or download. A non-green
cell is a diagnostics statement with concrete calibration/parameter/claim
IDs — not a buyer-grade economic quality certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from contracts.constants import SCENARIOS
from revenue_core import validate_document
from research.evidence_roles import analyze_operating_research
from research.native_dependencies import segment_roots

DIAGNOSTICS_SCHEMA_VERSION = "economic-support-diagnostics/1"


def _covering_calibrations_for_cell(
    calibrations: list[dict], *, segment: str, scenario: str, year: int,
    company: str, roots: list[str], parameters: dict,
) -> dict[str, set[str]]:
    """Bind support to the actual cell; a shared PID is not a shared scope."""
    covering: dict[str, set[str]] = {}
    for calibration in calibrations:
        if calibration["scope"] not in {company, segment}:
            continue
        output = calibration["scenario_output_parameter_ids"][scenario]
        if output in roots and parameters[output]["period"] == f"FY{year}":
            covering.setdefault(output, set()).add(calibration["calibration_id"])
    return covering


def build_support_diagnostics(data: dict, input_sha256: str) -> dict:
    validated = validate_document(data)
    adequacy = analyze_operating_research(data, validated) if data.get("operating_research") is not None else None
    calibrations = adequacy["calibrations"] if adequacy is not None else []
    referenced = []
    demoted = []
    for calibration in calibrations:
        if calibration["adequacy_status"] == "referenced_range":
            referenced.append(calibration)
        else:
            demoted.append(calibration)
    segments = []
    for segment in data.get("segments", []):
        entries = []
        scenario_keys = [s for s in SCENARIOS if s in segment.get("scenarios", {})]
        for scenario in scenario_keys:
            for year in data["forecast_years"]:
                roots = segment_roots(data, segment, scenario, year)
                covering = _covering_calibrations_for_cell(
                    referenced, segment=segment["name"], scenario=scenario, year=year,
                    company=data["company_name"], roots=roots,
                    parameters=validated["parameter_index"],
                )
                supported = sorted({p for p in roots if p in covering})
                unsupported = sorted({p for p in roots if p not in covering})
                reasons = []
                if adequacy is None:
                    reasons = ["no_optional_operating_research_declared"]
                else:
                    reasons = [f"parameter_without_referenced_range_calibration:{p}" for p in unsupported]
                    covering_ids = {calibration_id for p in supported for calibration_id in covering[p]}
                    for calibration in referenced:
                        if calibration["calibration_id"] not in covering_ids:
                            reasons.append(f"calibration_scope_not_covering:{calibration['calibration_id']}:{segment['name']}")
                    for calibration in demoted:
                        reasons.extend(f"calibration_not_referenced_range:{calibration['calibration_id']}:{reason}"
                                       for reason in calibration["reasons"])
                if roots and not unsupported:
                    status = "supported"
                elif supported and unsupported:
                    status = "conditional"
                else:
                    status = "unsupported"
                cell_calibration_ids = sorted({calibration_id for p in supported for calibration_id in covering[p]})
                claim_ids = sorted({claim for calibration in referenced
                                    if calibration["calibration_id"] in set(cell_calibration_ids)
                                    for claim in calibration["source_claim_ids"]})
                entries.append({"scenario": scenario, "year": str(year), "status": status,
                                "reasons": reasons, "supported_parameter_ids": supported,
                                "unsupported_parameter_ids": unsupported,
                                "calibration_ids": cell_calibration_ids, "claim_ids": claim_ids})
        segments.append({"segment": segment["name"], "entries": entries})
    return {"schema_version": DIAGNOSTICS_SCHEMA_VERSION,
            "input_sha256": input_sha256,
            "requested_years": [str(y) for y in data["forecast_years"]],
            "company": data.get("company_name"),
            "segments": segments,
            "economic_truth_inferred": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only economic support diagnostics over one native forecast input.")
    parser.add_argument("--input", required=True, help="Path to the native forecast input JSON (read-only).")
    parser.add_argument("--output", help="New output path for the diagnostics JSON; omit to print to stdout. Existing files are not overwritten.")
    args = parser.parse_args(argv)
    source = Path(args.input)
    try:
        payload = source.read_bytes()
        data = json.loads(payload.decode("utf-8"))
    except (OSError, ValueError) as exc:
        print(f"cannot read input {source}: {exc}", file=sys.stderr)
        return 2
    try:
        diagnostics = build_support_diagnostics(data, hashlib.sha256(payload).hexdigest())
    except Exception as exc:  # fail closed on any contract violation
        print(f"input rejected: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(diagnostics, ensure_ascii=False, indent=1) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
        return 0
    target = Path(args.output)
    if target.exists():
        print(f"refusing to overwrite existing output {target}", file=sys.stderr)
        return 2
    target.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
