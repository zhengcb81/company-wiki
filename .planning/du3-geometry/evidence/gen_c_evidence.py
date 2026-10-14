"""Generate bounded DU3-GEOMETRY node-C evidence from real originals (read-only).

Writes a COMPACT summary: per-sample binding/projection counts, fine-cell/word
provenance and frame, plus before/after fingerprints proving originals are
byte/mtime/size preserved.  No absolute paths, no whole-page text, no per-page
snapshots are persisted.  This is inspection tooling; it never enters the product.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve()
_WORKTREE = _HERE.parents[3]
sys.path.insert(0, str(_WORKTREE / "src"))
sys.path.insert(0, str(_WORKTREE / "tests" / "fixtures" / "document_normalization_layout_snapshots"))

import native_probe  # noqa: E402
from company_wiki.document_normalization.layout_snapshots import project_layout_snapshot  # noqa: E402

BINDINGS = _WORKTREE / ".planning" / "du3-geometry" / "bindings.local.json"
OUT = _WORKTREE / ".planning" / "du3-geometry" / "evidence" / "c-real-snapshots.json"


def _summarise(proj: dict, probe: dict) -> dict:
    gran = {}
    max_cols = 0
    cells_total = words_total = runs_total = 0
    frames = set()
    for meta in proj["unit_metadata"].values():
        g = meta["layout"]["granularity"]
        gran[g] = gran.get(g, 0) + 1
        frames.add(meta["layout"]["coordinate_frame"])
        uh = meta["upstream_hints"]
        cells_total += len(uh["cells"])
        words_total += len(uh["words"])
        runs_total += len(uh["font_runs"])
        cols = {c.get("column") for c in uh["cells"] if c.get("column") is not None}
        if cols:
            max_cols = max(max_cols, len(cols))
    return {
        "pages_in_snapshot": len(probe["snapshot"]["pages"]),
        "units_extracted": len(probe["units"]),
        "bound_unit_count": proj["coverage"]["bound_unit_count"],
        "granularity_counts": gran,
        "fine_cells": cells_total,
        "fine_words": words_total,
        "font_runs": runs_total,
        "max_distinct_cell_columns": max_cols,
        "coordinate_frames": sorted(x for x in frames if x),
        "complete": proj["coverage"]["complete"],
        "diag_codes": sorted({d["code"] for d in proj["diagnostics"]}),
    }


def main() -> int:
    bindings = native_probe.load_bindings_file(BINDINGS)
    samples = []
    fingerprints = []
    for spec in native_probe.GEOMETRY_SAMPLES:
        sid = spec["sample_id"]
        raw = bindings.get(sid)
        entry = {"sample_id": sid, "label": spec["label"], "pages": spec["pages"], "source_sha256": spec["sha256"]}
        t0 = time.monotonic()
        probe = native_probe.load_snapshot(bindings, sid)
        elapsed = round(time.monotonic() - t0, 3)
        if probe["status"] != "ok":
            entry.update(status="UNAVAILABLE", reason=probe.get("reason"))
            samples.append(entry)
            continue
        proj = project_layout_snapshot(probe["snapshot"], probe["units"])
        entry.update(status="OBSERVED", elapsed_s=elapsed, **_summarise(proj, probe))
        samples.append(entry)

        if raw:
            after = native_probe.fingerprint(Path(raw))
            fingerprints.append(
                {
                    "sample_id": sid,
                    "sha256": after["sha256"],
                    "sha_preserved": after["sha256"] == probe["fp_before"]["sha256"],
                    "mtime_preserved": after["mtime_ns"] == probe["fp_before"]["mtime_ns"],
                    "size_preserved": after["size"] == probe["fp_before"]["size"],
                }
            )

    payload = {
        "schema_version": "du3-geometry-c-evidence/1",
        "note": "real pages are measurement oracles; reliable binding != fine-column/table recall passed",
        "caps": {
            "max_pages_per_sample": native_probe.MAX_PAGES_PER_SAMPLE,
            "max_words_per_page": native_probe.MAX_WORDS_PER_PAGE,
            "max_cells_per_page": native_probe.MAX_CELLS_PER_PAGE,
            "max_text_bytes": native_probe.MAX_TEXT_BYTES,
            "time_budget_s": native_probe.TIME_BUDGET_S,
        },
        "samples": samples,
        "original_fingerprints": fingerprints,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
