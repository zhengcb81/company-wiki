"""Prepare config-only isolation for native RF -> FF -> CWP entry points.

This script never starts a subprocess, registers/scans sources, downloads, reads
credentials, or calls a model. Run it with the real editable CWP Python. Original
bytes remain mounted through storage configuration; only owned runtime files and
existing public security-master snapshots are written under the fixed R1 root.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys

import yaml

from company_wiki.source_catalog.acquisition_config import load_acquisition_config
from company_wiki.source_catalog.config import load_catalog_config


REPO = Path(__file__).resolve().parents[4]
OWNED_BASE = REPO / ".planning/shared-reading-production/r1-holdout-20261021"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def inventory(root: Path) -> list[dict]:
    if not root.exists():
        return []
    return [{"path": path.relative_to(root).as_posix(),
             "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())}
            for path in sorted(root.rglob("*")) if path.is_file()]


def _bounded_bytes(path: Path, limit: int = 1048576) -> bytes:
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"configuration exceeds preparation limit: {path.name}")
    return raw


def _location(value: str, *, config: Path, skill_root: Path) -> str:
    # Location metadata only. This function never opens the resulting key path.
    import os

    tokens = {"SKILL_ROOT": str(skill_root),
              "USER_PROFILE": os.environ.get("USERPROFILE", str(Path.home()))}

    def replace(match):
        if match.group(1) not in tokens:
            raise ValueError("unsupported FF location token")
        return tokens[match.group(1)]

    expanded = re.sub(r"\$\{([^}]+)\}", replace, value)
    if "${" in expanded:
        raise ValueError("incomplete FF location token")
    path = Path(expanded).expanduser()
    return str((path if path.is_absolute() else config.parent / path).resolve())


def prepare(args: argparse.Namespace) -> dict:
    date.fromisoformat(args.as_of_date)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}", args.entity_key):
        raise ValueError("entity-key must be a simple logical identity")
    company_key = args.entity_key.replace(":", "-")
    wiki = (OWNED_BASE / company_key / "wiki").resolve()
    wiki.relative_to(OWNED_BASE.resolve())
    if (wiki / "AUTO.sqlite").exists() or (wiki / ".source_catalog/catalog.sqlite3").exists():
        raise ValueError("runtime already started; resume its existing receipt instead of preparing again")
    production_config = REPO / "config/source_catalog.yaml"
    acquisition_config = REPO / "config/source_acquisition.yaml"
    source = load_catalog_config(production_config, project_root=REPO)
    acquisition = load_acquisition_config(acquisition_config, project_root=REPO)
    raw_source = yaml.safe_load(_bounded_bytes(production_config))
    roots = []
    for original in raw_source["roots"]:
        row = dict(original)
        spec = next(root for root in source.roots if root.root_id == row["root_id"])
        row["path"] = str(spec.path)
        row["read_only"] = True
        if spec.kind == "company_raw":
            # CanonicalSourceWriter requires EXACTLY ONE company_raw. Adapter
            # discovery and reuse are independent of the storage-root kind.
            row.update(kind="directory", adapter_id="company_raw_v1",
                       reusable_for_filing=True)
        roots.append(row)
    if any(row["root_id"] == "holdout_raw" for row in roots):
        raise ValueError("holdout_raw root ID is already in production config")
    roots.insert(0, {"root_id": "holdout_raw", "kind": "company_raw",
                     "path": str(wiki / "companies"), "priority": 1,
                     "adapter_id": "company_raw_v1", "read_only": False})
    catalog = {"schema_version": "1.0", "catalog_dir": str(wiki / ".source_catalog"),
               "reusable_root_kinds": list(source.reusable_root_kinds), "roots": roots}

    adapters = {}
    for market in ("cn", "hk", "us"):
        spec = getattr(acquisition, market)
        command = list(spec.command)
        # All code/executable paths have already been expanded by the owner's
        # real loader against production. Only mutable provider state is moved.
        if "--provider-state-root" in command:
            index = command.index("--provider-state-root") + 1
            if index == len(command):
                raise ValueError("provider-state-root has no argument")
            command[index] = str(wiki / ".source_catalog/provider-state/dayu")
        adapters[market] = {
            "name": spec.name, "version": spec.version, "interface": spec.interface,
            "supports_acquisition_budget": spec.supports_acquisition_budget,
            "project_root": str(spec.project_root),
            "config_root": str(spec.config_root) if spec.config_root is not None else None,
            "command": command,
        }
    acquisition_payload = {"schema_version": acquisition.schema_version,
                           "staging_root": str(wiki / ".source_catalog/staging"),
                           "timeout_seconds": acquisition.timeout_seconds,
                           "adapters": adapters}
    ff_root = args.filing_fetch_root.resolve(strict=True)
    rf_root = args.revenue_forecast_root.resolve(strict=True)
    if not (ff_root / "scripts/fetch_filing.py").is_file():
        raise ValueError("filing-fetch code root is unavailable")
    if not (rf_root / "scripts/source_preparation.py").is_file():
        raise ValueError("RF source preparation is unavailable")
    ff_config = ff_root / "config/company_wiki.json"
    selected = json.loads(_bounded_bytes(ff_config))
    connection = {"schema_version": "1.0", "company_wiki_root": str(wiki)}
    for field in ("earnings_transcripts_tool", "fmp_api_key_file"):
        if field in selected:
            connection[field] = _location(selected[field], config=ff_config, skill_root=ff_root)
    request = {"schema_version": "2.0", "company_query": args.company_query,
               "market": args.market, "document_kind": args.document_kind,
               "as_of_date": args.as_of_date, "filing_intent": "reuse_only"}
    if args.fiscal_year is None:
        request["mode"] = "latest_as_of"
    else:
        request.update(mode="exact", fiscal_year=args.fiscal_year)

    target_config = wiki / "config/source_catalog.yaml"
    worker_config = REPO / "config/source_catalog_worker.yaml"
    files = {
        target_config: json_bytes(catalog),
        wiki / "config/source_acquisition.yaml": json_bytes(acquisition_payload),
        wiki / "config/source_catalog_worker.yaml": _bounded_bytes(worker_config),
        wiki / "company_wiki.json": json_bytes(connection),
        wiki / "rf_filing_fetch.json": json_bytes({"schema_version": "1.0", "filing_fetch_root": str(ff_root)}),
        wiki / "requests/reuse.json": json_bytes(request),
    }
    master = source.catalog_dir / "security_master" / (args.market.lower() + ".json")
    files[wiki / ".source_catalog/security_master" / master.name] = _bounded_bytes(master, 16777216)
    before = inventory(wiki)
    # Refuse replacement of another run's differing preparation. No generic
    # recursive copying, raw copying, code links, or production writes exist.
    for path, raw in files.items():
        path.resolve().relative_to(wiki)
        if path.exists() and path.read_bytes() != raw:
            raise ValueError(f"owned file already differs: {path.relative_to(wiki)}")
    for path, raw in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(raw)
    (wiki / "companies").mkdir(exist_ok=True)
    # Native schema validation only: no SourceCatalog construction, DB, scan,
    # adapter process, credential lookup, or model creation.
    prepared = load_catalog_config(target_config, project_root=wiki)
    prepared_acquisition = load_acquisition_config(wiki / "config/source_acquisition.yaml", project_root=wiki)
    if len([root for root in prepared.roots if root.kind == "company_raw"]) != 1:
        raise ValueError("prepared catalog has ambiguous canonical writer")
    if prepared.database_path.is_relative_to(wiki) is not True:
        raise ValueError("prepared database escaped owned root")
    receipt = {
        "schema_version": "r1-isolated-runtime-preparation/1",
        "entity_key": args.entity_key, "company_query": args.company_query,
        "market": args.market, "as_of_date": args.as_of_date,
        "wiki_root": str(wiki), "python": sys.executable,
        "code_distribution": "existing editable CWP; subprocess -m; no code copy or symlink",
        "catalog_config": str(target_config), "database": str(prepared.database_path),
        "derived_dir": str(prepared.derived_dir), "export_dir": str(prepared.export_dir),
        "automation_db": str(wiki / "AUTO.sqlite"), "work_dir": str(wiki / "work"),
        "staging_root": str(prepared_acquisition.staging_root),
        "provider_state_root": str(wiki / ".source_catalog/provider-state/dayu"),
        "production_config_sha256": {str(path): digest(_bounded_bytes(path)) for path in
                                     (production_config, acquisition_config, worker_config, ff_config)},
        "security_snapshot": {"source": str(master), "sha256": digest(files[wiki / ".source_catalog/security_master" / master.name])},
        "native_source_preparation_reuse_argv": [sys.executable, "-B", "-X", "utf8",
            str(rf_root / "scripts/source_preparation.py"), "--request-file", str(wiki / "requests/reuse.json"),
            "--result-envelope", "--filing-fetch-root", str(ff_root), "--company-wiki-config", str(wiki / "company_wiki.json"),
            "--company-wiki-catalog-config", str(target_config), "--source-reader-receipt-version", "2.2"],
        "company_total_limits": {"tokens": 100000, "usd": "1.00", "scope": "all company attempts, not each document"},
        "budget_owner": "existing mother_totals plus native AUTO reservations; no new budget DB",
        "initial_owned_files_before_preparation": before,
        "prepared_baseline_files": inventory(wiki),
        "performed": {"config_schema_validation": True, "source_registration": False,
                      "raw_copies": 0, "downloads": 0, "model_calls": 0, "credential_reads": 0},
    }
    receipt_path = wiki / "preparation_receipt.json"
    if receipt_path.exists():
        # Keep first baseline immutable; a repeat emits its original receipt.
        return json.loads(_bounded_bytes(receipt_path))
    receipt_path.write_bytes(json_bytes(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entity-key", required=True)
    parser.add_argument("--company-query", required=True)
    parser.add_argument("--market", required=True, choices=("CN", "HK", "US"))
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--fiscal-year", type=int)
    parser.add_argument("--document-kind", default="annual_report")
    parser.add_argument("--filing-fetch-root", type=Path, default=REPO.parent / "filing-fetch")
    parser.add_argument("--revenue-forecast-root", type=Path, default=REPO.parent / "revenue-forecast")
    receipt = prepare(parser.parse_args())
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
