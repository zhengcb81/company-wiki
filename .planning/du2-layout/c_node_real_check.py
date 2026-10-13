"""Write C-node evidence for DU2-LAYOUT: probe mapping + result summary.

Runs derive_layout_hints over the real probes (span and row_collapse modes),
summarises the structural outcome per sample and writes bounded evidence:
probe-id -> page/bbox mapping (quotes capped at 8 KiB per source) plus a short
comparison note.  Inspection entry point only: it reads originals read-only
and never copies them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests" / "fixtures" / "document_understanding_layout_hints"))

import real_probe  # noqa: E402

from company_wiki.document_understanding.layout_hints import derive_layout_hints  # noqa: E402


def summarise(result: dict) -> dict:
    regions = [g for g in result["groups"] if g["kind"] == "table_region"]
    rows = [g for g in result["groups"] if g["kind"] == "table_row"]
    return {
        "groups": len(result["groups"]),
        "table_regions": len(regions),
        "table_rows": len(rows),
        "region_confidences": [g["confidence"] for g in regions],
        "rows_with_cells": sum(1 for r in rows if r["cells"]),
        "max_columns": max((len({c["column"] for c in r["cells"] if c["column"] is not None}) for r in rows), default=0),
        "relations": [r["kind"] for r in result["relations"]],
        "continuations": [r["basis"] for r in result["relations"] if r["kind"] == "continuation"],
        "diagnostics": [d["code"] for d in result["diagnostics"]],
        "coverage": result["coverage"],
        "work_units": next((d["detail"] for d in result["diagnostics"] if d["code"] == "WORK_UNITS"), None),
    }


def main() -> int:
    bindings_path = REPO / ".planning" / "du2-layout" / "bindings.local.json"
    out_dir = REPO / ".planning" / "du2-layout" / "c-evidence"
    bindings = json.loads(bindings_path.read_text(encoding="utf8"))
    results = []
    payload = {"schema_version": "du2-layout-c-evidence/1", "samples": []}
    for spec in real_probe.PROBE_SAMPLES:
        entry = {"sample_id": spec["sample_id"], "label": spec["label"], "pages": spec["pages"], "modes": {}}
        for mode in ("span", "row_collapse"):
            probe = real_probe.load_probe_input(bindings, spec["sample_id"], mode=mode)
            if probe["status"] != "ok":
                entry["modes"][mode] = {"status": "UNAVAILABLE", "reason": probe.get("reason")}
                continue
            result = derive_layout_hints(probe["observation"])
            entry["modes"][mode] = {"status": "OBSERVED", **summarise(result)}
            results.append(probe)
        payload["samples"].append(entry)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "c_node_summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    real_probe.write_mapping_evidence(out_dir / "probe_mapping.json", results)
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
