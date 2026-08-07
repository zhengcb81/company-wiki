"""Read-only catalog size / health report (catalog-space-remediation Phase 4).

Measures DB file size, SQLite page/freelist counts, document and evidence-span
totals, and free disk on the DB's volume, with a warning threshold. Used for
weekly capacity monitoring (task_plan Phase 4/5.3).
"""
from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WARN_DISK_FREE_BYTES = 30 * 1_000_000_000  # 30 GB


@dataclass(frozen=True)
class SizeReport:
    database_bytes: int
    page_count: int
    freelist_count: int
    documents_total: int
    documents_retired: int
    evidence_spans_total: int
    disk_free_bytes: int
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def catalog_size_report(
    database_path: Path | str,
    *,
    warn_disk_free_bytes: int = WARN_DISK_FREE_BYTES,
) -> SizeReport:
    database_path = Path(database_path)
    database_bytes = database_path.stat().st_size

    conn = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        page_count = int(conn.execute("PRAGMA page_count").fetchone()[0])
        freelist_count = int(conn.execute("PRAGMA freelist_count").fetchone()[0])
        documents_total = int(
            conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        )
        documents_retired = int(
            conn.execute(
                "SELECT COUNT(*) FROM documents WHERE source_status='retired'"
            ).fetchone()[0]
        )
        evidence_spans_total = int(
            conn.execute("SELECT COUNT(*) FROM evidence_spans").fetchone()[0]
        )
    finally:
        conn.close()

    volume = database_path.drive or database_path.anchor or str(database_path.parent)
    disk_free_bytes = int(shutil.disk_usage(volume).free)

    warnings: list[str] = []
    if disk_free_bytes < warn_disk_free_bytes:
        warnings.append(
            f"disk free {disk_free_bytes / 1e9:.1f} GB < "
            f"{warn_disk_free_bytes / 1e9:.0f} GB warning threshold"
        )
    return SizeReport(
        database_bytes=database_bytes,
        page_count=page_count,
        freelist_count=freelist_count,
        documents_total=documents_total,
        documents_retired=documents_retired,
        evidence_spans_total=evidence_spans_total,
        disk_free_bytes=disk_free_bytes,
        warnings=tuple(warnings),
    )


__all__ = ["SizeReport", "WARN_DISK_FREE_BYTES", "catalog_size_report"]
