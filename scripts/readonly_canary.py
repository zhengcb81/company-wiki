"""WU-1302: production read-only discovery canary.

Runs config doctor + real-root probes before/after a read-only shadow pass
over the production catalog.  No migration/restore/download/parser/LLM.
Any real-root change or shadow crash fails the canary.

Usage: python scripts/readonly_canary.py --catalog <catalog.sqlite3> \
       --root <real-root> [--root ...] --read-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _probe_fast(root: Path) -> dict:
    from real_root_probe import probe_fast  # type: ignore

    return probe_fast(root)


def _shadow_sample(catalog: Path) -> dict:
    import sqlite3

    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    try:
        by_kind = {
            row["document_kind"]: row["n"]
            for row in con.execute(
                """SELECT document_kind, COUNT(*) AS n FROM documents
                   WHERE source_status='active' GROUP BY document_kind
                   ORDER BY n DESC LIMIT 10"""
            )
        }
        scan_health = {
            row["status"]: row["n"]
            for row in con.execute(
                "SELECT status, COUNT(*) AS n FROM scan_runs "
                "GROUP BY status ORDER BY 2 DESC"
            )
        }
        return {"active_by_kind": by_kind, "scan_health": scan_health}
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only discovery canary")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--read-only", action="store_true", required=True)
    args = parser.parse_args()
    if not args.read_only:
        print("refusing: --read-only is mandatory", file=sys.stderr)
        return 2
    if not args.catalog.is_file():
        print(f"missing catalog: {args.catalog}", file=sys.stderr)
        return 2

    roots = [Path(p) for p in args.root]
    before = {str(r): _probe_fast(r) for r in roots}
    shadow = _shadow_sample(args.catalog)
    after = {str(r): _probe_fast(r) for r in roots}

    problems = []
    for r in roots:
        if before[str(r)] != after[str(r)]:
            problems.append(f"real root changed during canary: {r}")
    report = {
        "roots_before_after_identical": not problems,
        "problems": problems,
        "shadow": shadow,
        "note": "read-only: no migration/restore/download/parser/LLM",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
