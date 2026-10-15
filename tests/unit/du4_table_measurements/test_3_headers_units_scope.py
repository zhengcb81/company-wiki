"""Semantic counterexamples: multi-level headers, unit scope, scope/qualifier
refs and raw-value preservation.

Expected results were written independently of the implementation: parallel
CN/EN labels of one column are two labels of the same period, conflicting
labels never get one side chosen, units stay at their real cell/row/table
scope and never mix across metrics, and negative/bracketed/dash values are
kept verbatim instead of being flattened to zero.
"""

from __future__ import annotations

import pytest

from builders import (
    cell,
    column_by_native,
    diagnostic_codes,
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


def test_parallel_cn_en_labels_are_two_labels_of_one_period() -> None:
    u_h = unit(
        "u-h",
        "For the six months ended December 31, 截至12月31日止六個月 2023 2023年",
        kind="table_header",
    )
    u_v = unit("u-v", "6,895")
    h_en = text_ref("u-h", u_h["text"], "For the six months ended December 31,")
    h_cn = text_ref("u-h", u_h["text"], "截至12月31日止六個月")
    y_en = text_ref("u-h", u_h["text"], "2023")
    y_cn = text_ref("u-h", u_h["text"], "2023年")
    value = text_ref("u-v", u_v["text"], "6,895")
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[h_en, h_cn]),  # one cell, two labels
        cell("h1", 1, 1, presence="present", text_refs=[y_en, y_cn]),
        cell("v", 2, 1, presence="present", text_refs=[value]),
    ]
    obs = observation({"u-h": u_h, "u-v": u_v}, cells, header_rows=[0, 1])
    result = bind_operating_table(obs, work_budget=budget())
    col = column_by_native(result, 1)
    assert period_fields(col["period"]) == {
        "kind": "duration",
        "start": None,
        "end": "2023-12-31",
        "duration_months": 6,
        "fiscal_label": None,
    }
    assert col["period"]["raw_label_refs"] == [h_en, h_cn, y_en, y_cn]
    m = measurement_for(result, value)
    assert m["binding_status"] == "bound"
    assert m["period"]["raw_label_refs"] == [h_en, h_cn, y_en, y_cn]


def test_conflicting_parallel_labels_never_pick_one_side() -> None:
    u_h = unit(
        "u-h",
        "For the six months ended December 31, 截至12月31日止十二個月 2023",
        kind="table_header",
    )
    u_v = unit("u-v", "6,895")
    h_en = text_ref("u-h", u_h["text"], "For the six months ended December 31,")
    h_cn = text_ref("u-h", u_h["text"], "截至12月31日止十二個月")
    y = text_ref("u-h", u_h["text"], "2023")
    value = text_ref("u-v", u_v["text"], "6,895")
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[h_en]),
        cell("h0b", 1, 1, presence="present", text_refs=[h_cn]),
        cell("h1", 2, 1, presence="present", text_refs=[y]),
        cell("v", 3, 1, presence="present", text_refs=[value]),
    ]
    obs = observation({"u-h": u_h, "u-v": u_v}, cells, header_rows=[0, 1, 2])
    result = bind_operating_table(obs, work_budget=budget())
    col = column_by_native(result, 1)
    assert col["status"] == "ambiguous"
    assert period_fields(col["period"]) == {
        "kind": "unspecified",
        "start": None,
        "end": None,
        "duration_months": None,
        "fiscal_label": None,
    }
    assert "header_period_conflict" in diagnostic_codes(result)
    m = measurement_for(result, value)
    assert m["binding_status"] == "ambiguous"
    # the native column is still known; only the period is contested
    assert m["column_id"] == col["column_id"]
    assert m["period"] is None


def test_unit_and_footnote_rows_do_not_rewrite_the_period() -> None:
    u_h = unit(
        "u-h",
        "For the twelve months ended December 31, 2023 RMB in millions",
        kind="table_header",
    )
    u_lab = unit("u-lab", "Total GMV(1)")
    u_v = unit("u-v", "6,895")
    h_period = text_ref("u-h", u_h["text"], "For the twelve months ended December 31,")
    h_year = text_ref("u-h", u_h["text"], "2023")
    h_unit = text_ref("u-h", u_h["text"], "RMB in millions")
    label = text_ref("u-lab", u_lab["text"], "Total GMV(1)")
    value = text_ref("u-v", u_v["text"], "6,895")
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[h_period]),
        cell("h1", 1, 1, presence="present", text_refs=[h_year]),
        cell("h2", 2, 1, presence="present", text_refs=[h_unit]),
        cell("lab", 3, 0, presence="present", text_refs=[label]),
        cell("v", 3, 1, presence="present", text_refs=[value], header_refs=[label]),
    ]
    obs = observation({"u-h": u_h, "u-lab": u_lab, "u-v": u_v}, cells, header_rows=[0, 1, 2])
    result = bind_operating_table(obs, work_budget=budget())
    col = column_by_native(result, 1)
    assert period_fields(col["period"]) == {
        "kind": "duration",
        "start": None,
        "end": "2023-12-31",
        "duration_months": 12,
        "fiscal_label": None,
    }
    m = measurement_for(result, value)
    assert m["binding_status"] == "bound"
    # column-level unit kept as its own ref, footnote marker kept as qualifier
    assert m["unit_refs"] == [h_unit]
    assert text_ref("u-lab", u_lab["text"], "(1)") in m["qualifier_refs"]


