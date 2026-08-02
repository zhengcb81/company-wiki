"""Public source-only canonical ingest entry point."""

from __future__ import annotations

from typing import Any

from .canonical_ingest import (
    IngestContractError,
    IngestService,
    IngestSourceMismatchError,
    ParserResult,
)


_LEGACY_EXPORTS = frozenset(
    {
        "ContentAnalyzer",
        "ContentNormalizer",
        "LegacyResearchIngestService",
        "OutputValidator",
    }
)


def __getattr__(name: str) -> Any:
    """Load frozen legacy helpers only when explicitly requested."""

    if name not in _LEGACY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from . import legacy_research_ingest

    return getattr(legacy_research_ingest, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | _LEGACY_EXPORTS)


__all__ = [
    "IngestContractError",
    "IngestService",
    "IngestSourceMismatchError",
    "ParserResult",
]
