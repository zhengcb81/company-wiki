"""Aggregate, explicit-scope pruning without materializing all legacy spans."""
from __future__ import annotations

from contextlib import closing, nullcontext
from datetime import datetime
from pathlib import Path
import sqlite3

from company_wiki.source_catalog.lock import CatalogOperationLock, CatalogOperationLockedError
from legacy_storage.core import (
    db_numbers, empty_report, integrity_probe, read_connection, source_facts,
)

SELECTION_SCHEMA = "cwp-span-selection/1"


def _parse_selection(selection: dict) -> tuple[dict | None, str | None, str | None]:
    if not isinstance(selection, dict):
        return None, "bad_selection", "selection must be an object"
    parser = selection.get("parser_name")
    if not isinstance(parser, str) or not parser.strip():
        return None, "empty_selection", "parser_name must be explicit"
    if selection.get("schema_version") != SELECTION_SCHEMA:
        return None, "bad_selection", "unsupported selection schema"
    version = selection.get("parser_version")
    if version is not None and (not isinstance(version, str) or not version.strip()):
        return None, "bad_selection", "parser_version must be non-empty text or absent"
    parsed = {"parser_name": parser, "parser_version": version}
    for key in ("source_ids", "document_ids"):
        values = selection.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            return None, "bad_selection", f"{key} must be a list of non-empty IDs"
        parsed[key] = sorted(set(values))
    return parsed, None, None


def _where(selection: dict) -> tuple[str, list]:
    clauses, params = ["parser_name=?"], [selection["parser_name"]]
    if selection["parser_version"] is not None:
        clauses.append("parser_version=?")
        params.append(selection["parser_version"])
    for key, column in (("source_ids", "source_id"), ("document_ids", "document_id")):
        if selection[key]:
            clauses.append(f"{column} IN ({','.join('?' for _ in selection[key])})")
            params.extend(selection[key])
    return " AND ".join(clauses), params


def _requested_keep(connection, refs) -> set[tuple[str, str]]:
    pairs = set()
    for ref in refs:
        if not isinstance(ref, dict):
            raise LookupError("keep_ref_invalid")
        pair = (ref.get("source_id"), ref.get("locator"))
        if any(not isinstance(value, str) or not value for value in pair):
            raise LookupError("keep_ref_invalid")
        if pair not in pairs and connection.execute(
            "SELECT 1 FROM evidence_spans WHERE source_id=? AND locator=?", pair,
        ).fetchone() is None:
            raise LookupError("keep_ref_unknown")
        pairs.add(pair)
    return pairs


def run_prune_spans(config, selection: dict, *, keep_refs=None,
                    now: datetime | None = None, dry_run: bool = True) -> dict:
    """One SQL delete, aggregate receipt, memory proportional only to keep refs."""
    del now
    report = empty_report("prune-spans")
    report.update(dry_run=dry_run, deleted=0, already_absent=0)
    parsed, error, note = _parse_selection(selection)
    if parsed is None:
        report.update(status="refused", error_code=error, resume_notes=[note])
        return report
    database = Path(config.database_path)
    if not database.is_file():
        report.update(status="refused", error_code="database_missing")
        return report
    where, params = _where(parsed)
    lock = nullcontext() if dry_run else CatalogOperationLock(Path(config.catalog_dir), operation="prune-spans")
    before = None
    committed = False
    try:
        with lock:
            context = read_connection(database) if dry_run else closing(sqlite3.connect(database, timeout=5.0))
            with context as connection:
                if not dry_run:
                    connection.execute("PRAGMA foreign_keys=ON")
                    connection.execute("BEGIN IMMEDIATE")
                else:
                    connection.execute("BEGIN")
                before = db_numbers(database, connection=connection)
                report["source_facts_before"] = source_facts(database, connection=connection)
                keep = _requested_keep(connection, keep_refs if keep_refs is not None else ())
                total = connection.execute(f"SELECT COUNT(*) FROM evidence_spans WHERE {where}", params).fetchone()[0]
                kept = sum(connection.execute(
                    f"SELECT COUNT(*) FROM evidence_spans WHERE ({where}) AND source_id=? AND locator=?",
                    [*params, *pair],
                ).fetchone()[0] for pair in keep)
                report["selection"] = {**parsed, "candidate_pairs": total - kept,
                                       "kept_pairs": kept, "keep_ref_count": len(keep)}
                if not dry_run:
                    connection.execute("CREATE TEMP TABLE keep_spans (source_id TEXT, locator TEXT, PRIMARY KEY(source_id,locator)) WITHOUT ROWID")
                    connection.executemany("INSERT INTO keep_spans VALUES (?,?)", keep)
                    cursor = connection.execute(
                        f"DELETE FROM evidence_spans WHERE ({where}) AND NOT EXISTS "
                        "(SELECT 1 FROM keep_spans k WHERE k.source_id=evidence_spans.source_id AND k.locator=evidence_spans.locator)", params,
                    )
                    report["deleted"] = cursor.rowcount
                verified = all(connection.execute(
                    "SELECT 1 FROM evidence_spans WHERE source_id=? AND locator=?", pair,
                ).fetchone() is not None for pair in keep)
                report["selection"]["keep_verified"] = verified
                integrity = integrity_probe(connection)
                report.update(integrity)
                after_facts = source_facts(database, connection=connection)
                if not verified or after_facts != report["source_facts_before"] or integrity["foreign_key_check"] or integrity["integrity_check"] != "ok":
                    connection.rollback()
                    report.update(status="failed", error_code="protected_facts_or_integrity_changed", deleted=0)
                elif not dry_run:
                    connection.commit()
                    committed = True
                else:
                    connection.rollback()
            report["source_facts_after"] = source_facts(database)
            after = db_numbers(database)
            _measure(report, before, after)
            if report["source_facts_after"] != report["source_facts_before"]:
                report.update(status="failed", error_code="protected_facts_changed")
    except LookupError as exc:
        report.update(status="refused", error_code=str(exc), resume_notes=[str(exc)], deleted=0)
    except CatalogOperationLockedError:
        report.update(status="refused", error_code="catalog_busy")
    except (OSError, sqlite3.Error) as exc:
        report.update(status="failed", error_code=f"database_error:{type(exc).__name__}",
                      resume_notes=[str(exc)[:500]])
        if not committed:
            report["deleted"] = 0
    if before is not None and not report["database_bytes_before"]:
        _measure(report, before, before)
    return report


def _measure(report, before, after):
    for suffix, values in (("before", before), ("after", after)):
        report[f"database_bytes_{suffix}"] = values["file_bytes"]
        report[f"files_bytes_{suffix}"] = values["file_bytes"]
        report[f"page_count_{suffix}"] = values["page_count"]
        report[f"freelist_{suffix}"] = values["freelist"]
