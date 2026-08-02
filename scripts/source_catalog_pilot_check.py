"""Read-only pilot verification: sample worker status, DB, and process health.

Usage:
  python scripts/source_catalog_pilot_check.py --duration-minutes 30 --interval-seconds 60 --json-out artifacts/gates/source-catalog-bg/pilot.json
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from hashlib import sha256
from pathlib import Path
from typing import Any


DEFAULT_HEARTBEAT_STALE_SECONDS = 180


def sample_status(project_root: Path) -> dict[str, Any]:
    import subprocess

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "company_wiki.source_catalog.cli",
                "--config",
                str(project_root / "config" / "source_catalog.yaml"),
                "worker-status",
                "--worker-config",
                str(project_root / "config" / "source_catalog_worker.yaml"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
            timeout=30,
            cwd=str(project_root),
            env={**os.environ, "PYTHONUTF8": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": f"worker-status unavailable: {type(exc).__name__}"}
    if result.returncode != 0:
        return {"error": "worker-status failed", "stderr": result.stderr[:500]}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid JSON", "stdout": result.stdout[:500]}


def check_raw_safety(project_root: Path, sample_count: int = 5) -> dict[str, Any]:
    companies_dir = project_root / "companies"
    samples = []
    sample_hashes = []
    if companies_dir.is_dir():
        pdfs = sorted(companies_dir.rglob("*.pdf"))
        import hashlib

        for pdf_path in pdfs[:sample_count]:
            h = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            samples.append(str(pdf_path.relative_to(project_root)))
            sample_hashes.append(h)
    return {"samples": samples, "hashes": sample_hashes}


def snapshot_tree_metadata(root: Path) -> dict[str, Any]:
    """Hash path, size, and mtime without reading another repository's contents."""
    if not root.is_dir():
        return {"available": False, "root": str(root), "files": 0, "digest": None}
    digest = sha256()
    files = 0
    for path in sorted(
        item
        for item in root.rglob("*")
        if item.is_file() and ".git" not in item.relative_to(root).parts
    ):
        stat = path.stat()
        relative = path.relative_to(root).as_posix()
        digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
        files += 1
    return {
        "available": True,
        "root": str(root),
        "files": files,
        "digest": digest.hexdigest(),
    }


def check_database(project_root: Path) -> dict[str, Any]:
    from company_wiki.source_catalog import load_catalog_config

    config = load_catalog_config(
        project_root / "config" / "source_catalog.yaml",
        project_root=project_root,
    )
    started_at = time.time()
    connection = sqlite3.connect(
        f"{config.database_path.resolve().as_uri()}?mode=ro",
        uri=True,
        timeout=30,
    )
    try:
        result = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    finally:
        connection.close()
    return {
        "quick_check": result,
        "elapsed_seconds": round(time.time() - started_at, 1),
    }


