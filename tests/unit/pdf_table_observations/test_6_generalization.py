"""Card B-6: different legal table ids, header orders and business names.

No company name, page number or sample golden value is special-cased: the same
evidence shapes must produce the same semantics with any identifiers."""

from __future__ import annotations

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.table_measurements import bind_operating_table
from company_wiki.document_normalization.pdf_table_observations import (
    build_pdf_table_observations,
)

from .builders import layout_hints, observation, row_unit

PARENT = "urn:company-wiki:source:sha256:cccc"


def budget(n: int = 100_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


def _slice(table, ref):
    unit = table["units"][ref["unit_id"]]
    return unit["text"][ref["char_start"]:ref["char_end"]]


def test_header_order_and_business_names_do_not_change_the_semantics():
    samples = [
        ("p3:t7", 5, [("Metric", "FY2025", "FY2024"), ("Stores by operating model", "16", "21")]),
        ("t-x", 400, [("项目", "2025年", "2024年"), ("经销商门店", "38", "47")]),
        ("p223:t0", 223, [("項 目", "2025年度", "2024年度"), ("產能利用率", "91%", "88%")]),
    ]
    for table_id, page, grid in samples:
        units = [
            row_unit(
                f"u-{table_id}-{row}",
                list(enumerate(cells)),
                row=row,
                table_id=table_id,
                page=page,
                parent=PARENT,
                kind="table_header" if row == 0 else "table_row",
            )
            for row, cells in enumerate(grid)
        ]
        hints = layout_hints(
            region_units=[u["unit_id"] for u in units],
            header_units=[units[0]["unit_id"]],
            data_rows=[[units[1]["unit_id"]]],
        )
        result = build_pdf_table_observations(observation(units), hints, work_budget=budget())
        table, = result["tables"]
        assert table["scope"] == {"parent_id": PARENT, "table_id": table_id, "page": page}
        assert table["header_rows"] == [0]
        bound = bind_operating_table(table, work_budget=budget())
        values = [
            _slice(table, m["value_ref"]) for m in bound["measurements"]
        ]
        assert sorted(values) == sorted(grid[1])
        assert result["status"] == "partial"
        assert all(m["row_label_refs"] == [] for m in bound["measurements"])
        assert all(m["binding_status"] == "bound" for m in bound["measurements"])


def test_multi_row_header_blocks_follow_relations_not_header_row_constants():
    # 共享关系说表头是两行（例如期间行+单位行），wire 只声明第 0 行
    units = [
        row_unit("h0", [(0, "项目"), (1, "2025年"), (2, "2024年")], row=0, table_id="p1:t0",
                 kind="table_header"),
        row_unit("h1", [(0, "单位"), (1, "人民币万元"), (2, "人民币万元")], row=1, table_id="p1:t0"),
        row_unit("r2", [(0, "门店"), (1, "18"), (2, "21")], row=2, table_id="p1:t0"),
    ]
    hints = layout_hints(
        region_units=["h0", "h1", "r2"], header_units=["h0", "h1"], data_rows=[["r2"]]
    )
    result = build_pdf_table_observations(observation(units), hints, work_budget=budget())
    table, = result["tables"]
    assert table["header_rows"] == [0, 1]  # 证据给两行就是两行，不是固定 4 行
    bound = bind_operating_table(table, work_budget=budget())
    assert {m["binding_status"] for m in bound["measurements"]} == {"bound"}
    assert all(
        _slice(table, m["value_ref"]) in {"门店", "18", "21"} for m in bound["measurements"]
    )


def test_newest_year_is_never_a_header_rule():
    # 表头行在第 1 行（第 0 行是数据行），且年份从新到旧反序：都不影响判定
    units = [
        row_unit("r0", [(0, "直营门店"), (1, "18")], row=0, table_id="p1:t0"),
        row_unit("h1", [(0, "项目"), (1, "2025年")], row=1, table_id="p1:t0"),
        row_unit("r2", [(0, "经销商门店"), (1, "47")], row=2, table_id="p1:t0"),
    ]
    hints = layout_hints(
        region_units=["r0", "h1", "r2"], header_units=["h1"], data_rows=[["r0"], ["r2"]]
    )
    result = build_pdf_table_observations(observation(units), hints, work_budget=budget())
    table, = result["tables"]
    assert table["header_rows"] == [1]
    bound = bind_operating_table(table, work_budget=budget())
    values = {_slice(table, m["value_ref"]) for m in bound["measurements"]}
    assert values == {"直营门店", "经销商门店", "18", "47"}  # 第 0 行的 18 仍是值，不是标题
