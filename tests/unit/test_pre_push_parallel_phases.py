"""A push dispatches one bounded gate; full units stay a separate CI phase.

The retired two-phase dispatcher duplicated the full local responsibility on
every push. The daily push now runs one gate (affected files plus the shared
contract smoke set) while the full unit suite remains an explicit local mode
and a remote CI phase.
"""
import io

import pytest

from unit.test_pre_push_temp_scope import gate


def _push_dispatch(monkeypatch, selected, reason):
    monkeypatch.setattr(gate.sys, 'stdin', io.StringIO('fixture push range'))
    monkeypatch.setattr(gate, 'changed_paths', lambda *args: {'fixture'})
    monkeypatch.setattr(gate, 'select_unit_tests', lambda *args: (selected, reason))


@pytest.mark.parametrize('result', [0, 7])
def test_push_dispatch_runs_one_gate_with_every_case_exactly_once(monkeypatch, result):
    _push_dispatch(monkeypatch, ['tests/unit/test_reader.py'], 'affected unit tests')
    observed = []
    monkeypatch.setattr(gate, '_run_pytest_gate',
                        lambda cmd, label: observed.append((cmd, label)) or result)
    assert gate.main(['--push-checks']) == result
    assert len(observed) == 1
    cmd, label = observed[0]
    targets = cmd[cmd.index('--timeout=180') + 1:]
    expected = ['tests/unit/test_reader.py', *gate.FAST_CONTRACT_CASES]
    assert targets == expected
    assert len(targets) == len(set(targets))
    assert 'tests/unit' not in targets


def test_full_recommendation_still_dispatches_only_the_shared_smoke_gate(monkeypatch):
    _push_dispatch(monkeypatch, ['tests/unit'], 'configuration or test entrypoint changed')
    observed = []
    monkeypatch.setattr(gate, '_run_pytest_gate',
                        lambda cmd, label: observed.append(cmd) or 0)
    assert gate.main(['--push-checks']) == 0
    assert len(observed) == 1
    targets = observed[0][observed[0].index('--timeout=180') + 1:]
    assert targets == list(gate.FAST_CONTRACT_CASES)
    assert 'tests/unit' not in targets


def test_gate_exception_is_reported_not_swallowed(monkeypatch, capsys):
    _push_dispatch(monkeypatch, ['tests/unit/test_reader.py'], 'affected unit tests')

    def broken(cmd, label):
        raise OSError('synthetic transport failure')

    monkeypatch.setattr(gate, '_run_pytest_gate', broken)
    assert gate.main(['--push-checks']) == 1
    assert 'synthetic transport failure' in capsys.readouterr().out
