"""Read-only diagnostic wrappers; no provider, copied raw or acceptance claim."""
from pathlib import Path
import importlib.util
import json
import sys

PLAN = Path(__file__).resolve().parent
ROOT = PLAN.parents[2]
spec = importlib.util.spec_from_file_location("du11_page_probe",
    ROOT / "docs/plans/du11-source-priority-2026-10-18/real-source-probe/probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
probe.OUT = PLAN / (sys.argv[1] if len(sys.argv) > 1 else "page-scope-investigation")
assert probe.OUT.resolve().parent == PLAN.resolve()
probe.OUT.mkdir(exist_ok=False)
from company_wiki.source_catalog import narrative_reading

original = narrative_reading._prose_reading_packages
observations = []


def inspect(parsed, pipeline, *args, **kwargs):
    result = original(parsed, pipeline, *args, **kwargs)
    by_id = {u.unit_id: u for u in parsed.units}
    wires = pipeline["observation"]["units"]
    selected = [u for u in wires if u.get("page") == 16][-5:] + [u for u in wires if u.get("page") == 17][:7]
    rows = []
    for wire in selected:
        uid = wire["unit_id"]
        unit = by_id[uid]
        rows.append({"unit_id": uid, "ordinal": wire["ordinal"], "page": wire.get("page"),
            "paragraph_index": unit.coordinates.paragraph_index, "kind": wire.get("kind"),
            "role": wire.get("role"), "prefix": unit.raw_text[:40], "suffix": unit.raw_text[-30:],
            "block": unit.metadata.get("pdf_block"), "layout": wire.get("layout"),
            "hints": wire.get("hints"), "profile": pipeline["reading_plan"]["unit_profiles"].get(uid),
            "owners": [{key: p.get(key) for key in ("package_id", "kind", "anchor_unit_ids")}
                for p in pipeline["packages"]["packages"] if uid in p.get("member_unit_ids", ())],
            "sections": [s["section_id"] for s in pipeline["structure"]["sections"]
                if uid in (*s.get("heading_unit_ids", ()), *s.get("body_unit_ids", ()))],
            "blocked": uid in result[3]})
    observations.append({"scope": "diagnostic_only_wrappers_not_frozen_acceptance_or_timing",
        "mime_type": parsed.mime_type, "pages_read": parsed.pages_read,
        "source_page_flow": result[2].get("source_page_flow"),
        "opaque_pair_pages": sorted(set(parsed.opaque_pages) & {16, 17}),
        "deferred_pair_pages": sorted(set(parsed.deferred_table_pages) & {16, 17}),
        "furniture": [d for d in pipeline["structure"].get("diagnostics", ())
            if d.get("code") == "REPEATED_RUNNING_HEADER" and set(d.get("unit_ids", ())) & {u["unit_id"] for u in selected}],
        "rows": rows, "diagnostics": result[2]["diagnostics"]})
    return result


narrative_reading._prose_reading_packages = inspect
before = probe.bindings()
metadata = probe.MOTHER / ".planning/shared-reading-production/du11/metadata-registered-source-facts-20261017.json"
sample = next(row for row in json.loads(metadata.read_text(encoding="utf-8"))["samples"] if row["sample_id"] == "cn-h1")
try:
    record = probe.run(sample)
finally:
    narrative_reading._prose_reading_packages = original
assert before == probe.bindings()
(probe.OUT / "page-scope.json").write_text(json.dumps({"source_bindings": before,
    "observations": observations, "api_calls": 0, "raw_copies": 0,
    "original_unchanged": record["original_unchanged"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
