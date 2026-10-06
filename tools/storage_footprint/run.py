"""N6-FOOTPRINT command line entry point.

Read-only by construction: no model, no network, no database open, no content
read of any scanned file. One JSON line goes to stdout; exit code 0 means the
report was written (complete or explicitly partial), 2 means refused without
writing, 1 means an internal failure with temp output cleaned up.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap_sys_path() -> None:
    tools_dir = str(Path(__file__).resolve().parents[1])
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="storage_footprint/run.py",
        description=(
            "Read-only storage footprint scan of one explicit project root "
            "(metadata only; 256 KiB report budget)."
        ),
    )
    parser.add_argument(
        "--project-root",
        required=True,
        help="explicit root directory to scan (only this root is measured)",
    )
    parser.add_argument(
        "--max-files",
        required=True,
        type=int,
        help="hard file-entry budget; the scan stops exactly at this count",
    )
    parser.add_argument(
        "--max-seconds",
        required=True,
        type=float,
        help="wall-clock budget checked at operation boundaries",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="new report file; refuses unknown pre-existing targets and any path inside the scanned root",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _bootstrap_sys_path()
    args = build_parser().parse_args(argv)
    from storage_footprint.runner import run_scan

    code, payload = run_scan(
        project_root=args.project_root,
        max_files=args.max_files,
        max_seconds=args.max_seconds,
        output=args.output,
    )
    print(json.dumps(payload, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
