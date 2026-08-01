"""Consumer contract for the pure legacy PDF-extract-v3 adapter."""

from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
import importlib
import inspect
import math
from pathlib import Path

import pytest


PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)
EXTRACTION_FIELDS = {
    "text",
    "pages_read",
    "total_pages",
    "total_chars",
    "quality_score",
    "is_scanned",
    "scan_confidence",
    "error",
}


def _adapter():
    return importlib.import_module(
        "company_wiki.parser_adapters.pdf_extract_v3"
    )


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
    content_sha256 = hashlib.sha256(PDF_BYTES).hexdigest()
    raw_path = root / "companies" / "测试公司" / "raw" / f"{content_sha256}{suffix}"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(PDF_BYTES)
    manifest = contracts.SourceManifest.from_file(
        root=root,
        file_path=raw_path,
        entity_ids=("TEST:000001",),
        source_type=contracts.SourceType.COMPANY_ANNOUNCEMENT,
        published_date="2026-03-25",
        retrieved_at="2026-07-18T12:34:56Z",
        collector_name="fixture_collector",
        collector_version="1.0.0",
        mime_type=mime_type,
    )
    return manifest, raw_path


def _extraction(**overrides):
    text = overrides.get("text", "第一段正文\n\n第二段正文")
    values = {
        "text": text,
        "pages_read": 2,
        "total_pages": 2,
        "total_chars": len(text),
        "quality_score": 0.95,
        "is_scanned": False,
        "scan_confidence": 0.0,
        "error": None,
    }
    values.update(overrides)
    if "text" in overrides and "total_chars" not in overrides:
        values["total_chars"] = len(overrides["text"])
    return values


def _tree_snapshot(root: Path) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries.append((relative + "/", "directory"))
        else:
            entries.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(entries)


def test_adapter_has_a_narrow_source_only_public_api():
    module = _adapter()
    package = importlib.import_module("company_wiki.parser_adapters")

    assert package.adapt_pdf_extract_v3 is module.adapt_pdf_extract_v3
    assert set(module.__all__) == {
        "PDF_EXTRACT_V3_PARSER_NAME",
        "PDFExtractV3AdapterError",
        "adapt_pdf_extract_v3",
    }
    assert "source_id" not in inspect.signature(module.adapt_pdf_extract_v3).parameters


def test_adapter_does_not_import_or_call_legacy_runtime_or_writers():
    module = _adapter()
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (("." * node.level) + (node.module or ""))
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert all(not name.startswith("scripts") for name in imports)
    assert imports.isdisjoint(
        {"sqlite3", "requests", "urllib", "httpx", "openai", "threading"}
    )
    assert called_attributes.isdisjoint(
        {"open", "mkdir", "write_text", "write_bytes", "unlink", "replace"}
    )
    for forbidden in (
        "KnowledgePatch",
        "ClaimType",
        "SourceRegistry",
        "RunStore",
        "StockWiki",
    ):
        assert forbidden not in source


