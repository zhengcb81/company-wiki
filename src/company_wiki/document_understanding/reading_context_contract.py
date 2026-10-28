"""Shared wire capabilities; these labels do not classify document contents."""

from __future__ import annotations

import re

CURRENT_READING_CONTEXT_SCHEMA = "du-production-reading/4"
READING_CONTEXT_SCHEMAS = frozenset(
    f"du-production-reading/{version}" for version in (1, 2, 3, 4)
)
ATTRIBUTED_READING_CONTEXT_SCHEMAS = READING_CONTEXT_SCHEMAS - {
    "du-production-reading/1"
}
TRACED_READING_CONTEXT_SCHEMAS = frozenset(
    {"du-production-reading/3", CURRENT_READING_CONTEXT_SCHEMA}
)
SUMMARY_USE_CONTEXT_SCHEMAS = frozenset({CURRENT_READING_CONTEXT_SCHEMA})
SUMMARY_SUPPORT_USES = frozenset({"support", "context_only", "unresolved"})


def validate_summary_support_use(value: object, reason: object) -> tuple[str, str]:
    """Validate one source-owned use/reason without reading its evidence text."""
    if not isinstance(value, str) or value not in SUMMARY_SUPPORT_USES:
        raise ValueError("source summary support use is invalid")
    if (
        not isinstance(reason, str)
        or re.fullmatch(r"[a-z][a-z0-9_]{0,79}", reason) is None
    ):
        raise ValueError(
            "source summary support reason must be a bounded diagnostic code"
        )
    return value, reason
