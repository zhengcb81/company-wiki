"""Consumer contract for the pure page-aware canonical PDF adapter."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib
import inspect
from pathlib import Path

import pytest


PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)
PAGE_FIELDS = {
    "page_number",
    "text",
    "tables",
    "quality_score",
    "ocr_used",
    "ocr_confidence",
    "layout_ambiguous",
    "encoding_repaired",
    "error",
}
TABLE_FIELDS = {"markdown", "rows", "cols", "data"}


def _adapter():
    return importlib.import_module("company_wiki.parser_adapters.pdf_page_aware")


def _contracts():
    return importlib.import_module("company_wiki.source_contract")


def _ingest():
    return importlib.import_module("company_wiki.canonical_ingest")


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    return root


def _manifest(root: Path, *, mime_type: str = "application/pdf"):
    contracts = _contracts()
    suffix = ".pdf" if mime_type == "application/pdf" else ".md"
    digest = hashlib.sha256(PDF_BYTES).hexdigest()
    raw_path = root / "companies" / "TestCo" / "raw" / f"{digest}{suffix}"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(PDF_BYTES)
    manifest = contracts.SourceManifest.from_file(
        root=root,
        file_path=raw_path,
        entity_ids=("TEST:000001",),
        source_type=contracts.SourceType.COMPANY_ANNOUNCEMENT,
        published_date="2026-03-25",
        retrieved_at="2026-07-19T12:00:00Z",
        collector_name="fixture_collector",
        collector_version="1.0.0",
        mime_type=mime_type,
    )
    return manifest, raw_path


def _page(page_number: int, **overrides):
    values = {
        "page_number": page_number,
        "text": f"Page {page_number} text",
        "tables": [],
        "quality_score": 0.95,
        "ocr_used": False,
        "ocr_confidence": None,
        "layout_ambiguous": False,
        "encoding_repaired": False,
        "error": None,
    }
    values.update(overrides)
    return values


def _table(data):
    rows = len(data)
    cols = len(data[0]) if data else 0
    return {
        "markdown": "| fixture | table |",
        "rows": rows,
        "cols": cols,
        "data": data,
    }


def _tree_snapshot(root: Path) -> tuple[tuple[str, str], ...]:
    values = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            values.append((relative + "/", "directory"))
        else:
            values.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(values)


def test_page_aware_adapter_has_a_narrow_source_only_public_api():
    module = _adapter()
    package = importlib.import_module("company_wiki.parser_adapters")

    assert package.adapt_pdf_pages is module.adapt_pdf_pages
    assert set(module.__all__) == {
        "PAGE_AWARE_PDF_PARSER_NAME",
        "PageAwarePDFAdapterError",
        "PageAwarePDFResult",
        "adapt_pdf_pages",
    }
    assert "source_id" not in inspect.signature(module.adapt_pdf_pages).parameters


def test_page_aware_adapter_does_not_import_runtime_io_or_writers():
    module = _adapter()
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert imports.isdisjoint(
        {
            "fitz",
            "scripts",
            "sqlite3",
            "subprocess",
            "requests",
            "urllib",
            "httpx",
            "openai",
            "threading",
        }
    )
    assert called_attributes.isdisjoint(
        {"open", "mkdir", "write_text", "write_bytes", "unlink", "replace"}
    )
    for forbidden in ("StockWiki", "KnowledgePatch", "ClaimType", "RunStore"):
        assert forbidden not in source


def test_paragraphs_keep_physical_pages_empty_pages_and_global_offsets(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    pages = (
        _page(1, text="Alpha\n\nBeta"),
        _page(2, text=""),
        _page(3, text="Gamma"),
    )

    result = module.adapt_pdf_pages(
        manifest=manifest,
        pages=pages,
        parser_version="1.0.0",
    )

    assert result.normalized_text == "Alpha\n\nBeta\n\nGamma"
    assert result.page_count == 3
    assert len(result.parser_results) == 4
    first, second, empty, fourth = result.parser_results
    assert first.coordinates == contracts.EvidenceCoordinates(
        page_number=1,
        paragraph_index=0,
        char_start=0,
        char_end=5,
    )
    assert second.coordinates == contracts.EvidenceCoordinates(
        page_number=1,
        paragraph_index=1,
        char_start=7,
        char_end=11,
    )
    assert empty.coordinates == contracts.EvidenceCoordinates(page_number=2)
    assert empty.raw_text is None
    assert empty.structured_value is None
    assert empty.parse_status is contracts.ParseStatus.FAILED
    assert empty.quality_flags == ("empty_output",)
    assert fourth.coordinates == contracts.EvidenceCoordinates(
        page_number=3,
        paragraph_index=0,
        char_start=13,
        char_end=18,
    )


def test_table_cells_have_page_table_row_column_and_raw_structured_values(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    pages = (
        _page(
            1,
            text="",
            tables=[_table([["Metric", "Value"], ["Revenue", 100]])],
        ),
    )

    result = module.adapt_pdf_pages(
        manifest=manifest,
        pages=pages,
        parser_version="1.0.0",
    )

    assert result.normalized_text == ""
    assert len(result.parser_results) == 4
    numeric = result.parser_results[-1]
    assert numeric.coordinates == contracts.EvidenceCoordinates(
        page_number=1,
        table_index=0,
        row_index=1,
        column_index=1,
    )
    assert numeric.raw_text == "100"
    assert dict(numeric.structured_value) == {
        "column_index": 1,
        "kind": "table_cell",
        "page_number": 1,
        "raw_value": 100,
        "row_index": 1,
        "table_index": 0,
        "value": "100",
    }
    assert numeric.parse_status is contracts.ParseStatus.PARSED
    assert all(item.quality_flags != ("empty_output",) for item in result.parser_results)


def test_empty_table_cells_remain_structured_output_not_empty_pages(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    result = module.adapt_pdf_pages(
        manifest=manifest,
        pages=(_page(1, text="", tables=[_table([[None, ""]])]),),
        parser_version="1.0.0",
    )

    assert len(result.parser_results) == 2
    missing, blank = result.parser_results
    assert missing.coordinates == contracts.EvidenceCoordinates(
        page_number=1,
        table_index=0,
        row_index=0,
        column_index=0,
    )
    assert missing.raw_text is None
    assert dict(missing.structured_value)["raw_value"] is None
    assert missing.parse_status is contracts.ParseStatus.PARSED
    assert blank.raw_text == ""
    assert dict(blank.structured_value)["value"] == ""
    assert blank.parse_status is contracts.ParseStatus.PARSED


def test_ocr_layout_encoding_and_quality_metadata_map_to_stable_flags(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    pages = (
        _page(1, ocr_used=True, ocr_confidence=0.95),
        _page(2, ocr_used=True, ocr_confidence=0.50),
        _page(
            3,
            quality_score=0.20,
            layout_ambiguous=True,
            encoding_repaired=True,
        ),
    )

    result = module.adapt_pdf_pages(
        manifest=manifest,
        pages=pages,
        parser_version="1.0.0",
    )
    first, second, third = result.parser_results

    assert first.parse_status is contracts.ParseStatus.PARSED
    assert first.quality_flags == ("ocr_used",)
    assert second.parse_status is contracts.ParseStatus.PARTIAL
    assert second.quality_flags == ("low_ocr_confidence", "ocr_used")
    assert third.parse_status is contracts.ParseStatus.PARTIAL
    assert third.quality_flags == (
        "encoding_repaired",
        "layout_ambiguous",
        "parser_warning",
    )


def test_page_error_preserves_page_identity_without_publishing_error_text(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    result = module.adapt_pdf_pages(
        manifest=manifest,
        pages=(_page(1, text="", error="fixture extraction failure"),),
        parser_version="1.0.0",
    )

    failed = result.parser_results[0]
    assert failed.coordinates == contracts.EvidenceCoordinates(page_number=1)
    assert failed.parse_status is contracts.ParseStatus.FAILED
    assert failed.quality_flags == ("parser_error",)
    assert failed.raw_text is None
    assert failed.structured_value is None
    assert "fixture extraction failure" not in failed.to_evidence_span().canonical_json()


@pytest.mark.parametrize(
    ("pages", "error_text"),
    (
        (({key: value for key, value in _page(1).items() if key != "text"},), "fields"),
        (({**_page(1), "unexpected": True},), "fields"),
        ((_page(2),), "page_number"),
        ((_page(1), _page(3)), "page_number"),
        ((_page(1, text="line one\r\nline two"),), "LF"),
        ((_page(1, text="e\u0301"),), "NFC"),
        ((_page(1, quality_score=1.1),), "quality_score"),
        ((_page(1, ocr_used=True, ocr_confidence=None),), "ocr_confidence"),
        ((_page(1, ocr_used=False, ocr_confidence=0.5),), "ocr_confidence"),
        (
            (_page(1, tables=[{key: value for key, value in _table([[1]]).items() if key != "data"}]),),
            "table fields",
        ),
        ((_page(1, tables=[_table([[1], [2, 3]])]),), "rectangular"),
        ((_page(1, tables=[{**_table([[1]]), "rows": 2}]),), "rows"),
    ),
)
def test_page_aware_adapter_strictly_rejects_ambiguous_inputs(
    tmp_path, pages, error_text
):
    module = _adapter()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    with pytest.raises(module.PageAwarePDFAdapterError, match=error_text):
        module.adapt_pdf_pages(
            manifest=manifest,
            pages=pages,
            parser_version="1.0.0",
        )


def test_adapter_rejects_non_pdf_and_unverified_manifests(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    non_pdf, _ = _manifest(root, mime_type="text/markdown")

    with pytest.raises(module.PageAwarePDFAdapterError, match="application/pdf"):
        module.adapt_pdf_pages(
            manifest=non_pdf,
            pages=(_page(1),),
            parser_version="1.0.0",
        )

    manifest, _ = _manifest(root)
    quarantined = replace(
        manifest,
        immutable_status=contracts.ImmutableStatus.QUARANTINED,
    )
    with pytest.raises(module.PageAwarePDFAdapterError, match="verified"):
        module.adapt_pdf_pages(
            manifest=quarantined,
            pages=(_page(1),),
            parser_version="1.0.0",
        )


def test_result_is_frozen_deterministic_and_composes_with_ingest(tmp_path):
    module = _adapter()
    ingest = _ingest()
    root = _root(tmp_path)
    manifest, raw_path = _manifest(root)
    pages = (_page(1, text="Alpha\n\nBeta"), _page(2, text=""))
    before = _tree_snapshot(root)

    first = module.adapt_pdf_pages(
        manifest=manifest,
        pages=pages,
        parser_version="1.0.0",
    )
    replay = module.adapt_pdf_pages(
        manifest=manifest,
        pages=pages,
        parser_version="1.0.0",
    )
    assert replay == first
    with pytest.raises(FrozenInstanceError):
        first.page_count = 99

    service = ingest.IngestService(root=root)
    bundle = service.ingest(manifest=manifest, parser_results=first.parser_results)
    replay_bundle = service.ingest(
        manifest=manifest,
        parser_results=replay.parser_results,
        base=bundle,
    )
    assert replay_bundle.canonical_json() == bundle.canonical_json()
    assert _tree_snapshot(root) == before

    raw_path.write_bytes(b"X" * len(PDF_BYTES))
    drifted = _tree_snapshot(root)
    with pytest.raises(_contracts().SourceManifestMismatchError):
        service.ingest(manifest=manifest, parser_results=first.parser_results)
    assert _tree_snapshot(root) == drifted


def test_same_locator_parser_regression_fails_closed_without_writes(tmp_path):
    module = _adapter()
    ingest = _ingest()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    service = ingest.IngestService(root=root)
    first = module.adapt_pdf_pages(
        manifest=manifest,
        pages=(_page(1, text="Alpha"),),
        parser_version="1.0.0",
    )
    changed = module.adapt_pdf_pages(
        manifest=manifest,
        pages=(_page(1, text="Omega"),),
        parser_version="1.0.0",
    )
    base = service.ingest(manifest=manifest, parser_results=first.parser_results)
    before = _tree_snapshot(root)

    with pytest.raises(contracts.SourceExportConflictError):
        service.ingest(
            manifest=manifest,
            parser_results=changed.parser_results,
            base=base,
        )

    assert _tree_snapshot(root) == before


def test_invalid_parser_version_is_rejected_by_evidence_contract(tmp_path):
    module = _adapter()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    with pytest.raises(ValueError, match="parser_version"):
        module.adapt_pdf_pages(
            manifest=manifest,
            pages=(_page(1),),
            parser_version="latest",
        )


def test_page_aware_contract_is_published_but_not_wired_to_production():
    root = Path(__file__).resolve().parents[2]
    document = root / "docs" / "contracts" / "pdf-page-aware-parser-v1.md"

    assert document.is_file()
    content = document.read_text(encoding="utf-8")
    for phrase in (
        "physical page",
        "global normalized",
        "empty page",
        "table cell",
        "fail closed",
        "not production-wired",
    ):
        assert phrase in content
    assert "pdf-page-aware-parser-v1.md" in (root / "README.md").read_text(
        encoding="utf-8"
    )
    normalizer = (
        root / "src" / "company_wiki" / "source_catalog" / "normalizer.py"
    ).read_text(encoding="utf-8")
    assert "pdf_page_aware" not in normalizer
