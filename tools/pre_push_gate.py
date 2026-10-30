"""Local validation helpers for the GitHub CI fast gate.

Three bounded layers share one script. Commits keep static checks (pre-commit).
Daily pushes run the affected unit files plus the shared fast contract set
once, and defer everything else to CI; a wide, dynamic or unknown scope runs
the fast contract set alone and says so. A proven non-runtime range starts no
test process and reports tests_not_run. The full local suite below stays an
explicit decision and is never started implicitly by a push. A green fast pass
only proves the scope that actually ran (`local_fast_pass`), never the whole
project (`full_validation_pending` covers the rest).

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

Exit non-zero on the first red check, on a failed child launch, and on any
runner exception: a push must never be waved through because the check could
not run. The full local run is useful before a large integration but is not
part of every push. GitHub CI runs all Unit and the curated Contract smoke
set; full Contract tests, full-tree coverage and coverage are manual.
Complexity is an optional diagnostic report, not a gate. Local pytest gates
use an isolated short basetemp and UTF-8 subprocess streams so host
TEMP ACL/encoding do not create false reds.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from company_wiki._bounded_process import (  # noqa: E402
    ChildFailed, ChildTimeout, OutputLimitExceeded, TransportError, run_bounded,
)
from tools.changed_unit_tests import changed_paths, select_unit_tests  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Count a closed list as well as the literal full-suite recommendation. A
# hundreds-file list is still a broad validation run, not daily feedback.
DAILY_PUSH_MAX_AFFECTED_TARGETS = 32
# The normal curated smoke took ~52s for 154 cases. Three minutes allows
# affected unit work while keeping daily feedback bounded; full mode keeps 600s.
DAILY_PUSH_TIMEOUT_SECONDS = 180
DAILY_PUSH_LABEL_PREFIX = "daily push fast feedback:"
STDOUT_CAP_BYTES = 4 * 1024 * 1024
STDERR_CAP_BYTES = 512 * 1024
GIT_REPOSITORY_CONTEXT = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX",
    "GIT_NAMESPACE", "GIT_QUARANTINE_PATH", "GIT_SHALLOW_FILE",
)
CURRENT_CI_REGRESSION_CASES = (
    # CI 41019504113: PDF and TXT producers evolve independently. Three
    # in-process witnesses catch version-coupled fixtures without a full suite.
    "tests/unit/test_narrative_english_business_recall.py::test_recall_semantics_are_versioned_and_legacy_txt_locators_stay_unchanged",
    "tests/unit/test_narrative_verify_handler.py::test_verify_handler_transcript_replays_bytes_without_provider_policy",
    "tests/unit/test_official_json_projection_generation.py::test_old_raw_manifest_retains_exact_canonical_contract",
    # CI 41056460382: reject malformed JSON protocol identifiers through the
    # existing named boundary, even when a wide push defers other unit files.
    "tests/unit/test_narrative_protocol_identity_shapes.py::test_protocol_lookup_does_not_hash_non_string_json",
    "tests/unit/test_automation_migrations.py::test_m14_classification_uses_one_snapshot_during_concurrent_init",
    "tests/contract/test_zr203_reader_rewire.py::test_read_entrypoints_never_construct_catalog_store",
    "tests/contract/test_zr1003_shadow_assertions.py::test_c2_recorded_review_is_diagnostic_metadata",
    "tests/contract/test_zr1006_broker_cohort.py::test_c2_ramp_1_to_3_to_7",
    "tests/contract/test_source_catalog_temp_worker_governance.py::test_owned_temp_worker_helper_detects_test_pid",
    "tests/contract/test_source_catalog_temp_worker_governance.py::test_stop_does_not_touch_unowned_live_workers_or_temporary_files",
)
FAST_CONTRACT_CASES = (
    # Fast owner/history checks; the three-repository CLI stays at integration.
    "tests/unit/test_local_budget_observation.py::test_read_charge_reports_a_rejected_tail_separately_from_accepted_bytes",
    "tests/contract/test_local_prepare_failure_boundaries.py::test_real_discovery_completed_write_survives_later_unknown_failure",
    # Small OCR resource regressions; real model replay remains a major-node test.
    'tests/document_normalization/test_ocr_region_recovery.py::test_roi_budget_preflight_never_calls_rejected_renderer',
    'tests/document_normalization/test_ocr_region_recovery.py::test_rejected_render_attempt_keeps_reserved_budget',
    'tests/document_normalization/test_ocr_region_recovery.py::test_upscale_preflight_accounts_for_64m_canvas_without_allocating_it',
    'tests/document_normalization/test_isolated_ocr.py::test_noncooperative_native_stops_at_product_deadline[gil-block-inference-infer]',
    # Same fd0-lock invariant via Python's supported CRT wrapper. The direct
    # Windows ctypes ABI matrix stays in the full OCR major-node suite.
    'tests/document_normalization/test_isolated_ocr.py::test_native_stdin_probe_does_not_deadlock_liveness_monitor[preflight]',
    'tests/document_normalization/test_isolated_ocr.py::test_narrative_default_proxy_carries_deadline_without_starting_native',

    "tests/integration/test_m3_official_json_acceptance.py",
    "tests/unit/test_runtime_dependencies.py::test_ci_requirements_include_declared_runtime_dependencies",
    *CURRENT_CI_REGRESSION_CASES,
    "tests/contract/test_narrative_output_plan.py",
    "tests/contract/test_summary_group_coverage.py",
    "tests/contract/test_official_transcript_layouts.py",
    "tests/contract/test_transcript_speaker_affiliation.py",
    "tests/contract/test_source_scope_qualification.py",
    # In-process owner/projection controls (~2s); full cross-repo CLI replay is
    # an explicit major-node suite, not repeated on every push.
    "tests/contract/test_narrative_availability.py::test_one_verified_original_buffer_one_owner_lookup_no_new_fact_writer",
    "tests/contract/test_narrative_availability.py::test_projected_two_parents_cannot_borrow_one_raw_proof",
    "tests/unit/test_narrative_evidence.py::test_financial_table_rows_are_dropped_but_business_rows_are_selected",
    "tests/unit/test_narrative_evidence.py::test_numbered_project_rationale_heading_survives_a_tight_budget",
    "tests/unit/test_narrative_transport_contracts.py::test_frozen_producer_golden_contract_and_hash_bindings",
    "tests/contract/test_fc905_receipt_envelope.py::test_pi03_no_review_is_explicit_not_reviewed",
    "tests/unit/test_narrative_retrieval.py::test_resolver_fails_closed_when_raw_source_hash_changes",
    "tests/contract/test_b10_read_chain.py::test_b10_scan_is_not_vacuous",
    # Reused receipts retain one source-owner read for each operation.
    "tests/unit/test_shared_reading_cache_precheck.py::test_reuse_final_receipt_has_one_owner_read_per_operation",
    "tests/unit/test_shared_reading_cache_precheck.py::test_new_operation_rejects_changed_reused_original_before_new_fee",
)


def _print_output(value: str) -> None:
    """A legacy console must not erase a child's diagnostic or its exit code."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(value.encode(encoding, errors="backslashreplace").decode(encoding))


