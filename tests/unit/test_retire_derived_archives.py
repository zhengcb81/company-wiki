"""Two exact legacy derivative objects can go; raw and source facts cannot."""

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from support.derived_archive_fixture import minimal_archive_fixture, write_json


def _tool():
    return importlib.import_module('scripts.retire_derived_archives')


def test_plan_apply_retry_keep_database_and_raw(tmp_path):
    root, audit, current, zstd, archive, raw = minimal_archive_fixture(tmp_path)
    module = _tool()
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (current, raw)}
    initial = sorted(p.relative_to(root).as_posix() for p in root.rglob('*'))
    expected = zstd.stat().st_size + archive.stat().st_size
    plan = module.retire_archives(root, audit)
    assert plan['status'] == 'dry_run' and plan['candidate_deleted_bytes'] == expected
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob('*')) == initial
    result = module.retire_archives(root, audit, apply=True)
    assert result['status'] == 'removed' and result['deleted_bytes'] == expected
    assert result['newly_deleted_bytes'] == expected
    assert not zstd.exists() and not archive.exists()
    repeated = module.retire_archives(root, audit, apply=True)
    assert repeated['deleted_bytes'] == expected and repeated['newly_deleted_bytes'] == 0
    assert repeated['replayed'] is True
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before} == before


def test_interruption_after_first_unlink_reconciles_exact_increment(tmp_path, monkeypatch):
    root, audit, _, zstd, archive, _ = minimal_archive_fixture(tmp_path)
    module = _tool()
    first_size, second_size = zstd.stat().st_size, archive.stat().st_size
    original = Path.unlink

    def interrupt(path, *args, **kwargs):
        original(path, *args, **kwargs)
        if path == zstd:
            raise RuntimeError('after first unlink')

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'unlink', interrupt)
        with pytest.raises(RuntimeError, match='after first unlink'):
            module.retire_archives(root, audit, apply=True)
    assert not zstd.exists() and archive.exists()
    result = module.retire_archives(root, audit, apply=True)
    assert result['newly_deleted_bytes'] == second_size
    assert result['recovered_deleted_bytes'] == first_size
    assert result['deleted_bytes'] == first_size + second_size and result['reconciled']


@pytest.mark.parametrize('drift', ['sha', 'size', 'metadata', 'basis', 'db', 'wal', 'control'])
def test_drift_refuses_without_deleting_targets(tmp_path, drift):
    root, audit, current, zstd, archive, _ = minimal_archive_fixture(tmp_path)
    module = _tool()
    value = json.loads(audit.read_text())
    if drift == 'sha':
        archive.write_bytes(archive.read_bytes()[:-1] + b'x')
    elif drift == 'size':
        value['archives'][1]['byte_size'] += 1
        write_json(audit, value)
    elif drift == 'metadata':
        value['copied_metadata_tables'][0]['sha256'] = 'b' * 64
        write_json(audit, value)
    elif drift == 'basis':
        prepared = Path(value['basis']['prepared']['path'])
        prepared.write_bytes(prepared.read_bytes() + b' ')
    elif drift == 'db':
        current.write_bytes(current.read_bytes() + b' ')
    elif drift == 'wal':
        Path(str(current) + '-wal').write_bytes(b'not empty')
    else:
        write_json(root / '.source_catalog/worker_control.json', {'desired_state': 'running'})
    with pytest.raises(ValueError):
        module.retire_archives(root, audit, apply=True)
    assert zstd.exists() and archive.exists()


@pytest.mark.parametrize('target', ['raw', 'current', 'directory', 'escape'])
def test_arbitrary_candidates_rejected_even_if_other_bindings_match(tmp_path, target):
    root, audit, current, zstd, archive, raw = minimal_archive_fixture(tmp_path)
    module = _tool()
    value = json.loads(audit.read_text())
    candidate = {'raw': raw, 'current': current, 'directory': archive.parent,
                 'escape': tmp_path / 'outside.gz'}[target]
    value['archives'][1]['path'] = str(candidate)
    value['archives'][1]['relative_path'] = candidate.relative_to(root).as_posix() if (
        candidate.is_relative_to(root)
    ) else '../outside.gz'
    write_json(audit, value)
    with pytest.raises(ValueError):
        module.retire_archives(root, audit, apply=True)
    assert zstd.exists() and archive.exists() and raw.exists()


def test_missing_target_without_intent_is_refused(tmp_path):
    root, audit, _, zstd, archive, _ = minimal_archive_fixture(tmp_path)
    zstd.unlink()
    with pytest.raises(ValueError, match='missing'):
        _tool().retire_archives(root, audit, apply=True)
    assert archive.exists()


def test_reparse_target_is_refused(tmp_path, monkeypatch):
    root, audit, _, zstd, archive, _ = minimal_archive_fixture(tmp_path)
    module = _tool()
    original = module._no_reparse

    def reject(path):
        if path == archive:
            raise ValueError('reparse path')
        return original(path)

    monkeypatch.setattr(module, '_no_reparse', reject)
    with pytest.raises(ValueError, match='reparse'):
        module.retire_archives(root, audit, apply=True)
    assert zstd.exists() and archive.exists()


def test_archive_tool_is_source_lifecycle_not_research_writer():
    from scripts import writer_policy

    assert 'retire_derived_archives.py' in writer_policy.SOURCE_WORKFLOW_TOOL_ALLOWLIST
    assert not writer_policy.is_legacy_script_cli(Path(writer_policy.SCRIPTS_DIR) / 'retire_derived_archives.py')


def test_resume_refuses_changed_second_archive_without_reporting_completion(tmp_path, monkeypatch):
    root, audit, _, zstd, archive, raw = minimal_archive_fixture(tmp_path)
    original = Path.unlink

    def interrupt(path, *args, **kwargs):
        original(path, *args, **kwargs)
        if path == zstd:
            raise RuntimeError('after first unlink')

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'unlink', interrupt)
        with pytest.raises(RuntimeError):
            _tool().retire_archives(root, audit, apply=True)
    archive.write_bytes(archive.read_bytes() + b'changed')
    with pytest.raises(ValueError):
        _tool().retire_archives(root, audit, apply=True)
    assert archive.exists() and raw.exists()
    assert not list((root / '.source_catalog/archive-cleanup').rglob('receipt.json'))


def test_cli_json_paths_survive_non_utf8_stdout(tmp_path):
    unicode_base = tmp_path / '资料'
    unicode_base.mkdir()
    root, audit, _, zstd, archive, _ = minimal_archive_fixture(unicode_base)
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, '-B', str(repo / 'scripts/retire_derived_archives.py'),
         '--project-root', str(root), '--audit', str(audit)],
        capture_output=True, check=False, cwd=root, timeout=20,
        env={**os.environ, 'PYTHONPATH': str(repo / 'src'), 'PYTHONIOENCODING': 'gbk'},
    )
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    value = json.loads(result.stdout)
    assert value['project_root'] == str(root)
    assert all(Path(item['path']).exists() for item in value['targets'])
    assert value['status'] == 'dry_run' and zstd.exists() and archive.exists()
