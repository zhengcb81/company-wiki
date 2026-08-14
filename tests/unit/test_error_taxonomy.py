"""ZR-204 gate tests: unified lock/error taxonomy with the
non-lock-never-retryable rule and N/N-1 fail-closed classification."""

from __future__ import annotations

import sqlite3

import pytest

from company_wiki.source_catalog.error_taxonomy import (
    CATALOG_BUSY,
    CATALOG_LOCKED,
    DB_TIMEOUT,
    ERROR_TAXONOMY_SCHEMA,
    ERROR_TAXONOMY_VERSION,
    FATAL,
    WORKER_PAUSED,
    classify_error_type,
    classify_exception,
    is_retryable,
    structured_error,
)
from company_wiki.source_catalog.lock import CatalogOperationLockedError


# ---------------------------------------------------------------------------
# exception-form classification
# ---------------------------------------------------------------------------


def test_operation_lock_is_retryable_catalog_locked() -> None:
    exc = CatalogOperationLockedError("operation lock live")
    assert classify_exception(exc) == (CATALOG_LOCKED, True)


@pytest.mark.parametrize(
    "text", ["database is locked", "database is busy", "database table is locked"]
)
def test_raw_sqlite_lock_forms_map_to_catalog_busy_retryable(text: str) -> None:
    exc = sqlite3.OperationalError(text)
    assert classify_exception(exc) == (CATALOG_BUSY, True)


@pytest.mark.parametrize("text", ["query timed out", "deadline exceeded"])
def test_sqlite_timeout_maps_to_db_timeout_retryable(text: str) -> None:
    exc = sqlite3.OperationalError(text)
    assert classify_exception(exc) == (DB_TIMEOUT, True)


def test_timeout_error_maps_retryable() -> None:
    assert classify_exception(TimeoutError("waiting")) == (DB_TIMEOUT, True)


def test_paused_runtime_error_maps_worker_paused_retryable() -> None:
    exc = RuntimeError("source acquisition is paused; run worker-resume")
    assert classify_exception(exc) == (WORKER_PAUSED, True)


def test_non_lock_errors_are_fatal_not_retryable() -> None:
    for exc in (
        ValueError("bad request"),
        sqlite3.OperationalError("no such table: remediation_proposals"),
        sqlite3.DatabaseError("malformed database image"),
        KeyError("missing"),
        RuntimeError("unhandled worker failure"),
    ):
        code, retryable = classify_exception(exc)
        assert code == FATAL, f"{exc!r} classified {code}"
        assert retryable is False


# ---------------------------------------------------------------------------
# serialized (N-1/raw) classification
# ---------------------------------------------------------------------------


def test_structured_lock_type_retryable() -> None:
    assert classify_error_type("CatalogOperationLockedError") == (CATALOG_LOCKED, True)


def test_raw_operational_error_with_lock_text_retryable() -> None:
    assert classify_error_type("OperationalError", "database is locked") == (
        CATALOG_BUSY,
        True,
    )


def test_unknown_error_type_fails_closed() -> None:
    # N/N-1: an unknown serialized type must be fatal, never retryable.
    code, retryable = classify_error_type("SomeFutureError", "whatever")
    assert code == FATAL and retryable is False


def test_operational_error_without_lock_text_fatal() -> None:
    assert classify_error_type("OperationalError", "no such table: x") == (FATAL, False)


# ---------------------------------------------------------------------------
# emission shape + taxonomy versioning
# ---------------------------------------------------------------------------


def test_structured_error_emission_shape() -> None:
    payload = structured_error(sqlite3.OperationalError("database is locked"))
    assert payload == {
        "status": "failed",
        "error_type": CATALOG_BUSY,
        "error": "database is locked",
        "retryable": True,
    }


def test_taxonomy_versioned_and_retryable_set() -> None:
    assert ERROR_TAXONOMY_VERSION == "1.0"
    assert ERROR_TAXONOMY_SCHEMA == "error-taxonomy-1.0"
    assert is_retryable(CATALOG_BUSY)
    assert is_retryable(CATALOG_LOCKED)
    assert is_retryable(DB_TIMEOUT)
    assert is_retryable(WORKER_PAUSED)
    assert not is_retryable(FATAL)
    assert not is_retryable("unknown")
