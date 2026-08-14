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

_LOCK_TEXT_MARKERS = (
    "database is locked",
    "database is busy",
    "database table is locked",
)
_TIMEOUT_TEXT_MARKERS = ("timeout", "timed out", "deadline exceeded")
_PAUSED_TEXT_MARKERS = ("paused", "worker paused", "persistent_pause")


def classify_exception(exc: BaseException) -> tuple[str, bool]:
    """Classify a raised exception into ``(code, retryable)``."""
    name = type(exc).__name__
    if name == "CatalogOperationLockedError":
        return CATALOG_LOCKED, True
    if isinstance(exc, sqlite3.OperationalError):
        text = str(exc).lower()
        if any(marker in text for marker in _LOCK_TEXT_MARKERS):
            return CATALOG_BUSY, True
        if any(marker in text for marker in _TIMEOUT_TEXT_MARKERS):
            return DB_TIMEOUT, True
        return FATAL, False
    if isinstance(exc, (TimeoutError, sqlite3.ProgrammingError)):
        return DB_TIMEOUT, True
    text = str(exc).lower()
    if any(marker in text for marker in _PAUSED_TEXT_MARKERS):
        return WORKER_PAUSED, True
    return FATAL, False


def classify_error_type(error_type: str, error_text: str = "") -> tuple[str, bool]:
    """Classify a serialized ``error_type`` (+ optional error text) —
    the N-1/raw form: unknown types fail closed to fatal."""
    if error_type == "CatalogOperationLockedError":
        return CATALOG_LOCKED, True
    if error_type == "OperationalError":
        text = (error_text or "").lower()
        if any(marker in text for marker in _LOCK_TEXT_MARKERS):
            return CATALOG_BUSY, True
        if any(marker in text for marker in _TIMEOUT_TEXT_MARKERS):
            return DB_TIMEOUT, True
        return FATAL, False
    if error_type in {"TimeoutError", "ProgrammingError"}:
        return DB_TIMEOUT, True
    if error_type == "RuntimeError" and any(
        marker in (error_text or "").lower() for marker in _PAUSED_TEXT_MARKERS
    ):
        return WORKER_PAUSED, True
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
