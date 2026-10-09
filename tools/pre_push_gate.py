"""Local validation helpers for the GitHub CI fast gate.

The push hook adds affected unit files to the same CI contract smoke set.
GitHub Actions runs every unit test. Run this script without arguments for the
optional full local gate; all portable Contract tests remain available by
running pytest directly.

Run without flags for the optional full local validation suite:

  1. ruff check src tests/unit tests/contract scripts   (CI WU-1.2)
  2. compileall src scripts tests                        (CI WU-7.1)
  3. config_doctor                                       (CI WU-7.1)
  4. host-assumption guard                              (CI meta-gate, FC-1307-a)
  5. Full unit suite                                     (CI Unit tests)
  6. The current narrative selection, source-hash replay, receipt-envelope,
     and read-chain tests plus the gate's own regression tests.

The unit suite includes the second-order F-B01-9 regression: on CI run
34751519232 the NEW guard step itself failed `test_writer_freeze.py`, a test
class the local gate never ran - the gate must run the tests that judge the
gate.  Add a new `scripts/*.py` CLI and this step tells you locally whether it
needs the legacy-writer freeze.

Exit non-zero on the first red check. The full local run is useful before a
large integration but is not part of every push. GitHub CI runs all Unit and
the curated Contract smoke set; full Contract tests, full-tree coverage and
coverage are manual. Complexity is an optional diagnostic report, not a gate.
Local pytest gates use an isolated short basetemp and UTF-8 subprocess streams
so host TEMP ACL/encoding do not create false reds.

The small hook path is intentionally narrower than this full local gate.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.changed_unit_tests import changed_paths, select_unit_tests  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GIT_REPOSITORY_CONTEXT = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX",
    "GIT_NAMESPACE", "GIT_QUARANTINE_PATH", "GIT_SHALLOW_FILE",
)
CURRENT_CI_REGRESSION_CASES = (
    "tests/unit/test_automation_migrations.py::test_m14_classification_uses_one_snapshot_during_concurrent_init",
    "tests/contract/test_zr203_reader_rewire.py::test_read_entrypoints_never_construct_catalog_store",
    "tests/contract/test_zr1003_shadow_assertions.py::test_c2_recorded_review_is_diagnostic_metadata",
    "tests/contract/test_zr1006_broker_cohort.py::test_c2_ramp_1_to_3_to_7",
    "tests/contract/test_source_catalog_temp_worker_governance.py::test_owned_temp_worker_helper_detects_test_pid",
    "tests/contract/test_source_catalog_temp_worker_governance.py::test_stop_does_not_touch_unowned_live_workers_or_temporary_files",
)
FAST_CONTRACT_CASES = (
    "tests/unit/test_runtime_dependencies.py::test_ci_requirements_include_declared_runtime_dependencies",
    *CURRENT_CI_REGRESSION_CASES,
    "tests/unit/test_narrative_evidence.py::test_financial_table_rows_are_dropped_but_business_rows_are_selected",
    "tests/unit/test_narrative_evidence.py::test_numbered_project_rationale_heading_survives_a_tight_budget",
    "tests/unit/test_narrative_transport_contracts.py::test_frozen_producer_golden_contract_and_hash_bindings",
    "tests/contract/test_fc905_receipt_envelope.py::test_pi03_no_review_is_explicit_not_reviewed",
    "tests/unit/test_narrative_retrieval.py::test_resolver_fails_closed_when_raw_source_hash_changes",
    "tests/contract/test_b10_read_chain.py::test_b10_scan_is_not_vacuous",
)


def _run(
    cmd: list[str],
    label: str,
    timeout: int = 600,
    env_extra: dict | None = None,
) -> int:
    env = dict(os.environ)
    # Git hooks export their checkout context. Tests create their own repos;
    # their subprocesses must resolve Git from their own cwd, as they do in CI.
    for name in GIT_REPOSITORY_CONTEXT:
        env.pop(name, None)
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    if env_extra:
        env.update(env_extra)
    print(f"\n=== {label} ===")
    proc = subprocess.run(
        cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, env=env,
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    returncode = proc.returncode
    if returncode != 0:
        print(output)  # Keep the first failing node, not just the report's tail.
        print(f"FAILED: {label}")
    else:
        summary = next((line for line in reversed(output.splitlines()) if "passed" in line), "ok")
        print(summary)
    return returncode


def _run_pytest_gate(cmd: list[str], label: str) -> int:
    # Scratch belongs to this invocation, independent of checkout depth. Pytest's
    # existing Windows fallback handles path placement; its log is diagnostic.
    # TemporaryDirectory restores this owned root on success, failure or timeout.
    with tempfile.TemporaryDirectory(prefix="cwpp-") as basetemp:
        return _run(
            [*cmd, "--basetemp", basetemp, "-p", "no:cacheprovider"],
            label,
            env_extra={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"},
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-contract", action="store_true",
                        help="skip the contract-test step (fast lint-only)")
    parser.add_argument(
        "--push-checks", action="store_true",
        help="read Git push ref updates from stdin; run affected units and contract smoke once",
    )
    parser.add_argument(
        "--fast-contracts-only",
        action="store_true",
        help="run the curated portable contract smoke set used by CI and the push hook",
    )
    parser.add_argument(
        "--junitxml",
        help="write a JUnit report for the fast contract set",
    )
    args = parser.parse_args(argv)

    gates: list[tuple[list[str], str, dict | None]] = [
        (["ruff", "check", "src", "tests/unit", "tests/contract", "scripts"],
         "ruff (CI WU-1.2 full scope)", None),
        ([sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"],
         "compileall", None),
        ([sys.executable, "scripts/config_doctor.py"],
         "config_doctor (CI WU-7.1)", None),
        ([sys.executable, "scripts/host_assumption_guard.py"],
         "host assumption guard (FC-1307-a; the class that broke CI in F-B01-9)", None),
        ([sys.executable, "-m", "pytest", "tests/unit", "-q", "--tb=short"],
         "unit tests (CI Unit tests)", None),
    ]
    focused_contract_gate = (
            [sys.executable, "-m", "pytest", "-q", "--tb=short", "--timeout=180",
             "tests/unit/test_narrative_evidence.py",
             "tests/unit/test_narrative_transport_contracts.py",
             "tests/contract/test_legacy_observation.py",
             "tests/contract/test_zr506_section_chunk_fact.py",
             "tests/unit/test_narrative_retrieval.py",
             "tests/contract/test_fc905_receipt_envelope.py",
             "tests/contract/test_b10_read_chain.py",
             "tests/unit/test_writer_freeze.py",
             "tests/contract/test_fc1307_host_assumption_gate.py",
             *CURRENT_CI_REGRESSION_CASES],
            "focused contracts, recent CI regressions, and gate regression tests",
            None,
    )
    fast_contract_gate = (
        [sys.executable, "-m", "pytest", "-q", "--tb=short", "--timeout=180",
         *FAST_CONTRACT_CASES],
        "CI fast contract smoke set",
        None,
    )
    if args.push_checks:
        selected, reason = select_unit_tests(PROJECT_ROOT, changed_paths(PROJECT_ROOT, sys.stdin.read()))
        print(f"Push unit scope: {reason} ({len(selected)} paths)")
        cases = [*selected, *(case for case in FAST_CONTRACT_CASES
                 if not any(case.split('::')[0] == path or case.startswith(path + '/') for path in selected))]
        gates = [([sys.executable, "-m", "pytest", "-q", "--tb=short", "--timeout=180", *cases],
                  "affected units and CI contract smoke", None)]
    elif args.fast_contracts_only:
        fast_gate = fast_contract_gate
        if args.junitxml:
            fast_gate = (
                [*fast_contract_gate[0], f"--junitxml={args.junitxml}"],
                fast_contract_gate[1],
                fast_contract_gate[2],
            )
        gates = [fast_gate]
    elif not args.skip_contract:
        gates.append(focused_contract_gate)

    for cmd, label, env_extra in gates:
        if "-m" in cmd and "pytest" in cmd:
            rc = _run_pytest_gate(cmd, label)
        else:
            rc = _run(cmd, label, env_extra=env_extra)
        if rc != 0:
            print(f"\nGATE RED at: {label}\nFix the root cause (see "
                  f"revenue-forecast ci_root_fix.md), do not bypass.")
            return rc
    print("\npre-push gate GREEN — safe to push (then self-monitor CI).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


