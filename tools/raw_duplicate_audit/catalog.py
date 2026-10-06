"""Read-only SourceCatalog inputs for the raw duplicate audit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .core import sha256_file, utc_now_text


@dataclass(frozen=True)
class LocationRecord:
    """One ``locations`` row joined with its registered source identity."""

    location_id: str
    root_id: str
    relative_path: str
    absolute_path: str
    source_id: str | None
    document_id: str | None
    role: str
    location_status: str
    observed_size: int | None
    content_sha256: str | None
    byte_size: int | None

    @property
    def registered_size(self) -> int:
        if self.byte_size is not None:
            return int(self.byte_size)
        if self.observed_size is not None:
            return int(self.observed_size)
        return 0


@dataclass(frozen=True)
class CatalogInputs:
    config_path: Path
    project_root: Path
    database_path: Path
    config_sha256: str
    config_byte_size: int
    roots: tuple[Any, ...]

    @property
    def catalog_dir(self) -> Path:
        return self.database_path.parent


def load_inputs(
    config_path: Path, *, project_root: Path | None = None
) -> CatalogInputs:
    """Load catalog configuration with the official loader (no database touch)."""
    from company_wiki.source_catalog.config import load_catalog_config

    resolved = Path(config_path).expanduser()
    if project_root is None:
        project_root = resolved.resolve().parents[1]
    config = load_catalog_config(resolved, project_root=Path(project_root))
    return CatalogInputs(
        config_path=resolved,
        project_root=Path(project_root),
        database_path=Path(config.database_path),
        config_sha256=sha256_file(resolved),
        config_byte_size=resolved.stat().st_size,
        roots=tuple(config.roots),
    )


class ReadOnlyReader:
    """Strictly read-only catalog reader with a no-side-file open policy.

    Mirrors ``company_wiki.source_catalog.reader.ReadOnlyCatalogReader``
    (``?mode=ro`` + ``PRAGMA query_only=ON`` + fail-closed schema check) but
    adds the side-file rule the lane requires: an absent ``-wal`` is opened
    with ``immutable=1`` so SQLite never creates ``-wal``/``-shm`` files, and a
    ``-wal`` without its ``-shm`` partner is refused instead of repaired.
    """

    def __init__(self, database_path: Path):
        import sqlite3

        from company_wiki.source_catalog.reader import SUPPORTED_SCHEMA_VERSIONS
        from company_wiki.source_catalog.store import _tolerate_undecodable_text

        database = Path(database_path)
        if not database.is_file():
            raise FileNotFoundError(f"catalog database not found: {database}")
        wal = Path(str(database) + "-wal")
        shm = Path(str(database) + "-shm")
        if wal.exists() and not shm.is_file():
            raise sqlite3.OperationalError(
                "catalog WAL requires existing shared memory for readonly access"
            )
        uri = database.resolve().as_uri() + "?mode=ro"
        self.open_policy = "mode=ro"
        if not wal.exists():
            uri += "&immutable=1"
            self.open_policy = "mode=ro&immutable=1"
        self._connection = sqlite3.connect(uri, uri=True, timeout=30.0)
        self._connection.row_factory = sqlite3.Row
        _tolerate_undecodable_text(self._connection)
        self._connection.execute("PRAGMA query_only=ON")
        self._supported = frozenset(SUPPORTED_SCHEMA_VERSIONS)

    @property
    def query_only(self) -> bool:
        return True

    def fetchone(self, sql: str, params=()):
        return self._connection.execute(sql, tuple(params)).fetchone()

    def fetchall(self, sql: str, params=()):
        return list(self._connection.execute(sql, tuple(params)).fetchall())

    def schema_version(self) -> str:
        row = self.fetchone("SELECT value FROM catalog_meta WHERE key='schema_version'")
        if row is None:
            raise RuntimeError("catalog_meta has no schema_version row")
        value = str(row["value"])
        if value not in self._supported:
            raise RuntimeError(f"unsupported source catalog schema version: {value!r}")
        return value

    def close(self) -> None:
        self._connection.close()


def open_reader(inputs: CatalogInputs) -> ReadOnlyReader:
    """Open the catalog read-only, refusing unsafe side-file states."""
    return ReadOnlyReader(inputs.database_path)


def side_file_state(database_path: Path) -> dict:
    database = Path(database_path)
    return {
        "wal_present": Path(str(database) + "-wal").exists(),
        "shm_present": Path(str(database) + "-shm").exists(),
    }


def database_snapshot(database_path: Path, *, hash_database: bool = False) -> dict:
    path = Path(database_path)
    stat_result = path.stat()
    return {
        "byte_size": int(stat_result.st_size),
        "mtime_ns": int(stat_result.st_mtime_ns),
        "sha256": sha256_file(path) if hash_database else None,
        **side_file_state(path),
    }


def read_locations(reader, *, location_status: str = "all") -> list[LocationRecord]:
    """Every registered original location, metadata only (no file content)."""
    sql = [
        "SELECT l.location_id, l.root_id, l.relative_path, l.absolute_path,",
        " l.source_id, l.document_id, l.role, l.location_status, l.observed_size,",
        " s.content_sha256, s.byte_size",
        " FROM locations l JOIN sources s ON s.source_id = l.source_id",
        " WHERE l.source_id IS NOT NULL AND l.relative_path <> ''",
    ]
    params: list[object] = []
    if location_status != "all":
        sql.append(" AND l.location_status = ?")
        params.append(location_status)
    sql.append(" ORDER BY l.location_id")
    return [
        LocationRecord(
            location_id=row["location_id"],
            root_id=row["root_id"],
            relative_path=row["relative_path"],
            absolute_path=row["absolute_path"] or "",
            source_id=row["source_id"],
            document_id=row["document_id"],
            role=row["role"],
            location_status=row["location_status"],
            observed_size=row["observed_size"],
            content_sha256=row["content_sha256"],
            byte_size=row["byte_size"],
        )
        for row in reader.fetchall("".join(sql), params)
    ]


def similar_source_groups(reader, *, limit: int) -> list[dict]:
    """Registered sources sharing a byte size but not a content digest."""
    rows = reader.fetchall(
        "SELECT byte_size, COUNT(*) AS source_count,"
        " COUNT(DISTINCT content_sha256) AS sha_count"
        " FROM sources GROUP BY byte_size"
        " HAVING COUNT(DISTINCT content_sha256) > 1"
        " ORDER BY byte_size DESC, source_count DESC LIMIT ?",
        (int(limit),),
    )
    groups: list[dict] = []
    for row in rows:
        samples = reader.fetchall(
            "SELECT content_sha256 FROM sources WHERE byte_size = ?"
            " ORDER BY content_sha256 LIMIT 8",
            (row["byte_size"],),
        )
        groups.append(
            {
                "byte_size": int(row["byte_size"]),
                "source_count": int(row["source_count"]),
                "distinct_sha256_count": int(row["sha_count"]),
                "sample_sha256": [str(item["content_sha256"]) for item in samples],
                "classification": "similar_size_different_content",
                "logical_duplicate_bytes": 0,
            }
        )
    return groups


def roots_report(inputs: CatalogInputs, reader) -> list[dict]:
    counts = {
        str(row["root_id"]): int(row["total"])
        for row in reader.fetchall(
            "SELECT root_id, COUNT(*) AS total FROM locations GROUP BY root_id"
        )
    }
    return [
        {
            "root_id": root.root_id,
            "kind": root.kind,
            "priority": int(root.priority),
            "exists": Path(root.path).is_dir(),
            "location_count": counts.get(root.root_id, 0),
        }
        for root in inputs.roots
    ]


def registered_totals(reader) -> dict:
    sources = reader.fetchone(
        "SELECT COUNT(*) AS total, COALESCE(SUM(byte_size), 0) AS bytes FROM sources"
    )
    return {
        "sources": int(sources["total"]),
        "registered_bytes": int(sources["bytes"]),
    }


def protected_snapshot(inputs: CatalogInputs, reader) -> dict:
    """Numbers-only identity of everything this tool must leave untouched."""
    locations = reader.fetchone(
        "SELECT COUNT(*) AS total, COALESCE(SUM(observed_size), 0) AS bytes"
        " FROM locations"
    )
    by_status = {
        str(row["location_status"]): int(row["total"])
        for row in reader.fetchall(
            "SELECT location_status, COUNT(*) AS total FROM locations"
            " GROUP BY location_status"
        )
    }
    sources = registered_totals(reader)
    documents = reader.fetchone("SELECT COUNT(*) AS total FROM documents")
    return {
        "captured_at": utc_now_text(),
        "config_sha256": inputs.config_sha256,
        "database": database_snapshot(inputs.database_path),
        "locations": {
            "count": int(locations["total"]),
            "observed_bytes": int(locations["bytes"]),
            "by_status": by_status,
        },
        "sources": sources,
        "documents": {"count": int(documents["total"])},
        "original_files_deleted": 0,
    }


def protected_equal(before: dict, after: dict) -> bool:
    ignored = {"captured_at"}
    left = {key: value for key, value in before.items() if key not in ignored}
    right = {key: value for key, value in after.items() if key not in ignored}
    return left == right


def _relative(path: Path, project_root: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path(project_root).resolve()).as_posix()
    except ValueError:
        return "<outside-project-root>"


def catalog_identity(
    inputs: CatalogInputs, schema: str | None, *, hash_database: bool
) -> dict:
    return {
        "config_path": _relative(inputs.config_path, inputs.project_root),
        "config_sha256": inputs.config_sha256,
        "config_byte_size": inputs.config_byte_size,
        "database_path": _relative(inputs.database_path, inputs.project_root),
        "database": database_snapshot(
            inputs.database_path, hash_database=hash_database
        ),
        "schema_version": schema,
        "read_only": True,
        "opened_with": "ReadOnlyReader (sqlite3 uri mode=ro[&immutable=1] + PRAGMA query_only=ON)",
        "note": "config/database paths are project-relative; absolute paths go to --local-output",
    }
