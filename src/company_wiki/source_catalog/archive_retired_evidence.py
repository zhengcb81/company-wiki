"""Archive retired documents' evidence spans to gzip JSONL (Phase 2.1).

Streaming read-only export of ``evidence_spans`` for retired documents into
``source_manifests/archive/{yyyy-mm-dd}/retired-evidence.jsonl.gz`` with a row
count reconciliation against the live catalog. Runs on a read-only connection,
so it does not take the operation lock and may run while the worker is busy
(retired documents are never re-normalized, so their spans are stable).
"""
from __future__ import annotations

import gzip
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

BATCH_SIZE = 100_000

_SELECT = """SELECT e.span_id, e.source_id, e.document_id, e.locator, e.page_number,
                     e.paragraph_index, e.table_index, e.raw_text, e.span_json,
                     e.parser_name, e.parser_version, e.parse_status
              FROM evidence_spans e
              JOIN documents d ON d.document_id = e.document_id
              WHERE d.source_status = 'retired'"""


@dataclass(frozen=True)
class ArchiveReport:
    archive_path: str
    rows_written: int
    rows_in_catalog: int
    ok: bool

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def archive_retired_evidence(
    database_path: Path | str,
    archive_root: Path | str,
    *,
    progress: Callable[[int, int], None] | None = None,
) -> ArchiveReport:
    database_path = Path(database_path)
    archive_root = Path(archive_root)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = archive_root / "archive" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "retired-evidence.jsonl.gz"

    conn = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        total = int(
            conn.execute(
                "SELECT COUNT(*) FROM evidence_spans WHERE document_id IN "
                "(SELECT document_id FROM documents WHERE source_status='retired')"
            ).fetchone()[0]
        )

        rows_written = 0
        last_id: str | None = None
        with gzip.open(out_path, "wt", encoding="utf-8", newline="\n") as fh:
            while True:
                if last_id is None:
                    rows = conn.execute(
                        _SELECT + " ORDER BY e.span_id LIMIT ?", (BATCH_SIZE,)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        _SELECT + " AND e.span_id > ? ORDER BY e.span_id LIMIT ?",
                        (last_id, BATCH_SIZE),
                    ).fetchall()
                if not rows:
                    break
                for row in rows:
                    fh.write(json.dumps(dict(row), ensure_ascii=False) + "\n")
                    last_id = row["span_id"]
                rows_written += len(rows)
                if progress is not None:
                    progress(rows_written, total)
    finally:
        conn.close()

    return ArchiveReport(
        archive_path=str(out_path.resolve()),
        rows_written=rows_written,
        rows_in_catalog=total,
        ok=rows_written == total,
    )


__all__ = ["ArchiveReport", "archive_retired_evidence"]
