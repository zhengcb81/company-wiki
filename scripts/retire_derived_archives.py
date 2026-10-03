"""Precisely retire two obsolete derivative archives; never original documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any

from company_wiki.source_catalog.lock import CatalogOperationLock
if __package__:
    from .retire_catalog_snapshot import _bound, _hash, _inside, _json, _no_reparse, _write
else:
    from retire_catalog_snapshot import _bound, _hash, _inside, _json, _no_reparse, _write


RUN_ID = '20260926T170825Z-4a9c67e1'
RUN = f'.source_catalog/retirement/{RUN_ID}'
TARGETS = (f'{RUN}/catalog.full.sqlite3.zst',
           'source_manifests/archive/2026-08-07/retired-evidence.jsonl.gz')
REQUIRED_TABLES = {'sources', 'documents', 'locations', 'source_metadata_assertions',
                   'document_retire_audit', 'scan_runs', 'catalog_meta'}


class ArchiveRetirementError(ValueError):
    """The precise derivative retirement facts or current bytes no longer agree."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ArchiveRetirementError(reason)


def _binding(root: Path, value: dict[str, Any], relative: str) -> Path:
    target = _inside(root / relative, root)
    _no_reparse(target)
    _require(value.get('relative_path') == relative
             and value.get('path') == str(target), 'exact file path mismatch')
    _require(type(value.get('mtime_ns')) is int, 'invalid file timestamp')
    return target


def _verify_file(path: Path, value: dict[str, Any]) -> None:
    _require(path.is_file(), 'bound file missing')
    _bound(path, value.get('sha256'), value.get('byte_size'))
    _require(path.stat().st_mtime_ns == value['mtime_ns'], 'file timestamp changed')


def _metadata_proof(audit: dict[str, Any], prepared: dict[str, Any]) -> None:
    tables = prepared.get('tables', {})
    _require(isinstance(tables, dict) and REQUIRED_TABLES <= tables.keys(),
             'source metadata proof missing')
    copied = audit.get('copied_metadata_tables', [])
    _require(isinstance(copied, list), 'metadata proof is not a list')
    names = [item.get('table') for item in copied]
    _require(len(names) == len(set(names)) and set(names) == (
        tables.keys() - {'evidence_spans', 'scan_runs'}), 'metadata coverage mismatch')
    for item in copied:
        expected = tables[item['table']]
        _require(item.get('matches_prepared') is True and {
            'rows': item.get('rows'), 'sha256': item.get('sha256'),
        } == expected and item.get('prepared_rows') == expected['rows']
                 and item.get('prepared_sha256') == expected['sha256'],
                 'metadata digest proof mismatch')
    scan = audit.get('scan_runs', {})
    expected = tables['scan_runs']
    extra = scan.get('extra_rows', [])
    _require(scan.get('historical_matches_prepared') is True and {
        'rows': scan.get('historical_rows'), 'sha256': scan.get('historical_sha256'),
    } == expected and scan.get('prepared_rows') == expected['rows']
             and scan.get('prepared_sha256') == expected['sha256']
             and scan.get('current_rows') == expected['rows'] + len(extra),
             'historical scan proof mismatch')
    for row in extra:
        report = json.loads(row['report_json'])
        _require(row.get('status') == 'completed_with_errors'
                 and report.get('files_seen') == 0 and report.get('files_hashed') == 0,
                 'extra scan changed sources')


def _plan(root: Path, audit_path: Path) -> dict[str, Any]:
    audit_path = _inside(audit_path, root)
    audit = _json(audit_path)
    _require(audit.get('schema') == 'gd-b3-metadata-audit/1'
             and audit.get('status') == 'passed' and audit.get('project_root') == str(root)
             and audit.get('basis_run_id') == RUN_ID
             and audit.get('database_stat_unchanged_during_audit') is True
             and audit.get('nonempty_wal') is False
             and audit.get('worker_desired_state') == 'paused', 'invalid metadata audit')
    current = audit['current_database']
    _binding(root, current, '.source_catalog/catalog.sqlite3')
    basis = audit['basis']
    prepared_path = _binding(root, basis['prepared'], f'{RUN}/prepared.json')
    retired_path = _binding(root, basis['retired'], f'{RUN}/retired.json')
    _verify_file(prepared_path, basis['prepared'])
    _verify_file(retired_path, basis['retired'])
    p, r = _json(prepared_path), _json(retired_path)
    _require(p.get('schema') == 'catalog-retirement-prepared-v1'
             and r.get('schema') == 'catalog-retirement-retired-v1'
             and p.get('run_id') == r.get('run_id') == RUN_ID
             and p.get('project_root') == str(root)
             and p.get('production_database') == current['path']
             and p.get('shadow_sha256') == r.get('production_sha256')
             and p.get('backup_path') == r.get('backup_path') == str(root / TARGETS[0])
             and p.get('backup_sha256') == r.get('backup_sha256'), 'retirement basis mismatch')
    _metadata_proof(audit, p)
    candidates = audit['archives']
    _require(isinstance(candidates, list) and len(candidates) == 2
             and [item.get('relative_path') for item in candidates] == list(TARGETS),
             'only the two exact derivative archives are supported')
    for item, relative in zip(candidates, TARGETS):
        _binding(root, item, relative)
    _require(candidates[0]['sha256'] == p['backup_sha256']
             and candidates[0]['byte_size'] == p['backup_bytes'], 'archive basis mismatch')
    total = sum(item['byte_size'] for item in candidates)
    _require(total == audit['candidate_deleted_bytes'], 'candidate byte total mismatch')
    return {
        'schema': 'derived-archive-retirement-plan/1', 'project_root': str(root),
        'audit_sha256': _hash(audit_path), 'basis': basis,
        'current_database': current, 'targets': candidates,
        'candidate_deleted_bytes': total, 'old_span_restore_guaranteed': False,
    }


