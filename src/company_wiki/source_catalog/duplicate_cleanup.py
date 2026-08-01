"""User-selected, fail-closed recycling of indexed exact-copy locations."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable
import uuid

from .lock import CatalogOperationLock
from .service import SourceCatalog
from .store import canonical_json


DUPLICATE_CLEANUP_SCHEMA_VERSION = "1.0"
Recycler = Callable[[Path], None]


class DuplicateCleanupError(RuntimeError):
    """Raised when a requested duplicate recycle action is unsafe or incomplete."""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def recycle_to_windows_bin(path: Path) -> None:
    """Move one file to the Windows Recycle Bin without showing shell prompts."""
    if os.name != "nt":
        raise DuplicateCleanupError("Windows Recycle Bin is unavailable on this platform")
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    if not path.is_file() or path.is_symlink():
        raise DuplicateCleanupError("recycle target must be one existing regular file")

    class SHFileOperationStruct(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.SHFileOperationW.argtypes = (ctypes.POINTER(SHFileOperationStruct),)
    shell32.SHFileOperationW.restype = ctypes.c_int
    operation = SHFileOperationStruct()
    operation.wFunc = 3  # FO_DELETE
    operation.pFrom = str(path) + "\0\0"
    operation.pTo = None
    operation.fFlags = 0x0040 | 0x0010 | 0x0004 | 0x0400  # ALLOWUNDO, no UI
    result = shell32.SHFileOperationW(ctypes.byref(operation))
    if result != 0:
        raise DuplicateCleanupError(f"Windows Recycle Bin operation failed: code={result}")
    if operation.fAnyOperationsAborted:
        raise DuplicateCleanupError("Windows Recycle Bin operation was aborted")


class DuplicateCleanupJournal:
    """Append-only audit events; callers hold the catalog writer lock."""

    def __init__(self, catalog_dir: Path):
        self.path = catalog_dir / "duplicate_cleanup_events.jsonl"

    def record(
        self,
        *,
        action_id: str,
        event: str,
        location_id: str,
        absolute_path: str,
        canonical_location_id: str,
        canonical_path: str,
        source_id: str,
        content_sha256: str,
        error_type: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        if event not in {"requested", "recycled", "failed"}:
            raise ValueError(f"unsupported duplicate cleanup event: {event}")
        values = {
            "schema_version": DUPLICATE_CLEANUP_SCHEMA_VERSION,
            "event_id": "urn:company-wiki:duplicate-cleanup-event:uuid:" + uuid.uuid4().hex,
            "action_id": action_id,
            "event": event,
            "recorded_at": _utc_now(),
            "location_id": location_id,
            "absolute_path": absolute_path,
            "canonical_location_id": canonical_location_id,
            "canonical_path": canonical_path,
            "source_id": source_id,
            "content_sha256": content_sha256,
            "error_type": error_type,
            "error": error,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (canonical_json(values) + "\n").encode("utf-8")
        with self.path.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        return values

    def read_all(self) -> tuple[dict[str, Any], ...]:
        if not self.path.is_file():
            return ()
        events: list[dict[str, Any]] = []
        required = {
            "schema_version",
            "event_id",
            "action_id",
            "event",
            "recorded_at",
            "location_id",
            "absolute_path",
            "canonical_location_id",
            "canonical_path",
            "source_id",
            "content_sha256",
            "error_type",
            "error",
        }
        for line_number, raw in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid duplicate cleanup journal line {line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict) or set(value) != required:
                raise ValueError(
                    f"invalid duplicate cleanup journal fields on line {line_number}"
                )
            if value["schema_version"] != DUPLICATE_CLEANUP_SCHEMA_VERSION:
                raise ValueError(
                    f"unsupported duplicate cleanup journal schema on line {line_number}"
                )
            events.append(value)
        return tuple(events)


class DuplicateCleanupService:
    """Present and recycle exact copies by stable catalog location ID only."""

    def __init__(
        self,
        catalog: SourceCatalog,
        *,
        recycler: Recycler | None = None,
    ):
        if not isinstance(catalog, SourceCatalog):
            raise TypeError("catalog must be SourceCatalog")
        self.catalog = catalog
        self.recycler = recycler or recycle_to_windows_bin
        self.journal = DuplicateCleanupJournal(catalog.config.catalog_dir)

    def list_groups(
        self,
        *,
        text: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_semantic: bool = False,
    ) -> dict[str, Any]:
        if limit <= 0 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        normalized_text = text.casefold().strip() if text else ""
        location_rows = self.catalog.store.fetchall(
            """WITH duplicate_keys AS (
                SELECT document_id,source_id
                FROM locations
                WHERE role='original_primary' AND location_status='active'
                AND document_id IS NOT NULL AND source_id IS NOT NULL
                GROUP BY document_id,source_id HAVING COUNT(*) > 1
            )
            SELECT l.location_id,l.document_id,l.root_id,l.relative_path,l.absolute_path,
            l.source_id,l.role,l.location_status,l.observed_size,l.observed_mtime_ns,
            r.priority AS root_priority,d.title,d.document_kind,d.published_date,
            s.content_sha256
            FROM duplicate_keys k
            JOIN locations l ON l.document_id=k.document_id AND l.source_id=k.source_id
            JOIN roots r ON r.root_id=l.root_id
            JOIN documents d ON d.document_id=l.document_id
            JOIN sources s ON s.source_id=l.source_id
            WHERE l.role='original_primary' AND l.location_status='active'
            ORDER BY d.document_id,l.source_id,r.priority,l.root_id,l.relative_path,l.location_id"""
        )
        entity_rows = self.catalog.store.fetchall(
            """SELECT de.document_id,e.name FROM document_entities de
            JOIN entities e ON e.entity_id=de.entity_id ORDER BY de.document_id,e.entity_id"""
        )
        entities_by_document: dict[str, list[str]] = {}
        for item in entity_rows:
            entities_by_document.setdefault(item["document_id"], []).append(item["name"])
        locations_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for item in location_rows:
            locations_by_key.setdefault(
                (item["document_id"], item["source_id"]),
                [],
            ).append(dict(item))
        groups: list[dict[str, Any]] = []
        for (document_id, source_id), raw_locations in locations_by_key.items():
            locations = self.catalog._annotate_locations(document_id, raw_locations)
            canonical = next(item for item in locations if item["is_canonical"])
            duplicates = [
                item for item in locations if item["duplicate_relation"] == "exact_copy"
            ]
            if not duplicates:
                continue
            group_id = canonical["duplicate_group_id"]
            public_canonical = self._public_location(
                canonical,
                eligible=False,
                protection_reason="canonical_copy",
            )
            public_duplicates = [
                self._public_location(item, eligible=True, protection_reason=None)
                for item in duplicates
            ]
            entity_names = entities_by_document.get(document_id, [])
            group = {
                "duplicate_group_id": group_id,
                "relation_type": "exact_copy",
                "document_id": document_id,
                "title": canonical["title"],
                "document_kind": canonical["document_kind"],
                "published_date": canonical["published_date"],
                "entities": entity_names,
                "source_id": source_id,
                "content_sha256": canonical["content_sha256"],
                "copy_count": 1 + len(public_duplicates),
                "reclaimable_copy_count": len(public_duplicates),
                "reclaimable_bytes": sum(
                    int(item["size_bytes"] or 0) for item in public_duplicates
                ),
                "canonical": public_canonical,
                "duplicates": public_duplicates,
            }
            searchable = "\n".join(
                [
                    group_id,
                    canonical["title"],
                    canonical["document_kind"],
                    canonical["published_date"] or "",
                    *entity_names,
                    public_canonical["absolute_path"],
                    *(item["absolute_path"] for item in public_duplicates),
                ]
            ).casefold()
            if not normalized_text or normalized_text in searchable:
                groups.append(group)
        if include_semantic:
            for semantic in self.catalog.semantic_duplicate_groups():
                public_canonical = self._public_location(
                    semantic["canonical"],
                    eligible=False,
                    protection_reason="semantic_review_only",
                )
                public_duplicates = [
                    self._public_location(
                        item, eligible=False, protection_reason="semantic_review_only"
                    )
                    for item in semantic["duplicates"]
                ]
                group = {
                    "duplicate_group_id": semantic["duplicate_group_id"],
                    "relation_type": "semantic_copy",
                    "document_id": semantic["document_id"],
                    "title": semantic["title"],
                    "document_kind": semantic["document_kind"],
                    "published_date": semantic["published_date"],
                    "entities": semantic["entities"],
                    "source_id": semantic["source_id"],
                    "content_sha256": semantic["content_sha256"],
                    "copy_count": semantic["copy_count"],
                    "reclaimable_copy_count": 0,
                    "reclaimable_bytes": 0,
                    "canonical": public_canonical,
                    "duplicates": public_duplicates,
                }
                searchable = "\n".join(
                    [
                        group["duplicate_group_id"],
                        group["title"],
                        group["document_kind"],
                        group["published_date"] or "",
                        *group["entities"],
                        public_canonical["absolute_path"],
                        *(item["absolute_path"] for item in public_duplicates),
                    ]
                ).casefold()
                if not normalized_text or normalized_text in searchable:
                    groups.append(group)
        groups.sort(
            key=lambda item: (
                str(item["entities"][0] if item["entities"] else "").casefold(),
                str(item["published_date"] or ""),
                str(item["title"]).casefold(),
                str(item["duplicate_group_id"]),
            )
        )
        total_groups = len(groups)
        total_copies = sum(int(item["reclaimable_copy_count"]) for item in groups)
        total_bytes = sum(int(item["reclaimable_bytes"]) for item in groups)
        return {
            "schema_version": DUPLICATE_CLEANUP_SCHEMA_VERSION,
            "total_groups": total_groups,
            "total_reclaimable_copies": total_copies,
            "total_reclaimable_bytes": total_bytes,
            "offset": offset,
            "limit": limit,
            "groups": groups[offset : offset + limit],
        }

    @staticmethod
    def _public_location(
        location: dict[str, Any],
        *,
        eligible: bool,
        protection_reason: str | None,
    ) -> dict[str, Any]:
        return {
            "location_id": location["location_id"],
            "root_id": location["root_id"],
            "root_priority": int(location["root_priority"]),
            "relative_path": location["relative_path"],
            "absolute_path": location["absolute_path"],
            "size_bytes": location["observed_size"],
            "is_canonical": bool(location["is_canonical"]),
            "duplicate_relation": location["duplicate_relation"],
            "eligible_for_recycle": eligible,
            "protection_reason": protection_reason,
        }

    def preview(self, location_id: str) -> dict[str, Any]:
        prepared = self._prepare(location_id)
        token = self._confirmation_token(prepared)
        return {
            "schema_version": DUPLICATE_CLEANUP_SCHEMA_VERSION,
            "status": "ready",
            "location_id": prepared["location"]["location_id"],
            "absolute_path": str(prepared["path"]),
            "root_id": prepared["location"]["root_id"],
            "size_bytes": prepared["path_stat"].st_size,
            "source_id": prepared["source_id"],
            "content_sha256": prepared["content_sha256"],
            "canonical_location_id": prepared["canonical"]["location_id"],
            "canonical_path": str(prepared["canonical_path"]),
            "confirmation_token": token,
            "confirmation_phrase": "RECYCLE " + token[-8:].upper(),
            "action": "move_to_windows_recycle_bin",
            "recoverable": True,
        }

    def recycle(
        self,
        location_id: str,
        *,
        confirmation_token: str,
    ) -> dict[str, Any]:
        if not isinstance(confirmation_token, str) or not confirmation_token:
            raise DuplicateCleanupError("confirmation token is required")
        with CatalogOperationLock(
            self.catalog.config.catalog_dir,
            operation="duplicate_recycle",
        ):
            prepared = self._prepare(location_id)
            expected_token = self._confirmation_token(prepared)
            if confirmation_token != expected_token:
                raise DuplicateCleanupError(
                    "confirmation token is stale; preview the duplicate again"
                )
            path = prepared["path"]
            canonical_path = prepared["canonical_path"]
            content_sha256 = prepared["content_sha256"]
            if _sha256_file(canonical_path) != content_sha256:
                raise DuplicateCleanupError("canonical file hash no longer matches the catalog")
            if _sha256_file(path) != content_sha256:
                raise DuplicateCleanupError("duplicate file hash no longer matches the catalog")

            action_id = "urn:company-wiki:duplicate-cleanup-action:uuid:" + uuid.uuid4().hex
            event_values = {
                "action_id": action_id,
                "location_id": prepared["location"]["location_id"],
                "absolute_path": str(path),
                "canonical_location_id": prepared["canonical"]["location_id"],
                "canonical_path": str(canonical_path),
                "source_id": prepared["source_id"],
                "content_sha256": content_sha256,
            }
            self.journal.record(event="requested", **event_values)
            try:
                self.recycler(path)
                if path.exists():
                    raise DuplicateCleanupError(
                        "recycler returned without removing the selected copy"
                    )
                with self.catalog.store.transaction() as connection:
                    cursor = connection.execute(
                        """UPDATE locations SET location_status='missing'
                        WHERE location_id=? AND location_status='active' AND source_id=?""",
                        (prepared["location"]["location_id"], prepared["source_id"]),
                    )
                    if cursor.rowcount != 1:
                        raise DuplicateCleanupError(
                            "catalog location changed while the file was being recycled"
                        )
            except Exception as exc:
                self.journal.record(
                    event="failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                    **event_values,
                )
                if isinstance(exc, DuplicateCleanupError):
                    raise
                raise DuplicateCleanupError(str(exc)) from exc
            self.journal.record(event="recycled", **event_values)
            return {
                "schema_version": DUPLICATE_CLEANUP_SCHEMA_VERSION,
                "status": "recycled",
                "action_id": action_id,
                "location_id": prepared["location"]["location_id"],
                "absolute_path": str(path),
                "canonical_location_id": prepared["canonical"]["location_id"],
                "canonical_path": str(canonical_path),
                "content_sha256": content_sha256,
                "recoverable": True,
                "recovery_location": "Windows Recycle Bin",
            }

    def _prepare(self, location_id: str) -> dict[str, Any]:
        if not isinstance(location_id, str) or not location_id.strip():
            raise DuplicateCleanupError("location_id must be non-empty text")
        indexed = self.catalog.store.fetchone(
            """SELECT l.location_id,l.document_id,l.root_id,l.relative_path,l.absolute_path,
            l.source_id,l.role,l.location_status,l.observed_size,l.observed_mtime_ns,
            r.priority AS root_priority FROM locations l JOIN roots r ON r.root_id=l.root_id
            WHERE l.location_id=?""",
            (location_id,),
        )
        if indexed is None:
            raise DuplicateCleanupError("location is not an indexed exact-copy")
        target = dict(indexed)
        if (
            target["role"] != "original_primary"
            or target["location_status"] != "active"
            or not target["document_id"]
            or not target["source_id"]
        ):
            raise DuplicateCleanupError(
                "location is not an active noncanonical exact-copy"
            )
        peers = [
            dict(item)
            for item in self.catalog.store.fetchall(
                """SELECT l.location_id,l.document_id,l.root_id,l.relative_path,l.absolute_path,
                l.source_id,l.role,l.location_status,l.observed_size,l.observed_mtime_ns,
                r.priority AS root_priority FROM locations l JOIN roots r ON r.root_id=l.root_id
                WHERE l.document_id=? AND l.source_id=? AND l.role='original_primary'
                AND l.location_status='active'
                ORDER BY r.priority,l.root_id,l.relative_path,l.location_id""",
                (target["document_id"], target["source_id"]),
            )
        ]
        if len(peers) <= 1:
            raise DuplicateCleanupError("location is not an indexed exact-copy")
        annotated = self.catalog._annotate_locations(target["document_id"], peers)
        target = next(item for item in annotated if item["location_id"] == location_id)
        if target["is_canonical"]:
            raise DuplicateCleanupError("canonical copy is protected and cannot be recycled")
        if target["duplicate_relation"] != "exact_copy":
            raise DuplicateCleanupError(
                "location is not an active noncanonical exact-copy"
            )
        canonical = next(item for item in annotated if item["is_canonical"])
        source = self.catalog.store.fetchone(
            "SELECT content_sha256 FROM sources WHERE source_id=?",
            (target["source_id"],),
        )
        if source is None:
            raise DuplicateCleanupError("source hash is unavailable")
        path, path_stat = self._validated_path(target)
        canonical_path, canonical_stat = self._validated_path(canonical)
        if path == canonical_path:
            raise DuplicateCleanupError("duplicate and canonical resolve to the same path")
        return {
            "location": target,
            "canonical": canonical,
            "path": path,
            "path_stat": path_stat,
            "canonical_path": canonical_path,
            "canonical_stat": canonical_stat,
            "source_id": target["source_id"],
            "content_sha256": source["content_sha256"],
        }

    def _validated_path(self, location: dict[str, Any]) -> tuple[Path, os.stat_result]:
        root = next(
            (
                item
                for item in self.catalog.config.roots
                if item.root_id == location["root_id"]
            ),
            None,
        )
        if root is None:
            raise DuplicateCleanupError("location root is no longer configured")
        indexed_path = Path(location["absolute_path"])
        if indexed_path.is_symlink():
            raise DuplicateCleanupError("symbolic-link locations cannot be recycled")
        try:
            resolved_root = root.path.resolve(strict=True)
            resolved_path = indexed_path.resolve(strict=True)
            relative_parts = Path(location["relative_path"]).parts
            expected_path = resolved_root.joinpath(*relative_parts).resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise DuplicateCleanupError("indexed file or configured root no longer exists") from exc
        if not resolved_path.is_relative_to(resolved_root) or resolved_path != expected_path:
            raise DuplicateCleanupError("indexed path is outside its configured root")
        if not resolved_path.is_file() or resolved_path.is_symlink():
            raise DuplicateCleanupError("indexed location is not one regular file")
        return resolved_path, resolved_path.stat()

    @staticmethod
    def _confirmation_token(prepared: dict[str, Any]) -> str:
        values = {
            "location_id": prepared["location"]["location_id"],
            "canonical_location_id": prepared["canonical"]["location_id"],
            "source_id": prepared["source_id"],
            "content_sha256": prepared["content_sha256"],
            "absolute_path": str(prepared["path"]),
            "canonical_path": str(prepared["canonical_path"]),
            "size": prepared["path_stat"].st_size,
            "mtime_ns": prepared["path_stat"].st_mtime_ns,
            "canonical_size": prepared["canonical_stat"].st_size,
            "canonical_mtime_ns": prepared["canonical_stat"].st_mtime_ns,
        }
        return hashlib.sha256(canonical_json(values).encode("utf-8")).hexdigest()


__all__ = [
    "DUPLICATE_CLEANUP_SCHEMA_VERSION",
    "DuplicateCleanupError",
    "DuplicateCleanupJournal",
    "DuplicateCleanupService",
    "recycle_to_windows_bin",
]
