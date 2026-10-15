"""Semantic counterexamples: merged cells, unknown slots, provenance limits.

Mirrors the frozen card bullets: a merged big cell without per-value native
positioning stays ambiguous while positioned right-column values bind;
None / real empty string / merged_unknown stay distinct; a coarse whole-table
bbox is never copied into fine cells; equal table indexes on different
pages/parents are never stitched together.
"""

from __future__ import annotations

import pytest

from .builders import (
    cell,
    column_by_native,
    diagnostic_codes,
    measurement_for,
    observation,
    text_ref,
    unit,
)

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.table_measurements import bind_operating_table


def budget(n: int = 10_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


def _hk_like_merged_table() -> tuple[dict, dict[str, dict]]:
    """2023/2024 header, merged left cell with embedded values, later right column."""
    u_h = unit("u-h", "As of December 31, 2023 2024", kind="table_header")
    u_blob = unit("u-blob", "First-tier cities 522 Second-tier cities 1,617")
    u_r1 = unit("u-r1", "587")
    u_r2 = unit("u-r2", "1,822")
    u_r3 = unit("u-r3", "4,386")
    h_span = text_ref("u-h", u_h["text"], "As of December 31,")
    h_2023 = text_ref("u-h", u_h["text"], "2023")
    h_2024 = text_ref("u-h", u_h["text"], "2024")
    v_522 = text_ref("u-blob", u_blob["text"], "522")
    v_1617 = text_ref("u-blob", u_blob["text"], "1,617")
    r1 = text_ref("u-r1", u_r1["text"], "587")
    r2 = text_ref("u-r2", u_r2["text"], "1,822")
    r3 = text_ref("u-r3", u_r3["text"], "4,386")
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[h_span], column_span=2),
        cell("h0c2", 0, 2, presence="merged_unknown"),
        cell("h1", 1, 1, presence="present", text_refs=[h_2023]),
        cell("h2", 1, 2, presence="present", text_refs=[h_2024]),
        # merged big left cell: two value refs, no per-value native column
        cell("blob", 2, 0, presence="present", text_refs=[v_522, v_1617], column_span=2, row_span=3),
        cell("cov10", 3, 0, presence="merged_unknown"),
        cell("cov11", 3, 1, presence="merged_unknown"),
        cell("cov20", 4, 0, presence="merged_unknown"),
        cell("cov21", 4, 1, presence="merged_unknown"),
        # later rows: positioned right-column values
        cell("r1", 2, 2, presence="present", text_refs=[r1]),
        cell("r2", 3, 2, presence="present", text_refs=[r2]),
        cell("r3", 5, 2, presence="present", text_refs=[r3]),
    ]
    obs = observation(
        {"u-h": u_h, "u-blob": u_blob, "u-r1": u_r1, "u-r2": u_r2, "u-r3": u_r3},
        cells,
        header_rows=[0, 1],
    )
    return obs, {"v_522": v_522, "v_1617": v_1617, "r1": r1, "r2": r2, "r3": r3}


def test_merged_cell_values_stay_ambiguous_and_positioned_right_column_binds() -> None:
    obs, refs = _hk_like_merged_table()
    result = bind_operating_table(obs, work_budget=budget())
    for key in ("v_522", "v_1617"):
        m = measurement_for(result, refs[key])
        assert m["binding_status"] == "ambiguous", key
        assert m["column_id"] is None, key
        assert m["period"] is None, key
        assert refs[key] in result["unbound_value_refs"]
    col_2024 = column_by_native(result, 2)
    for key in ("r1", "r2", "r3"):
        m = measurement_for(result, refs[key])
        assert m["binding_status"] == "bound", key
        assert m["column_id"] == col_2024["column_id"], key
        assert m["period"]["kind"] == "as_of"
        assert m["period"]["end"] == "2024-12-31"
    # nothing was pulled back onto the 2023 column
    col_2023 = column_by_native(result, 1)
    assert all(m["column_id"] != col_2023["column_id"] for m in result["measurements"])
    codes = diagnostic_codes(result)
    assert "slot_merged_unknown" in codes
    assert result["status"] == "partial"


def test_none_empty_and_merged_unknown_slots_stay_distinct() -> None:
    u_v = unit("u-v", "42")
    u_lab = unit("u-lab", "Some label")
    value = text_ref("u-v", u_v["text"], "42")
    label = text_ref("u-lab", u_lab["text"], "Some label")
    cells = [
        cell("unavailable_slot", 0, 0, presence="unavailable"),
        cell("empty_slot", 0, 1, presence="empty"),
        cell("merged_slot", 0, 2, presence="merged_unknown"),
        # merged_unknown carrying a value ref is still a value candidate: ambiguous
        cell("merged_value", 1, 2, presence="merged_unknown", text_refs=[value], header_refs=[label]),
        cell("label", 1, 0, presence="present", text_refs=[label]),
    ]
    obs = observation({"u-v": u_v, "u-lab": u_lab}, cells, header_rows=None)
    result = bind_operating_table(obs, work_budget=budget())
    codes = diagnostic_codes(result)
    assert "slot_unavailable" in codes
    assert "slot_empty" in codes
    assert "slot_merged_unknown" in codes
    # the extractor-missing slot is not silently treated as a real empty slot
    assert [d["code"] for d in result["diagnostics"] if d.get("cell_id") == "unavailable_slot"] == [
        "slot_unavailable"
    ]
    m = measurement_for(result, value)
    assert m["binding_status"] == "ambiguous"
    assert "merged_value_no_column" in codes
    # no value was invented for empty/unavailable/merged slots without refs
    assert len(result["measurements"]) == 1


