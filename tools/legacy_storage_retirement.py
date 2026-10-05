#!/usr/bin/env python3
"""P5-STORAGE legacy derived/evidence retirement maintenance CLI.

operations:
  inventory       strictly read-only classification + manifest
  retire-derived  retire legacy artifact handles then unlink exactly those files
  prune-spans     prune legacy full-volume evidence_spans for an explicit
                  parser/source scope, protecting keep-refs
  vacuum          physical DB shrink with real-space accounting

Mutating entries require an explicit --apply; without it every mutating
operation runs dry (receipt records dry_run=true).  inventory is always dry.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from legacy_storage.core import directed_inside, normalized, write_json
from legacy_storage.shrink import run_vacuum
from legacy_storage.spans import run_prune_spans
from legacy_storage.retirement import run_retire_derived, _load_manifest

REPORT_SCHEMA = "cwp-storage-retirement/1"


def _load_config(path: Path):
    from company_wiki.source_catalog.config import load_catalog_config

    return load_catalog_config(Path(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)

    inv = sub.add_parser("inventory")
    inv.add_argument("--config", type=Path, required=True)
    inv.add_argument("--output", type=Path, required=False)

    ret = sub.add_parser("retire-derived")
    ret.add_argument("--config", type=Path, required=True)
    ret.add_argument("--manifest", type=Path, required=True)
    ret.add_argument("--receipt", type=Path, required=True)
    ret.add_argument("--apply", action="store_true")

    prune = sub.add_parser("prune-spans")
    prune.add_argument("--config", type=Path, required=True)
    prune.add_argument("--selection", type=Path, required=True)
    prune.add_argument("--keep-refs", type=Path, required=False, default=None)
    prune.add_argument("--receipt", type=Path, required=True)
    prune.add_argument("--apply", action="store_true")

    vac = sub.add_parser("vacuum")
    vac.add_argument("--config", type=Path, required=True)
    vac.add_argument("--receipt", type=Path, required=True)
    vac.add_argument("--apply", action="store_true")

    args = parser.parse_args(argv)
    config = _load_config(args.config)
    target = getattr(args, "output", None) or getattr(args, "receipt", None)
    if target is not None and (
        normalized(target) == normalized(args.config)
        or any(normalized(target) == normalized(root) or directed_inside(target, root)
               for root in (Path(config.catalog_dir), *(r.path for r in config.roots)))
    ):
        sys.stderr.write(json.dumps({"schema_version": REPORT_SCHEMA,
                                    "operation": args.operation, "status": "refused",
                                    "error_code": "report_path_overlaps_data"}) + "\n")
        return 2

    if args.operation == "inventory":
        from legacy_storage.inventory import run_inventory

        result = run_inventory(config)
        if args.output is not None:
            result.write_manifest(args.output)
        _emit(args.output, result.report, args.config)
        return 0 if result.report["status"] == "succeeded" else 2

    if args.operation == "retire-derived":
        manifest = _load_manifest(args.manifest)
        report = run_retire_derived(config, manifest, dry_run=not args.apply)
        _receipt(args.receipt, report)
        return 0 if report["status"] == "succeeded" else 2

    if args.operation == "prune-spans":
        selection = json.loads(args.selection.read_text(encoding="utf-8"))
        keep_refs = []
        if args.keep_refs is not None:
            with Path(args.keep_refs).open(encoding="utf-8") as stream:
                for line in stream:
                    if line.strip():
                        keep_refs.append(json.loads(line))
        report = run_prune_spans(
            config, selection, keep_refs=keep_refs, dry_run=not args.apply
        )
        _receipt(args.receipt, report)
        return 0 if report["status"] == "succeeded" else 2

    if args.operation == "vacuum":
        report = run_vacuum(config, dry_run=not args.apply)
        _receipt(args.receipt, report)
        return 0 if report["status"] == "succeeded" else 2

    parser.error(f"unknown operation {args.operation}")
    return 2


def _emit(output_ms, manifest, config_path) -> None:
    _ = config_path
    line = json.dumps(
        {
            "schema_version": REPORT_SCHEMA,
            "manifest_emitted": None if output_ms is None else str(output_ms),
            "operation": "inventory",
            "status": manifest["status"],
        },
        sort_keys=True,
    )
    _ = manifest
    sys.stderr.write(line + "\n")


def _receipt(path, report: dict) -> None:
    write_json(Path(path), report)


if __name__ == "__main__":
    raise SystemExit(main())
