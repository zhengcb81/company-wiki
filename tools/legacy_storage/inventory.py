"""Inventory: strictly read-only classification of legacy derived evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from legacy_storage.core import (
    REPORT_SCHEMA,
    db_numbers,
    integrity_probe,
    protected_objects,
    source_facts,
    tree_stats,
    utc_now_text,
    write_json,
)
from legacy_storage.selection import inventory_view

MANIFEST_SCHEMA = "cwp-storage-manifest/1"


@dataclass(frozen=True)
class InventoryResult:
    report: dict
    manifest: dict

    def write_manifest(self, output: Path) -> Path:
        write_json(Path(output), self.manifest)
        return Path(output)


def run_inventory(config, *, now: datetime | None = None) -> InventoryResult:
    """Read-only inventory; returns (report, manifest)."""
    catalog_dir = Path(config.catalog_dir)
    database_path = Path(config.database_path)
    derived_dir = Path(config.derived_dir)
    objects_stats = tree_stats(catalog_dir / "objects")

    facts = source_facts(database_path)
    db_stats = db_numbers(database_path)
    derived_stats = tree_stats(derived_dir)
    view = inventory_view(config, database_path)
    protected = protected_objects(database_path, catalog_dir)

    from legacy_storage.core import read_connection

    with read_connection(database_path) as probe:
        integrity = integrity_probe(probe)

    candidates = view["candidates"]
    candidate_bytes = sum(
        c["byte_size"]
        + sum(m["byte_size"] for m in c.get("managed_files") or [])
        for c in candidates
    )
    aggregated = {
        "candidate_count": len(candidates),
        "candidate_bytes": candidate_bytes,
        "derived_files_bytes": derived_stats["bytes"],
        "derived_file_count": derived_stats["files"],
        "excluded_count": len(view["excluded"]),
        "unreferenced_count": len(view["unreferenced"]),
        "unreferenced_bytes": sum(u["byte_size"] for u in view["unreferenced"]),
        "dangling_record_count": len(view["dangling"]),
        "span_total": view["span_total"],
        "span_parser_counts": view["span_parser_counts"],
        "source_facts_table_count": len(facts),
        "protected_object_bytes": objects_stats["bytes"],
        "protected_object_files": objects_stats["files"],
    }
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "created_at": utc_now_text(now),
        "catalog_dir": str(catalog_dir),
        "database_path": str(database_path),
        "aggregate": aggregated,
        "candidates": candidates,
        "excluded": view["excluded"],
        "resume": {
            "note": "retire-derived re-verifies every candidate (existence,"
            " containment, row status, content hash) before deleting",
        },
    }
    report = {
        "schema_version": REPORT_SCHEMA,
        "operation": "inventory",
        "dry_run": True,
        "status": "succeeded" if integrity["integrity_check"] == "ok" else "failed",
        "error_code": None
        if integrity["integrity_check"] == "ok"
        else "integrity_check_failed",
        "selection": {"mode": "legacy_derived", "catalog_dir": str(catalog_dir)},
        "source_facts_before": facts,
        "source_facts_after": facts,
        "protected_objects_before": protected,
        "protected_objects_after": protected,
        "candidates": candidates,
        "excluded": view["excluded"],
        "deleted": [],
        "already_absent": [dict(d, reason="file_missing") for d in view["dangling"]],
        "files_bytes_before": derived_stats["bytes"],
        "files_bytes_after": derived_stats["bytes"],
        "database_bytes_before": db_stats["file_bytes"],
        "database_bytes_after": db_stats["file_bytes"],
        "page_count_before": db_stats["page_count"],
        "page_count_after": db_stats["page_count"],
        "freelist_before": db_stats["freelist"],
        "freelist_after": db_stats["freelist"],
        "foreign_key_check": integrity["foreign_key_check"],
        "integrity_check": integrity["integrity_check"],
        "resume_notes": [],
        "manifest": aggregated,
        "unreferenced_derived": view["unreferenced"],
        "schema_inventory": view["schema_inventory"],
    }
    return InventoryResult(report=report, manifest=manifest)
