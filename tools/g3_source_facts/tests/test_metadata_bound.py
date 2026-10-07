"""Explicit input, read-only SQL and zero import-time discovery."""
import importlib
import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

@pytest.fixture
def database(tmp_path):
    db = tmp_path / 'custom # lake.sqlite'
    with sqlite3.connect(db) as conn:
        conn.executescript("""
        CREATE TABLE sources(source_id TEXT, content_sha256 TEXT, byte_size INTEGER);
        CREATE TABLE locations(source_id TEXT, root_id TEXT, relative_path TEXT, location_status TEXT);
        CREATE TABLE catalog_meta(key TEXT, value TEXT);
        INSERT INTO catalog_meta VALUES ('schema_version','1.2.0');
        INSERT INTO sources VALUES ('a','hash-a',100),('b','hash-b',30);
        INSERT INTO locations VALUES
        ('a','chosen','a.pdf','active'),('a','chosen','b.pdf','retired'),
        ('a','external','c.pdf','active'),('b','chosen','d.pdf','active');
        """)
    return db

def test_import_has_no_git_database_or_directory_side_effects(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('implicit discovery or I/O at import')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(sqlite3, 'connect', forbidden)
    monkeypatch.setattr(Path, 'mkdir', forbidden)
    from g3_source_facts import metadata_bound
    importlib.reload(metadata_bound)

def test_bound_reads_only_explicit_database_and_root(database, capsys):
    from g3_source_facts.metadata_bound import main
    before = (database.read_bytes(), database.stat().st_mtime_ns)
    assert main(['--database', str(database), '--root-id', 'chosen']) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['registered_upper_bound_bytes'] == 100
    assert payload['mixed_with_other_roots_groups'] == 1
    assert payload['distinct_single_copy_hashes'] == 1
    assert payload['total_changes'] == 0
    assert payload['scope'] == 'chosen'
    assert payload['allocated_bytes'] is None
    assert payload['releasable_bytes'] is None
    assert (database.read_bytes(), database.stat().st_mtime_ns) == before
    assert sorted(p.name for p in database.parent.iterdir()) == [database.name]

def test_missing_database_is_not_created(tmp_path):
    from g3_source_facts.metadata_bound import main
    absent = tmp_path / 'no' / 'db.sqlite'
    with pytest.raises(FileNotFoundError):
        main(['--database', str(absent), '--root-id', 'chosen'])
    assert not list(tmp_path.iterdir())


def test_report_cannot_overwrite_input_database(database):
    from g3_source_facts.metadata_bound import main
    before = database.read_bytes()
    with pytest.raises(SystemExit) as caught:
        main(['--database', str(database), '--root-id', 'chosen', '--output', str(database)])
    assert caught.value.code == 2
    assert database.read_bytes() == before