def _current(root: Path, plan: dict[str, Any]) -> None:
    database = root / '.source_catalog/catalog.sqlite3'
    _verify_file(database, plan['current_database'])
    wal = Path(str(database) + '-wal')
    _no_reparse(wal)
    _require(not wal.exists() or wal.stat().st_size == 0, 'current catalog WAL is nonempty')
    control = _json(_inside(root / '.source_catalog/worker_control.json', root))
    _require(control.get('desired_state') == 'paused', 'Worker must remain paused')


def _target(root: Path, value: dict[str, Any]) -> Path:
    path = _binding(root, value, value['relative_path'])
    _verify_file(path, value)
    magic = b'\x28\xb5\x2f\xfd' if path.suffix == '.zst' else b'\x1f\x8b'
    with path.open('rb') as stream:
        _require(stream.read(len(magic)) == magic, 'candidate archive header mismatch')
    return path


def _operation_paths(root: Path, plan: dict[str, Any]) -> tuple[Path, Path]:
    identity = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:24]
    directory = _inside(root / '.source_catalog/archive-cleanup' / identity, root)
    return _inside(directory / 'intent.json', root), _inside(directory / 'receipt.json', root)


def _finished(root: Path, plan: dict[str, Any], receipt: Path) -> dict[str, Any]:
    value = _json(_inside(receipt, root))
    _require(value.get('plan') == plan and value.get('status') == 'removed'
             and value.get('deleted_bytes') == plan['candidate_deleted_bytes'],
             'archive cleanup receipt drift')
    for item in plan['targets']:
        _require(not _binding(root, item, item['relative_path']).exists(),
                 'retired archive reappeared')
    return {**value, 'newly_deleted_bytes': 0, 'recovered_deleted_bytes': 0, 'replayed': True}


def _apply(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    intent_path, receipt_path = _operation_paths(root, plan)
    if receipt_path.exists():
        _require(intent_path.exists() and _json(intent_path).get('plan') == plan,
                 'completion missing matching intent')
        return _finished(root, plan, receipt_path)
    resumed = intent_path.exists()
    free_before_call = shutil.disk_usage(root).free
    if resumed:
        intent = _json(_inside(intent_path, root))
        _require(intent.get('plan') == plan, 'archive cleanup intent drift')
    else:
        for item in plan['targets']:
            _target(root, item)
        intent = {'plan': plan, 'states': ['pending'] * 2,
                  'free_bytes_before': free_before_call}
        _write(intent_path, intent)
    states = intent['states']
    _require(len(states) == 2 and set(states) <= {'pending', 'removed'}, 'invalid intent state')
    new_bytes, recovered_bytes = 0, 0
    for index, item in enumerate(plan['targets']):
        path = _binding(root, item, item['relative_path'])
        if states[index] == 'removed':
            _require(not path.exists(), 'retired archive reappeared')
            continue
        if path.exists():
            _target(root, item).unlink()
            new_bytes += item['byte_size']
        else:
            _require(resumed, 'candidate missing without cleanup intent')
            recovered_bytes += item['byte_size']
        states[index] = 'removed'
        _write(intent_path, intent)
    _current(root, plan)
    result = {
        'status': 'removed', 'plan': plan, 'deleted_bytes': plan['candidate_deleted_bytes'],
        'newly_deleted_bytes': new_bytes, 'recovered_deleted_bytes': recovered_bytes,
        'reconciled': resumed, 'replayed': False, 'target_states': states,
        'current_before': plan['current_database'], 'current_after': plan['current_database'],
        'free_bytes_before': intent['free_bytes_before'],
        'free_bytes_before_this_call': free_before_call,
        'free_bytes_after': shutil.disk_usage(root).free,
    }
    _write(receipt_path, result)
    return result


def retire_archives(project_root: Path, audit_path: Path, *, apply: bool = False) -> dict[str, Any]:
    root = Path(os.path.abspath(project_root))
    _no_reparse(root)
    plan = _plan(root, audit_path)
    if not apply:
        _current(root, plan)
        for item in plan['targets']:
            _target(root, item)
        return {'status': 'dry_run', **plan}
    with CatalogOperationLock(root / '.source_catalog', operation='retire-derived-archives'):
        _current(root, plan)
        return _apply(root, plan)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        result = retire_archives(args.project_root, args.audit, apply=args.apply)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'refused', 'reason': str(exc)}, ensure_ascii=True))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
