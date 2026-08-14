"""ZR-201: zero-write-capability ``CatalogReader`` and read-only factory.

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

Wiring the production read paths onto this reader is ZR-202/ZR-203; this
card only defines the protocol and factory, and changes nothing else.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Protocol, Sequence, runtime_checkable


class CatalogReaderUnavailable(RuntimeError):
    """The read-only catalog could not be opened (missing/unopenable)."""


@runtime_checkable
class CatalogReader(Protocol):
    """Read-only catalog surface.  No write entry points exist on this
    protocol: implementers that also expose execute/commit/DDL simply have
    MORE surface than the protocol — the protocol itself cannot write."""

    def fetchone(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        """Run a SELECT and return the first row (None when no rows)."""
        ...

    def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        """Run a SELECT and return all rows."""
        ...

    def schema_version(self) -> str:
        """Read the recorded catalog schema version (catalog_meta)."""
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
        return str(row["value"])

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "ReadOnlyCatalogReader":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
