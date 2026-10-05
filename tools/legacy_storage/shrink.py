"""vacuum: physical DB shrink with real-space accounting (outside any txn)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from legacy_storage.core import (
    REPORT_SCHEMA,
    db_numbers,
    utc_now_text,
)
from legacy_storage.retirement import integrity_probe_write, integrity_status

VACUUM_SCHEMA = REPORT_SCHEMA


def run_vacuum(config, *, now: datetime | None = None, dry_run: bool = False) -> dict:
    catalog_dir = Path(config.catalog_dir)
    database_path = Path(config.database_path)
    created_at = utc_now_text(now)
    if not database_path.is_file():
        report = _base(dry_run)
        report["status"] = "refused"
        report["error_code"] = "database_missing"
        report["resume_notes"] = [f"database not found: {database_path}"]
        _ = created_at, catalog_dir
        return report

    before = db_numbers(database_path)
    notes: list[str] = []

    if dry_run:
        report = _base(True)
        report.update(
            {
                "status": "succeeded",
                "selection": {"mode": "obsolete_pages_vacuum"},
                "database_bytes_before": before["file_bytes"],
                "database_bytes_after": before["file_bytes"],
                "page_count_before": before["page_count"],
                "page_count_after": before["page_count"],
                "freelist_before": before["freelist"],
                "freelist_after": before["freelist"],
                "files_bytes_before": before["file_bytes"],
                "files_bytes_after": before["file_bytes"],
                "foreign_key_check": integrity_probe_write(database_path),
                "integrity_check": integrity_status(database_path),
                "resume_notes": [],
            }
        )
        return report

    import sqlite3

    conn = sqlite3.connect(database_path, timeout=30.0, isolation_level=None)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        # exclusive writer probe: refuses when another writer/reader cluster is active
        try:
            conn.execute("VACUUM")
        except sqlite3.OperationalError as exc:
            report = _base(False)
            report["status"] = "failed"
            report["error_code"] = f"vacuum_refused:{type(exc).__name__}"
            report.update(
                {
                    "database_bytes_before": before["file_bytes"],
                    "page_count_before": before["page_count"],
                    "freelist_before": before["freelist"],
                }
            )
            report["resume_notes"] = [
                f"vacuum refused: {exc}; database untouched, no truncation attempted"
            ]
            return report
        checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        notes.append(f"wal_checkpoint(TRUNCATE) -> {checkpoint[0]}")
    finally:
        conn.close()

    after = db_numbers(database_path)
    from legacy_storage.core import source_facts

    report = _base(False)
    report.update(
        {
            "status": "succeeded",
            "error_code": None,
            "selection": {"mode": "obsolete_pages_vacuum"},
            "source_facts_before": source_facts(database_path),
            "source_facts_after": source_facts(database_path),
            "database_bytes_before": before["file_bytes"],
            "database_bytes_after": after["file_bytes"],
            "files_bytes_before": before["file_bytes"],
            "files_bytes_after": after["file_bytes"],
            "page_count_before": before["page_count"],
            "page_count_after": after["page_count"],
            "freelist_before": before["freelist"],
            "freelist_after": after["freelist"],
            "foreign_key_check": integrity_probe_write(database_path),
            "integrity_check": integrity_status(database_path),
            "resume_notes": notes,
        }
    )
    return report


def _base(dry_run: bool) -> dict:
    return {
        "schema_version": VACUUM_SCHEMA,
        "operation": "vacuum",
        "dry_run": dry_run,
        "status": "succeeded",
        "error_code": None,
        "selection": {},
        "source_facts_before": {},
        "source_facts_after": {},
        "protected_objects_before": {},
        "protected_objects_after": {},
        "candidates": [],
        "deleted": [],
        "already_absent": [],
        "files_bytes_before": 0,
        "files_bytes_after": 0,
        "database_bytes_before": 0,
        "database_bytes_after": 0,
        "page_count_before": 0,
        "page_count_after": 0,
        "freelist_before": 0,
        "freelist_after": 0,
        "foreign_key_check": [],
        "integrity_check": "ok",
        "resume_notes": [],
    }
