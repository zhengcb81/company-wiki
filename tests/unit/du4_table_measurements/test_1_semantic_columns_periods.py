"""Semantic counterexamples: value -> native column -> period binding.

Expected results were written independently of the implementation and mirror
the frozen acceptance card: a header with two year columns must never absorb a
value that has no native column proof, and same-year different-duration
columns stay distinct periods.
"""

from __future__ import annotations

import copy

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


def budget(n: int = 10_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


# ---------------------------------------------------------------------------
# 2023/2024 headers, one value per row: never auto-assign the latest year.
# ---------------------------------------------------------------------------


def _two_year_table() -> tuple[dict, dict, dict]:
    """Headers 'As of December 31, / 2023 / 2024'; value without column proof."""
    u_h = unit("u-h", "As of December 31, 2023 2024", kind="table_header")
    u_v = unit("u-v", "522")
    units = {"u-h": u_h, "u-v": u_v}
    h_span = text_ref("u-h", u_h["text"], "As of December 31,")
    h_2023 = text_ref("u-h", u_h["text"], "2023")
    h_2024 = text_ref("u-h", u_h["text"], "2024")
    value = text_ref("u-v", u_v["text"], "522")
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[h_span], row_span=1, column_span=2),
        cell("h0c2", 0, 2, presence="merged_unknown"),
        cell("h1", 1, 1, presence="present", text_refs=[h_2023]),
        cell("h2", 1, 2, presence="present", text_refs=[h_2024]),
        # one value row, one value, but the merged slot proves no value column
        cell("v0", 2, 0, presence="present", text_refs=[value], column_span=3),
    ]
    obs = observation(units, cells, header_rows=[0, 1])
    return obs, value, {"2023": h_2023, "2024": h_2024, "asof": h_span}


def test_single_value_without_column_proof_is_not_moved_to_latest_year() -> None:
    obs, value, _ = _two_year_table()
    snapshot = copy.deepcopy(obs)
    result = bind_operating_table(obs, work_budget=budget())
    assert obs == snapshot  # input immutability
    m = measurement_for(result, value)
    assert m["binding_status"] == "ambiguous"
    assert m["column_id"] is None
    assert m["period"] is None
    bound_ids = {
        mm["column_id"] for mm in result["measurements"] if mm["binding_status"] == "bound"
    }
    col_2024 = column_by_native(result, 2)
    assert col_2024["column_id"] not in bound_ids
    assert value in result["unbound_value_refs"]


def test_single_value_with_native_column_stays_on_its_own_year() -> None:
    u_h = unit("u-h", "As of December 31, 2023 2024", kind="table_header")
    u_v1 = unit("u-v1", "522")
    u_v2 = unit("u-v2", "587")
    h_span = text_ref("u-h", u_h["text"], "As of December 31,")
    h_2023 = text_ref("u-h", u_h["text"], "2023")
    h_2024 = text_ref("u-h", u_h["text"], "2024")
    v1 = text_ref("u-v1", u_v1["text"], "522")
    v2 = text_ref("u-v2", u_v2["text"], "587")
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[h_span], column_span=2),
        cell("h1", 1, 1, presence="present", text_refs=[h_2023]),
        cell("h2", 1, 2, presence="present", text_refs=[h_2024]),
        cell("v1", 2, 1, presence="present", text_refs=[v1]),
        cell("v2", 3, 2, presence="present", text_refs=[v2]),
    ]
    obs = observation({"u-h": u_h, "u-v1": u_v1, "u-v2": u_v2}, cells, header_rows=[0, 1])
    result = bind_operating_table(obs, work_budget=budget())
    m1 = measurement_for(result, v1)
    m2 = measurement_for(result, v2)
    col_2023 = column_by_native(result, 1)
    col_2024 = column_by_native(result, 2)
    assert m1["binding_status"] == "bound"
    assert m1["column_id"] == col_2023["column_id"]
    assert m2["binding_status"] == "bound"
    assert m2["column_id"] == col_2024["column_id"]
    assert period_fields(m1["period"]) == {
        "kind": "as_of",
        "start": None,
        "end": "2023-12-31",
        "duration_months": None,
        "fiscal_label": None,
    }
    assert period_fields(m2["period"]) == {
        "kind": "as_of",
        "start": None,
        "end": "2024-12-31",
        "duration_months": None,
        "fiscal_label": None,
    }
    # parallel label refs of the same period are kept, not merged away
    kept = {
        (r["unit_id"], r["char_start"], r["char_end"])
        for r in m1["period"]["raw_label_refs"]
    }
    assert kept == {
        (h_span["unit_id"], h_span["char_start"], h_span["char_end"]),
        (h_2023["unit_id"], h_2023["char_start"], h_2023["char_end"]),
    }


def test_bare_year_headers_do_not_invent_period_semantics() -> None:
    u_h = unit("u-h", "2023 2024", kind="table_header")
    u_v = unit("u-v", "522")
    u_v2 = unit("u-v2", "587")
    h_2023 = text_ref("u-h", u_h["text"], "2023")
    h_2024 = text_ref("u-h", u_h["text"], "2024")
    value = text_ref("u-v", u_v["text"], "522")
    value2 = text_ref("u-v2", u_v2["text"], "587")
    cells = [
        cell("h1", 0, 1, presence="present", text_refs=[h_2023]),
        cell("h2", 0, 2, presence="present", text_refs=[h_2024]),
        cell("v0", 1, 0, presence="present", text_refs=[value], column_span=3),
        cell("v1", 2, 1, presence="present", text_refs=[value2]),
    ]
    obs = observation({"u-h": u_h, "u-v": u_v, "u-v2": u_v2}, cells, header_rows=[0])
    result = bind_operating_table(obs, work_budget=budget())
    m_positioned = measurement_for(result, value2)
    assert m_positioned["binding_status"] == "bound"
    assert m_positioned["column_id"] == column_by_native(result, 1)["column_id"]
    col_2023 = column_by_native(result, 1)
    assert period_fields(col_2023["period"]) == {
        "kind": "unspecified",
        "start": None,
        "end": None,
        "duration_months": None,
        "fiscal_label": None,
    }
    assert col_2023["period"]["raw_label_refs"] == [h_2023]
    m_unpositioned = measurement_for(result, value)
    assert m_unpositioned["binding_status"] == "ambiguous"
    assert m_unpositioned["column_id"] is None


