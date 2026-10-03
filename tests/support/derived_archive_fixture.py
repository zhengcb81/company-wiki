"""Small real SQLite/gzip/zstd evidence for precise archive retirement tests."""

from contextlib import closing
import gzip
import hashlib
import json
import sqlite3

from scripts.retire_source_catalog_db import _row_digest


RUN = '20260926T170825Z-4a9c67e1'
GZIP_PATH = 'source_manifests/archive/2026-08-07/retired-evidence.jsonl.gz'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True), encoding='utf-8')


def _zstd_frame(data):
    # A standard single-segment Zstandard frame with raw (uncompressed) blocks.
    # This exercises legal .zst bytes without installing a test-only compressor.
    frame = b'\x28\xb5\x2f\xfd\xa0' + len(data).to_bytes(4, 'little')
    chunks = [data[i:i + 131072] for i in range(0, len(data), 131072)] or [b'']
    for index, chunk in enumerate(chunks):
        header = (len(chunk) << 3) | int(index == len(chunks) - 1)
        frame += header.to_bytes(3, 'little') + chunk
    return frame


def archive_audit(root):
    current = root / '.source_catalog/catalog.sqlite3'
    control = current.parent / 'worker_control.json'
    write_json(control, {'desired_state': 'paused'})
    run = current.parent / 'retirement' / RUN
    run.mkdir(parents=True)
    zstd = run / 'catalog.full.sqlite3.zst'
    zstd.write_bytes(_zstd_frame(current.read_bytes()))
    archive = root / GZIP_PATH
    archive.parent.mkdir(parents=True)
    with gzip.open(archive, 'wb') as stream:
        stream.write(b'{"span_id":"legacy-span","raw_text":"old derived text"}\n')
    with closing(sqlite3.connect(current.as_uri() + '?mode=ro', uri=True)) as db:
        names = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )]
        tables = {}
        for name in names:
            if name == 'evidence_spans':
                continue
            keys = tuple(r[0] for r in db.execute(
                "SELECT key FROM catalog_meta WHERE key NOT LIKE 'legacy_%' ORDER BY key"
            )) if name == 'catalog_meta' else None
            count, digest = _row_digest(db, name, meta_keys=keys)
            tables[name] = {'rows': count, 'sha256': digest}
    prepared, retired = run / 'prepared.json', run / 'retired.json'
    write_json(prepared, {
        'schema': 'catalog-retirement-prepared-v1', 'run_id': RUN,
        'project_root': str(root), 'production_database': str(current),
        'backup_path': str(zstd), 'backup_sha256': sha(zstd),
        'backup_bytes': zstd.stat().st_size, 'tables': tables,
        'shadow_sha256': sha(current), 'shadow_bytes': current.stat().st_size,
    })
    write_json(retired, {
        'schema': 'catalog-retirement-retired-v1', 'run_id': RUN,
        'backup_path': str(zstd), 'backup_sha256': sha(zstd),
        'production_sha256': sha(current),
    })

    def binding(path):
        return {
            'path': str(path), 'relative_path': path.relative_to(root).as_posix(),
            'byte_size': path.stat().st_size, 'mtime_ns': path.stat().st_mtime_ns,
            'sha256': sha(path),
        }

    copied = [
        {'table': name, **value, 'prepared_rows': value['rows'],
         'prepared_sha256': value['sha256'], 'matches_prepared': True}
        for name, value in tables.items() if name != 'scan_runs'
    ]
    audit = root / 'audit.json'
    write_json(audit, {
        'schema': 'gd-b3-metadata-audit/1', 'status': 'passed',
        'project_root': str(root), 'basis_run_id': RUN,
        'current_database': binding(current),
        'database_stat_unchanged_during_audit': True, 'nonempty_wal': False,
        'worker_desired_state': 'paused',
        'basis': {'prepared': binding(prepared), 'retired': binding(retired)},
        'copied_metadata_tables': copied,
        'scan_runs': {
            'table': 'scan_runs', 'current_rows': tables['scan_runs']['rows'],
            'historical_rows': tables['scan_runs']['rows'],
            'historical_sha256': tables['scan_runs']['sha256'],
            'prepared_rows': tables['scan_runs']['rows'],
            'prepared_sha256': tables['scan_runs']['sha256'],
            'historical_matches_prepared': True, 'extra_rows': [],
        },
        'archives': [binding(zstd), binding(archive)],
        'candidate_deleted_bytes': zstd.stat().st_size + archive.stat().st_size,
    })
    return audit, current, zstd, archive


def minimal_archive_fixture(tmp_path):
    root = tmp_path / 'project'
    catalog = root / '.source_catalog'
    catalog.mkdir(parents=True)
    current = catalog / 'catalog.sqlite3'
    with closing(sqlite3.connect(current)) as db:
        for name in ('sources', 'documents', 'locations', 'source_metadata_assertions',
                     'document_retire_audit', 'scan_runs'):
            db.execute(f'CREATE TABLE {name}(id TEXT PRIMARY KEY, value TEXT)')
            db.execute(f'INSERT INTO {name} VALUES (?,?)', (name, 'original source fact'))
        db.execute('CREATE TABLE catalog_meta(key TEXT PRIMARY KEY, value TEXT)')
        db.execute("INSERT INTO catalog_meta VALUES ('schema_version','test')")
        db.commit()
    raw = root / 'companies/source.txt'
    raw.parent.mkdir()
    raw.write_bytes(b'original download; never a candidate')
    audit, current, zstd, archive = archive_audit(root)
    return root, audit, current, zstd, archive, raw
