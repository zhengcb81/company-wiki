"""Production-wiring contracts for page-aware source-catalog PDF normalization."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import pytest


def _catalog_module():
    return importlib.import_module("company_wiki.source_catalog")


def _normalizer_module():
    return importlib.import_module("company_wiki.source_catalog.normalizer")


def _catalog(module: Any, *, project: Path, source_root: Path):
    return module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("documents", source_root, "directory"),),
        )
    )


def _file_identity(path: Path) -> tuple[int, int, str]:
    stat = path.stat()
    return (
        stat.st_size,
        stat.st_mtime_ns,
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _evidence(catalog: Any) -> list[dict[str, Any]]:
    rows = catalog.store.fetchall(
        "SELECT span_json FROM evidence_spans ORDER BY locator"
    )
    return [json.loads(row["span_json"]) for row in rows]


def _draw_table_page(page: Any) -> None:
    page.insert_text((50, 25), "Narrative before table")
    page.insert_text((50, 190), "Narrative after table")
    for x in (50, 150, 250):
        page.draw_line((x, 50), (x, 150))
    for y in (50, 100, 150):
        page.draw_line((50, y), (250, y))
    for point, value in (
        ((65, 80), "A"),
        ((165, 80), "B"),
        ((65, 130), "1"),
        ((165, 130), "2"),
    ):
        page.insert_text(point, value)


def test_source_catalog_persists_paragraphs_empty_pages_and_stable_global_offsets(
    tmp_path,
):
    module = _catalog_module()
    fitz = pytest.importorskip("fitz")
    project = tmp_path / "project"
    source_root = tmp_path / "documents"
    source_root.mkdir()
    pdf_path = source_root / "multi_page.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "First paragraph.")
    page.insert_text((72, 150), "Second paragraph.")
    document.new_page()
    page = document.new_page()
    page.insert_text((72, 72), "Third page.")
    document.save(pdf_path)
    document.close()
    before = _file_identity(pdf_path)
    catalog = _catalog(module, project=project, source_root=source_root)

    catalog.scan()
    report = catalog.normalize()
    first = _evidence(catalog)
    first_ids = [item["span_id"] for item in first]
    catalog.normalize(force=True)
    second = _evidence(catalog)

    assert report.partial == 1
    assert _file_identity(pdf_path) == before
    assert [item["span_id"] for item in second] == first_ids
    assert second == first
    assert {item["parser_name"] for item in first} == {"pdf_page_aware_core"}
    paragraph_values = [
        item for item in first if item["coordinates"]["paragraph_index"] is not None
    ]
    assert [item["raw_text"] for item in paragraph_values] == [
        "First paragraph.",
        "Second paragraph.",
        "Third page.",
    ]
    assert [item["coordinates"]["page_number"] for item in paragraph_values] == [
        1,
        1,
        3,
    ]
    assert [item["coordinates"]["paragraph_index"] for item in paragraph_values] == [
        0,
        1,
        0,
    ]
    normalized_text = "First paragraph.\n\nSecond paragraph.\n\nThird page."
    for item in paragraph_values:
        coordinates = item["coordinates"]
        assert (
            normalized_text[coordinates["char_start"] : coordinates["char_end"]]
            == item["raw_text"]
        )
    empty_page = [
        item
        for item in first
        if item["coordinates"]["page_number"] == 2
        and item["coordinates"]["paragraph_index"] is None
        and item["coordinates"]["table_index"] is None
    ]
    assert len(empty_page) == 1
    assert empty_page[0]["parse_status"] == "failed"
    assert empty_page[0]["quality_flags"] == ["empty_output"]


def test_source_catalog_persists_table_cells_without_duplicate_narrative(tmp_path):
    module = _catalog_module()
    fitz = pytest.importorskip("fitz")
    project = tmp_path / "project"
    source_root = tmp_path / "documents"
    source_root.mkdir()
    pdf_path = source_root / "table.pdf"
    document = fitz.open()
    _draw_table_page(document.new_page(width=300, height=300))
    document.save(pdf_path)
    document.close()
    before = _file_identity(pdf_path)
    catalog = _catalog(module, project=project, source_root=source_root)

    catalog.scan()
    report = catalog.normalize()
    evidence = _evidence(catalog)

    assert report.completed == 1
    assert _file_identity(pdf_path) == before
    paragraphs = [
        item for item in evidence if item["coordinates"]["paragraph_index"] is not None
    ]
    cells = [
        item for item in evidence if item["coordinates"]["table_index"] is not None
    ]
    assert [item["raw_text"] for item in paragraphs] == [
        "Narrative before table",
        "Narrative after table",
    ]
    assert [item["raw_text"] for item in cells] == ["A", "B", "1", "2"]
    assert [
        (
            item["coordinates"]["table_index"],
            item["coordinates"]["row_index"],
            item["coordinates"]["column_index"],
        )
        for item in cells
    ] == [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1)]
    assert not any(
        value in (item["raw_text"] or "")
        for item in paragraphs
        for value in ("A\nB", "1\n2")
    )
    normalized_path = Path(catalog.query(limit=1)[0]["normalized_path"])
    normalized = normalized_path.read_text(encoding="utf-8")
    assert "loc:v1/page:1/paragraph:0" in normalized
    assert "loc:v1/page:1/table:0/row:0/column:0" in normalized


class _PageWithoutTableAPI:
    def get_text(self, mode: str, *, sort: bool):
        assert mode == "blocks"
        assert sort is True
        return [(10.0, 10.0, 100.0, 20.0, "Narrative\n", 0, 0)]


class _PageWithBrokenText:
    def find_tables(self):
        return type("Finder", (), {"tables": ()})()

    def get_text(self, mode: str, *, sort: bool):
        raise RuntimeError("synthetic page text failure")


def test_snapshot_builder_marks_missing_table_api_as_layout_ambiguous():
    normalizer = _normalizer_module()

    pages = normalizer._pymupdf_page_snapshots([_PageWithoutTableAPI()])

    assert pages == (
        {
            "page_number": 1,
            "text": "Narrative",
            "tables": (),
            "quality_score": 1.0,
            "ocr_used": False,
            "ocr_confidence": None,
            "layout_ambiguous": True,
            "encoding_repaired": False,
            "error": None,
        },
    )


def test_snapshot_builder_preserves_page_identity_on_text_extraction_error():
    normalizer = _normalizer_module()

    pages = normalizer._pymupdf_page_snapshots([_PageWithBrokenText()])

    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert pages[0]["text"] == ""
    assert pages[0]["tables"] == ()
    assert pages[0]["error"].startswith("RuntimeError:")


def test_corrupt_pdf_remains_fail_closed_and_source_immutable(tmp_path):
    module = _catalog_module()
    project = tmp_path / "project"
    source_root = tmp_path / "documents"
    source_root.mkdir()
    pdf_path = source_root / "corrupt.pdf"
    pdf_path.write_bytes(b"not a pdf")
    before = _file_identity(pdf_path)
    catalog = _catalog(module, project=project, source_root=source_root)

    catalog.scan()
    report = catalog.normalize()

    # Deterministic corruption maps to unsupported, never to a retryable
    # failed state (WR-10.13 unsupported/failed mutual exclusivity).
    assert report.unsupported == 1
    assert report.failed == 0
    assert _file_identity(pdf_path) == before
    assert _evidence(catalog) == []
    normalized_path = Path(catalog.query(limit=1)[0]["normalized_path"])
    normalized = normalized_path.read_text(encoding="utf-8")
    assert "normalization_status: unsupported" in normalized
    assert "loc:v1/page:" not in normalized


def test_snapshot_builder_normalizes_non_nfc_table_cells():
    """Non-NFC table cells (e.g. U+2126 OHM SIGN) must be NFC-normalized so
    pdf_page_aware's strict input validation does not reject a valid PDF.
    Regression for the two prospectus PDFs that failed with
    ``PageAwarePDFAdapterError: table cell must use Unicode NFC``.
    """
    import unicodedata

    normalizer = _normalizer_module()

    class _Table:
        bbox = (10.0, 10.0, 200.0, 100.0)
        row_count = 1
        col_count = 1

        def extract(self):
            return [("\u2126",)]  # OHM SIGN, non-NFC; NFC form is U+03A9

        def to_markdown(self):
            return "| \u2126 |"

    class _Finder:
        tables = (_Table(),)

    class _Page:
        def find_tables(self):
            return _Finder()

        def get_text(self, mode: str, *, sort: bool):
            assert mode == "blocks"
            assert sort is True
            return []

    pages = normalizer._pymupdf_page_snapshots([_Page()])
    assert len(pages) == 1
    tables = pages[0]["tables"]
    assert len(tables) == 1
    (cell,) = tables[0]["data"][0]
    assert cell == "\u03a9"
    assert unicodedata.normalize("NFC", cell) == cell
    # markdown normalized too
    assert tables[0]["markdown"] == "| \u03a9 |"
