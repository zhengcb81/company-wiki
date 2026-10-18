"""DOCX footnote binding (card §5.5, §6 A)."""

from __future__ import annotations

import hashlib

from .ooxml_support import (
    cell,
    docx,
    docx_footnotes,
    footnote_reference,
    paragraph,
    row,
    run,
    table,
)

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


def _diagnostics(structure: dict[str, object]) -> list[dict[str, object]]:
    diagnostics = structure["diagnostics"]
    assert isinstance(diagnostics, list)
    return diagnostics  # type: ignore[return-value]


def _referencing_cell() -> str:
    body = "<w:p>" + run("收入") + footnote_reference("3") + "</w:p>"
    return f"<w:tc>{body}</w:tc>"


def test_docx_footnote_reference_binds_part_text():
    payload = docx(
        table(row(cell(paragraph("项目")), _referencing_cell())),
        extra={"word/footnotes.xml": docx_footnotes({"3": "含少数股东权益"})},
    )
    structure = _parse(payload)
    table_structure = _only_table(structure)
    entry = table_structure["cells"][1]  # type: ignore[index]
    assert entry["footnote_refs"] == [
        {"footnote_id": "3", "text": "含少数股东权益"}
    ]
    assert table_structure["footnotes"] == [
        {"footnote_id": "3", "text": "含少数股东权益", "text_refs": []}
    ]
    assert "p2_footnote_unresolved" not in [
        diagnostic["code"] for diagnostic in _diagnostics(structure)
    ]


def test_docx_missing_footnotes_part_is_unresolved_and_null():
    payload = docx(table(row(cell(paragraph("项目")), _referencing_cell())))
    structure = _parse(payload)
    table_structure = _only_table(structure)
    assert table_structure["footnotes"] == []
    entry = table_structure["cells"][1]  # type: ignore[index]
    assert entry["footnote_refs"] == [{"footnote_id": "3", "text": None}]
    unresolved = [
        diagnostic
        for diagnostic in _diagnostics(structure)
        if diagnostic["code"] == "p2_footnote_unresolved"
    ]
    assert unresolved, _diagnostics(structure)
    assert unresolved[0]["detail"] == "part_absent"
    assert structure["status"] == "ok"


def test_docx_footnote_id_absent_from_part_never_invents_text():
    payload = docx(
        table(row(_referencing_cell())),
        extra={"word/footnotes.xml": docx_footnotes({"1": "别的脚注"})},
    )
    structure = _parse(payload)
    table_structure = _only_table(structure)
    assert table_structure["footnotes"] == []
    entry = table_structure["cells"][0]  # type: ignore[index]
    assert entry["footnote_refs"] == [{"footnote_id": "3", "text": None}]
    assert "p2_footnote_unresolved" in [
        diagnostic["code"] for diagnostic in _diagnostics(structure)
    ]