def _unit_scope_table() -> tuple[dict, dict[str, dict]]:
    u_h = unit(
        "u-h",
        "For the fiscal year ended December 31, 2024",
        kind="table_header",
    )
    labels = [
        ("u-l1", "Total GMV(1) (RMB in millions)", "6,895"),
        ("u-l2", "Total number of transactions (in millions)", "183.2"),
        ("u-l3", "Average spending per transaction (RMB)", "37.6"),
        ("u-l4", "Same-store(2) GMV Growth (%)", "42"),
        ("u-l5", "Number of stores", "522"),
        ("u-l6", "Number of retail partners", "295"),
        ("u-l7", "Growth", "37.6%"),
    ]
    units = {"u-h": u_h}
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "For the fiscal year ended December 31,")]),
        cell("h1", 1, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "2024")]),
    ]
    value_refs: dict[str, dict] = {}
    for i, (uid, label_text, value_text) in enumerate(labels, start=2):
        u_lab = unit(f"{uid}-lab", label_text)
        u_val = unit(f"{uid}-val", value_text)
        units[f"{uid}-lab"] = u_lab
        units[f"{uid}-val"] = u_val
        label = text_ref(f"{uid}-lab", label_text, label_text)
        value = text_ref(f"{uid}-val", value_text, value_text)
        cells.append(cell(f"lab{i}", i, 0, presence="present", text_refs=[label]))
        cells.append(
            cell(f"v{i}", i, 1, presence="present", text_refs=[value], header_refs=[label])
        )
        value_refs[label_text] = value
    return observation(units, cells, header_rows=[0, 1]), value_refs


def test_units_stay_at_their_real_scope_and_never_mix_across_metrics() -> None:
    obs, values = _unit_scope_table()
    result = bind_operating_table(obs, work_budget=budget())

    def unit_texts(m: dict) -> set[str]:
        out = set()
        for ref in m["unit_refs"]:
            text = obs["units"][ref["unit_id"]]["text"]
            out.add(text[ref["char_start"] : ref["char_end"]])
        return out

    m_gmv = measurement_for(result, values["Total GMV(1) (RMB in millions)"])
    m_trx = measurement_for(result, values["Total number of transactions (in millions)"])
    m_avg = measurement_for(result, values["Average spending per transaction (RMB)"])
    m_pct = measurement_for(result, values["Same-store(2) GMV Growth (%)"])
    m_stores = measurement_for(result, values["Number of stores"])
    m_partners = measurement_for(result, values["Number of retail partners"])
    m_inline = measurement_for(result, values["Growth"])

    assert unit_texts(m_gmv) == {"(RMB in millions)"}
    assert unit_texts(m_trx) == {"(in millions)"}
    assert unit_texts(m_avg) == {"(RMB)"}
    assert unit_texts(m_pct) == {"(%)"}
    # counts carry no invented unit expression, and stay distinct rows
    assert m_stores["unit_refs"] == []
    assert m_partners["unit_refs"] == []
    # cell-level percent is the tightest scope for its own value only
    assert m_inline["unit_refs"] == [text_ref("u-l7-val", "37.6%", "%")]
    # same-store qualifier kept as its own refs
    assert text_ref("u-l4-lab", "Same-store(2) GMV Growth (%)", "(2)") in m_pct["qualifier_refs"]
    assert text_ref("u-l4-lab", "Same-store(2) GMV Growth (%)", "Same-store") in m_pct["qualifier_refs"]
    # no unit ref is ever shared between two metrics (units never mix)
    all_unit_refs = [
        (r["unit_id"], r["char_start"], r["char_end"])
        for m in (m_gmv, m_trx, m_avg, m_pct, m_stores, m_partners, m_inline)
        for r in m["unit_refs"]
    ]
    assert len(all_unit_refs) == len(set(all_unit_refs))


def test_scope_refs_keep_original_region_channel_and_tier_labels() -> None:
    u_h = unit("u-h", "As of December 31, 2024", kind="table_header")
    rows = [
        ("u-s1", "Asia excluding China 亞洲（中國除外）", "1,333"),
        ("u-s2", "First-tier cities 一線城市", "522"),
        ("u-s3", "New stores 新增门店", "88"),
        ("u-s4", "Omni-channel 全渠道", "9"),
    ]
    units = {"u-h": u_h}
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "As of December 31,")]),
        cell("h1", 1, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "2024")]),
    ]
    for i, (uid, label_text, value_text) in enumerate(rows, start=2):
        u_lab = unit(f"{uid}-lab", label_text)
        u_val = unit(f"{uid}-val", value_text)
        units[f"{uid}-lab"] = u_lab
        units[f"{uid}-val"] = u_val
        label = text_ref(f"{uid}-lab", label_text, label_text)
        value = text_ref(f"{uid}-val", value_text, value_text)
        cells.append(cell(f"lab{i}", i, 0, presence="present", text_refs=[label]))
        cells.append(cell(f"v{i}", i, 1, presence="present", text_refs=[value], header_refs=[label]))
        obs = observation(units, cells, header_rows=[0, 1])
        result = bind_operating_table(obs, work_budget=budget())
        m = measurement_for(result, value)
        assert label in m["scope_refs"], label_text
        assert label in m["row_label_refs"], label_text


