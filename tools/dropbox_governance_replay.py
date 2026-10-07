"""FC-503 read-only governance report entry (G3-CWP-MAINT).

The former real-root double-scan replay and its 中国平安 manual sign-off
gate are retired.  This tool is now a read-only report entry only:

* with no arguments it prints the read-only report contract
  (``inventory_only``, ``writes=0``) and exits 0 — it resolves NO root, opens
  NO catalog, and never scans the production Dropbox;
* an explicitly supplied ``--root`` is inventoried read-only, twice, and a
  compact JSON summary is printed (determinism + zero writes; no absolute
  paths, no file contents).

Company-specific manual sign-off checks were removed: the same sidecar
evidence classifies the same way for every company, and company counters in
the summary are diagnostics only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from company_wiki.source_catalog.dropbox_governance import (  # noqa: E402
    inventory_dropbox,
)
from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _report_contract() -> dict:
    """Static description of the read-only report entry (no I/O)."""
    return {
        "mode": "read_only_report",
        "inventory_only": True,
        "writes": 0,
        "scanned": False,
        "production_root_resolved": False,
        "note": (
            "supply --root PATH (optionally --catalog and --other-root-id) "
            "to inventory an EXPLICIT directory read-only; without arguments "
            "this entry resolves no root and scans nothing"
        ),
    }


def _summary(report: dict) -> dict:
    fp = report["fingerprint"]
    digest = hashlib.sha256(
        json.dumps(fp, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return {
        "candidates_total": report["candidates_total"],
        "by_role": report["by_role"],
        "buckets": report["buckets"],
        "missing_fields_top": dict(
            sorted(report["missing_fields"].items(), key=lambda kv: -kv[1])[:8]
        ),
        "duplicate_location_sets": report["duplicate_location_sets"]["count"],
        "company_specific": report["pingan"],  # diagnostics, never a gate
        "fingerprint_sha256": digest,
        "catalog_counts": report["catalog_counts"],
        "inventory_only": report["inventory_only"],
        "writes": report["writes"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="read-only governance report entry (no production scan)"
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="explicit directory to inventory read-only (twice, for determinism)",
    )
    parser.add_argument("--root-id", default="dropbox_stock")
    parser.add_argument("--adapter-id", default="sidecar_filing_v1")
    parser.add_argument(
        "--catalog",
        type=Path,
        help="optional catalog path opened read-only for duplicate sets",
    )
    parser.add_argument(
        "--other-root-id",
        action="append",
        default=[],
        help="root id to check for duplicate locations (repeatable)",
    )
    args = parser.parse_args(argv)

    if args.root is None:
        print(json.dumps(_report_contract(), ensure_ascii=False, indent=1))
        return 0

    root = RootSpec(
        root_id=args.root_id,
        path=args.root,
        kind="directory",
        adapter_id=args.adapter_id,
    )
    other_root_ids = tuple(args.other_root_id)
    first = inventory_dropbox(root, catalog=args.catalog, other_root_ids=other_root_ids)
    second = inventory_dropbox(
        root, catalog=args.catalog, other_root_ids=other_root_ids
    )
    if first["fingerprint"] != second["fingerprint"]:
        raise SystemExit("FAIL: fingerprint changed between two runs")
    if first["buckets"] != second["buckets"]:
        raise SystemExit("FAIL: buckets changed between two runs")
    if first["duplicate_location_sets"] != second["duplicate_location_sets"]:
        raise SystemExit("FAIL: duplicate sets changed between two runs")
    if first["writes"] != 0 or second["writes"] != 0:
        raise SystemExit("FAIL: inventory reported a write")
    print(
        json.dumps(
            {
                "result": "identical-across-two-runs",
                "summary": _summary(first),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
