"""Duplicate maintenance: read-only inventory retained, writes retired.

The user-selected recycling flow (preview → confirmation token → recycle bin
→ tombstone + journal events) is retired (G3-CWP-MAINT): the destructive
permission chain and its confirmation token are gone, and raw originals are
never deleted through this path.  What remains:

* :meth:`DuplicateCleanupService.list_groups` — the read-only inventory entry
  (source/document/location IDs, SHA, root order, canonical vs semantic,
  pagination) served from the zero-write ``catalog.reader``;
* :meth:`DuplicateCleanupJournal.read_all` — historical journal reading;
* thin retired entries for preview / recycle / recycle-bin / journal record,
  each raising the unified retirement signal (delivered through
  ``DuplicateMaintenanceRetired``, which is a ``RetiredMaintenanceError`` for
  new consumers and still a ``DuplicateCleanupError`` for legacy catchers)
  BEFORE any Store, hash, root, token or journal check runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .maintenance_retirement import RetiredMaintenanceError
from .service import SourceCatalog


DUPLICATE_CLEANUP_SCHEMA_VERSION = "1.0"
Recycler = Callable[[Path], None]


class DuplicateCleanupError(RuntimeError):
    """Raised when a requested duplicate recycle action is unsafe or incomplete."""


class DuplicateMaintenanceRetired(RetiredMaintenanceError, DuplicateCleanupError):
    """A retired duplicate-maintenance write entry was called.

    The canonical signal is :class:`RetiredMaintenanceError` (``code`` and
    ``operation``); the second base keeps legacy ``DuplicateCleanupError``
    catchers working for the retired preview/recycle entries.
    """


def recycle_to_windows_bin(path: Path) -> None:
    """Retired: never moves a file again; raises before touching the path."""
    raise DuplicateMaintenanceRetired("duplicate-recycle-bin")


class DuplicateCleanupJournal:
    """Append-only audit events; callers hold the catalog writer lock.

    Reading (``read_all``) is retained for historical audit/export; writing
    (``record``) is retired and fails closed before creating the file.
    """

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
        raise DuplicateMaintenanceRetired("duplicate-journal-record")

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
    """Read-only exact-copy inventory; every write entry is retired.

    Construction keeps the catalog reference without opening a Store; the
    inventory reads through ``catalog.reader`` only.
    """

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
        text: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_semantic: bool = False,
    ) -> dict[str, Any]:
        """Read-only inventory of exact-copy (and optional semantic) groups.

        Inventory only: ``eligible_for_recycle`` is uniformly false, no
        confirmation token is minted, and ``reclaimable_*`` totals are the
        registered upper bound — nothing here authorises a deletion.
        """
        if limit <= 0 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        normalized_text = text.casefold().strip() if text else ""
        reader = self.catalog.reader
        location_rows = reader.fetchall(
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
        entity_rows = reader.fetchall(
            """SELECT de.document_id,e.name FROM document_entities de
            JOIN entities e ON e.entity_id=de.entity_id ORDER BY de.document_id,e.entity_id"""
        )
        entities_by_document: dict[str, list[str]] = {}
        for item in entity_rows:
            entities_by_document.setdefault(item["document_id"], []).append(
                item["name"]
            )
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
                self._public_location(
                    item,
                    eligible=False,
                    protection_reason="maintenance_retired",
                )
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
                        item,
                        eligible=False,
                        protection_reason="semantic_review_only",
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
            "inventory_only": True,
            "original_delete_count": 0,
            "reclaimable_is_upper_bound": True,
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
        raise DuplicateMaintenanceRetired("duplicate-preview")

    def recycle(
        self,
        location_id: str,
        *,
        confirmation_token: str,
    ) -> dict[str, Any]:
        raise DuplicateMaintenanceRetired("duplicate-recycle")


__all__ = [
    "DUPLICATE_CLEANUP_SCHEMA_VERSION",
    "DuplicateCleanupError",
    "DuplicateCleanupJournal",
    "DuplicateCleanupService",
    "DuplicateMaintenanceRetired",
    "recycle_to_windows_bin",
]
