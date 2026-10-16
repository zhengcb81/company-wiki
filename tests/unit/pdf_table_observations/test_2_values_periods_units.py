"""Card B-2: same value in two periods, verbatim words, row label/unit/scope refs.

The expected binder outcomes here are the A-3 manual expectations: each value
ref must slice the original row text exactly at its own occurrence, row label
and caption fragments are carried as real refs (never rewritten), and missing
facts stay unknown instead of being filled from neighbours.
"""

from __future__ import annotations

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.table_measurements import bind_operating_table
from company_wiki.document_normalization.pdf_table_observations import (
    build_pdf_table_observations,
)

from .builders import caption_unit, layout_hints, observation, row_unit

PARENT = "urn:company-wiki:source:sha256:aaaa"
TABLE = "p1:t0"


def budget(n: int = 100_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


def _sample():
    rows = {
        0: [(0, "项目"), (1, "截至2025年12月31日"), (2, "截至2024年12月31日")],
        1: [(0, "海外直营门店"), (1, "16"), (2, "16")],
        2: [(0, "净利润变动"), (1, "-1,200"), (2, "—")],
        3: [(0, "经营进展"), (1, "稳步推进"), (2, "稳步提升")],
    }
    units = [
        row_unit(
            f"u-r{row}",
            cells,
            row=row,
            table_id=TABLE,
            parent=PARENT,
            kind="table_header" if row == 0 else "table_row",
        )
        for row, cells in rows.items()
    ]
    caption = caption_unit("u-cap", "单位：（人民币万元）", parent=PARENT)
    hints = layout_hints(
        region_units=[u["unit_id"] for u in units],
        header_units=["u-r0"],
        data_rows=[["u-r1"], ["u-r2"], ["u-r3"]],
        caption_units=["u-cap"],
    )
    return observation(units + [caption]), hints


def _slice(table, ref):
    unit = table["units"][ref["unit_id"]]
    return unit["text"][ref["char_start"]:ref["char_end"]]


def _cell(table, row, column):
    return next(c for c in table["cells"] if (c["row"], c["column"]) == (row, column))


def test_header_rows_follow_evidence_not_row_index_constants():
    obs, hints = _sample()
    result = build_pdf_table_observations(obs, hints, work_budget=budget())
    assert result["status"] == "partial"
    assert "ROW_LABEL_UNAVAILABLE" in {d["code"] for d in result["diagnostics"]}
    table, = result["tables"]
    assert table["header_rows"] == [0]
    assert all(
        cell["row_span"] is None and cell["column_span"] is None for cell in table["cells"]
    )


def test_same_value_in_two_periods_keeps_two_exact_occurrence_refs():
    obs, hints = _sample()
    result = build_pdf_table_observations(obs, hints, work_budget=budget())
    table, = result["tables"]
    earlier = _cell(table, 1, 1)
    later = _cell(table, 1, 2)
    assert [_slice(table, r) for r in earlier["text_refs"]] == ["16"]
    assert [_slice(table, r) for r in later["text_refs"]] == ["16"]
    first = earlier["text_refs"][0]
    second = later["text_refs"][0]
    assert first["unit_id"] == second["unit_id"] == "u-r1"
    assert (first["char_start"], first["char_end"]) != (second["char_start"], second["char_end"])
    row_text = table["units"]["u-r1"]["text"]
    assert row_text[first["char_start"]:first["char_end"]] == "16"
    assert row_text[second["char_start"]:second["char_end"]] == "16"
    assert row_text.count("16") == 2

    bound = bind_operating_table(table, work_budget=budget())
    early_m = next(
        m for m in bound["measurements"]
        if m["value_ref"]["char_start"] == first["char_start"]
    )
    late_m = next(
        m for m in bound["measurements"]
        if m["value_ref"]["char_start"] == second["char_start"]
    )
    assert early_m["column_id"] == "col-1" and early_m["period"]["end"] == "2025-12-31"
    assert late_m["column_id"] == "col-2" and late_m["period"]["end"] == "2024-12-31"
    assert early_m["binding_status"] == late_m["binding_status"] == "bound"


def test_row_label_unit_and_scope_refs_point_at_their_own_fragments():
    obs, hints = _sample()
    result = build_pdf_table_observations(obs, hints, work_budget=budget())
    table, = result["tables"]
    value_cell = _cell(table, 1, 1)
    label_ref = _cell(table, 1, 0)["text_refs"][0]
    assert [_slice(table, r) for r in _cell(table, 1, 0)["text_refs"]] == ["海外直营门店"]
    assert label_ref not in value_cell["header_refs"]  # native first column is not an observed row-label role
    caption_refs = [r for r in value_cell["header_refs"] if r["unit_id"] == "u-cap"]
    assert caption_refs and _slice(table, caption_refs[0]) == "单位：（人民币万元）"

    bound = bind_operating_table(table, work_budget=budget())
    value = next(
        m for m in bound["measurements"]
        if _slice(table, m["value_ref"]) == "16" and m["column_id"] == "col-1"
    )
    # No native row-label role exists on this wire: keep the original cell,
    # but do not borrow its text as a proven label for another value.
    assert value["row_label_refs"] == []
    assert any(_slice(table, m["value_ref"]) == "海外直营门店" for m in bound["measurements"])
    # 单位：来自 caption 片段，原词不变更、无换算
    assert [_slice(table, r) for r in value["unit_refs"]] == ["（人民币万元）"]
    # The neighbouring cell contains a geographic word, but no relation proves
    # it qualifies this number; scope stays unknown.
    assert value["scope_refs"] == []


def test_verbatim_values_negative_dash_and_strings_are_not_rewritten():
    obs, hints = _sample()
    result = build_pdf_table_observations(obs, hints, work_budget=budget())
    table, = result["tables"]
    texts = [
        _slice(table, ref)
        for cell in table["cells"]
        for ref in cell["text_refs"]
    ]
    assert "-1,200" in texts and "—" in texts and "稳步推进" in texts and "稳步提升" in texts
    bound = bind_operating_table(table, work_budget=budget())
    values = [
        table["units"][m["value_ref"]["unit_id"]]["text"][
            m["value_ref"]["char_start"]:m["value_ref"]["char_end"]
        ]
        for m in bound["measurements"]
    ]
    assert "-1,200" in values and "—" in values
    # Caption is observed context; the leading data cell lacks an observed
    # label role and must remain available as original data instead of vanishing.
    assert "海外直营门店" in values and "单位：（人民币万元）" not in values


def test_scale_currency_and_composite_unit_words_stay_verbatim():
    # 卡 B-2 点名：万元/亿元/币种/复合单位都不改原词，单位引用指向各自原片段
    rows = {
        0: [(0, "项目"), (1, "截至2025年12月31日")],
        1: [(0, "合同负债（人民币亿元）"), (1, "3.2")],
        2: [(0, "海外收入（US$千元）"), (1, "1,024")],
        3: [(0, "每股收益（人民币元）"), (1, "0.52")],
        4: [(0, "门店数（家）"), (1, "7,000")],
    }
    units = [
        row_unit(
            f"u-r{row}",
            cells,
            row=row,
            table_id=TABLE,
            parent=PARENT,
            kind="table_header" if row == 0 else "table_row",
        )
        for row, cells in rows.items()
    ]
    hints = layout_hints(
        region_units=[u["unit_id"] for u in units],
        header_units=["u-r0"],
        data_rows=[[f"u-r{r}"] for r in range(1, 5)],
    )
    result = build_pdf_table_observations(observation(units), hints, work_budget=budget())
    table, = result["tables"]
    texts = {_slice(table, ref) for cell in table["cells"] for ref in cell["text_refs"]}
    # 原词逐字保留：数值、单位词、复合单位括号都不改写
    assert {"3.2", "1,024", "0.52", "7,000"} <= texts
    assert {"合同负债（人民币亿元）", "海外收入（US$千元）", "每股收益（人民币元）", "门店数（家）"} <= texts

    bound = bind_operating_table(table, work_budget=budget())
    by_value = {
        _slice(table, m["value_ref"]): m for m in bound["measurements"]
    }
    assert set(by_value) == {"0.52", "1,024", "3.2", "7,000", "合同负债（人民币亿元）", "海外收入（US$千元）", "每股收益（人民币元）", "门店数（家）"}
    # Unit words in adjacent cells are preserved verbatim but not silently
    # promoted to a relation that the input never observed.
    for number in ("3.2", "1,024", "0.52", "7,000"):
        assert by_value[number]["unit_refs"] == []
        assert by_value[number]["row_label_refs"] == []
    assert result["status"] == "partial"


def test_missing_header_evidence_stays_unknown():
    obs, hints = _sample()
    # 没有任何共享 header 关系，且 wire 不声明表头行时，不得自造表头
    for unit in obs["units"]:
        if unit["kind"] == "table_header":
            unit["kind"] = "table_row"
    result = build_pdf_table_observations(obs, None, work_budget=budget())
    table, = result["tables"]
    assert table["header_rows"] == []
    bound = bind_operating_table(table, work_budget=budget())
    assert all(m["period"] is None for m in bound["measurements"])
    assert all(m["binding_status"] == "ambiguous" for m in bound["measurements"])
    assert "no_header_path" in {d["code"] for d in bound["diagnostics"]}
