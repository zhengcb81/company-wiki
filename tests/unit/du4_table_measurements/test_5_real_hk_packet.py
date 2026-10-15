"""Real retained HK packet: adapter + binder semantics.

Expected results are structural and positional — they never encode the golden
2024 numbers as rules.  The merged left cells hold the older labels/values
without per-value native positioning and must stay ambiguous, while the
positioned right-column cells bind to their real header path (as-of 2024 for
the store tables, fiscal 2024 for the GMV tables).
"""

from __future__ import annotations

import pytest

from builders import column_by_native, diagnostic_codes, period_fields
from real_packet import all_tables, project_table

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.table_measurements import bind_operating_table


def budget(n: int = 500_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


EXPECTED_COUNTS = {
    (14, 0): {"bound": 4, "ambiguous": 2, "unavailable": 0},
    (17, 0): {"bound": 6, "ambiguous": 2, "unavailable": 0},
    (18, 0): {"bound": 6, "ambiguous": 1, "unavailable": 0},
    (19, 0): {"bound": 12, "ambiguous": 1, "unavailable": 0},
    (20, 1): {"bound": 6, "ambiguous": 1, "unavailable": 0},
}


def _run(page: int, table_index: int) -> tuple[dict, dict]:
    obs, facts = project_table(page, table_index)
    result = bind_operating_table(obs, work_budget=budget())
    return result, facts


def _counts(result: dict) -> dict[str, int]:
    out = {"bound": 0, "ambiguous": 0, "unavailable": 0}
    for m in result["measurements"]:
        out[m["binding_status"]] += 1
    return out


def test_store_count_table_binds_only_the_positioned_right_column() -> None:
    result, _ = _run(14, 0)
    col_2023 = column_by_native(result, 1)
    col_2024 = column_by_native(result, 2)
    assert period_fields(col_2023["period"]) == {
        "kind": "as_of",
        "start": None,
        "end": "2023-12-31",
        "duration_months": None,
        "fiscal_label": None,
    }
    assert period_fields(col_2024["period"]) == {
        "kind": "as_of",
        "start": None,
        "end": "2024-12-31",
        "duration_months": None,
        "fiscal_label": None,
    }
    # the stub column has no header path at all
    assert column_by_native(result, 0)["status"] == "unavailable"

    bound = [m for m in result["measurements"] if m["binding_status"] == "bound"]
    ambiguous = [m for m in result["measurements"] if m["binding_status"] == "ambiguous"]
    assert len(bound) == EXPECTED_COUNTS[(14, 0)]["bound"]
    assert len(ambiguous) == EXPECTED_COUNTS[(14, 0)]["ambiguous"]
    for m in bound:
        assert m["column_id"] == col_2024["column_id"]
        assert m["period"]["end"] == "2024-12-31"
    for m in ambiguous:
        # merged left cell content: no per-value column, never absorbed by 2023/2024
        assert m["column_id"] is None
        assert m["period"] is None
        assert m["value_ref"] in result["unbound_value_refs"]
    assert all(m["column_id"] != col_2023["column_id"] for m in result["measurements"])
    assert result["status"] == "partial"


def test_three_period_table_keeps_same_year_durations_distinct() -> None:
    result, _ = _run(18, 0)
    col6 = column_by_native(result, 1)
    col12 = column_by_native(result, 2)
    colf = column_by_native(result, 3)
    assert period_fields(col6["period"]) == {
        "kind": "duration",
        "start": None,
        "end": "2023-12-31",
        "duration_months": 6,
        "fiscal_label": None,
    }
    assert period_fields(col12["period"]) == {
        "kind": "duration",
        "start": None,
        "end": "2023-12-31",
        "duration_months": 12,
        "fiscal_label": None,
    }
    assert period_fields(colf["period"]) == {
        "kind": "fiscal_year",
        "start": None,
        "end": "2024-12-31",
        "duration_months": None,
        "fiscal_label": "2024",
    }
    bound = [m for m in result["measurements"] if m["binding_status"] == "bound"]
    ambiguous = [m for m in result["measurements"] if m["binding_status"] == "ambiguous"]
    assert len(bound) == EXPECTED_COUNTS[(18, 0)]["bound"]
    assert len(ambiguous) == EXPECTED_COUNTS[(18, 0)]["ambiguous"]
    for m in bound:
        assert m["column_id"] == colf["column_id"]
        assert m["period"]["kind"] == "fiscal_year"
    # the two values inside the merged block never claimed the six/twelve-month columns
    assert all(m["column_id"] not in {col6["column_id"], col12["column_id"]} for m in result["measurements"])


def test_every_retained_table_reports_honest_counts() -> None:
    assert sorted(all_tables()) == sorted(EXPECTED_COUNTS)
    totals = {"bound": 0, "ambiguous": 0, "unavailable": 0}
    for page, table_index in all_tables():
        result, facts = _run(page, table_index)
        counts = _counts(result)
        assert counts == EXPECTED_COUNTS[(page, table_index)], (page, table_index)
        for key in totals:
            totals[key] += counts[key]
        for m in result["measurements"]:
            if m["binding_status"] == "bound":
                # only positioned right-column values bind: all on the 2024 column
                assert m["period"]["end"] == "2024-12-31", (page, table_index)
                last = max(c["native_column"] for c in result["columns"])
                assert m["column_id"] == column_by_native(result, last)["column_id"]
            else:
                assert m["value_ref"] in result["unbound_value_refs"]
        if facts["truncated"]:
            assert result["status"] == "partial"
            assert "observation_truncated" in diagnostic_codes(result)
    assert totals == {"bound": 34, "ambiguous": 7, "unavailable": 0}


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
