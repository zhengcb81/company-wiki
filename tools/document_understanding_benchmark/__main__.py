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
from .controls import run_rescue_controls, run_review_controls
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
from .review import ReviewError, validate_review

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
    scope = "HOLDOUT" if result.get("scope") == "holdout" else "dev"
    return (
        f"  [{scope:<7}] {result['sample_id']:<28} {result['status']:<12} "
        f"critical_recall={recall_text} "
        f"checks={len(result['checks'])} not_evaluated={len(result['not_evaluated'])}"
    )


def _print_scope_summary(summary: dict[str, Any]) -> None:
    for scope, row in summary.items():
        recall = row["critical_fact_recall"]
        recall_text = "n/a" if recall is None else f"{recall:.3f}"
        print(
            f"  {scope:<12} docs={row['documents']} "
            f"critical={row['critical_facts_passed']}/{row['critical_facts_total']} "
            f"({recall_text}) statuses={row['statuses']}"
        )


def _carrier_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Report which carriers this run could actually observe.

    A carrier the existing public path cannot take in must be visible in the
    report, because otherwise an unsupported carrier is indistinguishable from
    a document with no business content.
    """

    counts: dict[str, dict[str, Any]] = {}
    for observed in observations:
        carrier = (observed.get("execution") or {}).get("carrier") or {}
        suffix = carrier.get("suffix") or "unknown"
        row = counts.setdefault(
            suffix,
            {
                "kind": carrier.get("kind"),
                "supported": carrier.get("supported"),
                "entry_point": carrier.get("entry_point"),
                "reason": carrier.get("reason"),
                "documents": 0,
                "unavailable": 0,
            },
        )
        row["documents"] += 1
        if (observed.get("coverage") or {}).get("native_scan") == "unavailable":
            row["unavailable"] += 1
    return {
        "by_suffix": dict(sorted(counts.items())),
        "unsupported_carriers_present": sorted(
            suffix for suffix, row in counts.items() if row.get("supported") is False
        ),
    }


def _overall_exit(results: list[dict[str, Any]]) -> int:
    statuses = {result["status"] for result in results}
    if "FAIL" in statuses:
        return EXIT_FAIL
    if statuses & {"PARTIAL", "UNAVAILABLE"}:
        return EXIT_PARTIAL
    return EXIT_PASS


def _scope_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate by development/holdout.

    Development and holdout must never be merged into one headline number: the
    development samples were used to tune rules, so only the holdout split is
    evidence about generalisation. Both are reported with their own denominator.
    """

    by_scope: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_scope.setdefault(result.get("scope") or "development", []).append(result)

    summary: dict[str, Any] = {}
    for scope, rows in sorted(by_scope.items()):
        critical_pass = 0
        critical_total = 0
        critical_unavailable = 0
        fact_pass = 0
        fact_total = 0
        statuses: dict[str, int] = {}
        for row in rows:
            statuses[row["status"]] = statuses.get(row["status"], 0) + 1
            metrics = row.get("metrics") or {}
            denominator = metrics.get("critical_fact_recall_denominator") or 0
            recall = metrics.get("critical_fact_recall")
            if recall is not None and denominator:
                critical_pass += round(recall * denominator)
            critical_total += denominator
            critical_unavailable += metrics.get("critical_fact_unavailable") or 0
            fact_denominator = metrics.get("fact_recall_denominator") or 0
            fact_recall = metrics.get("fact_recall")
            if fact_recall is not None and fact_denominator:
                fact_pass += round(fact_recall * fact_denominator)
            fact_total += fact_denominator
        summary[scope] = {
            "documents": len(rows),
            "statuses": dict(sorted(statuses.items())),
            "critical_facts_passed": critical_pass,
            "critical_facts_total": critical_total,
            "critical_facts_unavailable": critical_unavailable,
            "critical_fact_recall": (
                critical_pass / critical_total if critical_total else None
            ),
            "facts_passed": fact_pass,
            "facts_total": fact_total,
            "fact_recall": (fact_pass / fact_total) if fact_total else None,
        }
    return summary


