"""Card B-3: sparse columns, lost empty slots, missing bbox, span None, unknown
frame, unavailable header, bad offsets and foreign-parent refs — every gap must
degrade to unknown instead of being filled by a guess."""

from __future__ import annotations

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.table_measurements import bind_operating_table
from company_wiki.document_normalization.pdf_table_observations import (
    build_pdf_table_observations,
)

from .builders import (
    caption_unit,
    fine_cell,
    layout_hints,
    observation,
    row_unit,
    wire_unit,
)

PARENT = "urn:company-wiki:source:sha256:aaaa"
FOREIGN = "urn:company-wiki:source:sha256:ffff"
TABLE = "p1:t0"


def budget(n: int = 100_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


def _slice(table, ref):
    unit = table["units"][ref["unit_id"]]
    return unit["text"][ref["char_start"]:ref["char_end"]]


def _codes(result):
    return {d["code"] for d in result["diagnostics"]}


def test_sparse_columns_and_lost_empty_slots_are_not_fabricated():
    # 列 1 在所有行都无观察（空位丢失）：只有列 0/2 有格
    header = row_unit(
        "u-h", [(0, "项目"), (2, "2024年")],
        row=0, table_id=TABLE, kind="table_header",
    )
    sparse = row_unit("u-r", [(0, "直营门店"), (2, "18")], row=1, table_id=TABLE)
    hints = layout_hints(
        region_units=["u-h", "u-r"], header_units=["u-h"], data_rows=[["u-r"]]
    )
    result = build_pdf_table_observations(observation([header, sparse]), hints, work_budget=budget())
    table, = result["tables"]
    slots = {(c["row"], c["column"]) for c in table["cells"]}
    assert (0, 1) not in slots and (1, 1) not in slots  # 空位丢失：不造空单元、不造 TextRef
    assert (1, 0) in slots and (1, 2) in slots
    assert all(c["presence"] != "empty" for c in table["cells"])
    row_texts = {
        _slice(table, r) for c in table["cells"] for r in c["text_refs"] if r["unit_id"] == "u-r"
    }
    assert row_texts == {"直营门店", "18"}
    bound = bind_operating_table(table, work_budget=budget())
    found = next(m for m in bound["measurements"] if _slice(table, m["value_ref"]) == "18")
    assert found["column_id"] == "col-2"  # 稀疏列不左移
    assert "column_without_cells" in {d["code"] for d in bound["diagnostics"]}


def test_missing_bbox_cell_is_dropped_without_a_fabricated_slot():
    # capture_table 只保留有值且有 bbox 的格；第三个值没有 fine cell 条目
    entries = [
        fine_cell("项目", 0, 2, row=0, column=0, table_id=TABLE),
        fine_cell("2025年", 5, 10, row=0, column=1, table_id=TABLE),
    ]
    header = wire_unit(
        "u-h", "项目 | 2025年", page=1, kind="table_header",
        table_id=TABLE, row=0, cells=entries,
    )
    body_entries = [
        fine_cell("门店", 0, 2, row=1, column=0, table_id=TABLE),
        fine_cell("18", 5, 7, row=1, column=1, table_id=TABLE),
    ]
    body = wire_unit(
        "u-r", "门店 | 18 | 未捕获", page=1, kind="table_row",
        table_id=TABLE, row=1, cells=body_entries,
    )
    hints = layout_hints(region_units=["u-h", "u-r"], header_units=["u-h"], data_rows=[["u-r"]])
    result = build_pdf_table_observations(observation([header, body]), hints, work_budget=budget())
    table, = result["tables"]
    texts = {_slice(table, r) for c in table["cells"] for r in c["text_refs"]}
    assert "未捕获" not in texts  # 不为缺 bbox 的值造 ref
    assert {(c["row"], c["column"]) for c in table["cells"]} == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_spans_stay_unknown_and_never_default_to_one():
    header = row_unit("u-h", [(0, "项目"), (1, "2025年")], row=0, table_id=TABLE, kind="table_header")
    body = row_unit("u-r", [(0, "门店"), (1, "18")], row=1, table_id=TABLE)
    hints = layout_hints(region_units=["u-h", "u-r"], header_units=["u-h"], data_rows=[["u-r"]])
    result = build_pdf_table_observations(observation([header, body]), hints, work_budget=budget())
    table, = result["tables"]
    assert all(c["row_span"] is None and c["column_span"] is None for c in table["cells"])
    assert all(p["row_span"] is None and p["column_span"] is None for p in table["provenance"])
    assert all(p["kind"] == "native_slot" for p in table["provenance"])


def test_unknown_frame_alignment_offsets_and_slice_mismatch_stay_unlocated():
    bad_frame = fine_cell("18", 5, 7, row=1, column=1, table_id=TABLE, frame=None)
    bad_align = fine_cell("19", 10, 12, row=1, column=2, table_id=TABLE, alignment="relocated")
    bad_offset = fine_cell("20", 900, 902, row=1, column=3, table_id=TABLE)
    bad_slice = fine_cell("别的词", 13, 15, row=1, column=4, table_id=TABLE)
    good = fine_cell("17", 0, 2, row=1, column=0, table_id=TABLE)
    body = wire_unit(
        "u-r", "17 | 18 | 19 | 20 | 21", page=1, kind="table_row",
        table_id=TABLE, row=1,
        cells=[good, bad_frame, bad_align, bad_offset, bad_slice],
    )
    header = row_unit("u-h", [(0, "项目"), (1, "2025年"), (2, "2024年")], row=0, table_id=TABLE, kind="table_header")
    hints = layout_hints(region_units=["u-h", "u-r"], header_units=["u-h"], data_rows=[["u-r"]])
    result = build_pdf_table_observations(observation([header, body]), hints, work_budget=budget())
    table, = result["tables"]
    cells = {c["column"]: c for c in table["cells"] if c["row"] == 1}
    assert [_slice(table, r) for r in cells[0]["text_refs"]] == ["17"]
    for column in (1, 2, 3, 4):
        assert cells[column]["presence"] == "present"  # 值确实被观察到
        assert cells[column]["text_refs"] == []        # 但定位不足→unknown，不猜
    assert "CELL_TEXT_UNLOCATABLE" in _codes(result)


def test_header_absence_is_unknown_not_a_row_zero_assumption():
    header = row_unit("u-h", [(0, "项目"), (1, "2025年")], row=0, table_id=TABLE, kind="table_header")
    body = row_unit("u-r", [(0, "门店"), (1, "18")], row=1, table_id=TABLE)
    # 共享引擎把两行都判为数据行、没有 header_for：原生 row-0 声明被反证
    hints = layout_hints(region_units=["u-h", "u-r"], header_units=[], data_rows=[["u-h"], ["u-r"]])
    result = build_pdf_table_observations(observation([header, body]), hints, work_budget=budget())
    table, = result["tables"]
    assert table["header_rows"] == []


def test_foreign_parent_context_is_dropped_with_a_diagnostic():
    header = row_unit("u-h", [(0, "项目"), (1, "2025年")], row=0, table_id=TABLE, kind="table_header")
    body = row_unit("u-r", [(0, "门店"), (1, "18")], row=1, table_id=TABLE)
    foreign = caption_unit("u-cap", "单位：（人民币万元）", parent=FOREIGN)
    hints = layout_hints(
        region_units=["u-h", "u-r"], header_units=["u-h"], data_rows=[["u-r"]],
        caption_units=["u-cap"],
    )
    result = build_pdf_table_observations(observation([header, body, foreign]), hints, work_budget=budget())
    table, = result["tables"]
    assert "u-cap" not in table["units"]
    assert all(
        r["unit_id"] != "u-cap" for c in table["cells"] for r in c["header_refs"]
    )
    assert "FOREIGN_CONTEXT_REF_DROPPED" in _codes(result)


def test_fine_cell_slot_mismatch_is_rejected_not_reassigned():
    header = row_unit("u-h", [(0, "项目"), (1, "2025年")], row=0, table_id=TABLE, kind="table_header")
    body = row_unit(
        "u-r", [(0, "门店"), (1, "18")], row=1, table_id=TABLE,
        cell_entries=[
            fine_cell("门店", 0, 2, row=7, column=0, table_id=TABLE),   # 行号与 hints.row 不一致
            fine_cell("18", 5, 7, row=1, column=1, table_id="p9:t9"),  # 属于别的表
        ],
    )
    hints = layout_hints(region_units=["u-h", "u-r"], header_units=["u-h"], data_rows=[["u-r"]])
    result = build_pdf_table_observations(observation([header, body]), hints, work_budget=budget())
    table, = result["tables"]
    assert not any(c["row"] == 7 for c in table["cells"])
    assert not any(c["column"] == 1 and c["row"] == 1 for c in table["cells"])
    assert "CELL_SLOT_MISMATCH" in _codes(result)
