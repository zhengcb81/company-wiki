"""Regression tests for defects found during independent review (2026-10-18).

Every case here reproduces a real divergence between the implementation as
delivered in ``f8c91996`` and the frozen card
(``docs/plans/parallel-packages-2026-10-18/P2-OFFICE-TABLE/card.md``) or the
INTERFACES error-code table.  The names state the card rule, not the old
behaviour, so a regression re-fails instead of silently passing.
"""

from __future__ import annotations

import copy
import hashlib

import pytest

from .ooxml_support import (
    cell,
    docx,
    footnote_reference,
    page_break_run,
    paragraph,
    pptx,
    pptx_cell,
    pptx_table,
    row,
    run,
    table,
)

from company_wiki.document_normalization.docx_parser import parse_docx
from company_wiki.document_normalization.limits import NormalizationLimits
from company_wiki.document_normalization.office_table_structure import (
    OfficeTableLimits,
    parse_office_tables,
    replay_office_tables,
)
from .ooxml_support import DOCX_MIME


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _parse(payload: bytes, **kwargs: object) -> dict[str, object]:
    return parse_office_tables(payload, source_sha256=_sha(payload), **kwargs)


def _tables(structure: dict[str, object]) -> list[dict[str, object]]:
    tables = structure["tables"]
    assert isinstance(tables, list)
    return tables  # type: ignore[return-value]


def _only_table(structure: dict[str, object]) -> dict[str, object]:
    tables = _tables(structure)
    assert len(tables) == 1
    return tables[0]


def _cells(table_structure: dict[str, object]) -> list[dict[str, object]]:
    cells = table_structure["cells"]
    assert isinstance(cells, list)
    return cells  # type: ignore[return-value]


def _codes(container: dict[str, object]) -> list[str]:
    diagnostics = container["diagnostics"]
    assert isinstance(diagnostics, list)
    return [entry["code"] for entry in diagnostics]  # type: ignore[index]


# --------------------------------------------------- footnote: null, not empty


def _footnote_part(inner: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main">'
        f"{inner}</w:footnotes>"
    ).encode("utf-8")


def test_footnote_id_present_without_text_is_null_not_empty_string():
    """Card §5.5: “id 存在但文本取不到 → text=null”. ``""`` is a claimed value."""
    payload = docx(
        table(row(cell("<w:p>" + run("收入") + footnote_reference("3") + "</w:p>"))),
        extra={
            "word/footnotes.xml": _footnote_part(
                '<w:footnote w:id="3">' + paragraph("") + "</w:footnote>"
            )
        },
    )
    structure = _parse(payload)
    table_structure = _only_table(structure)
    entry = _cells(table_structure)[0]
    assert entry["footnote_refs"] == [{"footnote_id": "3", "text": None}]
    assert table_structure["footnotes"] == []
    assert "p2_footnote_unresolved" in _codes(structure)


def test_footnote_separator_notes_are_not_treated_as_text():
    """``w:type="separator"``/``continuationSeparator`` carry layout, not text."""
    payload = docx(
        table(row(cell("<w:p>" + run("收入") + footnote_reference("3") + "</w:p>"))),
        extra={
            "word/footnotes.xml": _footnote_part(
                '<w:footnote w:type="separator" w:id="-1">'
                + paragraph("")
                + "</w:footnote>"
                '<w:footnote w:id="3">' + paragraph("正文脚注") + "</w:footnote>"
            )
        },
    )
    table_structure = _only_table(_parse(payload))
    assert table_structure["footnotes"] == [
        {"footnote_id": "3", "text": "正文脚注", "text_refs": []}
    ]
    assert _cells(table_structure)[0]["footnote_refs"] == [
        {"footnote_id": "3", "text": "正文脚注"}
    ]


# -------------------------------------------------- gridSpan: null, never one


def test_pptx_horizontal_continuation_past_grid_is_null_span_and_span_out_of_grid():
    """Card §5.3 rule 4 covers every span carrier, not only ``@gridSpan``.

    A run of ``hMerge="1"`` cells that overflows ``a:gridGrid`` is the same
    out-of-grid condition as an oversized ``@gridSpan``: report
    ``p2_span_out_of_grid`` and leave ``column_span`` unknown (``null``), never
    downgrade it to the confirmed ``1``.
    """
    payload = pptx(
        pptx_table(
            [2880, 2880],
            [
                [pptx_cell("甲"), pptx_cell("乙"), pptx_cell("", hmerge=True)],
            ],
        )
    )
    structure = _parse(payload)
    table_structure = _only_table(structure)
    overflow = _cells(table_structure)[-1]
    assert overflow["cell_id"] == "r0c2"
    assert overflow["column_span"] is None
    assert "p2_span_out_of_grid" in _codes(table_structure)
    assert structure["status"] == "partial"


