"""Coverage diagnostics retain every gap without rescanning the document."""
from types import SimpleNamespace

import pytest

from company_wiki.document_understanding.structure import _coverage_diagnostics
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded


class CountedUnits(list):
    visits = 0

    def __iter__(self):
        self.visits += len(self)
        return super().__iter__()


def test_many_gap_pages_visit_the_source_units_once():
    units = CountedUnits(SimpleNamespace(unit_id=f"u{i}", page=i % 7) for i in range(100))
    coverage = {"opaque_pages": list(range(40)), "deferred_pages": list(range(20, 70)),
                "native_scan": "partial"}
    result = _coverage_diagnostics({}, coverage, units)
    assert len(result) == 91
    assert units.visits <= len(units)
    assert result[0]["unit_ids"] == [f"u{i}" for i in range(0, 100, 7)]
    assert result[39]["code"] == "OPAQUE_PAGE" and result[39]["unit_ids"] == []
    assert result[40]["code"] == "DEFERRED_PAGE"
    assert result[-1]["code"] == "NATIVE_SCAN_INCOMPLETE"


def test_diagnostic_index_pays_for_input_and_output_in_the_same_budget():
    units = [SimpleNamespace(unit_id=f"u{i}", page=i) for i in range(400)]
    coverage = {"opaque_pages": list(range(400)), "deferred_pages": [0, 0],
                "native_scan": "complete"}
    budget = WorkBudget(2_000)
    result = _coverage_diagnostics({}, coverage, units, work_budget=budget)
    assert len(result) == 402 and result[-1] == result[-2]
    assert 800 <= budget.used < 2_000


def test_unaffordable_diagnostics_do_not_start_source_iteration():
    class UnpaidUnits(list):
        def __iter__(self):
            raise AssertionError("source iteration before reservation")

    budget = WorkBudget(0)
    with pytest.raises(WorkBudgetExceeded):
        _coverage_diagnostics({}, {"opaque_pages": [1], "deferred_pages": [],
                                  "native_scan": "partial"}, UnpaidUnits([None]),
                              work_budget=budget)
    assert budget.used == 0 and budget.exhausted