def summarize_pilot(
    *,
    samples: list[dict[str, Any]],
    start_time: float,
    end_time: float,
    raw_baseline: dict[str, Any],
    raw_final: dict[str, Any],
    database_check: dict[str, Any],
    stockwiki_baseline: dict[str, Any],
    stockwiki_final: dict[str, Any],
    heartbeat_stale_seconds: int = DEFAULT_HEARTBEAT_STALE_SECONDS,
    max_same_path_seconds: int = 900,
    require_progress: bool = False,
    minimum_normalized_delta: int = 15,
    required_export_progress_total: int | None = None,
    require_visible_scan_enumeration: bool = False,
    require_supervisor: bool = False,
    require_code_match: bool = False,
) -> dict[str, Any]:
    first_pending = samples[0]["markdown_pending"] if samples else None
    last_pending = samples[-1]["markdown_pending"] if samples else None
    first_normalized = samples[0]["markdown_completed"] if samples else None
    last_normalized = samples[-1]["markdown_completed"] if samples else None
    first_artifacts = samples[0]["artifact_rows"] if samples else None
    last_artifacts = samples[-1]["artifact_rows"] if samples else None
    raw_stale_count = sum(
        1
        for sample in samples
        if sample.get("heartbeat_age") is not None
        and float(sample["heartbeat_age"]) > heartbeat_stale_seconds
    )

    def same_path_limit(sample: dict[str, Any]) -> float:
        parser_timeout = sample.get("parser_timeout_seconds")
        if sample.get("parser_pid") is not None and parser_timeout is not None:
            return float(parser_timeout) + heartbeat_stale_seconds
        return float(max_same_path_seconds)

    stale_count = sum(
        1
        for sample in samples
        if sample.get("heartbeat_age") is not None
        and float(sample["heartbeat_age"]) > heartbeat_stale_seconds
        and not (
            sample.get("parser_pid") is None
            and
            sample.get("current_path")
            and sample.get("current_path_elapsed_seconds") is not None
            and float(sample["current_path_elapsed_seconds"])
            < same_path_limit(sample)
        )
    )
    production_counts = [
        int(sample.get("production_workers", 0)) for sample in samples
    ]
    foreign_count = max(
        (int(sample.get("foreign_workers", 0)) for sample in samples),
        default=0,
    )
    pytest_count = max(
        (int(sample.get("pytest_temp_workers", 0)) for sample in samples),
        default=0,
    )
    production_supervisor_counts = [
        int(sample.get("production_supervisors", 0)) for sample in samples
    ]
    production_supervisor_min = min(production_supervisor_counts, default=0)
    production_supervisor_max = max(production_supervisor_counts, default=0)
    foreign_supervisor_count = max(
        (int(sample.get("foreign_supervisors", 0)) for sample in samples),
        default=0,
    )
    pytest_supervisor_count = max(
        (int(sample.get("pytest_temp_supervisors", 0)) for sample in samples),
        default=0,
    )
    production_supervisor_pids = sorted(
        {
            int(pid)
            for sample in samples
            for pid in (sample.get("production_supervisor_pids") or [])
        }
    )
    repeated_cycle_error = None
    repeated_cycle_failure_count = 0
    cycle_failures: dict[str, set[float]] = {}
    for sample in samples:
        if sample.get("last_cycle_status") != "failed":
            continue
        error = str(sample.get("last_cycle_error") or "").strip()
        cycle_at = sample.get("last_cycle_at")
        if not error or cycle_at is None:
            continue
        cycle_failures.setdefault(error, set()).add(float(cycle_at))
    if cycle_failures:
        repeated_cycle_error, attempts = max(
            cycle_failures.items(), key=lambda item: len(item[1])
        )
        repeated_cycle_failure_count = len(attempts)
        if repeated_cycle_failure_count < 2:
            repeated_cycle_error = None
    production_min = min(production_counts, default=0)
    production_max = max(production_counts, default=0)
    runtime_all_running = bool(samples) and all(
        sample.get("runtime_state") == "running" for sample in samples
    )
    production_pids = {
        int(sample["pid"]) for sample in samples if sample.get("pid") is not None
    }
    loaded_code_fingerprints = sorted(
        {
            str(sample["loaded_code_fingerprint"])
            for sample in samples
            if sample.get("loaded_code_fingerprint")
        }
    )
    current_code_fingerprints = sorted(
        {
            str(sample["current_code_fingerprint"])
            for sample in samples
            if sample.get("current_code_fingerprint")
        }
    )
    code_match_all = bool(samples) and all(
        sample.get("code_match") is True for sample in samples
    )
    raw_sample_unchanged = raw_baseline == raw_final
    stockwiki_unchanged = (
        stockwiki_baseline.get("available") is True
        and stockwiki_baseline == stockwiki_final
    )
    interrupted_counts = [
        sample.get("scan_interrupted_count")
        for sample in samples
        if sample.get("scan_interrupted_count") is not None
    ]
    scan_interrupted_delta = (
        int(interrupted_counts[-1]) - int(interrupted_counts[0])
        if interrupted_counts
        else None
    )
    baseline_scan_run_id = samples[0].get("last_scan_run_id") if samples else None
    seen_scan_run_ids = {baseline_scan_run_id} if baseline_scan_run_id else set()
    new_scan_error_count = 0
    new_scan_error_runs: list[str] = []
    for sample in samples[1:]:
        run_id = sample.get("last_scan_run_id")
        if not run_id or run_id in seen_scan_run_ids:
            continue
        seen_scan_run_ids.add(run_id)
        new_error_count = int(sample.get("last_scan_new_errors") or 0)
        if new_error_count > 0:
            new_scan_error_count += new_error_count
            new_scan_error_runs.append(str(run_id))
    same_path_max_seconds = max(
        (
            float(sample.get("current_path_elapsed_seconds") or 0)
            for sample in samples
        ),
        default=0.0,
    )
    same_path_timeout_samples = [
        sample
        for sample in samples
        if sample.get("current_path_elapsed_seconds") is not None
        and float(sample["current_path_elapsed_seconds"]) >= same_path_limit(sample)
    ]
    parser_pids_by_path: dict[str, set[int]] = {}
    for sample in samples:
        current_path = sample.get("current_path")
        parser_pid = sample.get("parser_pid")
        if current_path and parser_pid is not None:
            parser_pids_by_path.setdefault(str(current_path), set()).add(int(parser_pid))
    restarted_parser_paths = sorted(
        path for path, pids in parser_pids_by_path.items() if len(pids) > 1
    )
    parse_timeout_counts = [
        int(sample["parse_timeout_total"])
        for sample in samples
        if sample.get("parse_timeout_total") is not None
    ]
    parse_timeout_delta = (
        parse_timeout_counts[-1] - parse_timeout_counts[0]
        if parse_timeout_counts
        else None
    )
    pending_delta = (
        first_pending - last_pending
        if first_pending is not None and last_pending is not None
        else None
    )
    artifact_delta = (
        last_artifacts - first_artifacts
        if first_artifacts is not None and last_artifacts is not None
        else None
    )
    normalized_delta = (
        last_normalized - first_normalized
        if first_normalized is not None and last_normalized is not None
        else None
    )
    progress_observed = bool(
        (normalized_delta is not None and normalized_delta > 0)
        or (pending_delta is not None and pending_delta > 0)
        or (artifact_delta is not None and artifact_delta > 0)
    )
    throughput_pass = bool(
        (normalized_delta is not None and normalized_delta >= minimum_normalized_delta)
        or (pending_delta is not None and pending_delta > 0)
    )
    export_progress_totals = sorted(
        {
            int(total)
            for sample in samples
            for total in (
                sample.get("progress_total")
                if sample.get("worker_status") == "exporting"
                else None,
                sample.get("last_export_progress_total"),
            )
            if total is not None
        }
    )
    export_progress_contract_observed = (
        required_export_progress_total is None
        or required_export_progress_total in export_progress_totals
    )
    scan_enumeration_samples = [
        sample
        for sample in samples
        if sample.get("worker_status") == "scanning"
        and str(sample.get("progress_detail") or "").startswith("enumerating root ")
    ]
    scan_enumeration_running_visible = bool(scan_enumeration_samples) and all(
        sample.get("latest_running_scan") is not None
        for sample in scan_enumeration_samples
    )
    checks = [
        ("no_samples", bool(samples), "WR-6"),
        ("runtime_not_running", runtime_all_running, "WR-2"),
        (
            "production_worker_count_not_one",
            production_min == 1 and production_max == 1,
            "WR-1",
        ),
        ("production_pid_changed", len(production_pids) == 1, "WR-2"),
        (
            "worker_code_mismatch_or_unknown",
            not require_code_match or code_match_all,
            "WR-10",
        ),
        ("heartbeat_stale", stale_count == 0, "WR-4"),
        ("foreign_worker_present", foreign_count == 0, "WR-1"),
        ("pytest_temp_worker_present", pytest_count == 0, "WR-3"),
        (
            "production_supervisor_count_not_one",
            not require_supervisor
            or (
                production_supervisor_min == 1
                and production_supervisor_max == 1
            ),
            "WR-10",
        ),
        (
            "production_supervisor_pid_changed",
            not require_supervisor or len(production_supervisor_pids) == 1,
            "WR-10",
        ),
        (
            "foreign_supervisor_present",
            not require_supervisor or foreign_supervisor_count == 0,
            "WR-10",
        ),
        (
            "pytest_temp_supervisor_present",
            not require_supervisor or pytest_supervisor_count == 0,
            "WR-10",
        ),
        (
            "database_quick_check_failed",
            database_check.get("quick_check") == "ok",
            "WR-7",
        ),
        ("raw_sample_changed", raw_sample_unchanged, "WR-6"),
        ("stockwiki_changed_or_unavailable", stockwiki_unchanged, "WR-6"),
        (
            "scan_interrupted_delta_nonzero",
            scan_interrupted_delta is None or scan_interrupted_delta == 0,
            "WR-4",
        ),
        ("scan_new_errors_nonzero", new_scan_error_count == 0, "WR-10"),
        (
            "same_path_timeout",
            not same_path_timeout_samples,
            "WR-6",
        ),
        (
            "same_path_parser_restarted",
            not restarted_parser_paths,
            "WR-10",
        ),
        (
            "normalization_timeout_delta_nonzero",
            parse_timeout_delta is None or parse_timeout_delta == 0,
            "WR-10",
        ),
        (
            "repeated_cycle_failure",
            repeated_cycle_failure_count < 2,
            "WR-10",
        ),
        (
            "throughput_below_required_threshold",
            not require_progress or throughput_pass,
            "WR-6",
        ),
        (
            "required_export_progress_contract_not_observed",
            export_progress_contract_observed,
            "WR-8",
        ),
        (
            "scan_enumeration_running_record_not_visible",
            not require_visible_scan_enumeration
            or scan_enumeration_running_visible,
            "WR-9",
        ),
    ]
    first_failure = next((name for name, ok, _phase in checks if not ok), None)
    recommended_next_phase = next(
        (phase for _name, ok, phase in checks if not ok),
        None,
    )
    last_good_sample = next(
        (
            sample
            for sample in reversed(samples)
            if sample.get("runtime_state") == "running"
            and int(sample.get("production_workers", 0)) == 1
            and int(sample.get("foreign_workers", 0)) == 0
            and int(sample.get("pytest_temp_workers", 0)) == 0
            and (
                not require_supervisor
                or (
                    int(sample.get("production_supervisors", 0)) == 1
                    and int(sample.get("foreign_supervisors", 0)) == 0
                    and int(sample.get("pytest_temp_supervisors", 0)) == 0
                )
            )
            and (
                sample.get("heartbeat_age") is None
                or float(sample["heartbeat_age"]) <= heartbeat_stale_seconds
                or (
                    sample.get("parser_pid") is None
                    and
                    sample.get("current_path")
                    and sample.get("current_path_elapsed_seconds") is not None
                    and float(sample["current_path_elapsed_seconds"])
                    < same_path_limit(sample)
                )
            )
        ),
        None,
    )
    passed = first_failure is None
    return {
        "pilot_pass": passed,
        "first_failure": first_failure,
        "recommended_next_phase": recommended_next_phase,
        "last_good_sample": last_good_sample,
        "duration_minutes": round((end_time - start_time) / 60, 1),
        "sample_count": len(samples),
        "runtime_all_running": runtime_all_running,
        "production_worker_count": production_max,
        "production_worker_min": production_min,
        "production_worker_pids": sorted(production_pids),
        "code_match_required": require_code_match,
        "code_match_all": code_match_all,
        "loaded_code_fingerprints": loaded_code_fingerprints,
        "current_code_fingerprints": current_code_fingerprints,
        "heartbeat_stale_threshold_seconds": heartbeat_stale_seconds,
        "raw_heartbeat_stale_count": raw_stale_count,
        "heartbeat_stale_count": stale_count,
        "foreign_worker_max": foreign_count,
        "pytest_temp_worker_max": pytest_count,
        "supervisor_required": require_supervisor,
        "production_supervisor_min": production_supervisor_min,
        "production_supervisor_max": production_supervisor_max,
        "production_supervisor_pids": production_supervisor_pids,
        "repeated_cycle_failure_count": repeated_cycle_failure_count,
        "repeated_cycle_error": repeated_cycle_error,
        "foreign_supervisor_max": foreign_supervisor_count,
        "pytest_temp_supervisor_max": pytest_supervisor_count,
        "pending_start": first_pending,
        "pending_end": last_pending,
        "pending_delta": pending_delta,
        "normalized_start": first_normalized,
        "normalized_end": last_normalized,
        "normalized_delta": normalized_delta,
        "minimum_normalized_delta": minimum_normalized_delta,
        "artifact_start": first_artifacts,
        "artifact_end": last_artifacts,
        "artifact_delta": artifact_delta,
        "progress_required": require_progress,
        "progress_observed": progress_observed,
        "throughput_pass": throughput_pass,
        "required_export_progress_total": required_export_progress_total,
        "export_progress_totals_observed": export_progress_totals,
        "export_progress_contract_observed": export_progress_contract_observed,
        "scan_enumeration_sample_count": len(scan_enumeration_samples),
        "scan_enumeration_running_visible": scan_enumeration_running_visible,
        "visible_scan_enumeration_required": require_visible_scan_enumeration,
        "same_path_max_seconds": round(same_path_max_seconds, 1),
        "same_path_limit_seconds": max_same_path_seconds,
        "same_path_timeout_sample_count": len(same_path_timeout_samples),
        "restarted_parser_paths": restarted_parser_paths,
        "parse_timeout_delta": parse_timeout_delta,
        "scan_interrupted_delta": scan_interrupted_delta,
        "new_scan_error_count": new_scan_error_count,
        "new_scan_error_runs": new_scan_error_runs,
        "db_quick_check": database_check.get("quick_check"),
        "db_quick_check_elapsed_seconds": database_check.get("elapsed_seconds"),
        "raw_samples": raw_baseline["samples"],
        "raw_sample_unchanged": raw_sample_unchanged,
        "stockwiki_writes": 0 if stockwiki_unchanged else None,
        "stockwiki_write_check": "path/size/mtime metadata snapshot",
        "stockwiki_unchanged": stockwiki_unchanged,
        "stockwiki_files": stockwiki_final.get("files"),
        "samples": samples,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only Source Catalog worker pilot verification."
    )
    parser.add_argument("--duration-minutes", type=int, default=30)
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument(
        "--heartbeat-stale-seconds",
        type=int,
        default=DEFAULT_HEARTBEAT_STALE_SECONDS,
    )
    parser.add_argument("--max-same-path-seconds", type=int, default=900)
    parser.add_argument("--minimum-normalized-delta", type=int, default=15)
    parser.add_argument("--require-progress", action="store_true")
    parser.add_argument("--require-export-progress-total", type=int)
    parser.add_argument(
        "--require-visible-scan-enumeration",
        action="store_true",
    )
    parser.add_argument("--require-supervisor", action="store_true")
    parser.add_argument("--require-code-match", action="store_true")
    parser.add_argument("--json-out")
    parser.add_argument("--dry-run", action="store_true")
    parsed = parser.parse_args(argv)
    for field in (
        "duration_minutes",
        "interval_seconds",
        "heartbeat_stale_seconds",
        "max_same_path_seconds",
    ):
        if getattr(parsed, field) <= 0:
            parser.error(f"--{field.replace('_', '-')} must be greater than zero")
    if parsed.minimum_normalized_delta < 0:
        parser.error("--minimum-normalized-delta must be zero or greater")
    if (
        parsed.require_export_progress_total is not None
        and parsed.require_export_progress_total < 0
    ):
        parser.error("--require-export-progress-total must be zero or greater")
    return parsed


