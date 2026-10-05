"""retire-derived: retire legacy artifact handles, then unlink exactly those files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from legacy_storage.core import (
    LEGACY_RECORD_TABLES,
    REPORT_SCHEMA,
    db_numbers,
    directed_inside,
    file_sha256,
    
    protected_objects,
    read_connection,
    source_facts,
    tree_stats,
    utc_now_text,
)
from legacy_storage.selection import LEGACY_ROLES

RETIRE_STATUS = "retired"


def _load_manifest(path: Path) -> dict:
    import json

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _live_rows(database_path: Path) -> dict[str, dict]:
    with read_connection(database_path) as conn:
        return {
            row[0]: {"status": row[1], "sha": row[2], "path": row[3]}
            for row in conn.execute(
                "SELECT artifact_id, status, content_sha256, path FROM artifacts"
            )
        }


def _verify_candidate(entry: dict, derived_dir: Path) -> tuple[str, dict | None]:
    path = Path(entry["path"])
    entry = dict(entry, path=str(path))
    if not directed_inside(path, derived_dir):
        return "path_outside_derived", None
    if not path.is_file() or path.is_symlink():
        return "file_missing", entry
    if file_sha256(path) != entry["content_sha256"]:
        return "content_hash_mismatch", None
    return "ok", entry


def run_retire_derived(
    config, manifest: dict, *, now: datetime | None = None, dry_run: bool = False
) -> dict:
    """Retire legacy derived artifacts (metadata first, then precise unlinks)."""
    catalog_dir = Path(config.catalog_dir)
    database_path = Path(config.database_path)
    derived_dir = Path(config.derived_dir)
    created_at = utc_now_text(now)
    notes: list[str] = []

    entries = list(manifest.get("candidates") or [])
    if not entries:
        report = _base_report(
            dry_run=dry_run,
            status="refused",
            error_code="empty_candidate_scope",
            notes=["manifest has no candidate scope"],
            entries_text=True,
        )
        _ = created_at
        return report

    facts_before = source_facts(database_path)
    protected_before = protected_objects(database_path, catalog_dir)
    derived_stats_before = tree_stats(derived_dir)
    db_before = db_numbers(database_path)

    actionable: dict[str, dict] = {}
    excluded: list[dict] = []
    already_absent: list[dict] = []
    live = _live_rows(database_path)
    for entry in entries:
        artifact_id = entry["artifact_id"]
        row_live = live.get(artifact_id)
        if row_live is None:
            excluded.append(dict(entry, reason="record_absent"))
            already_absent.append(entry)
            continue
        if row_live["status"] == RETIRE_STATUS:
            excluded.append(dict(entry, reason="already_retired"))
            continue
        if (
            row_live["status"] != "completed"
            or row_live["sha"] != entry["content_sha256"]
        ):
            excluded.append(dict(entry, reason="state_changed"))
            continue
        verdict, verified = _verify_candidate(entry, derived_dir)
        if verdict == "file_missing":
            already_absent.append(verified)
            excluded.append(dict(entry, reason="file_missing"))
            continue
        if verdict != "ok":
            excluded.append(dict(entry, reason=verdict))
            continue
        actionable[artifact_id] = verified

    deleted: list[dict] = []
    metadata_error: str | None = None
    if not dry_run and actionable:
        import sqlite3

        conn = sqlite3.connect(database_path, timeout=30.0)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("BEGIN IMMEDIATE")
            for artifact_id, entry in actionable.items():
                cursor = conn.execute(
                    "UPDATE artifacts SET status=? WHERE artifact_id=?"
                    " AND status='completed' AND content_sha256=?",
                    (RETIRE_STATUS, artifact_id, entry["content_sha256"]),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError(f"artifact state changed mid-run: {artifact_id}")
            conn.commit()
        except Exception as exc:  # noqa: BLE001 - single batch aborted, kept facts
            conn.rollback()
            metadata_error = f"{type(exc).__name__}: {exc}"
            notes.append("metadata transaction failed; no file was unlinked")
        finally:
            conn.close()
    if metadata_error is not None:
        report = _build_report(
            catalog_dir,
            database_path,
            derived_dir,
            facts_before,
            protected_before,
            derived_stats_before,
            db_before,
            entries,
            deleted=[],
            already_absent=[],
            excluded=[
                dict(e, reason="metadata_update_failed") for e in actionable.values()
            ]
            + excluded,
            notes=notes,
            dry_run=dry_run,
            status="failed",
            error_code="metadata_update_failed",
        )
        return report

    if not dry_run:
        for artifact_id, entry in actionable.items():
            path = Path(entry["path"])
            verdict, _ = _verify_candidate(entry, derived_dir)
            if verdict == "file_missing":
                already_absent.append(entry)
                continue
            if verdict != "ok":
                excluded.append(dict(entry, reason=verdict))
                notes.append(f"skipped, candidate changed after verification: {path}")
                continue
            try:
                path.unlink()
            except FileNotFoundError:
                already_absent.append(entry)
            except OSError as exc:
                excluded.append(dict(entry, reason=f"unlink_failed:{exc.errno}"))
                notes.append(f"unlink failed, file kept: {path}")
                continue
            deleted.append(entry)
            for managed in entry.get("managed_files") or []:
                managed_path = Path(managed["path"])
                try:
                    managed_path.unlink()
                    deleted.append({
                        "artifact_id": None,
                        "artifact_role": "sections",
                        "generator_name": entry["generator_name"],
                        "path": str(managed_path),
                        "byte_size": managed["byte_size"],
                        "managed_by": artifact_id,
                    })
                except FileNotFoundError:
                    already_absent.append({
                        "artifact_id": None, "artifact_role": "sections",
                        "path": str(managed_path),
                        "byte_size": managed["byte_size"],
                        "managed_by": artifact_id,
                    })
                except OSError as exc2:
                    excluded.append({
                        "artifact_id": None,
                        "artifact_role": "sections",
                        "path": str(managed_path),
                        "reason": f"unlink_failed:{getattr(exc2, 'errno', '?')}",
                    })
        deleted.extend(_sections_index_sweep(derived_dir))
        _prune_empty_dirs(derived_dir)
    if dry_run:
        notes.append(
            f"dry run: {len(actionable)} candidate(s) would be retired; nothing deleted"
        )

    leftovers: list[str] = []
    if entries:
        with read_connection(database_path) as conn:
            leftovers = [
                row[0]
                for row in conn.execute(
                    "SELECT artifact_id FROM artifacts WHERE status='completed'"
                    " AND artifact_id IN (%s)" % ",".join("?" * len(entries)),
                    tuple(e["artifact_id"] for e in entries),
                )
            ]
    if leftovers:
        notes.append(f"completed handles remain for {len(leftovers)} manifest rows")

    report = _build_report(
        catalog_dir,
        database_path,
        derived_dir,
        facts_before,
        protected_before,
        derived_stats_before,
        db_before,
        entries,
        deleted=deleted,
        already_absent=already_absent,
        excluded=excluded,
        notes=notes,
        dry_run=dry_run,
        status="succeeded" if not leftovers else "failed",
        error_code=None if not leftovers else "handle_still_completed",
    )
    report["created_at"] = created_at
    report["handle_verification"] = {
        "remaining_completed_handles": leftovers,
        "legacy_roles": sorted(LEGACY_ROLES),
        "legacy_record_tables": sorted(LEGACY_RECORD_TABLES),
    }
    return report


def _sections_index_sweep(derived_dir: Path) -> list[dict]:
    """Delete sections/index.json once every section file of that dir is gone
    AND the dir holds nothing but that index."""
    removed: list[dict] = []
    if not derived_dir.is_dir():
        return removed
    for index in derived_dir.rglob("index.json"):
        parent = index.parent
        if parent.name != "sections":
            continue
        siblings = [p for p in parent.iterdir() if p.is_file()]
        if siblings != [index]:
            continue
        size = index.stat().st_size
        try:
            index.unlink()
        except OSError:
            continue
        removed.append(
            {
                "artifact_id": None,
                "artifact_role": "sections",
                "generator_name": "source_catalog_section_extractor",
                "path": str(index),
                "byte_size": size,
            }
        )
    return removed


def _prune_empty_dirs(derived_dir: Path) -> None:
    if not derived_dir.is_dir():
        return
    for path in sorted(
        derived_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True
    ):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass


def report_base(operation: str) -> dict:
    return {
        "schema_version": REPORT_SCHEMA,
        "operation": operation,
        "dry_run": True,
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


def _base_report(
    *,
    dry_run: bool,
    status: str,
    error_code: str | None,
    notes: list[str],
    entries_text: bool = False,
) -> dict:
    report = report_base("retire-derived")
    report["dry_run"] = dry_run
    report["status"] = status
    report["error_code"] = error_code
    report["resume_notes"] = notes
    _ = entries_text
    return report


def _build_report(
    catalog_dir,
    database_path,
    derived_dir,
    facts_before,
    protected_before,
    derived_stats_before,
    db_before,
    entries,
    *,
    deleted,
    already_absent,
    excluded,
    notes,
    dry_run,
    status,
    error_code,
) -> dict:
    facts_after = source_facts(database_path)
    protected_after = protected_objects(database_path, catalog_dir)
    derived_stats_after = tree_stats(derived_dir)
    db_after = db_numbers(database_path)
    report = report_base("retire-derived")
    report.update(
        {
            "dry_run": dry_run,
            "status": status,
            "error_code": error_code,
            "selection": {"manifest_candidates": len(entries)},
            "source_facts_before": facts_before,
            "source_facts_after": facts_after,
            "protected_objects_before": protected_before,
            "protected_objects_after": protected_after,
            "candidates": entries,
            "deleted": deleted,
            "already_absent": already_absent,
            "excluded": excluded,
            "files_bytes_before": derived_stats_before["bytes"],
            "files_bytes_after": derived_stats_after["bytes"],
            "database_bytes_before": db_before["file_bytes"],
            "database_bytes_after": db_after["file_bytes"],
            "page_count_before": db_before["page_count"],
            "page_count_after": db_after["page_count"],
            "freelist_before": db_before["freelist"],
            "freelist_after": db_after["freelist"],
            "foreign_key_check": integrity_probe_write(database_path),
            "integrity_check": integrity_status(database_path),
            "resume_notes": notes,
        }
    )
    return report


def integrity_probe_write(database_path: Path) -> list:
    with read_connection(database_path) as conn:
        return [tuple(row) for row in conn.execute("PRAGMA foreign_key_check")]


def integrity_status(database_path: Path) -> object:
    with read_connection(database_path) as conn:
        rows = [row[0] for row in conn.execute("PRAGMA integrity_check")]
    return "ok" if rows == ["ok"] else rows
