"""PPTX table merge and continuation structure (card §5.2-§5.4, §6 A)."""

from __future__ import annotations

import hashlib

from .ooxml_support import pptx, pptx_cell, pptx_table

from company_wiki.document_normalization.office_table_structure import (
    parse_office_tables,
)


def _parse(payload: bytes) -> dict[str, object]:
    return parse_office_tables(
        payload, source_sha256=hashlib.sha256(payload).hexdigest()
    )


def _only_table(structure: dict[str, object]) -> dict[str, object]:
    tables = structure["tables"]
    assert isinstance(tables, list) and len(tables) == 1
    return tables[0]  # type: ignore[return-value]


def _cells(table_structure: dict[str, object]) -> list[dict[str, object]]:
    cells = table_structure["cells"]
    assert isinstance(cells, list)
    return cells  # type: ignore[return-value]


def _cell_at(table_structure: dict[str, object], row_index: int, column: int):
    for entry in _cells(table_structure):
        if entry["row"] == row_index and entry["column"] == column:
            return entry
    raise AssertionError(f"no cell at r{row_index}c{column}")


def _codes(table_structure: dict[str, object]) -> list[str]:
    diagnostics = table_structure["diagnostics"]
    assert isinstance(diagnostics, list)
    return [entry["code"] for entry in diagnostics]  # type: ignore[index]


def test_pptx_horizontal_merge_marks_continuation():
    payload = pptx(
        pptx_table(
            [2880, 2880],
            [
                [pptx_cell("客户", grid_span=2), pptx_cell("", hmerge=True)],
                [pptx_cell("甲"), pptx_cell("乙")],
            ],
        )
    )
    structure = _parse(payload)
    table_structure = _only_table(structure)
    assert structure["format"] == "pptx"
    assert table_structure["package_part"] == "ppt/slides/slide1.xml"
    origin = _cell_at(table_structure, 0, 0)
    assert origin["column_span"] == 2
    continued = _cell_at(table_structure, 0, 1)
    assert continued["merge"] == "horizontal"
    assert structure["status"] == "ok"


def test_pptx_vertical_merge_marks_continuation():
    payload = pptx(
        pptx_table(
            [2880, 2880],
            [
                [pptx_cell("起始"), pptx_cell("右")],
                [pptx_cell("", vmerge=True), pptx_cell("右2")],
            ],
        )
    )
    structure = _parse(payload)
    table_structure = _only_table(structure)
    assert _cell_at(table_structure, 0, 0)["merge"] == "vertical_start"
    continuation = _cell_at(table_structure, 1, 0)
    assert continuation["merge"] == "vertical_continue"
    assert continuation["row"] == 1
    assert continuation["column"] == 0


def test_pptx_conflicting_merge_signals_are_unresolved_with_null_spans():
    payload = pptx(
        pptx_table(
            [2880, 2880],
            [
                [pptx_cell("甲", grid_span=2, hmerge=True), pptx_cell("乙")],
            ],
        )
    )
    structure = _parse(payload)
    table_structure = _only_table(structure)
    conflicted = _cell_at(table_structure, 0, 0)
    assert conflicted["merge"] == "none"
    assert conflicted["column_span"] is None
    assert conflicted["row_span"] is None
    assert "p2_merge_unresolved" in _codes(table_structure)


def test_pptx_continuation_is_not_applicable_and_header_is_none():
    payload = pptx(
        pptx_table([2880, 2880], [[pptx_cell("A"), pptx_cell("B")]])
    )
    structure = _parse(payload)
    table_structure = _only_table(structure)
    continuation = table_structure["continuation"]
    assert continuation["status"] == "not_applicable"
    assert continuation["page_break_hints"] == []
    assert continuation["repeated_header"] is False
    assert continuation["continuation_of"] is None
    assert table_structure["header"] == {"rows": [], "source": "none"}
    assert table_structure["footnotes"] == []


def test_pptx_grid_widths_are_raw_emu():
    payload = pptx(
        pptx_table([914400, 1828800], [[pptx_cell("A"), pptx_cell("B")]])
    )
    table_structure = _only_table(_parse(payload))
    assert table_structure["grid"] == {"rows": 1, "columns": 2}
    assert table_structure["column_widths"] == [914400, 1828800]


def test_pptx_cell_locator_matches_parser_shape():
    payload = pptx(pptx_table([2880, 2880], [[pptx_cell("A"), pptx_cell("B")]]))
    table_structure = _only_table(_parse(payload))
    locators = [entry["locator"] for entry in _cells(table_structure)]
    assert locators == [
        "cwp-pptx-shape/2|s=1|p=0|c=0,0",
        "cwp-pptx-shape/2|s=1|p=0|c=0,1",
    ]
