"""Copy only frozen synthetic vectors and add portable regression tests in ROOT leaf."""
import json
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
LEAF = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root")
assert LEAF.resolve().name == "audit-measures-root"
cases = json.loads((EVIDENCE.parent / "intake/counterexamples.json").read_text(encoding="utf-8"))["cases"]
fixture = LEAF / "tests/fixtures/financial_measures/root_acceptance_regressions.json"
fixture.write_text(json.dumps({"schema_version": "financial-measure-root-regressions/1",
                               "synthetic": True, "frozen_delivery_head": "6a50d7ed1b4cf389589c7ca62b4ab161b5dc0ad1",
                               "cases": [{"id": row["id"], "ledger": row["ledger"], "expected_statuses": row["expected_statuses"]}
                                         for row in cases]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
test = LEAF / "tests/test_financial_measure_root_regressions.py"
test.write_text('''"""ROOT acceptance vectors frozen before implementation; synthetic, no source truth claims."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("financial_measure_root_regressions", ROOT / "skills/revenue-forecast-audit/scripts/financial_measure_audit.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
VECTORS = json.loads((ROOT / "tests/fixtures/financial_measures/root_acceptance_regressions.json").read_text(encoding="utf-8"))["cases"]

class FrozenRootAcceptanceTests(unittest.TestCase):
    pass

def make_test(case):
    def run(self):
        report = module.audit_measures(case["ledger"])
        self.assertIn(report["overall"], case["expected_statuses"], case["id"] + "\\n" + json.dumps(report, ensure_ascii=False))
        self.assertIs(report["source_truth_verified"], False)
        self.assertEqual(report["economic_reasonableness"], "not_evaluated")
    return run

for case in VECTORS:
    setattr(FrozenRootAcceptanceTests, "test_" + case["id"], make_test(case))

if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")
print(json.dumps({"fixture": str(fixture), "test": str(test), "cases": len(cases)}))
