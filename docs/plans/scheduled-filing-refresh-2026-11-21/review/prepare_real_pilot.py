"""Prepare a three-market acceptance catalog using only public owner commands.

The output root must be new. The fixture copies originals and their sidecars
without changing source facts. It does not run providers or install a task.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml


SAMPLES = (("CN", "300750"), ("HK", "00700"), ("US", "MSFT"))
LOCAL_ORIGINALS = (
    "腾讯/raw/financial_reports/annual/腾讯：2025年年度报告.pdf",
    "Microsoft/raw/transcripts/MSFT_Q4_2026_earnings_call.txt",
)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def command(arguments: list[str], *, cwd: Path | None = None) -> dict:
    result = subprocess.run(arguments, cwd=cwd, capture_output=True, encoding="utf-8",
                            timeout=120, check=True)
    return json.loads(result.stdout)


def prepare(args: argparse.Namespace) -> dict:
    root = args.scratch.resolve()
    source = args.company_wiki.resolve(strict=True)
    candidate = args.cwp_runtime.resolve(strict=True)
    stockwiki = args.identity_workspace.resolve(strict=True)
    identity_cli = source.parent / "StockWiki" / "dashboard_identity_bridge_cli.py"
    identity_base = [sys.executable, "-B", "-X", "utf8", str(identity_cli)]
    members = []
    receipts = {}
    for market, ticker in SAMPLES:
        search = command([*identity_base, "search", "--root", str(stockwiki), "--query", ticker])
        match, = search["matches"]
        identity = command([*identity_base, "resolve", "--root", str(stockwiki),
                            "--entity-id", match["entity_id"]])
        member, = [row for row in identity["entity"]["listings"] if (
            row["market"], row["ticker"], row["listing_status"]
        ) == (market, ticker, "active")]
        members.append({key: member[key] for key in (
            "entity_id", "listing_id", "market", "ticker", "exchange_raw",
        )})
        receipts[market] = identity["lookup_receipt_sha256"]

    root.mkdir(parents=True, exist_ok=False)
    config_dir = root / "config"
    config_dir.mkdir()
    catalog_dir = root / ".source_catalog"
    shutil.copytree(source / ".source_catalog/security_master", catalog_dir / "security_master",
                    ignore=shutil.ignore_patterns("*.lock", "*.tmp"))
    seeds = {}
    for relative in LOCAL_ORIGINALS:
        src = source / "companies" / relative
        dst = root / "companies" / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        shutil.copy2(Path(str(src) + ".source.json"), Path(str(dst) + ".source.json"))
        with src.open("rb") as original:
            seeds[relative] = hashlib.file_digest(original, "sha256").hexdigest()

    catalog_config = config_dir / "source_catalog.yaml"
    write_json(catalog_config, {
        "schema_version": "1.0", "catalog_dir": str(catalog_dir),
        "roots": [{"root_id": "company", "kind": "company_raw", "read_only": False,
                   "path": str(root / "companies"), "priority": 10}],
    })
    shutil.copy2(source / "config/source_catalog_worker.yaml", config_dir)
    acquisition = yaml.safe_load((source / "config/source_acquisition.yaml").read_text(encoding="utf-8"))
    acquisition["staging_root"] = str(catalog_dir / "staging")
    for adapter in acquisition["adapters"].values():
        adapter["project_root"] = adapter["project_root"].replace("${PROJECT_ROOT}", source.as_posix())
        command_line = adapter["command"]
        for index, argument in enumerate(command_line):
            if argument == "${PROJECT_ROOT}/tools/dayu_sdk_bridge.py":
                command_line[index] = str(candidate / "tools/dayu_sdk_bridge.py")
            elif argument.startswith("${PROJECT_ROOT}/../"):
                command_line[index] = argument.replace("${PROJECT_ROOT}", source.as_posix(), 1)
        if "--provider-state-root" in command_line:
            command_line[command_line.index("--provider-state-root") + 1] = str(catalog_dir / "provider-state")
    acquisition_config = config_dir / "source_acquisition.yaml"
    write_json(acquisition_config, acquisition)

    # All modules below are documented public CWP command entry points. This
    # bootstrap selects the tested code checkout independently of the data root.
    launch = root / "cwp_entry.py"
    launch.write_text(
        "import os, runpy, sys\n"
        f"source_dir = {str(candidate / 'src')!r}\n"
        "sys.path.insert(0, source_dir)\n"
        "os.environ['PYTHONPATH'] = os.pathsep.join(filter(None, (source_dir, os.environ.get('PYTHONPATH'))))\n"
        "if __name__ == '__main__':\n"
        "    module = sys.argv.pop(1)\n"
        "    runpy.run_module('company_wiki.source_catalog.' + module, run_name='__main__')\n",
        encoding="utf-8",
    )
    base = [sys.executable, "-B", "-X", "utf8", str(launch)]
    connection = config_dir / "company_wiki.json"
    write_json(connection, {
        "schema_version": "1.0",
        "connection": {
            "cwd": str(root), "acquisition_config": str(acquisition_config),
            "commands": {
                role: [*base, module, "--config", str(catalog_config)]
                for role, module in (("catalog", "cli"), ("query", "source_query_cli"),
                                     ("open", "source_reader_cli"), ("local_prepare", "local_prepare_cli"))
            },
        },
    })
    write_json(config_dir / "rosters.json", {"rosters": {"three-market-pilot": {
        "snapshot_id": "stockwiki-" + hashlib.sha256(
            json.dumps(receipts, sort_keys=True).encode("utf-8")
        ).hexdigest(), "items": members,
    }}})
    write_json(config_dir / "scheduled_refresh.json", {
        "schema_version": "ff-scheduled-refresh-deployment/1",
        "pinned_rosters": "rosters.json", "lookback_days": 260, "overlap_days": 7,
        "limits": {"tick_seconds": 360, "metadata_pages": 18, "reading_documents": 6,
                   "acquisitions": 4,
                   "discovery": {"max_bytes": 8388608, "timeout_seconds": 60,
                                 "max_cost_usd": "0", "max_requests": 6},
                   "acquisition": {"max_bytes": 52428800, "timeout_seconds": 120, "max_cost_usd": "0"},
                   "reading": {"timeout_seconds": 180}},
    })
    result = command([*base, "cli", "--config", str(catalog_config), "scan"], cwd=root)
    proof = {"identity_receipts": receipts, "seed_sha256": seeds,
             "catalog_scan": result, "connection": str(connection)}
    write_json(root / "pilot-inputs.json", proof)
    return proof


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("company-wiki", "cwp-runtime", "identity-workspace", "scratch"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args()), ensure_ascii=False))


if __name__ == "__main__":
    main()
