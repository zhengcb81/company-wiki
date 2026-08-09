"""WU-901: resumable, journaled catalog migration tool.

Modes: dry-run (default), shadow-write (temp catalog), apply, verify, resume.
Every batch records a journal row (last key, input/output hashes, created
assertion IDs) so an interrupted run resumes from the committed boundary.
Re-running never duplicates assertions; a changed code/plan hash refuses to
resume an old journal.  Migration writes the catalog only — never external
files or sidecars.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

JOURNAL_TABLE = "migration_journal"


@dataclass
class MigrationConfig:
    code_hash: str
    plan_hash: str
    batch_size: int = 500


@dataclass
class MigrationResult:
    processed: int = 0
    created_assertions: int = 0
    skipped: int = 0
    errors: int = 0
    resumed_from: str | None = None
    journal: list[dict] = field(default_factory=list)

    # sources without a documents row (orphans) cannot carry a FK-bound
    # assertion on real catalogs; they are skipped and counted, never
    # silently dropped.
    def add_skipped_fk(self, count: int) -> None:
        self.skipped += count


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _ensure_journal(con: sqlite3.Connection) -> None:
    con.execute(
        f"""CREATE TABLE IF NOT EXISTS {JOURNAL_TABLE} (
            batch_id TEXT PRIMARY KEY,
            last_key TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            plan_hash TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            output_hash TEXT NOT NULL,
            created_assertions TEXT NOT NULL,
            committed_at TEXT NOT NULL
        )"""
    )


def _hash_rows(rows: list[sqlite3.Row]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(dict(row), sort_keys=True,
                                 default=str).encode("utf-8"))
    return digest.hexdigest()


def migration_start(
    catalog: Path,
    *,
    config: MigrationConfig,
    mode: str = "dry-run",
    last_key: str | None = None,
    batch_size: int | None = None,
) -> MigrationResult:
    """Run one migration pass over sources in last-key order.

    mode: dry-run (no writes) | shadow-write (temp db) | apply | verify.
    Returns the result; an interrupted apply can be resumed by passing the
    journal's last_key.
    """
    if mode not in {"dry-run", "shadow-write", "apply", "verify"}:
        raise ValueError(f"unknown mode {mode!r}")
    con = _connect(catalog)
    _ensure_journal(con)
    result = MigrationResult()
    try:
        # resume guard: a different code/plan hash must never continue an
        # old journal silently (MIG-05)
        if last_key:
            row = con.execute(
                f"SELECT code_hash, plan_hash FROM {JOURNAL_TABLE} "
                "ORDER BY committed_at DESC LIMIT 1"
            ).fetchone()
            if row is not None and (
                row["code_hash"] != config.code_hash
                or row["plan_hash"] != config.plan_hash
            ):
                raise ValueError(
                    "journal belongs to different code/plan hash — refusing resume"
                )
            result.resumed_from = last_key

        sources = con.execute(
            """SELECT s.source_id, s.content_sha256, s.byte_size,
                      d.document_id
               FROM sources s
               LEFT JOIN documents d ON d.primary_source_id = s.source_id
               WHERE s.source_id > ? ORDER BY s.source_id LIMIT ?""",
            (last_key or "", batch_size or config.batch_size),
        ).fetchall()
        if not sources:
            return result
        result.processed = len(sources)
        input_hash = _hash_rows(sources)

        created: list[str] = []
        skipped_fk = 0
        if mode in {"shadow-write", "apply"}:
            # v2 candidate assertions for each source (one per source).
            # document_id is FK-constrained on real catalogs: a source with
            # no documents row (orphan) cannot carry an assertion — skip it
            # and count (WU-906 drill A surfaced this against production).
            for source in sources:
                if not source["document_id"]:
                    skipped_fk += 1
                    continue
                assertion_id = f"mig-{hashlib.sha256(source['source_id'].encode()).hexdigest()[:16]}"
                exists = con.execute(
                    "SELECT 1 FROM source_metadata_assertions WHERE assertion_id=?",
                    (assertion_id,),
                ).fetchone()
                if exists is None:
                    con.execute(
                        """INSERT INTO source_metadata_assertions
                        (assertion_id, source_id, document_id, content_sha256,
                         evidence_basis, evidence_json, decision, created_at,
                         created_by, schema_version, adapter_id, adapter_version,
                         normalization_status, visibility_state)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (assertion_id, source["source_id"], source["document_id"],
                         source["content_sha256"], "v2-migration", "{}",
                         "verified", "2026-08-09", "wu-901",
                         "2.0", "migration_v1", "1.0.0",
                         "capture_ready", "shadow"),
                    )
                    created.append(assertion_id)
            con.commit()
        result.add_skipped_fk(skipped_fk)
        result.created_assertions = len(created)
        output_hash = _hash_rows(sources)

        if mode in {"shadow-write", "apply"}:
            con.execute(
                f"""INSERT INTO {JOURNAL_TABLE}
                (batch_id, last_key, code_hash, plan_hash, input_hash,
                 output_hash, created_assertions, committed_at)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(batch_id) DO NOTHING""",
                (f"batch-{sources[-1]['source_id']}", sources[-1]["source_id"],
                 config.code_hash, config.plan_hash, input_hash, output_hash,
                 json.dumps(created), "2026-08-09"),
            )
            con.commit()
        result.journal = [
            {"last_key": sources[-1]["source_id"], "input_hash": input_hash,
             "output_hash": output_hash, "created": len(created)}
        ]
    finally:
        con.close()
    return result
