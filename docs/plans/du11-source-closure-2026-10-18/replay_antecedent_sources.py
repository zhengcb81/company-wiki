"""One-off B2 replay for HK/US under the same budget; no provider or copy."""
from pathlib import Path
import importlib.util, json, sys
PLAN = Path(__file__).resolve().parent
ROOT = PLAN.parents[2]
spec = importlib.util.spec_from_file_location("du11_probe",
    ROOT/"docs/plans/du11-source-priority-2026-10-18/real-source-probe/probe.py")
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
probe.OUT = PLAN/("b2-real-sources-" + (sys.argv[1] if len(sys.argv) > 1 else "20261018"))
probe.OUT.mkdir(exist_ok=False)
before = probe.bindings()
meta = probe.MOTHER/".planning/shared-reading-production/du11/metadata-registered-source-facts-20261017.json"
samples = json.loads(meta.read_text(encoding="utf-8"))["samples"]
records = [probe.run(sample) for sample in samples if sample["sample_id"] in {"hk-annual", "us-10k"}]
assert before == probe.bindings(), "SOURCE_CHANGED_DURING_PROBE"
(probe.OUT/"replay.json").write_text(json.dumps({
    "source_bindings": before, "api_calls": 0, "raw_copies": 0, "source_unchanged": True,
    "samples": [{k: r.get(k) for k in ("sample", "status", "seconds", "selected_count", "claims",
        "selected_required", "canonical_required", "required_total", "deferral_reasons",
        "original_unchanged", "gold_unchanged")} for r in records]},
    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
