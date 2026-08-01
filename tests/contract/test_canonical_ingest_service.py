"""Consumer contract for the source-only canonical ingest boundary."""

from __future__ import annotations

import ast
from dataclasses import fields, replace
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
SOURCE_URL = (
    "https://star.sse.com.cn/disclosure/listedinfo/announcement/c/new/"
    "2026-03-25/688012_20260325_404H.pdf"
)
FINAL_URL = SOURCE_URL.replace("star.sse.com.cn", "static.sse.com.cn")


def _module():
    return importlib.import_module("company_wiki.canonical_ingest")


def _contracts():
    return importlib.import_module("company_wiki.source_contract")


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    return root


def _manifest(root: Path, *, content: bytes = PDF_BYTES):
    contracts = _contracts()
    content_sha256 = hashlib.sha256(content).hexdigest()
    raw_path = (
        root
        / "companies"
        / "中微公司"
        / "raw"
        / "announcements"
        / f"{content_sha256}.pdf"
    )
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(content)
    manifest = contracts.SourceManifest.from_file(
        root=root,
        file_path=raw_path,
        entity_ids=("SSE:688012",),
        source_type=contracts.SourceType.COMPANY_ANNOUNCEMENT,
        published_date="2026-03-25",
        retrieved_at="2026-07-18T12:34:56Z",
        collector_name="official_exchange_announcement",
        collector_version="1.0.0",
        mime_type="application/pdf",
    )
    return manifest, raw_path


def _parser_result(source_id: str, **overrides):
    module = _module()
    contracts = _contracts()
    values = {
        "source_id": source_id,
        "coordinates": contracts.EvidenceCoordinates(
            page_number=1,
            paragraph_index=0,
        ),
        "raw_text": "公司公告正文",
        "structured_value": {"document_type": "announcement"},
        "parser_name": "fixture_pdf_parser",
        "parser_version": "1.0.0",
        "parse_status": contracts.ParseStatus.PARSED,
        "quality_flags": (),
    }
    values.update(overrides)
    return module.ParserResult(**values)


def _receipt(manifest):
    contracts = _contracts()
    content_hash = manifest.content_sha256
    provenance_key = hashlib.sha256(
        (content_hash + "\0" + SOURCE_URL).encode("utf-8")
    ).hexdigest()
    return contracts.AnnouncementCollectionReceipt.create(
        source_url=SOURCE_URL,
        final_url=FINAL_URL,
        title="关于召开2025年度业绩说明会的公告",
        published_date="2026-03-25",
        retrieved_at="2026-07-18T12:34:56Z",
        content_type="application/pdf",
        etag='"official-etag"',
        last_modified="Wed, 25 Mar 2026 08:00:00 GMT",
        manifest_path=(
            f"source_manifests/companies/中微公司/{content_hash}.json"
        ),
        provenance_path=(
            "source_provenance/companies/中微公司/announcements/"
            f"{provenance_key}.json"
        ),
        manifest=manifest,
    )


def _tree_snapshot(root: Path) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries.append((relative + "/", "directory"))
        else:
            entries.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(entries)


def test_public_ingest_name_is_the_canonical_source_only_service():
    module = _module()
    public_module = importlib.import_module("company_wiki.ingest")

    assert public_module.IngestService is module.IngestService
    assert public_module.LegacyResearchIngestService is not module.IngestService
    assert hasattr(module.IngestService, "ingest")
    assert hasattr(module.IngestService, "ingest_announcement")
    assert not hasattr(module.IngestService, "analyze")


def test_canonical_module_has_no_research_writer_or_runtime_dependencies():
    module = _module()
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert imports.isdisjoint(
        {"sqlite3", "requests", "urllib", "httpx", "openai", "threading"}
    )
    for forbidden in (
        "KnowledgePatch",
        "ClaimType",
        "SourceRegistry",
        "RunStore",
        "StockWiki",
        "write_text",
        "write_bytes",
    ):
        assert forbidden not in source


def test_parser_result_is_immutable_and_builds_the_published_span_contract(tmp_path):
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    structured_value = {"metrics": ["revenue"]}
    result = _parser_result(
        manifest.source_id,
        structured_value=structured_value,
    )
    structured_value["metrics"].append("profit")

    span = result.to_evidence_span()
    assert span.source_id == manifest.source_id
    assert span.locator == "loc:v1/page:1/paragraph:0"
    assert span.to_dict()["structured_value"] == {"metrics": ["revenue"]}
    with pytest.raises((AttributeError, TypeError)):
        result.raw_text = "mutated"


