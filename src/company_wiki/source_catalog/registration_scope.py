"""Storage-owned registration orchestration and bounded location access."""

from __future__ import annotations

from typing import Any

from .models import CatalogConfig, ScanReport
from .source_group_scope import SourceRegistrationScope
from .store import CatalogStore

def existing_group_locations(store: CatalogStore, root_id: str,
                             relative_paths: set[str] | None) -> dict[str, Any]:
    columns = "relative_path,source_id,document_id,observed_size,observed_mtime_ns,manifest_json,location_status,error"
    if relative_paths is None:
        rows = store.fetchall(f"SELECT {columns} FROM locations WHERE root_id=?", (root_id,))
    else:
        rows = []
        paths = sorted(relative_paths)
        # Bounded SQL parameters; no full-root SELECT followed by Python filtering.
        for start in range(0, len(paths), 500):
            part = paths[start:start + 500]
            marks = ",".join("?" for _ in part)
            rows.extend(store.fetchall(
                f"SELECT {columns} FROM locations WHERE root_id=? AND relative_path IN ({marks})",
                (root_id, *part),
            ))
    return {row["relative_path"]: row for row in rows}


def register_catalog_sources(config: CatalogConfig, store: CatalogStore,
                             scope: SourceRegistrationScope, *, progress=None) -> ScanReport:
    """Register explicit source groups; caller owns the existing catalog lock.

    Uses the one scanner normalization/transaction implementation. Root adapter
    declarations determine discovery; a historical rollout flag cannot change
    the importer into a different reader or a complete root reconciliation.
    """
    from .scanner import scan_catalog

    selected = next((root for root in config.roots if root.root_id == scope.root_id), None)
    if selected is None:
        raise ValueError("registration root is not configured")
    return scan_catalog(config, store, root_ids={scope.root_id},
                        relative_paths=set(scope.relative_paths),
                        v2_scan_shadow=bool(selected.adapter_id), progress=progress)
