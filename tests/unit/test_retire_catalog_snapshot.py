"""One exact obsolete SQLite snapshot can go without touching current data."""

import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.retire_catalog_snapshot import SnapshotRetirementError, retire_snapshot


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path):
    root = tmp_path / 'catalog'
    root.mkdir()
    current = root / 'catalog.sqlite3'
    with closing(sqlite3.connect(current)) as db:
        db.execute('CREATE TABLE sources(source_id TEXT, content_sha256 TEXT)')
        db.execute('INSERT INTO sources VALUES (?,?)', ('source', 'a' * 64))
        db.commit()
    snapshot = root / 'catalog.sqlite3.bak-test'
    snapshot.write_bytes(current.read_bytes())
    run = root / 'retirement' / 'test-run'
    run.mkdir(parents=True)
    archive = run / 'catalog.full.sqlite3.zst'
    # The cleanup never decompresses or restores an archive. Here its bytes
    # only exercise exact retained-file binding, not zstd format validation.
    archive.write_bytes(b'retained archive test payload')
    prepared = run / 'prepared.json'
    retired = run / 'retired.json'
    prepared.write_text(json.dumps({
        'schema': 'catalog-retirement-prepared-v1',
        'run_id': 'test-run', 'production_database': str(current),
        'shadow_sha256': _sha(snapshot), 'shadow_bytes': snapshot.stat().st_size,
        'backup_path': str(archive), 'backup_sha256': _sha(archive),
        'backup_bytes': archive.stat().st_size,
    }), encoding='utf-8')
    retired.write_text(json.dumps({
        'schema': 'catalog-retirement-retired-v1', 'run_id': 'test-run',
        'production_sha256': _sha(snapshot),
        'backup_path': str(archive), 'backup_sha256': _sha(archive),
    }), encoding='utf-8')
    raw = tmp_path / 'companies' / 'source.txt'
    raw.parent.mkdir()
    raw.write_bytes(b'original downloaded document')
    return root, snapshot, prepared, retired, current, archive, raw


def test_dry_run_apply_retry_preserve_current_sources_and_raw(tmp_path):
    root, snapshot, prepared, retired, current, archive, raw = _fixture(tmp_path)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (current, archive, raw)}
    expected = snapshot.stat().st_size
    plan = retire_snapshot(root, snapshot.name, prepared, retired)
    assert plan['status'] == 'dry_run' and plan['candidate_bytes'] == expected
    assert snapshot.exists() and not (root / 'snapshot-cleanup').exists()
    result = retire_snapshot(root, snapshot.name, prepared, retired, apply=True)
    assert result['status'] == 'removed' and result['deleted_bytes'] == expected
    assert not snapshot.exists()
    assert retire_snapshot(root, snapshot.name, prepared, retired, apply=True) == result
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before} == before
    with closing(sqlite3.connect(f'{current.as_uri()}?mode=ro', uri=True)) as db:
        assert db.execute('SELECT * FROM sources').fetchall() == [('source', 'a' * 64)]


@pytest.mark.parametrize('name', ['catalog.sqlite3', '../companies/source.txt', 'source.pdf'])
def test_only_direct_snapshot_names_can_be_candidates(tmp_path, name):
    root, snapshot, prepared, retired, *_ = _fixture(tmp_path)
    with pytest.raises(SnapshotRetirementError):
        retire_snapshot(root, name, prepared, retired, apply=True)
    assert snapshot.exists()


@pytest.mark.parametrize('kind', ['snapshot', 'archive', 'basis', 'size'])
def test_binding_drift_refuses_before_delete(tmp_path, kind):
    root, snapshot, prepared, retired, _, archive, _ = _fixture(tmp_path)
    if kind in {'snapshot', 'archive'}:
        path = snapshot if kind == 'snapshot' else archive
        data = path.read_bytes()
        path.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
    elif kind == 'basis':
        value = json.loads(retired.read_text(encoding='utf-8'))
        value['production_sha256'] = 'b' * 64
        retired.write_text(json.dumps(value), encoding='utf-8')
    else:
        value = json.loads(prepared.read_text(encoding='utf-8'))
        value['shadow_bytes'] += 1
        prepared.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(SnapshotRetirementError):
        retire_snapshot(root, snapshot.name, prepared, retired, apply=True)
    assert snapshot.exists()