def test_label_ref_used_as_header_is_never_a_measurement() -> None:
    u_v = unit("u-v", "42")
    u_lab = unit("u-lab", "Some label")
    value = text_ref("u-v", u_v["text"], "42")
    label = text_ref("u-lab", u_lab["text"], "Some label")
    cells = [
        cell("label", 0, 0, presence="present", text_refs=[label]),
        cell("v", 0, 1, presence="present", text_refs=[value], header_refs=[label]),
    ]
    obs = observation({"u-v": u_v, "u-lab": u_lab}, cells)
    result = bind_operating_table(obs, work_budget=budget())
    assert [m["value_ref"] for m in result["measurements"]] == [value]
    assert measurement_for(result, value)["row_label_refs"] == [label]


def test_coarse_table_bbox_is_not_copied_into_fine_cells() -> None:
    u_h = unit("u-h", "As of December 31, 2024", kind="table_header")
    u_v = unit("u-v", "42")
    value = text_ref("u-v", u_v["text"], "42")
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "As of December 31,")]),
        cell("h1", 1, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "2024")]),
        cell("v", 2, 1, presence="present", text_refs=[value]),
    ]
    obs = observation(
        {"u-h": u_h, "u-v": u_v},
        cells,
        header_rows=[0, 1],
        provenance=[
            {
                "cell_id": "v",
                "kind": "fine_geometry",
                "bbox": [0.0, 0.0, 100.0, 100.0],  # whole-table box, no span result
            }
        ],
    )
    result = bind_operating_table(obs, work_budget=budget())
    codes = diagnostic_codes(result)
    assert "coarse_geometry_ignored" in codes
    m = measurement_for(result, value)
    # the coarse box did not become a fine cell: the native slot still binds
    assert m["binding_status"] == "bound"
    assert m["column_id"] == column_by_native(result, 1)["column_id"]


def test_provenance_span_attribution_is_used_for_merged_cells() -> None:
    u_h = unit("u-h", "2023 2024", kind="table_header")
    u_v = unit("u-v", "522")
    h_2023 = text_ref("u-h", u_h["text"], "2023")
    h_2024 = text_ref("u-h", u_h["text"], "2024")
    value = text_ref("u-v", u_v["text"], "522")
    cells = [
        cell("h1", 0, 1, presence="present", text_refs=[h_2023]),
        cell("h2", 0, 2, presence="present", text_refs=[h_2024]),
        cell("v", 1, 1, presence="present", text_refs=[value]),
    ]
    obs = observation(
        {"u-h": u_h, "u-v": u_v},
        cells,
        header_rows=[0],
        provenance=[
            {"cell_id": "v", "kind": "native_slot", "column_span": 2, "row_span": 1}
        ],
    )
    result = bind_operating_table(obs, work_budget=budget())
    m = measurement_for(result, value)
    assert m["binding_status"] == "ambiguous"
    assert m["column_id"] is None


def test_same_table_index_on_different_pages_is_not_stitched() -> None:
    def one(page: int, parent: str, value_text: str, val_id: str) -> tuple[dict, dict]:
        u_v = unit(val_id, value_text, parent_id=parent, locator={"page_number": page})
        ref = text_ref(val_id, value_text, value_text)
        obs = observation(
            {val_id: u_v},
            [cell("v", 1, 1, presence="present", text_refs=[ref])],
            parent_id=parent,
            table_id="t0",
            page=page,
        )
        return obs, ref

    obs_a, ref_a = one(14, "parent-a", "522", "u-a")
    obs_b, ref_b = one(17, "parent-b", "1,333", "u-b")
    res_a = bind_operating_table(obs_a, work_budget=budget())
    res_b = bind_operating_table(obs_b, work_budget=budget())
    assert res_a["scope"] == {"parent_id": "parent-a", "table_id": "t0", "page": 14}
    assert res_b["scope"] == {"parent_id": "parent-b", "table_id": "t0", "page": 17}
    assert res_a["measurements"][0]["value_ref"] == ref_a
    assert res_b["measurements"][0]["value_ref"] == ref_b
    assert all(m["value_ref"] != ref_b for m in res_a["measurements"])
    assert all(m["value_ref"] != ref_a for m in res_b["measurements"])


def test_cross_parent_and_cross_page_refs_are_not_silently_bound() -> None:
    u_v = unit("u-v", "522", parent_id="other-parent")
    u_w = unit("u-w", "587", parent_id="parent-1", locator={"page_number": 9})
    value = text_ref("u-v", u_v["text"], "522")
    other_page = text_ref("u-w", u_w["text"], "587")
    cells = [
        cell("v", 1, 1, presence="present", text_refs=[value]),
        cell("w", 2, 1, presence="present", text_refs=[other_page]),
    ]
    obs = observation({"u-v": u_v, "u-w": u_w}, cells, parent_id="parent-1", page=1)
    result = bind_operating_table(obs, work_budget=budget())
    m1 = measurement_for(result, value)
    m2 = measurement_for(result, other_page)
    assert m1["binding_status"] == "ambiguous"
    assert m2["binding_status"] == "ambiguous"
    codes = diagnostic_codes(result)
    assert "cross_parent_ref" in codes
    assert "cross_page_ref" in codes


def test_truncation_and_missing_page_are_diagnostics() -> None:
    u_v = unit("u-v", "42")
    value = text_ref("u-v", u_v["text"], "42")
    obs = observation(
        {"u-v": u_v},
        [cell("v", 1, 1, presence="present", text_refs=[value])],
        page=None,
        truncated=True,
    )
    result = bind_operating_table(obs, work_budget=budget())
    codes = diagnostic_codes(result)
    assert "observation_truncated" in codes
    assert "page_not_observed" in codes
    assert result["status"] != "complete"
    assert result["status"] == "partial"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
