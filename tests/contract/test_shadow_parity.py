"""WU-603 RED/audit tests: v1/v2 shadow parity diff gate.

SCENARIO: IDX-01 IDX-02 IDX-03 IDX-04 IDX-05 IDX-06 IDX-07 IDX-08
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.adapters.parity import run_parity  # noqa: E402


class _C:
    def __init__(self, path, role="original_primary", entity=None, status="active"):
        self.relative_path = path
        self.role = role
        self.entity_name = entity
        self.source_status = status


def test_identical_sets_ok():
    v1 = [_C("a.pdf", entity="Acme")]
    v2 = [_C("a.pdf", entity="Acme")]
    report = run_parity(v1, v2)
    assert report.ok and not report.diffs


def test_presence_diff_is_blocker():
    report = run_parity([_C("a.pdf")], [])
    assert not report.ok
    assert any(d.path == "a.pdf" and d.field == "presence" for d in report.blockers)


def test_known_bad_classified_not_blocker():
    v1 = [_C("b.pdf", entity="Acme")]
    v2 = [_C("b.pdf", entity="ACME")]
    report = run_parity(v1, v2, known_bad={("b.pdf", "entity"): "case normalization"})
    assert report.ok  # classified, not blocking
    assert any(d.classification == "known_bad" for d in report.diffs)


def test_unclassified_diff_is_blocker():
    v1 = [_C("c.pdf", entity="Acme")]
    v2 = [_C("c.pdf", entity="Other")]
    report = run_parity(v1, v2)
    assert not report.ok
    assert any(d.field == "entity" and d.classification == "blocker"
               for d in report.diffs)


def test_status_diff_blocker():
    v1 = [_C("d.pdf", status="active")]
    v2 = [_C("d.pdf", status="incomplete")]
    report = run_parity(v1, v2)
    assert any(d.field == "status" for d in report.blockers)
