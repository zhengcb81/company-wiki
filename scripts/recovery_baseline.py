#!/usr/bin/env python3
"""Create a resumable, hash-verified recovery baseline for a copied worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDES = {".git", ".codegraph", "__pycache__", ".pytest_cache"}


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path, excluded_names: set[str]) -> Iterable[tuple[str, Path]]:
    for base, directories, filenames in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in excluded_names)
        for filename in sorted(filenames):
            path = Path(base) / filename
            relative = path.relative_to(root)
            if any(part in excluded_names for part in relative.parts):
                continue
            yield relative.as_posix(), path


class RecoveryBaselineVerifier:
    """Persist per-file verification so an interrupted full hash can resume."""

    def __init__(
        self,
        source: Path,
        destination: Path,
        state_db: Path,
        manifest_path: Path,
        excluded_names: set[str] | None = None,
    ) -> None:
        self.source = source.resolve()
        self.destination = destination.resolve()
        self.state_db = state_db.resolve()
        self.manifest_path = manifest_path.resolve()
        self.excluded_names = excluded_names or set(DEFAULT_EXCLUDES)
        if not self.source.is_dir():
            raise ValueError(f"Source is not a directory: {self.source}")
        if not self.destination.is_dir():
            raise ValueError(f"Destination is not a directory: {self.destination}")
        if self.destination == self.source or self.destination.is_relative_to(self.source):
            raise ValueError("Destination must be outside the source tree")
        self.state_db.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.state_db))
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def close(self) -> None:
        self._connection.close()

    def _initialize_schema(self) -> None:
        self._connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                source_size INTEGER,
                source_mtime_ns INTEGER,
                destination_size INTEGER,
                destination_mtime_ns INTEGER,
                source_sha256 TEXT,
                destination_sha256 TEXT,
                status TEXT NOT NULL,
                error TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_recovery_files_status ON files(status);
            """
        )
        self._connection.commit()

    def _metadata(self) -> dict[str, str]:
        rows = self._connection.execute("SELECT key, value FROM metadata").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def _write_metadata(self, values: dict[str, str]) -> None:
        self._connection.executemany(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)", values.items()
        )
        self._connection.commit()

    def scan(self, force: bool = False) -> dict[str, int]:
        metadata = self._metadata()
        expected = {
            "source": str(self.source),
            "destination": str(self.destination),
            "excluded_names": json.dumps(sorted(self.excluded_names)),
        }
        if metadata.get("scan_complete") == "1" and not force:
            for key, value in expected.items():
                if metadata.get(key) != value:
                    raise ValueError(f"Recovery state belongs to a different {key}")
            return self.summary()

        source_files = dict(iter_files(self.source, self.excluded_names))
        destination_files = dict(iter_files(self.destination, self.excluded_names))
        rows: list[tuple[object, ...]] = []
        for relative, source_path in source_files.items():
            source_stat = source_path.stat()
            destination_path = destination_files.get(relative)
            if destination_path is None:
                rows.append(
                    (
                        relative,
                        source_stat.st_size,
                        source_stat.st_mtime_ns,
                        None,
                        None,
                        None,
                        None,
                        "missing",
                        "destination file missing",
                    )
                )
                continue
            destination_stat = destination_path.stat()
            status = "pending" if source_stat.st_size == destination_stat.st_size else "size_mismatch"
            error = "" if status == "pending" else "source/destination sizes differ"
            rows.append(
                (
                    relative,
                    source_stat.st_size,
                    source_stat.st_mtime_ns,
                    destination_stat.st_size,
                    destination_stat.st_mtime_ns,
                    None,
                    None,
                    status,
                    error,
                )
            )

        for relative, destination_path in destination_files.items():
            if relative in source_files:
                continue
            destination_stat = destination_path.stat()
            rows.append(
                (
                    relative,
                    None,
                    None,
                    destination_stat.st_size,
                    destination_stat.st_mtime_ns,
                    None,
                    None,
                    "extra",
                    "destination contains an extra file",
                )
            )

        with self._connection:
            self._connection.execute("DELETE FROM files")
            self._connection.executemany(
                """
                INSERT INTO files(
                    path, source_size, source_mtime_ns,
                    destination_size, destination_mtime_ns,
                    source_sha256, destination_sha256, status, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        self._write_metadata(
            {
                **expected,
                "scan_complete": "1",
                "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        return self.summary()

    def verify(self, max_files: int | None = None, progress_interval_s: float = 30.0) -> dict[str, int]:
        rows = self._connection.execute(
            "SELECT * FROM files WHERE status = 'pending' ORDER BY path"
        ).fetchall()
        processed = 0
        processed_bytes = 0
        last_report = time.monotonic()
        for row in rows:
            if max_files is not None and processed >= max_files:
                break
            relative = row["path"]
            source_path = self.source / Path(relative)
            destination_path = self.destination / Path(relative)
            try:
                source_stat = source_path.stat()
                destination_stat = destination_path.stat()
                if (
                    source_stat.st_size != row["source_size"]
                    or source_stat.st_mtime_ns != row["source_mtime_ns"]
                ):
                    raise RuntimeError("source changed after baseline scan")
                if destination_stat.st_size != row["destination_size"]:
                    raise RuntimeError("destination size changed after baseline scan")
                source_hash = sha256_file(source_path)
                destination_hash = sha256_file(destination_path)
                status = "verified" if source_hash == destination_hash else "hash_mismatch"
                error = "" if status == "verified" else "SHA-256 differs"
                with self._connection:
                    self._connection.execute(
                        """
                        UPDATE files
                        SET source_sha256 = ?, destination_sha256 = ?, status = ?, error = ?
                        WHERE path = ?
                        """,
                        (source_hash, destination_hash, status, error, relative),
                    )
                processed += 1
                processed_bytes += source_stat.st_size
            except Exception as exc:  # Persist the exact file failure and continue.
                with self._connection:
                    self._connection.execute(
                        "UPDATE files SET status = 'error', error = ? WHERE path = ?",
                        (repr(exc), relative),
                    )
                processed += 1

            now = time.monotonic()
            if now - last_report >= progress_interval_s:
                remaining = self._connection.execute(
                    "SELECT COUNT(*) FROM files WHERE status = 'pending'"
                ).fetchone()[0]
                print(
                    json.dumps(
                        {
                            "processed_this_run": processed,
                            "processed_bytes": processed_bytes,
                            "remaining": remaining,
                        }
                    ),
                    flush=True,
                )
                last_report = now
        return self.summary()

    def summary(self) -> dict[str, int]:
        rows = self._connection.execute(
            "SELECT status, COUNT(*) AS count FROM files GROUP BY status"
        ).fetchall()
        summary = {row["status"]: row["count"] for row in rows}
        summary["total"] = sum(summary.values())
        summary["bytes"] = self._connection.execute(
            "SELECT COALESCE(SUM(source_size), 0) FROM files"
        ).fetchone()[0]
        return summary

    def write_manifest(self) -> dict[str, object]:
        summary = self.summary()
        rows = [dict(row) for row in self._connection.execute("SELECT * FROM files ORDER BY path")]
        manifest = {
            "schema_version": 1,
            "source": str(self.source),
            "destination": str(self.destination),
            "excluded_rebuildable": sorted(self.excluded_names),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": summary,
            "files": rows,
        }
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return manifest

    def is_complete_and_valid(self) -> bool:
        summary = self.summary()
        return summary.get("verified", 0) == summary.get("total", 0) and summary.get("total", 0) > 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--state-db", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--rescan", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    exclusions = set(DEFAULT_EXCLUDES) | set(args.exclude)
    verifier = RecoveryBaselineVerifier(
        args.source, args.destination, args.state_db, args.manifest, exclusions
    )
    try:
        verifier.scan(force=args.rescan)
        verifier.verify(max_files=args.max_files)
        manifest = verifier.write_manifest()
        print(json.dumps(manifest["summary"], ensure_ascii=False, indent=2))
        return 0 if verifier.is_complete_and_valid() else 2
    finally:
        verifier.close()


if __name__ == "__main__":
    raise SystemExit(main())
