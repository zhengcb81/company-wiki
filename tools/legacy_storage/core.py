"""Shared measuring/report helpers for the legacy storage retirement tools."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

REPORT_SCHEMA = "cwp-storage-retirement/1"
REPORT_FIELDS = (
    "schema_version",
    "operation",
    "dry_run",
    "status",
    "error_code",
    "selection",
    "source_facts_before",
    "source_facts_after",
    "protected_objects_before",
    "protected_objects_after",
    "candidates",
    "deleted",
    "already_absent",
    "files_bytes_before",
    "files_bytes_after",
    "database_bytes_before",
    "database_bytes_after",
    "page_count_before",
    "page_count_after",
    "freelist_before",
    "freelist_after",
    "foreign_key_check",
    "integrity_check",
    "resume_notes",
)

FACT_TABLES = (
    "catalog_meta",
    "roots",
    "sources",
    "documents",
    "locations",
    "entities",
    "document_entities",
    "source_metadata_assertions",
    "document_fingerprint_state",
    "document_retire_audit",
    "document_restore_audit",
    "activation_journal",
    "llm_summary_failures",
    "remediation_proposals",
    "producer_events",
    "producer_attempts",
    "migration_journal",
    "migration_rollback_journal",
    "artifact_bindings",
    "scan_runs",
)
PROTECTED_TABLES = ("narrative_artifact_versions",)
LEGACY_RECORD_TABLES = ("artifacts", "evidence_spans")
ARTIFACT_OBJECTS_SUBDIR = "objects/sha256"


@contextmanager
def read_connection(database_path: Path) -> Iterator["object"]:
    """Open a strictly read-only SQLite connection (never creates/migrates)."""
    import sqlite3

    db = Path(database_path)
    if not db.is_file():
        raise FileNotFoundError(f"database not found: {db}")
    wal, shm = Path(str(db) + "-wal"), Path(str(db) + "-shm")
    if wal.exists() and not shm.is_file():
        raise sqlite3.OperationalError("catalog WAL requires existing shared memory for readonly access")
    uri = db.resolve().as_uri() + "?mode=ro"
    if not wal.exists():
        uri += "&immutable=1"
    connection = sqlite3.connect(uri, uri=True, timeout=30.0)
    try:
        connection.execute("PRAGMA query_only=ON")
        yield connection
    finally:
        connection.close()


def utc_now_text(now: datetime | None = None) -> str:
    moment = now if now is not None else datetime.now(UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalized(path: Path) -> Path:
    """Case- and symlink-normalized absolute path (Windows-safe)."""
    return Path(os.path.normcase(os.path.realpath(str(path))))


def directed_inside(child: Path, root: Path) -> bool:
    child_real, root_real = normalized(child), normalized(root)
    try:
        child_real.relative_to(root_real)
    except ValueError:
        return False
    return child_real != root_real


def file_sha256(path: Path, *, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            data = handle.read(chunk)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()


def tree_stats(root: Path) -> dict[str, int]:
    """File count + total bytes of a directory tree (0 for missing trees)."""
    total = 0
    count = 0
    if root.is_dir():
        for path in root.rglob("*"):
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
                count += 1
    return {"files": count, "bytes": total}


def db_numbers(database_path: Path, *, connection=None) -> dict[str, int]:
    with (nullcontext(connection) if connection is not None else read_connection(database_path)) as conn:
        page_count = int(conn.execute("PRAGMA page_count").fetchone()[0])
        freelist = int(conn.execute("PRAGMA freelist_count").fetchone()[0])
        page_size = int(conn.execute("PRAGMA page_size").fetchone()[0])
    return {
        "page_count": page_count,
        "freelist": freelist,
        "page_size": page_size,
        "logical_bytes": page_count * page_size,
        "file_bytes": Path(database_path).stat().st_size,
    }


def integrity_probe(connection) -> dict[str, object]:
    fk = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]
    integrity_rows = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    integrity = integrity_rows[0] if integrity_rows == ["ok"] else integrity_rows
    return {"foreign_key_check": fk, "integrity_check": integrity}


def canonical_row_text(cursor, row) -> str:
    names = [item[0] for item in cursor.description]
    return json.dumps(
        dict(zip(names, row)),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def table_digest(connection, table: str) -> dict[str, object]:
    """Streaming deterministic count+digest for one table (never loads raw text)."""
    quoted = '"' + table.replace('"', '""') + '"'
    columns = list(connection.execute(f"PRAGMA table_info({quoted})"))
    # Explicit stable order, including tables whose ROWID is repacked by VACUUM.
    ordered = sorted((column for column in columns if column[5]), key=lambda column: column[5]) or columns
    order_sql = ",".join('"' + column[1].replace('"', '""') + '"' for column in ordered)
    cursor = connection.execute(f"SELECT * FROM {quoted} ORDER BY {order_sql}")
    digest = hashlib.sha256()
    count = 0
    while True:
        batch = cursor.fetchmany(4096)
        if not batch:
            break
        for row in batch:
            digest.update(canonical_row_text(cursor, row).encode("utf-8"))
            count += 1
    return {"count": count, "digest": digest.hexdigest()}


def _classify_tables(connection, names: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    known_fact = tuple(n for n in names if n in FACT_TABLES)
    known_protected = tuple(n for n in names if n in PROTECTED_TABLES)
    legacy = tuple(n for n in names if n in LEGACY_RECORD_TABLES)
    unknown = tuple(
        n
        for n in names
        if n not in FACT_TABLES + PROTECTED_TABLES + LEGACY_RECORD_TABLES
    )
    return {
        "fact": known_fact,
        "protected": known_protected,
        "legacy_record": legacy,
        "unknown": unknown,
    }


def source_facts(database_path: Path, *, connection=None) -> dict[str, dict[str, object]]:
    """Deterministic per-table count/digest over source-fact + protected tables."""
    result: dict[str, dict[str, object]] = {}
    with (nullcontext(connection) if connection is not None else read_connection(database_path)) as connection:
        names = tuple(
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        )
        groups = _classify_tables(connection, names)
        measured = groups["fact"] + groups["protected"] + groups["unknown"]
        for table in sorted(measured):
            result[table] = table_digest(connection, table)
    return result


def facts_overview(database_path: Path) -> dict[str, object]:
    """Facts summary: table counts including legacy-record table row counts."""
    overview: dict[str, object] = {}
    with read_connection(database_path) as connection:
        names = tuple(
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        )
        groups = _classify_tables(connection, names)
        counted = (
            groups["fact"]
            + groups["protected"]
            + groups["legacy_record"]
            + groups["unknown"]
        )
        for table in sorted(counted):
            overview[table] = int(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            )
    return overview


def protected_objects(database_path: Path, catalog_dir: Path, *, connection=None) -> dict[str, object]:
    """New narrative finals + raw originals summary (numbers only, no contents)."""
    with (nullcontext(connection) if connection is not None else read_connection(database_path)) as connection:
        new_finals = [
            {
                "artifact_version_id": row[0],
                "source_id": row[1],
                "content_sha256": row[2],
                "object_key": row[3],
                "status": row[4],
            }
            for row in connection.execute(
                "SELECT artifact_version_id, source_id, content_sha256, object_key,"
                " status FROM narrative_artifact_versions"
            )
        ]
        originals = connection.execute(
            "SELECT COUNT(*) FROM locations WHERE role='original_primary'"
        ).fetchone()[0]
    roots = (catalog_dir / "objects", catalog_dir / "artifacts" / "objects")
    measured = [tree_stats(root) for root in roots]
    objects_stats = {key: sum(item[key] for item in measured) for key in ("bytes", "files")}
    return {
        "new_final_items": new_finals,
        "new_final_count": len(new_finals),
        "object_bytes": objects_stats["bytes"],
        "object_file_count": objects_stats["files"],
        "raw_original_locations": originals,
    }


def empty_report(operation: str, *, now: datetime | None = None) -> dict[str, object]:
    return {
        "schema_version": REPORT_SCHEMA,
        "operation": operation,
        "dry_run": True,
        "status": "succeeded",
        "error_code": None,
        "selection": {},
        "source_facts_before": {},
        "source_facts_after": {},
        "protected_objects_before": {},
        "protected_objects_after": {},
        "candidates": [],
        "deleted": [],
        "already_absent": [],
        "files_bytes_before": 0,
        "files_bytes_after": 0,
        "database_bytes_before": 0,
        "database_bytes_after": 0,
        "page_count_before": 0,
        "page_count_after": 0,
        "freelist_before": 0,
        "freelist_after": 0,
        "foreign_key_check": [],
        "integrity_check": "ok",
        "resume_notes": [],
    }


def refused(operation: str, error_code: str, notes: list[str] | None = None) -> dict:
    report = empty_report(operation)
    report["dry_run"] = False
    report["status"] = "refused"
    report["error_code"] = error_code
    report["resume_notes"] = notes or []
    return report


def write_json(path: Path, payload: dict) -> dict:
    from pathlib import Path as _Path

    target = _Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True).encode(
            "utf-8"
        )
    )
    os.replace(tmp, target)
    return payload
