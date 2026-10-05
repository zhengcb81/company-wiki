"""prune-spans: explicit-scope pruning of legacy full-volume evidence_spans."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from legacy_storage.core import (
    REPORT_SCHEMA,
    db_numbers,
    read_connection,
    source_facts,
    utc_now_text,
)
from legacy_storage.retirement import integrity_probe_write, integrity_status

SELECTION_SCHEMA = "cwp-span-selection/1"


def _parse_selection(selection: dict) -> tuple[dict | None, str | None, str | None]:
    parser_name = selection.get("parser_name")
    if not isinstance(parser_name, str) or not parser_name.strip():
        return (
            None,
            "empty_selection",
            "selection.parser_name must be a non-empty string",
        )
    parser_version = selection.get("parser_version")
    if parser_version is not None and not isinstance(parser_version, str):
        return None, "bad_selection", "selection.parser_version must be a string"
    source_ids = selection.get("source_ids") or []
    document_ids = selection.get("document_ids") or []
    if not isinstance(source_ids, list) or not isinstance(document_ids, list):
        return None, "bad_selection", "source_ids/document_ids must be lists"
    return (
        {
            "parser_name": parser_name,
            "parser_version": parser_version,
            "source_ids": [str(v) for v in source_ids],
            "document_ids": [str(v) for v in document_ids],
        },
        None,
        None,
    )


def _where(selection: dict) -> tuple[str, list]:
    clauses = ["parser_name = ?"]
    params: list = [selection["parser_name"]]
    if selection["parser_version"] is not None:
        clauses.append("parser_version = ?")
        params.append(selection["parser_version"])
    if selection["source_ids"]:
        clauses.append(
            "source_id IN (%s)" % ",".join("?" * len(selection["source_ids"]))
        )
        params.extend(selection["source_ids"])
    if selection["document_ids"]:
        clauses.append(
            "document_id IN (%s)" % ",".join("?" * len(selection["document_ids"]))
        )
        params.extend(selection["document_ids"])
    return " AND ".join(clauses), params


def _keep_pairs(database_path: Path, keep_refs: list[dict]) -> set[tuple[str, str]]:
    with read_connection(database_path) as conn:
        pairs = {
            (row[0], row[1])
            for row in conn.execute("SELECT source_id, locator FROM evidence_spans")
        }
    requested = set()
    missing = []
    for ref in keep_refs:
        pair = (ref.get("source_id"), ref.get("locator"))
        if pair not in pairs:
            missing.append(pair)
        requested.add(pair)
    if missing:
        raise LookupError(f"keep_ref_unknown:{missing[0]!r}")
    return requested


def run_prune_spans(
    config,
    selection: dict,
    *,
    keep_refs: list[dict] | None = None,
    now: datetime | None = None,
    dry_run: bool = True,
) -> dict:
    """Prune evidence_spans for an EXPLICIT legacy parser/source scope,
    protecting the keep-refs and everyParser outside the selection."""
    database_path = Path(config.database_path)
    created_at = utc_now_text(now)
    parsed, error_code, error_note = _parse_selection(selection)
    if parsed is None:
        report = _base("prune-spans", dry_run=dry_run)
        report["status"] = "refused"
        report["error_code"] = error_code
        report["resume_notes"] = [error_note]
        _ = created_at
        return report

    facts_before = source_facts(database_path)
    db_before = db_numbers(database_path)
    try:
        keep_pairs = _keep_pairs(database_path, keep_refs or [])
    except LookupError as exc:
        report = _base("prune-spans", dry_run=dry_run)
        report["status"] = "refused"
        report["error_code"] = "keep_ref_unknown"
        report["resume_notes"] = [str(exc)]
        report["source_facts_before"] = facts_before
        report["database_bytes_before"] = db_before["file_bytes"]
        _ = created_at
        return report
    where, params = _where(parsed)
    notes: list[str] = []

    import sqlite3

    conn = sqlite3.connect(database_path, timeout=30.0)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        candidates = conn.execute(
            f"SELECT source_id, locator FROM evidence_spans WHERE {where}", params
        ).fetchall()
        protectable = keep_pairs
        doomed = [pair for pair in candidates if pair not in protectable]
        if dry_run:
            conn.rollback()
            deleted = 0
            already_absent = 0
        else:
            conn.executemany(
                "DELETE FROM evidence_spans WHERE source_id=? AND locator=?",
                doomed,
            )
            deleted = len(doomed)
            already_absent = len(candidates) - deleted  # protected keep rows stayed
            rolled = False
            conn.execute("COMMIT")
            rolled = True
            _ = rolled
    except LookupError as exc:
        conn.rollback()
        report = _base("prune-spans", dry_run=dry_run)
        report["status"] = "refused"
        report["error_code"] = "keep_ref_unknown"
        report["resume_notes"] = [str(exc)]
        report["source_facts_before"] = facts_before
        report["database_bytes_before"] = db_before["file_bytes"]
        return report
    except sqlite3.Error as exc:
        conn.rollback()
        report = _base("prune-spans", dry_run=dry_run)
        report["status"] = "failed"
        report["error_code"] = f"database_error:{type(exc).__name__}"
        report["resume_notes"] = [f"{type(exc).__name__}: {exc}"]
        report["source_facts_before"] = facts_before
        report["database_bytes_before"] = db_before["file_bytes"]
        return report
    finally:
        conn.close()

    if dry_run:
        report = _base("prune-spans", dry_run=True)
        report["status"] = "succeeded"
        report["selection"] = {
            **parsed,
            "candidate_pairs": len(doomed),
            "kept_pairs": len(protectable),
        }
        report["source_facts_before"] = facts_before
        report["source_facts_after"] = facts_before
        report["database_bytes_before"] = db_before["file_bytes"]
        report["database_bytes_after"] = db_before["file_bytes"]
        report["page_count_before"] = db_before["page_count"]
        report["page_count_after"] = db_before["page_count"]
        report["freelist_before"] = db_before["freelist"]
        report["freelist_after"] = db_before["freelist"]
        report["candidates"] = [{"source_id": src, "locator": loc} for src, loc in doomed]
        report["deleted"] = 0
        report["already_absent"] = 0
        report["resume_notes"] = notes
        return report

    facts_after = source_facts(database_path)
    db_after = db_numbers(database_path)
    kept_rows = _verify_keep(database_path, keep_pairs)
    report = _base("prune-spans", dry_run=False)
    report.update(
        {
            "status": "succeeded",
            "error_code": None,
            "selection": {
                **parsed,
                "candidate_pairs": len(doomed),
                "kept_pairs": len(keep_pairs),
                "keep_verified": kept_rows,
            },
            "source_facts_before": facts_before,
            "source_facts_after": facts_after,
            "protected_objects_before": {},
            "protected_objects_after": {},
            "candidates": [],
            "deleted": deleted,
            "already_absent": already_absent,
            "files_bytes_before": db_before["file_bytes"],
            "files_bytes_after": db_after["file_bytes"],
            "database_bytes_before": db_before["file_bytes"],
            "database_bytes_after": db_after["file_bytes"],
            "page_count_before": db_before["page_count"],
            "page_count_after": db_after["page_count"],
            "freelist_before": db_before["freelist"],
            "freelist_after": db_after["freelist"],
            "foreign_key_check": integrity_probe_write(database_path),
            "integrity_check": integrity_status(database_path),
            "resume_notes": notes,
        }
    )
    return report


def _verify_keep(database_path: Path, keep_pairs: set) -> bool:
    from company_wiki.source_catalog.evidence_query import EvidenceQueryService

    service = EvidenceQueryService(Path(database_path))
    for source_id, locator in sorted(keep_pairs):
        service.lookup(source_id=source_id, locator=locator)
    return True


def _base(operation: str, *, dry_run: bool) -> dict:
    return {
        "schema_version": REPORT_SCHEMA,
        "operation": operation,
        "dry_run": dry_run,
        "status": "succeeded",
        "error_code": None,
        "selection": {},
        "source_facts_before": {},
        "source_facts_after": {},
        "protected_objects_before": {},
        "protected_objects_after": {},
        "candidates": [],
        "deleted": 0,
        "already_absent": 0,
        "files_bytes_before": 0,
        "files_bytes_after": 0,
        "database_bytes_before": 0,
        "database_bytes_after": 0,
        "page_count_before": 0,
        "page_count_after": 0,
        "freelist_before": 0,
        "freelist_after": 0,
        "foreign_key_check": [],
        "integrity_check": "ok",
        "resume_notes": [],
    }
