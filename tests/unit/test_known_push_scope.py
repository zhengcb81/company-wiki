"""Uncertain scope never erases known consumers from bounded daily feedback."""
import io
import subprocess

import pytest

from tools import pre_push_gate as gate
from unit.test_ci_push_selection import _file


def dispatched(root, changes, monkeypatch):
    observed = []
    monkeypatch.setattr(gate, 'PROJECT_ROOT', root)
    monkeypatch.setattr(gate.sys, 'stdin', io.StringIO('fixture range'))
    monkeypatch.setattr(gate, 'changed_paths', lambda *_: changes)
    monkeypatch.setattr(gate, '_run_pytest_gate',
                        lambda command, label: observed.append(command) or 0)
    assert gate.main(['--push-checks']) == 0
    assert len(observed) == 1
    return observed[0][observed[0].index('--timeout=180') + 1:]


@pytest.mark.parametrize('uncertainty', ['runtime', 'resource', 'tool'])
def test_unknown_remainder_cannot_erase_known_source_consumer(tmp_path, monkeypatch, capsys, uncertainty):
    core = _file(tmp_path, 'src/pkg/core.py', 'VALUE = 1\n')
    near = _file(tmp_path, 'tests/unit/test_near.py', 'from pkg import core\n')
    changes = {core}
    if uncertainty == 'runtime':
        _file(tmp_path, core, 'import importlib\nload = lambda name: importlib.import_module(name)\n')
    elif uncertainty == 'resource':
        changes.add(_file(tmp_path, 'config/input.json', '{}'))
    else:
        changes.add(_file(tmp_path, 'tools/helper.py', 'import subprocess\nsubprocess.run(argv)\n'))
    targets = dispatched(tmp_path, changes, monkeypatch)
    assert near in targets
    assert 'tests/unit' not in targets
    assert 'full_validation_pending' in capsys.readouterr().out


def test_dynamic_unrelated_tests_remain_ci_responsibility_not_daily_seeds(tmp_path, monkeypatch):
    core = _file(tmp_path, 'src/pkg/core.py', 'VALUE = 1\n')
    near = _file(tmp_path, 'tests/unit/test_near.py', 'from pkg import core\n')
    unknown = _file(tmp_path, 'tests/unit/test_unknown.py',
                    'import subprocess\nsubprocess.run(argv)\n')
    targets = dispatched(tmp_path, {core}, monkeypatch)
    assert near in targets and unknown not in targets


def test_wide_scope_keeps_changed_units_then_nearest_static_consumers(tmp_path, monkeypatch, capsys):
    core = _file(tmp_path, 'src/pkg/core.py', 'VALUE = 1\n')
    _file(tmp_path, 'src/pkg/bridge.py', 'from pkg import core\n')
    far = _file(tmp_path, 'tests/unit/test_aaa_far.py', 'from pkg import bridge\n')
    directly_changed = _file(tmp_path, 'tests/unit/test_zzz_changed.py', 'def test_changed(): pass\n')
    nearby = [_file(tmp_path, f'tests/unit/test_direct_{index:02d}.py', 'from pkg import core\n')
              for index in range(35)]
    targets = dispatched(tmp_path, {core, directly_changed}, monkeypatch)
    units = [path for path in targets if path not in gate.FAST_CONTRACT_CASES]
    assert units == [directly_changed, *nearby[:31]]
    assert far not in targets
    assert len(units) == gate.DAILY_PUSH_MAX_AFFECTED_TARGETS == 32
    output = capsys.readouterr().out
    assert 'deferred' in output and 'full_validation_pending' in output


def test_unowned_change_and_known_changed_unit_are_not_all_or_nothing(tmp_path, monkeypatch):
    changed = _file(tmp_path, 'tests/unit/test_explicit.py', 'def test_x(): pass\n')
    targets = dispatched(tmp_path, {'src/pkg/deleted.py', changed}, monkeypatch)
    assert changed in targets


def test_unknown_only_range_still_runs_smoke_never_pytest_with_empty_targets(tmp_path, monkeypatch):
    assert dispatched(tmp_path, {'config/input.json'}, monkeypatch) == list(gate.FAST_CONTRACT_CASES)


def test_real_git_hook_blocks_known_failure_despite_dynamic_runtime(tmp_path):
    from unit.test_daily_push_policy import _fixture_repository, _git

    work, remote, _ = _fixture_repository(tmp_path)
    core = _file(work, 'src/pushprobe/core.py',
                 'import importlib\nVALUE=1\ndef load(name): return importlib.import_module(name)\n')
    _file(work, 'tests/unit/test_known_consumer.py',
          'from pushprobe import core\ndef test_actual_value(): assert core.VALUE == 1\n')
    _git(work, 'add', '--', core, 'tests/unit/test_known_consumer.py')
    _git(work, 'commit', '-qm', 'baseline with known consumer')
    _git(work, 'push', '-q', 'origin', 'master')
    before = _git(remote, 'rev-parse', 'refs/heads/master').stdout.strip()
    _file(work, core, 'import importlib\nVALUE=2\ndef load(name): return importlib.import_module(name)\n')
    _git(work, 'add', '--', core)
    _git(work, 'commit', '-qm', 'deliberate runtime regression')
    failed = subprocess.run(['git', 'push', 'origin', 'master'], cwd=work,
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    assert failed.returncode != 0, failed.stdout + failed.stderr
    assert 'test_actual_value' in failed.stdout + failed.stderr
    assert _git(remote, 'rev-parse', 'refs/heads/master').stdout.strip() == before
