"""Compatibility exports for the former text matching module."""

from company_wiki.document_model.text_matching import (
    SCRIPT_MATCHING_VERSION as SCRIPT_MATCHING_VERSION,
    matching_script_text as matching_script_text,
    matching_reading_text as matching_reading_text,
)

__all__ = [
    "SCRIPT_MATCHING_VERSION",
    "matching_script_text",
    "matching_reading_text",
]
