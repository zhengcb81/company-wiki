#!/usr/bin/env python3
"""N5-RAW-DUP: read-only assessment of duplicate raw originals.

operations:
  scan    metadata candidate scan only (stat + registered digest grouping, 0 bytes read)
  verify  the same scan plus bounded streaming SHA-256 re-check of candidate groups

The tool never deletes, moves, hard-links or copies an original, never opens a
cloud placeholder, never follows a directory outside the configured roots and
never sweeps the filesystem: only catalog-registered locations are inspected.

Exact usage:

  PYTHONPATH=src python tools/raw_duplicate_audit/cli.py verify \
      --config config/source_catalog.yaml \
      --output .planning/n5-raw-duplicate-audit/raw_duplicate_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = PACKAGE_DIR.parent
REPO_ROOT = TOOLS_DIR.parent
for _path in (REPO_ROOT / "src", TOOLS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from raw_duplicate_audit.assessment import exit_code, run_assessment  # noqa: E402
from raw_duplicate_audit.core import (  # noqa: E402
    DEADLINE_SECONDS_DEFAULT,
    MAX_DETAIL_ROWS_DEFAULT,
    MAX_GROUPS_DEFAULT,
    MAX_READ_BYTES_DEFAULT,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="raw_duplicate_audit",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", choices=("scan", "verify"))
    parser.add_argument("--config", required=True, help="read-only source_catalog.yaml")
    parser.add_argument("--output", required=True, help="report.json path (Git-safe)")
    parser.add_argument(
        "--local-output",
        default=None,
        help="optional non-Git side file holding machine-absolute paths",
    )
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--max-groups", type=int, default=MAX_GROUPS_DEFAULT)
    parser.add_argument("--max-read-bytes", type=int, default=MAX_READ_BYTES_DEFAULT)
    parser.add_argument(
        "--deadline-seconds", type=float, default=DEADLINE_SECONDS_DEFAULT
    )
    parser.add_argument("--max-detail-rows", type=int, default=MAX_DETAIL_ROWS_DEFAULT)
    parser.add_argument("--max-similar-groups", type=int, default=100)
    parser.add_argument(
        "--location-status",
        choices=("all", "active"),
        default="all",
        help="restrict catalog locations by location_status (default: all)",
    )
    parser.add_argument(
        "--hash-catalog",
        action="store_true",
        help="also record the full SHA-256 of the catalog database file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing non-audit file at --output",
    )
    parser.add_argument("--quiet", action="store_true")
    return parser


def summary(report: dict, output: Path) -> dict:
    counts = report.get("counts", {})
    recommendations = report.get("recommendations", {})
    return {
        "schema_version": report.get("schema_version"),
        "status": report.get("status"),
        "error_code": report.get("error_code"),
        "operation": report.get("operation"),
        "report_path": str(output) if report.get("written") else None,
        "candidate_groups": counts.get("candidate_groups"),
        "duplicate_groups_listed": counts.get("duplicate_groups_listed"),
        "verified_groups": counts.get("verified_groups"),
        "logical_duplicate_bytes_upper_bound": report.get(
            "logical_duplicate_bytes_upper_bound"
        ),
        "verified_duplicate_bytes": report.get("verified_duplicate_bytes"),
        "physical_allocated_bytes": report.get("physical_allocated_bytes"),
        "deleted_bytes": report.get("deleted_bytes"),
        "limits_hit": report.get("limits_hit", []),
        "read_bytes": report.get("read_bytes"),
        "read_files": report.get("read_files"),
        "elapsed_seconds": report.get("elapsed_seconds"),
        "recommendation_verdict": recommendations.get("verdict"),
        "protected_unchanged": report.get("protected_unchanged"),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_assessment(
        mode=args.mode,
        config_path=Path(args.config),
        output_path=Path(args.output),
        project_root=Path(args.project_root) if args.project_root else None,
        max_groups=args.max_groups,
        max_read_bytes=args.max_read_bytes,
        deadline_seconds=args.deadline_seconds,
        max_detail_rows=args.max_detail_rows,
        max_similar_groups=args.max_similar_groups,
        location_status=args.location_status,
        hash_catalog=args.hash_catalog,
        overwrite=args.overwrite,
        local_output_path=Path(args.local_output) if args.local_output else None,
    )
    if not args.quiet:
        print(
            json.dumps(summary(report, Path(args.output)), ensure_ascii=False, indent=2)
        )
    return exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
