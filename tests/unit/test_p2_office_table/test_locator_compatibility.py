"""Locator compatibility with the existing parsers (card §5.3, §6 A)."""

from __future__ import annotations

import hashlib

from .ooxml_support import (
    DOCX_MIME,
    cell,
    docx,
    page_break_run,
    paragraph,
    pptx,
    pptx_cell,
    pptx_table,
    row,
    table,
)

from company_wiki.document_normalization.docx_parser import parse_docx
from company_wiki.document_normalization.limits import NormalizationLimits
from company_wiki.document_normalization.office_table_structure import (
    parse_office_tables,
)


def _structure(payload: bytes) -> dict[str, object]:
    return parse_office_tables(
        payload, source_sha256=hashlib.sha256(payload).hexdigest()
    )


def _parsed_docx_locators(payload: bytes) -> list[str]:
    sha = hashlib.sha256(payload).hexdigest()
    parsed = parse_docx(
        payload,
        source_id="urn:company-wiki:source:sha256:" + sha,
        source_sha256=sha,
        mime_type=DOCX_MIME,
        limits=NormalizationLimits(),
    )
    return [
        unit.metadata["source_locator"]
        for unit in parsed.units
        if unit.coordinates.table_index is not None
    ]


def test_docx_cell_locators_match_parse_docx_byte_for_byte():
    """The structure must reuse the exact locator ``parse_docx`` already emits."""
    payload = docx(
        table(
            row(cell(paragraph("项目")), cell(paragraph("金额"))),
            row(cell(paragraph("收入")), cell(paragraph("100"))),
        )
        + table(
            row(cell(paragraph("合并"), grid_span=2)),
            row(cell(paragraph("左")), cell(paragraph("右"))),
        )
    )

    existing = _parsed_docx_locators(payload)
    assert existing, "the DOCX fixture must produce table units"

    structure = _structure(payload)
    tables = structure["tables"]
    assert isinstance(tables, list)
    emitted = [
        entry["locator"]
        for table_structure in tables
        for entry in table_structure["cells"]  # type: ignore[index]
        if entry["locator"] is not None
    ]
    assert set(emitted) <= set(existing), (
        "structure emitted a locator the existing parser never produces: "
        f"{sorted(set(emitted) - set(existing))}"
    )
    # Every plain (unmerged) cell locator must be byte-identical.
    assert "cwp-docx-body/1|t=0|r=0|c=0|p=0" in emitted
    assert "cwp-docx-body/1|t=1|r=1|c=1|p=0" in emitted


def test_docx_cell_without_paragraph_has_null_locator():
    payload = docx(table(row(cell(paragraph("有段落")), cell())))
    tables = _structure(payload)["tables"]
    assert isinstance(tables, list)
    entries = tables[0]["cells"]  # type: ignore[index]
    assert entries[0]["locator"] == "cwp-docx-body/1|t=0|r=0|c=0|p=0"
    assert entries[1]["locator"] is None
    assert entries[1]["text"] == ""


def test_docx_locator_uses_first_visible_paragraph_index():
    """An empty first paragraph shifts the emitted locator's ``p`` index."""
    payload = docx(
        table(row("<w:tc><w:tcPr/><w:p/><w:p>" + "<w:r><w:t>后面</w:t></w:r>"
                    + "</w:p></w:tc>"))
    )
    tables = _structure(payload)["tables"]
    assert isinstance(tables, list)
    entry = tables[0]["cells"][0]  # type: ignore[index]
    assert entry["text"] == "后面"
    assert entry["locator"] == "cwp-docx-body/1|t=0|r=0|c=0|p=1"


def test_docx_page_break_only_cell_keeps_null_locator_and_hint():
    payload = docx(
        table(
            row(cell(paragraph("A"))),
            row("<w:tc><w:tcPr/><w:p>" + page_break_run() + "</w:p></w:tc>"),
        )
    )
    tables = _structure(payload)["tables"]
    assert isinstance(tables, list)
    entry = tables[0]["cells"][1]  # type: ignore[index]
    assert entry["locator"] is None
    assert tables[0]["continuation"]["page_break_hints"] == ["r1c0"]


