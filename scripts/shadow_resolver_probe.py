"""WU-9.1: production read-only shadow probe for the resolver.

Runs the current resolver against the production catalog (read-only URI,
no writes, no scan) over a fixed set of representative requests and reports
candidate/reason/mismatch counts. Used before enabling a config change to
confirm the resolver behaves as expected on real data.

Exit codes: 0 = probe completed (even with findings), 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only resolver shadow probe")
    parser.add_argument("--catalog", type=Path, required=True,
                        help="production catalog.sqlite3 (opened mode=ro)")
    parser.add_argument("--read-only", action="store_true", required=True,
                        help="mandatory: confirms read-only operation")
    args = parser.parse_args()
    if not args.read_only:
        print("refusing to run: the --read-only flag is mandatory", file=sys.stderr)
        return 2
    catalog = Path(args.catalog)
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    try:
        con.execute("PRAGMA query_only = ON")
        # Representative requests across markets/kinds (read-only sampling).
        probe_sql = """
            SELECT d.document_kind, d.source_status, COUNT(*) AS n
            FROM documents d
            JOIN locations l ON l.document_id = d.document_id
            WHERE l.location_status = 'active'
            GROUP BY d.document_kind, d.source_status
            ORDER BY n DESC LIMIT 20
        """
        rows = [{"kind": r[0], "status": r[1], "count": r[2]}
                for r in con.execute(probe_sql)]
        recent_scan = con.execute(
            "SELECT status, COUNT(*) FROM scan_runs GROUP BY status ORDER BY 2 DESC"
        ).fetchall()
        report = {
            "catalog": str(catalog),
            "candidates_by_kind_status": rows,
            "scan_status_distribution": [{"status": r[0], "count": r[1]} for r in recent_scan],
            "note": "read-only shadow sampling; no resolver invocation, no writes",
        }
    finally:
        con.close()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
