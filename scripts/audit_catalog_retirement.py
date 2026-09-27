"""Read-only active/retired EvidenceQueryService diff for a prepared shadow."""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any

from company_wiki.source_catalog.evidence_query import (
    EvidenceQueryArchivedError,
    EvidenceQueryError,
    EvidenceQueryNotFoundError,
    EvidenceQueryService,
)


class AuditRefused(RuntimeError):
    pass


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _sample(old: sqlite3.Connection, status: str, limit: int) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    kinds: dict[str, int] = {}
    documents = old.execute(
        "SELECT document_id,document_kind FROM documents WHERE source_status=? "
        "ORDER BY document_kind,document_id",
        (status,),
    )
    for document_id, kind in documents:
        if kinds.get(kind, 0) >= 5:
            continue
        row = old.execute(
            "SELECT source_id,locator FROM evidence_spans WHERE document_id=? "
            "ORDER BY span_id LIMIT 1",
            (document_id,),
        ).fetchone()
        if row is None:
            continue
        result.append((document_id, row[0], row[1]))
        kinds[kind] = kinds.get(kind, 0) + 1
        if len(result) >= limit:
            break
    return result


def audit(prepared_path: Path) -> dict[str, Any]:
    prepared_path = prepared_path.resolve(strict=True)
    data = json.loads(prepared_path.read_text(encoding="utf-8"))
    if data.get("schema") != "catalog-retirement-prepared-v1":
        raise AuditRefused("prepared receipt schema is invalid")
    old_path = Path(data["production_database"])
    shadow_path = Path(data["shadow_path"])
    if not old_path.is_file() or not shadow_path.is_file():
        raise AuditRefused("old or shadow catalog is unavailable")
    if old_path.stat().st_size != data["source_bytes"] or _sha(old_path) != data["source_sha256"]:
        raise AuditRefused("old catalog differs from the prepared snapshot")
    source_stat = old_path.stat()
    if shadow_path.stat().st_size != data["shadow_bytes"] or _sha(shadow_path) != data["shadow_sha256"]:
        raise AuditRefused("shadow catalog differs from the prepared snapshot")
    wal = Path(str(old_path) + "-wal")
    if wal.exists() and wal.stat().st_size != 0:
        raise AuditRefused("production WAL gained data")
    with closing(sqlite3.connect(old_path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as old:
        old.execute("PRAGMA query_only=ON")
        active = _sample(old, "active", 100)
        retired = _sample(old, "retired", 100)
        other_non_active = (
            _sample(old, "upstream_rejected", 20)
            + _sample(old, "quarantined", 20)
        )
        mixed_source_ids = int(old.execute(
            "SELECT COUNT(*) FROM (SELECT primary_source_id FROM documents "
            "WHERE primary_source_id IS NOT NULL GROUP BY primary_source_id "
            "HAVING SUM(source_status='active')>0 "
            "AND SUM(source_status<>'active')>0)"
        ).fetchone()[0])
    if len(active) < 10 or len(retired) < 10:
        raise AuditRefused("insufficient active or retired evidence samples")
    old_service = EvidenceQueryService(old_path)
    shadow_service = EvidenceQueryService(shadow_path)
    for document_id, source_id, locator in active:
        expected = old_service.lookup(source_id=source_id, locator=locator).to_dict()
        actual = shadow_service.lookup(source_id=source_id, locator=locator).to_dict()
        if actual != expected:
            raise AuditRefused(f"active lookup differs: {document_id} {locator}")
        old_page = old_service.list_spans(document_id=document_id, limit=2).to_dict()
        new_page = shadow_service.list_spans(document_id=document_id, limit=2).to_dict()
        if old_page != new_page:
            raise AuditRefused(f"active list differs: {document_id}")
    non_active = retired + other_non_active
    with closing(sqlite3.connect(shadow_path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as shadow:
        collisions = {
            (source_id, locator) for _, source_id, locator in non_active
            if shadow.execute(
                "SELECT 1 FROM evidence_spans WHERE source_id=? AND locator=? LIMIT 1",
                (source_id, locator),
            ).fetchone() is not None
        }
    for document_id, source_id, locator in non_active:
        old_service.list_spans(document_id=document_id, limit=1)
        actions = [lambda: shadow_service.list_spans(document_id=document_id)]
        if (source_id, locator) not in collisions:
            old_service.lookup(source_id=source_id, locator=locator)
            actions.append(lambda: shadow_service.lookup(source_id=source_id, locator=locator))
        for action in actions:
            try:
                action()
            except EvidenceQueryArchivedError:
                pass
            else:
                raise AuditRefused(f"retired evidence did not fail closed: {document_id}")
    try:
        shadow_service.list_spans(
            source_id="urn:company-wiki:source:sha256:" + "0" * 64
        )
    except EvidenceQueryNotFoundError:
        pass
    else:
        raise AuditRefused("unknown source was not reported as not found")
    if (old_path.stat().st_size, old_path.stat().st_mtime_ns) != (
        source_stat.st_size, source_stat.st_mtime_ns
    ) or (wal.exists() and wal.stat().st_size):
        raise AuditRefused("old catalog changed during evidence audit")
    return {
        "schema": "catalog-retirement-evidence-audit-v1",
        "prepared_receipt": str(prepared_path),
        "active_checked": len(active),
        "retired_checked": len(retired),
        "other_non_active_checked": len(other_non_active),
        "retired_source_locator_collisions_with_active": len(collisions),
        "source_ids_shared_by_active_and_non_active_documents": mixed_source_ids,
        "old_source_sha256": data["source_sha256"],
        "shadow_sha256": data["shadow_sha256"],
        "status": "passed",
        "consumer_contracts_checked": False,
        "full_disk_restore_performed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared_receipt", type=Path)
    parser.add_argument("--output", type=Path, help="Write an immutable audit receipt")
    args = parser.parse_args(argv)
    try:
        result = audit(args.prepared_receipt)
        if args.output is not None:
            output = args.output.resolve()
            if output.exists() or output.with_name(output.name + ".partial").exists():
                raise AuditRefused("audit receipt path already exists")
            if output.parent != args.prepared_receipt.resolve(strict=True).parent:
                raise AuditRefused("audit receipt must stay beside prepared.json")
            pending = output.with_name(output.name + ".partial")
            with pending.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(pending, output)
        print(json.dumps(result, sort_keys=True))
    except (AuditRefused, EvidenceQueryError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
