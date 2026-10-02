"""Pre-push gate: CI-equivalent fast checks BEFORE pushing (root-cause fix).

Runs the CI-quality checks plus its complete unit suite before push:

  1. ruff check src tests/unit tests/contract scripts   (CI WU-1.2)
  2. compileall src scripts tests                        (CI WU-7.1)
  3. config_doctor                                       (CI WU-7.1)
  4. FC-1204 complexity ratchet                          (CI meta-gate)
  5. host-assumption guard                              (CI meta-gate, FC-1307-a)
  6. Full unit suite                                     (CI Unit tests)
  7. The focused high-risk contract tests (including the shared-column reader,
     receipt-envelope, and B10 handoff contracts) plus the gate's own regression tests.

Step 6's meta pair is the fix for the second-order F-B01-9 lesson: on CI run
34751519232 the NEW guard step itself failed `test_writer_freeze.py`, a test
class the local gate never ran - the gate must run the tests that judge the
gate.  Add a new `scripts/*.py` CLI and this step tells you locally whether it
needs the legacy-writer freeze.

Exit non-zero on the first red check. The full unit suite and focused high-risk
contract suite run here so regressions in the affected surfaces block push. CI
still runs the broader contract selection and coverage/mutation ratchets. Local pytest gates use an isolated short basetemp and
UTF-8 subprocess streams so host TEMP ACL/encoding do not create false reds.

Push protocol (see revenue-forecast ci_root_fix.md):
    python tools/pre_push_gate.py   # ~2-3 min
    git push ...
    # self-monitor GitHub Actions until green; on red fix the ROOT CAUSE.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
READER_CONTRACT_FILES = (
    "tests/contract/test_r4b05b_shared_column_readers.py",
    "tests/contract/test_fc905_receipt_envelope.py",
    "tests/contract/test_b10_read_chain.py",
)
CURRENT_CI_REGRESSION_CASES = (
    "tests/contract/test_zr203_reader_rewire.py::test_read_entrypoints_never_construct_catalog_store",
    "tests/contract/test_zr1003_shadow_assertions.py::test_c2_recorded_review_unblocks",
    "tests/contract/test_source_catalog_temp_worker_governance.py::test_owned_temp_worker_helper_detects_test_pid",
    "tests/contract/test_source_catalog_temp_worker_governance.py::test_stop_does_not_touch_unowned_live_workers_or_temporary_files",
)


def _run(
    cmd: list[str],
    label: str,
    timeout: int = 600,
    env_extra: dict | None = None,
    expected_basetemp: Path | None = None,
) -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    if env_extra:
        env.update(env_extra)
    print(f"\n=== {label} ===")
    proc = subprocess.run(
        cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, env=env,
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    tail = output[-3000:]
    returncode = proc.returncode
    if expected_basetemp is not None:
        decisions = []
        for line in output.splitlines():
            if line.startswith("CW-BASETEMP-DECISION "):
                try:
                    decisions.append(json.loads(line.removeprefix("CW-BASETEMP-DECISION ")))
                except json.JSONDecodeError:
                    decisions.append({"invalid_record": line})
        expected = os.path.normcase(os.path.abspath(expected_basetemp))
        if (
            len(decisions) != 1
            or decisions[0].get("relocated") is not False
            or os.path.normcase(os.path.abspath(decisions[0].get("requested_basetemp", ""))) != expected
        ):
            print("pytest basetemp decision was missing, relocated, or unexpected:")
            print("\n".join(line for line in output.splitlines() if line.startswith("CW-BASETEMP-")))
            returncode = returncode or 1
        elif returncode == 0:
            print("pytest basetemp verified: short, repository-local, and not relocated")
    if returncode != 0:
        print(tail)
        print(f"FAILED: {label}")
    else:
        print("ok")
    return returncode


def _run_pytest_gate(cmd: list[str], label: str) -> int:
    temp_root = PROJECT_ROOT / "tmp"
    temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pp", dir=temp_root) as basetemp:
        basetemp_path = Path(basetemp)
        if len(str(basetemp_path)) > 60:
            print(f"FAILED: pytest basetemp exceeds the 60-character limit: {basetemp_path}")
            return 1
        result = _run(
            [*cmd, "--basetemp", basetemp, "-p", "no:cacheprovider"],
            label,
            env_extra={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
            expected_basetemp=basetemp_path,
        )
    if basetemp_path.exists():
        print(f"FAILED: pytest basetemp was not removed: {basetemp_path}")
        return result or 1
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-contract", action="store_true",
                        help="skip the contract-test step (fast lint-only)")
    parser.add_argument(
        "--metadata-reader-contracts-only",
        action="store_true",
        help="run reader contracts and the current CI regression cases",
    )
    args = parser.parse_args(argv)

    gates: list[tuple[list[str], str, dict | None]] = [
        (["ruff", "check", "src", "tests/unit", "tests/contract", "scripts"],
         "ruff (CI WU-1.2 full scope)", None),
        ([sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"],
         "compileall", None),
        ([sys.executable, "scripts/config_doctor.py"],
         "config_doctor (CI WU-7.1)", None),
        ([sys.executable, "-m", "pytest",
          "tests/contract/test_fc1204_complexity_ratchet.py", "-q"],
         "FC-1204 complexity ratchet (CI meta-gate)", None),
        ([sys.executable, "scripts/host_assumption_guard.py"],
         "host assumption guard (FC-1307-a; the class that broke CI in F-B01-9)", None),
        ([sys.executable, "-m", "pytest", "tests/unit", "-q", "--tb=short"],
         "unit tests (CI Unit tests)", None),
    ]
    focused_contract_gate = (
            [sys.executable, "-m", "pytest", "-q", "--tb=short", "--timeout=180",
             "tests/contract/test_source_catalog_section_extractor.py",
             "tests/contract/test_fc906a_producer_binding_metadata.py",
             "tests/contract/test_legacy_observation.py",
             "tests/contract/test_zr506_section_chunk_fact.py",
             "tests/contract/test_r4b05b_shared_column_readers.py",
             "tests/contract/test_fc905_receipt_envelope.py",
             "tests/contract/test_b10_read_chain.py",
             "tests/unit/test_writer_freeze.py",
             "tests/contract/test_fc1307_host_assumption_gate.py",
             *CURRENT_CI_REGRESSION_CASES],
            "focused contracts, recent CI regressions, and gate regression tests",
            None,
    )
    metadata_reader_contract_gate = (
        [sys.executable, "-m", "pytest", "-q", "--tb=short", "--timeout=180",
         *READER_CONTRACT_FILES, *CURRENT_CI_REGRESSION_CASES],
        "reader contracts plus the current CI regression cases",
        None,
    )
    if args.metadata_reader_contracts_only:
        gates = [metadata_reader_contract_gate]
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


