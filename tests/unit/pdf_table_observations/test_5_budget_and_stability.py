"""Card B-5: one shared WorkBudget through preparation and the original binder.

Zero / spent budgets stop before any traversal, mid-exhaustion keeps only closed
tables, inputs are never modified, and the downstream binder is really called
with the same budget instance."""

from __future__ import annotations

import json

from company_wiki.document_understanding.layout_hints.contract import (
    WorkBudget,
    WorkBudgetExceeded,
)
from company_wiki.document_understanding.table_measurements import bind_operating_table
from company_wiki.document_normalization.pdf_table_observations import (
    build_pdf_table_observations,
)

from .builders import layout_hints, merge_layout_hints, observation, row_unit

PARENT = "urn:company-wiki:source:sha256:aaaa"


def _two_tables():
    t1 = [
        row_unit("a-r0", [(0, "项目"), (1, "2025年")], row=0, table_id="p1:t0", kind="table_header"),
        row_unit("a-r1", [(0, "门店"), (1, "18")], row=1, table_id="p1:t0"),
    ]
    t2 = [
        row_unit("b-r0", [(0, "项目"), (1, "2025年")], row=0, table_id="p1:t1", kind="table_header"),
        row_unit("b-r1", [(0, "门店"), (1, "21")], row=1, table_id="p1:t1"),
    ]
    hints = layout_hints(
        region_units=["a-r0", "a-r1"], header_units=["a-r0"], data_rows=[["a-r1"]]
    )
    piece = layout_hints(
        region_units=["b-r0", "b-r1"], header_units=["b-r0"], data_rows=[["b-r1"]]
    )
    return observation(t1 + t2), merge_layout_hints(hints, piece)


class Unread(dict):
    def get(self, *args, **kwargs):
        raise AssertionError("zero budget traversed input")

    def __getitem__(self, key):
        raise AssertionError("zero budget traversed input")


def test_spent_budget_stops_before_traversal_without_resetting_prior_spend():
    budget = WorkBudget(7, used=7)
    result = build_pdf_table_observations(Unread(), Unread(), work_budget=budget)
    assert result["status"] == "partial"
    assert result["tables"] == []
    assert {d["code"] for d in result["diagnostics"]} == {"WORK_BUDGET_EXCEEDED"}
    assert budget.used == 7 and budget.exhausted
    assert result["work_used"] == 0


def test_mid_exhaustion_keeps_only_closed_tables_and_half_of_nothing():
    obs, hints = _two_tables()
    full = build_pdf_table_observations(obs, hints, work_budget=WorkBudget(100_000))
    assert len(full["tables"]) == 2
    # Check every actual cutoff, instead of assuming full_work-1 must land
    # inside table #2 rather than a paid final diagnostic scan.
    saw_exactly_one_closed_table = False
    for cap in range(full["work_used"]):
        budget = WorkBudget(max_work_units=cap)
        result = build_pdf_table_observations(obs, hints, work_budget=budget)
        assert budget.exhausted
        assert result["status"] == "partial"
        assert "WORK_BUDGET_EXCEEDED" in {d["code"] for d in result["diagnostics"]}
        assert result["tables"] == full["tables"][:len(result["tables"])]
        assert result["work_used"] == budget.used <= cap
        saw_exactly_one_closed_table |= len(result["tables"]) == 1
    assert saw_exactly_one_closed_table



def test_inputs_are_unchanged_and_outputs_are_deterministic():
    obs, hints = _two_tables()
    obs_before = json.dumps(obs, sort_keys=True)
    hints_before = json.dumps(hints, sort_keys=True)
    first = build_pdf_table_observations(obs, hints, work_budget=WorkBudget(100_000))
    second = build_pdf_table_observations(obs, hints, work_budget=WorkBudget(100_000))
    assert json.dumps(obs, sort_keys=True) == obs_before
    assert json.dumps(hints, sort_keys=True) == hints_before
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_downstream_original_binder_runs_on_the_same_budget_instance():
    obs, hints = _two_tables()
    budget = WorkBudget(100_000, used=17)
    result = build_pdf_table_observations(obs, hints, work_budget=budget)
    spent_after_prepare = budget.used
    assert result["work_used"] == spent_after_prepare - 17
    bound = [
        bind_operating_table(table, work_budget=budget) for table in result["tables"]
    ]
    assert budget.used > spent_after_prepare  # 同一预算实例继续计费
    assert all(row["schema_version"] == "du4-table-bindings/1" for row in bound)
    assert all(row["status"] == "complete" for row in bound)


def test_exhausted_budget_flows_to_the_binder_as_partial_not_an_exception():
    obs, hints = _two_tables()
    budget = WorkBudget(100_000)
    result = build_pdf_table_observations(obs, hints, work_budget=budget)
    budget.charge(budget.max_work_units - budget.used)  # 用尽
    try:
        bound = bind_operating_table(result["tables"][0], work_budget=budget)
    except WorkBudgetExceeded as exc:  # pragma: no cover - contract violation
        raise AssertionError("binder must report partial, not raise") from exc
    assert bound["status"] == "partial"
    assert "work_budget_exhausted" in {d["code"] for d in bound["diagnostics"]}
