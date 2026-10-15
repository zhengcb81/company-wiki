"""Report the real retained-packet walkthrough (lane evidence, not a test).

Run from the worktree root::

    PYTHONPATH=src python -B tests/unit/du4_table_measurements/report_real_packet.py --output <owned-test-output.json>

Prints JSON or writes an explicit test output path, preserving author receipts,
with the retained bound/ambiguous/unavailable counts and value refs per table,
budget usage and elapsed-time observations (no thresholds).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / 'tests'))

from unit.du4_table_measurements.real_packet import all_tables, project_table  # noqa: E402

from company_wiki.document_understanding.layout_hints.contract import WorkBudget  # noqa: E402
from company_wiki.document_understanding.table_measurements import bind_operating_table  # noqa: E402

def _ref(ref: dict, units: dict) -> dict:
    text = units[ref["unit_id"]]["text"][ref["char_start"] : ref["char_end"]]
    return {**ref, "text": text[:80]}


def main(output: Path | None = None) -> None:
    report: dict = {"tables": {}, "budget_observations": []}
    totals = {"bound": 0, "ambiguous": 0, "unavailable": 0}
    for page, table_index in all_tables():
        obs, facts = project_table(page, table_index)
        b = WorkBudget(max_work_units=500_000)
        started = time.perf_counter()
        result = bind_operating_table(obs, work_budget=b)
        elapsed_ms = (time.perf_counter() - started) * 1000
        units = obs["units"]
        counts = {"bound": 0, "ambiguous": 0, "unavailable": 0}
        entries = []
        for m in result["measurements"]:
            counts[m["binding_status"]] += 1
            entries.append(
                {
                    "binding_status": m["binding_status"],
                    "value_ref": _ref(m["value_ref"], units),
                    "column_id": m["column_id"],
                    "period": (
                        {k: v for k, v in m["period"].items() if k != "raw_label_refs"}
                        if m["period"]
                        else None
                    ),
                    "row_label_refs": [_ref(r, units) for r in m["row_label_refs"]],
                    "unit_refs": [_ref(r, units) for r in m["unit_refs"]],
                }
            )
        for key in totals:
            totals[key] += counts[key]
        report["tables"][f"p{page}t{table_index}"] = {
            "facts": facts,
            "status": result["status"],
            "counts": counts,
            "columns": [
                {
                    "native_column": c["native_column"],
                    "status": c["status"],
                    "period": {k: v for k, v in c["period"].items() if k != "raw_label_refs"},
                    "header_refs": [_ref(r, units) for r in c["header_refs"]],
                }
                for c in result["columns"]
            ],
            "measurements": entries,
            "unbound_value_refs": [_ref(r, units) for r in result["unbound_value_refs"]],
            "diagnostic_codes": sorted({d["code"] for d in result["diagnostics"]}),
            "work_used": result["work_used"],
            "elapsed_ms": round(elapsed_ms, 3),
        }
    report["totals"] = totals

    obs0, _ = project_table(14, 0)
    for cap in (0, 5, 50, 400):
        b = WorkBudget(max_work_units=cap)
        result = bind_operating_table(obs0, work_budget=b)
        report["budget_observations"].append(
            {
                "max_work_units": cap,
                "status": result["status"],
                "work_used": result["work_used"],
                "measurements_kept": len(result["measurements"]),
                "exhausted_diagnostic": any(
                    d["code"] == "work_budget_exhausted" for d in result["diagnostics"]
                ),
            }
        )
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if output is None:
        print(encoded)
    else:
        output.write_text(encoded, encoding="utf-8")
        print("totals:", totals)


if __name__ == "__main__":
    import argparse
    args = argparse.ArgumentParser()
    args.add_argument('--output', type=Path)
    main(args.parse_args().output)