# ---------------------------------------------------------------------------
# six months 2023 / twelve months 2023 / fiscal 2024: three periods, two
# values.  Empty slots stay empty and values never right-align.
# ---------------------------------------------------------------------------


def _three_period_table(value_columns: tuple[int, ...]) -> tuple[dict, dict[int, dict]]:
    u_h = unit(
        "u-h",
        "For the six months ended December 31, "
        "For the twelve months ended December 31, "
        "For the fiscal year ended December 31, "
        "2023 2023 2024",
        kind="table_header",
    )
    u_lab = unit("u-lab", "Total GMV")
    h6 = text_ref("u-h", u_h["text"], "For the six months ended December 31,")
    h12 = text_ref("u-h", u_h["text"], "For the twelve months ended December 31,")
    hf = text_ref("u-h", u_h["text"], "For the fiscal year ended December 31,")
    y1 = text_ref("u-h", u_h["text"], "2023")
    y2 = text_ref("u-h", u_h["text"], "2023", occurrence=2)
    y3 = text_ref("u-h", u_h["text"], "2024")
    label = text_ref("u-lab", u_lab["text"], "Total GMV")
    cells = [
        cell("h0a", 0, 1, presence="present", text_refs=[h6]),
        cell("h0b", 0, 2, presence="present", text_refs=[h12]),
        cell("h0c", 0, 3, presence="present", text_refs=[hf]),
        cell("h1a", 1, 1, presence="present", text_refs=[y1]),
        cell("h1b", 1, 2, presence="present", text_refs=[y2]),
        cell("h1c", 1, 3, presence="present", text_refs=[y3]),
        cell("lab", 2, 0, presence="present", text_refs=[label]),
    ]
    value_refs: dict[int, dict] = {}
    numbers = {1: "6,895", 2: "13,035", 3: "14,008"}
    used = [c for c in value_columns]
    for col in range(1, 4):
        cid = f"v{col}"
        if col in used:
            u_v = unit(f"u-v{col}", numbers[col])
            vref = text_ref(f"u-v{col}", u_v["text"], numbers[col])
            # the provider asserts the stub label applies to this value cell
            cells.append(cell(cid, 2, col, presence="present", text_refs=[vref], header_refs=[label]))
            value_refs[col] = vref
        else:
            cells.append(cell(cid, 2, col, presence="empty"))
    units = {"u-h": u_h, "u-lab": u_lab}
    for col, vref in value_refs.items():
        units[vref["unit_id"]] = unit(vref["unit_id"], numbers[col])
    return observation(units, cells, header_rows=[0, 1]), value_refs


def test_three_period_headers_two_values_keep_empty_slot_and_distinct_periods() -> None:
    obs, values = _three_period_table((1, 3))
    result = bind_operating_table(obs, work_budget=budget())
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
    # same year 2023, different durations: never merged into one period
    assert col6["column_id"] != col12["column_id"]
    assert period_fields(col6["period"]) != period_fields(col12["period"])

    m1 = measurement_for(result, values[1])
    m2 = measurement_for(result, values[3])
    # no right-alignment: the first value stays on the six-month column
    assert m1["binding_status"] == "bound"
    assert m1["column_id"] == col6["column_id"]
    assert m2["binding_status"] == "bound"
    assert m2["column_id"] == colf["column_id"]
    assert period_fields(m2["period"])["duration_months"] is None

    # the middle column keeps its empty slot: no measurement was invented
    assert all(m["column_id"] != col12["column_id"] for m in result["measurements"])
    assert "slot_empty" in [d["code"] for d in result["diagnostics"]]
    assert result["status"] == "complete"


def test_values_on_left_two_columns_leave_fiscal_slot_empty() -> None:
    obs, values = _three_period_table((1, 2))
    result = bind_operating_table(obs, work_budget=budget())
    col6 = column_by_native(result, 1)
    col12 = column_by_native(result, 2)
    colf = column_by_native(result, 3)
    assert measurement_for(result, values[1])["column_id"] == col6["column_id"]
    assert measurement_for(result, values[2])["column_id"] == col12["column_id"]
    assert all(m["column_id"] != colf["column_id"] for m in result["measurements"])
    assert "slot_empty" in [d["code"] for d in result["diagnostics"]]


def test_row_label_of_bound_measurement_is_kept_as_ref() -> None:
    obs, values = _three_period_table((1,))
    result = bind_operating_table(obs, work_budget=budget())
    m = measurement_for(result, values[1])
    assert m["row_label_refs"] == [
        {"unit_id": "u-lab", "char_start": 0, "char_end": len("Total GMV")}
    ]
    # the stub label is a label, never a measurement of its own
    label_ref = {"unit_id": "u-lab", "char_start": 0, "char_end": len("Total GMV")}
    assert all(mm["value_ref"] != label_ref for mm in result["measurements"])


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
