"""DOCX merge, header and continuation structure (card §5.2-§5.4, §6 A)."""

from __future__ import annotations

import hashlib

from .ooxml_support import (
    cell,
    docx,
    page_break_run,
    paragraph,
    row,
    table,
)

from company_wiki.document_normalization.office_table_structure import (
    OfficeTableLimits,
    parse_office_tables,
)


def _parse(payload: bytes, **kwargs: object) -> dict[str, object]:
    return parse_office_tables(
        payload,
        source_sha256=hashlib.sha256(payload).hexdigest(),
        **kwargs,  # type: ignore[arg-type]
    )


def _tables(structure: dict[str, object]) -> list[dict[str, object]]:
    tables = structure["tables"]
    assert isinstance(tables, list)
    return tables  # type: ignore[return-value]


def _cells(table_structure: dict[str, object]) -> list[dict[str, object]]:
    cells = table_structure["cells"]
    assert isinstance(cells, list)
    return cells  # type: ignore[return-value]


def _cell_at(table_structure: dict[str, object], row_index: int, column: int):
    for entry in _cells(table_structure):
        if entry["row"] == row_index and entry["column"] == column:
            return entry
    raise AssertionError(
        f"no cell at r{row_index}c{column}; "
        f"have {[(c['row'], c['column']) for c in _cells(table_structure)]}"
    )


def _codes(structure: dict[str, object]) -> list[str]:
    diagnostics = structure["diagnostics"]
    assert isinstance(diagnostics, list)
    return [entry["code"] for entry in diagnostics]  # type: ignore[index]


def _table_codes(table_structure: dict[str, object]) -> list[str]:
    diagnostics = table_structure["diagnostics"]
    assert isinstance(diagnostics, list)
    return [entry["code"] for entry in diagnostics]  # type: ignore[index]


# --------------------------------------------------------------------- gridSpan


def test_docx_horizontal_span_is_one_cell_with_column_span():
    """A 2x2 table whose first row is one ``gridSpan=2`` cell is ONE cell, not two.

    Today's parser emits two units (one per ``w:tc`` repeated value); the
    structure must say: one cell, ``column_span=2``, and no cell at grid column 1.
    """
    payload = docx(
        table(
            row(cell(paragraph("合并表头"), grid_span=2)),
            row(cell(paragraph("左")), cell(paragraph("右"))),
        )
    )
    structure = _parse(payload)
    (table_structure,) = _tables(structure)

    assert table_structure["grid"] == {"rows": 2, "columns": 2}
    assert table_structure["column_widths"] == [2880, 2880]
    top_left = _cell_at(table_structure, 0, 0)
    assert top_left["column_span"] == 2
    assert top_left["merge"] == "none"
    assert [entry["column"] for entry in _cells(table_structure) if entry["row"] == 0] == [
        0
    ]
    assert structure["status"] == "ok"


def test_docx_absent_grid_span_confirms_one_not_null():
    payload = docx(table(row(cell(paragraph("A")), cell(paragraph("B")))))
    (table_structure,) = _tables(_parse(payload))
    both = _cells(table_structure)
    assert [entry["column_span"] for entry in both] == [1, 1]
    assert [entry["row_span"] for entry in both] == [1, 1]


def test_docx_tbl_grid_columns_missing_is_null_not_guessed():
    payload = docx(table(row(cell(paragraph("A")), cell(paragraph("B"))), widths=None))
    (table_structure,) = _tables(_parse(payload))
    assert table_structure["grid"] == {"rows": 1, "columns": None}
    assert table_structure["column_widths"] is None


# ---------------------------------------------------------------------- vMerge


def test_docx_vertical_merge_three_rows_start_and_two_continues():
    payload = docx(
        table(
            row(cell(paragraph("起始值"), vmerge="restart")),
            row(cell(vmerge="")),
            row(cell(vmerge="continue")),
        )
    )
    (table_structure,) = _tables(_parse(payload))
    entries = _cells(table_structure)
    assert len(entries) == 3
    assert [entry["merge"] for entry in entries] == [
        "vertical_start",
        "vertical_continue",
        "vertical_continue",
    ]
    assert entries[0]["text"] == "起始值"
    assert [entry["text"] for entry in entries[1:]] == ["", ""]
    assert [entry["row"] for entry in entries] == [0, 1, 2]
    # A continuation "still occupies one grid row position" (card §5.3 rule 2), and
    # the grid keeps one row per row: the merge is expressed by `merge`, not by an
    # inflated row_span.
    assert [entry["row_span"] for entry in entries] == [1, 1, 1]
    # A well-formed merge records no merge diagnostic; the only diagnostic is the
    # honest "no pagination hint" note (card §5.4).
    assert "p2_merge_unresolved" not in _table_codes(table_structure)
    assert _table_codes(table_structure) == ["p2_continuation_unknown"]


