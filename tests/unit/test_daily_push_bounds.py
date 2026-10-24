"""Bound the affected set itself; an explicit list can still mean a full run."""
import pytest

from tools import pre_push_gate as gate


@pytest.mark.parametrize('count', [33, 65, 333])
def test_wide_closed_file_set_is_wholly_deferred_not_truncated(count):
    selected = [f'tests/unit/test_changed_{index}.py' for index in range(count)]
    actual, reason = gate._push_targets(selected)
    assert actual == list(gate.FAST_CONTRACT_CASES)
    assert 'deferred' in reason and str(count) in reason


def test_small_boundary_runs_complete_files_and_deduplicates_repeated_paths():
    selected = [f'tests/unit/test_changed_{index}.py' for index in range(32)]
    actual, _ = gate._push_targets([*selected, *selected])
    assert actual[:32] == selected
    assert len(actual) == len(set(actual))


@pytest.mark.parametrize('directory', ['tests/unit', 'tests/unit/source_catalog', 'tests/contract'])
def test_unbounded_directory_is_not_a_small_file(directory):
    actual, reason = gate._push_targets([directory])
    assert actual == list(gate.FAST_CONTRACT_CASES)
    assert 'deferred' in reason


@pytest.mark.parametrize('returncode', [0, 1])
def test_pass_is_reported_only_after_runner_success(monkeypatch, capsys, returncode):
    monkeypatch.setattr(gate, 'changed_paths', lambda *_: {'source.py'})
    monkeypatch.setattr(gate, 'select_unit_tests', lambda *_: (['tests/unit'], 'wide'))
    monkeypatch.setattr(gate.sys, 'stdin', type('Input', (), {'read': lambda self: 'refs'})())

    def execute(*_):
        before = capsys.readouterr().out
        assert 'local_fast_pass' not in before
        assert 'planned' in before
        assert all(target in before for target in gate.FAST_CONTRACT_CASES)
        return returncode

    monkeypatch.setattr(gate, '_run_pytest_gate', execute)
    assert gate.main(['--push-checks']) == returncode
    after = capsys.readouterr().out
    assert ('local_fast_pass' in after) is (returncode == 0)
