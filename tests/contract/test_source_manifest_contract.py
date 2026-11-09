"""CW-1 contract tests for the versioned upstream source manifest."""

import importlib
import importlib.util
import json
import os
from pathlib import Path
import unicodedata

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


def test_manifest_keeps_distinct_unicode_file_names_with_the_same_bytes(tmp_path):
    module = _contract()
    composed = tmp_path / "Caf\u00e9.md"
    decomposed = tmp_path / "Cafe\u0301.md"
    for path in (composed, decomposed):
        path.write_bytes(b"same immutable bytes")
    if {child.name for child in tmp_path.iterdir()} != {composed.name, decomposed.name}:
        pytest.skip("this filesystem cannot distinguish canonically equivalent names")

    first = _manifest(module, tmp_path, composed)
    second = _manifest(module, tmp_path, decomposed)

    assert first.source_id == second.source_id
    assert first.original_path == composed.name
    assert second.original_path == decomposed.name
    assert module.SourceManifest.from_dict(second.to_dict()) == second
    first.verify_file(root=tmp_path, file_path=composed)
    second.verify_file(root=tmp_path, file_path=decomposed)
    with pytest.raises(module.SourceManifestMismatchError, match="location"):
        first.verify_file(root=tmp_path, file_path=decomposed)
    with pytest.raises(module.SourceManifestMismatchError, match="location"):
        second.verify_file(root=tmp_path, file_path=composed)
    decomposed.unlink()
    with pytest.raises(module.SourceManifestMismatchError):
        second.verify_file(root=tmp_path)


def test_manifest_rejects_ambiguous_old_nfc_locator_without_selecting_by_hash(tmp_path):
    module = _contract()
    first = tmp_path / "e\u0327\u0301.md"
    second = tmp_path / "e\u0301\u0327.md"
    first.write_bytes(b"known original")
    second.write_bytes(b"different file")
    if {child.name for child in tmp_path.iterdir()} != {first.name, second.name}:
        pytest.skip("this filesystem cannot distinguish canonically equivalent names")
    canonical = unicodedata.normalize("NFC", first.name)
    assert canonical == unicodedata.normalize("NFC", second.name)
    assert canonical not in (first.name, second.name)
    manifest = module.SourceManifest.from_dict({
        **_manifest(module, tmp_path, first).to_dict(), "original_path": canonical,
    })

    with pytest.raises(module.SourceManifestMismatchError, match="ambiguous"):
        manifest.verify_file(root=tmp_path, file_path=first)


def test_old_nfc_fallback_rejects_shadowed_parent_even_if_one_parent_is_exact(tmp_path):
    module = _contract()
    parents = (tmp_path / "Caf\u00e9", tmp_path / "Cafe\u0301")
    for parent in parents:
        parent.mkdir(exist_ok=True)
    if {child.name for child in tmp_path.iterdir()} != {parent.name for parent in parents}:
        pytest.skip("this filesystem cannot distinguish canonically equivalent names")
    first = parents[0] / "Re\u0301sume\u0301.md"
    second = parents[1] / "R\u00e9sum\u00e9.md"
    first.write_bytes(b"known original")
    second.write_bytes(b"another original")
    observed = _manifest(module, tmp_path, first)
    legacy = module.SourceManifest.from_dict({
        **observed.to_dict(), "original_path": unicodedata.normalize("NFC", observed.original_path),
    })

    with pytest.raises(module.SourceManifestMismatchError, match="ambiguous"):
        legacy.verify_file(root=tmp_path)


def test_old_nfc_fallback_does_not_hash_a_canonically_equivalent_outside_link(tmp_path, monkeypatch):
    module = _contract()
    implementation = importlib.import_module("company_wiki.source_contract.source_manifest")
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    original = root / "valid.md"
    original.write_bytes(b"known original")
    (outside / "valid.md").write_bytes(original.read_bytes())
    try:
        (root / "Cafe\u0301").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this host")
    manifest = module.SourceManifest.from_dict({
        **_manifest(module, root, original).to_dict(), "original_path": "Caf\u00e9/valid.md",
    })

    def unexpected_hash(_path):
        pytest.fail("a locator outside the root reached the SHA read")

    monkeypatch.setattr(implementation, "_hash_file", unexpected_hash)
    with pytest.raises(module.SourceManifestMismatchError, match="inside root"):
        manifest.verify_file(root=root)


def test_old_nfc_locator_never_falls_through_existing_exact_spelling(tmp_path):
    module = _contract()
    decomposed = tmp_path / "Cafe\u0301.md"
    composed = tmp_path / "Caf\u00e9.md"
    decomposed.write_bytes(b"original")
    composed.write_bytes(b"tampered")
    if {child.name for child in tmp_path.iterdir()} != {composed.name, decomposed.name}:
        pytest.skip("this filesystem cannot distinguish canonically equivalent names")
    manifest = module.SourceManifest.from_dict({
        **_manifest(module, tmp_path, decomposed).to_dict(), "original_path": composed.name,
    })

    with pytest.raises(module.SourceManifestMismatchError, match="SHA-256"):
        manifest.verify_file(root=tmp_path, file_path=composed)
    with pytest.raises(module.SourceManifestMismatchError, match="location"):
        manifest.verify_file(root=tmp_path, file_path=decomposed)


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


def test_manifest_keeps_historical_posix_names_with_nonleading_colons(tmp_path):
    module = _contract()
    source = tmp_path / "original.pdf"
    source.write_bytes(b"unchanged bytes")
    manifest = _manifest(module, tmp_path, source)
    relative_path = "reports/C:annual.pdf"
    stored = module.SourceManifest.from_dict({**manifest.to_dict(), "original_path": relative_path})

    assert stored.original_path == relative_path
    if os.name != "nt":
        physical = tmp_path / relative_path
        physical.parent.mkdir()
        physical.write_bytes(source.read_bytes())
        stored.verify_file(root=tmp_path, file_path=physical)


@pytest.mark.parametrize(
    "relative_path",
    ("../escape.pdf", "/absolute.pdf", "companies/./report.pdf", "a\\b.pdf", "C:escape.pdf"),
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


def test_verify_file_refuses_a_source_changed_during_hashing(tmp_path, monkeypatch):
    module = _contract()
    implementation = importlib.import_module("company_wiki.source_contract.source_manifest")
    source = tmp_path / "report.pdf"
    source.write_bytes(b"original")
    manifest = _manifest(module, tmp_path, source)
    hash_file = implementation._hash_file

    def hash_then_mutate(path):
        digest = hash_file(path)
        before = path.stat()
        path.write_bytes(b"tampered")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
        return digest

    monkeypatch.setattr(implementation, "_hash_file", hash_then_mutate)
    with pytest.raises(module.SourceManifestMismatchError, match="changed while hashing"):
        manifest.verify_file(root=tmp_path, file_path=source)


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
