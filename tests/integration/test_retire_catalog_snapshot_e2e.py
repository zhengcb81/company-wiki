"""Real source pipeline remains readable after a disposable snapshot is retired."""

import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from scripts.retire_catalog_snapshot import retire_snapshot
from support.narrative_transport_fixture import published_fixture


def test_snapshot_cleanup_preserves_formal_narrative_read_and_raw(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    with published_fixture(tmp_path) as fixture:
        root = fixture.catalog.config.catalog_dir
        current = fixture.catalog.config.database_path
        snapshot = root / 'catalog.sqlite3.bak-e2e'
        with closing(sqlite3.connect(f'{current.as_uri()}?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as destination:
                source.backup(destination)
        digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        run = root / 'retirement' / 'e2e'
        run.mkdir(parents=True)
        archive = run / 'retained-test-archive.zst'
        archive.write_bytes(b'only tests retained byte binding; no full restore')
        archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
        prepared, retired = run / 'prepared.json', run / 'retired.json'
        prepared.write_text(json.dumps({
            'schema': 'catalog-retirement-prepared-v1', 'run_id': 'e2e',
            'production_database': str(current), 'shadow_sha256': digest,
            'shadow_bytes': snapshot.stat().st_size, 'backup_path': str(archive),
            'backup_sha256': archive_sha, 'backup_bytes': archive.stat().st_size,
        }), encoding='utf-8')
        retired.write_text(json.dumps({
            'schema': 'catalog-retirement-retired-v1', 'run_id': 'e2e',
            'production_sha256': digest, 'backup_path': str(archive),
            'backup_sha256': archive_sha,
        }), encoding='utf-8')
        env = {**os.environ, 'PYTHONPATH': str(repo / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}

        def call(operation, request):
            result = subprocess.run(
                [sys.executable, '-m', 'company_wiki.source_catalog.narrative_transport_cli',
                 '--config', str(fixture.config_path), '--operation', operation],
                input=json.dumps(request).encode(), capture_output=True,
                env=env, cwd=fixture.root, timeout=20, check=False,
            )
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            return result

        ref = json.loads(call('reference', {
            'schema_version': 'narrative-reference-request/1',
            'source_ref': fixture.source_ref.to_dict(),
        }).stdout)
        request = {
            'schema_version': 'narrative-read-request/1', 'narrative_ref': ref,
            'as_of_date': '2026-09-01', 'expected_source': fixture.expected_source,
        }
        before = call('read', request)
        source_before = (fixture.raw_path.read_bytes(), fixture.raw_path.stat().st_mtime_ns)
        db_before = (current.read_bytes(), current.stat().st_mtime_ns)
        assert retire_snapshot(root, snapshot.name, prepared, retired)['status'] == 'dry_run'
        result = retire_snapshot(root, snapshot.name, prepared, retired, apply=True)
        assert result['status'] == 'removed' and not snapshot.exists()
        after = call('read', request)
        assert after.stdout == before.stdout == fixture.payload
        assert json.loads(after.stderr)['replay_status'] == 'verified'
        assert (fixture.raw_path.read_bytes(), fixture.raw_path.stat().st_mtime_ns) == source_before
        assert (current.read_bytes(), current.stat().st_mtime_ns) == db_before
    assert list(tmp_path.iterdir()) == []