def test_adapter_maps_global_paragraphs_and_exact_character_ranges(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    text = "第一段正文\n\n第二段正文"

    results = module.adapt_pdf_extract_v3(
        manifest=manifest,
        extraction=_extraction(text=text),
        parser_version="3.0.0",
    )

    assert len(results) == 2
    first, second = results
    assert first.source_id == manifest.source_id
    assert first.coordinates == contracts.EvidenceCoordinates(
        paragraph_index=0,
        char_start=0,
        char_end=len("第一段正文"),
    )
    second_start = len("第一段正文\n\n")
    assert second.coordinates == contracts.EvidenceCoordinates(
        paragraph_index=1,
        char_start=second_start,
        char_end=len(text),
    )
    assert [item.raw_text for item in results] == ["第一段正文", "第二段正文"]
    assert all(item.parser_name == module.PDF_EXTRACT_V3_PARSER_NAME for item in results)
    assert all(item.parser_version == "3.0.0" for item in results)
    assert all(item.parse_status is contracts.ParseStatus.PARSED for item in results)


def test_adapter_never_fabricates_physical_page_or_table_coordinates(tmp_path):
    module = _adapter()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    results = module.adapt_pdf_extract_v3(
        manifest=manifest,
        extraction=_extraction(),
        parser_version="3.0.0",
    )

    for result in results:
        coordinates = result.coordinates
        assert coordinates.page_number is None
        assert coordinates.table_index is None
        assert coordinates.row_index is None
        assert coordinates.column_index is None


def test_adapter_preserves_auditable_aggregate_metadata(tmp_path):
    module = _adapter()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    result = module.adapt_pdf_extract_v3(
        manifest=manifest,
        extraction=_extraction(),
        parser_version="3.0.0",
    )[0]

    assert result.to_evidence_span().to_dict()["structured_value"] == {
        "adapter": "pdf_extract_v3_aggregate",
        "physical_page_locator_available": False,
        "quality_score": 0.95,
        "scan_confidence": 0.0,
        "pages_read": 2,
        "total_pages": 2,
    }


def test_table_marker_is_text_only_and_flagged_ambiguous(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    text = "正文\n\n[TABLE 1]\n|项目|金额|\n|收入|100|"

    results = module.adapt_pdf_extract_v3(
        manifest=manifest,
        extraction=_extraction(text=text),
        parser_version="3.0.0",
    )

    assert results[0].parse_status is contracts.ParseStatus.PARSED
    assert results[1].parse_status is contracts.ParseStatus.PARTIAL
    assert results[1].quality_flags == ("table_structure_ambiguous",)
    assert results[1].coordinates.table_index is None


def test_truncation_and_low_quality_become_extraction_flags(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    result = module.adapt_pdf_extract_v3(
        manifest=manifest,
        extraction=_extraction(
            pages_read=1,
            total_pages=3,
            quality_score=0.29,
        ),
        parser_version="3.0.0",
    )[0]

    assert result.parse_status is contracts.ParseStatus.PARTIAL
    assert result.quality_flags == ("parser_warning", "truncated")


@pytest.mark.parametrize(
    "mutator",
    (
        lambda value: {key: item for key, item in value.items() if key != "text"},
        lambda value: {**value, "unexpected": True},
    ),
)
def test_adapter_rejects_missing_or_unknown_legacy_fields(tmp_path, mutator):
    module = _adapter()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    with pytest.raises(module.PDFExtractV3AdapterError, match="fields"):
        module.adapt_pdf_extract_v3(
            manifest=manifest,
            extraction=mutator(_extraction()),
            parser_version="3.0.0",
        )


@pytest.mark.parametrize(
    ("overrides", "error_text"),
    (
        ({"pages_read": True}, "pages_read"),
        ({"pages_read": 0}, "pages_read"),
        ({"total_pages": 1, "pages_read": 2}, "total_pages"),
        ({"total_chars": 999}, "total_chars"),
        ({"quality_score": math.nan}, "quality_score"),
        ({"quality_score": 1.1}, "quality_score"),
        ({"is_scanned": 0}, "is_scanned"),
        ({"scan_confidence": -0.1}, "scan_confidence"),
        ({"scan_confidence": 0.2}, "scan_confidence"),
        ({"text": "line one\r\nline two"}, "LF"),
        ({"text": "e\u0301"}, "NFC"),
    ),
)
def test_adapter_strictly_validates_legacy_value_types_and_identities(
    tmp_path,
    overrides,
    error_text,
):
    module = _adapter()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    with pytest.raises(module.PDFExtractV3AdapterError, match=error_text):
        module.adapt_pdf_extract_v3(
            manifest=manifest,
            extraction=_extraction(**overrides),
            parser_version="3.0.0",
        )


@pytest.mark.parametrize(
    ("overrides", "error_text"),
    (
        ({"error": "cannot open PDF"}, "error"),
        ({"is_scanned": True, "scan_confidence": 0.95}, "scanned"),
        ({"text": "", "pages_read": 0}, "empty"),
    ),
)
def test_adapter_rejects_error_scanned_and_empty_outputs(
    tmp_path,
    overrides,
    error_text,
):
    module = _adapter()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    with pytest.raises(module.PDFExtractV3AdapterError, match=error_text):
        module.adapt_pdf_extract_v3(
            manifest=manifest,
            extraction=_extraction(**overrides),
            parser_version="3.0.0",
        )


def test_adapter_rejects_non_pdf_and_quarantined_manifests(tmp_path):
    module = _adapter()
    contracts = _contracts()
    root = _root(tmp_path)
    non_pdf, _ = _manifest(root, mime_type="text/markdown")

    with pytest.raises(module.PDFExtractV3AdapterError, match="application/pdf"):
        module.adapt_pdf_extract_v3(
            manifest=non_pdf,
            extraction=_extraction(),
            parser_version="3.0.0",
        )

    pdf_manifest, _ = _manifest(root)
    quarantined = replace(
        pdf_manifest,
        immutable_status=contracts.ImmutableStatus.QUARANTINED,
    )
    with pytest.raises(module.PDFExtractV3AdapterError, match="verified"):
        module.adapt_pdf_extract_v3(
            manifest=quarantined,
            extraction=_extraction(),
            parser_version="3.0.0",
        )


def test_invalid_parser_version_is_rejected_by_the_evidence_contract(tmp_path):
    module = _adapter()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)

    with pytest.raises(ValueError, match="parser_version"):
        module.adapt_pdf_extract_v3(
            manifest=manifest,
            extraction=_extraction(),
            parser_version="latest",
        )


def test_adapter_composes_with_ingest_and_replays_byte_identically(tmp_path):
    module = _adapter()
    ingest = _ingest()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    results = module.adapt_pdf_extract_v3(
        manifest=manifest,
        extraction=_extraction(),
        parser_version="3.0.0",
    )
    service = ingest.IngestService(root=root)

    first = service.ingest(manifest=manifest, parser_results=results)
    replay = service.ingest(
        manifest=manifest,
        parser_results=results,
        base=first,
    )

    assert first.counts == {"source_manifests": 1, "evidence_spans": 2}
    assert replay.canonical_json() == first.canonical_json()


def test_adapter_and_ingest_are_read_only_and_raw_drift_still_fails(tmp_path):
    module = _adapter()
    ingest = _ingest()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, raw_path = _manifest(root)
    before = _tree_snapshot(root)
    results = module.adapt_pdf_extract_v3(
        manifest=manifest,
        extraction=_extraction(),
        parser_version="3.0.0",
    )
    service = ingest.IngestService(root=root)

    service.ingest(manifest=manifest, parser_results=results)
    assert _tree_snapshot(root) == before

    raw_path.write_bytes(b"X" * len(PDF_BYTES))
    drifted = _tree_snapshot(root)
    with pytest.raises(contracts.SourceManifestMismatchError):
        service.ingest(manifest=manifest, parser_results=results)
    assert _tree_snapshot(root) == drifted


def test_adapter_contract_document_is_published_and_linked():
    root = Path(__file__).resolve().parents[2]
    document = root / "docs" / "contracts" / "pdf-extract-v3-adapter-v1.md"

    assert document.is_file()
    content = document.read_text(encoding="utf-8")
    assert "global paragraph" in content
    assert "page_number" in content
    assert "table_index" in content
    assert "fail closed" in content
    assert "pdf-extract-v3-adapter-v1.md" in (root / "README.md").read_text(
        encoding="utf-8"
    )
