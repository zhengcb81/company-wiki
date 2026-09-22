"""Archive retired documents' evidence spans to gzip JSONL (Phase 2.1).

Streaming read-only export of ``evidence_spans`` for retired documents, repaired
for the five DW15-REPAIR defects (owner ruling A-1, 2026-09-22; proposal source:
I-15-A decision.md).  Repaired behaviour:

* **D2 (同日覆写)** — every run writes a *uniquely named* snapshot
  (``retired-evidence-<token>.jsonl.gz``); no run can truncate, replace or
  overwrite another run's published snapshot.
* **D3 (时钟取目录名)** — the function never reads the system clock.  The date
  directory comes from the explicitly injected ``now`` parameter; the uniqueness
  token is a non-clock value (uuid4).  ``now`` is required: there is no
  wall-clock fallback.
* **D5 (崩溃后不可恢复)** — the snapshot is written to a temporary file,
  flushed+fsynced, re-read and verified (row count + per-row digests), and only
  then atomically published with a create-if-absent link/rename.  A kill at any
  point leaves **no truncated file at a published snapshot path**: either the
  previous snapshot is still intact, or the new one appears complete, or the
  evidence simply stays in the catalog.

After a successful publish a per-snapshot manifest
(``archive-verified-manifest-1.0``) is written atomically next to the snapshot,
pinning it by sha256/size/exact span ids/row digests/verified completion time
(I-15-A D-W15-1).  Prune may only authorise deletions from such a manifest (D1).

The export still runs on a read-only connection and does not take the operation
lock (retired documents are never re-normalized, so their spans are stable).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .models import CATALOG_SCHEMA_VERSION

BATCH_SIZE = 100_000
MANIFEST_SCHEMA = "archive-verified-manifest-1.0"

_SELECT = """SELECT e.span_id, e.source_id, e.document_id, e.locator, e.page_number,
                     e.paragraph_index, e.table_index, e.raw_text, e.span_json,
                     e.parser_name, e.parser_version, e.parse_status
              FROM evidence_spans e
              JOIN documents d ON d.document_id = e.document_id
              WHERE d.source_status = 'retired'"""


@dataclass(frozen=True)
class ArchiveReport:
    archive_path: str
    manifest_path: str
    rows_written: int
    rows_in_catalog: int
    ok: bool

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _row_digest(row: dict[str, Any]) -> str:
    """Canonical row digest (I-15-A D-W15-1): sorted-keys compact JSON."""
    payload = json.dumps(row, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    """Publish ``text`` at ``path`` via temp + fsync + atomic replace."""
    tmp = path.with_name(f"{path.name}.partial-{uuid.uuid4().hex[:8]}")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _publish(temp_path: Path, final_path: Path) -> None:
    """Atomically publish ``temp_path`` at ``final_path`` without ever
    overwriting an existing published file (create-if-absent)."""
    if final_path.exists():
        raise FileExistsError(f"snapshot path already published: {final_path}")
    try:
        os.link(temp_path, final_path)   # atomic; fails if the target exists
        temp_path.unlink()
    except (AttributeError, NotImplementedError, OSError):
        if final_path.exists():
            raise FileExistsError(f"snapshot path already published: {final_path}")
        os.rename(temp_path, final_path)


def _fsync_file(path: Path) -> None:
    with open(path, "r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())


def _verify_snapshot(temp_path: Path) -> tuple[int, dict[str, str]]:
    """Re-read the written bytes and recompute count + digests (fail closed)."""
    ids: list[str] = []
    digests: dict[str, str] = {}
    with gzip.open(temp_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            span_id = row["span_id"]
            if span_id in digests:
                raise RuntimeError(f"duplicate span_id in snapshot: {span_id}")
            ids.append(span_id)
            digests[span_id] = _row_digest(row)
    return len(ids), digests


def archive_retired_evidence(
    database_path: Path | str,
    archive_root: Path | str,
    *,
    now: datetime,
    progress: Callable[[int, int], None] | None = None,
) -> ArchiveReport:
    """Archive retired spans; ``now`` (timezone-aware) is REQUIRED.

    The machine clock is never read: ``now`` decides the date directory and the
    provenance timestamp, a uuid4 token decides file uniqueness (D2/D3).
    """
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise TypeError(
            "now: a timezone-aware datetime is required (no system-clock fallback)")
    database_path = Path(database_path)
    archive_root = Path(archive_root)

    moment = now.astimezone(timezone.utc)
    day = moment.date().isoformat()
    token = uuid.uuid4().hex[:16]                     # non-clock uniqueness (D2/D3)
    out_dir = archive_root / "archive" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"retired-evidence-{token}.jsonl.gz"
    if out_path.exists():
        raise FileExistsError(f"snapshot path already published: {out_path}")
    tmp_path = out_dir / (
        f"retired-evidence-{token}.jsonl.gz.partial-{uuid.uuid4().hex[:8]}")

    conn = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    published = False
    try:
        total = int(
            conn.execute(
                "SELECT COUNT(*) FROM evidence_spans WHERE document_id IN "
                "(SELECT document_id FROM documents WHERE source_status='retired')"
            ).fetchone()[0]
        )

        rows_written = 0
        written_digests: dict[str, str] = {}
        last_id: str | None = None
        # D5: everything below writes the TEMP file only; the published path
        # is touched once, atomically, after verification.
        with gzip.open(tmp_path, "wt", encoding="utf-8", newline="\n") as fh:
            while True:
                if last_id is None:
                    rows = conn.execute(
                        _SELECT + " ORDER BY e.span_id LIMIT ?", (BATCH_SIZE,)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        _SELECT + " AND e.span_id > ? ORDER BY e.span_id LIMIT ?",
                        (last_id, BATCH_SIZE),
                    ).fetchall()
                if not rows:
                    break
                for row in rows:
                    row_dict = dict(row)
                    fh.write(json.dumps(row_dict, ensure_ascii=False) + "\n")
                    written_digests[row_dict["span_id"]] = _row_digest(row_dict)
                    last_id = row["span_id"]
                rows_written += len(rows)
                if progress is not None:
                    progress(rows_written, total)

        if rows_written != total:
            raise RuntimeError(
                f"archive reconciliation failed: wrote {rows_written}, "
                f"catalog reports {total}; snapshot not published")

        # verify the bytes we are about to publish (fail closed, D5)
        _fsync_file(tmp_path)
        verified_count, verified_digests = _verify_snapshot(tmp_path)
        if verified_count != rows_written or verified_digests != written_digests:
            raise RuntimeError(
                "archive self-verification failed: snapshot not published")

        _publish(tmp_path, out_path)
        published = True

        archive_sha256 = _sha256_file(out_path)
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "catalog_identity": f"{database_path.name}:{CATALOG_SCHEMA_VERSION}",
            "archive_path": str(out_path.resolve()),
            "archive_sha256": archive_sha256,
            "archive_bytes": out_path.stat().st_size,
            "rows_in_archive": verified_count,
            "verified_completed_at": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "span_ids": sorted(verified_digests),
            "row_digests": {k: verified_digests[k] for k in sorted(verified_digests)},
            "verifier": ("archive_retired_evidence self-check: re-read snapshot, "
                         "recomputed per-row digests and count before publish"),
            "problems": [],
            "ok": True,
        }
        manifest_path = out_dir / f"{out_path.name}.manifest.json"
        _atomic_write_text(manifest_path,
                           json.dumps(manifest, ensure_ascii=False, indent=2))
    finally:
        conn.close()
        if not published and tmp_path.exists():
            # crash/abort residue must never sit at a published path (D5)
            tmp_path.unlink(missing_ok=True)

    return ArchiveReport(
        archive_path=str(out_path.resolve()),
        manifest_path=str(manifest_path.resolve()),
        rows_written=rows_written,
        rows_in_catalog=total,
        ok=True,
    )


__all__ = ["ArchiveReport", "archive_retired_evidence"]
