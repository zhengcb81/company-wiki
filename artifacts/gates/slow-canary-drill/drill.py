"""WR-10.13 controlled slow-canary drill on an ISOLATED catalog.

Runs scan + normalize + fingerprint-backfill against a real large PDF in a
throwaway catalog dir so the production DB is never touched. Uses shortened
parser timeout / heartbeat (ratio equivalent to the old 900s watchdog / 3600s
parser timeout) so the "slow document exceeds old watchdog" scenario is
observable without sleeping a real 900 seconds. The drill records every
parser_alive heartbeat, the elapsed wall time, that the parser PID stayed
single-stable, that no .parser-result temp leaks remain, and that the run
completed (or hit a clean terminal) rather than being killed mid-way.

Output: writes a JSON receipt to --out.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--catalog-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--parser-timeout-seconds", type=float, default=600.0)
    ap.add_argument("--heartbeat-interval-seconds", type=float, default=5.0)
    ap.add_argument("--scan-files", type=int, default=0)
    args = ap.parse_args()

    source_root = Path(args.source_root).resolve()
    catalog_dir = Path(args.catalog_dir).resolve()
    catalog_dir.mkdir(parents=True, exist_ok=True)

    config = CatalogConfig(
        project_root=PROJECT,
        catalog_dir=catalog_dir,
        roots=(RootSpec("canary_root", source_root, "directory"),),
    )
    catalog = SourceCatalog(config)

    heartbeats: list[dict[str, Any]] = []
    scan_heartbeats: list[dict[str, Any]] = []
    norm_heartbeats: list[dict[str, Any]] = []
    fp_heartbeats: list[dict[str, Any]] = []
    start = time.time()

    def make_progress(target: list[dict[str, Any]], stage_name: str):
        def _progress(**kw: Any) -> None:
            stamp = {**kw, "t": round(time.time() - start, 3), "stage": stage_name}
            heartbeats.append(stamp)
            target.append(stamp)

        return _progress

    scan = catalog.scan(progress=make_progress(scan_heartbeats, "scan"))
    scanned = scan.files_seen if hasattr(scan, "files_seen") else None

    norm = catalog.normalize(
        limit=1,
        progress=make_progress(norm_heartbeats, "normalize"),
        parser_timeout_seconds=args.parser_timeout_seconds,
        parser_heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        retry_limit=2,
        retry_backoff_seconds=0,
    )
    norm_secs = time.time() - start

    fp = catalog.backfill_text_fingerprints(
        limit=1,
        progress=make_progress(fp_heartbeats, "fingerprint"),
        retry_limit=2,
        retry_backoff_seconds=0,
        parser_timeout_seconds=args.parser_timeout_seconds,
        parser_heartbeat_interval_seconds=args.heartbeat_interval_seconds,
    )
    fp_secs = time.time() - start

    # orphan / temp check
    temp_leaks = list(catalog_dir.glob("**/.parser-result-*.json"))

    def _pid_stats(hbs: list[dict[str, Any]]) -> dict[str, Any]:
        pids = {h.get("parser_pid") for h in hbs if h.get("parser_pid") is not None}
        return {
            "count": len(hbs),
            "parser_alive_count": sum(
                1 for h in hbs if h.get("detail") == "parser_alive"
            ),
            "parser_pids_seen": sorted(str(p) for p in pids),
            "parser_pid_stable": len(pids) == 1,
            "max_elapsed_on_path": max(
                (h.get("parser_elapsed_seconds") or 0 for h in hbs), default=0
            ),
        }

    norm_hb = _pid_stats(norm_heartbeats)
    fp_hb = _pid_stats(fp_heartbeats)

    summary = {
        "schema_version": "1.0",
        "work_unit": "WR-10.13",
        "title": "controlled slow-canary drill (isolated catalog)",
        "verdict": None,
        "source_root": str(source_root),
        "catalog_dir": str(catalog_dir),
        "config": {
            "parser_timeout_seconds": args.parser_timeout_seconds,
            "heartbeat_interval_seconds": args.heartbeat_interval_seconds,
            "note": "shortened clock; ratio equivalent to old 900s watchdog / 3600s parser timeout",
        },
        "scan": {
            "files_seen": scanned,
            "locations_active": scan.locations_active,
            "new_errors": scan.new_errors,
        },
        "normalize": {
            "completed": norm.completed,
            "failed": norm.failed,
            "unsupported": norm.unsupported,
            "partial": norm.partial,
            "wall_seconds": round(norm_secs, 3),
        },
        "fingerprint": {
            "completed": fp.completed,
            "failed": fp.failed,
            "unsupported": fp.unsupported,
            "partial": fp.partial,
            "wall_seconds": round(fp_secs, 3),
        },
        "heartbeat": {
            "count": len(heartbeats),
            "normalize": norm_hb,
            "fingerprint": fp_hb,
        },
        "temp_leaks_after": [str(p) for p in temp_leaks],
        "total_wall_seconds": round(time.time() - start, 3),
    }

    ok = (
        scan.locations_active >= 1
        and norm.completed == 1
        and fp.completed == 1
        and norm_hb["parser_pid_stable"]
        and fp_hb["parser_pid_stable"]
        and not temp_leaks
    )
    summary["verdict"] = "accepted" if ok else "rejected"
    summary["reason"] = (
        "scan found canary, normalize completed, fingerprint completed, "
        "each operation kept one stable parser PID, no temp leaks"
        if ok
        else "one or more checks failed; see fields"
    )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