def test_cross_row_label_applies_to_every_covered_row() -> None:
    u_h = unit("u-h", "As of December 31, 2024", kind="table_header")
    u_lab = unit("u-lab", "Overseas markets 海外市場")
    u_v1 = unit("u-v1", "1,333")
    u_v2 = unit("u-v2", "172")
    label = text_ref("u-lab", u_lab["text"], "Overseas markets 海外市場")
    v1 = text_ref("u-v1", u_v1["text"], "1,333")
    v2 = text_ref("u-v2", u_v2["text"], "172")
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "As of December 31,")]),
        cell("h1", 1, 1, presence="present", text_refs=[text_ref("u-h", u_h["text"], "2024")]),
        cell("lab", 2, 0, presence="present", text_refs=[label], row_span=2),
        cell("v1", 2, 1, presence="present", text_refs=[v1], header_refs=[label]),
        cell("v2", 3, 1, presence="present", text_refs=[v2], header_refs=[label]),
    ]
    obs = observation({"u-h": u_h, "u-lab": u_lab, "u-v1": u_v1, "u-v2": u_v2}, cells, header_rows=[0, 1])
    result = bind_operating_table(obs, work_budget=budget())
    for v in (v1, v2):
        m = measurement_for(result, v)
        assert m["binding_status"] == "bound"
        assert m["row_label_refs"] == [label]
        assert m["scope_refs"] == [label]


def test_identical_column_labels_do_not_auto_merge_columns() -> None:
    u_h = unit("u-h", "2023 2023年", kind="table_header")
    u_v = unit("u-v", "522 587")
    h1 = text_ref("u-h", u_h["text"], "2023")
    h2 = text_ref("u-h", u_h["text"], "2023年")
    v1 = text_ref("u-v", u_v["text"], "522")
    v2 = text_ref("u-v", u_v["text"], "587")
    cells = [
        cell("h1", 0, 1, presence="present", text_refs=[h1]),
        cell("h2", 0, 2, presence="present", text_refs=[h2]),
        cell("v1", 1, 1, presence="present", text_refs=[v1]),
        cell("v2", 1, 2, presence="present", text_refs=[v2]),
    ]
    obs = observation({"u-h": u_h, "u-v": u_v}, cells, header_rows=[0])
    result = bind_operating_table(obs, work_budget=budget())
    col1 = column_by_native(result, 1)
    col2 = column_by_native(result, 2)
    assert col1["column_id"] != col2["column_id"]
    assert measurement_for(result, v1)["column_id"] == col1["column_id"]
    assert measurement_for(result, v2)["column_id"] == col2["column_id"]


def test_negative_bracketed_and_dash_values_are_kept_verbatim() -> None:
    u_h = unit("u-h", "As of December 31, 2024", kind="table_header")
    u_v = unit("u-v", "(1,234) - 0 35%~40% 14.3")
    h = text_ref("u-h", u_h["text"], "As of December 31,")
    y = text_ref("u-h", u_h["text"], "2024")
    values = {
        "(1,234)": text_ref("u-v", u_v["text"], "(1,234)"),
        "-": text_ref("u-v", u_v["text"], "-"),
        "0": text_ref("u-v", u_v["text"], "0"),
        "35%~40%": text_ref("u-v", u_v["text"], "35%~40%"),
        "14.3": text_ref("u-v", u_v["text"], "14.3"),
    }
    cells = [
        cell("h0", 0, 1, presence="present", text_refs=[h]),
        cell("h1", 1, 1, presence="present", text_refs=[y]),
    ]
    for i, (raw, ref) in enumerate(values.items(), start=2):
        cells.append(cell(f"v{i}", i, 1, presence="present", text_refs=[ref]))
    obs = observation({"u-h": u_h, "u-v": u_v}, cells, header_rows=[0, 1])
    result = bind_operating_table(obs, work_budget=budget())
    for raw, ref in values.items():
        m = measurement_for(result, ref)
        text = obs["units"][ref["unit_id"]]["text"][ref["char_start"] : ref["char_end"]]
        assert text == raw  # verbatim: nothing collapsed to zero or rewritten
        assert m["binding_status"] == "bound"
        assert m["column_id"] == column_by_native(result, 1)["column_id"]
        # a bracketed negative is a value, not a footnote qualifier
        assert all(q != ref for q in m["qualifier_refs"])
    # a dash value is not an empty slot
    assert "slot_empty" not in diagnostic_codes(result)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