def _run(
    cmd: list[str],
    label: str,
    timeout: float = 600,
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
    _print_output(f"\n=== {label} ===")
    try:
        result = run_bounded(
            cmd, cwd=str(PROJECT_ROOT), timeout_seconds=timeout, env=env,
            stdout_cap_bytes=STDOUT_CAP_BYTES, stderr_cap_bytes=STDERR_CAP_BYTES,
        )
        stdout, stderr, returncode = result["stdout"], result["stderr"], 0
    except ChildFailed as exc:
        stdout, stderr, returncode = exc.stdout, exc.stderr, exc.returncode
    except TransportError as exc:
        # The owner kills and reaps its entire tree before returning. Preserve
        # progress and cleanup diagnostics without making a transport red green.
        for stream in (getattr(exc, "stdout", b""), getattr(exc, "stderr", b"")):
            if stream:
                _print_output(stream.decode("utf-8", errors="replace")
                              if isinstance(stream, bytes) else stream)
        for note in getattr(exc, "__notes__", ()):
            _print_output(note)
        if isinstance(exc, ChildTimeout):
            _print_output(f"FAILED: {label} (timeout after {timeout}s)")
            return 124
        if isinstance(exc, OutputLimitExceeded):
            _print_output(f"FAILED: {label} (output truncated: {exc}; "
                          f"stdout cap={STDOUT_CAP_BYTES}, stderr cap={STDERR_CAP_BYTES} bytes)")
            return 125
        _print_output(f"FAILED: {label} ({type(exc).__name__}: {exc})")
        return 1
    output = "\n".join(stream.decode("utf-8", errors="replace")
                       if isinstance(stream, bytes) else str(stream or "")
                       for stream in (stdout, stderr))
    if returncode != 0:
        _print_output(output)  # Keep the first failing node, not just the tail.
        _print_output(f"FAILED: {label}")
    else:
        summary = next((line for line in reversed(output.splitlines()) if "passed" in line), "ok")
        _print_output(summary)
        if "--durations=15" in cmd:
            durations = next((index for index, line in enumerate(output.splitlines())
                              if "slowest 15 durations" in line), None)
            if durations is not None:
                _print_output("\n".join(output.splitlines()[durations:]))
    return returncode


def _explicit_test_paths(cmd: list[str]) -> int:
    """Count explicit pytest targets; a wide affected set needs the same bound."""
    return sum(1 for item in cmd if item.startswith("tests/"))


def _scratch_candidate_roots() -> list[str]:
    """Bounded scratch-root candidates, shortest first.

    The Git hook's process may have restricted access, so no candidate is
    trusted here: each is verified by actually creating the owned scratch
    (see _open_scratch). The environment's own temp hints come first, the
    standard system temp directory backs them up, and PROJECT_ROOT stays as
    the in-checkout fallback for hosts where nothing outside is writable.
    Keeping the list ordered by length stops checkout depth from eating the
    child's path budget.
    """
    env_roots = [os.environ.get(name) for name in ("TEMP", "TMP", "TMPDIR")]
    candidates = [root for root in env_roots if root]
    if not candidates:
        candidates.append(tempfile.gettempdir())
    candidates.append(str(PROJECT_ROOT))
    return sorted(dict.fromkeys(candidates), key=lambda root: (len(root), root))


def _open_scratch(candidates: list[str]) -> tempfile.TemporaryDirectory:
    """Create this invocation's owned scratch at the first usable candidate.

    Every candidate is verified once with a real directory and one probe
    file; a rejected attempt is recorded and never retried. When no candidate
    is usable the error names every attempt, so a red gate explains itself
    instead of failing deep inside a child.
    """
    attempts: list[str] = []
    for root in candidates:
        try:
            scratch = tempfile.TemporaryDirectory(prefix="cwpp-", dir=root)
        except OSError as exc:
            attempts.append(f"{root}: cannot create scratch ({exc})")
            continue
        try:
            probe = Path(scratch.name) / "write-probe"
            with probe.open("wb") as stream:
                stream.write(b"probe")
            probe.unlink()
        except OSError as exc:
            scratch.cleanup()
            attempts.append(f"{root}: scratch not writable ({exc})")
            continue
        return scratch
    raise RuntimeError(
        "no writable scratch root for the pytest gate; tried:\n  "
        + "\n  ".join(attempts))


def _run_pytest_gate(cmd: list[str], label: str) -> int:
    # Scratch belongs to this invocation, is verified writable before any
    # child starts, and stays path-bounded regardless of checkout depth.
    # Pytest's existing Windows fallback handles path placement; its log is
    # diagnostic. Cleanup covers the success, failure and timeout paths.
    # Full bootstrap progress is captured (not streamed on successful pushes).
    # On timeout it identifies the last test; successful output lists slow cases.
    daily = label.startswith(DAILY_PUSH_LABEL_PREFIX)
    if daily:
        # Capture the last running node on timeout and slow successful cases.
        cmd = [*cmd, "-vv", "--durations=15"]
    if "tests/unit" in cmd or _explicit_test_paths(cmd) > 200:
        # xdist is already a declared test dependency. Each worker has its own
        # interpreter and pytest temp tree; file scheduling keeps module-level
        # fixtures together. Retain the full collection and the same timeout.
        # An explicitly requested wide file set gets the same two workers as
        # the full unit suite. Daily policy defers wide recommendations to CI.
        # Narrow changed-file and contract gates avoid this startup overhead.
        cmd = [*cmd, "-n", "2", "--dist=loadfile", "-vv", "--durations=15"]
    # Windows SQLite and tempfile consult TEMP/TMP independently of pytest's
    # --basetemp. Keep all three roots inside this invocation's owned scratch:
    # the host TEMP may be inaccessible to the Git hook's restricted process,
    # which otherwise turns a large WAL write into SQLITE_CANTOPEN mid-test.
    scratch = _open_scratch(_scratch_candidate_roots())
    try:
        owned_temp = str(Path(scratch.name).resolve())
        return _run(
            [*cmd, "--basetemp", scratch.name, "-p", "no:cacheprovider"],
            label,
            timeout=DAILY_PUSH_TIMEOUT_SECONDS if daily else 600,
            env_extra={
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "TEMP": owned_temp,
                "TMP": owned_temp,
                "TMPDIR": owned_temp,
                "SQLITE_TMPDIR": owned_temp,
            },
        )
    finally:
        scratch.cleanup()


def _push_targets(selected: list[str]) -> tuple[list[str], str]:
    """Decide what a daily push runs; a full recommendation defers to CI.

    The selection layer may still recommend the whole unit suite for wide,
    dynamic, configuration or unknown scopes. That recommendation stays with
    CI: silently starting all unit tests on every push is the regression this
    policy exists to prevent. A trusted empty selection has no runtime targets;
    other pushes run the shared fast contract set once, deduplicated against
    whole-file selections. A small explainable affected set keeps its full files.
    """
    selected = list(dict.fromkeys(selected))
    if not selected:
        return [], "no runtime test targets in the classified push range"
    if "tests/unit" in selected:
        return list(FAST_CONTRACT_CASES), "full unit suite recommendation deferred to CI"
    if any(not target.split("::", 1)[0].endswith(".py") for target in selected):
        return list(FAST_CONTRACT_CASES), "unbounded test directory recommendation deferred to CI"
    # The selector also describes changed integration/root test modules. Those
    # recommendations belong to CI or a separate major-node integration run;
    # only affected units may expand the fixed daily contract inventory.
    units = [target for target in selected
             if target.startswith("tests/unit/")
             and ".." not in target.split("::", 1)[0].split("/")
             and "\\" not in target.split("::", 1)[0]]
    nonunit_count = len(selected) - len(units)
    selected = units
    if len(selected) > DAILY_PUSH_MAX_AFFECTED_TARGETS:
        return list(FAST_CONTRACT_CASES), f"wide affected set ({len(selected)} targets) deferred to CI"
    whole_files = {path for path in selected if "::" not in path}
    targets = list(selected)
    # A whole-file target covers every fast node in that file. A node-id
    # target covers only itself, so keep sibling fast nodes and remove only
    # exact duplicate node IDs.
    targets.extend(case for case in FAST_CONTRACT_CASES
                   if case.split("::")[0] not in whole_files and case not in targets)
    deferred = f"tests/unit outside the {len(targets)} ran targets deferred to CI"
    if nonunit_count:
        deferred += (f"; {nonunit_count} non-unit recommendation(s) deferred to CI "
                     "or separate major-node integration acceptance")
    return targets, deferred


def _dispatch_gate(cmd: list[str], label: str, env_extra: dict | None = None) -> int:
    """Run one gate and never let a launch failure look like a green check."""
    try:
        if "-m" in cmd and "pytest" in cmd:
            return _run_pytest_gate(cmd, label)
        return _run(cmd, label, env_extra=env_extra)
    except Exception as exc:
        _print_output(f"FAILED: {label} ({type(exc).__name__}: {exc})")
        return 1


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
        selected, reason = select_unit_tests(
            PROJECT_ROOT, changed_paths(PROJECT_ROOT, sys.stdin.read()))
        targets, deferred = _push_targets(selected)
        if not targets:
            # pytest with an empty target list would collect the entire project.
            # Only the existing range classifier can produce this empty scope;
            # unknown/configuration ranges still select the contract smoke set.
            print(f"Push scope: {reason}; planned 0 runtime targets. "
                  f"tests_not_run: {deferred}; CI policy unchanged.")
            return 0
        print(f"Push scope: {reason}; planned {len(targets)} target(s); "
              f"full_validation_pending: {deferred}.")
        print("Planned test targets:", *targets, sep="\n  ")
        label = (
            f"{DAILY_PUSH_LABEL_PREFIX} affected unit tests and CI contract smoke"
            if any(target not in FAST_CONTRACT_CASES for target in targets)
            else f"{DAILY_PUSH_LABEL_PREFIX} CI contract smoke (no affected unit files)"
        )
        code = _dispatch_gate(
            [sys.executable, "-m", "pytest", "-q", "--tb=short", "--timeout=180", *targets],
            label)
        if code:
            print("\nPUSH CHECKS RED — fix the failing phase; do not bypass.")
        else:
            print("\nPush fast gate GREEN (local_fast_pass for the ran scope only); "
                  "full_validation_pending — CI still runs the full suites.")
        return code
    if args.fast_contracts_only:
        fast_gate = fast_contract_gate
        if args.junitxml:
            fast_gate = (
                [*fast_gate[0], f"--junitxml={args.junitxml}"],
                fast_gate[1],
                fast_gate[2],
            )
        gates = [fast_gate]
        green_message = ("fast contract gate GREEN (local_fast_pass for the curated "
                         "set); full_validation_pending — full suites stay with CI "
                         "and the explicit full local mode.")
    else:
        if not args.skip_contract:
            gates.append(focused_contract_gate)
        green_message = ("full local gate GREEN (contracts skipped by --skip-contract); "
                         "this was not a full validation run."
                         if args.skip_contract else
                         "full local gate GREEN — full validation ran locally; self-monitor CI.")

    for cmd, label, env_extra in gates:
        rc = _dispatch_gate(cmd, label, env_extra)
        if rc != 0:
            print(f"\nGATE RED at: {label}\nFix the root cause (see "
                  f"revenue-forecast ci_root_fix.md), do not bypass.")
            return rc
    print(f"\n{green_message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


