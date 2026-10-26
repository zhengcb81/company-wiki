"""Daily feedback keeps its unit boundary and every curated invariant."""
import sys

from tools import pre_push_gate as gate


def test_mixed_selection_defers_nonunit_files_but_keeps_affected_units():
    selected = ["tests/unit/test_reader.py", "tests/integration/test_slow.py",
                "tests/test_phase_c_sample_metadata.py"]
    targets, reason = gate._push_targets(selected)
    assert targets == [selected[0], *gate.FAST_CONTRACT_CASES]
    assert "non-unit" in reason and "deferred" in reason


def test_nonunit_selection_cannot_expand_curated_whole_files():
    selected = ["tests/contract/test_source_catalog_temp_worker_governance.py",
                "tests/document_normalization/test_isolated_ocr.py"]
    targets, reason = gate._push_targets(selected)
    assert targets == list(gate.FAST_CONTRACT_CASES)
    assert "non-unit" in reason and "deferred" in reason


def test_parent_traversal_is_an_unknown_scope_not_an_affected_unit():
    targets, reason = gate._push_targets(["tests/unit/../integration/test_slow.py"])
    assert targets == list(gate.FAST_CONTRACT_CASES)
    assert "deferred" in reason


def test_daily_gate_has_one_total_deadline_and_last_node_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "PROJECT_ROOT", tmp_path)
    observed = []
    monkeypatch.setattr(gate, "_run", lambda cmd, label, **kwargs:
                        observed.append((cmd, kwargs)) or 0)
    gate._run_pytest_gate([sys.executable, "-m", "pytest", *gate.FAST_CONTRACT_CASES],
                          "daily push fast feedback: curated inventory")
    command, options = observed[0]
    assert options["timeout"] == gate.DAILY_PUSH_TIMEOUT_SECONDS == 180
    assert "-vv" in command and "--durations=15" in command
    assert all(case in command for case in gate.FAST_CONTRACT_CASES)
    assert not list(tmp_path.iterdir())


def test_manual_full_gate_retains_its_original_deadline(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "PROJECT_ROOT", tmp_path)
    observed = []
    monkeypatch.setattr(gate, "_run", lambda cmd, label, **kwargs:
                        observed.append((cmd, kwargs)) or 0)
    gate._run_pytest_gate([sys.executable, "-m", "pytest", "tests/unit"], "unit tests")
    command, options = observed[0]
    assert "tests/unit" in command and options["timeout"] == 600
    assert "-n" in command and command[command.index("-n") + 1] == "2"
