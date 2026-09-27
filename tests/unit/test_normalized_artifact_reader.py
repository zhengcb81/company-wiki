"""The shared normalized-text reader verifies bytes and source lineage."""

from __future__ import annotations

import hashlib
import json

import pytest

from company_wiki.source_catalog.models import NORMALIZER_VERSION
from company_wiki.source_catalog.normalized_artifact_reader import (
    NormalizedArtifactReadError,
    read_verified_normalized_text,
)


def _row(tmp_path, data: bytes = b"Verified source text.\n") -> dict[str, str]:
    path = tmp_path / "normalized.md"
    path.write_bytes(data)
    source_sha = "a" * 64
    return {
        "normalized_path": str(path),
        "normalized_sha256": hashlib.sha256(data).hexdigest(),
        "normalized_status": "completed",
        "normalized_source_id": "urn:source:test",
        "normalized_source_sha256": source_sha,
        "normalized_generator_name": "source_catalog_normalizer",
        "normalized_generator_version": NORMALIZER_VERSION,
        "primary_source_id": "urn:source:test",
        "source_sha256": source_sha,
    }


@pytest.mark.parametrize("status", ["completed", "partial"])
def test_verified_normalized_reader_returns_exact_utf8_text(tmp_path, status):
    row = _row(tmp_path, "业务进展。\n".encode("utf-8"))
    row["normalized_status"] = status
    assert read_verified_normalized_text(row) == "业务进展。\n"


@pytest.mark.parametrize(
    ("field", "wrong", "reason"),
    [
        ("normalized_status", "unsupported", "normalized_status_unusable"),
        ("normalized_source_id", "urn:source:other", "normalized_source_binding_mismatch"),
        ("normalized_source_sha256", "b" * 64, "normalized_source_sha_mismatch"),
        ("normalized_generator_version", "0.0.0", "normalized_generator_unsupported"),
    ],
)
def test_verified_normalized_reader_refuses_unusable_lineage(
    tmp_path, field, wrong, reason
):
    row = _row(tmp_path)
    row[field] = wrong
    with pytest.raises(NormalizedArtifactReadError, match=reason):
        read_verified_normalized_text(row)


def test_verified_normalized_reader_refuses_invalid_utf8_after_hash_match(tmp_path):
    row = _row(tmp_path, b"\xff")
    with pytest.raises(NormalizedArtifactReadError, match="normalized_utf8_invalid"):
        read_verified_normalized_text(row)


def _legacy_row(
    tmp_path,
    *,
    generator_name="structured_text",
    parser_name="structured_text",
    metadata=None,
):
    source_sha = "a" * 64
    data = (
        "---\n"
        "artifact_role: normalized\n"
        "document_id: urn:document:test\n"
        "source_id: urn:source:test\n"
        f"source_sha256: {source_sha}\n"
        "normalization_status: completed\n"
        f"parser_name: {parser_name}\n"
        "parser_version: 1.0.0\n"
        "---\n\n# Verified source text\n"
    ).encode("utf-8")
    row = _row(tmp_path, data)
    row.update(
        document_id="urn:document:test",
        normalized_source_sha256="",
        normalized_generator_name=generator_name,
        normalized_generator_version="1.0.0",
        normalized_metadata_json=json.dumps(metadata or {}),
    )
    return row, data


@pytest.mark.parametrize(
    ("generator_name", "parser_name", "metadata"),
    [
        ("structured_text", "structured_text", {}),
        (
            "source_catalog_normalizer",
            "plain_text",
            {"parser_name": "plain_text", "parser_version": "1.0.0"},
        ),
        ("pymupdf_page_text", "pdf_page_aware_core", {}),
    ],
)
def test_verified_normalized_reader_accepts_bound_legacy_artifact(
    tmp_path, generator_name, parser_name, metadata
):
    row, data = _legacy_row(
        tmp_path,
        generator_name=generator_name,
        parser_name=parser_name,
        metadata=metadata,
    )
    assert read_verified_normalized_text(row) == data.decode("utf-8")


@pytest.mark.parametrize(
    ("field", "wrong", "reason"),
    [
        ("source_id", "urn:source:other", "normalized_frontmatter_source_mismatch"),
        ("source_sha256", "b" * 64, "normalized_frontmatter_source_mismatch"),
        ("document_id", "urn:document:other", "normalized_frontmatter_document_mismatch"),
        ("parser_name", "unknown_parser", "normalized_parser_binding_mismatch"),
        ("parser_version", "0.0.0", "normalized_parser_binding_mismatch"),
        ("normalization_status", "failed", "normalized_frontmatter_status_mismatch"),
    ],
)
def test_verified_normalized_reader_refuses_legacy_frontmatter_mismatch(
    tmp_path, field, wrong, reason
):
    row, data = _legacy_row(tmp_path)
    original = {
        "source_id": "urn:source:test",
        "source_sha256": "a" * 64,
        "document_id": "urn:document:test",
        "parser_name": "structured_text",
        "parser_version": "1.0.0",
        "normalization_status": "completed",
    }[field]
    changed = data.decode("utf-8").replace(
        f"{field}: {original}",
        f"{field}: {wrong}",
        1,
    ).encode("utf-8")
    path = tmp_path / "normalized.md"
    path.write_bytes(changed)
    row["normalized_sha256"] = hashlib.sha256(changed).hexdigest()
    with pytest.raises(NormalizedArtifactReadError, match=reason):
        read_verified_normalized_text(row)


def test_verified_normalized_reader_refuses_legacy_bad_digest(tmp_path):
    row, data = _legacy_row(tmp_path)
    (tmp_path / "normalized.md").write_bytes(data + b"\nTampered\n")
    with pytest.raises(NormalizedArtifactReadError, match="normalized_digest_mismatch"):
        read_verified_normalized_text(row)


def test_verified_normalized_reader_refuses_unbound_normalizer_parser(tmp_path):
    row, _ = _legacy_row(tmp_path, generator_name="source_catalog_normalizer")
    with pytest.raises(NormalizedArtifactReadError, match="normalized_parser_binding_missing"):
        read_verified_normalized_text(row)


def test_verified_normalized_reader_refuses_legacy_metadata_disagreement(tmp_path):
    row, _ = _legacy_row(
        tmp_path,
        generator_name="source_catalog_normalizer",
        parser_name="plain_text",
        metadata={"parser_name": "structured_text", "parser_version": "1.0.0"},
    )
    with pytest.raises(NormalizedArtifactReadError, match="normalized_parser_binding_mismatch"):
        read_verified_normalized_text(row)


def test_verified_normalized_reader_refuses_missing_legacy_frontmatter_field(tmp_path):
    row, data = _legacy_row(tmp_path)
    changed = data.replace(b"parser_version: 1.0.0\n", b"", 1)
    (tmp_path / "normalized.md").write_bytes(changed)
    row["normalized_sha256"] = hashlib.sha256(changed).hexdigest()
    with pytest.raises(NormalizedArtifactReadError, match="normalized_frontmatter_invalid"):
        read_verified_normalized_text(row)
