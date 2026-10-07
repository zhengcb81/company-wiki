"""Single-transaction read-only catalog probe used by this lane's fixtures.

Opens ``file:...?mode=ro`` with ``PRAGMA query_only=ON``, never creates a
missing database, never writes a side file and reports its own change count so
tests can prove the reader stayed a reader.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sqlite3
from typing import Any, Sequence

_ALLOWED_ROWS = ("locations", "sources", "documents", "catalog_meta", "roots")


class CatalogProbeError(RuntimeError):
    """Raised when the catalog cannot be opened read-only."""


@dataclass
class ProbeResult:
    schema_version: str | None
    statements: list[str] = field(default_factory=list)
    total_changes: int = 0
    query_only: bool = False
    in_transaction: bool = False
    locations: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    roots: list[dict[str, Any]] = field(default_factory=list)
    catalog_meta: dict[str, Any] = field(default_factory=dict)


def _uri(database_path: Path) -> str:
    return "file:" + database_path.resolve().as_posix() + "?mode=ro"


def probe_catalog(
    database_path: str | Path, *, rows: Sequence[str] = ("locations",)
) -> ProbeResult:
    path = Path(database_path)
    if not path.exists():
        raise CatalogProbeError(f"catalog database not found: {path.name}")
    unknown = [name for name in rows if name not in _ALLOWED_ROWS]
    if unknown:
        raise CatalogProbeError(f"unsupported probe rows: {unknown}")

    result = ProbeResult(schema_version=None)
    try:
        connection = sqlite3.connect(_uri(path), uri=True, timeout=5.0)
    except sqlite3.Error as exc:  # pragma: no cover - platform specific
        raise CatalogProbeError(f"cannot open catalog read-only: {exc}") from exc

    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        result.query_only = bool(connection.execute("PRAGMA query_only").fetchone()[0])
        connection.execute("BEGIN")
        row = connection.execute(
            "SELECT value FROM catalog_meta WHERE key='schema_version'"
        ).fetchone()
        result.schema_version = row[0] if row else None
        result.statements.append("SELECT schema_version")

        for name in rows:
            result.statements.append(f"SELECT {name}")
            cursor = connection.execute(f"SELECT * FROM {name}")
            fetched = [dict(item) for item in cursor.fetchall()]
            if name == "catalog_meta":
                result.catalog_meta = {r["key"]: r["value"] for r in fetched}
            elif name == "locations":
                result.locations = fetched
            elif name == "sources":
                result.sources = fetched
            elif name == "documents":
                result.documents = fetched
            elif name == "roots":
                result.roots = fetched
        connection.execute("COMMIT")
    except sqlite3.Error as exc:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise CatalogProbeError(f"catalog read failed: {exc}") from exc
    finally:
        result.total_changes = int(connection.total_changes)
        result.in_transaction = bool(connection.in_transaction)
        connection.close()
    return result


__all__ = ["CatalogProbeError", "ProbeResult", "probe_catalog"]
