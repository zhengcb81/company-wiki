"""One policy owner for daily feedback, CI remainder and explicit full mode.

Optional AST selection is tested separately. Real Git hook E2Es and bounded
process/scratch tests retain their own behavior owners; they do not redefine
which test inventory daily pushes must share with CI.
"""
from io import StringIO
from pathlib import Path
import sys

import pytest
import yaml

from tools import changed_unit_tests
from tools import pre_push_gate as gate


RUNTIME_RANGES = [
    {"src/pkg/core.py"}, {"config/input.json"}, {"tests/unit/test_explicit.py"},
    {f"tests/unit/test_changed_{index}.py" for index in range(379)},
    {"README.md", "src/pkg/core.py"}, {"unknown/runtime.txt"}, {"README.js"}, None,
]
DOCUMENT_RANGES = [set(), {"docs/usage.md"},
    {"README.md", "docs/plans/run/probe.py", ".planning/run/result.json"}]


def _push(monkeypatch, changes):
    monkeypatch.setattr(gate.sys, "stdin", StringIO("fixture push range"))
    monkeypatch.setattr(gate, "changed_paths", lambda *_: changes)


def _targets(command):
    return [part for part in command if part.startswith("tests/")]


def test_daily_and_ci_inventories_have_distinct_responsibilities():
    daily = gate.DAILY_PUSH_CASES
    assert len(daily) == len(set(daily))
    assert all("::" in node for node in daily)
    assert set(daily) < set(gate.FAST_CONTRACT_CASES)
    for name in (
        "test_reuse_final_receipt_has_one_owner_read_per_operation",
        "test_new_operation_rejects_changed_reused_original_before_new_fee",
        "test_resolver_fails_closed_when_raw_source_hash_changes",
        "test_protocol_lookup_does_not_hash_non_string_json",
    ):
        assert sum(node.endswith("::" + name) for node in daily) == 1
    # Full Unit already covers its own files. CI's separate remainder keeps
    # the full curated contract files, including slower OCR/publication work.
    assert len(gate.CI_CONTRACT_CASES) == len(set(gate.CI_CONTRACT_CASES))
    assert set(gate.CI_CONTRACT_CASES) == {
        node for node in gate.FAST_CONTRACT_CASES if not node.startswith("tests/unit/")}
    assert not any(node.startswith("tests/unit/") for node in gate.CI_CONTRACT_CASES)
    for path in (
        "tests/contract/test_layer_public_boundaries.py",
        "tests/contract/test_source_catalog_independent.py",
        "tests/contract/test_announcement_collector.py",
        "tests/contract/test_narrative_pdf_replay_once.py::test_native_pdf_entry_hashes_the_original_once",
        "tests/contract/test_narrative_pdf_replay_once.py::test_native_html_entry_hashes_the_original_once",
        "tests/contract/test_source_acquisition_verified_reuse.py::test_exact_local_reuse_streams_once_per_request",
        "tests/contract/test_source_export_cli.py::test_v1_cli_replays_nested_unicode_path_and_round_trips_the_same_wire",
        "tests/document_normalization/test_pptx.py::TestMediaAndGaps::test_mixed_slide_preserves_positive_replay_but_cannot_prove_empty_selection",
        "tests/contract/test_narrative_output_plan.py",
        "tests/contract/test_summary_group_coverage.py",
        "tests/contract/test_official_transcript_layouts.py",
        "tests/contract/test_source_scope_qualification.py",
    ):
        assert path in gate.CI_CONTRACT_CASES
    assert "tests/contract/test_fresh_cache_behavior_receipts.py" not in gate.CI_CONTRACT_CASES
    # These real OCR-resource regressions stay in the remote contract phase,
    # rather than making every local push execute their expensive native paths.
    required_ocr = {
        'tests/document_normalization/test_ocr_region_recovery.py::test_roi_budget_preflight_never_calls_rejected_renderer',
        'tests/document_normalization/test_ocr_region_recovery.py::test_rejected_render_attempt_keeps_reserved_budget',
        'tests/document_normalization/test_ocr_region_recovery.py::test_upscale_preflight_accounts_for_64m_canvas_without_allocating_it',
        'tests/document_normalization/test_isolated_ocr.py::test_noncooperative_native_stops_at_product_deadline[gil-block-inference-infer]',
        'tests/document_normalization/test_isolated_ocr.py::test_native_stdin_probe_does_not_deadlock_liveness_monitor[preflight]',
        'tests/document_normalization/test_isolated_ocr.py::test_narrative_default_proxy_carries_deadline_without_starting_native',
    }
    assert required_ocr <= set(gate.CI_CONTRACT_CASES)