def main(argv: list[str] | None = None):
    project_root = Path(__file__).resolve().parents[1]
    args = _parse_args(argv)
    duration_minutes = args.duration_minutes
    interval_seconds = args.interval_seconds
    heartbeat_stale_seconds = args.heartbeat_stale_seconds
    max_same_path_seconds = args.max_same_path_seconds
    minimum_normalized_delta = args.minimum_normalized_delta
    require_progress = args.require_progress
    required_export_progress_total = args.require_export_progress_total
    require_visible_scan_enumeration = args.require_visible_scan_enumeration
    require_supervisor = args.require_supervisor
    require_code_match = args.require_code_match
    dry_run = args.dry_run
    json_out = args.json_out

    if dry_run:
        print(
            "Dry-run OK. Would sample for {} minutes at {}s intervals.".format(
                duration_minutes, interval_seconds
            )
        )
        return 0

    start_time = time.time()
    deadline = start_time + duration_minutes * 60
    samples: list[dict[str, Any]] = []
    raw_baseline = check_raw_safety(project_root)
    stockwiki_baseline = snapshot_tree_metadata(project_root.parent / "StockWiki")

    while time.time() < deadline:
        sample_time = time.time()
        status = sample_status(project_root)
        st = status.get("runtime_state", "unknown")
        hb = status.get("heartbeat_age_seconds")
        pipeline = status.get("pipeline", {})
        last_scan = pipeline.get("last_scan") or {}
        md = pipeline.get("markdown", {})
        artifacts = pipeline.get("health", {}).get("artifacts", {})
        inv = status.get("process_inventory", {})
        scheduler = status.get("scheduler", {})
        lock_health = pipeline.get("health", {}).get("locks", {})

        samples.append(
            {
                "timestamp": sample_time,
                "runtime_state": st,
                "pid": status.get("pid"),
                "heartbeat_age": hb,
                "worker_status": status.get("worker_status"),
                "progress_current": status.get("progress_current"),
                "progress_total": status.get("progress_total"),
                "progress_detail": status.get("progress_detail"),
                "current_path": status.get("current_path"),
                "current_path_elapsed_seconds": status.get(
                    "current_path_elapsed_seconds"
                ),
                "parser_pid": status.get("parser_pid"),
                "parser_elapsed_seconds": status.get("parser_elapsed_seconds"),
                "parser_timeout_seconds": status.get("parser_timeout_seconds"),
                "parser_ownership": status.get("parser_ownership"),
                "loaded_code_fingerprint": status.get("loaded_code_fingerprint"),
                "current_code_fingerprint": status.get("current_code_fingerprint"),
                "code_match": status.get("code_match"),
                "markdown_pending": md.get("pending"),
                "markdown_completed": md.get("completed"),
                "artifact_rows": artifacts.get("artifact_rows"),
                "production_workers": len(inv.get("production_workers", [])),
                "foreign_workers": len(inv.get("foreign_workers", [])),
                "pytest_temp_workers": len(inv.get("pytest_temp_workers", [])),
                "production_supervisors": len(
                    inv.get("production_supervisors", [])
                ),
                "foreign_supervisors": len(inv.get("foreign_supervisors", [])),
                "pytest_temp_supervisors": len(
                    inv.get("pytest_temp_supervisors", [])
                ),
                "production_supervisor_pids": [
                    item.get("pid")
                    for item in inv.get("production_supervisors", [])
                    if item.get("pid") is not None
                ],
                "long_running": status.get("long_running_document_warning"),
                "scan_interrupted_count": pipeline.get("health", {})
                .get("scan", {})
                .get("interrupted_total"),
                "last_scan_run_id": last_scan.get("run_id"),
                "last_scan_new_errors": last_scan.get("new_errors"),
                "last_scan_known_quarantined": last_scan.get(
                    "known_quarantined"
                ),
                "latest_running_scan": pipeline.get("health", {})
                .get("scan", {})
                .get("latest_running_scan"),
                "operation_lock": pipeline.get("health", {})
                .get("locks", {})
                .get("operation_lock"),
                "operation_lock_pid": lock_health.get("operation_lock_pid"),
                "operation_lock_identity_verification": lock_health.get(
                    "operation_lock_identity_verification"
                ),
                "operation_lock_process_creation_time": lock_health.get(
                    "operation_lock_process_creation_time"
                ),
                "operation_lock_observed_process_creation_time": lock_health.get(
                    "operation_lock_observed_process_creation_time"
                ),
                "last_cycle_at": scheduler.get("last_cycle_at"),
                "last_cycle_status": scheduler.get("last_cycle_status"),
                "last_cycle_error": scheduler.get("last_error"),
                "parse_timeout_total": scheduler.get("parse_timeout_total"),
                "last_parse_timeout_path": scheduler.get(
                    "last_parse_timeout_path"
                ),
                "next_wake_reason": status.get("next_wake_reason"),
                "next_wait_seconds": status.get("next_wait_seconds"),
                "last_export_progress_total": status.get("scheduler", {}).get(
                    "last_export_progress_total"
                ),
                "last_export_duration_seconds": status.get("scheduler", {}).get(
                    "last_export_duration_seconds"
                ),
            }
        )
        time.sleep(interval_seconds)

    database_check = check_database(project_root)
    raw_final = check_raw_safety(project_root)
    stockwiki_final = snapshot_tree_metadata(project_root.parent / "StockWiki")
    end_time = time.time()
    result = summarize_pilot(
        samples=samples,
        start_time=start_time,
        end_time=end_time,
        raw_baseline=raw_baseline,
        raw_final=raw_final,
        database_check=database_check,
        stockwiki_baseline=stockwiki_baseline,
        stockwiki_final=stockwiki_final,
        heartbeat_stale_seconds=heartbeat_stale_seconds,
        max_same_path_seconds=max_same_path_seconds,
        require_progress=require_progress,
        minimum_normalized_delta=minimum_normalized_delta,
        required_export_progress_total=required_export_progress_total,
        require_visible_scan_enumeration=require_visible_scan_enumeration,
        require_supervisor=require_supervisor,
        require_code_match=require_code_match,
    )

    if json_out:
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(json_out).write_text(
            json.dumps(result, indent=2, default=str), encoding="utf-8"
        )

    print(json.dumps(result, indent=2, default=str))
    return 0 if result["pilot_pass"] else 1


if __name__ == "__main__":
    from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze  # noqa: F401
    sys.exit(main())
