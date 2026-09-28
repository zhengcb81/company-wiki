"""Compatibility facade for deterministic transcript text and lineage replay."""

from .transcript_lineage import load_transcript_material
from .transcript_text_extract import (
    TRANSCRIPT_MATERIAL_EXTRACTOR,
    TRANSCRIPT_MATERIAL_SCHEMA,
    TranscriptMaterial,
    TranscriptMaterialError,
    TranscriptTextLine,
    extract_transcript_material,
)


__all__ = [
    "TRANSCRIPT_MATERIAL_EXTRACTOR",
    "TRANSCRIPT_MATERIAL_SCHEMA",
    "TranscriptMaterial",
    "TranscriptMaterialError",
    "TranscriptTextLine",
    "extract_transcript_material",
    "load_transcript_material",
]
