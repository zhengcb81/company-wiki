"""Check the real CWP source inventory against the reviewed Phase 1 baseline."""

import json
from pathlib import Path

from tools.anti_trick_gate_spec.evidence import baseline, changed_inventory, compare, renamed_waivers
from tools.anti_trick_gate_spec.static_scan import scan

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ("src/company_wiki",)
STORAGE = (
    "src/company_wiki/source_catalog/store.py",
    "src/company_wiki/automation/store.py",
)


def test_current_source_does_not_add_unreviewed_boundary_debt():
    before = json.loads((ROOT / "tests/contract/ratchet_baseline.json").read_bytes())
    actual = scan(ROOT, SOURCE, STORAGE)
    assert "src/company_wiki/source_catalog/cli.py" in actual.files
    assert "src/company_wiki/automation/store.py" in actual.files
    recorded = {**baseline(actual.findings), "source_files": list(actual.files),
                "constant_shapes": actual.constant_shapes}
    assert not changed_inventory(actual, before, ROOT)
    assert not compare(recorded, before) + renamed_waivers(recorded, before)