@pytest.mark.parametrize("changes", RUNTIME_RANGES)
def test_daily_runtime_config_or_unknown_runs_only_fixed_scope_once(monkeypatch, capsys, changes):
    _push(monkeypatch, changes)
    def no_graph(*_args, **_kwargs):
        pytest.fail("daily policy must not scan or build an AST impact graph")
    monkeypatch.setattr(changed_unit_tests, "select_unit_tests", no_graph)
    monkeypatch.setattr(Path, "rglob", no_graph)
    observed = []
    monkeypatch.setattr(gate, "_run_pytest_gate", lambda cmd, label: observed.append((cmd, label)) or 0)
    assert gate.main(["--push-checks"]) == 0
    assert len(observed) == 1
    command, label = observed[0]
    assert _targets(command) == list(gate.DAILY_PUSH_CASES)
    assert len(_targets(command)) == len(set(_targets(command)))
    assert "tests/unit" not in command
    assert label.startswith(gate.DAILY_PUSH_LABEL_PREFIX)
    output = capsys.readouterr().out
    assert "local_fast_pass for fixed smoke only" in output
    assert "change-specific tests are the author's responsibility" in output
    assert "full_validation_pending" in output and "safe to push" not in output
    if changes is None:
        assert "unknown push range" in output


@pytest.mark.parametrize("changes", DOCUMENT_RANGES)
def test_proven_documentation_range_starts_zero_tests(monkeypatch, capsys, changes):
    _push(monkeypatch, changes)
    monkeypatch.setattr(gate, "_run_pytest_gate", lambda *_: pytest.fail("documentation must not collect tests"))
    assert gate.main(["--push-checks"]) == 0
    output = capsys.readouterr().out
    assert "tests_not_run" in output and "planned 0" in output
    assert "local_fast_pass" not in output


@pytest.mark.parametrize("returncode", [0, 1, 7, 124, 125])
def test_daily_reports_pass_only_after_its_single_child_succeeds(monkeypatch, capsys, returncode):
    _push(monkeypatch, {"config/runtime.yaml"})
    calls = []
    def execute(command, label):
        before = capsys.readouterr().out
        assert "planned" in before and "local_fast_pass" not in before
        calls.append(command)
        assert _targets(command) == list(gate.DAILY_PUSH_CASES)
        return returncode
    monkeypatch.setattr(gate, "_run_pytest_gate", execute)
    assert gate.main(["--push-checks"]) == returncode
    assert len(calls) == 1
    output = capsys.readouterr().out
    assert ("local_fast_pass" in output) is (returncode == 0)
    assert ("PUSH CHECKS RED" in output) is (returncode != 0)


def test_failed_child_launch_is_not_a_green_push(monkeypatch, capsys):
    _push(monkeypatch, None)
    def broken(*_args):
        raise OSError("synthetic spawn failure")
    monkeypatch.setattr(gate, "_run_pytest_gate", broken)
    assert gate.main(["--push-checks"]) == 1
    output = capsys.readouterr().out
    assert "synthetic spawn failure" in output and "local_fast_pass" not in output


