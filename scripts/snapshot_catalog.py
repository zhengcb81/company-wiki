"""WU-0.2: anonymized production catalog snapshot generator.

Exports from a source_catalog SQLite database ONLY the anonymous shape
needed to replay/verify behavior in CI without the real 49 GB catalog or
the three real root directories:

- ``schema``: table names + columns (no rows, no data);
- ``root_policy``: root_id/kind/priority (raw paths replaced by root_id);
- ``status_distributions``: document/location counts by status;
- ``samples``: at most ``--max-samples`` de-path'd document rows.

Hard constraints (enforced by tests/contract/test_snapshot_catalog.py):

- ``--read-only`` flag is mandatory; without it the tool refuses to run.
- The catalog is opened with ``file:...?mode=ro`` + ``busy_timeout`` so a
  locked production catalog times out instead of hanging; no writes, no
  WAL/SHM side files.
- Output is deterministic: ordered queries + sorted JSON keys, so two runs
  hash identically.
- No absolute paths, user directories, or personal paths are exported.

Usage::

    python scripts/snapshot_catalog.py --read-only --catalog <db> \
        [--max-samples N]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

BUSY_TIMEOUT_MS = 5000
DEFAULT_MAX_SAMPLES = 10


def _open_readonly(catalog: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    con.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    con.execute("PRAGMA query_only = ON")
    return con


def _tables(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _schema(con: sqlite3.Connection) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for table in _tables(con):
        cols = con.execute(f"PRAGMA table_info({table})").fetchall()
        out[table] = [c[1] for c in cols]
    return out


def _root_policy(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        "SELECT root_id, kind, priority FROM roots ORDER BY priority, root_id"
    ).fetchall()
    return [{"root_id": r[0], "kind": r[1], "priority": r[2]} for r in rows]


def _status_distributions(con: sqlite3.Connection) -> dict[str, dict[str, int]]:
    documents: dict[str, int] = {}
    for (status,) in con.execute(
        "SELECT source_status FROM documents"
    ).fetchall():
        documents[status] = documents.get(status, 0) + 1
    locations: dict[str, int] = {}
    for (status,) in con.execute(
        "SELECT location_status FROM locations"
    ).fetchall():
        locations[status] = locations.get(status, 0) + 1
    return {
        "documents_by_status": dict(sorted(documents.items())),
        "locations_by_status": dict(sorted(locations.items())),
    }


def _samples(con: sqlite3.Connection, max_samples: int) -> list[dict[str, Any]]:
    """De-path'd sample rows: keep shape/status facts, drop any path."""
    rows = con.execute(
        """
        SELECT d.document_id, d.document_kind, d.source_status,
               d.source_type, d.published_date,
               l.role, l.location_status, l.root_id
        FROM documents d
        LEFT JOIN locations l ON l.document_id = d.document_id
        ORDER BY d.document_id, l.location_id
        """
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        if len(out) >= max_samples:
            break
        out.append(
            {
                "document_id": row[0],
                "document_kind": row[1],
                "source_status": row[2],
                "source_type": row[3],
                "published_date": row[4],
                "location_role": row[5],
                "location_status": row[6],
                "root_id": row[7],
            }
        )
    return out


def snapshot(catalog: Path, max_samples: int) -> dict[str, Any]:
    con = _open_readonly(catalog)
    try:
        return {
            "schema_version": con.execute("PRAGMA user_version").fetchone()[0],
            "schema": _schema(con),
            "root_policy": _root_policy(con),
            "status_distributions": _status_distributions(con),
            "samples": _samples(con, max_samples),
        }
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Anonymized catalog snapshot")
    parser.add_argument("--read-only", action="store_true",
                        help="mandatory: confirms read-only operation")
    parser.add_argument("--catalog", type=Path, required=True, help="catalog.sqlite3 path")
    parser.add_argument("--max-samples", type=int, default=DEFAULT_MAX_SAMPLES,
                        help="max de-path'd sample rows (default 10)")
    args = parser.parse_args()
    if not args.read_only:
        print("refusing to run: the --read-only flag is mandatory", file=sys.stderr)
        return 2
    data = snapshot(args.catalog, max(0, args.max_samples))
    print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
