"""Build and verify an active-only catalog plus a byte-identical cold backup.

This tool never cuts over or deletes the production database. It deliberately
verifies the zstd archive by hashing the full decompression stream without
materializing a restored 46 GiB database, as requested by the user.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
from typing import Any

from company_wiki.source_catalog.lock import CatalogOperationLock


RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
CHUNK_SIZE = 8 * 1024 * 1024
MIN_FREE_RESERVE = 10 * 1024**3
MARKERS = {
    "legacy_evidence_retention": "active_only",
    "legacy_evidence_backup_format": "zstd-full-sqlite-stream-sha256-v1",
}


class RetirementRefused(RuntimeError):
    """A required identity, consistency, or space check failed."""


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def _sync_file(path: Path) -> None:
    with path.open("r+b") as stream:
        os.fsync(stream.fileno())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    pending = path.with_name(path.name + ".partial")
    with pending.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, path)


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _readonly(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.execute("PRAGMA query_only=ON")
    return connection


def _source_state(project_root: Path) -> tuple[Path, tuple[int, int]]:
    catalog = (project_root / ".source_catalog").resolve(strict=True)
    database = catalog / "catalog.sqlite3"
    if not database.is_file() or database.is_symlink():
        raise RetirementRefused("production catalog is absent or a symlink")
    control = json.loads((catalog / "worker_control.json").read_text(encoding="utf-8"))
    if control.get("desired_state") != "paused":
        raise RetirementRefused("Worker desired_state is not paused")
    wal = Path(str(database) + "-wal")
    if wal.exists() and wal.stat().st_size != 0:
        raise RetirementRefused("production SQLite WAL is not empty")
    # A 0-byte WAL and a 32 KiB SHM may remain after a prior reader. They
    # contain no committed WAL frames; recheck the WAL after every phase.
    stat = database.stat()
    if stat.st_size <= 0:
        raise RetirementRefused("production catalog is empty")
    return database, (stat.st_size, stat.st_mtime_ns)


def _assert_source_unchanged(database: Path, initial: tuple[int, int]) -> None:
    now = database.stat()
    if (now.st_size, now.st_mtime_ns) != initial:
        raise RetirementRefused("production catalog changed during preparation")
    wal = Path(str(database) + "-wal")
    if wal.exists() and wal.stat().st_size != 0:
        raise RetirementRefused("production SQLite WAL gained data")


def _schema(source: sqlite3.Connection) -> tuple[
    list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]
]:
    objects = source.execute(
        "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' "
        "ORDER BY type,name"
    ).fetchall()
    unsupported = [
        (kind, name) for kind, name, _ in objects
        if kind not in {"table", "index", "trigger"}
    ]
    if unsupported:
        raise RetirementRefused(f"unhandled schema objects: {unsupported}")
    tables = [(name, sql) for kind, name, sql in objects if kind == "table" and sql]
    indexes = [(name, sql) for kind, name, sql in objects if kind == "index" and sql]
    triggers = [(name, sql) for kind, name, sql in objects if kind == "trigger" and sql]
    if "evidence_spans" not in {name for name, _ in tables}:
        raise RetirementRefused("evidence_spans table is missing")
    if "catalog_meta" not in {name for name, _ in tables}:
        raise RetirementRefused("catalog_meta table is missing")
    return tables, indexes, triggers


def _row_digest(connection: sqlite3.Connection, table: str, *, active_only: bool = False,
                meta_keys: tuple[str, ...] | None = None) -> tuple[int, str]:
    columns = [row[1] for row in connection.execute(f"PRAGMA table_info({_q(table)})")]
    pk_columns = [row[1] for row in sorted(
        (r for r in connection.execute(f"PRAGMA table_info({_q(table)})") if r[5]),
        key=lambda r: r[5],
    )]
    order = ",".join(_q(column) for column in (pk_columns or columns))
    if active_only:
        # Per-document index walks avoid a multi-gigabyte global ORDER BY
        # temp B-tree over the 1.49 million active production spans.
        def rows():
            documents = connection.execute(
                "SELECT document_id FROM documents WHERE source_status='active' "
                "ORDER BY document_id"
            )
            for (document_id,) in documents:
                yield from connection.execute(
                    "SELECT * FROM evidence_spans WHERE document_id=? ORDER BY span_id",
                    (document_id,),
                )
        stream = rows()
    elif meta_keys is not None:
        if not meta_keys:
            raise RetirementRefused("catalog_meta has no original keys")
        placeholders = ",".join("?" for _ in meta_keys)
        query = f"SELECT * FROM {_q(table)} WHERE key IN ({placeholders}) ORDER BY {order}"
        stream = connection.execute(query, meta_keys)
    else:
        query = f"SELECT * FROM {_q(table)} ORDER BY {order}"
        stream = connection.execute(query)
    digest = hashlib.sha256()
    count = 0
    for row in stream:
        count += 1
        for value in row:
            if value is None:
                digest.update(b"N")
                continue
            if isinstance(value, bytes):
                data = value
                tag = b"B"
            else:
                data = str(value).encode("utf-8")
                tag = b"T" if isinstance(value, str) else b"V"
            digest.update(tag)
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
        digest.update(b"\xff")
    return count, digest.hexdigest()


def _make_shadow(source_path: Path, target_path: Path, *, source_sha256: str,
                 backup_name: str) -> dict[str, Any]:
    source = _readonly(source_path)
    target = sqlite3.connect(target_path, uri=True)
    try:
        tables, indexes, triggers = _schema(source)
        page_size = int(source.execute("PRAGMA page_size").fetchone()[0])
        target.execute(f"PRAGMA page_size={page_size}")
        target.execute("PRAGMA foreign_keys=OFF")
        target.execute("PRAGMA journal_mode=DELETE")
        target.execute("PRAGMA synchronous=FULL")
        target.execute("ATTACH DATABASE ? AS old", (source_path.resolve().as_uri() + "?mode=ro&immutable=1",))
        for _, statement in tables:
            target.execute(statement)
        for name, _ in tables:
            if name == "evidence_spans":
                target.execute(
                    "INSERT INTO evidence_spans SELECT e.* FROM old.evidence_spans e "
                    "JOIN old.documents d ON d.document_id=e.document_id "
                    "WHERE d.source_status='active'"
                )
            else:
                target.execute(f"INSERT INTO {_q(name)} SELECT * FROM old.{_q(name)}")
        for _, statement in indexes:
            target.execute(statement)
        # Install triggers after the bulk copy. In production, the artifact
        # trigger would otherwise create duplicate producer_events.
        for _, statement in triggers:
            target.execute(statement)
        target.commit()
        original_meta = tuple(row[0] for row in source.execute("SELECT key FROM catalog_meta ORDER BY key"))
        table_digests: dict[str, Any] = {}
        for name, _ in tables:
            expected = _row_digest(source, name, active_only=name == "evidence_spans")
            actual = _row_digest(
                target, name,
                active_only=name == "evidence_spans",
                meta_keys=original_meta if name == "catalog_meta" else None,
            )
            if expected != actual:
                raise RetirementRefused(f"row digest differs for {name}: {expected} != {actual}")
            table_digests[name] = {"rows": expected[0], "sha256": expected[1]}
        if table_digests["evidence_spans"]["rows"] <= 0:
            raise RetirementRefused("no active spans copied")
        for key, value in {
            **MARKERS,
            "legacy_source_sha256": source_sha256,
            "legacy_backup_name": backup_name,
        }.items():
            target.execute("INSERT INTO catalog_meta(key,value) VALUES(?,?)", (key, value))
        target.commit()
        if list(target.execute("PRAGMA foreign_key_check")):
            raise RetirementRefused("shadow foreign_key_check failed")
        if target.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RetirementRefused("shadow quick_check failed")
        target.execute("DETACH DATABASE old")
        target.close()
        source.close()
        _sync_file(target_path)
        shadow_hash, shadow_bytes = _sha256_file(target_path)
        return {
            "shadow_path": str(target_path.resolve()),
            "shadow_bytes": shadow_bytes,
            "shadow_sha256": shadow_hash,
            "tables": table_digests,
            "index_names": [name for name, _ in indexes],
            "trigger_names": [name for name, _ in triggers],
        }
    finally:
        try:
            target.close()
        except sqlite3.Error:
            pass
        source.close()


def _make_backup(zstd: Path, source_path: Path, backup_path: Path,
                 expected_sha: str, expected_bytes: int) -> dict[str, Any]:
    result = subprocess.run(
        [str(zstd), "-3", "-T1", "-q", "-o", str(backup_path), str(source_path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RetirementRefused(f"zstd compression failed: {result.stderr[-500:]}")
    _sync_file(backup_path)
    archive_sha, archive_bytes = _sha256_file(backup_path)
    tested = subprocess.run([str(zstd), "-t", "-q", str(backup_path)],
                            capture_output=True, text=True, check=False)
    if tested.returncode != 0:
        raise RetirementRefused(f"zstd -t failed: {tested.stderr[-500:]}")
    digest = hashlib.sha256()
    total = 0
    with subprocess.Popen([str(zstd), "-d", "-q", "-c", str(backup_path)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        assert process.stdout is not None
        while chunk := process.stdout.read(CHUNK_SIZE):
            total += len(chunk)
            digest.update(chunk)
        assert process.stderr is not None
        errors = process.stderr.read().decode("utf-8", "replace")
        if process.wait() != 0:
            raise RetirementRefused(f"full decompression stream failed: {errors[-500:]}")
    if total != expected_bytes or digest.hexdigest() != expected_sha:
        raise RetirementRefused("decompression stream does not match the old database")
    return {
        "backup_path": str(backup_path.resolve()),
        "backup_bytes": archive_bytes,
        "backup_sha256": archive_sha,
        "decompressed_bytes": total,
        "decompressed_sha256": digest.hexdigest(),
        "zstd_test": "ok",
        "full_disk_restore_performed": False,
    }


def prepare(project_root: Path, run_id: str, zstd: Path) -> dict[str, Any]:
    project_root = project_root.resolve(strict=True)
    if not RUN_ID.fullmatch(run_id):
        raise RetirementRefused("run_id must be UTC timestamp plus eight lowercase hex digits")
    if not zstd.is_file():
        raise RetirementRefused("zstd executable is missing")
    catalog = project_root / ".source_catalog"
    run_dir = catalog / "retirement" / run_id
    if run_dir.exists():
        raise RetirementRefused("run directory already exists; use a fresh run_id")
    with CatalogOperationLock(catalog, operation="catalog-retirement-prepare"):
        database, initial = _source_state(project_root)
        free_before = shutil.disk_usage(catalog).free
        worst_case_increment = initial[0] + initial[0] // 8
        if free_before < worst_case_increment + MIN_FREE_RESERVE:
            raise RetirementRefused(
                "insufficient same-volume free space for shadow, full backup, "
                "and 10 GiB reserve"
            )
        run_dir.mkdir(parents=True, exist_ok=False)
        print("F0 source identity and read-only integrity", file=sys.stderr, flush=True)
        source_sha, source_bytes = _sha256_file(database)
        _assert_source_unchanged(database, initial)
        source = _readonly(database)
        try:
            if source.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise RetirementRefused("production source quick_check failed")
            schema_version = source.execute(
                "SELECT value FROM catalog_meta WHERE key='schema_version'"
            ).fetchone()
            if schema_version is None or schema_version[0] != "1.2.0":
                raise RetirementRefused("unexpected production schema_version")
        finally:
            source.close()
        _assert_source_unchanged(database, initial)
        shadow_partial = run_dir / "catalog.active.sqlite3.partial"
        backup_partial = run_dir / "catalog.full.sqlite3.zst.partial"
        print("F1 build and compare active-only shadow", file=sys.stderr, flush=True)
        shadow = _make_shadow(database, shadow_partial,
                              source_sha256=source_sha,
                              backup_name="catalog.full.sqlite3.zst")
        _assert_source_unchanged(database, initial)
        if shutil.disk_usage(catalog).free < source_bytes + MIN_FREE_RESERVE:
            raise RetirementRefused("insufficient free space before full backup")
        print("F2 compress and verify full decompression stream", file=sys.stderr, flush=True)
        backup = _make_backup(zstd, database, backup_partial, source_sha, source_bytes)
        _assert_source_unchanged(database, initial)
        final_sha, final_bytes = _sha256_file(database)
        if (final_sha, final_bytes) != (source_sha, source_bytes):
            raise RetirementRefused("production source hash changed during preparation")
        shadow_final = run_dir / "catalog.active.sqlite3"
        backup_final = run_dir / "catalog.full.sqlite3.zst"
        os.replace(shadow_partial, shadow_final)
        os.replace(backup_partial, backup_final)
        shadow["shadow_path"] = str(shadow_final.resolve())
        backup["backup_path"] = str(backup_final.resolve())
        result = {
            "schema": "catalog-retirement-prepared-v1",
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "project_root": str(project_root),
            "production_database": str(database.resolve()),
            "source_bytes": source_bytes,
            "source_sha256": source_sha,
            "source_mtime_ns": initial[1],
            "worker_desired_state": "paused",
            "free_bytes_before": free_before,
            "free_bytes_after": shutil.disk_usage(catalog).free,
            **shadow,
            **backup,
            "cutover_performed": False,
            "old_database_deleted": False,
        }
        _write_json(run_dir / "prepared.json", result)
        print("F0-F2 prepared and verified; production database unchanged", file=sys.stderr, flush=True)
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--zstd", type=Path, default=Path(r"C:\Miniconda\Library\bin\zstd.exe"))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.project_root, args.run_id, args.zstd),
                         ensure_ascii=False, sort_keys=True))
    except (RetirementRefused, OSError, sqlite3.Error) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
