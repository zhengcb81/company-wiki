"""Shared classification policy for Source Catalog LLM summary failures."""

from __future__ import annotations


_PERMANENT_ERROR_MARKERS = (
    "forbidden investment conclusion",
    "not valid json",
    "invalid schema",
)


def is_permanent_llm_summary_error(error: str) -> bool:
    normalized = str(error).casefold()
    return any(marker in normalized for marker in _PERMANENT_ERROR_MARKERS)


def effective_llm_summary_failure_scope(scope: str, error: str) -> str:
    if scope == "document" and is_permanent_llm_summary_error(error):
        return "permanent_document"
    return scope


__all__ = [
    "effective_llm_summary_failure_scope",
    "is_permanent_llm_summary_error",
]
