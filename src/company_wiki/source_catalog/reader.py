"""ZR-201 + ZR-202: zero-write ``CatalogReader`` with typed read queries.

The production read model's counterexample (replayed in ZR-001, W1):
``CatalogStore.__init__`` on a nonexistent path creates a full writable
database — mkdir, ``PRAGMA journal_mode=WAL``, DDL, additive migrations,
seed and commit — and on an OS-read-only file it crashes with
``attempt to write a readonly database``.

This module defines the fix surface:

- ``CatalogReader`` — a Protocol that exposes ONLY read methods; the type
  level has no execute/commit/migrate/seed/DDL entry points.
- ``ReadOnlyCatalogReader`` — the real implementation:
  * a nonexistent database path raises ``CatalogReaderUnavailable`` and
    leaves the filesystem byte-identical (no file, no parent dirs);
  * opens ``file:...?mode=ro`` + ``PRAGMA query_only=ON`` immediately;
  * never issues journal_mode/WAL/DDL/migrations/seeds/commits;
  * works on an OS-read-only database file.
- ZR-202 typed read queries on the same reader: ``document``,
  ``source_sha``, ``artifacts_for``, ``location_counts``, ``status``,
  ``scan_health``, ``query``, ``entities_like`` (identify), ``resolve_handle``,
  ``bundle`` and ``health`` — schema mismatch fails closed, and
  ``query_only`` is exposed as a property that is always True.

Wiring the production read paths onto this reader is ZR-203; this module
only defines the protocol, the factory and the typed query layer, and
changes nothing else.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Protocol, Sequence, runtime_checkable

from .models import CATALOG_SCHEMA_VERSION

SUPPORTED_SCHEMA_VERSIONS = frozenset({CATALOG_SCHEMA_VERSION})


class CatalogReaderUnavailable(RuntimeError):
    """The read-only catalog could not be opened (missing/unopenable) or its
    schema version is unsupported (fail closed)."""


@runtime_checkable
class CatalogReader(Protocol):
    """Read-only catalog surface.  No write entry points exist on this
    protocol: implementers that also expose execute/commit/DDL simply have
    MORE surface than the protocol — the protocol itself cannot write."""

    @property
    def query_only(self) -> bool:
        """True: the connection is ``PRAGMA query_only=ON`` (always True)."""
        ...

    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        """Run a SELECT and return the first row (None when no rows)."""
        ...

    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        """Run a SELECT and return all rows."""
        ...

    def schema_version(self) -> str:
        """Read the recorded catalog schema version (catalog_meta)."""
        ...

    def document(self, document_id: str) -> sqlite3.Row | None:
        """Typed: one documents row by id."""
        ...

    def source_sha(self, source_id: str) -> str | None:
        """Typed: content_sha256 for a source id."""
        ...

    def artifacts_for(self, document_id: str) -> list[sqlite3.Row]:
        """Typed: artifacts for a document, ordered by role/created_at/id."""
        ...

    def location_counts(self, root_id: str) -> dict[str, int]:
        """Typed: location counts by location_status for a root."""
        ...

    def status(self) -> dict[str, int]:
        """Typed: catalog aggregate counts (8 counters)."""
        ...

    def scan_health(self) -> dict[str, Any]:
        """Typed: latest scan-run statuses + interrupted count."""
        ...

    def query(
        self,
        *,
        text: str | None = None,
        document_kind: str | None = None,
        source_status: str = "active",
        limit: int = 100,
    ) -> list[sqlite3.Row]:
        """Typed: filtered document listing (read-only)."""
        ...

    def entities_like(self, name: str, limit: int = 20) -> list[sqlite3.Row]:
        """Typed: entities whose name matches (identify helper)."""
        ...

    def resolve_handle(
        self,
        document_id: str,
        *,
        expected_content_sha256: str | None = None,
    ) -> dict[str, Any] | None:
        """Typed: read-only resolve shape — document + source sha, fail
        closed (None) when the claimed hash drifts or the document is
        unknown."""
        ...

    def bundle(
        self,
        document_id: str,
        *,
        registry: dict[str, set[str]],
        allowed_roots: tuple[Path, ...],
        now: str,
        expected_content_sha256: str | None = None,
    ) -> dict[str, Any] | None:
        """Typed: read-only SourceBundle assembly (fail closed on drift)."""
        ...

    def health(self) -> dict[str, Any]:
        """Typed: schema_version + status + scan_health + query_only."""
        ...

    def close(self) -> None:
        """Release the read-only connection."""
        ...

    def __enter__(self) -> "CatalogReader": ...

    def __exit__(self, *exc: object) -> None: ...


class ReadOnlyCatalogReader:
    """A CatalogReader over an existing SQLite catalog, opened strictly
    read-only.  Constructing on a nonexistent path fails WITHOUT creating
    anything; constructing on an OS-read-only file succeeds.

    Note (SQLite read protocol): opening a WAL-mode database read-only may
    let SQLite create EMPTY ``-wal``/``-shm`` side files when they are
    absent — the reader itself never issues journal_mode/DDL/migrations/
    seeds/commits and the data file stays byte-identical.  On the live
    catalog those side files already exist (the writer maintains them), so
    no filesystem change occurs in production use.
    """

    def __init__(self, database_path: Path):
        if not isinstance(database_path, Path):
            raise TypeError("database_path must be pathlib.Path")
        self.database_path = database_path
        if not database_path.exists():
            raise CatalogReaderUnavailable(
                f"catalog does not exist (not created, not touched): {database_path}"
            )
        uri = f"file:{database_path.resolve().as_posix()}?mode=ro"
        try:
            self._connection = sqlite3.connect(uri, uri=True, timeout=5.0)
        except sqlite3.Error as exc:
            raise CatalogReaderUnavailable(
                f"cannot open catalog read-only: {database_path}: {exc}"
            ) from exc
        self._connection.row_factory = sqlite3.Row
        # The connection can only ever read; a write attempt raises
        # sqlite3.OperationalError('attempt to write a readonly database').
        self._connection.execute("PRAGMA query_only=ON")

    @property
    def query_only(self) -> bool:
        return True

    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        return self._connection.execute(sql, tuple(params)).fetchone()

    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        return list(self._connection.execute(sql, tuple(params)).fetchall())

    def schema_version(self) -> str:
        row = self.fetchone("SELECT value FROM catalog_meta WHERE key='schema_version'")
        if row is None:
            raise CatalogReaderUnavailable(
                "catalog_meta has no schema_version row (unreadable catalog)"
            )
        value = str(row["value"])
        if value not in SUPPORTED_SCHEMA_VERSIONS:
            raise CatalogReaderUnavailable(
                f"unsupported source catalog schema version: {value!r} "
                f"(supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)})"
            )
        return value

    # -- ZR-202 typed queries -------------------------------------------------

    def document(self, document_id: str) -> sqlite3.Row | None:
        return self.fetchone(
            "SELECT * FROM documents WHERE document_id = ?", (document_id,)
        )

    def source_sha(self, source_id: str) -> str | None:
        row = self.fetchone(
            "SELECT content_sha256 FROM sources WHERE source_id = ?",
            (source_id,),
        )
        return None if row is None else str(row["content_sha256"])

    def artifacts_for(self, document_id: str) -> list[sqlite3.Row]:
        return self.fetchall(
            """SELECT artifact_id,artifact_role,source_id,path,content_sha256,
                      byte_size,mime_type,generator_name,generator_version,
                      status,error,schema_version,source_sha256,created_at
               FROM artifacts WHERE document_id = ?
               ORDER BY artifact_role,created_at,artifact_id""",
            (document_id,),
        )

    def location_counts(self, root_id: str) -> dict[str, int]:
        rows = self.fetchall(
            "SELECT location_status, COUNT(*) AS n FROM locations "
            "WHERE root_id = ? GROUP BY location_status",
            (root_id,),
        )
        return {str(row["location_status"]): int(row["n"]) for row in rows}

    def status(self) -> dict[str, int]:
        counts = {
            "sources": "SELECT COUNT(*) FROM sources",
            "documents": "SELECT COUNT(*) FROM documents",
            "active_locations": (
                "SELECT COUNT(*) FROM locations WHERE location_status='active'"
            ),
            "missing_locations": (
                "SELECT COUNT(*) FROM locations WHERE location_status='missing'"
            ),
            "normalized_artifacts": (
                "SELECT COUNT(*) FROM artifacts WHERE artifact_role='normalized'"
            ),
            "summary_artifacts": (
                "SELECT COUNT(*) FROM artifacts WHERE artifact_role='summary'"
            ),
            "llm_summary_artifacts": (
                "SELECT COUNT(*) FROM artifacts WHERE artifact_role='summary' "
                "AND generator_name='source_catalog_llm_summary'"
            ),
            "evidence_spans": "SELECT COUNT(*) FROM evidence_spans",
        }
        return {key: int(self.fetchone(sql)[0]) for key, sql in counts.items()}

    def scan_health(self) -> dict[str, Any]:
        rows = self.fetchall(
            "SELECT * FROM scan_runs ORDER BY started_at DESC, rowid DESC LIMIT 20"
        )
        latest_running = None
        latest_completed = None
        interrupted = 0
        for row in rows:
            if row["status"] == "running" and latest_running is None:
                latest_running = {
                    "run_id": row["run_id"],
                    "started_at": row["started_at"],
                    "status": "running",
                }
            if (
                row["status"] in {"completed", "completed_with_errors"}
                and latest_completed is None
            ):
                latest_completed = {
                    "run_id": row["run_id"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "status": row["status"],
                }
            if row["status"] == "interrupted":
                interrupted += 1
        return {
            "latest_running": latest_running,
            "latest_completed": latest_completed,
            "interrupted_count": interrupted,
        }

    def query(
        self,
        *,
        text: str | None = None,
        document_kind: str | None = None,
        source_status: str = "active",
        limit: int = 100,
    ) -> list[sqlite3.Row]:
        sql = "SELECT * FROM documents WHERE source_status = ?"
        params: list[Any] = [source_status]
        if document_kind is not None:
            sql += " AND document_kind = ?"
            params.append(document_kind)
        if text is not None:
            sql += " AND title LIKE ?"
            params.append(f"%{text}%")
        sql += " ORDER BY published_date DESC, title LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        return self.fetchall(sql, tuple(params))

    def entities_like(self, name: str, limit: int = 20) -> list[sqlite3.Row]:
        return self.fetchall(
            """SELECT e.entity_id, e.name, e.entity_kind, COUNT(de.document_id) AS docs
               FROM entities e
               LEFT JOIN document_entities de ON de.entity_id = e.entity_id
               WHERE e.name LIKE ?
               GROUP BY e.entity_id, e.name, e.entity_kind
               ORDER BY e.name LIMIT ?""",
            (f"%{name}%", max(1, min(int(limit), 200))),
        )

    def resolve_handle(
        self,
        document_id: str,
        *,
        expected_content_sha256: str | None = None,
    ) -> dict[str, Any] | None:
        document = self.document(document_id)
        if document is None:
            return None
        handle: dict[str, Any] = dict(document)
        source_id = document["primary_source_id"] or ""
        content_sha = self.source_sha(source_id) if source_id else None
        if (
            expected_content_sha256 is not None
            and expected_content_sha256 != content_sha
        ):
            return None  # fail closed: bytes drifted from the claim
        handle["content_sha256"] = content_sha or ""
        return handle

    def bundle(
        self,
        document_id: str,
        *,
        registry: dict[str, set[str]],
        allowed_roots: tuple[Path, ...],
        now: str,
        expected_content_sha256: str | None = None,
    ) -> dict[str, Any] | None:
        document = self.document(document_id)
        if document is None:
            return None
        doc = dict(document)
        source = {
            "document_id": doc["document_id"],
            "primary_source_id": doc["primary_source_id"] or "",
            "source_sha256": "",
            "as_of_date": doc["published_date"] or "",
        }
        if doc.get("primary_source_id"):
            content_sha = self.source_sha(str(doc["primary_source_id"]))
            if (
                expected_content_sha256 is not None
                and expected_content_sha256 != content_sha
            ):
                return None  # fail closed: stale/forged derivation
            source["source_sha256"] = content_sha or ""
        artifacts = [dict(row) for row in self.artifacts_for(document_id)]
        from .source_bundle import build_source_bundle  # local import: read path

        return build_source_bundle(
            source=source,
            artifacts=artifacts,
            registry=registry,
            allowed_roots=allowed_roots,
            now=now,
        ).to_dict()

    def health(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version(),
            "query_only": self.query_only,
            "status": self.status(),
            "scan_health": self.scan_health(),
        }

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "ReadOnlyCatalogReader":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def reader_from(database_path: Path) -> CatalogReader:
    """Factory: open a read-only catalog reader."""
    return ReadOnlyCatalogReader(database_path)


__all__ = [
    "CatalogReader",
    "CatalogReaderUnavailable",
    "ReadOnlyCatalogReader",
    "reader_from",
    "SUPPORTED_SCHEMA_VERSIONS",
]
