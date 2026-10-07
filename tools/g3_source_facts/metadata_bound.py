"""Registered-metadata upper bound for company_raw-internal duplicates.

Pure catalog aggregation in one read-only transaction: no file is opened, no
raw byte is read, and the database is never written. Only an explicitly
requested report output is written. The result is the *registered logical*
redundancy (n_internal_copies - 1) x byte_size per content hash, which the
RAW-DUP row cap alone cannot show (only 45 of 3531 groups are detailed there).
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3


def registered_bound(database_path: Path, *, root_id: str) -> dict:
    """Aggregate one caller-selected existing database/root, without discovery."""
    path = database_path.resolve(strict=True)
    uri = path.as_uri() + '?mode=ro'
    con = sqlite3.connect(uri, uri=True, timeout=10.0)
    try:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA query_only=ON")
        con.execute("BEGIN")
        rows = con.execute(
            """
            SELECT s.content_sha256 AS sha,
                   s.byte_size AS byte_size,
                   SUM(CASE WHEN l.root_id = :root THEN 1 ELSE 0 END) AS n_internal,
                   COUNT(*) AS n_total
              FROM locations l
              JOIN sources s ON s.source_id = l.source_id
             WHERE l.source_id IS NOT NULL AND l.relative_path <> ''
             GROUP BY s.content_sha256, s.byte_size
            """,
            {"root": root_id},
        ).fetchall()
        schema = con.execute(
            "SELECT value FROM catalog_meta WHERE key='schema_version'"
        ).fetchone()[0]
        location_status = con.execute(
            "SELECT location_status, COUNT(*) AS n FROM locations WHERE root_id = :root "
            "GROUP BY location_status",
            {"root": root_id},
        ).fetchall()
        con.execute("COMMIT")
    finally:
        total_changes = int(con.total_changes)
        con.close()

    multi = [r for r in rows if r["n_internal"] >= 2]
    upper = sum((r["n_internal"] - 1) * r["byte_size"] for r in multi)
    mixed = [r for r in multi if r["n_total"] > r["n_internal"]]
    mixed_upper = sum((r["n_internal"] - 1) * r["byte_size"] for r in mixed)
    payload = {
        "scope": root_id,
        "source": "catalog metadata aggregation (read-only, 0 file reads)",
        "database_schema_version": schema,
        "total_changes": total_changes,
        "location_status": {r["location_status"]: r["n"] for r in location_status},
        "content_hashes_with_internal_copies": len(multi),
        "registered_upper_bound_bytes": upper,
        "mixed_with_other_roots_groups": len(mixed),
        "mixed_with_other_roots_upper_bound_bytes": mixed_upper,
        "distinct_single_copy_hashes": sum(1 for r in rows if r["n_internal"] == 1),
        "note": (
            "upper bound = sum((internal_copies - 1) * registered byte_size); it is a "
            "registered logical bound, not an allocated or releasable byte claim"
        ),
    }
    payload['allocated_bytes'] = None
    payload['releasable_bytes'] = None
    return payload


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--root-id', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.output and args.output.resolve() == args.database.resolve():
        parser.error('report output must differ from the input database')
    payload = registered_bound(args.database, root_id=args.root_id)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