def test_docx_grid_span_zero_honours_the_previous_merge_state():
    """``w:gridSpan w:val="0"`` is not one column; it must not close a vMerge."""
    payload = docx(
        table(
            row(cell(paragraph("起始"), vmerge="restart")),
            row(cell(vmerge="", grid_span=0)),
        )
    )
    table_structure = _only_table(_parse(payload))
    cells = _cells(table_structure)
    assert [entry["merge"] for entry in cells] == ["vertical_start", "vertical_continue"]
    # The invalid width is unknown, never silently 1 — but it no longer closes
    # the open vMerge chain above it either.
    assert [entry["column_span"] for entry in cells] == [1, None]
    assert "p2_span_out_of_grid" in _codes(table_structure)
    assert _parse(payload)["status"] == "partial"


# ------------------------------------------------- PPTX: continuation is hidden


def test_pptx_vertical_continuation_keeps_the_parser_text_of_its_cell():
    """DOCX hides a covered cell's text; PPTX deliberately does not.

    Verified against the existing parser: ``pptx_parser`` emits a unit with text
    for a ``@vMerge="1"`` cell (probe: ``cwp-pptx-shape/2|s=1|p=0|c=1,0`` ->
    ``幽灵文本``).  Blanking the text here would make the structure disagree
    with the parser the locators come from, so the covered position is expressed
    by ``merge`` alone.  This test pins that DOCX/PPTX asymmetry as a decision,
    not a leak.
    """
    payload = pptx(
        pptx_table(
            [2880, 2880],
            [
                [pptx_cell("起始"), pptx_cell("右")],
                [pptx_cell("幽灵文本", vmerge=True), pptx_cell("右2")],
            ],
        )
    )
    table_structure = _only_table(_parse(payload))
    continuation = next(
        entry for entry in _cells(table_structure) if entry["merge"] == "vertical_continue"
    )
    assert continuation["cell_id"] == "r1c0"
    assert continuation["text"] == "幽灵文本"

    from company_wiki.document_normalization.pptx_parser import parse_pptx

    from .ooxml_support import PPTX_MIME

    parsed = parse_pptx(
        payload,
        source_id="urn:company-wiki:source:sha256:" + _sha(payload),
        source_sha256=_sha(payload),
        mime_type=PPTX_MIME,
        limits=NormalizationLimits(),
    )
    by_locator = {unit.metadata["source_locator"]: unit.raw_text for unit in parsed.units}
    assert by_locator[continuation["locator"]] == continuation["text"]
    assert continuation["locator"] == "cwp-pptx-shape/2|s=1|p=0|c=1,0"

    from company_wiki.document_normalization.pptx_parser import parse_pptx

    from .ooxml_support import PPTX_MIME

    parsed = parse_pptx(
        payload,
        source_id="urn:company-wiki:source:sha256:" + _sha(payload),
        source_sha256=_sha(payload),
        mime_type=PPTX_MIME,
        limits=NormalizationLimits(),
    )
    assert continuation["locator"] in {
        unit.metadata["source_locator"] for unit in parsed.units
    }


# --------------------------------------------------- page-break hints are local


def test_page_break_inside_a_foreign_table_is_not_a_hint_of_this_table():
    """A hint names a cell of *this* table, by ``cell_id`` (card §5.4).

    The nested table is its own table (``tbl-1``); its page break must not be
    reported as a hint on the enclosing ``tbl-0``.
    """
    foreign = (
        "<w:tbl><w:tr><w:tc><w:p>"
        + page_break_run()
        + "</w:p></w:tc></w:tr></w:tbl>"
    )
    payload = docx(
        table(
            row(cell(paragraph("A"))),
            row("<w:tc><w:tcPr/>" + foreign + "</w:tc>"),
        )
    )
    outer, inner = _tables(_parse(payload))
    assert outer["table_id"] == "tbl-0"
    assert outer["continuation"]["page_break_hints"] == []
    assert inner["continuation"]["page_break_hints"] == ["r0c0"]


# ------------------------------------------------------- bounded work accounting


def test_work_used_counts_emitted_cells_and_cell_text():
    """``work_used`` is “实际处理量” (card §5.1), so it counts what was emitted."""
    payload = docx(
        table(row(cell(paragraph("合并表头"), grid_span=2)))
        + table(row(cell(paragraph("AAAA")), cell(paragraph("BB"))))
    )
    structure = _parse(payload)
    tables = _tables(structure)
    assert [len(_cells(entry)) for entry in tables] == [1, 2]
    assert structure["work_used"] == {"tables": 2, "cells": 3, "chars": 10}


