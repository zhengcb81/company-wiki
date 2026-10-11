"""One narrow ROOT regression and fix after independent boundary review."""
from pathlib import Path
import sys

TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root')
TEST = TREE / 'tests/test_financial_measure_report_boundary.py'
PRODUCT = TREE / 'skills/revenue-forecast-audit/scripts/financial_measure_audit.py'
TEST_BODY = '''"""All report shapes retain the same unverified source boundary."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/revenue-forecast-audit/scripts"))
from financial_measure_audit import audit_measures


class ReportBoundaryTests(unittest.TestCase):
    def test_source_qualification_boundary_on_all_report_shapes(self):
        legal = json.loads((ROOT / "tests/fixtures/financial_measures/legal_cn.json").read_text(encoding="utf-8"))
        cases = [None, [], "not an object", {},
                 {"schema_version": "financial-measure-ledger/1", "as_of_date": "2026-10-11", "observations": {}},
                 {"schema_version": "financial-measure-ledger/1", "as_of_date": "2026-10-11", "observations": [], "relations": {}},
                 legal]
        for index, ledger in enumerate(cases):
            with self.subTest(index=index):
                report = audit_measures(ledger)
                self.assertIs(report.get("source_qualification_verified"), False)
                self.assertIs(report["source_truth_verified"], False)
                self.assertEqual(report["economic_reasonableness"], "not_evaluated")


if __name__ == "__main__":
    unittest.main()
'''

if sys.argv[1:] == ['--test']:
    assert not TEST.exists()
    TEST.write_text(TEST_BODY, encoding='utf-8')
elif sys.argv[1:] == ['--fix']:
    original = PRODUCT.read_bytes()
    needle = b'"source_truth_verified": False, "economic_reasonableness": "not_evaluated",'
    assert original.count(needle) == 1
    PRODUCT.write_bytes(original.replace(needle, b'"source_truth_verified": False, "source_qualification_verified": False, "economic_reasonableness": "not_evaluated",', 1))
else:
    raise SystemExit('choose --test or --fix')