def test_ingest_verifies_raw_and_emits_only_manifest_and_evidence(tmp_path):
    module = _module()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    result = _parser_result(manifest.source_id)

    bundle = module.IngestService(root=root).ingest(
        manifest=manifest,
        parser_results=(result,),
    )

    assert bundle.counts == {"source_manifests": 1, "evidence_spans": 1}
    assert bundle.manifests == (manifest,)
    assert bundle.evidence_spans == (result.to_evidence_span(),)
    assert set(bundle.to_dict()) == {
        "schema_version",
        "export_id",
        "bundle_sha256",
        "source_manifest_schema_version",
        "evidence_span_schema_version",
        "counts",
        "manifests",
        "evidence_spans",
    }


def test_ingest_fails_closed_when_raw_bytes_drift_without_size_change(tmp_path):
    module = _module()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, raw_path = _manifest(root)
    raw_path.write_bytes(b"X" * len(PDF_BYTES))

    with pytest.raises(contracts.SourceManifestMismatchError, match="SHA-256"):
        module.IngestService(root=root).ingest(
            manifest=manifest,
            parser_results=(_parser_result(manifest.source_id),),
        )


def test_ingest_rejects_parser_result_for_another_source(tmp_path):
    module = _module()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    other_source_id = contracts.source_id_for_sha256("b" * 64)

    with pytest.raises(module.IngestSourceMismatchError, match="parser result"):
        module.IngestService(root=root).ingest(
            manifest=manifest,
            parser_results=(_parser_result(other_source_id),),
        )


def test_ingest_rejects_conflicting_outputs_at_one_locator(tmp_path):
    module = _module()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    first = _parser_result(manifest.source_id, raw_text="first")
    second = _parser_result(manifest.source_id, raw_text="second")

    with pytest.raises(contracts.SourceExportConflictError, match="locator"):
        module.IngestService(root=root).ingest(
            manifest=manifest,
            parser_results=(first, second),
        )


def test_identical_replay_and_incremental_replay_are_byte_identical(tmp_path):
    module = _module()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    result = _parser_result(manifest.source_id)
    service = module.IngestService(root=root)

    duplicate_bundle = service.ingest(
        manifest=manifest,
        parser_results=(result, result),
    )
    replay_bundle = service.ingest(
        manifest=manifest,
        parser_results=(result,),
        base=duplicate_bundle,
    )

    assert duplicate_bundle.counts == {
        "source_manifests": 1,
        "evidence_spans": 1,
    }
    assert replay_bundle.canonical_json() == duplicate_bundle.canonical_json()


def test_ingest_is_read_only_across_success_and_failure(tmp_path):
    module = _module()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    before = _tree_snapshot(root)
    service = module.IngestService(root=root)

    service.ingest(
        manifest=manifest,
        parser_results=(_parser_result(manifest.source_id),),
    )
    with pytest.raises(module.IngestSourceMismatchError):
        service.ingest(
            manifest=manifest,
            parser_results=(_parser_result(_contracts().source_id_for_sha256("c" * 64)),),
        )

    assert _tree_snapshot(root) == before


def test_announcement_receipt_adapter_uses_the_general_ingest_path(tmp_path):
    module = _module()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    result = _parser_result(manifest.source_id)

    bundle = module.IngestService(root=root).ingest_announcement(
        receipt=_receipt(manifest),
        parser_results=(result,),
    )

    assert bundle.manifests == (manifest,)
    assert bundle.evidence_spans == (result.to_evidence_span(),)


def test_announcement_adapter_revalidates_receipt_identity(tmp_path):
    module = _module()
    contracts = _contracts()
    root = _root(tmp_path)
    manifest, _ = _manifest(root)
    tampered = replace(
        _receipt(manifest),
        collection_id=(
            contracts.ANNOUNCEMENT_COLLECTION_ID_PREFIX + "0" * 64
        ),
    )

    with pytest.raises(contracts.AnnouncementCollectionError, match="collection_id"):
        module.IngestService(root=root).ingest_announcement(
            receipt=tampered,
            parser_results=(_parser_result(manifest.source_id),),
        )


def test_parser_result_and_service_expose_no_downstream_research_state():
    module = _module()
    result_fields = {field.name for field in fields(module.ParserResult)}

    assert result_fields == {
        "source_id",
        "coordinates",
        "raw_text",
        "structured_value",
        "parser_name",
        "parser_version",
        "parse_status",
        "quality_flags",
    }
    assert result_fields.isdisjoint(
        {
            "rating",
            "target_price",
            "position",
            "valuation",
            "sotp",
            "accepted",
            "rejected",
            "claims",
            "knowledge_patch",
        }
    )
