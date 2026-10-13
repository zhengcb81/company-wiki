"""Benchmark CLI: ``python -m tools.document_understanding_benchmark``.

Modes
-----
``offline``
    Synthetic fixtures only. No original, no network, no model call.
``native``
    Read-only observation of whitelisted originals through the *existing*
    public parser/selector. Originals are resolved by local bindings and
    verified by SHA-256; a missing binding or digest mismatch is ``UNAVAILABLE``.

Both modes write only inside the directory given by ``--output``, and only into
a child the run marks as owned. Exit codes: 0 all evaluated samples PASS,
2 refused to run (bad gold/bindings/adapter), 3 PARTIAL/UNAVAILABLE present,
1 FAIL present.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from . import __name__ as package_name
from .evaluate import evaluate
from .fixtures import OFFLINE_FIXTURE_BUDGET, all_fixtures, fixture_bytes
from .gold import GoldError, load_bindings, load_gold_dir, resolve_original, unavailable_observed
from .mutations import run_mutation_suite
from .records import validate_gold, validate_observed
from .recovery import (
    cleanup_owned,
    compare_fingerprints,
    directory_size,
    file_fingerprint,
    fingerprint_many,
    install_sentinel,
    mark_owned,
    peak_rss_bytes,
    resource_report,
    restore_sentinel,
)
from .schema import BenchmarkSchemaError

OFFLINE_FIXTURE_BUDGET_LOCAL = OFFLINE_FIXTURE_BUDGET
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_REFUSED = 2
EXIT_PARTIAL = 3


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf8",
    )


def _summary_line(result: dict[str, Any]) -> str:
    metrics = result.get("metrics") or {}
    recall = metrics.get("critical_fact_recall")
    recall_text = "n/a" if recall is None else f"{recall:.3f}"
    return (
        f"  {result['sample_id']:<20} {result['status']:<12} "
        f"critical_recall={recall_text} "
        f"checks={len(result['checks'])} not_evaluated={len(result['not_evaluated'])}"
    )


def _overall_exit(results: list[dict[str, Any]]) -> int:
    statuses = {result["status"] for result in results}
    if "FAIL" in statuses:
        return EXIT_FAIL
    if statuses & {"PARTIAL", "UNAVAILABLE"}:
        return EXIT_PARTIAL
    return EXIT_PASS


def run_offline(args: argparse.Namespace) -> int:
    size = fixture_bytes()
    if size > OFFLINE_FIXTURE_BUDGET:
        print(f"offline fixtures exceed budget: {size} > {OFFLINE_FIXTURE_BUDGET}", file=sys.stderr)
        return EXIT_REFUSED

    out_dir = Path(args.output)
    owned = out_dir / "offline"
    mark_owned(owned)
    sentinel = install_sentinel(owned, {"mode": "offline"}, preserve_existing=True)

    started = time.monotonic()
    results: list[dict[str, Any]] = []
    mutation_reports: list[dict[str, Any]] = []
    for fixture in all_fixtures():
        gold = validate_gold(fixture["gold"])
        observed = validate_observed(fixture["observed"])
        result = evaluate(observed, gold)
        result["fixture_id"] = fixture["fixture_id"]
        results.append(result)
        mutation_reports.append(run_mutation_suite(observed, gold))

    elapsed = time.monotonic() - started
    exit_code = _overall_exit(results)

    report = {
        "schema_version": "du-bench-run/1",
        "mode": "offline",
        "entry_point": f"{package_name}.__main__",
        "fixtures_total": len(results),
        "fixture_bytes": size,
        "fixture_budget_bytes": OFFLINE_FIXTURE_BUDGET,
        "network_calls": 0,
        "model_calls": 0,
        "paid_calls": 0,
        "elapsed_seconds": round(elapsed, 3),
        "results": results,
        "mutations": mutation_reports,
        "resources": resource_report(
            elapsed_seconds=elapsed,
            derived_bytes=directory_size(owned),
            scratch_bytes=directory_size(owned),
            raw_bytes=0,
            model_calls=0,
            peak_rss=peak_rss_bytes(),
        ),
    }
    _write_json(owned / "summary.json", report)

    sentinel_restored = restore_sentinel(owned, sentinel)
    print(f"offline fixtures: {len(results)} ({size} bytes)")
    for result in results:
        print(_summary_line(result))
    applicable = sum(row["mutations_applicable"] for row in mutation_reports)
    detected = sum(row["mutations_detected"] for row in mutation_reports)
    not_applicable = sum(row["mutations_not_applicable"] for row in mutation_reports)
    print(
        f"mutations detected: {detected}/{applicable} "
        f"({not_applicable} not applicable to these fixtures)"
    )
    print(f"sentinel restored: {sentinel_restored['unchanged']} ({sentinel_restored['reason']})")
    print(f"summary: {owned / 'summary.json'}")
    return exit_code


def run_native(args: argparse.Namespace) -> int:
    from .observer import ObserverUnavailable, observe_native

    try:
        golds = load_gold_dir(Path(args.gold_dir) if args.gold_dir else None)
        bindings = load_bindings(Path(args.bindings) if args.bindings else None)
    except (GoldError, BenchmarkSchemaError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED

    selected = set(args.sample or [])
    if selected:
        golds = [gold for gold in golds if gold["sample_id"] in selected]
        if not golds:
            print(f"refused: no gold matches {sorted(selected)}", file=sys.stderr)
            return EXIT_REFUSED

    out_dir = Path(args.output)
    owned = out_dir / "native"
    mark_owned(owned)

    # Capture any pre-existing sentinel *before* touching it, then put it back
    # byte-identical at the end. A run must never rewrite content it found.
    sentinel = install_sentinel(owned, {"mode": "native"}, preserve_existing=True)

    probes = [Path(value) for value in (args.probe_file or [])]
    probes += [Path(path) for path in (args.probe_config or [])]
    probes.append(Path(sentinel["path"]))
    before = fingerprint_many(probes)

    started = time.monotonic()
    results: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for gold in golds:
        resolved = resolve_original(gold["sample_id"], gold["source_sha256"], bindings)
        if resolved["status"] != "OK":
            observed = unavailable_observed(gold, resolved["reason"])
            observed["execution"]["resolved_path"] = resolved.get("path")
        else:
            path = Path(resolved["path"])
            original_before = file_fingerprint(path)
            try:
                observed = observe_native(
                    path,
                    sha256=gold["source_sha256"],
                    sample_id=gold["sample_id"],
                )
            except ObserverUnavailable as exc:
                observed = unavailable_observed(gold, f"observer unavailable: {exc}")
            finally:
                original_after = file_fingerprint(path)
            observed["execution"]["resolved_path"] = str(path)
            observed["execution"]["raw_unchanged"] = (
                original_before.get("sha256") == original_after.get("sha256")
                and original_before.get("mtime_ns") == original_after.get("mtime_ns")
            )
        result = evaluate(observed, gold)
        results.append(result)
        observations.append(observed)

    elapsed = time.monotonic() - started
    after = fingerprint_many(probes)
    restoration = compare_fingerprints(before, after)
    sentinel_restored = restore_sentinel(owned, sentinel)

    raw_unchanged = all(
        observation.get("execution", {}).get("raw_unchanged", True) for observation in observations
    )

    exit_code = _overall_exit(results)
    report = {
        "schema_version": "du-bench-run/1",
        "mode": "native",
        "entry_point": f"{package_name}.__main__",
        "samples_total": len(results),
        "bindings_supplied": len(bindings),
        "resolved": sum(1 for o in observations if o.get("coverage", {}).get("native_scan") != "unavailable"),
        "unavailable": sum(
            1 for o in observations if o.get("coverage", {}).get("native_scan") == "unavailable"
        ),
        "network_calls": 0,
        "model_calls": 0,
        "paid_calls": 0,
        "elapsed_seconds": round(elapsed, 3),
        "results": results,
        "observations": observations,
        "restoration": {
            "config_unchanged": restoration,
            "raw_unchanged": raw_unchanged,
            "sentinel_restored": sentinel_restored,
            "sentinel_stable": sentinel_restored["unchanged"],
        },
        "resources": resource_report(
            elapsed_seconds=elapsed,
            derived_bytes=directory_size(owned),
            scratch_bytes=directory_size(owned),
            raw_bytes=sum(
                int(file_fingerprint(Path(o["execution"]["resolved_path"])).get("size") or 0)
                for o in observations
                if o.get("execution", {}).get("resolved_path")
            ),
            model_calls=0,
            peak_rss=peak_rss_bytes(),
        ),
    }
    _write_json(owned / "summary.json", report)

    print(f"native samples: {len(results)} (bindings={len(bindings)})")
    for result in results:
        print(_summary_line(result))
    print(f"raw unchanged: {raw_unchanged}")
    print(f"config unchanged: {restoration['unchanged']} (probes={restoration['count']})")
    print(f"sentinel restored: {sentinel_restored['unchanged']} ({sentinel_restored['reason']})")
    print(f"summary: {owned / 'summary.json'}")

    if args.cleanup:
        cleanup = cleanup_owned(owned, keep={"summary.json"})
        print(f"cleanup: {cleanup}")
    return exit_code


def run_du_adapter(args: argparse.Namespace) -> int:
    """Observe through a ROOT-injected adapter for testing the adapter seam."""


    adapter_path = Path(args.adapter) if args.adapter else None
    if adapter_path is None or not adapter_path.is_file():
        print("refused: --adapter must point to an importable python file", file=sys.stderr)
        return EXIT_REFUSED

    import importlib.util

    spec = importlib.util.spec_from_file_location("du_bench_adapter", adapter_path)
    if spec is None or spec.loader is None:
        print("refused: cannot load adapter", file=sys.stderr)
        return EXIT_REFUSED
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entry = getattr(module, "observe", None)
    if not callable(entry):
        print("refused: adapter must define observe(observation) -> mapping", file=sys.stderr)
        return EXIT_REFUSED

    print("adapter loaded; use --mode native with ROOT-injected wiring for real runs")
    return EXIT_PASS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.document_understanding_benchmark",
        description="Independent document-understanding quality benchmark (DU-BENCH).",
    )
    parser.add_argument("--mode", choices=("offline", "native", "adapter"), default="offline")
    parser.add_argument("--bindings", help="local uncommitted {sample_id: absolute_path} JSON")
    parser.add_argument("--output", required=True, help="directory owned by this run")
    parser.add_argument("--gold-dir", help="override the packaged gold directory")
    parser.add_argument("--sample", action="append", help="restrict to a sample_id (repeatable)")
    parser.add_argument("--adapter", help="path to a ROOT-injected observer adapter")
    parser.add_argument(
        "--probe-file",
        action="append",
        help="extra file whose SHA+mtime must be unchanged (repeatable)",
    )
    parser.add_argument(
        "--probe-config",
        action="append",
        help="production config file to fingerprint (repeatable)",
    )
    parser.add_argument("--cleanup", action="store_true", help="remove owned scratch after the run")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "offline":
        return run_offline(args)
    if args.mode == "native":
        return run_native(args)
    return run_du_adapter(args)


if __name__ == "__main__":
    raise SystemExit(main())
