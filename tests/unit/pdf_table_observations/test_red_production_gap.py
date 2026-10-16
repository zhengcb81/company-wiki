"""RED: the current PDF production observation gap and the row-0 header
assumption, shown through the existing public adapters — plus the desired
evidence-based replacement (non fixture-constant).

The first three tests are stable characterizations of today's code; the last
ones express the desired component behavior and are the behavioral RED before
implementation."""

from __future__ import annotations

import pytest

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.native_table_bridge import bind_native_tables

from .builders import real_pdf_bytes
from .pipeline import parse_and_observe


def _row_grid():
    # 一张正常表（表头行 + 数值行）
    return {"grid": [["Stores by operating model", "FY2026", "FY2027"],
                     ["Directly operated stores", "16", "21"],
                     ["Distributor stores", "38", "47"]]}


def _continuation_grid():
    # 续表：没有任何表头行，第 0 行就是数据行
    return {"grid": [["Directly operated stores", "16", "21"],
                     ["Distributor stores", "38", "47"],
                     ["Total", "54", "68"]]}


def test_pdf_wire_carries_no_native_table_hints_today():
    raw = real_pdf_bytes(pages=[_row_grid()])
    _parsed, observation, _hints, _budget = parse_and_observe(raw, table_pages=(1,))
    rows = [u for u in observation["units"] if u["hints"].get("table_id")]
    assert rows, "the parser must have produced table rows for the drawn grid"
    assert all("native_tables" not in u["hints"] for u in observation["units"])


def test_public_native_bridge_binds_observed_pdf_values_without_inventing_row_roles():
    raw = real_pdf_bytes(pages=[_row_grid()])
    _parsed, observation, hints, _budget = parse_and_observe(raw, table_pages=(1,))
    result = bind_native_tables(observation, layout_hints=hints, work_budget=WorkBudget(100_000))
    assert result['tables'], 'the production bridge must consume observed fine slots'
    units = {unit['unit_id']: unit['text'] for unit in observation['units']}
    values = set()
    for table in result['tables']:
        for measurement in table['measurements']:
            ref = measurement['value_ref']
            text = units[ref['unit_id']]
            assert 0 <= ref['char_start'] < ref['char_end'] <= len(text)
            values.add(text[ref['char_start']:ref['char_end']])
            # Native PDF slots prove position, not an HTML row-header role.
            assert measurement['row_label_refs'] == []
    assert {'16', '21', '38', '47'} <= values


def test_continuation_data_row_is_declared_table_header_today():
    raw = real_pdf_bytes(pages=[_continuation_grid()])
    _parsed, observation, _hints, _budget = parse_and_observe(raw, table_pages=(1,))
    rows = [u for u in observation["units"] if u["hints"].get("table_id")]
    first = min(rows, key=lambda u: u["hints"]["row"])
    # WRONG HEADER ASSUMPTION: the wire calls row 0 of every extracted table a
    # header even when it is a continuation data row.
    assert first["kind"] == "table_header"


def test_component_fills_the_gap_on_the_real_parser_wire():
    pytest.importorskip("fitz")
    from company_wiki.document_normalization.pdf_table_observations import (
        build_pdf_table_observations,
    )

    raw = real_pdf_bytes(pages=[_row_grid()])
    _parsed, observation, hints, budget = parse_and_observe(raw, table_pages=(1,))
    result = build_pdf_table_observations(observation, hints, work_budget=budget)
    assert result["tables"], "PDF fine cells must become production table observations"
    table = result["tables"][0]
    assert table["schema_version"] == "du4-table-observation/1"
    assert table["cells"]
    for cell in table["cells"]:
        for ref in cell["text_refs"] + cell["header_refs"]:
            text = table["units"][ref["unit_id"]]["text"]
            assert 0 <= ref["char_start"] < ref["char_end"] <= len(text)
    values = {
        table["units"][r["unit_id"]]["text"][r["char_start"]:r["char_end"]]
        for c in table["cells"]
        for r in c["text_refs"]
    }
    assert {"16", "21", "38", "47"} <= values
    # 非 fixture 常量方案：表头行来自证据，不是固定 [0,1,2,3]
    assert table["header_rows"] == [0]


def test_component_does_not_promote_a_contradicted_row_zero_header():
    pytest.importorskip("fitz")
    from company_wiki.document_normalization.pdf_table_observations import (
        build_pdf_table_observations,
    )

    raw = real_pdf_bytes(pages=[_continuation_grid()])
    _parsed, observation, hints, budget = parse_and_observe(raw, table_pages=(1,))
    # 前置事实（真实共享引擎输出）：这些行是数量数据行，且没有 header_for 关系
    row_ids = {u["unit_id"] for u in observation["units"] if u["hints"].get("table_id")}
    data_groups = [
        g for g in hints["groups"]
        if g["kind"] == "table_row" and set(g["member_unit_ids"]) & row_ids
    ]
    header_relations = [r for r in hints["relations"] if r["kind"] == "header_for"]
    assert data_groups and not header_relations
    result = build_pdf_table_observations(observation, hints, work_budget=budget)
    table = result["tables"][0]
    assert table["header_rows"] == []  # 续表无表头证据 → unknown，不猜第 0 行
