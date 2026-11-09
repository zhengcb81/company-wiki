"""Compatibility facade for source-owned parser identity helpers."""

from company_wiki.source_catalog.narrative_formats import (
    NORMALIZED_MIME_TYPES as NORMALIZED_MIME_TYPES,
    NARRATIVE_PARSER_NAME as NARRATIVE_PARSER_NAME,
    NARRATIVE_PARSER_VERSION as NARRATIVE_PARSER_VERSION,
    parser_component as parser_component,
    source_class_for as source_class_for,
    transcript_parser_contract as transcript_parser_contract,
)

__all__ = [
    "NORMALIZED_MIME_TYPES",
    "NARRATIVE_PARSER_NAME",
    "NARRATIVE_PARSER_VERSION",
    "parser_component",
    "source_class_for",
    "transcript_parser_contract",
]
