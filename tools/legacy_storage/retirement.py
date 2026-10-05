"""Retire only current registered legacy objects; resume interrupted unlinks."""
from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from company_wiki.source_catalog.lock import CatalogOperationLock
from legacy_storage.core import (
    db_numbers, directed_inside, empty_report, file_sha256, normalized,
    protected_objects, read_connection, source_facts, tree_stats, utc_now_text,
)
from legacy_storage.selection import LEGACY_GENERATORS, LEGACY_ROLES, _sections_managed_files

RETIRE_STATUS = "retired"
_RESUME_KEY = "legacy_storage_retirement"
_IDENTITY = ("document_id", "artifact_role", "path", "content_sha256", "byte_size",
             "generator_name", "generator_version")
_ELIGIBLE = {"completed", "partial", "unsupported", "failed", "retired"}


def _load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _live_rows(database_path: Path):
    with read_connection(database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = {row["artifact_id"]: dict(row) for row in connection.execute("SELECT * FROM artifacts")}
        originals = {normalized(Path(row[0])) for row in connection.execute("SELECT absolute_path FROM locations")}
    return rows, originals


def _safe_path(path: Path, derived: Path, originals: set) -> bool:
    if not path.is_absolute() or not directed_inside(path, derived) or normalized(path) in originals:
        return False
    current = path
    boundary = derived.absolute()
    while True:
        try:
            attrs = current.lstat()
        except FileNotFoundError:
            attrs = None
        if current.is_symlink() or (attrs is not None and getattr(attrs, "st_file_attributes", 0) & 0x400):
            return False
        if current == boundary:
            return True
        if current == current.parent:
            return False
        current = current.parent


def _check_target(target: dict, derived: Path, originals: set) -> str | None:
    path = Path(target["path"])
    if not _safe_path(path, derived, originals):
        return "path_not_managed_derived"
    if not path.exists():
        return None
    if not path.is_file() or file_sha256(path) != target.get("content_sha256"):
        return "content_hash_mismatch"
    if path.stat().st_size != target.get("byte_size"):
        return "byte_size_mismatch"
    return None


def _managed_scope(row: dict, entry: dict, derived: Path, originals: set):
    if row["artifact_role"] != "sections":
        if entry.get("managed_files"):
            return [], "unexpected_managed_files"
        return [], None
    index = Path(row["path"])
    if index.name != "index.json" or index.parent.name != "sections":
        return [], "index_not_legacy_sections"
    metadata = json.loads(row.get("metadata_json") or "{}")
    if not isinstance(metadata, dict):
        return [], "metadata_unreadable"
    saved = metadata.get(_RESUME_KEY)
    if isinstance(saved, dict) and saved.get("index_sha256") == row["content_sha256"]:
        managed = saved["managed_files"]
    elif index.is_file():
        managed, error = _sections_managed_files(index, derived)
        if error:
            return [], error
        declared = {item["path"]: item for item in entry.get("managed_files", [])}
        if set(declared) != {item["path"] for item in managed}:
            return [], "managed_scope_changed"
        # The index hash pins its paths; the observed section hashes pin bytes.
        for item in managed:
            observation = declared[item["path"]]
            if Path(item["path"]).exists() and any(
                item.get(field) != observation.get(field) for field in ("role", "content_sha256", "byte_size")
            ):
                return [], "managed_bytes_changed"
    else:
        if entry.get("managed_files"):
            return [], "managed_resume_metadata_missing"
        managed = []
    for item in managed:
        path = Path(item["path"])
        role = item.get("role")
        if not isinstance(role, str) or not role or not all(c.isascii() and (c.isalnum() or c == "_") for c in role):
            return [], "managed_role_invalid"
        if normalized(path) != normalized(index.parent / (role + ".md")):
            return [], "managed_path_not_index_member"
        error = _check_target(item, derived, originals)
        if error:
            return [], error
    return managed, None


def run_retire_derived(config, manifest: dict, *, now: datetime | None = None, dry_run: bool = False) -> dict:
    report = empty_report("retire-derived", now=now)
    report["dry_run"] = dry_run
    report["created_at"] = utc_now_text(now)
    entries = list(manifest.get("candidates") or [])
    if not entries:
        report.update(status="refused", error_code="empty_candidate_scope")
        return report
    database = Path(config.database_path)
    catalog = Path(config.catalog_dir)
    if manifest.get("schema_version") != "cwp-storage-manifest/1" or (
        normalized(Path(manifest.get("catalog_dir", ""))) != normalized(catalog)
        or normalized(Path(manifest.get("database_path", ""))) != normalized(database)
    ):
        report.update(status="refused", error_code="manifest_catalog_mismatch")
        return report
    lock = nullcontext() if dry_run else CatalogOperationLock(catalog, operation="retire-derived")
    with lock:
        return _execute(config, entries, report)


def _execute(config, entries: list, report: dict) -> dict:
    database, derived, catalog = Path(config.database_path), Path(config.derived_dir), Path(config.catalog_dir)
    report["source_facts_before"] = source_facts(database)
    report["protected_objects_before"] = protected_objects(database, catalog)
    files_before = tree_stats(derived)
    before = db_numbers(database)
    live, originals = _live_rows(database)
    actions, excluded = {}, []
    for entry in entries:
        row = live.get(entry.get("artifact_id"))
        reason = None
        if row is None:
            reason = "record_absent"
        elif row["generator_name"] not in LEGACY_GENERATORS or row["artifact_role"] not in LEGACY_ROLES:
            reason = "current_record_not_legacy"
        elif row["status"] not in _ELIGIBLE:
            reason = "state_changed"
        elif any(row[field] != entry.get(field) for field in _IDENTITY):
            reason = "record_binding_changed"
        if reason:
            excluded.append(dict(entry, reason=reason))
            continue
        target = {field: row[field] for field in ("artifact_id", *_IDENTITY)}
        reason = _check_target(target, derived, originals)
        if reason:
            excluded.append(dict(entry, reason=reason))
            continue
        try:
            managed, reason = _managed_scope(row, entry, derived, originals)
        except (KeyError, TypeError, ValueError, OSError):
            managed, reason = [], "managed_scope_unreadable"
        if reason:
            excluded.append(dict(entry, reason=reason))
            continue
        actions[row["artifact_id"]] = (row, target, managed)
    report.update(candidates=entries, excluded=excluded, selection={"manifest_candidates": len(entries)})
    if not report["dry_run"] and actions:
        connection = sqlite3.connect(database, timeout=30)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("BEGIN IMMEDIATE")
            for row, target, managed in actions.values():
                metadata = json.loads(row.get("metadata_json") or "{}")
                saved_scope = {"index_sha256": row["content_sha256"], "managed_files": managed}
                if row["status"] == "retired" and (
                    row["artifact_role"] != "sections" or metadata.get(_RESUME_KEY) == saved_scope
                ):
                    continue
                if row["artifact_role"] == "sections":
                    metadata[_RESUME_KEY] = {"index_sha256": row["content_sha256"], "managed_files": managed}
                cursor = connection.execute(
                    "UPDATE artifacts SET status='retired', metadata_json=? WHERE artifact_id=?"
                    " AND status=? AND " + " AND ".join(field + "=?" for field in _IDENTITY),
                    (json.dumps(metadata, ensure_ascii=False), row["artifact_id"], row["status"],
                     *(row[field] for field in _IDENTITY)),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("artifact state changed during retirement")
            connection.commit()
        except (sqlite3.Error, RuntimeError, ValueError, TypeError):
            connection.rollback()
            report.update(status="failed", error_code="metadata_update_failed")
            return _finish(config, report, files_before, before)
        finally:
            connection.close()
        seen = set()
        for row, target, managed in actions.values():
            # Keep the pinned index until every managed child is resolved.
            group_failed = False
            for member in [*managed, target]:
                item = member if member is target else dict(
                    member, artifact_id=None, artifact_role="sections",
                    generator_name=row["generator_name"], managed_by=row["artifact_id"])
                path = Path(item["path"])
                identity = normalized(path)
                if identity in seen:
                    continue
                if item is target and group_failed:
                    break
                error = _check_target(item, derived, originals)
                if error:
                    report["excluded"].append(dict(item, reason=error))
                    group_failed = True
                    continue
                if not path.exists():
                    report["already_absent"].append(dict(item))
                    seen.add(identity)
                    continue
                actual_size = path.stat().st_size
                try:
                    path.unlink()
                except FileNotFoundError:
                    report["already_absent"].append(dict(item))
                except OSError as error:
                    report["excluded"].append(dict(item, reason=f"unlink_failed:{error.errno}"))
                    group_failed = True
                    continue
                else:
                    report["deleted"].append(dict(item, byte_size=actual_size))
                seen.add(identity)
    report["status"] = "failed" if report["excluded"] else "succeeded"
    report["error_code"] = "candidate_changed_or_unlink_failed" if report["excluded"] else None
    return _finish(config, report, files_before, before)


def _finish(config, report, files_before, before):
    database, catalog = Path(config.database_path), Path(config.catalog_dir)
    after = db_numbers(database)
    report.update(source_facts_after=source_facts(database),
                  protected_objects_after=protected_objects(database, catalog),
                  files_bytes_before=files_before["bytes"], files_bytes_after=tree_stats(Path(config.derived_dir))["bytes"],
                  database_bytes_before=before["file_bytes"], database_bytes_after=after["file_bytes"],
                  page_count_before=before["page_count"], page_count_after=after["page_count"],
                  freelist_before=before["freelist"], freelist_after=after["freelist"],
                  foreign_key_check=integrity_probe_write(database), integrity_check=integrity_status(database))
    if report["source_facts_before"] != report["source_facts_after"] or report["protected_objects_before"] != report["protected_objects_after"]:
        report.update(status="failed", error_code="protected_facts_changed")
    return report


def integrity_probe_write(database_path: Path) -> list:
    with read_connection(database_path) as connection:
        return [tuple(row) for row in connection.execute("PRAGMA foreign_key_check")]


def integrity_status(database_path: Path):
    with read_connection(database_path) as connection:
        rows = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    return "ok" if rows == ["ok"] else rows