def test_cell_budget_admits_tables_by_emitted_cells():
    """A span cell is one cell; the budget must not charge it twice."""
    payload = docx(
        table(row(cell(paragraph("合并表头"), grid_span=2)))
        + table(row(cell(paragraph("C")), cell(paragraph("D"))))
    )
    structure = _parse(payload, limits=OfficeTableLimits(max_cells=3))
    assert [len(_cells(entry)) for entry in _tables(structure)] == [1, 2]
    assert structure["status"] == "ok"


# ------------------------------------------------------- replay covers every field


def _header_payload() -> bytes:
    return docx(
        table(
            row(cell(paragraph("项目")), cell(paragraph("金额")), header=True),
            row(cell(paragraph("收入")), cell(paragraph("100"))),
        )
    )


@pytest.mark.parametrize(
    ("path", "field", "value"),
    [
        (("header",), "header", {"rows": [1], "source": "tblHeader"}),
        (("grid",), "grid", {"rows": 9, "columns": 9}),
        (("column_widths",), "column_widths", [1, 2]),
        (("package_part",), "package_part", "word/other.xml"),
        (("native_index",), "native_index", 7),
        (("footnotes",), "footnotes", [{"footnote_id": "9", "text": "x", "text_refs": []}]),
    ],
)
def test_replay_detects_a_changed_table_field(
    path: tuple[str, ...], field: str, value: object
) -> None:
    payload = _header_payload()
    structure = _parse(payload)
    tampered = copy.deepcopy(structure)
    table_structure = tampered["tables"][0]  # type: ignore[index]
    table_structure[path[0]] = value
    with pytest.raises(ValueError) as error:
        replay_office_tables(payload, tampered)
    message = str(error.value)
    assert message.startswith("replay mismatch: tbl-0 "), message
    assert field in message


def test_replay_detects_a_changed_continuation_status():
    payload = _header_payload()
    structure = _parse(payload)
    tampered = copy.deepcopy(structure)
    tampered["tables"][0]["continuation"]["status"] = "ok"  # type: ignore[index]
    with pytest.raises(ValueError, match="continuation"):
        replay_office_tables(payload, tampered)


def test_replay_detects_changed_cell_text_and_cell_id():
    payload = _header_payload()
    structure = _parse(payload)
    for field, value in (
        ("text", "伪造"),
        ("text_refs", [{"a": 1}]),
    ):
        tampered = copy.deepcopy(structure)
        tampered["tables"][0]["cells"][0][field] = value  # type: ignore[index]
        with pytest.raises(ValueError, match=field):
            replay_office_tables(payload, tampered)
    # `cell_id` is the locator of the cell in replay, so changing it is refused
    # through the positional checks rather than silently re-keyed.
    tampered = copy.deepcopy(structure)
    tampered["tables"][0]["cells"][0]["cell_id"] = "r9c9"  # type: ignore[index]
    with pytest.raises(ValueError, match="cell_id"):
        replay_office_tables(payload, tampered)


def test_replay_detects_a_changed_footnote_binding():
    payload = docx(
        table(row(cell("<w:p>" + run("收入") + footnote_reference("3") + "</w:p>"))),
        extra={
            "word/footnotes.xml": _footnote_part(
                '<w:footnote w:id="3">' + paragraph("含少数股东权益") + "</w:footnote>"
            )
        },
    )
    structure = _parse(payload)
    tampered = copy.deepcopy(structure)
    tampered["tables"][0]["cells"][0]["footnote_refs"] = []  # type: ignore[index]
    with pytest.raises(ValueError, match="footnote_refs"):
        replay_office_tables(payload, tampered)


def test_replay_round_trip_stays_byte_identical_after_the_stricter_check():
    payload = _header_payload()
    structure = _parse(payload)
    replayed = replay_office_tables(payload, structure)
    assert replayed == structure
    assert replayed["structure_sha256"] == structure["structure_sha256"]


# ------------------------------------------------------------- locator parity


def test_docx_locators_are_exactly_the_parse_docx_locator_set():
    """Not merely a subset: the two sets must be equal for the same cells."""
    payload = docx(
        table(
            row(cell(paragraph("项目")), cell(paragraph("金额"))),
            row(cell(paragraph("收入"), grid_span=2)),
            row("<w:tc><w:tcPr/><w:p/><w:p>" + run("后面") + "</w:p></w:tc>", cell()),
        )
        + table(row(cell(paragraph("X")), cell()))
    )
    parsed = parse_docx(
        payload,
        source_id="urn:company-wiki:source:sha256:" + _sha(payload),
        source_sha256=_sha(payload),
        mime_type=DOCX_MIME,
        limits=NormalizationLimits(),
    )
    existing = {
        unit.metadata["source_locator"]
        for unit in parsed.units
        if unit.coordinates.table_index is not None
    }
    emitted = {
        entry["locator"]
        for table_structure in _tables(_parse(payload))
        for entry in _cells(table_structure)
        if entry["locator"] is not None
    }
    assert emitted == existing
