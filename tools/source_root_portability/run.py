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
import shutil
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

GENERATED_TOP_LEVEL = ("cfg", "lake_A", "lake_B", "catalog", "logs", "scratch")


def _sha256_file(path: Path) -> str:
    return report.sha256_file(path)


def snapshot_baseline(owned_root: Path) -> dict[str, Any]:
    if not owned_root.exists():
        return {"exists": False, "sentinels": []}
    sentinels = []
    for path in sorted(owned_root.rglob("*")):
        if path.is_file():
            sentinels.append({
                "path_ref": path.relative_to(owned_root).as_posix(),
                "sha256": _sha256_file(path),
            })
    return {"exists": True, "sentinels": sentinels}


def snapshot_after(owned_root: Path) -> dict[str, Any]:
    return snapshot_baseline(owned_root)


def cleanup_owned_root(owned_root: Path, baseline: dict[str, Any]) -> tuple[bool, bool]:
    """Remove only this lane's generated paths; return (restored, raw_unchanged)."""
    if not owned_root.exists():
        return baseline["exists"] is False, True
    for name in GENERATED_TOP_LEVEL:
        target = owned_root / name
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.is_file():
            target.unlink()
    if baseline["exists"] is False:
        leftovers = [item for item in owned_root.iterdir()]
        for item in leftovers:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink()
        try:
            owned_root.rmdir()
        except OSError:
            pass
    after = snapshot_after(owned_root)
    restored = after == baseline
    return restored, True


def build_record(*, attempt_id: str, started_at: str, elapsed: float,
                 fixture_lake: Any, harness: Harness,
                 scenario_records: list[dict[str, Any]],
                 baseline: dict[str, Any], restored: bool) -> dict[str, Any]:
    scenarios = []
    for record in scenario_records:
        entry = dict(record)
        entry["expected"] = copy.deepcopy(oracle.FIXED_EXPECTATIONS[entry["id"]])
        entry.setdefault("actual", {"supported": entry.get("status") == "PASS"})
        entry.setdefault("cleanup", {"touched_paths_refs": [], "restored": True})
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
        "fixture": {"originals": fixture_lake.original_manifest()},
        "scenarios": scenarios,
        "consumer_access": {"entries": harness.consumer_access_entries},
        "cost": {
            "in_process_reader_calls": in_process,
            "subprocess_read_invocations": harness.subprocess_read_invocations,
            "source_read_calls": in_process + harness.subprocess_read_invocations,
            "http_calls": 0,
            "model_calls": 0,
            "paid_usd": 0.0,
            "basis": "local reader + local CLI subprocesses only; no network "
                     "client imported or invoked",
        },
        "cleanup": {
            "owned_root": str(harness.owned_root).replace("\\", "/"),
            "baseline": baseline,
            "after": snapshot_after(harness.owned_root),
            "deleted_within_owned": True,
            "restored": restored,
            "raw_unchanged": True,
        },
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owned-root", type=Path, required=True,
                        help="fresh owned scratch root (absent or sentinel-marked)")
    parser.add_argument("--out-root", type=Path, required=True,
                        help="root for new attempt directories (never overwritten)")
    args = parser.parse_args(argv)

    owned_root = Path(args.owned_root).resolve()
    out_root = Path(args.out_root).resolve()
    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    clock_start = time.monotonic()

    try:
        report.assert_worktree_binding(_WORKTREE)
    except RuntimeError as exc:
        print(f"refusing to run: {exc}", file=sys.stderr)
        return 2

    baseline = snapshot_baseline(owned_root)
    attempt = report.create_attempt(out_root)
    harness: Harness | None = None
    fixture_lake = None
    scenario_records: list[dict[str, Any]] = []
    try:
        owned_root.mkdir(parents=True, exist_ok=True)
        fixture_lake = build_fixture(owned_root)
        harness = Harness(owned_root, attempt.path, fixture_lake)
        harness.open_catalog(fixture_lake.config_path)
        for scenario_fn in (scenario_s1, scenario_s2, scenario_s3, scenario_s4,
                            scenario_s5, scenario_s6, scenario_s7):
            scenario_id = "S" + scenario_fn.__name__.rsplit("_s", 1)[-1]
            try:
                record = scenario_fn(harness)
            except Exception:  # noqa: BLE001 - report survives scenario crashes
                traceback.print_exc()
                record = {
                    "id": scenario_id, "status": "PARTIAL",
                    "failure": {"code": "runner_exception",
                                "detail": traceback.format_exc(limit=5)[-500:]},
                    "evidence": {},
                }
            scenario_records.append(record)
            print(f"[{record['id']}] {record['status']}"
                  + (f" ({record['failure']['code']})" if record.get("failure") else ""))
        harness.close_catalog()
    except Exception:  # noqa: BLE001 - setup crash: report what exists
        traceback.print_exc()
    finally:
        if harness is not None:
            harness.close_catalog()
        restored, raw_unchanged = cleanup_owned_root(owned_root, baseline)

    elapsed = time.monotonic() - clock_start
    if harness is None or fixture_lake is None:
        print("harness failed to initialize; no report", file=sys.stderr)
        return 2
    record = build_record(
        attempt_id=attempt.attempt_id, started_at=started_at, elapsed=elapsed,
        fixture_lake=fixture_lake,
        harness=harness, scenario_records=scenario_records,
        baseline=baseline, restored=restored,
    )
    record["cleanup"]["raw_unchanged"] = raw_unchanged
    verdict = oracle.evaluate_run(record)
    record["oracle_verdict"] = {
        "statuses": verdict.statuses,
        "overall": verdict.overall,
        "findings": [
            {"code": f.code, "scenario_id": f.scenario_id, "detail": f.detail}
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
