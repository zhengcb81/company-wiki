"""Independent CI responsibilities share wall time, never mutable scratch."""
from pathlib import Path
import io
import sys
import threading

import pytest

from unit.test_pre_push_temp_scope import gate


def test_both_phases_start_before_either_finishes(monkeypatch):
    barrier = threading.Barrier(2, timeout=2)
    observed = []
    def run(cmd, label):
        observed.append(label)
        barrier.wait()
        return 0
    monkeypatch.setattr(gate, '_run_pytest_gate', run)
    assert gate._run_parallel_pytest_gates([(['unit'], 'units'), (['contract'], 'contracts')]) == 0
    assert sorted(observed) == ['contracts', 'units']


@pytest.mark.parametrize('codes', [(0, 7), (8, 0), (124, 9)])
def test_failure_of_either_phase_is_not_hidden_by_another_green(monkeypatch, codes):
    observed = []
    def run(cmd, label):
        observed.append(label)
        return codes[0 if label == 'units' else 1]
    monkeypatch.setattr(gate, '_run_pytest_gate', run)
    result = gate._run_parallel_pytest_gates([(['unit'], 'units'), (['contract'], 'contracts')])
    assert result == next(code for code in codes if code)
    assert sorted(observed) == ['contracts', 'units']


def test_parallel_real_children_have_distinct_owned_scratch_and_clean_it(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, 'PROJECT_ROOT', tmp_path)
    sentinel = tmp_path/'original.txt'
    sentinel.write_text('untouched', encoding='utf-8')
    allocated = []
    original = gate._run
    def run(cmd, label, **kwargs):
        allocated.append(Path(cmd[cmd.index('--basetemp')+1]))
        return original(cmd, label, **kwargs)
    monkeypatch.setattr(gate, '_run', run)
    script = "import pathlib,sys; p=pathlib.Path(sys.argv[sys.argv.index('--basetemp')+1]); (p/'owned').write_text('x')"
    command = [sys.executable, '-c', script]
    assert gate._run_parallel_pytest_gates([(command, 'units'), (command, 'contracts')]) == 0
    assert len(set(allocated)) == 2 and all(not path.exists() for path in allocated)
    assert list(tmp_path.iterdir()) == [sentinel]
    assert sentinel.read_text(encoding='utf-8') == 'untouched'


@pytest.mark.parametrize('result', [0, 7])
def test_full_push_dispatch_keeps_every_existing_case_exactly_once(monkeypatch, result):
    monkeypatch.setattr(gate.sys, 'stdin', io.StringIO('fixture push range'))
    monkeypatch.setattr(gate, 'changed_paths', lambda *args: {'fixture'})
    monkeypatch.setattr(gate, 'select_unit_tests', lambda *args: (['tests/unit'], 'global'))
    phases = []
    monkeypatch.setattr(gate, '_run_parallel_pytest_gates', lambda rows: phases.extend(rows) or result)
    assert gate.main(['--push-checks']) == result
    assert len(phases) == 2
    assert phases[0][0][-1] == 'tests/unit'
    expected = [case for case in gate.FAST_CONTRACT_CASES if not case.startswith('tests/unit/')]
    assert phases[1][0][phases[1][0].index('--timeout=180')+1:] == expected


def test_wrapper_exception_waits_for_other_phase_and_restores_both_temps(monkeypatch):
    allocated = []
    observed = []
    def run(cmd, label, **kwargs):
        path = Path(cmd[cmd.index('--basetemp')+1])
        allocated.append(path)
        (path/'partial').write_text('partial', encoding='utf-8')
        observed.append(label)
        if label == 'units':
            raise TimeoutError('synthetic transport failure')
        return 0
    monkeypatch.setattr(gate, '_run', run)
    assert gate._run_parallel_pytest_gates([(['fixture'], 'units'), (['fixture'], 'contracts')]) == 1
    assert sorted(observed) == ['contracts', 'units']
    assert len(allocated) == 2 and all(not path.exists() for path in allocated)
