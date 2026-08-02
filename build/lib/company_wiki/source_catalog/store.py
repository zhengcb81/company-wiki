"""Single-threaded SQLite catalog for source locations and derived artifacts."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterator, Sequence

from .models import CATALOG_SCHEMA_VERSION, NORMALIZER_VERSION


_NORMALIZER_NAME = "source_catalog_normalizer"
_LLM_SUMMARIZER_NAME = "source_catalog_llm_summary"


_DDL = """
CREATE TABLE IF NOT EXISTS catalog_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scan_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    report_json TEXT
);
CREATE TABLE IF NOT EXISTS roots (
    root_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    priority INTEGER NOT NULL,
    last_scan_run TEXT,
    last_scanned_at TEXT
);
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    content_sha256 TEXT NOT NULL UNIQUE,
    byte_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    first_seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    primary_source_id TEXT,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL,
    document_kind TEXT NOT NULL,
    published_date TEXT,
    source_status TEXT NOT NULL,
    metadata_priority INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    FOREIGN KEY(primary_source_id) REFERENCES sources(source_id)
);
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS document_entities (
    document_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    confidence REAL NOT NULL,
    method TEXT NOT NULL,
    PRIMARY KEY(document_id, entity_id),
    FOREIGN KEY(document_id) REFERENCES documents(document_id),
    FOREIGN KEY(entity_id) REFERENCES entities(entity_id)
);
CREATE TABLE IF NOT EXISTS locations (
    location_id TEXT PRIMARY KEY,
    root_id TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    absolute_path TEXT NOT NULL,
    source_id TEXT,
    document_id TEXT,
    role TEXT NOT NULL,
    location_status TEXT NOT NULL,
    observed_size INTEGER,
    observed_mtime_ns INTEGER,
    last_seen_run TEXT NOT NULL,
    manifest_json TEXT,
    metadata_json TEXT NOT NULL,
    error TEXT,
    UNIQUE(root_id, relative_path),
    FOREIGN KEY(root_id) REFERENCES roots(root_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id),
    FOREIGN KEY(document_id) REFERENCES documents(document_id)
);
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    source_id TEXT,
    artifact_role TEXT NOT NULL,
    path TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    generator_name TEXT NOT NULL,
    generator_version TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    metadata_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(document_id, artifact_role, generator_name, generator_version),
    FOREIGN KEY(document_id) REFERENCES documents(document_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE TABLE IF NOT EXISTS llm_summary_failures (
    document_id TEXT NOT NULL,
    generator_name TEXT NOT NULL,
    generator_version TEXT NOT NULL,
    failure_scope TEXT NOT NULL,
    error TEXT NOT NULL,
    attempt_count INTEGER NOT NULL,
    retry_after REAL NOT NULL,
    first_failed_at REAL NOT NULL,
    last_failed_at REAL NOT NULL,
    PRIMARY KEY(document_id, generator_name, generator_version),
    FOREIGN KEY(document_id) REFERENCES documents(document_id)
);
CREATE TABLE IF NOT EXISTS evidence_spans (
    span_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    locator TEXT NOT NULL,
    page_number INTEGER,
    paragraph_index INTEGER,
    table_index INTEGER,
    raw_text TEXT,
    span_json TEXT NOT NULL,
    parser_name TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    parse_status TEXT NOT NULL,
    UNIQUE(source_id, locator),
    FOREIGN KEY(document_id) REFERENCES documents(document_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE INDEX IF NOT EXISTS idx_locations_source ON locations(source_id);
CREATE INDEX IF NOT EXISTS idx_locations_document ON locations(document_id);
CREATE INDEX IF NOT EXISTS idx_locations_status ON locations(location_status);
CREATE INDEX IF NOT EXISTS idx_documents_kind ON documents(document_kind);
CREATE INDEX IF NOT EXISTS idx_artifacts_document ON artifacts(document_id);
CREATE INDEX IF NOT EXISTS idx_llm_summary_failures_retry
ON llm_summary_failures(generator_name, generator_version, retry_after);
CREATE INDEX IF NOT EXISTS idx_spans_document ON evidence_spans(document_id);
"""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _empty_pipeline_status(*, error: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "available": False,
        "error": error,
        "last_scan": None,
        "index": {
            "physical_locations": 0,
            "active_locations": 0,
            "missing_locations": 0,
            "quarantined_locations": 0,
            "unique_sources": 0,
            "documents": 0,
            "active_documents": 0,
            "incomplete_documents": 0,
            "quarantined_documents": 0,
            "upstream_rejected_documents": 0,
            "duplicate_copies": 0,
            "unlinked_active_locations": 0,
        },
        "markdown": {
            "eligible": 0,
            "pending": 0,
            "blocked": 0,
            "in_progress": 0,
            "completed": 0,
            "partial": 0,
            "unsupported": 0,
            "failed": 0,
        },
        "llm_summary": {
            "eligible": 0,
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "partial": 0,
            "failed": 0,
            "deferred": False,
            "next_document_retry_after": None,
            "last_failed_document_id": None,
        },
        "current": {"stage": "unavailable", "active_documents": 0},
    }


def _count(connection: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> int:
    return int(connection.execute(sql, tuple(params)).fetchone()[0])


def read_pipeline_status(database_path: Path) -> dict[str, Any]:
    """Read pipeline inventory without creating or mutating a catalog database."""

    if not isinstance(database_path, Path):
        raise TypeError("database_path must be pathlib.Path")
    if not database_path.is_file():
        return _empty_pipeline_status()
    try:
        connection = sqlite3.connect(
            database_path.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=5.0,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        try:
            latest = connection.execute(
                """SELECT run_id,started_at,completed_at,status,report_json
                FROM scan_runs WHERE completed_at IS NOT NULL
                ORDER BY started_at DESC LIMIT 1"""
            ).fetchone()
            last_scan: dict[str, Any] | None = None
            if latest is not None:
                report = json.loads(latest["report_json"] or "{}")
                last_scan = {
                    "run_id": latest["run_id"],
                    "started_at": latest["started_at"],
                    "completed_at": latest["completed_at"],
                    "status": latest["status"],
                    **report,
                    "new_sources": _count(
                        connection,
                        "SELECT COUNT(*) FROM sources WHERE first_seen_at>=? AND first_seen_at<=?",
                        (latest["started_at"], latest["completed_at"]),
                    ),
                    "new_documents": _count(
                        connection,
                        "SELECT COUNT(*) FROM documents WHERE first_seen_at>=? AND first_seen_at<=?",
                        (latest["started_at"], latest["completed_at"]),
                    ),
                }

            active_linked = _count(
                connection,
                """SELECT COUNT(*) FROM locations
                WHERE location_status='active' AND source_id IS NOT NULL""",
            )
            active_unique_sources = _count(
                connection,
                """SELECT COUNT(DISTINCT source_id) FROM locations
                WHERE location_status='active' AND source_id IS NOT NULL""",
            )
            document_statuses = {
                row["source_status"]: int(row["count"])
                for row in connection.execute(
                    "SELECT source_status,COUNT(*) AS count FROM documents GROUP BY source_status"
                )
            }
            index = {
                "physical_locations": _count(connection, "SELECT COUNT(*) FROM locations"),
                "active_locations": _count(
                    connection,
                    "SELECT COUNT(*) FROM locations WHERE location_status='active'",
                ),
                "missing_locations": _count(
                    connection,
                    "SELECT COUNT(*) FROM locations WHERE location_status='missing'",
                ),
                "quarantined_locations": _count(
                    connection,
                    "SELECT COUNT(*) FROM locations WHERE location_status='quarantined'",
                ),
                "unique_sources": _count(connection, "SELECT COUNT(*) FROM sources"),
                "documents": _count(connection, "SELECT COUNT(*) FROM documents"),
                "active_documents": document_statuses.get("active", 0),
                "incomplete_documents": document_statuses.get("incomplete", 0),
                "quarantined_documents": document_statuses.get("quarantined", 0),
                "upstream_rejected_documents": document_statuses.get("upstream_rejected", 0),
                "duplicate_copies": max(0, active_linked - active_unique_sources),
                "unlinked_active_locations": _count(
                    connection,
                    """SELECT COUNT(*) FROM locations
                    WHERE location_status='active' AND document_id IS NULL""",
                ),
            }

            markdown_statuses = {
                row["status"]: int(row["count"])
                for row in connection.execute(
                    """SELECT status,COUNT(*) AS count FROM artifacts
                    WHERE artifact_role='normalized' AND generator_name=?
                    AND generator_version=? GROUP BY status""",
                    (_NORMALIZER_NAME, NORMALIZER_VERSION),
                )
            }
            markdown_eligible = _count(
                connection,
                """SELECT COUNT(*) FROM documents d
                JOIN sources s ON s.source_id=d.primary_source_id""",
            )
            markdown = {
                "eligible": markdown_eligible,
                "pending": _count(
                    connection,
                    """SELECT COUNT(*) FROM documents d
                    JOIN sources s ON s.source_id=d.primary_source_id
                    WHERE NOT EXISTS (
                        SELECT 1 FROM artifacts existing
                        WHERE existing.document_id=d.document_id
                        AND existing.artifact_role='normalized'
                        AND existing.generator_name=? AND existing.generator_version=?
                    )""",
                    (_NORMALIZER_NAME, NORMALIZER_VERSION),
                ),
                "blocked": max(0, index["documents"] - markdown_eligible),
                "in_progress": 0,
                "completed": markdown_statuses.get("completed", 0),
                "partial": markdown_statuses.get("partial", 0),
                "unsupported": markdown_statuses.get("unsupported", 0),
                "failed": markdown_statuses.get("failed", 0),
            }

            llm_statuses = {
                row["status"]: int(row["count"])
                for row in connection.execute(
                    """SELECT status,COUNT(*) AS count FROM artifacts
                    WHERE artifact_role='summary' AND generator_name=? GROUP BY status""",
                    (_LLM_SUMMARIZER_NAME,),
                )
            }
            status_now = time.time()
            llm_failure = connection.execute(
                """SELECT COUNT(*) AS count,MIN(retry_after) AS next_retry_after
                FROM llm_summary_failures
                WHERE generator_name=? AND retry_after>?""",
                (_LLM_SUMMARIZER_NAME, status_now),
            ).fetchone()
            latest_llm_failure = connection.execute(
                """SELECT document_id FROM llm_summary_failures
                WHERE generator_name=? AND retry_after>?
                ORDER BY last_failed_at DESC LIMIT 1""",
                (_LLM_SUMMARIZER_NAME, status_now),
            ).fetchone()
            llm_summary = {
                "eligible": _count(
                    connection,
                    """SELECT COUNT(DISTINCT d.document_id) FROM documents d
                    JOIN artifacts a ON a.document_id=d.document_id
                    WHERE a.artifact_role='normalized'""",
                ),
                "pending": _count(
                    connection,
                    """SELECT COUNT(DISTINCT d.document_id) FROM documents d
                    JOIN artifacts a ON a.document_id=d.document_id
                    WHERE a.artifact_role='normalized' AND NOT EXISTS (
                        SELECT 1 FROM artifacts existing
                        WHERE existing.document_id=d.document_id
                        AND existing.artifact_role='summary'
                        AND existing.generator_name=?
                    ) AND NOT EXISTS (
                        SELECT 1 FROM llm_summary_failures failure
                        WHERE failure.document_id=d.document_id
                        AND failure.generator_name=? AND failure.retry_after>?
                    )""",
                    (_LLM_SUMMARIZER_NAME, _LLM_SUMMARIZER_NAME, status_now),
                ),
                "in_progress": 0,
                "completed": llm_statuses.get("completed", 0),
                "partial": llm_statuses.get("partial", 0),
                "failed": int(llm_failure["count"]),
                "deferred": False,
                "next_document_retry_after": llm_failure["next_retry_after"],
                "last_failed_document_id": (
                    latest_llm_failure["document_id"] if latest_llm_failure is not None else None
                ),
            }
            return {
                "schema_version": "1.0",
                "available": True,
                "error": None,
                "last_scan": last_scan,
                "index": index,
                "markdown": markdown,
                "llm_summary": llm_summary,
                "current": {"stage": "idle", "active_documents": 0},
            }
        finally:
            connection.close()
    except (OSError, sqlite3.Error, json.JSONDecodeError, ValueError) as exc:
        return _empty_pipeline_status(error=f"{type(exc).__name__}: {str(exc)[:500]}")


class CatalogStore:
    def __init__(self, database_path: Path):
        if not isinstance(database_path, Path):
            raise TypeError("database_path must be pathlib.Path")
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._coalesced_connection: sqlite3.Connection | None = None
        self._coalesced_operations = 0
        self._coalesced_max_operations = 0
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        if self._coalesced_connection is not None:
            connection = self._coalesced_connection
            try:
                yield connection
            except Exception:
                connection.rollback()
                connection.execute("BEGIN IMMEDIATE")
                self._coalesced_operations = 0
                raise
            else:
                self._coalesced_operations += 1
                if self._coalesced_operations >= self._coalesced_max_operations:
                    connection.commit()
                    connection.execute("BEGIN IMMEDIATE")
                    self._coalesced_operations = 0
            return
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def coalesced_transactions(self, *, max_operations: int = 250) -> Iterator[None]:
        """Reuse one connection and durably commit every bounded operation group."""
        if max_operations <= 0:
            raise ValueError("max_operations must be positive")
        if self._coalesced_connection is not None:
            raise RuntimeError("coalesced transaction scope is already active")
        connection = self._connect()
        self._coalesced_connection = connection
        self._coalesced_operations = 0
        self._coalesced_max_operations = max_operations
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            self._coalesced_connection = None
            self._coalesced_operations = 0
            self._coalesced_max_operations = 0
            connection.close()

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(_DDL)
            existing = connection.execute(
                "SELECT value FROM catalog_meta WHERE key='schema_version'"
            ).fetchone()
            if existing is not None and existing["value"] != CATALOG_SCHEMA_VERSION:
                raise ValueError("unsupported source catalog schema version")
            connection.execute(
                "INSERT OR IGNORE INTO catalog_meta(key,value) VALUES('schema_version',?)",
                (CATALOG_SCHEMA_VERSION,),
            )
            connection.commit()
        finally:
            connection.close()

    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        if self._coalesced_connection is not None:
            return self._coalesced_connection.execute(sql, tuple(params)).fetchone()
        connection = self._connect()
        try:
            return connection.execute(sql, tuple(params)).fetchone()
        finally:
            connection.close()

    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        if self._coalesced_connection is not None:
            return list(self._coalesced_connection.execute(sql, tuple(params)).fetchall())
        connection = self._connect()
        try:
            return list(connection.execute(sql, tuple(params)).fetchall())
        finally:
            connection.close()

    def status(self) -> dict[str, int]:
        connection = self._connect()
        try:
            counts = {
                "sources": connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
                "documents": connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
                "active_locations": connection.execute(
                    "SELECT COUNT(*) FROM locations WHERE location_status='active'"
                ).fetchone()[0],
                "missing_locations": connection.execute(
                    "SELECT COUNT(*) FROM locations WHERE location_status='missing'"
                ).fetchone()[0],
                "normalized_artifacts": connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE artifact_role='normalized'"
                ).fetchone()[0],
                "summary_artifacts": connection.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE artifact_role='summary'"
                ).fetchone()[0],
                "llm_summary_artifacts": connection.execute(
                    """SELECT COUNT(*) FROM artifacts WHERE artifact_role='summary'
                    AND generator_name='source_catalog_llm_summary'"""
                ).fetchone()[0],
                "evidence_spans": connection.execute(
                    "SELECT COUNT(*) FROM evidence_spans"
                ).fetchone()[0],
            }
            return {key: int(value) for key, value in counts.items()}
        finally:
            connection.close()


__all__ = ["CatalogStore", "canonical_json", "read_pipeline_status"]