def test_docx_vertical_continue_without_start_is_unresolved_without_fabrication():
    payload = docx(
        table(
            row(cell(vmerge="continue")),
            row(cell(paragraph("后来"))),
        )
    )
    structure = _parse(payload)
    (table_structure,) = _tables(structure)
    entries = _cells(table_structure)
    assert entries[0]["merge"] == "vertical_continue"
    assert len(entries) == 2
    assert "p2_merge_unresolved" in _table_codes(table_structure)
    assert "p2_merge_unresolved" in _codes(structure)


# ------------------------------------------------------------- span out of grid


def test_docx_grid_span_past_declared_grid_is_null_and_partial():
    payload = docx(
        table(
            row(cell(paragraph("超宽"), grid_span=5)),
            row(cell(paragraph("A")), cell(paragraph("B")), cell(paragraph("C"))),
            widths=(2880, 2880, 2880),
        )
    )
    structure = _parse(payload)
    (table_structure,) = _tables(structure)
    wide = _cell_at(table_structure, 0, 0)
    assert wide["column_span"] is None
    assert "p2_span_out_of_grid" in _table_codes(table_structure)
    assert structure["status"] == "partial"


# --------------------------------------------------------------------- tblHeader


def test_docx_tbl_header_row_is_recorded_from_markup_only():
    payload = docx(
        table(
            row(cell(paragraph("项目")), cell(paragraph("金额")), header=True),
            row(cell(paragraph("收入")), cell(paragraph("100"))),
        )
    )
    (table_structure,) = _tables(_parse(payload))
    assert table_structure["header"] == {"rows": [0], "source": "tblHeader"}


def test_docx_bold_centered_first_row_is_not_guessed_as_header():
    """No ``w:tblHeader`` means ``none`` — bold/centered text must not be used."""
    bold_center = '<w:rPr><w:b/></w:rPr><w:jc w:val="center"/>'
    payload = docx(
        table(
            row(
                "<w:tc><w:tcPr/>"
                + f"<w:p><w:pPr>{bold_center}</w:pPr>"
                + '<w:r><w:rPr><w:b/></w:rPr><w:t>项目</w:t></w:r></w:p>'
                + "</w:tc>",
                "<w:tc><w:tcPr/>"
                + f"<w:p><w:pPr>{bold_center}</w:pPr>"
                + '<w:r><w:rPr><w:b/></w:rPr><w:t>金额</w:t></w:r></w:p>'
                + "</w:tc>",
            ),
            row(cell(paragraph("收入")), cell(paragraph("100"))),
        )
    )
    (table_structure,) = _tables(_parse(payload))
    assert table_structure["header"] == {"rows": [], "source": "none"}


# ------------------------------------------------------------------ continuation


def _continuation_tables() -> bytes:
    header_row = row(cell(paragraph("项目")), cell(paragraph("金额")), header=True)
    return docx(
        table(
            header_row,
            row(cell(paragraph("收入")), cell(paragraph("100"))),
            row(
                "<w:tc><w:tcPr/>" + "<w:p>" + page_break_run() + "</w:p>" + "</w:tc>",
                cell(paragraph("200")),
            ),
        )
        + para_between()
        + table(
            header_row,
            row(cell(paragraph("成本")), cell(paragraph("80"))),
        )
    )


def para_between() -> str:
    return paragraph("表格之间的正文")


def test_docx_page_break_with_repeated_header_marks_continuation():
    payload = _continuation_tables()
    structure = _parse(payload)
    first, second = _tables(structure)

    continuation = first["continuation"]
    assert continuation["page_break_hints"] == ["r2c0"]
    assert continuation["repeated_header"] is True
    assert continuation["status"] == "ok"

    second_continuation = second["continuation"]
    assert second_continuation["continuation_of"] == "tbl-0"
    assert second["header"] == {"rows": [0], "source": "tblHeader"}


