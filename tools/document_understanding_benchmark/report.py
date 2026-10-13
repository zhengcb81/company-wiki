"""CLI helper: run the packaged gold against local bindings and emit a report.

This is a convenience wrapper used by the maintainer and by C-node evidence
collection. It is not part of the public evaluation interface.

Usage::

    python -X utf8 tools/document_understanding_benchmark/report.py \
        --bindings <local bindings.json> --output <owned-dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .evaluate import evaluate
from .gold import GoldError, load_bindings, load_gold_dir, resolve_original, unavailable_observed
from .recovery import (
    compare_fingerprints,
    directory_size,
    file_fingerprint,
    fingerprint_many,
)
from .schema import BenchmarkSchemaError

REPORT_SCHEMA_VERSION = "du-bench-report/1"


def _native_sample(gold: dict, bindings: dict[str, str], probes: list[Path]) -> dict:
    from .observer import ObserverUnavailable, observe_native

    resolved = resolve_original(gold["sample_id"], gold["source_sha256"], bindings)
    if resolved["status"] != "OK":
        observed = unavailable_observed(gold, resolved["reason"])
        return {
            "sample_id": gold["sample_id"],
            "resolved": resolved,
            "observed": observed,
            "evaluation": evaluate(observed, gold),
            "raw_unchanged": None,
        }

    path = Path(resolved["path"])
    before = file_fingerprint(path)
    try:
        observed = observe_native(path, sha256=gold["source_sha256"], sample_id=gold["sample_id"])
    except ObserverUnavailable as exc:
        observed = unavailable_observed(gold, f"observer unavailable: {exc}")
    after = file_fingerprint(path)
    unchanged = before.get("sha256") == after.get("sha256") and before.get("mtime_ns") == after.get(
        "mtime_ns"
    )
    return {
        "sample_id": gold["sample_id"],
        "resolved": resolved,
        "observed": observed,
        "evaluation": evaluate(observed, gold),
        "raw_unchanged": unchanged,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect DU-BENCH evidence.")
    parser.add_argument("--bindings", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--probe-config", action="append", default=[])
    args = parser.parse_args(argv)

    try:
        golds = load_gold_dir()
        bindings = load_bindings(Path(args.bindings))
    except (GoldError, BenchmarkSchemaError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    probes = [Path(p) for p in args.probe_config]
    before = fingerprint_many(probes)

    samples = [_native_sample(gold, bindings, probes) for gold in golds]
    after = fingerprint_many(probes)

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "samples": [
            {
                "sample_id": sample["sample_id"],
                "status": sample["evaluation"]["status"],
                "critical_fact_recall": sample["evaluation"]["metrics"]["critical_fact_recall"],
                "critical_fact_denominator": sample["evaluation"]["metrics"][
                    "critical_fact_recall_denominator"
                ],
                "raw_unchanged": sample["raw_unchanged"],
                "resolved": sample["resolved"]["status"],
                "routed_kind": (sample["observed"].get("route") or {}).get("document_kind"),
                "selected_spans": sample["observed"]["metrics"].get("selected_spans"),
                "candidate_count": sample["observed"]["metrics"].get("candidate_count"),
                "source_units": sample["observed"]["metrics"].get("source_units"),
                "pages_read": sample["observed"]["metrics"].get("pages_read"),
                "page_count": sample["observed"]["metrics"].get("page_count"),
                "native_scan": sample["observed"]["coverage"].get("native_scan"),
                "opaque_pages": sample["observed"]["coverage"].get("opaque_pages"),
                "elapsed_seconds": sample["observed"]["execution"].get("elapsed_seconds"),
            }
            for sample in samples
        ],
        "config_unchanged": compare_fingerprints(before, after),
        "raw_all_unchanged": all(
            sample["raw_unchanged"] is not False for sample in samples
        ),
        "network_calls": 0,
        "model_calls": 0,
        "paid_calls": 0,
        "raw_copies": 0,
        "derived_bytes": directory_size(Path(args.output)),
    }

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    target = output / "native-report.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf8")
    print(json.dumps(report, ensure_ascii=False, indent=2)[:4000])
    print(f"\nwrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
