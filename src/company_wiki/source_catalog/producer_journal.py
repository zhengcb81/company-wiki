"""ZR-304: producer attempt/result journal (append-only).

Closes the failure-evidence gap: the artifact INSERT trigger
(``trg_artifact_producer_event``) only records SUCCESSFUL producers that
created an artifact — a parser/LLM run that fails without producing an
artifact leaves zero evidence.  This module adds an independent append-only
``producer_attempts`` table:

- ``record_attempt`` — records a producer attempt/result with an explicit
  outcome (succeeded|failed) and an optional request_id.  A FAILED attempt
  is recorded even when no artifact exists.  A SUCCESSFUL producer gets
  BOTH the attempt row and its artifact-trigger event in ``producer_events``
  (complementary, both append-only; the existing trigger is untouched).
- ``attempts_for`` / ``calls_this_request`` — read attempts; the
  request-scoped count separates THIS request's calls from history
  (historical events have request_id NULL and are never counted).
"""

from __future__ import annotations

import uuid
from typing import Any

ATTEMPT_OUTCOMES = frozenset({"succeeded", "failed"})

PRODUCER_ATTEMPTS_DDL = """
CREATE TABLE IF NOT EXISTS producer_attempts (
    attempt_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    artifact_role TEXT NOT NULL,
    producer_name TEXT NOT NULL,
    producer_version TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('succeeded', 'failed')),
    request_id TEXT,
    created_at TEXT NOT NULL
    -- No FK on document_id: append-only history must never block
    -- document cleanup (same policy as producer_events).
);
CREATE INDEX IF NOT EXISTS idx_producer_attempts_document
    ON producer_attempts(document_id, request_id);
"""


class ProducerJournalError(ValueError):
    """Raised on invalid attempt records (fail closed)."""


def _nonempty(value: str | None, field: str) -> str:
    if not value or not value.strip():
        raise ProducerJournalError(f"{field} must be non-empty")
    return value


def _validate_attempt_inputs(
    *,
    document_id: str,
    producer_name: str,
    producer_version: str,
    outcome: str,
    artifact_role: str,
    created_at: str,
) -> None:
    """Fail-closed validation shared by the attempt writer."""
    _nonempty(document_id, "document_id")
    _nonempty(producer_name, "producer_name")
    _nonempty(producer_version, "producer_version")
    _nonempty(artifact_role, "artifact_role")
    _nonempty(created_at, "created_at")
    if outcome not in ATTEMPT_OUTCOMES:
        raise ProducerJournalError(
            f"outcome must be one of {sorted(ATTEMPT_OUTCOMES)}, got {outcome!r}")


def record_attempt(
    connection: Any,
    document_id: str,
    *,
    producer_name: str,
    producer_version: str,
    outcome: str,
    artifact_role: str,
    created_at: str,
    request_id: str | None = None,
) -> dict[str, str]:
    """Append one producer attempt/result row to ``producer_attempts``.

    ``connection`` must be a sqlite3.Connection (caller owns commit).
    Validates fail-closed: non-empty document/producer/role, outcome enum,
    non-empty created_at.  ``request_id`` distinguishes this request's
    calls from history (None = historical event).  A FAILED attempt is
    recorded even though no artifact was created — the journal is the only
    evidence of the call.
    """
    _validate_attempt_inputs(
        document_id=document_id,
        producer_name=producer_name,
        producer_version=producer_version,
        outcome=outcome,
        artifact_role=artifact_role,
        created_at=created_at,
    )
    attempt_id = f"pa-{uuid.uuid4().hex}"
    connection.execute(
        "INSERT INTO producer_attempts(attempt_id, document_id, artifact_role, "
        "producer_name, producer_version, outcome, request_id, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            attempt_id, document_id, artifact_role, producer_name,
            producer_version, outcome, request_id, created_at,
        ),
    )
    return {
        "attempt_id": attempt_id,
        "document_id": document_id,
        "artifact_role": artifact_role,
        "producer_name": producer_name,
        "producer_version": producer_version,
        "outcome": outcome,
        "request_id": request_id or "",
        "created_at": created_at,
    }


def attempts_for(
    store: Any,
    document_id: str,
    *,
    request_id: str | None = None,
) -> list[dict[str, Any]]:
    """Read attempt rows for the document (optionally one request)."""
    if request_id is None:
        rows = store.fetchall(
            "SELECT * FROM producer_attempts WHERE document_id=? "
            "ORDER BY created_at, attempt_id",
            (document_id,),
        )
    else:
        rows = store.fetchall(
            "SELECT * FROM producer_attempts WHERE document_id=? "
            "AND request_id=? ORDER BY created_at, attempt_id",
            (document_id, request_id),
        )
    return [dict(row) for row in rows]


def calls_this_request(
    store: Any,
    document_id: str,
    request_id: str,
) -> dict[str, int]:
    """Exact producer call counts for THIS request (not history).

    Counts attempt rows tagged with the request_id, by outcome.  Zero is
    honest (no attempt recorded for this request), never an absence claim.
    """
    rows = store.fetchall(
        "SELECT outcome, COUNT(*) AS n FROM producer_attempts "
        "WHERE document_id=? AND request_id=? GROUP BY outcome",
        (document_id, request_id),
    )
    counts = {outcome: 0 for outcome in ATTEMPT_OUTCOMES}
    for row in rows:
        outcome = str(row["outcome"])
        if outcome in counts:
            counts[outcome] = int(row["n"])
    return counts


__all__ = [
    "ATTEMPT_OUTCOMES",
    "PRODUCER_ATTEMPTS_DDL",
    "ProducerJournalError",
    "attempts_for",
    "calls_this_request",
    "record_attempt",
]
