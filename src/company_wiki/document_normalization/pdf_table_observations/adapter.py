"""Compatibility exports for the former normalization-side PDF table adapter."""

from company_wiki.document_understanding.pdf_table_observations import (
    SCHEMA_OUT as SCHEMA_OUT,
    build_pdf_table_observations as build_pdf_table_observations,
)

__all__ = [
    "SCHEMA_OUT",
    "build_pdf_table_observations",
]
