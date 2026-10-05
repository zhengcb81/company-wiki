"""Source-facts digest API (alias of core.py helpers)."""

from __future__ import annotations

from legacy_storage.core import (
    FACT_TABLES,
    PROTECTED_TABLES,
    LEGACY_RECORD_TABLES,
    facts_overview,
    source_facts,
)

__all__ = [
    "FACT_TABLES",
    "LEGACY_RECORD_TABLES",
    "PROTECTED_TABLES",
    "facts_overview",
    "source_facts",
]
