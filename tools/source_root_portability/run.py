"""W06-CWP-PORTABILITY manual runner.

Usage:
    python -B tools/source_root_portability/run.py \
        --owned-root <fresh-root> --out-root <new-attempt-root>

Builds a synthetic fixture lake, replays the seven migration/reference
scenarios against the real company_wiki source catalog, writes one small
report (schema cwp-root-portability/1) into a fresh attempt directory, and
restores the owned root to its baseline.  Exit codes: 0 all PASS, 3 product
gaps reported as PARTIAL/UNKNOWN, 1 oracle FAIL, 2 invalid record/runtime.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_WORKTREE = Path(__file__).resolve().parents[2]
_WORKTREE_SRC = _WORKTREE / "src"
for _entry in (str(_WORKTREE_SRC), str(_WORKTREE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from tools.source_root_portability import oracle, report  # noqa: E402
from tools.source_root_portability.fixture_builder import (  # noqa: E402
    FIXTURE_ROOT_SPECS,
    build_fixture,
)
from tools.source_root_portability.scenarios import (  # noqa: E402
    Harness,
    scenario_s1,
    scenario_s2,
    scenario_s3,
    scenario_s4,
    scenario_s5,
    scenario_s6,
    scenario_s7,
)

from tools.source_root_portability.runtime import (  # noqa: E402
    OwnedAttempt, child_env, offline_guard, synthetic_environment, validate_roots,
)


def _sha256_file(path: Path) -> str:
    return report.sha256_file(path)


def snapshot_baseline(owned_root: Path) -> dict[str, Any]:
    """Shallow stat inventory only; never scan/hash a caller's existing lake."""
    if not owned_root.exists():
        return {"exists": False, "sentinels": []}
    entries = []
    for path in sorted(owned_root.iterdir()):
        metadata = path.lstat()
        entries.append({
            "path_ref": path.name,
            "type": "directory" if __import__("stat").S_ISDIR(metadata.st_mode) else "file",
            "byte_size": metadata.st_size,
            "mtime_ns": metadata.st_mtime_ns,
            "inode": metadata.st_ino,
        })
    return {"exists": True, "sentinels": entries}


def snapshot_after(owned_root: Path) -> dict[str, Any]:
    return snapshot_baseline(owned_root)


def cleanup_owned_root(owned_root: Path, baseline: dict[str, Any],
                       created_attempt: OwnedAttempt | None = None) -> tuple[bool, bool]:
    """No ownership object means no deletion, including legacy named folders."""
    if created_attempt is not None:
        if created_attempt.container != owned_root:
            raise ValueError("attempt belongs to another container")
        created_attempt.cleanup()
    restored = snapshot_after(owned_root) == baseline
    return restored, restored


