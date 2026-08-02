"""Audited cleanup for sources rejected by the focus admission policy."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from .admission import FOCUS_RELATIVE_PREFIX, FOCUS_ROOT_ID, evaluate_admission
from .lock import CatalogOperationLock
from .models import DOCUMENT_EXTENSIONS
from .store import canonical_json


FOCUS_CLEANUP_SCHEMA_VERSION = "1.0"
_SIDECAR_SUFFIX = ".source.json"
_DATABASE_BACKUP_SUFFIX = ".sqlite3"
_DOCUMENT_CHILD_TABLES = (
    "llm_summary_failures",
    "evidence_spans",
    "source_metadata_assertions",
    "document_fingerprint_state",
    "document_retire_audit",
    "document_restore_audit",
    "artifacts",
    "document_entities",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _archive_files(
    files: list[tuple[Path, str]], archive_dir: Path, base: Path
) -> list[dict[str, Any]]:
    """Copy files into archive_dir/files/ and return manifest entries."""
    members_dir = archive_dir / "files"
    members_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for index, (path, kind) in enumerate(files):
        data = path.read_bytes()
        member_name = f"{index:04d}-{hashlib.sha256(data).hexdigest()[:12]}"
        member_path = members_dir / member_name
        if not member_path.exists():
            member_path.write_bytes(data)
        stat = path.stat()
        try:
            relative = path.resolve().relative_to(base.resolve())
        except ValueError:
            relative = Path(os.path.relpath(path.resolve(), base.resolve()))
        entries.append(
            {
                "original_path": str(path.resolve()),
                "relative_path": relative.as_posix(),
                "kind": kind,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "content_sha256": hashlib.sha256(data).hexdigest(),
                "archive_member": f"files/{member_name}",
            }
        )
    return entries


def _load_metadata(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"meta_parse_error": True}
    return payload if isinstance(payload, dict) else {"meta_parse_error": True}


def _rows(store: Any, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in store.fetchall(sql, tuple(params))]


def _in_clause(values: Iterable[str]) -> tuple[str, tuple[str, ...]]:
    items = tuple(sorted(set(values)))
    if not items:
        return "", ()
    return ",".join("?" for _ in items), items


class FocusScopeCleanupService:
    """Remove rejected catalog state while preserving every user original."""

    def __init__(self, catalog: Any):
        self.catalog = catalog
        self.config = catalog.config
        self.store = catalog.store

    def _scope(self, *, root_id: str, relative_prefix: str) -> tuple[Any, Path]:
        if root_id != FOCUS_ROOT_ID or relative_prefix != FOCUS_RELATIVE_PREFIX:
            raise ValueError("cleanup scope must be exact dropbox_stock/重点关注")
        root = next(
            (item for item in self.config.roots if item.root_id == root_id), None
        )
        if root is None or root.kind != "directory":
            raise ValueError("focus cleanup root is not configured as a directory")
        root_path = root.path.resolve(strict=True)
        target = (root_path / relative_prefix).resolve(strict=True)
        if not target.is_relative_to(root_path) or target.parent != root_path:
            raise ValueError("focus cleanup target escaped the configured root")
        return root, target

    @staticmethod
    def _relative(path: Path, root: Path) -> str:
        return path.relative_to(root).as_posix()

    def _filesystem_plan(self, root: Any, target: Path) -> dict[str, Any]:
        files = sorted(path for path in target.rglob("*") if path.is_file())
        sidecars = {
            str(path)[: -len(_SIDECAR_SUFFIX)]: path
            for path in files
            if path.name.endswith(_SIDECAR_SUFFIX)
        }
        supported_originals = [
            path
            for path in files
            if not path.name.endswith(_SIDECAR_SUFFIX)
            and path.suffix.casefold() in DOCUMENT_EXTENSIONS
        ]
        original_paths = {str(path) for path in supported_originals}
        decisions: list[dict[str, Any]] = []
        allowed_original_relatives: set[str] = set()
        rejected_sidecars: list[Path] = []
        for path in supported_originals:
            relative = self._relative(path, root.path)
            sidecar = sidecars.get(str(path))
            metadata = _load_metadata(sidecar)
            decision = evaluate_admission(
                root_id=root.root_id,
                relative_path=relative,
                metadata=metadata,
            )
            if decision is None:
                raise RuntimeError("focus policy did not evaluate a focus path")
            decisions.append(
                {
                    "relative_path": relative,
                    "sidecar_relative_path": (
                        self._relative(sidecar, root.path) if sidecar else None
                    ),
                    "admitted": decision.admitted,
                    "document_kind": decision.document_kind,
                    "priority": decision.priority,
                    "reason": decision.reason,
                    "evidence": list(decision.evidence),
                }
            )
            if decision.admitted:
                allowed_original_relatives.add(relative)
            elif sidecar is not None:
                rejected_sidecars.append(sidecar)
        for target_name, sidecar in sorted(sidecars.items()):
            if target_name not in original_paths:
                rejected_sidecars.append(sidecar)
                decisions.append(
                    {
                        "relative_path": None,
                        "sidecar_relative_path": self._relative(sidecar, root.path),
                        "admitted": False,
                        "document_kind": None,
                        "priority": 1000,
                        "reason": "focus_policy_orphan_sidecar",
                        "evidence": [],
                    }
                )

        protected_originals = [
            path for path in files if not path.name.endswith(_SIDECAR_SUFFIX)
        ]
        original_manifest = [
            {
                "relative_path": self._relative(path, root.path),
                "byte_size": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
                "content_sha256": _sha256_file(path),
            }
            for path in protected_originals
        ]
        manifest_sha = hashlib.sha256(
            canonical_json(original_manifest).encode("utf-8")
        ).hexdigest()
        return {
            "decisions": decisions,
            "allowed_original_relatives": allowed_original_relatives,
            "sidecars_to_delete": sorted(set(rejected_sidecars)),
            "original_manifest": original_manifest,
            "original_manifest_sha256": manifest_sha,
        }

    def _database_plan(
        self, *, root_id: str, relative_prefix: str, allowed: set[str]
    ) -> dict[str, Any]:
        prefix_pattern = relative_prefix + "/%"
        target_locations = _rows(
            self.store,
            """SELECT * FROM locations
            WHERE root_id=? AND relative_path LIKE ? ORDER BY relative_path""",
            (root_id, prefix_pattern),
        )
        remove_locations = [
            row
            for row in target_locations
            if row["relative_path"].endswith(_SIDECAR_SUFFIX)
            or row["relative_path"] not in allowed
        ]
        remove_location_ids = {str(row["location_id"]) for row in remove_locations}
        affected_document_ids = {
            str(row["document_id"])
            for row in remove_locations
            if row.get("document_id")
        }
        affected_source_ids = {
            str(row["source_id"])
            for row in remove_locations
            if row.get("source_id")
        }

        document_clause, document_params = _in_clause(affected_document_ids)
        all_document_locations = (
            _rows(
                self.store,
                f"SELECT * FROM locations WHERE document_id IN ({document_clause})",
                document_params,
            )
            if document_clause
            else []
        )
        remaining_by_document: dict[str, list[dict[str, Any]]] = {}
        for row in all_document_locations:
            if row["location_id"] in remove_location_ids:
                continue
            remaining_by_document.setdefault(str(row["document_id"]), []).append(row)
        orphan_document_ids = {
            document_id
            for document_id in affected_document_ids
            if not remaining_by_document.get(document_id)
        }
        external_shared_document_ids = {
            document_id
            for document_id, rows in remaining_by_document.items()
            if any(
                not (
                    row["root_id"] == root_id
                    and str(row["relative_path"]).startswith(relative_prefix + "/")
                )
                for row in rows
            )
        }

        orphan_clause, orphan_params = _in_clause(orphan_document_ids)
        documents_to_delete = (
            _rows(
                self.store,
                f"SELECT * FROM documents WHERE document_id IN ({orphan_clause})",
                orphan_params,
            )
            if orphan_clause
            else []
        )
        affected_source_ids.update(
            str(row["primary_source_id"])
            for row in documents_to_delete
            if row.get("primary_source_id")
        )
        child_rows: dict[str, list[dict[str, Any]]] = {}
        if orphan_clause:
            for table in _DOCUMENT_CHILD_TABLES:
                child_rows[table] = _rows(
                    self.store,
                    f"SELECT * FROM {table} WHERE document_id IN ({orphan_clause})",
                    orphan_params,
                )
        else:
            child_rows = {table: [] for table in _DOCUMENT_CHILD_TABLES}

        source_clause, source_params = _in_clause(affected_source_ids)
        sources_to_delete: list[dict[str, Any]] = []
        if source_clause:
            candidates = _rows(
                self.store,
                f"SELECT * FROM sources WHERE source_id IN ({source_clause})",
                source_params,
            )
            for source in candidates:
                source_id = source["source_id"]
                retained = False
                for row in _rows(
                    self.store,
                    "SELECT location_id FROM locations WHERE source_id=?",
                    (source_id,),
                ):
                    if row["location_id"] not in remove_location_ids:
                        retained = True
                        break
                if retained:
                    continue
                retained_document = self.store.fetchone(
                    "SELECT document_id FROM documents WHERE primary_source_id=? LIMIT 1",
                    (source_id,),
                )
                if retained_document is not None and str(
                    retained_document["document_id"]
                ) not in orphan_document_ids:
                    continue
                for table in (
                    "artifacts",
                    "evidence_spans",
                    "source_metadata_assertions",
                    "document_fingerprint_state",
                ):
                    rows = _rows(
                        self.store,
                        f"SELECT document_id FROM {table} WHERE source_id=?",
                        (source_id,),
                    )
                    if any(str(row["document_id"]) not in orphan_document_ids for row in rows):
                        retained = True
                        break
                if not retained:
                    sources_to_delete.append(source)

        entity_ids = {
            str(row["entity_id"])
            for row in child_rows.get("document_entities", [])
            if row.get("entity_id")
        }
        entities_to_delete: list[dict[str, Any]] = []
        for entity_id in sorted(entity_ids):
            retained = self.store.fetchone(
                """SELECT document_id FROM document_entities
                WHERE entity_id=? AND document_id NOT IN ({}) LIMIT 1""".format(
                    orphan_clause or "''"
                ),
                (entity_id, *orphan_params),
            )
            if retained is None:
                row = self.store.fetchone(
                    "SELECT * FROM entities WHERE entity_id=?", (entity_id,)
                )
                if row is not None:
                    entities_to_delete.append(dict(row))

        snapshot_records: list[dict[str, Any]] = []
        for row in remove_locations:
            snapshot_records.append({"table": "locations", "row": row})
        for table in _DOCUMENT_CHILD_TABLES:
            for row in child_rows[table]:
                snapshot_records.append({"table": table, "row": row})
        for row in documents_to_delete:
            snapshot_records.append({"table": "documents", "row": row})
        for row in sources_to_delete:
            snapshot_records.append({"table": "sources", "row": row})
        for row in entities_to_delete:
            snapshot_records.append({"table": "entities", "row": row})

        return {
            "target_locations": target_locations,
            "remove_locations": remove_locations,
            "remove_location_ids": remove_location_ids,
            "orphan_document_ids": orphan_document_ids,
            "external_shared_document_ids": external_shared_document_ids,
            "documents_to_delete": documents_to_delete,
            "child_rows": child_rows,
            "sources_to_delete": sources_to_delete,
            "entities_to_delete": entities_to_delete,
            "snapshot_records": snapshot_records,
        }

    def _build_plan(self, *, root_id: str, relative_prefix: str) -> dict[str, Any]:
        root, target = self._scope(
            root_id=root_id, relative_prefix=relative_prefix
        )
        filesystem = self._filesystem_plan(root, target)
        database = self._database_plan(
            root_id=root_id,
            relative_prefix=relative_prefix,
            allowed=filesystem["allowed_original_relatives"],
        )
        token_payload = {
            "schema_version": FOCUS_CLEANUP_SCHEMA_VERSION,
            "database_path": str(self.config.database_path.resolve()),
            "root_id": root_id,
            "relative_prefix": relative_prefix,
            "original_manifest_sha256": filesystem["original_manifest_sha256"],
            "sidecars": [
                {
                    "path": str(path.resolve()),
                    "size": path.stat().st_size,
                    "mtime_ns": path.stat().st_mtime_ns,
                }
                for path in filesystem["sidecars_to_delete"]
            ],
            "location_ids": sorted(database["remove_location_ids"]),
            "orphan_document_ids": sorted(database["orphan_document_ids"]),
        }
        token = hashlib.sha256(canonical_json(token_payload).encode("utf-8")).hexdigest()
        return {
            "root": root,
            "target": target,
            "filesystem": filesystem,
            "database": database,
            "confirmation_token": token,
        }

    @staticmethod
    def _public_plan(plan: dict[str, Any], *, mode: str) -> dict[str, Any]:
        filesystem = plan["filesystem"]
        database = plan["database"]
        return {
            "schema_version": FOCUS_CLEANUP_SCHEMA_VERSION,
            "mode": mode,
            "root_id": plan["root"].root_id,
            "relative_prefix": FOCUS_RELATIVE_PREFIX,
            "target_path": str(plan["target"]),
            "original_delete_count": 0,
            "protected_originals": len(filesystem["original_manifest"]),
            "original_manifest_sha256": filesystem["original_manifest_sha256"],
            "admission_decisions": filesystem["decisions"],
            "sidecars_to_delete": len(filesystem["sidecars_to_delete"]),
            "database_locations_to_remove": len(database["remove_locations"]),
            "orphan_documents_to_delete": len(database["orphan_document_ids"]),
            "shared_documents_preserved": len(
                database["external_shared_document_ids"]
            ),
            "artifacts_to_delete": len(database["child_rows"]["artifacts"]),
            "evidence_spans_to_delete": len(
                database["child_rows"]["evidence_spans"]
            ),
            "sources_to_delete": len(database["sources_to_delete"]),
            "confirmation_token": plan["confirmation_token"],
        }

    def preview(
        self,
        *,
        root_id: str,
        relative_prefix: str,
        receipt_path: Path | None = None,
    ) -> dict[str, Any]:
        plan = self._build_plan(root_id=root_id, relative_prefix=relative_prefix)
        result = self._public_plan(plan, mode="dry_run")
        if receipt_path is not None:
            resolved = self._validate_output(receipt_path, plan["target"])
            _atomic_write(resolved, canonical_json(result) + "\n")
            result["receipt_path"] = str(resolved)
        return result

    def _require_paused_if_managed(self) -> None:
        control_path = self.config.catalog_dir / "worker_control.json"
        if not control_path.is_file():
            return
        try:
            payload = json.loads(control_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("worker control state is unreadable") from exc
        if payload.get("desired_state") != "paused":
            raise RuntimeError("worker must be persistently paused before cleanup apply")

    @staticmethod
    def _validate_output(path: Path, target: Path) -> Path:
        resolved = path.resolve(strict=False)
        if resolved == target or resolved.is_relative_to(target):
            raise ValueError("cleanup audit output must be outside the source target")
        return resolved

    def apply(
        self,
        *,
        root_id: str,
        relative_prefix: str,
        confirmation_token: str,
        snapshot_path: Path,
        receipt_path: Path,
        archive_dir: Path | None = None,
    ) -> dict[str, Any]:
        self._require_paused_if_managed()
        with CatalogOperationLock(self.config.catalog_dir, operation="focus_cleanup"):
            plan = self._build_plan(
                root_id=root_id, relative_prefix=relative_prefix
            )
            if confirmation_token != plan["confirmation_token"]:
                raise ValueError("cleanup confirmation token is stale or invalid")
            snapshot_path = self._validate_output(snapshot_path, plan["target"])
            receipt_path = self._validate_output(receipt_path, plan["target"])
            if archive_dir is None:
                archive_dir = (
                    self.config.catalog_dir
                    / "focus_cleanup_archive"
                    / Path(receipt_path).stem
                )
            archive_dir = archive_dir.resolve()
            snapshot_text = "".join(
                canonical_json(record) + "\n"
                for record in plan["database"]["snapshot_records"]
            )
            _atomic_write(snapshot_path, snapshot_text)
            snapshot_sha = _sha256_file(snapshot_path)

            database = plan["database"]
            with self.store.transaction() as connection:
                for row in database["remove_locations"]:
                    connection.execute(
                        "DELETE FROM locations WHERE location_id=?",
                        (row["location_id"],),
                    )
                orphan_ids = sorted(database["orphan_document_ids"])
                if orphan_ids:
                    placeholders = ",".join("?" for _ in orphan_ids)
                    for table in _DOCUMENT_CHILD_TABLES:
                        connection.execute(
                            f"DELETE FROM {table} WHERE document_id IN ({placeholders})",
                            orphan_ids,
                        )
                    connection.execute(
                        f"DELETE FROM documents WHERE document_id IN ({placeholders})",
                        orphan_ids,
                    )
                for row in database["sources_to_delete"]:
                    connection.execute(
                        "DELETE FROM sources WHERE source_id=?",
                        (row["source_id"],),
                    )
                for row in database["entities_to_delete"]:
                    connection.execute(
                        "DELETE FROM entities WHERE entity_id=?",
                        (row["entity_id"],),
                    )

            sidecars_deleted = 0
            filesystem_errors: list[str] = []
            target = plan["target"].resolve(strict=True)
            to_archive: dict[str, tuple[Path, str]] = {}
            for path in plan["filesystem"]["sidecars_to_delete"]:
                try:
                    resolved = path.resolve(strict=True)
                    if not resolved.is_relative_to(target) or not resolved.name.endswith(
                        _SIDECAR_SUFFIX
                    ):
                        raise ValueError("sidecar deletion target escaped focus scope")
                    to_archive[str(resolved)] = (resolved, "sidecar")
                except (OSError, ValueError) as exc:
                    filesystem_errors.append(f"sidecar:{path}:{type(exc).__name__}:{exc}")

            artifact_files_deleted = 0
            derived_root = self.config.derived_dir.resolve(strict=False)
            for row in database["child_rows"]["artifacts"]:
                path = Path(row["path"])
                try:
                    resolved = path.resolve(strict=False)
                    if not resolved.is_relative_to(derived_root):
                        raise ValueError("artifact path is outside derived root")
                    if resolved.is_file():
                        # dedupe: multiple artifact rows may reference one file
                        to_archive[str(resolved)] = (resolved, "artifact")
                except (OSError, ValueError) as exc:
                    filesystem_errors.append(f"artifact:{path}:{type(exc).__name__}:{exc}")

            root_base = plan["root"].path.resolve(strict=False)
            archive_items = list(to_archive.values())
            archived_files = _archive_files(archive_items, archive_dir, root_base)
            archive_manifest = {
                "schema_version": FOCUS_CLEANUP_SCHEMA_VERSION,
                "files": archived_files,
            }
            _atomic_write(
                archive_dir / "manifest.json",
                canonical_json(archive_manifest) + "\n",
            )
            archive_sha = _sha256_file(archive_dir / "manifest.json")

            for resolved, _kind in archive_items:
                try:
                    resolved.unlink()
                    if resolved.name.endswith(_SIDECAR_SUFFIX):
                        sidecars_deleted += 1
                    else:
                        artifact_files_deleted += 1
                except OSError as exc:
                    filesystem_errors.append(f"unlink:{resolved}:{type(exc).__name__}:{exc}")
            for row in database["child_rows"]["artifacts"]:
                path = Path(row["path"])
                try:
                    resolved = path.resolve(strict=False)
                    parent = resolved.parent
                    while parent != derived_root and parent.is_relative_to(derived_root):
                        try:
                            parent.rmdir()
                        except OSError:
                            break
                        parent = parent.parent
                except (OSError, ValueError) as exc:
                    filesystem_errors.append(f"artifact:{path}:{type(exc).__name__}:{exc}")

            refreshed_filesystem = self._filesystem_plan(plan["root"], plan["target"])
            original_unchanged = (
                refreshed_filesystem["original_manifest_sha256"]
                == plan["filesystem"]["original_manifest_sha256"]
            )
            foreign_key_violations = _rows(self.store, "PRAGMA foreign_key_check")
            result = {
                **self._public_plan(plan, mode="apply"),
                "status": (
                    "completed"
                    if not filesystem_errors
                    and original_unchanged
                    and not foreign_key_violations
                    else "failed"
                ),
                "database_locations_deleted": len(database["remove_locations"]),
                "documents_deleted": len(database["orphan_document_ids"]),
                "sources_deleted": len(database["sources_to_delete"]),
                "sidecars_deleted": sidecars_deleted,
                "artifact_files_deleted": artifact_files_deleted,
                "originals_unchanged": original_unchanged,
                "foreign_key_violations": foreign_key_violations,
                "filesystem_errors": filesystem_errors,
                "snapshot_path": str(snapshot_path),
                "snapshot_sha256": snapshot_sha,
                "archive_dir": str(archive_dir),
                "archive_manifest_sha256": archive_sha,
                "archived_files": len(archived_files),
            }
            _atomic_write(receipt_path, canonical_json(result) + "\n")
            result["receipt_path"] = str(receipt_path)
            if result["status"] != "completed":
                raise RuntimeError(
                    "focus cleanup completed with failed safety invariants; keep worker paused"
                )
            return result

    def restore_files(
        self, *, manifest_path: Path, dest_root: Path
    ) -> dict[str, Any]:
        """Restore archived sidecar/derived files from a cleanup manifest.

        Byte-for-byte restore of every archived member into ``dest_root`` using
        each entry's relative path. Verifies SHA-256 while copying.
        """
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = payload.get("files", [])
        archive_dir = manifest_path.parent
        restored: list[str] = []
        errors: list[str] = []
        for entry in entries:
            member = archive_dir / entry["archive_member"]
            target = dest_root / entry["relative_path"]
            try:
                data = member.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                if digest != entry["content_sha256"]:
                    raise ValueError("archive member hash mismatch")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                restored.append(entry["original_path"])
            except (OSError, ValueError) as exc:
                errors.append(f"{entry['original_path']}:{type(exc).__name__}:{exc}")
        return {
            "restored_count": len(restored),
            "restored_paths": restored,
            "errors": errors,
            "manifest_sha256": _sha256_file(manifest_path),
        }

    def restore_database(
        self, *, snapshot_path: Path, database_path: Path
    ) -> dict[str, Any]:
        """Rebuild deleted DB rows from the apply snapshot JSONL.

        Snapshot records are written in delete order (locations first, then
        child rows, documents, sources, entities). Restoring requires FK-safe
        reverse order: entities -> sources -> documents -> child rows ->
        locations. Every row is re-inserted with its full original fields.
        """
        if not database_path.is_file():
            raise ValueError("restore target database does not exist")
        records: list[dict[str, Any]] = []
        with snapshot_path.open(encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                records.append(payload)
        order = (
            "entities",
            "sources",
            "documents",
            *_DOCUMENT_CHILD_TABLES,
            "locations",
        )
        by_table = {table: [] for table in order}
        for record in records:
            table = record["table"]
            if table not in by_table:
                raise ValueError(f"snapshot contains unexpected table {table}")
            by_table[table].append(record["row"])

        restored_counts: dict[str, int] = {}
        with sqlite3.connect(str(database_path)) as connection:
            for table in order:
                rows = by_table[table]
                if not rows:
                    continue
                columns = list(rows[0].keys())
                placeholders = ",".join("?" for _ in columns)
                column_sql = ",".join(columns)
                connection.executemany(
                    f"INSERT OR IGNORE INTO {table} ({column_sql}) VALUES ({placeholders})",
                    [tuple(row.get(column) for column in columns) for row in rows],
                )
                restored_counts[table] = len(rows)
            fk_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if fk_violations:
                raise RuntimeError(
                    f"restore produced {len(fk_violations)} foreign key violations"
                )
        return {
            "restored_tables": restored_counts,
            "total_rows": len(records),
            "foreign_key_violations": 0,
            "snapshot_sha256": _sha256_file(snapshot_path),
        }


__all__ = [
    "FOCUS_CLEANUP_SCHEMA_VERSION",
    "FocusScopeCleanupService",
]
