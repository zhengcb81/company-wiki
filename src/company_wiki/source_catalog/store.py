"""Single-threaded SQLite catalog for source locations and derived artifacts."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterator, Sequence
import uuid

from .lock import operation_lock_status
from .models import CATALOG_SCHEMA_VERSION, FingerprintStatus, NORMALIZER_VERSION


_NORMALIZER_NAME = "source_catalog_normalizer"
_LLM_SUMMARIZER_NAME = "source_catalog_llm_summary"

# Schema versions that may be upgraded in place to CATALOG_SCHEMA_VERSION.
# Any other recorded value is rejected fail-closed (CW-2.28 §12.3 rule 12).
_UPGRADEABLE_SCHEMA_VERSIONS = frozenset({"1.0.0", "1.1.0"})


def _utc_iso(epoch: float | None = None) -> str:
    """UTC timestamp as a second-precision ISO-8601 string (sortable as text)."""
    if epoch is None:
        epoch = time.time()
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_iso_from(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    text_fingerprint TEXT,
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
CREATE TABLE IF NOT EXISTS source_metadata_assertions (
    assertion_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    entity TEXT,
    market TEXT,
    security_id TEXT,
    document_kind TEXT,
    form_type TEXT,
    fiscal_year INTEGER,
    fiscal_period TEXT,
    provider TEXT,
    provider_document_id TEXT,
    source_url TEXT,
    filing_date TEXT,
    content_sha256 TEXT NOT NULL,
    evidence_basis TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    decision TEXT NOT NULL,
    supersedes_assertion_id TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(source_id),
    FOREIGN KEY(document_id) REFERENCES documents(document_id)
);
CREATE TABLE IF NOT EXISTS document_fingerprint_state (
    document_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'pending',
            'completed',
            'unsupported_terminal',
            'retryable_failed',
            'failed_terminal'
        )
    ),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    terminal_reason TEXT,
    last_error_code TEXT,
    last_error_message_redacted TEXT,
    normalizer_version TEXT NOT NULL,
    last_attempt_at TEXT,
    next_retry_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES documents(document_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE INDEX IF NOT EXISTS idx_fingerprint_state_dispatch
ON document_fingerprint_state(status, next_retry_at, document_id);
CREATE TABLE IF NOT EXISTS document_retire_audit (
    audit_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(document_id) REFERENCES documents(document_id)
);
"""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


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
        "health": {
                "scan": {
                    "latest_running_scan": None,
                    "stale_running_scan": False,
                    "last_completed_scan": None,
                    "recent_interrupted_count": 0,
                    "interrupted_total": 0,
                },
            "locks": {"operation_lock": "absent"},
            "artifacts": {
                "artifact_rows": 0,
                "artifact_index_empty": True,
                "derived_detached_count": 0,
                "reconciliation_needed": False,
            },
        },
        "explanations": {"markdown_pending_reason": "database unavailable"},
        "current": {"stage": "unavailable", "active_documents": 0},
    }


