"""Card B-4: several units carrying one native cell keep only their real refs.

No joined pseudo-text is invented across units, and the ambiguity is left to the
original binder instead of being resolved inside the adapter."""

from __future__ import annotations

from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding.table_measurements import bind_operating_table
from company_wiki.document_normalization.pdf_table_observations import (
    build_pdf_table_observations,
)

from .builders import fine_cell, layout_hints, observation, row_unit, wire_unit

PARENT = "urn:company-wiki:source:sha256:aaaa"
TABLE = "p1:t0"


def budget(n: int = 100_000) -> WorkBudget:
    return WorkBudget(max_work_units=n)


def _slice(table, ref):
    unit = table["units"][ref["unit_id"]]
    return unit["text"][ref["char_start"]:ref["char_end"]]


def test_multi_unit_cell_carries_every_real_ref_without_a_fabricated_join():
    header = row_unit(
        "u-h", [(0, "问题"), (1, "答复")], row=0, table_id=TABLE, kind="table_header"
    )
    # 一个原生格由两个 QA 碎片单元承接（真实 PDF 问答表形态）
    left = wire_unit(
        "u-a", "12", page=1, kind="paragraph", role="investor_question",
        table_id=TABLE, row=1, column=0,
        cells=[fine_cell("12", 0, 2, row=1, column=0, table_id=TABLE,
                         native_cell_char_start=0, native_cell_char_end=2, partial_cell=True)],
    )
    right_one = wire_unit(
        "u-b", "34", page=1, kind="paragraph", role="management",
        table_id=TABLE, row=1, column=1,
        cells=[fine_cell("34", 0, 2, row=1, column=1, table_id=TABLE,
                         native_cell_char_start=0, native_cell_char_end=2, partial_cell=True)],
    )
    right_two = wire_unit(
        "u-c", "56", page=1, kind="paragraph", role="management",
        table_id=TABLE, row=1, column=1,
        cells=[fine_cell("56", 0, 2, row=1, column=1, table_id=TABLE,
                         native_cell_char_start=2, native_cell_char_end=4, partial_cell=True)],
    )
    hints = layout_hints(
        region_units=["u-h", "u-a", "u-b", "u-c"],
        header_units=["u-h"],
        data_rows=[["u-a", "u-b", "u-c"]],
    )
    obs = observation([header, left, right_one, right_two])
    result = build_pdf_table_observations(obs, hints, work_budget=budget())
    table, = result["tables"]
    multi = next(c for c in table["cells"] if (c["row"], c["column"]) == (1, 1))
    assert multi["cell_id"] == "r1c1"
    assert {_slice(table, r) for r in multi["text_refs"]} == {"34", "56"}
    assert len(multi["text_refs"]) == 2
    # 不伪造连续原文：任何 ref 都不跨单元、不拼接
    for ref in multi["text_refs"]:
        assert ref["unit_id"] in {"u-b", "u-c"}
        assert _slice(table, ref) == table["units"][ref["unit_id"]]["text"]
    joined = [
        ref for ref in multi["text_refs"]
        if _slice(table, ref) in {"34 56", "3456", "34 | 56"}
    ]
    assert joined == []
    # 歧义交给原 binder：两个真实引用各自成值，组件不择一
    bound = bind_operating_table(table, work_budget=budget())
    values = sorted(
        table["units"][m["value_ref"]["unit_id"]]["text"][
            m["value_ref"]["char_start"]:m["value_ref"]["char_end"]
        ]
        for m in bound["measurements"]
    )
    assert values == ["12", "34", "56"]  # no invented leading-cell label
    assert all(m["binding_status"] == "unavailable" for m in bound["measurements"])
    assert result["status"] == "partial"
    assert all(v not in {"34 56", "3456"} for v in values)


def test_partial_cell_fragments_keep_their_parent_cell_provenance():
    header = row_unit(
        "u-h", [(0, "问题"), (1, "答复")], row=0, table_id=TABLE, kind="table_header"
    )
    fragment = wire_unit(
        "u-a", "仅片段", page=1, kind="paragraph", role="investor_question",
        table_id=TABLE, row=1, column=1,
        cells=[fine_cell("仅片段", 0, 3, row=1, column=1, table_id=TABLE,
                         native_cell_char_start=6, native_cell_char_end=9, partial_cell=True)],
    )
    hints = layout_hints(
        region_units=["u-h", "u-a"], header_units=["u-h"], data_rows=[["u-a"]]
    )
    result = build_pdf_table_observations(observation([header, fragment]), hints, work_budget=budget())
    table, = result["tables"]
    cell = next(c for c in table["cells"] if (c["row"], c["column"]) == (1, 1))
    assert [_slice(table, r) for r in cell["text_refs"]] == ["仅片段"]
    assert all(p["kind"] == "native_slot" for p in table["provenance"])
