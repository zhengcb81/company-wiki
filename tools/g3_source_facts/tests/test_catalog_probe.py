"""Read-only fixture checks: the probe opens facts without ever becoming a writer."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from g3_source_facts.catalog_probe import CatalogProbeError, probe_catalog


def _make_fixture(source_dir: Path) -> Path:
    db = source_dir / "catalog.sqlite3"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL,
            first_seen_at TEXT NOT NULL);
        CREATE TABLE locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT NOT NULL, source_id TEXT, document_id TEXT,
            role TEXT, location_status TEXT NOT NULL, observed_size INTEGER);
        INSERT INTO catalog_meta VALUES ('schema_version', '1.2.0');
        INSERT INTO sources VALUES ('urn:company-wiki:source:sha256:aa', 'aa', 10,
                                    'application/pdf', '2026-01-01T00:00:00Z');
        INSERT INTO locations VALUES ('urn:company-wiki:location:sha256:bb',
            'company_raw', 'x/y.pdf', 'urn:company-wiki:source:sha256:aa', NULL,
            'original_primary', 'active', 10);
        """
    )
    con.commit()
    con.close()
    return db


def _snapshot(directory: Path) -> dict[str, tuple[int, str]]:
    out = {}
    for path in sorted(directory.iterdir()):
        data = path.read_bytes()
        out[path.name] = (len(data), hashlib.sha256(data).hexdigest())
    return out


def test_probe_is_zero_writer_and_touches_no_side_file(tmp_path: Path):
    source_dir = tmp_path / "source_dir"
    source_dir.mkdir()
    db = _make_fixture(source_dir)
    before = _snapshot(source_dir)

    result = probe_catalog(db)

    after = _snapshot(source_dir)
    assert after == before, "probe must not add, resize or rewrite any file"
    assert not (source_dir / "catalog.sqlite3-wal").exists()
    assert not (source_dir / "catalog.sqlite3-shm").exists()
    assert result.schema_version == "1.2.0"
    assert result.total_changes == 0
    assert result.locations[0]["relative_path"] == "x/y.pdf"


def test_probe_refuses_to_create_a_missing_database(tmp_path: Path):
    missing = tmp_path / "catalog.sqlite3"
    with pytest.raises(CatalogProbeError):
        probe_catalog(missing)
    assert not missing.exists()


def test_probe_runs_inside_a_single_read_transaction(tmp_path: Path):
    source_dir = tmp_path / "source_dir"
    source_dir.mkdir()
    db = _make_fixture(source_dir)
    result = probe_catalog(db, rows=("locations", "sources", "catalog_meta"))
    assert result.statements == [
        "SELECT schema_version",
        "SELECT locations",
        "SELECT sources",
        "SELECT catalog_meta",
    ]
    assert result.in_transaction is False
    assert result.query_only is True
