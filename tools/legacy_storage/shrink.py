"""Physical SQLite compaction with actual before/after facts and disk space."""
from __future__ import annotations

from contextlib import closing, nullcontext
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import tempfile

from company_wiki.source_catalog.lock import CatalogOperationLock, CatalogOperationLockedError
from legacy_storage.core import (
    LEGACY_RECORD_TABLES, db_numbers, empty_report, integrity_probe,
    protected_objects, read_connection, source_facts, table_digest,
)


def _snapshot(database, catalog):
    with read_connection(database) as connection:
        connection.execute("BEGIN")
        return {"numbers": db_numbers(database, connection=connection),
                "facts": source_facts(database, connection=connection),
                "legacy": {t: table_digest(connection, t) for t in LEGACY_RECORD_TABLES},
                "protected": protected_objects(database, catalog, connection=connection),
                "integrity": integrity_probe(connection)}


def _record(report, snapshot, suffix):
    numbers = snapshot["numbers"]
    report[f"source_facts_{suffix}"] = snapshot["facts"]
    report[f"legacy_record_facts_{suffix}"] = snapshot["legacy"]
    report[f"protected_objects_{suffix}"] = snapshot["protected"]
    report[f"database_bytes_{suffix}"] = numbers["file_bytes"]
    report[f"database_logical_bytes_{suffix}"] = numbers["logical_bytes"]
    report[f"files_bytes_{suffix}"] = numbers["file_bytes"]
    report[f"page_count_{suffix}"] = numbers["page_count"]
    report[f"freelist_{suffix}"] = numbers["freelist"]
    if suffix == "after":
        report["after_measurement_available"] = True
        report.update(snapshot["integrity"])


def run_vacuum(config, *, now: datetime | None = None, dry_run: bool = False) -> dict:
    """No backup copy or restore exercise; native SQLite handles its transaction."""
    del now
    database, catalog = Path(config.database_path), Path(config.catalog_dir)
    report = empty_report("vacuum")
    report.update(dry_run=dry_run, selection={"mode": "obsolete_pages_vacuum"}, stage="preflight")
    if not database.is_file():
        report.update(status="refused", error_code="database_missing")
        return report
    lock = nullcontext() if dry_run else CatalogOperationLock(catalog, operation="vacuum")
    before = None
    try:
        # Measure first, so an insufficient-space refusal performs no catalog writes.
        numbers = db_numbers(database)
        for suffix in ("before", "after"):
            report[f"database_bytes_{suffix}"] = numbers["file_bytes"]
            report[f"database_logical_bytes_{suffix}"] = numbers["logical_bytes"]
            report[f"files_bytes_{suffix}"] = numbers["file_bytes"]
            report[f"page_count_{suffix}"] = numbers["page_count"]
            report[f"freelist_{suffix}"] = numbers["freelist"]
        report["disk_free_bytes_before"] = shutil.disk_usage(database.parent).free
        report["disk_free_bytes_after"] = report["disk_free_bytes_before"]
        report["temp_disk_free_bytes"] = shutil.disk_usage(tempfile.gettempdir()).free
        report["scratch_required_bytes"] = 2 * max(numbers["file_bytes"], numbers["logical_bytes"])
        if not dry_run and min(report["disk_free_bytes_before"], report["temp_disk_free_bytes"]) < report["scratch_required_bytes"]:
            report.update(status="refused", error_code="insufficient_disk_space")
            return report
        if dry_run:
            before = _snapshot(database, catalog)
            _record(report, before, "before")
            _record(report, before, "after")
            if before["integrity"]["foreign_key_check"] or before["integrity"]["integrity_check"] != "ok":
                report.update(status="refused", error_code="integrity_check_failed")
            return report
        with lock:
            # Re-sample under the existing operation lock; never label post-VACUUM as before.
            before = _snapshot(database, catalog)
            _record(report, before, "before")
            _record(report, before, "after")
            if before["integrity"]["foreign_key_check"] or before["integrity"]["integrity_check"] != "ok":
                report.update(status="refused", error_code="integrity_check_failed")
                return report
            report["scratch_required_bytes"] = 2 * max(before["numbers"]["file_bytes"], before["numbers"]["logical_bytes"])
            if min(shutil.disk_usage(database.parent).free, shutil.disk_usage(tempfile.gettempdir()).free) < report["scratch_required_bytes"]:
                report.update(status="refused", error_code="insufficient_disk_space")
                return report
            # Operation may have changed physical state even if readback later fails.
            for key in list(report):
                if key.endswith("_after"):
                    report[key] = None
            report.update(after_measurement_available=False, integrity_check=None, foreign_key_check=None)
            try:
                with closing(sqlite3.connect(database, timeout=5.0, isolation_level=None)) as connection:
                    report["stage"] = "checkpoint_before"
                    checkpoint = tuple(connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone())
                    report["checkpoint_before"] = checkpoint
                    if checkpoint[0]:
                        report.update(status="refused", error_code="checkpoint_busy")
                    else:
                        report["stage"] = "vacuum"
                        connection.execute("VACUUM")
                        report["stage"] = "checkpoint_after"
                        checkpoint = tuple(connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone())
                        report["checkpoint_after"] = checkpoint
                        if checkpoint[0]:
                            report.update(status="failed", error_code="checkpoint_busy")
                        else:
                            report["stage"] = "completed"
            except sqlite3.Error as exc:
                report.update(status="failed", error_code=f"vacuum_error:{type(exc).__name__}",
                              resume_notes=[f"{report['stage']}: {str(exc)[:400]}; inspect measured state before resuming"])
            finally:
                after = _snapshot(database, catalog)
                _record(report, after, "after")
                report["disk_free_bytes_after"] = shutil.disk_usage(database.parent).free
                report["database_file_bytes_released"] = before["numbers"]["file_bytes"] - after["numbers"]["file_bytes"]
                if before["facts"] != after["facts"] or before["legacy"] != after["legacy"] or before["protected"] != after["protected"]:
                    report.update(status="failed", error_code="protected_facts_changed")
                elif after["integrity"]["foreign_key_check"] or after["integrity"]["integrity_check"] != "ok":
                    report.update(status="failed", error_code="integrity_check_failed")
    except CatalogOperationLockedError:
        report.update(status="refused", error_code="catalog_busy")
    except (OSError, sqlite3.Error) as exc:
        report.update(status="failed", error_code=f"vacuum_error:{type(exc).__name__}",
                      resume_notes=[f"{report['stage']}: {str(exc)[:400]}"])
    return report
