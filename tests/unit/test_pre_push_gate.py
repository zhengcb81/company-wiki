"""Daily feedback keeps its unit boundary and every curated invariant."""
import sys

from tools import pre_push_gate as gate


def test_fast_inventory_keeps_the_four_reuse_receipt_regressions_without_a_whole_file():
    path = "tests/unit/test_shared_reading_cache_precheck.py"
    required = (
        path + "::test_reuse_final_receipt_has_one_owner_read_per_operation",
        path + "::test_new_operation_rejects_changed_reused_original_before_new_fee",
    )
    # Existing bounded inventory plus one protocol-shape regression node.
    assert len(gate.FAST_CONTRACT_CASES) == 35
    assert path not in gate.FAST_CONTRACT_CASES
    assert all(gate.FAST_CONTRACT_CASES.count(node) == 1 for node in required)
    protocol_path = 'tests/unit/test_narrative_protocol_identity_shapes.py'
    protocol_node = protocol_path + '::test_protocol_lookup_does_not_hash_non_string_json'
    assert gate.CURRENT_CI_REGRESSION_CASES.count(protocol_node) == 1
    assert protocol_path not in gate.FAST_CONTRACT_CASES
    assert gate.DAILY_PUSH_TIMEOUT_SECONDS == 180


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
