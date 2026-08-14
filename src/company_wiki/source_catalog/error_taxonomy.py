"""ZR-204: unified DB busy/locked / operation-lock / timeout / paused
error taxonomy with the non-lock-never-retryable rule.

The counterexample (ZR102-F2, replayed fresh): a raw SQLite
``OperationalError("database is locked")`` emitted by the wiki CLI was
classified ``fatal``/non-retryable by filing-fetch, while only the
structured ``CatalogOperationLockedError`` mapped to ``catalog_locked``.
This module is the single classification truth: every raw form maps to a
canonical ``(code, retryable)`` pair, unknown forms fail closed to
``fatal`` (never retryable), and the CLI emits the structured shape.

Versioned: ``ERROR_TAXONOMY_VERSION``/``ERROR_TAXONOMY_SCHEMA``; consumers
treat unknown codes as fatal (N/N-1).
"""

from __future__ import annotations

import sqlite3
from typing import Any

ERROR_TAXONOMY_VERSION = "1.0"
ERROR_TAXONOMY_SCHEMA = "error-taxonomy-1.0"

# Canonical codes.  Retryable codes are bounded by the consumer's deadline
# (ZR-205); everything else is fatal and must never be retried.
CATALOG_BUSY = "catalog_busy"  # raw SQLite busy/locked
CATALOG_LOCKED = "catalog_locked"  # operation lock (exclusive writer)
DB_TIMEOUT = "db_timeout"  # sqlite timeout / deadline
WORKER_PAUSED = "worker_paused"  # persistent worker pause
FATAL = "fatal"  # everything else (fail closed)

RETRYABLE_CODES = frozenset({CATALOG_BUSY, CATALOG_LOCKED, DB_TIMEOUT, WORKER_PAUSED})

# Table-driven: (code, marker substrings) per raw text family.  The first
# matching family wins; order encodes precedence (lock > timeout > paused).
_TEXT_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        CATALOG_BUSY,
        ("database is locked", "database is busy", "database table is locked"),
    ),
    (DB_TIMEOUT, ("timeout", "timed out", "deadline exceeded")),
    (WORKER_PAUSED, ("paused", "worker paused", "persistent_pause")),
)

# Exact serialized-type → canonical code (N-1 structured forms).
_STRUCTURED_TYPES: dict[str, str] = {
    "CatalogOperationLockedError": CATALOG_LOCKED,
    "TimeoutError": DB_TIMEOUT,
    "ProgrammingError": DB_TIMEOUT,
}


def _code_for_text(text: str) -> str | None:
    lowered = text.lower()
    for code, markers in _TEXT_FAMILIES:
        if any(marker in lowered for marker in markers):
            return code
    return None


def classify_exception(exc: BaseException) -> tuple[str, bool]:
    """Classify a raised exception into ``(code, retryable)``."""
    exact = _STRUCTURED_TYPES.get(type(exc).__name__)
    if exact is not None:
        return exact, True
    if isinstance(exc, (TimeoutError, sqlite3.ProgrammingError)):
        return DB_TIMEOUT, True
    if isinstance(exc, sqlite3.OperationalError):
        code = _code_for_text(str(exc))
        return (code, True) if code is not None else (FATAL, False)
    code = _code_for_text(str(exc))
    if code == WORKER_PAUSED:
        return code, True
    return FATAL, False


def classify_error_type(error_type: str, error_text: str = "") -> tuple[str, bool]:
    """Classify a serialized ``error_type`` (+ optional error text) —
    the N-1/raw form: unknown types fail closed to fatal."""
    exact = _STRUCTURED_TYPES.get(error_type)
    if exact is not None:
        return exact, True
    if error_type == "OperationalError":
        code = _code_for_text(error_text)
        return (code, True) if code is not None else (FATAL, False)
    if error_type == "RuntimeError":
        code = _code_for_text(error_text)
        if code == WORKER_PAUSED:
            return code, True
    # N/N-1: unknown / arbitrary error types are fatal, never retryable.
    return FATAL, False


def is_retryable(code: str) -> bool:
    return code in RETRYABLE_CODES


def structured_error(exc: BaseException) -> dict[str, Any]:
    """The CLI emission shape: {status, error_type, error, retryable}."""
    code, retryable = classify_exception(exc)
    return {
        "status": "failed",
        "error_type": code,
        "error": str(exc),
        "retryable": retryable,
    }


__all__ = [
    "ERROR_TAXONOMY_VERSION",
    "ERROR_TAXONOMY_SCHEMA",
    "CATALOG_BUSY",
    "CATALOG_LOCKED",
    "DB_TIMEOUT",
    "WORKER_PAUSED",
    "FATAL",
    "RETRYABLE_CODES",
    "classify_exception",
    "classify_error_type",
    "is_retryable",
    "structured_error",
]
