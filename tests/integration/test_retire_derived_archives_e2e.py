"""Actual source/query/narrative CLI works with the obsolete archives removed."""

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from scripts.retire_derived_archives import retire_archives
from company_wiki.source_catalog.evidence_query import (
    EvidenceQueryArchivedError, EvidenceQueryNotFoundError, EvidenceQueryService,
)
from support.derived_archive_fixture import archive_audit, sha, write_json
from support.narrative_transport_fixture import published_fixture


def _retired_source(fixture):
    raw = fixture.raw_path.parent / 'retired.txt'
    raw.write_bytes(b'Original retired company document retained after derivative disposal.')
    digest = sha(raw)
    source_id = 'urn:company-wiki:source:sha256:' + digest
    document_id = 'urn:company-wiki:document:sha256:' + digest
    with fixture.catalog.store.transaction() as db:
        db.execute('INSERT INTO sources VALUES (?,?,?,?,?)', (
            source_id, digest, raw.stat().st_size, 'text/plain', '2026-08-01T00:00:00Z',
        ))
        db.execute('''INSERT INTO documents
            (document_id,primary_source_id,title,source_type,document_kind,
             source_status,metadata_priority,metadata_json,first_seen_at,last_seen_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)''', (
            document_id, source_id, 'Retired original', 'filing', 'annual_report',
            'retired', 1, '{}', '2026-08-01T00:00:00Z', '2026-08-01T00:00:00Z',
        ))
        db.execute('''INSERT INTO locations
            (location_id,root_id,relative_path,absolute_path,source_id,document_id,
             role,location_status,last_seen_run,metadata_json)
            VALUES (?,?,?,?,?,?,?,?,?,?)''', (
            'retired-location', 'company_raw', raw.relative_to(fixture.root / 'companies').as_posix(),
            str(raw), source_id, document_id, 'original_primary', 'active', 'test', '{}',
        ))
        db.execute('INSERT INTO document_retire_audit VALUES (?,?,?,?,?)', (
            'retired-audit', document_id, 'superseded derived evidence', 'test', '2026-08-01T00:00:00Z',
        ))
        db.execute("INSERT INTO catalog_meta VALUES ('legacy_evidence_retention','active_only')")
    return raw, source_id, document_id


def test_retirement_keeps_source_facts_raw_query_and_formal_narrative_cli(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    with published_fixture(tmp_path) as fixture:
        fixture.catalog.normalize()
        retired_raw, retired_id, retired_document = _retired_source(fixture)
        fixture.catalog.close()
        # Freeze the scratch catalog just as the production maintenance basis
        # requires. A still-open fixture reader can otherwise leave WAL frames.
        with closing(sqlite3.connect(fixture.catalog.config.database_path)) as db:
            assert db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0] == 0
        current_dir = fixture.root / '.source_catalog'
        fixture.catalog.config.catalog_dir.rename(current_dir)
        current = current_dir / 'catalog.sqlite3'
        config = json.loads(fixture.config_path.read_text())
        config['catalog_dir'] = str(current_dir)
        write_json(fixture.config_path, config)
        audit, current, zstd, archive = archive_audit(fixture.root)
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(repo / 'src'), str(repo))),
               'PYTHONDONTWRITEBYTECODE': '1'}

        def narrative(operation, request):
            result = subprocess.run(
                [sys.executable, '-B', '-m', 'company_wiki.source_catalog.narrative_transport_cli',
                 '--config', str(fixture.config_path), '--operation', operation],
                input=json.dumps(request).encode(), capture_output=True, check=False,
                env=env, cwd=fixture.root, timeout=20,
            )
            assert result.returncode == 0, result.stderr.decode(errors='replace')
            return result

        reference = json.loads(narrative('reference', {
            'schema_version': 'narrative-reference-request/1',
            'source_ref': fixture.source_ref.to_dict(),
        }).stdout)
        request = {'schema_version': 'narrative-read-request/1', 'narrative_ref': reference,
                   'as_of_date': '2026-09-01', 'expected_source': fixture.expected_source}
        before = narrative('read', request)
        identity_before = {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                           for p in (current, fixture.raw_path, retired_raw)}
        with closing(sqlite3.connect(current.as_uri() + '?mode=ro', uri=True)) as db:
            active_locator = db.execute(
                'SELECT locator FROM evidence_spans WHERE source_id=? LIMIT 1',
                (fixture.source_ref.source_id,),
            ).fetchone()[0]
        service = EvidenceQueryService(current)
        active_before = service.lookup(source_id=fixture.source_ref.source_id, locator=active_locator).to_dict()
        assert retire_archives(fixture.root, audit)['status'] == 'dry_run'
        command = subprocess.run(
            [sys.executable, '-B', str(repo / 'scripts/retire_derived_archives.py'),
             '--project-root', str(fixture.root), '--audit', str(audit), '--apply'],
            capture_output=True, env=env, cwd=fixture.root, check=False, timeout=20,
        )
        assert command.returncode == 0, command.stderr.decode(errors='replace')
        result = json.loads(command.stdout)
        assert result['status'] == 'removed' and result['newly_deleted_bytes'] > 0
        assert not zstd.exists() and not archive.exists()
        assert retire_archives(fixture.root, audit, apply=True)['newly_deleted_bytes'] == 0
        after = narrative('read', request)
        assert before.stdout == after.stdout == fixture.payload
        assert json.loads(after.stderr)['replay_status'] == 'verified'
        assert service.lookup(source_id=fixture.source_ref.source_id, locator=active_locator).to_dict() == active_before
        with pytest.raises(EvidenceQueryArchivedError, match='source identity'):
            service.list_spans(document_id=retired_document)
        with pytest.raises(EvidenceQueryArchivedError, match='source identity'):
            service.lookup(source_id=retired_id, locator='loc:v1/page:1')
        with pytest.raises(EvidenceQueryNotFoundError):
            service.list_spans(source_id='urn:company-wiki:source:sha256:' + '0' * 64)
        assert {p: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                for p in identity_before} == identity_before
    assert list(tmp_path.iterdir()) == []