def _load_reviews(path_value: str | None) -> dict[str, Any] | None:
    """Load an optional independent-review file, keyed by sample_id.

    Returns ``None`` to refuse the run when the file exists but is malformed: a
    bad review must never be silently ignored, because ignoring it would report
    ``NOT_EVALUATED`` where the operator believed a review had been applied.

    Accepts either one review object or a list of them.
    """

    if not path_value:
        return {}
    path = Path(path_value)
    try:
        raw = json.loads(path.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"refused: cannot read review file {path}: {exc}", file=sys.stderr)
        return None
    records = raw if isinstance(raw, list) else [raw]
    reviews: dict[str, Any] = {}
    for index, record in enumerate(records):
        try:
            checked = validate_review(record)
        except ReviewError as exc:
            print(f"refused: review[{index}] is invalid: {exc}", file=sys.stderr)
            return None
        sample_id = checked.get("sample_id")
        if not sample_id:
            print(f"refused: review[{index}] has no sample_id", file=sys.stderr)
            return None
        reviews[str(sample_id)] = checked
    print(f"reviews loaded: {len(reviews)} ({sorted(reviews)})")
    return reviews


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
    review_reports: list[dict[str, Any]] = []
    reviews = _load_reviews(args.review)
    if reviews is None:
        return EXIT_REFUSED
    for fixture in all_fixtures():
        gold = validate_gold(fixture["gold"])
        observed = validate_observed(fixture["observed"])
        result = evaluate(observed, gold, review=reviews.get(gold["sample_id"]))
        result["fixture_id"] = fixture["fixture_id"]
        results.append(result)
        mutation_reports.append(run_mutation_suite(observed, gold))
        # Measure what only a review can catch, and prove a review cannot mask
        # a deterministic failure. Reported even when no review was supplied,
        # because the controls inject their own verdicts.
        review_reports.append(
            {
                "fixture_id": fixture["fixture_id"],
                "semantic_only": run_review_controls(dict(observed), gold),
                "rescue": run_rescue_controls(dict(observed), gold),
            }
        )

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
        "by_scope": _scope_summary(results),
        "results": results,
        "mutations": mutation_reports,
        "review_controls": review_reports,
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
    print("by scope:")
    _print_scope_summary(report["by_scope"])
    blind = sum(row["semantic_only"]["deterministic_blind_count"] for row in review_reports)
    controls = sum(row["semantic_only"]["controls_total"] for row in review_reports)
    review_ok = all(row["semantic_only"]["review_caught_all"] for row in review_reports)
    rescue_ok = all(row["rescue"]["all_rescues_blocked"] for row in review_reports)
    print(
        f"semantic-only defects invisible to deterministic checks: {blind}/{controls}; "
        f"review caught all: {review_ok}; review cannot rescue a FAIL: {rescue_ok}"
    )
    print(f"sentinel restored: {sentinel_restored['unchanged']} ({sentinel_restored['reason']})")
    print(f"summary: {owned / 'summary.json'}")
    return exit_code


def run_native(args: argparse.Namespace) -> int:
    from .observer import ObserverUnavailable, carrier_support, observe_native

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

    reviews = _load_reviews(args.review)
    if reviews is None:
        return EXIT_REFUSED

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
            observed["execution"]["carrier"] = carrier_support(path)
            observed["execution"]["raw_unchanged"] = (
                original_before.get("sha256") == original_after.get("sha256")
                and original_before.get("mtime_ns") == original_after.get("mtime_ns")
            )
        result = evaluate(observed, gold, review=reviews.get(gold["sample_id"]))
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
        "by_scope": _scope_summary(results),
        "carrier_support": _carrier_summary(observations),
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
    print("by scope:")
    _print_scope_summary(report["by_scope"])
    carriers = report["carrier_support"]
    for suffix, row in carriers["by_suffix"].items():
        state = "supported" if row["supported"] else "UNSUPPORTED"
        print(
            f"  carrier {suffix:<7} {state:<12} docs={row['documents']} "
            f"unavailable={row['unavailable']}"
        )
    if carriers["unsupported_carriers_present"]:
        print(
            f"  unsupported carriers present: {carriers['unsupported_carriers_present']} "
            "(no route into the existing selector; reported UNAVAILABLE, not a quality verdict)"
        )
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
        "--review",
        help=(
            "independent semantic-review JSON (one object or a list, each with "
            "sample_id and per-claim verdicts). Without it, semantics.entailment "
            "stays NOT_EVALUATED rather than silently passing."
        ),
    )
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