def test_non_sqlite_snapshot_is_not_deleted_even_when_resigned(tmp_path):
    root, snapshot, prepared, retired, *_ = _fixture(tmp_path)
    snapshot.write_bytes(b'original document pretending to be a backup')
    p = json.loads(prepared.read_text(encoding='utf-8'))
    r = json.loads(retired.read_text(encoding='utf-8'))
    p.update(shadow_sha256=_sha(snapshot), shadow_bytes=snapshot.stat().st_size)
    r['production_sha256'] = _sha(snapshot)
    prepared.write_text(json.dumps(p), encoding='utf-8')
    retired.write_text(json.dumps(r), encoding='utf-8')
    with pytest.raises(SnapshotRetirementError):
        retire_snapshot(root, snapshot.name, prepared, retired, apply=True)
    assert snapshot.exists()


def test_interruption_after_unlink_reconciles_from_intent(tmp_path, monkeypatch):
    root, snapshot, prepared, retired, *_ = _fixture(tmp_path)
    original = Path.unlink

    def unlink_then_interrupt(path, *args, **kwargs):
        original(path, *args, **kwargs)
        if path == snapshot:
            raise RuntimeError('simulated interruption after unlink')

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'unlink', unlink_then_interrupt)
        with pytest.raises(RuntimeError, match='simulated interruption'):
            retire_snapshot(root, snapshot.name, prepared, retired, apply=True)
    assert not snapshot.exists()
    result = retire_snapshot(root, snapshot.name, prepared, retired, apply=True)
    assert result['status'] == 'removed' and result['reconciled'] is True


def test_missing_candidate_without_intent_is_not_a_success(tmp_path):
    root, snapshot, prepared, retired, *_ = _fixture(tmp_path)
    snapshot.unlink()
    with pytest.raises(SnapshotRetirementError):
        retire_snapshot(root, snapshot.name, prepared, retired, apply=True)


def test_reparse_candidate_is_refused_without_following_it(tmp_path, monkeypatch):
    from scripts import retire_catalog_snapshot as module

    root, snapshot, prepared, retired, *_ = _fixture(tmp_path)
    original = module._no_reparse

    def reject_candidate(path):
        if path == snapshot:
            raise SnapshotRetirementError('reparse path')
        return original(path)

    monkeypatch.setattr(module, '_no_reparse', reject_candidate)
    with pytest.raises(SnapshotRetirementError, match='reparse'):
        retire_snapshot(root, snapshot.name, prepared, retired, apply=True)
    assert snapshot.exists()


def test_completed_receipt_can_replay_after_retained_archive_is_retired(tmp_path):
    root, snapshot, prepared, retired, _, archive, _ = _fixture(tmp_path)
    result = retire_snapshot(root, snapshot.name, prepared, retired, apply=True)
    archive.unlink()
    assert retire_snapshot(root, snapshot.name, prepared, retired, apply=True) == result


def test_new_snapshot_cannot_reuse_completed_receipt_without_archive(tmp_path):
    root, snapshot, prepared, retired, current, archive, _ = _fixture(tmp_path)
    retire_snapshot(root, snapshot.name, prepared, retired, apply=True)
    archive.unlink()
    new_snapshot = root / 'catalog.sqlite3.bak-new'
    new_snapshot.write_bytes(current.read_bytes())
    with pytest.raises(SnapshotRetirementError):
        retire_snapshot(root, new_snapshot.name, prepared, retired, apply=True)
    assert new_snapshot.exists()
