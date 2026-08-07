"""Prune retired documents' evidence spans after the retention window (Phase 2.3).

Evidence for retired documents is archived to ``source_manifests/archive/{date}``
(Phase 2.1). Once the oldest archive date is at least ``RETENTION_DAYS`` old,
the retired spans may be physically deleted (the archive is the protected copy).
Dry-run by default; ``--apply`` is explicit and runs under
``CatalogOperationLock``, deleting in batches with a receipt written to
``artifacts/gates``.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .lock import CatalogOperationLock
from .models import CatalogConfig
from .store import CatalogStore

RETENTION_DAYS = 90
BATCH_SIZE = 100_000

_DELETE_BATCH = """DELETE FROM evidence_spans WHERE span_id IN (
    SELECT span_id FROM evidence_spans WHERE document_id IN (
        SELECT document_id FROM documents WHERE source_status='retired')
    ORDER BY span_id LIMIT ?)"""


@dataclass(frozen=True)
class PruneReport:
    dry_run: bool
    retired_documents: int
    span_rows: int
    oldest_archive: str | None
    retention_days: int
    due: bool
    deleted_rows: int = 0
    receipt_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        if self.receipt_path is None:
            d.pop("receipt_path", None)
        return d


def _iso_date(name: str) -> bool:
    try:
        date.fromisoformat(name)
        return True
    except ValueError:
        return False


def prune_retired_evidence(
    config: CatalogConfig,
    archive_root: Path,
    *,
    apply: bool = False,
    retention_days: int = RETENTION_DAYS,
) -> PruneReport:
    archive_dir = archive_root / "archive"
    dates = sorted(
        d.name
        for d in archive_dir.iterdir()
        if d.is_dir() and len(d.name) == 10 and _iso_date(d.name)
    ) if archive_dir.exists() else []
    oldest = dates[0] if dates else None
    today = datetime.now(timezone.utc).date()
    due = False
    if oldest is not None:
        due = (today - date.fromisoformat(oldest)).days >= retention_days

    conn = sqlite3.connect(f"file:{config.database_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        span_rows = int(
            conn.execute(
                "SELECT COUNT(*) FROM evidence_spans WHERE document_id IN "
                "(SELECT document_id FROM documents WHERE source_status='retired')"
            ).fetchone()[0]
        )
        retired = int(
            conn.execute(
                "SELECT COUNT(*) FROM documents WHERE source_status='retired'"
            ).fetchone()[0]
        )
    finally:
        conn.close()

    if not apply:
        return PruneReport(
            dry_run=True,
            retired_documents=retired,
            span_rows=span_rows,
            oldest_archive=oldest,
            retention_days=retention_days,
            due=due,
        )
    if not due:
        return PruneReport(
            dry_run=False,
            retired_documents=retired,
            span_rows=span_rows,
            oldest_archive=oldest,
            retention_days=retention_days,
            due=False,
        )

    with CatalogOperationLock(config.catalog_dir, operation="prune_retired_evidence"):
        store = CatalogStore(config.database_path)
        deleted = 0
        while True:
            with store.transaction() as connection:
                cursor = connection.execute(_DELETE_BATCH, (BATCH_SIZE,))
                batch = cursor.rowcount
            deleted += batch
            if batch < BATCH_SIZE:
                break

    now = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    receipt_path = (
        config.catalog_dir / "artifacts" / "gates" / f"prune-retired-{now}.json"
    )
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {
                "oldest_archive": oldest,
                "retired_documents": retired,
                "span_rows_before": span_rows,
                "deleted_rows": deleted,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return PruneReport(
        dry_run=False,
        retired_documents=retired,
        span_rows=span_rows,
        oldest_archive=oldest,
        retention_days=retention_days,
        due=True,
        deleted_rows=deleted,
        receipt_path=str(receipt_path.resolve()),
    )


__all__ = ["PruneReport", "RETENTION_DAYS", "prune_retired_evidence"]