def retire_document(
    store: "CatalogStore", *, document_id: str, reason: str, created_by: str
) -> dict[str, Any]:
    """Soft-delete a document (Phase 15.5): mark the document and its
    locations as ``retired`` and write an audit row with reason/actor/time.
    Nothing is physically deleted, and retired documents are excluded from
    default queries and the resolver."""
    if not document_id or not document_id.strip():
        raise ValueError("document_id must be non-empty text")
    if not reason or not reason.strip():
        raise ValueError("reason must be non-empty text")
    if not created_by or not created_by.strip():
        raise ValueError("created_by must be non-empty text")
    now = _utc_iso()
    audit_id = f"retire-{uuid.uuid4().hex}"
    with store.transaction() as conn:
        row = conn.execute(
            "SELECT document_id FROM documents WHERE document_id=?", (document_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"document not found: {document_id}")
        conn.execute(
            "UPDATE documents SET source_status='retired' WHERE document_id=?",
            (document_id,),
        )
        conn.execute(
            "UPDATE locations SET location_status='retired' WHERE document_id=?",
            (document_id,),
        )
        conn.execute(
            """INSERT INTO document_retire_audit
            (audit_id, document_id, reason, created_by, created_at)
            VALUES(?,?,?,?,?)""",
            (audit_id, document_id, reason, created_by, now),
        )
    return {
        "document_id": document_id,
        "source_status": "retired",
        "audit_id": audit_id,
        "created_at": now,
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
                "physical_locations": _count(
                    connection, "SELECT COUNT(*) FROM locations"
                ),
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
                "upstream_rejected_documents": document_statuses.get(
                    "upstream_rejected", 0
                ),
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
                    latest_llm_failure["document_id"]
                    if latest_llm_failure is not None
                    else None
                ),
            }
            # --- health diagnostics ---
            scan_runs = connection.execute(
                """SELECT run_id,started_at,completed_at,status
                FROM scan_runs ORDER BY started_at DESC LIMIT 20"""
            ).fetchall()
            running_scans = [r for r in scan_runs if r["status"] == "running"]
            interrupted_scans = [r for r in scan_runs if r["status"] == "interrupted"]
            completed_scans = [
                r
                for r in scan_runs
                if r["status"] in {"completed", "completed_with_errors"}
            ]
            interrupted_total = _count(
                connection,
                "SELECT COUNT(*) FROM scan_runs WHERE status='interrupted'",
            )
            stale_running = len(running_scans) > 0 and len(completed_scans) == 0
            # derived dir detection
            derived_dir = database_path.parent.parent / ".source_catalog" / "derived"
            derived_count = 0
            if derived_dir.exists():
                derived_count = sum(1 for _ in derived_dir.rglob("*") if _.is_file())
            artifact_rows = _count(connection, "SELECT COUNT(*) FROM artifacts")
            lock_health = operation_lock_status(database_path.parent)
            health = {
                "scan": {
                    "latest_running_scan": (
                        {
                            "run_id": running_scans[0]["run_id"],
                            "started_at": running_scans[0]["started_at"],
                            "status": running_scans[0]["status"],
                        }
                        if running_scans
                        else None
                    ),
                    "stale_running_scan": stale_running,
                    "last_completed_scan": (
                        {
                            "run_id": completed_scans[0]["run_id"],
                            "started_at": completed_scans[0]["started_at"],
                            "completed_at": completed_scans[0]["completed_at"],
                            "status": completed_scans[0]["status"],
                        }
                        if completed_scans
                        else None
                    ),
                    "recent_interrupted_count": len(interrupted_scans),
                    "interrupted_total": interrupted_total,
                },
                "locks": {
                    "operation_lock": lock_health["state"],
                    "operation_lock_pid": lock_health["pid"],
                    "operation_lock_operation": lock_health["operation"],
                },
                "artifacts": {
                    "artifact_rows": artifact_rows,
                    "artifact_index_empty": artifact_rows == 0,
                    "derived_detached_count": derived_count
                    if artifact_rows == 0
                    else 0,
                    "reconciliation_needed": artifact_rows == 0 and derived_count > 0,
                },
            }
            if artifact_rows > 0:
                pending_reason = ""
            elif derived_count > 0:
                pending_reason = "DB artifact index empty; derived files detached and need reconciliation"
            else:
                pending_reason = "no normalized artifacts yet"
            explanations = {
                "markdown_pending_reason": pending_reason,
            }
            return {
                "schema_version": "1.0",
                "available": True,
                "error": None,
                "last_scan": last_scan,
                "index": index,
                "markdown": markdown,
                "llm_summary": llm_summary,
                "health": health,
                "explanations": explanations,
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
            self._apply_additive_migrations(connection)
            existing = connection.execute(
                "SELECT value FROM catalog_meta WHERE key='schema_version'"
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO catalog_meta(key,value) VALUES('schema_version',?)",
                    (CATALOG_SCHEMA_VERSION,),
                )
            elif existing["value"] != CATALOG_SCHEMA_VERSION:
                raise ValueError("unsupported source catalog schema version")
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _apply_additive_migrations(connection: sqlite3.Connection) -> None:
        """Idempotent additive migrations from prior schema versions (CW-2.28 §12.3).

        Version handling:
          * fresh DB (no recorded version) — additive tables/columns created by
            ``_DDL``; no version bump here (``_initialize`` inserts it);
          * recorded in ``_UPGRADEABLE_SCHEMA_VERSIONS`` (1.0.0, 1.1.0) — run
            additive steps, seed fingerprint state, bump to current;
          * recorded == current — run idempotent additive steps + seed only;
          * any other (unknown/future) version — fail closed BEFORE any data
            write (§12.3 rule 12: zero partial writes).
        """
        existing = connection.execute(
            "SELECT value FROM catalog_meta WHERE key='schema_version'"
        ).fetchone()
        recorded = existing["value"] if existing is not None else None
        known = (
            recorded is None
            or recorded == CATALOG_SCHEMA_VERSION
            or recorded in _UPGRADEABLE_SCHEMA_VERSIONS
        )
        if not known:
            raise ValueError(
                f"unsupported source catalog schema version: {recorded!r} "
                f"(expected fresh, {sorted(_UPGRADEABLE_SCHEMA_VERSIONS)}, "
                f"or {CATALOG_SCHEMA_VERSION})"
            )

        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(documents)")
        }
        if "text_fingerprint" not in columns:
            connection.execute("ALTER TABLE documents ADD COLUMN text_fingerprint TEXT")
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "source_metadata_assertions" not in tables:
            connection.execute("""CREATE TABLE IF NOT EXISTS source_metadata_assertions (
                assertion_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                entity TEXT,
                market TEXT,
                security_id TEXT,
                document_kind TEXT,
                form_type TEXT,
                fiscal_year INTEGER,
                fiscal_period TEXT,
                provider TEXT,
                provider_document_id TEXT,
                source_url TEXT,
                filing_date TEXT,
                content_sha256 TEXT NOT NULL,
                evidence_basis TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                decision TEXT NOT NULL,
                supersedes_assertion_id TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(source_id),
                FOREIGN KEY(document_id) REFERENCES documents(document_id)
            )""")
        if "document_fingerprint_state" not in tables:
            # _DDL normally creates this for fresh DBs; older DBs reach here via
            # executescript(_DDL) too, but keep an explicit guard for safety.
            connection.execute(
                """CREATE TABLE IF NOT EXISTS document_fingerprint_state (
                    document_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('pending','completed','unsupported_terminal',
                                   'retryable_failed','failed_terminal')
                    ),
                    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
                    terminal_reason TEXT,
                    last_error_code TEXT,
                    last_error_message_redacted TEXT,
                    normalizer_version TEXT NOT NULL,
                    last_attempt_at TEXT,
                    next_retry_at TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(document_id),
                    FOREIGN KEY(source_id) REFERENCES sources(source_id)
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_fingerprint_state_dispatch "
                "ON document_fingerprint_state(status, next_retry_at, document_id)"
            )
        if "document_retire_audit" not in tables:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS document_retire_audit (
                    audit_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(document_id)
                )"""
            )

        CatalogStore._seed_fingerprint_state(connection)

        if recorded in _UPGRADEABLE_SCHEMA_VERSIONS:
            connection.execute(
                "UPDATE catalog_meta SET value=? WHERE key='schema_version'",
                (CATALOG_SCHEMA_VERSION,),
            )

    @staticmethod
    def _seed_fingerprint_state(connection: sqlite3.Connection) -> None:
        """Insert a fingerprint-state row for every document lacking one.

        Seed rule (§12.3 rules 2-3): non-NULL fingerprint → ``completed``; NULL
        → ``pending``. Idempotent: documents that already have a state row are
        left untouched. Only documents with a primary source are seeded (a
        document without a primary source has no SHA to bind the state to).
        """
        now = _utc_iso()
        connection.execute(
            """
            INSERT INTO document_fingerprint_state
                (document_id, source_id, source_sha256, status, attempt_count,
                 terminal_reason, last_error_code, last_error_message_redacted,
                 normalizer_version, last_attempt_at, next_retry_at, updated_at)
            SELECT d.document_id, d.primary_source_id, s.content_sha256,
                   CASE WHEN d.text_fingerprint IS NOT NULL THEN 'completed'
                        ELSE 'pending' END,
                   CASE WHEN d.text_fingerprint IS NOT NULL THEN 1 ELSE 0 END,
                   NULL, NULL, NULL, ?,
                   CASE WHEN d.text_fingerprint IS NOT NULL THEN ? ELSE NULL END,
                   NULL, ?
            FROM documents d
            JOIN sources s ON s.source_id = d.primary_source_id
            WHERE NOT EXISTS (
                SELECT 1 FROM document_fingerprint_state st
                WHERE st.document_id = d.document_id
            )
            """,
            (NORMALIZER_VERSION, now, now),
        )

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
            return list(
                self._coalesced_connection.execute(sql, tuple(params)).fetchall()
            )
        connection = self._connect()
        try:
            return list(connection.execute(sql, tuple(params)).fetchall())
        finally:
            connection.close()

    def status(self) -> dict[str, int]:
        connection = self._connect()
        try:
            counts = {
                "sources": connection.execute(
                    "SELECT COUNT(*) FROM sources"
                ).fetchone()[0],
                "documents": connection.execute(
                    "SELECT COUNT(*) FROM documents"
                ).fetchone()[0],
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

    def scan_health(self) -> dict[str, Any]:
        """Return scan-run health diagnostics from the catalog."""
        connection = self._connect()
        connection.row_factory = sqlite3.Row
        try:
            runs = connection.execute(
                "SELECT * FROM scan_runs ORDER BY started_at DESC LIMIT 20"
            ).fetchall()
            latest_running = None
            latest_completed = None
            interrupted_count = 0
            for r in runs:
                if r["status"] == "running" and latest_running is None:
                    latest_running = {
                        "run_id": r["run_id"],
                        "started_at": r["started_at"],
                        "status": "running",
                    }
                if (
                    r["status"] in {"completed", "completed_with_errors"}
                    and latest_completed is None
                ):
                    latest_completed = {
                        "run_id": r["run_id"],
                        "started_at": r["started_at"],
                        "completed_at": r["completed_at"],
                        "status": r["status"],
                    }
                if r["status"] == "interrupted":
                    interrupted_count += 1
            stale_running = (
                latest_running is not None
                and latest_completed is not None
                and (
                    latest_running["started_at"]
                    > latest_completed.get("completed_at", "")
                )
            ) or (latest_running is not None and latest_completed is None)
            return {
                "latest_running_scan": latest_running,
                "last_completed_scan": latest_completed,
                "stale_running_scan": stale_running,
                "recent_interrupted_count": interrupted_count,
                "total_runs": len(runs),
            }
        finally:
            connection.close()

    def artifact_health(self) -> dict[str, Any]:
        """Return artifact health diagnostics."""
        connection = self._connect()
        try:
            artifact_rows = connection.execute(
                "SELECT COUNT(*) FROM artifacts"
            ).fetchone()[0]
            evidence_rows = connection.execute(
                "SELECT COUNT(*) FROM evidence_spans"
            ).fetchone()[0]
            return {
                "artifact_rows": int(artifact_rows),
                "evidence_span_rows": int(evidence_rows),
                "artifact_index_empty": artifact_rows == 0,
            }
        finally:
            connection.close()

    # ------------------------------------------------------------------
    # Fingerprint persistent state (CW-2.28 §12.3)
    # ------------------------------------------------------------------

    def fingerprint_state_counts(self) -> dict[str, int]:
        """Return ``{status: count}`` over all documents with a primary source.

        Documents with no ``document_fingerprint_state`` row yet are counted as
        ``pending`` (§12.3 rule 1: a newly seen document is implicitly pending
        until first processed).
        """
        rows = self.fetchall(
            """
            SELECT COALESCE(st.status, 'pending') AS status, COUNT(*) AS c
            FROM documents d
            LEFT JOIN document_fingerprint_state st ON st.document_id = d.document_id
            WHERE d.primary_source_id IS NOT NULL
            GROUP BY COALESCE(st.status, 'pending')
            """
        )
        return {str(row["status"]): int(row["c"]) for row in rows}

    def select_fingerprint_batch(
        self, *, limit: int | None, now_iso: str
    ) -> list[sqlite3.Row]:
        """Dispatch the next fingerprint batch (§12.3 rule 9).

        Selects documents whose fingerprint state is ``pending`` (including
        documents that have no state row yet — they are implicitly pending) plus
        ``retryable_failed`` rows whose backoff has expired. Terminal and
        completed rows are never re-selected. ``limit=None`` selects the whole
        due backlog.
        """
        if limit is not None and limit <= 0:
            raise ValueError("limit must be positive or None")
        base_sql = """
            SELECT d.document_id, d.primary_source_id AS source_id,
                   s.content_sha256 AS source_sha256,
                   COALESCE(st.attempt_count, 0) AS attempt_count
            FROM documents d
            JOIN sources s ON s.source_id = d.primary_source_id
            LEFT JOIN document_fingerprint_state st ON st.document_id = d.document_id
            WHERE st.document_id IS NULL
               OR st.status='pending'
               OR (st.status='retryable_failed'
                   AND (st.next_retry_at IS NULL OR st.next_retry_at <= ?))
            ORDER BY d.document_id
            """
        if limit is None:
            return self.fetchall(base_sql, (now_iso,))
        return self.fetchall(base_sql + " LIMIT ?", (now_iso, limit))

    def record_fingerprint_outcome(
        self,
        *,
        document_id: str,
        source_id: str,
        source_sha256: str,
        fingerprint: str | None,
        status: str,
        attempt_count: int,
        terminal_reason: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        next_retry_at: str | None = None,
        normalizer_version: str = NORMALIZER_VERSION,
        updated_at: str | None = None,
    ) -> None:
        """Atomically write a fingerprint outcome (§12.3 rule 10).

        Updates ``documents.text_fingerprint`` and upserts the matching
        ``document_fingerprint_state`` row in a single transaction so a crash
        between them cannot leave the two tables inconsistent. The UPSERT also
        covers documents that have no state row yet (newly scanned).
        """
        if status not in FingerprintStatus._value2member_map_:
            raise ValueError(f"invalid fingerprint status: {status!r}")
        stamp = updated_at or _utc_iso()
        with self.transaction() as connection:
            connection.execute(
                "UPDATE documents SET text_fingerprint=? WHERE document_id=?",
                (fingerprint, document_id),
            )
            connection.execute(
                """
                INSERT INTO document_fingerprint_state
                    (document_id, source_id, source_sha256, status, attempt_count,
                     terminal_reason, last_error_code, last_error_message_redacted,
                     normalizer_version, last_attempt_at, next_retry_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    status=excluded.status,
                    attempt_count=excluded.attempt_count,
                    terminal_reason=excluded.terminal_reason,
                    last_error_code=excluded.last_error_code,
                    last_error_message_redacted=excluded.last_error_message_redacted,
                    normalizer_version=excluded.normalizer_version,
                    last_attempt_at=excluded.last_attempt_at,
                    next_retry_at=excluded.next_retry_at,
                    updated_at=excluded.updated_at
                """,
                (
                    document_id,
                    source_id,
                    source_sha256,
                    status,
                    attempt_count,
                    terminal_reason,
                    error_code,
                    _redact_message(error_message),
                    normalizer_version,
                    stamp,
                    next_retry_at,
                    stamp,
                ),
            )

    def fingerprint_status(self, *, now_iso: str) -> dict[str, int]:
        """Return global fingerprint backlog counts for status/UI (§12.3 rule 11)."""
        counts = self.fingerprint_state_counts()
        pending = counts.get("pending", 0)
        completed = counts.get("completed", 0)
        unsupported_terminal = counts.get("unsupported_terminal", 0)
        retryable_failed = counts.get("retryable_failed", 0)
        failed_terminal = counts.get("failed_terminal", 0)
        due_retry_row = self.fetchone(
            """SELECT COUNT(*) AS c FROM document_fingerprint_state
               WHERE status='retryable_failed'
               AND (next_retry_at IS NULL OR next_retry_at <= ?)""",
            (now_iso,),
        )
        due_retry = int(due_retry_row["c"]) if due_retry_row else 0
        terminal = unsupported_terminal + failed_terminal
        return {
            "eligible": pending + due_retry,
            "pending": pending,
            "due_retry": due_retry,
            "completed": completed,
            "terminal": terminal,
            "unsupported_terminal": unsupported_terminal,
            "retryable_failed": retryable_failed,
            "failed_terminal": failed_terminal,
        }


def _redact_message(message: str | None) -> str | None:
    """Truncate and sanitize an error message before persisting it."""
    if not message:
        return None
    truncated = str(message).strip()
    if len(truncated) > 200:
        truncated = truncated[:200]
    return truncated


__all__ = ["CatalogStore", "canonical_json", "read_pipeline_status"]
