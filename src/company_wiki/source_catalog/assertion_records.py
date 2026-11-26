"""SQLite persistence for append-only source assertions and their projection."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import sqlite3
from typing import Any, Protocol


class _Query(Protocol):
    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None: ...
    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]: ...


def _visibility(
    reader: str, current_epoch: str | None, active_cohorts: tuple[str, ...],
) -> tuple[str, tuple[Any, ...]]:
    if reader == "v1":
        return "visibility_state='legacy'", ()
    if reader == "steady":
        return "visibility_state IN ('legacy','active')", ()
    if reader == "v2":
        if not current_epoch or not active_cohorts:
            return "1=0", ()
        marks = ",".join("?" for _ in active_cohorts)
        return f"visibility_state='active' AND activation_epoch=? AND cohort IN ({marks})", (
            current_epoch, *active_cohorts,
        )
    raise ValueError(f"unknown reader {reader!r}")


class AssertionRecords:
    """Named read queries for both read-only and active transaction views."""

    def __init__(self, query: _Query) -> None:
        self._query = query

    def visible_verified(
        self, identity: str, *, by_document: bool, reader: str,
        current_epoch: str | None, active_cohorts: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        column = "document_id" if by_document else "source_id"
        visibility, extra = _visibility(reader, current_epoch, active_cohorts)
        rows = self._query.fetchall(
            f"""SELECT * FROM source_metadata_assertions
            WHERE {column}=? AND decision='verified' AND {visibility} ORDER BY created_at DESC""",
            (identity, *extra),
        )
        return [dict(row) for row in rows]

    def find(self, assertion_id: str) -> dict[str, Any] | None:
        row = self._query.fetchone(
            "SELECT * FROM source_metadata_assertions WHERE assertion_id=?", (assertion_id,),
        )
        return dict(row) if row is not None else None

    def verified_for_version(self, source_id: str, document_id: str, content_sha256: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self._query.fetchall(
            """SELECT * FROM source_metadata_assertions
            WHERE source_id=? AND document_id=? AND content_sha256=? AND decision='verified'
            ORDER BY created_at DESC""", (source_id, document_id, content_sha256),
        )]

    def decision_exists_for(self, assertion_id: str) -> bool:
        return self._query.fetchone(
            """SELECT 1 FROM source_metadata_assertions
            WHERE supersedes_assertion_id=? AND decision IN ('verified','rejected')""", (assertion_id,),
        ) is not None

    def find_normalized(
        self, source_id: str, content_sha256: str, adapter_id: str, adapter_version: str, metadata_hash: str,
    ) -> dict[str, Any] | None:
        row = self._query.fetchone(
            """SELECT * FROM source_metadata_assertions WHERE source_id=? AND content_sha256=?
            AND adapter_id=? AND adapter_version=? AND normalized_sha256=? AND decision='verified'
            ORDER BY created_at DESC LIMIT 1""",
            (source_id, content_sha256, adapter_id, adapter_version, metadata_hash),
        )
        return dict(row) if row is not None else None


def current_fact_record(
    connection: sqlite3.Connection, *, document_id: str, source_id: str | None,
) -> sqlite3.Row | None:
    if not source_id:
        return None
    return connection.execute(
        """SELECT a.evidence_basis,a.evidence_json FROM source_metadata_assertions a
        JOIN sources s ON s.source_id=a.source_id AND s.content_sha256=a.content_sha256
        WHERE a.document_id=? AND a.source_id=? AND a.decision='verified'
          AND a.visibility_state IN ('legacy','active')
        ORDER BY a.created_at DESC LIMIT 1""", (document_id, source_id),
    ).fetchone()


_ASSERTION_COLUMNS = frozenset({
    "assertion_id", "source_id", "document_id", "entity", "market", "security_id", "document_kind",
    "form_type", "fiscal_year", "fiscal_period", "period_end", "provider", "provider_document_id",
    "source_url", "filing_date", "content_sha256", "evidence_basis", "evidence_json", "decision",
    "supersedes_assertion_id", "created_at", "created_by", "schema_version", "published_at", "language",
    "adapter_id", "adapter_version", "normalized_sha256", "normalization_status", "visibility_state",
})
_PROJECTED_FIELDS = frozenset({"document_kind", "source_type", "published_date", "title"})


class FactWriteTransaction:
    """Only the storage owner can mutate the assertion, document and location tables."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def append_assertion(self, row: Mapping[str, Any]) -> None:
        if row.keys() - _ASSERTION_COLUMNS:
            raise ValueError("unknown source assertion storage field")
        columns = tuple(row)
        marks = ",".join("?" for _ in columns)
        self._connection.execute(
            f"INSERT INTO source_metadata_assertions ({','.join(columns)}) VALUES ({marks})",
            tuple(row[column] for column in columns),
        )

    def append_projection(
        self, document_id: str, assertion: Mapping[str, Any], projection: Mapping[str, Any],
    ) -> None:
        self.append_assertion(assertion)
        if not projection:
            return
        if projection.keys() - _PROJECTED_FIELDS:
            raise ValueError("unknown source fact projection field")
        assignment = ",".join(f"{field}=?" for field in projection)
        self._connection.execute(
            f"UPDATE documents SET {assignment} WHERE document_id=?", (*projection.values(), document_id),
        )

    def restore_verified_locations(
        self, document_id: str, source_id: str, location_ids: Sequence[str], *,
        audit_id: str, created_at: str,
    ) -> None:
        self._connection.execute("UPDATE documents SET source_status='active' WHERE document_id=?", (document_id,))
        self._connection.executemany(
            "UPDATE locations SET location_status='active' WHERE location_id=? AND source_id=? AND location_status='retired'",
            [(location_id, source_id) for location_id in location_ids],
        )
        self._connection.execute(
            """INSERT INTO document_restore_audit(audit_id,document_id,reason,created_by,created_at)
            VALUES(?,?,?,'automated-local-reconcile',?)""",
            (audit_id, document_id, "verified local original and corrected source facts; prior retirement audits retained",
             created_at),
        )
