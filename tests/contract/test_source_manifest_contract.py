"""CW-1 contract tests for the versioned upstream source manifest."""

import importlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FIELDS = {
    "schema_version",
    "source_id",
    "entity_ids",
    "original_path",
    "content_sha256",
    "source_type",
    "published_date",
    "retrieved_at",
    "collector_name",
    "collector_version",
    "mime_type",
    "byte_size",
    "immutable_status",
}


def _contract():
    module_name = "company_wiki.source_contract"
    assert importlib.util.find_spec(module_name) is not None, (
        "versioned company_wiki.source_contract is not implemented"
    )
    return importlib.import_module(module_name)


def _manifest(module, root: Path, file_path: Path):
    return module.SourceManifest.from_file(
        root=root,
        file_path=file_path,
        entity_ids=("SSE:688012",),
        source_type=module.SourceType.REGULATORY_FILING,
        published_date="2026-03-31",
        retrieved_at="2026-07-17T09:30:00Z",
        collector_name="stock-info-downloader",
        collector_version="2.1.0",
        mime_type="application/pdf",
    )


def test_schema_is_versioned_strict_and_packaged():
    module = _contract()
    schema = module.load_source_manifest_schema()

    assert module.SOURCE_MANIFEST_SCHEMA_VERSION == "1.0.0"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:company-wiki:schema:source-manifest:1.0.0"
    assert set(schema["required"]) == REQUIRED_FIELDS
    assert set(schema["properties"]) == REQUIRED_FIELDS
    assert schema["additionalProperties"] is False


def test_from_file_builds_stable_content_identity_and_canonical_path(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    source = root / "companies" / "中微公司" / "raw" / "annual.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.7\nimmutable-source\n")

    first = _manifest(module, root, source)
    second = _manifest(module, root, source)

    assert first == second
    assert first.source_id == f"urn:company-wiki:source:sha256:{first.content_sha256}"
    assert first.original_path == "companies/中微公司/raw/annual.pdf"
    assert first.entity_ids == ("SSE:688012",)
    assert first.byte_size == source.stat().st_size
    assert first.immutable_status is module.ImmutableStatus.VERIFIED
    assert json.loads(first.canonical_json()) == first.to_dict()


def test_same_bytes_at_another_path_keep_source_id_but_not_location(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    left = root / "companies" / "中微公司" / "raw" / "left.pdf"
    right = root / "companies" / "中微公司" / "raw" / "right.pdf"
    left.parent.mkdir(parents=True)
    left.write_bytes(b"same immutable bytes")
    right.write_bytes(left.read_bytes())

    left_manifest = _manifest(module, root, left)
    right_manifest = _manifest(module, root, right)

    assert left_manifest.source_id == right_manifest.source_id
    assert left_manifest.content_sha256 == right_manifest.content_sha256
    assert left_manifest.original_path != right_manifest.original_path


def test_entity_ids_are_unique_sorted_and_unicode_normalized(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    source = root / "raw" / "news.md"
    source.parent.mkdir(parents=True)
    source.write_text("来源", encoding="utf-8")

    manifest = module.SourceManifest.from_file(
        root=root,
        file_path=source,
        entity_ids=("sector:半导体设备", "SSE:688012", "SSE:688012"),
        source_type=module.SourceType.ORIGINAL_NEWS,
        published_date=None,
        retrieved_at="2026-07-17T09:30:00Z",
        collector_name="news-collector",
        collector_version="1.0.0",
        mime_type="text/markdown",
    )

    assert manifest.entity_ids == ("SSE:688012", "sector:半导体设备")


@pytest.mark.parametrize(
    "relative_path",
    ("../escape.pdf", "/absolute.pdf", "companies/./report.pdf", "a\\b.pdf"),
)
def test_manifest_rejects_noncanonical_original_paths(relative_path):
    module = _contract()
    data = {
        "schema_version": "1.0.0",
        "source_id": "urn:company-wiki:source:sha256:" + "a" * 64,
        "entity_ids": ["SSE:688012"],
        "original_path": relative_path,
        "content_sha256": "a" * 64,
        "source_type": "regulatory_filing",
        "published_date": "2026-03-31",
        "retrieved_at": "2026-07-17T09:30:00Z",
        "collector_name": "collector",
        "collector_version": "1.0.0",
        "mime_type": "application/pdf",
        "byte_size": 10,
        "immutable_status": "verified",
    }
    with pytest.raises(ValueError):
        module.SourceManifest.from_dict(data)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("schema_version", "2.0.0"),
        ("source_id", "a" * 64),
        ("content_sha256", "A" * 64),
        ("published_date", "2026-02-30"),
        ("retrieved_at", "2026-07-17T09:30:00+00:00"),
        ("collector_name", ""),
        ("collector_version", "latest"),
        ("mime_type", "pdf"),
        ("byte_size", 0),
        ("immutable_status", "mutable"),
        ("source_type", "model_inference"),
    ),
)
def test_manifest_rejects_invalid_contract_values(field, value):
    module = _contract()
    data = {
        "schema_version": "1.0.0",
        "source_id": "urn:company-wiki:source:sha256:" + "a" * 64,
        "entity_ids": ["SSE:688012"],
        "original_path": "companies/中微公司/raw/report.pdf",
        "content_sha256": "a" * 64,
        "source_type": "regulatory_filing",
        "published_date": "2026-03-31",
        "retrieved_at": "2026-07-17T09:30:00Z",
        "collector_name": "collector",
        "collector_version": "1.0.0",
        "mime_type": "application/pdf",
        "byte_size": 10,
        "immutable_status": "verified",
    }
    data[field] = value
    with pytest.raises((TypeError, ValueError)):
        module.SourceManifest.from_dict(data)


