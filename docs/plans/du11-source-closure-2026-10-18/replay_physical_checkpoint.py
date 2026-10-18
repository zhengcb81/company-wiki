"""Offline replay for the physical-flow revision; never overwrite B1 evidence."""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile

PLAN = Path(__file__).resolve().parent
ROOT = PLAN.parents[2]
path = ROOT / "docs/plans/du11-source-priority-2026-10-18/real-source-probe/probe.py"
spec = importlib.util.spec_from_file_location("du11_physical_probe", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.OUT = PLAN / (sys.argv[1] if len(sys.argv) > 1 else "physical-source-final-replay")
assert module.OUT.resolve().parent == PLAN.resolve()
module.OUT.mkdir(exist_ok=False)
module.MODULES.append("company_wiki.document_understanding.indented_tail_geometry")
module.MODULES.extend(("company_wiki.document_understanding.operating_states.relations",
    "company_wiki.document_understanding.operating_states.patterns",
    "company_wiki.document_understanding.operating_states.text_view",
    "company_wiki.document_normalization.text_matching"))
before = module.bindings()
metadata = module.MOTHER / ".planning/shared-reading-production/du11/metadata-registered-source-facts-20261017.json"
rows = []
with tempfile.TemporaryDirectory(prefix="du11-physical-source-") as temp:
    owned = Path(temp)
    assert not list(owned.iterdir())
    for sample in json.loads(metadata.read_text(encoding="utf-8"))["samples"]:
        rows.append(module.run(sample))
    assert not list(owned.iterdir())
assert before == module.bindings()
receipt = {"schema_version": "du11-physical-source-replay/1", "source_bindings": before,
    "api_calls": 0, "raw_copies": 0, "owned_temp_removed": not owned.exists(),
    "originals_unchanged": all(row["original_unchanged"] for row in rows),
    "gold_unchanged": all(row["gold_unchanged"] for row in rows),
    "metadata_sha256": module.sha(metadata.read_bytes()),
    "samples": [{key: row.get(key) for key in ("sample", "status", "selected_required",
        "canonical_required", "required_total", "actual_work_accounts")} for row in rows],
    "content_acceptance": "OPEN: antecedent closure and formal provider C remain pending"}
(module.OUT / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert all(row["status"] == "ENGINEERING_PASS_CONTENT_OPEN" for row in rows)