def test_pptx_cell_locators_match_parse_pptx_byte_for_byte():
    from .ooxml_support import PPTX_MIME
    from company_wiki.document_normalization.pptx_parser import parse_pptx

    payload = pptx(
        pptx_table([2880, 2880], [[pptx_cell("A"), pptx_cell("B")]])
    )
    sha = hashlib.sha256(payload).hexdigest()
    parsed = parse_pptx(
        payload,
        source_id="urn:company-wiki:source:sha256:" + sha,
        source_sha256=sha,
        mime_type=PPTX_MIME,
        limits=NormalizationLimits(),
    )
    existing = {
        unit.metadata["source_locator"]
        for unit in parsed.units
        if unit.coordinates.table_index is not None
    }
    assert existing, "the PPTX fixture must produce table units"

    tables = _structure(payload)["tables"]
    assert isinstance(tables, list)
    emitted = {
        entry["locator"]
        for entry in tables[0]["cells"]  # type: ignore[index]
        if entry["locator"] is not None
    }
    assert emitted == existing


def test_docx_table_numbering_follows_the_parser_with_nested_tables():
    """Tables the parser never numbers must not consume a ``t=`` index.

    ``docx_parser.table()`` recurses only into a ``w:tbl`` that is a *direct*
    child of a cell; a nested table wrapped in ``w:sdt`` inside a cell is
    reported as an unsupported element and never entered, yet ``body.iter``
    yields it — so a real research note whose cells carry such tables shifted
    every later ``t=`` index by three and broke locator parity on 24.8% of the
    structure's cells.  This fixture reproduces that divergence: the direct
    child must be numbered, the ``w:sdt``-wrapped one must not, and the table
    after the outer one must keep the index the parser gives it.
    """
    nested_visible = table(row(cell(paragraph("可见嵌套"))))
    nested_hidden = table(row(cell(paragraph("不可见嵌套"))))
    sdt_wrapped = (
        "<w:sdt><w:sdtPr/><w:sdtContent>" + nested_hidden + "</w:sdtContent></w:sdt>"
    )
    payload = docx(
        table(
            row(cell(paragraph("外层A")), cell(paragraph("外层B"))),
            row(
                "<w:tc><w:tcPr/>"
                + paragraph("承上")
                + nested_visible
                + sdt_wrapped
                + "</w:tc>"
            ),
        )
        + table(row(cell(paragraph("后一个表"))))
    )

    existing = set(_parsed_docx_locators(payload))
    assert existing, "the fixture must produce table units"
    # The parser numbers the outer table, its direct nested child, then the
    # later sibling — and never the sdt-wrapped one.
    assert "cwp-docx-body/1|t=0|r=0|c=0|p=0" in existing
    assert "cwp-docx-body/1|t=1|r=0|c=0|p=0" in existing
    assert "cwp-docx-body/1|t=2|r=0|c=0|p=0" in existing

    tables = _structure(payload)["tables"]
    assert isinstance(tables, list)
    emitted = {
        entry["locator"]
        for table_structure in tables
        for entry in table_structure["cells"]  # type: ignore[index]
        if entry["locator"] is not None
    }
    assert emitted <= existing, (
        "nested-table numbering drifted from the parser: "
        f"{sorted(emitted - existing)}"
    )
    # Three numbered tables, exactly as the parser sees them.
    assert len(tables) == 3
    # The sdt-wrapped cell content never produced a locator the parser lacks.
    assert not any("不可见" in str(entry.get("text")) for entry in [
        c for t in tables for c in t["cells"]  # type: ignore[index]
    ])


