"""Read verified normalized text for internal source-processing consumers.

The catalog owns the physical path.  Callers receive text from the same bytes
that passed the artifact digest check, with no root or privacy allowance.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .models import NORMALIZER_VERSION


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_READABLE_STATUSES = frozenset({"completed", "partial"})
_LEGACY_FIELDS = frozenset(
    {
        "artifact_role",
        "document_id",
        "source_id",
        "source_sha256",
        "normalization_status",
        "parser_name",
        "parser_version",
    }
)
# The historical PDF artifact row used the library name while its own
# frontmatter recorded the normalized parser name. Both carry the same version.
_LEGACY_PARSER_ALIASES = {"pymupdf_page_text": "pdf_page_aware_core"}


class NormalizedArtifactReadError(ValueError):
    """A pathless refusal to consume an unverified normalized artifact."""


def _field(row: Any, name: str) -> str:
    value = row[name]
    return value if isinstance(value, str) else ""


def _legacy_frontmatter(text: str) -> dict[str, str]:
    """Read only the top-level scalar bindings, not the potentially large YAML tree."""
    if not text.startswith("---\n"):
        raise NormalizedArtifactReadError("normalized_frontmatter_invalid")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise NormalizedArtifactReadError("normalized_frontmatter_invalid")
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if not separator or key not in _LEGACY_FIELDS:
            continue
        if key in fields:
            raise NormalizedArtifactReadError("normalized_frontmatter_invalid")
        try:
            parsed = yaml.safe_load(value.strip())
        except yaml.YAMLError:
            raise NormalizedArtifactReadError("normalized_frontmatter_invalid") from None
        if not isinstance(parsed, str) or not parsed:
            raise NormalizedArtifactReadError("normalized_frontmatter_invalid")
        fields[key] = parsed
    if fields.keys() != _LEGACY_FIELDS:
        raise NormalizedArtifactReadError("normalized_frontmatter_invalid")
    return fields


def _verify_legacy_lineage(row: Any, text: str, source_sha: str) -> None:
    frontmatter = _legacy_frontmatter(text)
    if frontmatter["artifact_role"] != "normalized":
        raise NormalizedArtifactReadError("normalized_frontmatter_invalid")
    if frontmatter["document_id"] != _field(row, "document_id"):
        raise NormalizedArtifactReadError("normalized_frontmatter_document_mismatch")
    if (
        frontmatter["source_id"] != _field(row, "primary_source_id")
        or frontmatter["source_sha256"] != source_sha
    ):
        raise NormalizedArtifactReadError("normalized_frontmatter_source_mismatch")
    if frontmatter["normalization_status"] != _field(row, "normalized_status"):
        raise NormalizedArtifactReadError("normalized_frontmatter_status_mismatch")
    try:
        metadata = json.loads(_field(row, "normalized_metadata_json"))
    except json.JSONDecodeError:
        raise NormalizedArtifactReadError("normalized_parser_binding_missing") from None
    if not isinstance(metadata, dict):
        raise NormalizedArtifactReadError("normalized_parser_binding_missing")
    generator_name = _field(row, "normalized_generator_name")
    generator_version = _field(row, "normalized_generator_version")
    parser_name = frontmatter["parser_name"]
    parser_version = frontmatter["parser_version"]
    if not generator_name or not generator_version:
        raise NormalizedArtifactReadError("normalized_parser_binding_missing")
    if generator_name == "source_catalog_normalizer":
        if not metadata.get("parser_name") or not metadata.get("parser_version"):
            raise NormalizedArtifactReadError("normalized_parser_binding_missing")
    elif (
        parser_name != _LEGACY_PARSER_ALIASES.get(generator_name, generator_name)
        or parser_version != generator_version
    ):
        raise NormalizedArtifactReadError("normalized_parser_binding_mismatch")
    if metadata.get("parser_name", parser_name) != parser_name or metadata.get(
        "parser_version", parser_version
    ) != parser_version:
        raise NormalizedArtifactReadError("normalized_parser_binding_mismatch")


def preferred_normalized_artifact_predicate(alias: str) -> str:
    """Select one artifact per document before any consumer reads its bytes.

    A damaged preferred row must remain the selected row so the reader can
    report its failure; selection never substitutes an older source version.
    """
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", alias):
        raise ValueError("invalid SQL alias")
    return f"""{alias}.artifact_id = (
        SELECT candidate.artifact_id FROM artifacts candidate
        WHERE candidate.document_id=d.document_id
          AND candidate.artifact_role='normalized'
        ORDER BY CASE
            WHEN candidate.generator_name='source_catalog_normalizer'
             AND candidate.generator_version='{NORMALIZER_VERSION}' THEN 0
            WHEN candidate.generator_name='source_catalog_normalizer' THEN 1
            ELSE 2 END,
            candidate.created_at DESC, candidate.artifact_id ASC
        LIMIT 1)"""


def read_verified_normalized_text(row: Any) -> str:
    """Verify one joined catalog row and return its exact UTF-8 text."""
    if _field(row, "normalized_status") not in _READABLE_STATUSES:
        raise NormalizedArtifactReadError("normalized_status_unusable")
    source_id = _field(row, "primary_source_id")
    if not source_id or _field(row, "normalized_source_id") != source_id:
        raise NormalizedArtifactReadError("normalized_source_binding_mismatch")
    source_sha = _field(row, "source_sha256")
    if not _SHA256.fullmatch(source_sha):
        raise NormalizedArtifactReadError("normalized_source_sha_mismatch")
    artifact_source_sha = _field(row, "normalized_source_sha256")
    legacy = not artifact_source_sha
    if not legacy:
        if artifact_source_sha != source_sha:
            raise NormalizedArtifactReadError("normalized_source_sha_mismatch")
        if (
            _field(row, "normalized_generator_name") != "source_catalog_normalizer"
            or _field(row, "normalized_generator_version") != NORMALIZER_VERSION
        ):
            raise NormalizedArtifactReadError("normalized_generator_unsupported")
    expected_sha = _field(row, "normalized_sha256")
    if not _SHA256.fullmatch(expected_sha):
        raise NormalizedArtifactReadError("normalized_digest_invalid")
    path_value = _field(row, "normalized_path")
    if not path_value:
        raise NormalizedArtifactReadError("normalized_path_missing")
    try:
        data = Path(path_value).read_bytes()
    except OSError:
        raise NormalizedArtifactReadError("normalized_read_failed") from None
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise NormalizedArtifactReadError("normalized_digest_mismatch")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise NormalizedArtifactReadError("normalized_utf8_invalid") from None
    if legacy:
        _verify_legacy_lineage(row, text, source_sha)
    return text


__all__ = [
    "NormalizedArtifactReadError",
    "preferred_normalized_artifact_predicate",
    "read_verified_normalized_text",
]
