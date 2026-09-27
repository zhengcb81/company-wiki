"""Compare the source-oriented read contracts against a prepared shadow DB.

The candidate is exposed under the expected filename through a temporary
same-volume hardlink. All catalog instances are closed before the link is
removed, so the 2.8 GiB candidate is never copied or written by this audit.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any

import yaml

from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver, SourceResolutionError
from company_wiki.source_catalog.reader import CatalogReaderUnavailable, ReadOnlyCatalogReader
from company_wiki.source_catalog.service import SourceCatalog


# Keep this inventory byte-for-byte aligned with cutover_source_catalog_db.py;
# cutover checks the exact key set before trusting the audit receipt.
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


class ConsumerAuditRefused(RuntimeError):
    pass


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise ConsumerAuditRefused("consumer audit receipt already exists")
    pending = path.with_name(path.name + ".partial")
    with pending.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(pending, path)


def audit(prepared_path: Path) -> dict[str, Any]:
    prepared_path = prepared_path.resolve(strict=True)
    data = json.loads(prepared_path.read_text(encoding="utf-8"))
    if data.get("schema") != "catalog-retirement-prepared-v1":
        raise ConsumerAuditRefused("unexpected prepared schema")
    root = Path(data["project_root"]).resolve(strict=True)
    run_dir = root / ".source_catalog" / "retirement" / data["run_id"]
    if prepared_path != run_dir / "prepared.json":
        raise ConsumerAuditRefused("prepared receipt is outside the run directory")
    old_path = root / ".source_catalog" / "catalog.sqlite3"
    shadow_path = run_dir / "catalog.active.sqlite3"
    if (Path(data["production_database"]) != old_path
            or Path(data["shadow_path"]) != shadow_path):
        raise ConsumerAuditRefused("database paths differ from prepared receipt")
    control = root / ".source_catalog" / "worker_control.json"
    if json.loads(control.read_text(encoding="utf-8")).get("desired_state") != "paused":
        raise ConsumerAuditRefused("Worker is not paused")
    wal = Path(str(old_path) + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise ConsumerAuditRefused("production WAL is nonempty")
    source_stat = old_path.stat()
    if (old_path.stat().st_size, _sha(old_path)) != (data["source_bytes"], data["source_sha256"]):
        raise ConsumerAuditRefused("old catalog changed")
    if (shadow_path.stat().st_size, _sha(shadow_path)) != (data["shadow_bytes"], data["shadow_sha256"]):
        raise ConsumerAuditRefused("shadow catalog changed")
    stockwiki_config = root.parent / "StockWiki" / "config" / "source_provider.yaml"
    provider = yaml.safe_load(stockwiki_config.read_text(encoding="utf-8"))
    company_provider = provider["providers"]["company-wiki"]
    if company_provider["enabled"] is not False:
        raise ConsumerAuditRefused("StockWiki company-wiki provider is enabled")
    forecast_client = root.parent / "revenue-forecast" / "scripts" / "filing_fetch_client.py"
    filing_fetch = root.parent / "filing-fetch" / "scripts" / "fetch_filing.py"
    if not forecast_client.is_file() or not filing_fetch.is_file():
        raise ConsumerAuditRefused("filing-fetch/revenue-forecast read-path files missing")

    probe = run_dir / "catalog.sqlite3"
    if probe.exists() or any(Path(str(probe) + suffix).exists() for suffix in ("-wal", "-shm")):
        raise ConsumerAuditRefused("candidate probe path is already occupied")
    config = load_catalog_config(root / "config" / "source_catalog.yaml", project_root=root)
    original = SourceCatalog(config)
    candidate = SourceCatalog(config)
    os.link(shadow_path, probe)
    query_cases = 0
    resolver_cases = 0
    resolver_statuses: dict[str, int] = {}
    try:
        candidate._reader = ReadOnlyCatalogReader(probe)
        kinds = [row[0] for row in original.reader.fetchall(
            "SELECT DISTINCT document_kind FROM documents WHERE source_status='active' "
            "ORDER BY document_kind"
        )]
        if not kinds:
            raise ConsumerAuditRefused("no active document kinds")
        cases = [(None, "active"), (None, "retired")]
        cases.extend((kind, "active") for kind in kinds[:4])
        for kind, status in cases:
            expected = original.query(document_kind=kind, source_status=status, limit=10)
            actual = candidate.query(document_kind=kind, source_status=status, limit=10)
            if expected != actual:
                raise ConsumerAuditRefused(f"query differed: {kind} {status}")
            query_cases += 1
        samples = original.reader.fetchall(
            "WITH ranked AS ("
            "SELECT e.name AS entity,d.document_kind,d.primary_source_id,"
            "ROW_NUMBER() OVER (PARTITION BY d.document_kind ORDER BY d.document_id) AS rn "
            "FROM documents d JOIN document_entities de ON de.document_id=d.document_id "
            "JOIN entities e ON e.entity_id=de.entity_id "
            "WHERE d.source_status='active' AND d.document_kind<>'other'),"
            "picks AS (SELECT entity,document_kind,primary_source_id FROM ranked "
            "WHERE rn<=3 ORDER BY document_kind,entity LIMIT 12) "
            "SELECT p.entity,p.document_kind,"
            "(SELECT a.fiscal_year FROM source_metadata_assertions a "
            "WHERE a.source_id=p.primary_source_id AND a.decision='verified' "
            "ORDER BY a.created_at DESC LIMIT 1) AS fiscal_year,"
            "(SELECT a.fiscal_period FROM source_metadata_assertions a "
            "WHERE a.source_id=p.primary_source_id AND a.decision='verified' "
            "ORDER BY a.created_at DESC LIMIT 1) AS fiscal_period FROM picks p"
        )
        if len(samples) < 5:
            raise ConsumerAuditRefused("insufficient active resolver samples")
        original_resolver = SourceResolver(original)
        candidate_resolver = SourceResolver(candidate)
        for row in samples:
            request = SourceRequest(
                entity=row["entity"], document_kind=row["document_kind"],
                as_of_date=date.today().isoformat(), fiscal_year=row["fiscal_year"],
                fiscal_period=row["fiscal_period"], allow_download=False,
            )
            expected = original_resolver.resolve(request).to_dict()
            actual = candidate_resolver.resolve(request).to_dict()
            if expected != actual:
                raise ConsumerAuditRefused(
                    f"resolver differed: {row['entity']} {row['document_kind']}"
                )
            resolver_cases += 1
            status = str(expected["status"])
            resolver_statuses[status] = resolver_statuses.get(status, 0) + 1
    finally:
        original.close()
        candidate.close()
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(probe) + suffix)
            if sidecar.exists():
                if suffix == "-wal" and sidecar.stat().st_size:
                    raise ConsumerAuditRefused("probe unexpectedly gained WAL data")
                sidecar.unlink()
        probe.unlink()
    if _sha(shadow_path) != data["shadow_sha256"]:
        raise ConsumerAuditRefused("candidate changed during read-only audit")
    if (old_path.stat().st_size, old_path.stat().st_mtime_ns) != (
        source_stat.st_size, source_stat.st_mtime_ns
    ) or (wal.exists() and wal.stat().st_size):
        raise ConsumerAuditRefused("source changed during consumer audit")
    if json.loads(control.read_text(encoding="utf-8")).get("desired_state") != "paused":
        raise ConsumerAuditRefused("Worker was resumed during consumer audit")
    result = {
        "schema": "catalog-retirement-consumer-audit-v1",
        "status": "passed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": data["source_sha256"],
        "shadow_sha256": data["shadow_sha256"],
        "contracts_checked": [
            "SourceCatalog.query active/retired by document kind",
            "SourceResolver.resolve no-download paired parity",
            "StockWiki company-wiki provider disabled configuration",
            "revenue-forecast to filing-fetch to company-wiki read path present",
        ],
        "query_cases": query_cases,
        "resolver_cases": resolver_cases,
        "resolver_statuses": resolver_statuses,
        "stockwiki_provider_enabled": False,
        "stockwiki_config_sha256": _sha(stockwiki_config),
        "forecast_client_sha256": _sha(forecast_client),
        "filing_fetch_sha256": _sha(filing_fetch),
        "company_wiki_contract_sha256": {
            relative: _sha(root / relative) for relative in CONTRACT_FILES
        },
        "downstream_live_business_run_performed": False,
        "full_disk_restore_performed": False,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prepared_receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(args.prepared_receipt)
        _write_new(args.prepared_receipt.resolve(strict=True).parent / "consumer_audit.json", result)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (ConsumerAuditRefused, CatalogReaderUnavailable, SourceResolutionError,
            OSError, sqlite3.Error, KeyError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
