"""Focus admission cleanup — retired write maintenance (G3-CWP-MAINT).

The audited cleanup implementation (scope/plan/apply, confirmation token,
archive/restore of sidecars and derived files) is retired: the S5/S6 data
cleanup completed and the second destructive permission chain is gone.  Only
the import-compatible entry points remain, and every one of them fails closed
with the unified :class:`~.maintenance_retirement.RetiredMaintenanceError`
BEFORE opening a Store, taking the operation lock, or touching any file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .maintenance_retirement import RetiredMaintenanceError

FOCUS_CLEANUP_SCHEMA_VERSION = "1.0"


class FocusScopeCleanupService:
    """Retired focus-cleanup service: construction and every entry are inert.

    The constructor keeps the catalog reference without dereferencing it, so
    constructing the service never opens a Store or the database.
    """

    def __init__(self, catalog: Any) -> None:
        self.catalog = catalog

    def preview(
        self,
        *,
        root_id: str,
        relative_prefix: str,
        receipt_path: Path | None = None,
    ) -> dict[str, Any]:
        raise RetiredMaintenanceError("focus-cleanup")

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
        raise RetiredMaintenanceError("focus-cleanup")

    def restore_files(self, *, manifest_path: Path, dest_root: Path) -> dict[str, Any]:
        raise RetiredMaintenanceError("focus-cleanup-restore-files")

    def restore_database(
        self, *, snapshot_path: Path, database_path: Path
    ) -> dict[str, Any]:
        raise RetiredMaintenanceError("focus-cleanup-restore-database")


__all__ = [
    "FOCUS_CLEANUP_SCHEMA_VERSION",
    "FocusScopeCleanupService",
]
