"""Retire one redundant SQLite snapshot identified by completed retirement facts.

No recursive deletion, raw files, current database, or archive restoration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
from typing import Any

from company_wiki.source_catalog.lock import CatalogOperationLock


class SnapshotRetirementError(ValueError):
    """A snapshot cannot be proven redundant under this narrow operation."""


def _no_reparse(path: Path) -> None:
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise SnapshotRetirementError('reparse path')


def _inside(path: Path, root: Path) -> Path:
    value = Path(os.path.abspath(path))
    _no_reparse(value)
    if not value.is_relative_to(root):
        raise SnapshotRetirementError('path leaves catalog directory')
    return value


def _json(path: Path) -> dict[str, Any]:
    with path.open('rb') as stream:
        raw = stream.read(131_073)
    if len(raw) > 131_072:
        raise SnapshotRetirementError('receipt too large')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise SnapshotRetirementError('receipt must be an object')
    return value


def _hash(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _bound(path: Path, sha: object, size: object) -> None:
    if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha):
        raise SnapshotRetirementError('invalid file hash')
    if type(size) is not int or size <= 0:
        raise SnapshotRetirementError('invalid file size')
    _no_reparse(path)
    if not path.is_file() or path.stat().st_size != size or _hash(path) != sha:
        raise SnapshotRetirementError('file binding changed')


def _basis(root: Path, prepared: Path, retired: Path) -> dict[str, Any]:
    p = _json(_inside(prepared, root / 'retirement'))
    r = _json(_inside(retired, root / 'retirement'))
    current = _inside(Path(p.get('production_database', '')), root)
    if (p.get('schema') != 'catalog-retirement-prepared-v1'
            or r.get('schema') != 'catalog-retirement-retired-v1'
            or not p.get('run_id') or p['run_id'] != r.get('run_id')
            or current != root / 'catalog.sqlite3' or not current.is_file()):
        raise SnapshotRetirementError('completed retirement basis mismatch')
    if (p.get('shadow_sha256') != r.get('production_sha256')
            or p.get('backup_path') != r.get('backup_path')
            or p.get('backup_sha256') != r.get('backup_sha256')):
        raise SnapshotRetirementError('retirement identity mismatch')
    archive = _inside(Path(p['backup_path']), root / 'retirement')
    _bound(archive, p['backup_sha256'], p['backup_bytes'])
    return {
        'snapshot_sha256': p['shadow_sha256'], 'candidate_bytes': p['shadow_bytes'],
        'basis_run_id': p['run_id'], 'archive_sha256': p['backup_sha256'],
        'prepared_sha256': _hash(prepared), 'retired_sha256': _hash(retired),
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    _no_reparse(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.partial')
    _no_reparse(temp)
    with temp.open('wb') as stream:
        stream.write(json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def _apply(root: Path, snapshot: Path, plan: dict[str, Any]) -> dict[str, Any]:
    operation_id = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:24]
    directory = _inside(root / 'snapshot-cleanup' / operation_id, root)
    intent, receipt = directory / 'intent.json', directory / 'receipt.json'
    _no_reparse(intent)
    _no_reparse(receipt)
    if receipt.exists():
        result = _json(receipt)
        if result.get('plan') != plan or snapshot.exists():
            raise SnapshotRetirementError('cleanup receipt does not match current state')
        return result
    existed = snapshot.exists()
    if intent.exists():
        if _json(intent).get('plan') != plan:
            raise SnapshotRetirementError('cleanup intent drift')
    elif existed:
        _write(intent, {'plan': plan})
    else:
        raise SnapshotRetirementError('snapshot missing without cleanup intent')
    current = root / 'catalog.sqlite3'
    before = (current.stat().st_mtime_ns, current.stat().st_size, _hash(current))
    free_before = shutil.disk_usage(root).free
    if existed:
        _verify_snapshot(snapshot, plan)
        snapshot.unlink()
    after = (current.stat().st_mtime_ns, current.stat().st_size, _hash(current))
    if before != after:
        raise SnapshotRetirementError('current catalog changed during snapshot cleanup')
    result = {
        'status': 'removed', 'plan': plan, 'deleted_bytes': plan['candidate_bytes'],
        'reconciled': not existed, 'current_sha256': after[2],
        'current_mtime_ns': after[0], 'free_bytes_before': free_before,
        'free_bytes_after': shutil.disk_usage(root).free,
    }
    _write(receipt, result)
    return result


def _verify_snapshot(snapshot: Path, plan: dict[str, Any]) -> None:
    _bound(snapshot, plan['snapshot_sha256'], plan['candidate_bytes'])
    with snapshot.open('rb') as stream:
        if stream.read(16) != b'SQLite format 3\x00':
            raise SnapshotRetirementError('candidate is not a SQLite snapshot')


def retire_snapshot(
    catalog_dir: Path, snapshot_name: str, prepared: Path, retired: Path,
    *, apply: bool = False,
) -> dict[str, Any]:
    if not re.fullmatch(r'catalog\.sqlite3\.bak-[A-Za-z0-9_.-]+', snapshot_name):
        raise SnapshotRetirementError('only direct catalog snapshot names are supported')
    root = Path(os.path.abspath(catalog_dir))
    _no_reparse(root)
    snapshot = _inside(root / snapshot_name, root)
    if not apply:
        plan = {'snapshot_name': snapshot_name, **_basis(root, prepared, retired)}
        _verify_snapshot(snapshot, plan)
        return {'status': 'dry_run', **plan}
    with CatalogOperationLock(root, operation='retire-redundant-snapshot'):
        plan = {'snapshot_name': snapshot_name, **_basis(root, prepared, retired)}
        if snapshot.exists():
            _verify_snapshot(snapshot, plan)
        return _apply(root, snapshot, plan)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog-dir', type=Path, required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--retired', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        value = retire_snapshot(args.catalog_dir, args.snapshot, args.prepared, args.retired, apply=args.apply)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'status': 'refused', 'reason': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