def test_manifest_rejects_unknown_fields_and_hash_identity_mismatch():
    module = _contract()
    data = {
        "schema_version": "1.0.0",
        "source_id": "urn:company-wiki:source:sha256:" + "a" * 64,
        "entity_ids": ["SSE:688012"],
        "original_path": "companies/中微公司/raw/report.pdf",
        "content_sha256": "b" * 64,
        "source_type": "regulatory_filing",
        "published_date": None,
        "retrieved_at": "2026-07-17T09:30:00Z",
        "collector_name": "collector",
        "collector_version": "1.0.0",
        "mime_type": "application/pdf",
        "byte_size": 10,
        "immutable_status": "verified",
        "rating": "buy",
    }
    with pytest.raises(ValueError, match="unknown fields"):
        module.SourceManifest.from_dict(data)

    data.pop("rating")
    with pytest.raises(ValueError, match="source_id"):
        module.SourceManifest.from_dict(data)


def test_from_file_fails_closed_for_missing_empty_or_outside_root(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    root.mkdir()
    empty = root / "empty.pdf"
    empty.write_bytes(b"")
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"outside")

    with pytest.raises(FileNotFoundError):
        _manifest(module, root, root / "missing.pdf")
    with pytest.raises(ValueError, match="empty"):
        _manifest(module, root, empty)
    with pytest.raises(ValueError, match="root"):
        _manifest(module, root, outside)


def test_verify_file_detects_size_or_hash_drift(tmp_path):
    module = _contract()
    root = tmp_path / "repo"
    source = root / "raw" / "report.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"original")
    manifest = _manifest(module, root, source)

    manifest.verify_file(root=root, file_path=source)
    source.write_bytes(b"tampered")  # same length: hash check must catch the drift
    assert source.stat().st_size == manifest.byte_size
    with pytest.raises(module.SourceManifestMismatchError):
        manifest.verify_file(root=root, file_path=source)


def test_schema_documentation_lists_every_field_and_semantic_boundary():
    _contract()
    text = (ROOT / "docs" / "contracts" / "source-manifest-v1.md").read_text(
        encoding="utf-8"
    )
    for field in REQUIRED_FIELDS:
        assert f"`{field}`" in text
    assert "accepted investment conclusion" in text
    assert "StockWiki" in text
    assert "model_inference" in text


def test_source_type_enum_has_no_model_generated_source():
    module = _contract()
    values = {item.value for item in module.SourceType}
    assert "model_inference" not in values
    assert {
        "regulatory_filing",
        "company_announcement",
        "investor_relations",
        "broker_research",
        "original_news",
        "aggregated_news",
        "prospectus",
    } <= values
