"""Registered-metadata upper bound for company_raw-internal duplicates.

Pure catalog aggregation in one read-only transaction: no file is opened, no
byte is read, nothing is written. The result is the *registered logical*
redundancy (n_internal_copies - 1) x byte_size per content hash, which the
RAW-DUP row cap alone cannot show (only 45 of 3531 groups are detailed there).
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3


def _git_common_dir() -> Path:
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


REPO = Path(__file__).resolve().parents[2]
LIVE = _git_common_dir().parent
LIVE_DB = LIVE / ".source_catalog" / "catalog.sqlite3"
OUT = REPO / ".planning" / "g3-source-facts" / "scratch" / "metadata_bound.json"
ROOT_ID = "company_raw"


def main() -> int:
    if not LIVE_DB.exists():
        raise SystemExit("live catalog database missing")
    uri = "file:" + LIVE_DB.resolve().as_posix() + "?mode=ro"
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
            {"root": ROOT_ID},
        ).fetchall()
        schema = con.execute(
            "SELECT value FROM catalog_meta WHERE key='schema_version'"
        ).fetchone()[0]
        location_status = con.execute(
            "SELECT location_status, COUNT(*) AS n FROM locations WHERE root_id = :root "
            "GROUP BY location_status",
            {"root": ROOT_ID},
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
        "scope": ROOT_ID,
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
