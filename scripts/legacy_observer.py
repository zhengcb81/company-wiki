"""WU-1500: legacy observation period reporter — read-only.

Runs a read-only resolver pass over the production catalog with an
observer attached, reporting legacy_bridge_hits for the current
observation period.  Period bookkeeping (started_at, hits, freeze gate
status) is recorded to a JSON file next to the catalog; the production
catalog and real roots are never written.

Usage: python scripts/legacy_observer.py --catalog <catalog.sqlite3> \
       --period <n> --period-file <periods.json> --read-only
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from company_wiki.source_catalog.observability import MetricsCollector  # noqa: E402
from company_wiki.source_catalog.resolver import _source_metadata  # noqa: E402


def observe(
    catalog: Path,
    *,
    sample_limit: int = 2000,
) -> dict:
    """Read-only legacy bridge observation over active documents."""
    con = sqlite3.connect(f"file:{catalog}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    collector = MetricsCollector()
    rows = con.execute(
        """SELECT d.document_id, d.metadata_json, d.primary_source_id
           FROM documents d
           WHERE d.source_type='regulatory_filing'
             AND d.source_status='active'
             AND d.metadata_json LIKE '%acquisition%'
           LIMIT ?""",
        (sample_limit,),
    ).fetchall()
    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except json.JSONDecodeError:
            metadata = {}
        _source_metadata({"source_id": row["primary_source_id"],
                          "metadata": metadata}, observer=collector)
    con.close()
    report = collector.snapshot()
    return {
        "sampled_documents": len(rows),
        "legacy_bridge_hits": report.legacy_bridge_hits,
        "shadow_diffs": report.shadow_diffs,
        "reasons": report.aggregate("reason"),
    }


def _load_periods(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"periods": []}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="WU-1500 legacy observer")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--period", type=int, required=True)
    parser.add_argument("--period-file", type=Path, required=True)
    parser.add_argument("--read-only", action="store_true", required=True)
    parser.add_argument("--sample-limit", type=int, default=2000)
    args = parser.parse_args()
    if not args.read_only:
        print("refusing: --read-only is mandatory", file=sys.stderr)
        return 2

    result = observe(args.catalog, sample_limit=args.sample_limit)
    periods = _load_periods(args.period_file)
    existing = [p for p in periods["periods"] if p["period"] == args.period]
    if existing:
        entry = existing[0]
        entry["ended_at"] = None  # still observing
        entry["legacy_bridge_hits"] = result["legacy_bridge_hits"]
    else:
        periods["periods"].append({
            "period": args.period,
            "started_at": "2026-08-09T00:00:00Z",
            "legacy_bridge_hits": result["legacy_bridge_hits"],
            "shadow_diffs": result["shadow_diffs"],
            "sampled_documents": result["sampled_documents"],
            "freeze_gate": "no new callers (resolver._source_metadata only)",
            "status": "observing",
        })
    periods["periods"].sort(key=lambda p: p["period"])
    args.period_file.parent.mkdir(parents=True, exist_ok=True)
    args.period_file.write_text(
        json.dumps(periods, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
