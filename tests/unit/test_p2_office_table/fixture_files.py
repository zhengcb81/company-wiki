"""Named synthetic fixture packages stored under ``fixtures/``.

Each package is generated from the literals in :mod:`.ooxml_support`; the
committed bytes and the ``sha256.json`` manifest exist so reviewers can diff and
hash what the tests actually parse (card §6).

Regenerate the committed fixtures with
``python -m tests.unit.test_p2_office_table.fixture_files``; the tests only
assert the committed bytes equal this generator and never rewrite them.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from .ooxml_support import (
    cell,
    docx,
    docx_footnotes,
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

MANIFEST_NAME = "sha256.json"
MANIFEST_SCHEMA = "cwp-office-table-fixtures/1"


def _docx_grid_span() -> bytes:
    return docx(
        table(
            row(cell(paragraph("合并表头"), grid_span=2)),
            row(cell(paragraph("左")), cell(paragraph("右"))),
        )
    )


def _docx_vertical_merge() -> bytes:
    return docx(
        table(
            row(cell(paragraph("起始值"), vmerge="restart")),
            row(cell(vmerge="")),
            row(cell(vmerge="continue")),
        )
    )


def _docx_span_out_of_grid() -> bytes:
    return docx(
        table(
            row(cell(paragraph("超宽"), grid_span=5)),
            row(cell(paragraph("A")), cell(paragraph("B")), cell(paragraph("C"))),
            widths=(2880, 2880, 2880),
        )
    )


def _docx_header_and_continuation() -> bytes:
    header_row = row(cell(paragraph("项目")), cell(paragraph("金额")), header=True)
    return docx(
        table(
            header_row,
            row(cell(paragraph("收入")), cell(paragraph("100"))),
            row(
                "<w:tc><w:tcPr/><w:p>" + page_break_run() + "</w:p></w:tc>",
                cell(paragraph("200")),
            ),
        )
        + paragraph("表格之间的正文")
        + table(
            header_row,
            row(cell(paragraph("成本")), cell(paragraph("80"))),
        )
    )


def _docx_footnotes() -> bytes:
    referencing = (
        "<w:tc><w:p>"
        + run("收入")
        + footnote_reference("3")
        + "</w:p></w:tc>"
    )
    return docx(
        table(row(cell(paragraph("项目")), referencing)),
        extra={"word/footnotes.xml": docx_footnotes({"3": "含少数股东权益"})},
    )


def _docx_footnotes_missing_part() -> bytes:
    referencing = (
        "<w:tc><w:p>"
        + run("收入")
        + footnote_reference("3")
        + "</w:p></w:tc>"
    )
    return docx(table(row(cell(paragraph("项目")), referencing)))


def _pptx_merged() -> bytes:
    return pptx(
        pptx_table(
            [2880, 2880],
            [
                [pptx_cell("客户", grid_span=2), pptx_cell("", hmerge=True)],
                [pptx_cell("", vmerge=True), pptx_cell("乙")],
            ],
        )
    )


def _pptx_plain() -> bytes:
    return pptx(pptx_table([2880, 2880], [[pptx_cell("A"), pptx_cell("B")]]))


_BUILDERS: Mapping[str, tuple[str, object]] = {
    "docx_grid_span.docx": ("docx", _docx_grid_span),
    "docx_vertical_merge.docx": ("docx", _docx_vertical_merge),
    "docx_span_out_of_grid.docx": ("docx", _docx_span_out_of_grid),
    "docx_header_and_continuation.docx": ("docx", _docx_header_and_continuation),
    "docx_footnotes.docx": ("docx", _docx_footnotes),
    "docx_footnotes_missing_part.docx": ("docx", _docx_footnotes_missing_part),
    "pptx_merged.pptx": ("pptx", _pptx_merged),
    "pptx_plain.pptx": ("pptx", _pptx_plain),
}


def build_all() -> dict[str, bytes]:
    return {name: builder() for name, (_kind, builder) in _BUILDERS.items()}  # type: ignore[operator]


def manifest_payload(packages: Mapping[str, bytes]) -> dict[str, object]:
    return {
        "schema": MANIFEST_SCHEMA,
        "fixtures": [
            {
                "file": name,
                "kind": _BUILDERS[name][0],
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
            for name, payload in sorted(packages.items())
        ],
    }


def sync_fixtures(directory: Path) -> None:
    """Write the packages and manifest so the committed bytes match generation."""
    directory.mkdir(parents=True, exist_ok=True)
    packages = build_all()
    for name, payload in packages.items():
        target = directory / name
        if not target.exists() or target.read_bytes() != payload:
            target.write_bytes(payload)
    manifest = directory / MANIFEST_NAME
    rendered = (
        json.dumps(
            manifest_payload(packages), ensure_ascii=True, sort_keys=True, indent=2
        )
        + "\n"
    )
    if not manifest.exists() or manifest.read_text(encoding="utf-8") != rendered:
        manifest.write_text(rendered, encoding="utf-8")


__all__ = ["MANIFEST_NAME", "build_all", "manifest_payload", "sync_fixtures"]


if __name__ == "__main__":  # pragma: no cover - manual regeneration entry
    sync_fixtures(Path(__file__).resolve().parent / "fixtures")
