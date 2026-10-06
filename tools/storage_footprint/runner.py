"""Orchestration: validate inputs, scan, build, enforce budget, write atomically."""

from __future__ import annotations

from pathlib import Path

from . import report as report_module
from .core import (
    REPORT_SCHEMA,
    ReportTooLarge,
    error_label,
    paths_overlap,
    report_is_ours,
    write_report,
)
from .report import build_report, enforce_report_budget
from .scan import scan_tree

REFUSED = 2
FAILED = 1
WRITTEN = 0


def _base_payload(status: str, reason: str) -> dict:
    return {"schema_version": REPORT_SCHEMA, "status": status, "reason": reason}


def run_scan(
    *,
    project_root: str | Path,
    max_files: int,
    max_seconds: float,
    output: str | Path,
) -> tuple[int, dict]:
    """Run one bounded read-only scan and write the report.

    Exit codes: ``0`` report written (complete or explicit partial), ``2``
    refused without touching the target, ``1`` internal failure after temp
    output cleanup.
    """
    root_text = str(project_root)
    root = Path(project_root)
    try:
        root_ok = root.is_dir()
    except OSError:
        root_ok = False
    if not root_ok:
        return REFUSED, _base_payload("refused", "invalid_root")
    try:
        files_limit = int(max_files)
        seconds_limit = float(max_seconds)
    except (TypeError, ValueError):
        return REFUSED, _base_payload("refused", "invalid_limits")
    if files_limit <= 0 or seconds_limit <= 0:
        return REFUSED, _base_payload("refused", "invalid_limits")

    output_path = Path(output)
    if paths_overlap(output_path, root):
        return REFUSED, _base_payload("refused", "report_path_overlaps_data")
    if output_path.exists() and not report_is_ours(output_path):
        return REFUSED, _base_payload("refused", "output_exists_unknown")

    try:
        result = scan_tree(root, max_files=files_limit, max_seconds=seconds_limit)
    except OSError as error:
        payload = _base_payload("error", "scan_failed")
        payload["error"] = error_label(error)
        return FAILED, payload

    payload = build_report(
        result,
        project_root_text=root_text,
        limits={"max_files": files_limit, "max_seconds": seconds_limit},
    )
    limit = report_module.MAX_REPORT_BYTES
    try:
        payload, _notes = enforce_report_budget(payload, max_bytes=limit)
        written = write_report(output_path, payload, max_bytes=limit)
    except ReportTooLarge:
        return FAILED, _base_payload("error", "report_too_large")
    except FileExistsError:
        return REFUSED, _base_payload("refused", "output_exists_unknown")
    except OSError as error:
        failure = _base_payload("error", "write_failed")
        failure["error"] = error_label(error)
        return FAILED, failure

    return WRITTEN, {
        "status": "written",
        "schema_version": REPORT_SCHEMA,
        "output": str(output_path),
        "complete": payload["scope"]["complete"],
        "stop_reason": payload["scope"]["stop_reason"],
        "files_measured": payload["totals"]["files_measured"],
        "logical_path_bytes": payload["totals"]["logical_path_bytes"],
        "report_bytes": written.stat().st_size,
    }