def test_docx_deleted_region_tables_consume_the_parser_index():
    """A table inside ``w:del`` consumes a ``t=`` index without a structure.

    ``docx_parser.body()`` walks ``w:del`` / ``w:moveFrom`` with
    ``visible=False``: no unit is emitted, but ``body(visible=False)`` still
    does ``self.tables += sum(1 for _ in child.iter(W + "tbl"))`` on a
    ``w:tbl`` child — the very counter ``table()`` reads for ``t=``.  A
    deleted-region table therefore shifts every later ``t=`` (a nested table
    in its cells shifts it further, wrappers inside the region are descended,
    and a table inside a ``w:p`` inside the region is never reached because
    ``body()`` never descends a paragraph).  The structure must reproduce that
    shift: the deleted table is never emitted, but the tables after it keep
    the indices the parser gives them.
    """
    deleted_outer = table(row(cell(paragraph("被删的表"))))
    deleted_with_nested = table(
        row(
            "<w:tc><w:tcPr/><w:p/>"
            + table(row(cell(paragraph("删除区嵌套表"))))
            + "</w:tc>"
        )
    )

    def payload(del_region: str) -> bytes:
        return docx(
            table(row(cell(paragraph("首表"))))
            + del_region
            + table(row(cell(paragraph("末表"))))
        )

    # One deleted table: the parser numbers the last visible table t=2.
    one_deleted = payload(f"<w:del>{deleted_outer}</w:del>")
    existing = set(_parsed_docx_locators(one_deleted))
    assert "cwp-docx-body/1|t=0|r=0|c=0|p=0" in existing
    assert "cwp-docx-body/1|t=2|r=0|c=0|p=0" in existing
    assert not any(locator.startswith("cwp-docx-body/1|t=1|") for locator in existing)

    tables = _structure(one_deleted)["tables"]
    assert isinstance(tables, list)
    emitted = {
        entry["locator"]
        for table_structure in tables
        for entry in table_structure["cells"]  # type: ignore[index]
        if entry["locator"] is not None
    }
    assert emitted <= existing, (
        "deleted-region numbering drifted from the parser: "
        f"{sorted(emitted - existing)}"
    )
    # The deleted table itself never produced a structure.
    assert len(tables) == 2
    assert [t["native_index"] for t in tables] == [0, 2]  # type: ignore[index]

    # A deleted table with a nested cell table consumes TWO indices (t=3 next).
    two_deleted = payload(f"<w:del>{deleted_with_nested}</w:del>")
    existing_two = set(_parsed_docx_locators(two_deleted))
    assert "cwp-docx-body/1|t=3|r=0|c=0|p=0" in existing_two
    tables_two = _structure(two_deleted)["tables"]
    assert isinstance(tables_two, list)
    emitted_two = {
        entry["locator"]
        for table_structure in tables_two
        for entry in table_structure["cells"]  # type: ignore[index]
        if entry["locator"] is not None
    }
    assert emitted_two <= existing_two, (
        "deleted-region nested numbering drifted from the parser: "
        f"{sorted(emitted_two - existing_two)}"
    )
    assert [t["native_index"] for t in tables_two] == [0, 3]  # type: ignore[index]

    # w:moveFrom behaves exactly like w:del.
    moved_away = payload(f"<w:moveFrom>{deleted_outer}</w:moveFrom>")
    existing_moved = set(_parsed_docx_locators(moved_away))
    assert "cwp-docx-body/1|t=2|r=0|c=0|p=0" in existing_moved
    tables_moved = _structure(moved_away)["tables"]
    assert isinstance(tables_moved, list)
    emitted_moved = {
        entry["locator"]
        for table_structure in tables_moved
        for entry in table_structure["cells"]  # type: ignore[index]
        if entry["locator"] is not None
    }
    assert emitted_moved <= existing_moved
    assert [t["native_index"] for t in tables_moved] == [0, 2]  # type: ignore[index]

    # A table inside a w:p inside w:del is never reached by the parser's walk
    # (body() never descends a paragraph), so it consumes NO index.
    hidden_in_paragraph = payload(
        f"<w:del><w:p>{deleted_outer}</w:p></w:del>"
    )
    existing_hidden = set(_parsed_docx_locators(hidden_in_paragraph))
    assert "cwp-docx-body/1|t=1|r=0|c=0|p=0" in existing_hidden
    tables_hidden = _structure(hidden_in_paragraph)["tables"]
    assert isinstance(tables_hidden, list)
    assert [t["native_index"] for t in tables_hidden] == [0, 1]  # type: ignore[index]