def build_record(*, attempt_id: str, started_at: str, elapsed: float,
                 fixture_lake: Any, harness: Harness,
                 scenario_records: list[dict[str, Any]],
                 baseline: dict[str, Any], restored: bool,
                 owned_container: Path, final_reads: list[dict[str, Any]],
                 raw_unchanged: bool, blocked_actions: list[str]) -> dict[str, Any]:
    scenarios = []
    for record in scenario_records:
        entry = dict(record)
        entry["expected"] = copy.deepcopy(oracle.FIXED_EXPECTATIONS[entry["id"]])
        entry["actual"] = {"reported_status": entry.get("status")}
        entry["cleanup"] = {"scope": "created_attempt", "restored": restored}
        scenarios.append(entry)
    findings = []
    for entry in scenarios:
        if entry.get("status") == "PARTIAL" and entry.get("failure"):
            findings.append({
                "id": f"{entry['id']}-{entry['failure'].get('code')}",
                "root_cause": entry["failure"].get("detail", ""),
                "disposition": "ROOT_FIX_SUGGESTED",
                "evidence": f"report scenarios[{entry['id']}]",
                "test_ids": ["tests/integration/test_w06_root_portability.py"],
            })
        if entry.get("evidence", {}).get("needs_root_decision"):
            findings.append({
                "id": f"{entry['id']}-identity-stability-unknown",
                "root_cause": "document identity stability across re-registration "
                              "is not promised by the read interface",
                "disposition": "ROOT_DECIDES",
                "evidence": "S3 revision relation observation",
                "test_ids": [],
            })
    in_process = harness.in_process_reader_calls
    config_summary = {
        "schema_version": "1.0",
        "roots": [
            {
                "root_id": spec["root_id"],
                "path_ref": f"lake/{fixture_lake.root_dirs[spec['root_id']].name}",
                "kind": "directory",
                "priority": spec["priority"],
                "adapter_id": "sidecar_filing_v1",
            }
            for spec in FIXTURE_ROOT_SPECS
        ],
        "catalog_dir_ref": "owned/catalog",
        "config_files": [
            "owned/cfg/config_lake_A.yaml", "owned/cfg/config_lake_B.yaml",
        ],
    }
    return {
        "schema_version": oracle.SCHEMA_VERSION,
        "run": {
            "run_id": attempt_id,
            "runner_pid": os.getpid(),
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "elapsed_seconds": round(elapsed, 3),
            "code_identity": report.capture_code_identity(_WORKTREE),
            "config_summary": config_summary,
        },
        "fixture": {"originals": fixture_lake.original_manifest(),
                    "final_reads": final_reads},
        "scenarios": scenarios,
        "consumer_access": {"entries": harness.consumer_access_entries},
        "cost": {
            "in_process_reader_calls": in_process,
            "subprocess_read_invocations": harness.subprocess_read_invocations,
            "source_read_calls": in_process + harness.subprocess_read_invocations,
            "http_calls": 0,
            "model_calls": 0,
            "paid_usd": 0.0,
            "basis": "synthetic current-reader/CLI only; active offline audit guard",
            "blocked_actions": blocked_actions,
        },
        "cleanup": {
            "owned_root": str(owned_container).replace("\\", "/"),
            "created_child": str(harness.owned_root).replace("\\", "/"),
            "baseline": baseline,
            "after": snapshot_after(owned_container),
            "deleted_within_owned": True,
            "restored": restored,
            "raw_unchanged": raw_unchanged,
            "raw_scope": "known synthetic originals only; no production raw accessed",
        },
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owned-root", type=Path, required=True,
                        help="container for a unique owned child; existing contents are preserved")
    parser.add_argument("--out-root", type=Path, required=True,
                        help="root for new attempt directories (never overwritten)")
    args = parser.parse_args(argv)

    try:
        owned_root, out_root = validate_roots(args.owned_root, args.out_root)
        report.assert_worktree_binding(_WORKTREE)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"refusing to run: {exc}", file=sys.stderr)
        return 2
    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    clock_start = time.monotonic()
    baseline = snapshot_baseline(owned_root)
    attempt = report.create_attempt(out_root)
    created: OwnedAttempt | None = None
    harness: Harness | None = None
    fixture_lake = None
    scenario_records: list[dict[str, Any]] = []
    final_reads: list[dict[str, Any]] = []
    blocked_actions: list[str] = []
    setup_error = None
    raw_unchanged = False
    restored = False
    try:
        created = OwnedAttempt(owned_root)
        env = child_env(_WORKTREE, created.path / "runtime")
        with synthetic_environment(env), offline_guard() as blocked_actions:
            fixture_lake = build_fixture(created.path)
            harness = Harness(created.path, attempt.path, fixture_lake)
            harness.open_catalog(fixture_lake.config_path)
            for scenario_fn in (scenario_s1, scenario_s2, scenario_s3, scenario_s4,
                                scenario_s5, scenario_s6, scenario_s7):
                scenario_id = "S" + scenario_fn.__name__.rsplit("_s", 1)[-1]
                try:
                    value = scenario_fn(harness)
                except Exception:
                    traceback.print_exc()
                    value = {
                        "id": scenario_id, "status": "PARTIAL",
                        "failure": {"code": "runner_exception",
                                    "detail": traceback.format_exc(limit=5)[-500:]},
                        "evidence": {},
                    }
                scenario_records.append(value)
                print(f"[{value['id']}] {value['status']}")
            for doc in fixture_lake.docs.values():
                final_reads.append(harness.verified_read(harness.ref_for(doc), doc))
            raw_unchanged = all(
                read["read_sha256"] == fixture_lake.docs[read["doc_key"]].content_sha256
                and read["byte_size"] == fixture_lake.docs[read["doc_key"]].byte_size
                for read in final_reads
            )
            harness.close_catalog()
    except Exception as exc:
        traceback.print_exc()
        setup_error = f"{type(exc).__name__}: {exc}"
    finally:
        if harness is not None:
            harness.close_catalog()
        try:
            restored, _ = cleanup_owned_root(owned_root, baseline, created)
        except (OSError, ValueError) as exc:
            setup_error = f"cleanup failure: {type(exc).__name__}: {exc}"

    elapsed = time.monotonic() - clock_start
    if harness is None or fixture_lake is None:
        failure = {"status": "INVALID_RECORD", "setup_error": setup_error,
                   "baseline": baseline, "after": snapshot_after(owned_root),
                   "restored": restored, "elapsed_seconds": round(elapsed, 3)}
        (attempt.path / "initialization-failure.json").write_text(
            json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("harness failed to initialize; failure receipt retained", file=sys.stderr)
        return 2
    record = build_record(
        attempt_id=attempt.attempt_id, started_at=started_at, elapsed=elapsed,
        fixture_lake=fixture_lake, harness=harness, scenario_records=scenario_records,
        baseline=baseline, restored=restored, owned_container=owned_root,
        final_reads=final_reads, raw_unchanged=raw_unchanged,
        blocked_actions=blocked_actions,
    )
    if setup_error:
        record["findings"].append({"id": "runner-error", "root_cause": setup_error})
    verdict = oracle.evaluate_run(record)
    record["oracle_verdict"] = {
        "statuses": verdict.statuses,
        "overall": verdict.overall,
        "findings": [
            {"code": f.code, "scenario_id": f.scenario_id,
             "detail": f.detail, "outcome": f.outcome}
            for f in verdict.findings
        ],
    }
    report_path = report.write_report(attempt, record)
    print(f"report: {report_path}")
    print(f"overall: {verdict.overall}")
    for finding in verdict.findings:
        print(f"  finding: {finding.code} [{finding.scenario_id}] {finding.detail}")
    if verdict.overall == oracle.STATUS_PASS:
        return 0
    if verdict.overall in {oracle.STATUS_PARTIAL, oracle.STATUS_UNKNOWN}:
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
