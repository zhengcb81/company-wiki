"""Card B capstone: one real parse → adapter → layout hints → this component →
the original binder, with every ref re-sliced back to the original text."""

from __future__ import annotations

import hashlib

import pytest

from company_wiki.document_understanding.table_measurements import bind_operating_table

from .builders import real_pdf_bytes
from .pipeline import PARSE_COUNT, parse_and_observe


def _grid():
    return {
        "grid": [
            ["Stores by operating model", "FY2026", "FY2027"],
            ["Directly operated stores", "16", "16"],
            ["Distributor stores", "-1,200", "N/A"],
        ],
        "caption": "Unit: (RMB in millions)",
    }


def test_real_parse_produces_observations_that_bind_and_slice_back():
    pytest.importorskip("fitz")
    from company_wiki.document_normalization.pdf_table_observations import (
        build_pdf_table_observations,
    )

    raw = real_pdf_bytes(pages=[_grid()])
    before = PARSE_COUNT["n"]
    parsed, observation, hints, budget = parse_and_observe(raw, language="en", table_pages=(1,))
    assert PARSE_COUNT["n"] == before + 1  # 原 parser 只 parse 一次

    result = build_pdf_table_observations(observation, hints, work_budget=budget)
    assert result["tables"]
    table = result["tables"][0]
    assert table["header_rows"] == [0]
    parsed_text = {u.unit_id: u.raw_text for u in parsed.units}

    # 每个 ref 逐一回切原文：完全相等，且 hash 记录
    seen = []
    for cell in table["cells"]:
        for ref in cell["text_refs"] + cell["header_refs"]:
            unit = table["units"][ref["unit_id"]]
            slice_text = unit["text"][ref["char_start"]:ref["char_end"]]
            assert parsed_text[ref["unit_id"]][ref["char_start"]:ref["char_end"]] == slice_text
            seen.append((ref, slice_text, hashlib.sha256(slice_text.encode("utf-8")).hexdigest()))
    values = {text for _ref, text, _sha in seen if text in {"16", "-1,200", "N/A"}}
    assert values == {"16", "-1,200", "N/A"}


    bound = bind_operating_table(table, work_budget=budget)
    assert bound["measurements"]
    for m in bound["measurements"]:
        unit = table["units"][m["value_ref"]["unit_id"]]
        value_text = unit["text"][m["value_ref"]["char_start"]:m["value_ref"]["char_end"]]
        assert parsed_text[m["value_ref"]["unit_id"]][
            m["value_ref"]["char_start"]:m["value_ref"]["char_end"]
        ] == value_text
    value_list = sorted(
        table["units"][m["value_ref"]["unit_id"]]["text"][
            m["value_ref"]["char_start"]:m["value_ref"]["char_end"]
        ]
        for m in bound["measurements"]
    )
    assert value_list == ["-1,200", "16", "16", "N/A"]
    columns = {
        table["units"][m["value_ref"]["unit_id"]]["text"][
            m["value_ref"]["char_start"]:m["value_ref"]["char_end"]
        ]: m["column_id"]
        for m in bound["measurements"]
        if m["binding_status"] == "bound"
    }
    assert columns["-1,200"] == "col-1" and columns["N/A"] == "col-2"
    # 双期同数值：两个 16 分别落在两个期间列
    ones = [
        m for m in bound["measurements"]
        if table["units"][m["value_ref"]["unit_id"]]["text"][
            m["value_ref"]["char_start"]:m["value_ref"]["char_end"]
        ] == "16"
    ]
    assert sorted(m["column_id"] for m in ones) == ["col-1", "col-2"]