@pytest.mark.parametrize("junit", [None, "fixture-results.xml"])
def test_ci_contract_phase_runs_only_the_nonunit_remainder_once(monkeypatch, junit):
    observed = []
    monkeypatch.setattr(gate, "_dispatch_gate", lambda cmd, *_args: observed.append(cmd) or 0)
    argv = ["--fast-contracts-only"] + (["--junitxml", junit] if junit else [])
    assert gate.main(argv) == 0
    assert len(observed) == 1
    assert _targets(observed[0]) == list(gate.CI_CONTRACT_CASES)
    assert "tests/unit" not in observed[0]
    if junit:
        assert observed[0].count("--junitxml=" + junit) == 1


def test_explicit_full_mode_runs_all_stages_and_only_one_unit_collection(monkeypatch, capsys):
    observed = []
    monkeypatch.setattr(gate, "_dispatch_gate", lambda cmd, label, *_args: observed.append((cmd, label)) or 0)
    assert gate.main([]) == 0
    assert [label for _, label in observed] == [
        "ruff (CI WU-1.2 full scope)", "compileall", "config_doctor (CI WU-7.1)",
        "host assumption guard (FC-1307-a; the class that broke CI in F-B01-9)",
        "unit tests (CI Unit tests)",
        "focused contracts, recent CI regressions, and gate regression tests",
    ]
    commands = [cmd for cmd, _ in observed if "pytest" in cmd]
    assert len(commands) == 2 and sum("tests/unit" in cmd for cmd in commands) == 1
    assert not any(node.startswith("tests/unit/") for node in commands[-1])
    assert "tests/contract/test_b10_read_chain.py" in commands[-1]
    output = capsys.readouterr().out
    assert "full local gate GREEN" in output and "local_fast_pass" not in output
    assert "safe to push" not in output


@pytest.mark.parametrize("daily", [True, False])
def test_total_deadline_worker_scope_and_owned_scratch_remain_real(tmp_path, monkeypatch, daily):
    monkeypatch.setattr(gate, "PROJECT_ROOT", tmp_path)
    # Observe the actual freshly owned short scratch selected by its owner.
    # A long pytest fixture cannot be forced past the real Windows path budget.
    owned = []
    open_scratch = gate._open_scratch
    def capture_scratch(candidates):
        scratch = open_scratch(candidates)
        owned.append(Path(scratch.name))
        assert owned[-1].is_dir()
        return scratch
    monkeypatch.setattr(gate, "_open_scratch", capture_scratch)
    observed = []
    monkeypatch.setattr(gate, "_run", lambda cmd, label, **kwargs: observed.append((cmd, kwargs)) or 0)
    targets = list(gate.DAILY_PUSH_CASES) if daily else ["tests/unit"]
    label = gate.DAILY_PUSH_LABEL_PREFIX + " fixture" if daily else "unit tests"
    assert gate._run_pytest_gate([sys.executable, "-m", "pytest", *targets], label) == 0
    command, options = observed[0]
    assert options["timeout"] == (gate.DAILY_PUSH_TIMEOUT_SECONDS if daily else 600)
    assert "-vv" in command and "--durations=15" in command
    assert all(target in command for target in targets)
    assert ("-n" in command) is (not daily)
    if not daily:
        assert command[command.index("-n") + 1] == "2"
    assert len(owned) == 1 and not owned[0].exists()
    assert not list(tmp_path.iterdir())


def test_real_ci_and_hook_wiring_keeps_full_unit_and_separate_contracts():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.load((root / ".github/workflows/ci.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    for event in ("push", "pull_request"):
        ignores = workflow["on"][event]["paths-ignore"]
        assert "docs/plans/**" in ignores and ".planning/**" in ignores
        assert "src/**" not in ignores and "tests/**" not in ignores
    commands = [step.get("run", "") for step in workflow["jobs"]["test"]["steps"]]
    assert sum("pytest tests/unit" in command for command in commands) == 1
    assert sum("pre_push_gate.py --fast-contracts-only" in command for command in commands) == 1
    hook = (root / ".githooks/pre-push").read_text(encoding="utf-8")
    assert "--push-checks" in hook and "--fast-contracts-only" not in hook
    assert "SKIP" not in hook.upper().replace("SKIPPING", "")