def test_docx_page_break_without_repeated_header_stays_unknown():
    payload = docx(
        table(
            row(cell(paragraph("A"))),
            row("<w:tc><w:tcPr/>" + "<w:p>" + page_break_run() + "</w:p></w:tc>"),
        )
    )
    (table_structure,) = _tables(_parse(payload))
    continuation = table_structure["continuation"]
    assert continuation["page_break_hints"] == ["r1c0"]
    assert continuation["repeated_header"] is False
    assert continuation["continuation_of"] is None
    assert continuation["status"] == "unknown"


def test_docx_absent_page_break_is_unknown_and_sectpr_is_not_evidence():
    payload = docx(
        table(
            row(cell(paragraph("A"))),
            row(cell(paragraph("B"))),
        )
    )
    (table_structure,) = _tables(_parse(payload))
    continuation = table_structure["continuation"]
    assert continuation["page_break_hints"] == []
    assert continuation["repeated_header"] is False
    assert continuation["continuation_of"] is None
    assert continuation["status"] == "unknown"


# --------------------------------------------------------------------- limit guard


def test_docx_limits_are_per_call_and_never_truncate_half_a_table():
    payload = docx(
        table(row(cell(paragraph("A")), cell(paragraph("B"))))
        + table(row(cell(paragraph("C")), cell(paragraph("D"))))
    )
    structure = _parse(payload, limits=OfficeTableLimits(max_tables=1))
    assert len(_tables(structure)) == 1
    assert structure["status"] == "partial"
    assert "p2_table_limit" in _codes(structure)
    assert structure["work_used"] == {"tables": 1, "cells": 2, "chars": 2}


def test_docx_cell_limit_keeps_whole_tables_only():
    payload = docx(
        table(row(cell(paragraph("A")), cell(paragraph("B"))))
        + table(row(cell(paragraph("C")), cell(paragraph("D"))))
    )
    structure = _parse(payload, limits=OfficeTableLimits(max_cells=3))
    kept = _tables(structure)
    assert len(kept) == 1
    assert [len(_cells(entry)) for entry in kept] == [2]
    assert structure["status"] == "partial"


def test_docx_text_limit_marks_partial():
    payload = docx(table(row(cell(paragraph("很长的单元格文本")), cell(paragraph("B")))))
    structure = _parse(payload, limits=OfficeTableLimits(max_text_chars=4))
    assert structure["status"] == "partial"
    assert "p2_table_limit" in _codes(structure)


# ------------------------------------------------------------------------ schema


def test_docx_structure_shell_matches_frozen_schema():
    from company_wiki.document_normalization.office_table_structure import (
        P2_OFFICE_TABLE_SCHEMA,
        P2_OFFICE_TABLE_VERSION,
    )

    payload = docx(table(row(cell(paragraph("A")))))
    structure = _parse(payload)
    assert structure["schema_version"] == P2_OFFICE_TABLE_SCHEMA == "cwp-office-table/1"
    assert P2_OFFICE_TABLE_VERSION == "1.0.0"
    assert structure["format"] == "docx"
    assert structure["source_sha256"] == hashlib.sha256(payload).hexdigest()
    assert structure["parser"] == {
        "name": "cwp_office_table_structure",
        "version": P2_OFFICE_TABLE_VERSION,
    }
    (table_structure,) = _tables(structure)
    assert table_structure["table_id"] == "tbl-0"
    assert table_structure["package_part"] == "word/document.xml"
    assert table_structure["native_index"] == 0
    assert table_structure["footnotes"] == []
    assert set(table_structure) == {
        "table_id",
        "package_part",
        "native_index",
        "grid",
        "column_widths",
        "header",
        "cells",
        "footnotes",
        "continuation",
        "diagnostics",
    }
    cell_shell = _cells(table_structure)[0]
    assert set(cell_shell) == {
        "cell_id",
        "row",
        "column",
        "row_span",
        "column_span",
        "merge",
        "locator",
        "text_refs",
        "footnote_refs",
        "text",
    }
    assert cell_shell["cell_id"] == "r0c0"
    assert cell_shell["locator"] == "cwp-docx-body/1|t=0|r=0|c=0|p=0"
    assert cell_shell["text_refs"] == []
