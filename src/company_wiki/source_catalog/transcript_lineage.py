"""Compact transcript lineage validation and deterministic replay."""

from __future__ import annotations

from typing import Any, Mapping

from .transcript_text_extract import (
    MAX_TRANSCRIPT_LINES,
    TRANSCRIPT_MIME_TYPES,
    TranscriptMaterial,
    TranscriptMaterialError,
    extract_transcript_material,
)


_LINEAGE_FIELDS = frozenset(
    {
        "schema_version",
        "original_source_id",
        "original_sha256",
        "original_mime_type",
        "original_byte_size",
        "text_sha256",
        "text_byte_size",
        "extractor_version",
        "line_count",
    }
)
_TEXT_FIELDS = (
    "schema_version",
    "original_source_id",
    "original_sha256",
    "original_mime_type",
    "text_sha256",
    "extractor_version",
)
_INTEGER_FIELDS = ("original_byte_size", "text_byte_size", "line_count")


def _validate_lineage_shape(lineage: Mapping[str, Any]) -> None:
    if not isinstance(lineage, Mapping) or set(lineage) != _LINEAGE_FIELDS:
        raise TranscriptMaterialError("lineage fields differ from schema")
    if any(not isinstance(lineage[key], str) for key in _TEXT_FIELDS):
        raise TranscriptMaterialError("lineage text fields must be strings")
    if any(type(lineage[key]) is not int for key in _INTEGER_FIELDS):
        raise TranscriptMaterialError(
            "lineage sizes and line count must be integers"
        )


def _validate_replay_inputs(
    lineage: Mapping[str, Any],
    original: object,
    text_utf8: object,
    expected_mime_type: object,
) -> None:
    if not isinstance(original, bytes) or not isinstance(text_utf8, bytes):
        raise TranscriptMaterialError("original and derived text must be bytes")
    if not isinstance(expected_mime_type, str) or (
        expected_mime_type not in TRANSCRIPT_MIME_TYPES
    ):
        raise TranscriptMaterialError("unsupported trusted original MIME type")
    if lineage["original_mime_type"] != expected_mime_type:
        raise TranscriptMaterialError(
            "lineage MIME differs from trusted source receipt"
        )
    if not 0 < lineage["line_count"] <= MAX_TRANSCRIPT_LINES:
        raise TranscriptMaterialError("lineage line count is out of bounds")


def load_transcript_material(
    lineage: Mapping[str, Any],
    *,
    original: bytes,
    text_utf8: bytes,
    expected_mime_type: str,
) -> TranscriptMaterial:
    """Replay compact lineage using MIME trusted from the source receipt."""
    _validate_lineage_shape(lineage)
    _validate_replay_inputs(lineage, original, text_utf8, expected_mime_type)
    extracted = extract_transcript_material(
        original, mime_type=expected_mime_type
    )
    if extracted.lineage_dict() != dict(lineage):
        raise TranscriptMaterialError(
            "lineage differs from deterministic extraction"
        )
    if text_utf8 != extracted.text_utf8.encode("utf-8"):
        raise TranscriptMaterialError(
            "derived text differs from deterministic extraction"
        )
    return extracted
