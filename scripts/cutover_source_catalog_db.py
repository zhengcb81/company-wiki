"""Guarded catalog DB cutover, rollback, and exact-file retirement.

The commands operate only on one prepared run. A cutover intent is persisted
before the first rename so an interrupted run can be rolled back explicitly.
No command here deletes a directory or a raw document.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time
from typing import Any

from company_wiki.source_catalog.lock import CatalogOperationLock
from company_wiki.source_catalog.evidence_query import EvidenceQueryService


CONTRACT_FILES = (
    "config/source_catalog.yaml",
    "src/company_wiki/source_catalog/__init__.py",
    "src/company_wiki/source_catalog/artifact_dag.py",
    "src/company_wiki/source_catalog/cli.py",
    "src/company_wiki/source_catalog/config.py",
    "src/company_wiki/source_catalog/evidence_query.py",
    "src/company_wiki/source_catalog/llm_summarizer.py",
    "src/company_wiki/source_catalog/models.py",
    "src/company_wiki/source_catalog/normalizer.py",
    "src/company_wiki/source_catalog/processing_demand.py",
    "src/company_wiki/source_catalog/reader.py",
    "src/company_wiki/source_catalog/resolver.py",
    "src/company_wiki/source_catalog/section_extractor.py",
    "src/company_wiki/source_catalog/service.py",
    "src/company_wiki/source_catalog/store.py",
)


class CutoverRefused(RuntimeError):
    pass


def _hash(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


def _write_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise CutoverRefused(f"receipt already exists: {path.name}")
    pending = path.with_name(path.name + ".partial")
    with pending.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(pending, path)


def _rename(source: Path, target: Path) -> None:
    """Allow a short Windows scanner/reader handle delay, never overwrite."""
    if target.exists():
        raise CutoverRefused(f"rename target already exists: {target}")
    deadline = time.monotonic() + 10.0
    while True:
        try:
            os.rename(source, target)
            return
        except PermissionError:
            if time.monotonic() >= deadline or target.exists() or not source.exists():
                raise
            time.sleep(0.2)


def _read(path: Path, schema: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != schema:
        raise CutoverRefused(f"unexpected receipt schema: {path.name}")
    return data


def _paths(prepared_path: Path) -> tuple[dict[str, Any], Path, Path, Path, Path]:
    prepared_path = prepared_path.resolve(strict=True)
    data = _read(prepared_path, "catalog-retirement-prepared-v1")
    run_dir = prepared_path.parent
    project = Path(data["project_root"]).resolve(strict=True)
    catalog = project / ".source_catalog"
    run_id = data["run_id"]
    if (run_dir != catalog / "retirement" / run_id
            or prepared_path.name != "prepared.json"):
        raise CutoverRefused("prepared receipt is outside the exact run directory")
    production = catalog / "catalog.sqlite3"
    shadow = run_dir / "catalog.active.sqlite3"
    backup = run_dir / "catalog.full.sqlite3.zst"
    if (Path(data["production_database"]) != production
            or Path(data["shadow_path"]) != shadow
            or Path(data["backup_path"]) != backup):
        raise CutoverRefused("prepared file paths differ from the whitelist")
    if any(path.is_symlink() for path in (catalog, run_dir, production, shadow, backup)):
        raise CutoverRefused("symlink in cutover paths")
    return data, production, shadow, backup, run_dir


def _paused(production: Path) -> None:
    control = json.loads((production.parent / "worker_control.json").read_text(encoding="utf-8"))
    if control.get("desired_state") != "paused":
        raise CutoverRefused("Worker is not paused")
    wal = Path(str(production) + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise CutoverRefused("production WAL is nonempty")


def _check(path: Path, size: int, digest: str) -> None:
    if not path.is_file() or path.is_symlink() or _hash(path) != (size, digest):
        raise CutoverRefused(f"identity mismatch: {path}")


def _sidecars(production: Path, old: Path) -> list[tuple[Path, Path]]:
    items = []
    for suffix in ("-wal", "-shm"):
        source = Path(str(production) + suffix)
        target = Path(str(old) + suffix)
        if target.exists():
            raise CutoverRefused(f"retiring sidecar already exists: {target}")
        if source.exists():
            if suffix == "-wal" and source.stat().st_size:
                raise CutoverRefused("production WAL is nonempty")
            items.append((source, target))
    return items


def _check_audits(run_dir: Path, data: dict[str, Any]) -> None:
    evidence = _read(run_dir / "evidence_audit.json", "catalog-retirement-evidence-audit-v1")
    if (evidence.get("status") != "passed"
            or evidence.get("old_source_sha256") != data["source_sha256"]
            or evidence.get("shadow_sha256") != data["shadow_sha256"]):
        raise CutoverRefused("evidence audit does not match prepared source/shadow")
    consumer = _read(run_dir / "consumer_audit.json", "catalog-retirement-consumer-audit-v1")
    if (consumer.get("status") != "passed"
            or consumer.get("source_sha256") != data["source_sha256"]
            or consumer.get("shadow_sha256") != data["shadow_sha256"]
            or not consumer.get("contracts_checked")):
        raise CutoverRefused("consumer contract audit is missing or does not match")
    project = Path(data["project_root"])
    contract_hashes = consumer.get("company_wiki_contract_sha256")
    if not isinstance(contract_hashes, dict) or set(contract_hashes) != set(CONTRACT_FILES):
        raise CutoverRefused("company-wiki contract file set differs from audit")
    for relative in CONTRACT_FILES:
        path = project / relative
        if not path.is_file() or _hash(path)[1] != contract_hashes[relative]:
            raise CutoverRefused(f"company-wiki contract changed after audit: {relative}")
    dependencies = (
        (project.parent / "StockWiki" / "config" / "source_provider.yaml",
         "stockwiki_config_sha256"),
        (project.parent / "revenue-forecast" / "scripts" / "filing_fetch_client.py",
         "forecast_client_sha256"),
        (project.parent / "filing-fetch" / "scripts" / "fetch_filing.py",
         "filing_fetch_sha256"),
    )
    for path, field in dependencies:
        if not path.is_file() or _hash(path)[1] != consumer.get(field):
            raise CutoverRefused(f"consumer dependency changed after audit: {path.name}")


def cutover(prepared_path: Path) -> dict[str, Any]:
    data, production, shadow, backup, run_dir = _paths(prepared_path)
    old = production.with_name(production.name + ".retiring." + data["run_id"])
    with CatalogOperationLock(production.parent, operation="catalog-retirement-cutover"):
        if old.exists() or (run_dir / "cutover-intent.json").exists():
            raise CutoverRefused("cutover already attempted; inspect and recover")
        _paused(production)
        _check_audits(run_dir, data)
        _check(production, data["source_bytes"], data["source_sha256"])
        _check(shadow, data["shadow_bytes"], data["shadow_sha256"])
        _check(backup, data["backup_bytes"], data["backup_sha256"])
        sidecars = _sidecars(production, old)
        intent = {
            "schema": "catalog-retirement-cutover-intent-v1",
            "run_id": data["run_id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "production_database": str(production),
            "old_database": str(old),
            "shadow_database": str(shadow),
            "sidecars": [{"from": str(a), "to": str(b), "bytes": a.stat().st_size,
                          "sha256": _hash(a)[1]}
                         for a, b in sidecars],
            "source_sha256": data["source_sha256"],
            "shadow_sha256": data["shadow_sha256"],
        }
        _write_new(run_dir / "cutover-intent.json", intent)
        moved_sidecars: list[tuple[Path, Path]] = []
        old_moved = False
        new_moved = False
        try:
            for source, target in sidecars:
                _rename(source, target)
                moved_sidecars.append((source, target))
            _paused(production)
            _rename(production, old)
            old_moved = True
            _rename(shadow, production)
            new_moved = True
            _check(production, data["shadow_bytes"], data["shadow_sha256"])
            _check(old, data["source_bytes"], data["source_sha256"])
        except Exception:
            if new_moved and production.exists() and not shadow.exists():
                _rename(production, shadow)
            if old_moved and old.exists() and not production.exists():
                _rename(old, production)
            for source, target in reversed(moved_sidecars):
                if target.exists() and not source.exists():
                    _rename(target, source)
            raise
        result = {
            "schema": "catalog-retirement-cutover-v1",
            "run_id": data["run_id"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "production_database": str(production),
            "old_database": str(old),
            "production_sha256": data["shadow_sha256"],
            "old_sha256": data["source_sha256"],
            "worker_desired_state": "paused",
            "old_database_deleted": False,
        }
        _write_new(run_dir / "cutover.json", result)
        return result


def rollback(prepared_path: Path) -> dict[str, Any]:
    data, production, shadow, _, run_dir = _paths(prepared_path)
    old = production.with_name(production.name + ".retiring." + data["run_id"])
    intent = _read(run_dir / "cutover-intent.json", "catalog-retirement-cutover-intent-v1")
    if intent["old_database"] != str(old) or intent["production_database"] != str(production):
        raise CutoverRefused("cutover intent paths differ")
    if (run_dir / "delete-intent.json").exists() or (run_dir / "retired.json").exists():
        raise CutoverRefused("old database deletion has already begun")
    with CatalogOperationLock(production.parent, operation="catalog-retirement-rollback"):
        _paused(production)
        if old.exists():
            _check(old, data["source_bytes"], data["source_sha256"])
            if production.exists():
                _check(production, data["shadow_bytes"], data["shadow_sha256"])
                if shadow.exists():
                    raise CutoverRefused("both shadow paths exist; inspect manually")
                _rename(production, shadow)
            if not production.exists():
                _rename(old, production)
        else:
            _check(production, data["source_bytes"], data["source_sha256"])
        for item in reversed(intent["sidecars"]):
            source, target = Path(item["from"]), Path(item["to"])
            if (source, target) not in (
                (Path(str(production) + "-wal"), Path(str(old) + "-wal")),
                (Path(str(production) + "-shm"), Path(str(old) + "-shm")),
            ):
                raise CutoverRefused("sidecar paths differ from the exact whitelist")
            if target.exists() and not source.exists():
                _check(target, item["bytes"], item["sha256"])
                _rename(target, source)
        _check(production, data["source_bytes"], data["source_sha256"])
        result = {"schema": "catalog-retirement-rollback-v1",
                  "completed_at": datetime.now(timezone.utc).isoformat(),
                  "production_database": str(production), "source_sha256": data["source_sha256"]}
        _write_new(run_dir / "rollback.json", result)
        return result


def smoke(prepared_path: Path, ordinal: int) -> dict[str, Any]:
    if ordinal not in (1, 2):
        raise CutoverRefused("smoke ordinal must be 1 or 2")
    data, production, _, backup, run_dir = _paths(prepared_path)
    old = production.with_name(production.name + ".retiring." + data["run_id"])
    _read(run_dir / "cutover.json", "catalog-retirement-cutover-v1")
    _check_audits(run_dir, data)
    if (run_dir / "rollback.json").exists():
        raise CutoverRefused("run was rolled back")
    _paused(production)
    _check(production, data["shadow_bytes"], data["shadow_sha256"])
    _check(old, data["source_bytes"], data["source_sha256"])
    _check(backup, data["backup_bytes"], data["backup_sha256"])
    connection = sqlite3.connect(production.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise CutoverRefused("new production quick_check failed")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise CutoverRefused("new production foreign_key_check failed")
        active = connection.execute(
            "SELECT e.source_id,e.locator,e.document_id FROM evidence_spans e "
            "JOIN documents d ON d.document_id=e.document_id "
            "WHERE d.source_status='active' ORDER BY e.span_id LIMIT 1"
        ).fetchone()
        if active is None:
            raise CutoverRefused("new production has no active evidence")
        active_count = int(connection.execute(
            "SELECT COUNT(*) FROM evidence_spans"
        ).fetchone()[0])
        if active_count != data["tables"]["evidence_spans"]["rows"]:
            raise CutoverRefused("new production active span count differs")
    finally:
        connection.close()
    result = EvidenceQueryService(production).lookup(
        source_id=active[0], locator=active[1]
    )
    if result.document_id != active[2]:
        raise CutoverRefused("active evidence query returned another document")
    _paused(production)
    payload = {
        "schema": "catalog-retirement-smoke-v1",
        "run_id": data["run_id"],
        "ordinal": ordinal,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "production_sha256": data["shadow_sha256"],
        "old_sha256": data["source_sha256"],
        "backup_sha256": data["backup_sha256"],
        "active_span_count": active_count,
        "sample_document_id": active[2],
        "quick_check": "ok",
        "foreign_key_check": "ok",
        "worker_desired_state": "paused",
    }
    _write_new(run_dir / f"smoke_{ordinal}.json", payload)
    return payload


def retire(prepared_path: Path, *, minimum_interval_seconds: int = 600) -> dict[str, Any]:
    data, production, _, backup, run_dir = _paths(prepared_path)
    old = production.with_name(production.name + ".retiring." + data["run_id"])
    _read(run_dir / "cutover.json", "catalog-retirement-cutover-v1")
    _check_audits(run_dir, data)
    first = _read(run_dir / "smoke_1.json", "catalog-retirement-smoke-v1")
    second = _read(run_dir / "smoke_2.json", "catalog-retirement-smoke-v1")
    if (run_dir / "rollback.json").exists() or (run_dir / "retired.json").exists():
        raise CutoverRefused("run already rolled back or retired")
    if (first.get("status"), first.get("ordinal"), second.get("status"), second.get("ordinal")) != (
        "passed", 1, "passed", 2
    ):
        raise CutoverRefused("two passed smoke receipts are required")
    started = datetime.fromisoformat(first["completed_at"])
    ended = datetime.fromisoformat(second["completed_at"])
    if (ended - started).total_seconds() < minimum_interval_seconds:
        raise CutoverRefused("smoke observations are too close together")
    for item in (first, second):
        if (item.get("production_sha256") != data["shadow_sha256"]
                or item.get("old_sha256") != data["source_sha256"]
                or item.get("backup_sha256") != data["backup_sha256"]):
            raise CutoverRefused("smoke identity differs from prepared receipt")
    with CatalogOperationLock(production.parent, operation="catalog-retirement-retire"):
        _paused(production)
        _check(production, data["shadow_bytes"], data["shadow_sha256"])
        _check(backup, data["backup_bytes"], data["backup_sha256"])
        cutover_intent = _read(run_dir / "cutover-intent.json", "catalog-retirement-cutover-intent-v1")
        recorded_sidecars = {Path(item["to"]) for item in cutover_intent["sidecars"]}
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(old) + suffix)
            if sidecar.exists() and sidecar not in recorded_sidecars:
                raise CutoverRefused("unrecorded old sidecar appeared")
        deletion_path = run_dir / "delete-intent.json"
        if deletion_path.exists():
            intent = _read(deletion_path, "catalog-retirement-delete-intent-v1")
            if (intent.get("old_database") != str(old)
                    or intent.get("old_sha256") != data["source_sha256"]
                    or intent.get("backup_sha256") != data["backup_sha256"]):
                raise CutoverRefused("delete intent identity differs")
        else:
            _check(old, data["source_bytes"], data["source_sha256"])
            intent = {
                "schema": "catalog-retirement-delete-intent-v1",
                "run_id": data["run_id"],
                "old_database": str(old),
                "old_bytes": data["source_bytes"],
                "old_sha256": data["source_sha256"],
                "backup_path": str(backup),
                "backup_sha256": data["backup_sha256"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _write_new(deletion_path, intent)
        _paused(production)
        free_before = shutil.disk_usage(production.parent).free
        if old.exists():
            _check(old, data["source_bytes"], data["source_sha256"])
            old.unlink()
        sidecars_deleted: list[str] = []
        for item in cutover_intent["sidecars"]:
            sidecar = Path(item["to"])
            if sidecar.exists():
                if sidecar not in (Path(str(old) + "-wal"), Path(str(old) + "-shm")):
                    raise CutoverRefused("old sidecar is outside the exact whitelist")
                _check(sidecar, item["bytes"], item["sha256"])
                sidecar.unlink()
                sidecars_deleted.append(str(sidecar))
        result = {
            "schema": "catalog-retirement-retired-v1",
            "run_id": data["run_id"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "deleted_database": str(old),
            "deleted_bytes": data["source_bytes"],
            "deleted_sidecars": sidecars_deleted,
            "old_sha256": data["source_sha256"],
            "backup_path": str(backup),
            "backup_sha256": data["backup_sha256"],
            "production_sha256": data["shadow_sha256"],
            "full_disk_restore_performed": False,
            "free_bytes_before": free_before,
            "free_bytes_after": shutil.disk_usage(production.parent).free,
        }
        _write_new(run_dir / "retired.json", result)
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("cutover", "rollback", "smoke-1", "smoke-2", "retire"))
    parser.add_argument("prepared_receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        actions = {"cutover": cutover, "rollback": rollback,
                   "smoke-1": lambda path: smoke(path, 1),
                   "smoke-2": lambda path: smoke(path, 2),
                   "retire": retire}
        result = actions[args.action](args.prepared_receipt)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (CutoverRefused, OSError, sqlite3.Error, KeyError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
