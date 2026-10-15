"""Independent synthetic holdout: multi-table and repeated-year shapes.

Not the HK fixture: two different tables sharing the same local table index on
different pages, and a four-period grid where years repeat across durations.
Nothing here reuses the retained packet's strings or numbers.
"""

from __future__ import annotations

import pytest

from builders import (
    cell,
    column_by_native,
    measurement_for,
    observation,
    period_fields,
    text_ref,
    unit,
)

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.table_measurements import bind_operating_table


def budget(n: int = 100_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


def _period_grid(parent: str, page: int, numbers: dict[int, str]) -> tuple[dict, dict[int, dict]]:
    """six-2023 / twelve-2023 / six-2024 / twelve-2024 with a value row."""
    header_text = (
        "For the six months ended June 30, "
        "For the twelve months ended December 31, "
        "2023 2023 2024 2024"
    )
    h_id = f"{parent}-u-h"
    lab_id = f"{parent}-u-lab"
    u_h = unit(h_id, header_text, parent_id=parent, kind="table_header", locator={"page_number": page})
    u_lab = unit(lab_id, "Total GMV (RMB in millions)", parent_id=parent, locator={"page_number": page})
    units = {h_id: u_h, lab_id: u_lab}
    h6 = text_ref(h_id, header_text, "For the six months ended June 30,")
    h12 = text_ref(h_id, header_text, "For the twelve months ended December 31,")
    years = [
        text_ref(h_id, header_text, "2023"),
        text_ref(h_id, header_text, "2023", occurrence=2),
        text_ref(h_id, header_text, "2024"),
        text_ref(h_id, header_text, "2024", occurrence=2),
    ]
    label = text_ref(lab_id, "Total GMV (RMB in millions)", "Total GMV (RMB in millions)")
    cells = [
        cell("h0a", 0, 1, presence="present", text_refs=[h6]),
        cell("h0b", 0, 2, presence="present", text_refs=[h12]),
        cell("h0c", 0, 3, presence="present", text_refs=[h6]),
        cell("h0d", 0, 4, presence="present", text_refs=[h12]),
    ]
    for col, year in enumerate(years, start=1):
        cells.append(cell(f"h1{col}", 1, col, presence="present", text_refs=[year]))
    cells.append(cell("lab", 2, 0, presence="present", text_refs=[label]))
    value_refs: dict[int, dict] = {}
    for col in range(1, 5):
        if col in numbers:
            uid = f"{parent}-u-v{col}"
            units[uid] = unit(uid, numbers[col], parent_id=parent, locator={"page_number": page})
            vref = text_ref(uid, numbers[col], numbers[col])
            cells.append(cell(f"v{col}", 2, col, presence="present", text_refs=[vref], header_refs=[label]))
            value_refs[col] = vref
        else:
            cells.append(cell(f"v{col}", 2, col, presence="empty"))
    obs = observation(units, cells, parent_id=parent, table_id="t0", page=page, header_rows=[0, 1])
    return obs, value_refs


def test_repeated_years_across_durations_stay_four_distinct_columns() -> None:
    obs, values = _period_grid("holdout-a", 7, {1: "101", 2: "202", 4: "404"})
    result = bind_operating_table(obs, work_budget=budget())
    expected = {
        1: {"kind": "duration", "start": None, "end": "2023-06-30", "duration_months": 6, "fiscal_label": None},
        2: {"kind": "duration", "start": None, "end": "2023-12-31", "duration_months": 12, "fiscal_label": None},
        3: {"kind": "duration", "start": None, "end": "2024-06-30", "duration_months": 6, "fiscal_label": None},
        4: {"kind": "duration", "start": None, "end": "2024-12-31", "duration_months": 12, "fiscal_label": None},
    }
    for native, want in expected.items():
        assert period_fields(column_by_native(result, native)["period"]) == want
    assert measurement_for(result, values[1])["column_id"] == column_by_native(result, 1)["column_id"]
    assert measurement_for(result, values[2])["column_id"] == column_by_native(result, 2)["column_id"]
    assert measurement_for(result, values[4])["column_id"] == column_by_native(result, 4)["column_id"]
    # the repeated 2024 six-month column keeps its empty slot
    assert all(m["column_id"] != column_by_native(result, 3)["column_id"] for m in result["measurements"])
    # all four periods stay distinct although only two years appear
    kinds = {column_by_native(result, n)["period"]["end"] for n in range(1, 5)}
    assert len(kinds) == 4


def test_same_local_table_index_on_two_pages_binds_independently() -> None:
    obs_a, values_a = _period_grid("holdout-a", 7, {1: "101", 2: "202", 3: "303", 4: "404"})
    obs_b, values_b = _period_grid("holdout-b", 9, {1: "909"})
    res_a = bind_operating_table(obs_a, work_budget=budget())
    res_b = bind_operating_table(obs_b, work_budget=budget())
    assert res_a["scope"] == {"parent_id": "holdout-a", "table_id": "t0", "page": 7}
    assert res_b["scope"] == {"parent_id": "holdout-b", "table_id": "t0", "page": 9}
    assert len(res_a["measurements"]) == 4
    assert len(res_b["measurements"]) == 1
    refs_a = {m["value_ref"]["unit_id"] for m in res_a["measurements"]}
    refs_b = {m["value_ref"]["unit_id"] for m in res_b["measurements"]}
    assert refs_a.isdisjoint(refs_b)
    # the sparse table keeps its own empty slots instead of borrowing values
    assert all(m["column_id"] != column_by_native(res_b, 3)["column_id"] for m in res_b["measurements"])
    m_b = measurement_for(res_b, values_b[1])
    assert m_b["column_id"] == column_by_native(res_b, 1)["column_id"]
    assert m_b["period"]["end"] == "2023-06-30"
    assert all(m_b["value_ref"] != m["value_ref"] for m in res_a["measurements"])


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
