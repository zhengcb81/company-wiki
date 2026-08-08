"""WU-5.3: SourceBundle served by SourceCatalog (producer side).

``query_source_bundle`` returns source + verified artifacts in one call,
with the WU-5.1 fail-closed gates applied to real DB rows (schema_version
and source_sha256 now persisted on the artifacts table via the additive
migration). Unknown document → None.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path


def _catalog(tmp_path: Path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
            reusable_root_kinds=("company_raw",),
        )
    )
    catalog.store.status()
    con = sqlite3.connect(catalog.config.database_path)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL UNIQUE,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL, first_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT,
            source_type TEXT, document_kind TEXT, published_date TEXT,
            source_status TEXT NOT NULL, metadata_priority INTEGER NOT NULL,
            metadata_json TEXT NOT NULL, text_fingerprint TEXT,
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_kind TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS document_entities (
            document_id TEXT NOT NULL, entity_id TEXT NOT NULL,
            confidence REAL NOT NULL, method TEXT NOT NULL,
            PRIMARY KEY(document_id, entity_id)
        );
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL,
            source_id TEXT, document_id TEXT, role TEXT NOT NULL,
            location_status TEXT NOT NULL, observed_size INTEGER,
            observed_mtime_ns INTEGER, last_seen_run TEXT NOT NULL,
            manifest_json TEXT, metadata_json TEXT NOT NULL, error TEXT
        );
        CREATE TABLE IF NOT EXISTS roots (
            root_id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL,
            priority INTEGER NOT NULL, last_scan_run TEXT, last_scanned_at TEXT
        );
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            source_id TEXT,
            artifact_role TEXT NOT NULL,
            path TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            byte_size INTEGER NOT NULL,
            mime_type TEXT NOT NULL,
            generator_name TEXT NOT NULL,
            generator_version TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    con.execute(
        "INSERT INTO roots VALUES ('company_raw', ?, 'company_raw', 10, NULL, NULL)",
        (str(companies),),
    )
    con.execute("INSERT INTO entities VALUES ('ticker:ACME', 'ACME', 'ticker')")
    sid = "src-1"
    sha = hashlib.sha256(b"source-body").hexdigest()
    con.execute("INSERT INTO sources VALUES (?,?,?,?,?)", (sid, sha, 11, "application/pdf", "2025-01-01"))
    con.execute(
        "INSERT INTO documents VALUES ('doc-1', ?, 'ACME 2025 annual', 'filing', 'annual_report', "
        "'2026-04-15', 'active', 1, '{}', NULL, '2025-01-01', '2026-08-08')",
        (sid,),
    )
    con.execute("INSERT INTO document_entities VALUES ('doc-1', 'ticker:ACME', 1.0, 'path_ticker')")
    con.execute(
        "INSERT INTO locations VALUES ('loc-1', 'company_raw', 'ACME/1.pdf', ?, ?, 'doc-1', "
        "'original_primary', 'active', 11, 1, 'scan-x', NULL, '{}', NULL)",
        (str(companies / "ACME" / "1.pdf"), sid),
    )
    con.commit()
    con.close()
    return catalog


def _registry():
    return {"normalizer": {"1.0.0"}, "summarizer": {"1.0.0"}, "section_extractor": {"1.0.0"}}


def test_query_source_bundle_unknown_document_returns_none(tmp_path):
    catalog = _catalog(tmp_path)
    assert catalog.query_source_bundle(
        document_id="nope", registry=_registry(), allowed_roots=(tmp_path,),
        now="2026-08-08T12:00:00Z",
    ) is None


def test_query_source_bundle_with_artifact(tmp_path):
    """A completed artifact row (with schema_version/source_sha256 columns)
    is returned as a valid handle in the bundle."""
    catalog = _catalog(tmp_path)
    body = b"# normalized body"
    artifact_path = tmp_path / "normalized.md"
    artifact_path.write_bytes(body)
    con = sqlite3.connect(catalog.config.database_path)
    con.execute(
        """INSERT INTO artifacts(artifact_id,document_id,source_id,artifact_role,path,
           content_sha256,byte_size,mime_type,generator_name,generator_version,status,
           error,metadata_json,created_at,schema_version,source_sha256)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "art-1", "doc-1", "src-1", "normalized", str(artifact_path),
            hashlib.sha256(body).hexdigest(), len(body), "text/markdown",
            "normalizer", "1.0.0", "completed", None, "{}", "2026-08-08T10:00:00Z",
            "1.0", hashlib.sha256(b"source-body").hexdigest(),
        ),
    )
    con.commit()
    con.close()
    bundle = catalog.query_source_bundle(
        document_id="doc-1", registry=_registry(), allowed_roots=(tmp_path,),
        now="2026-08-08T12:00:00Z",
    )
    assert bundle is not None
    assert bundle["source"]["document_id"] == "doc-1"
    assert "normalized" in bundle["valid_handles"]
    assert bundle["invalid"] == {}
    assert len(bundle["bundle_hash"]) == 64


def test_migration_adds_artifact_columns(tmp_path):
    """The additive migration must add schema_version/source_sha256 to an
    existing artifacts table without a schema version bump, and be re-runnable."""
    catalog = _catalog(tmp_path)
    con = sqlite3.connect(catalog.config.database_path)
    columns = {row[1] for row in con.execute("PRAGMA table_info(artifacts)")}
    con.close()
    assert "schema_version" in columns
    assert "source_sha256" in columns
    # re-running the migration is a no-op
    catalog.store.status()
    con = sqlite3.connect(catalog.config.database_path)
    columns2 = {row[1] for row in con.execute("PRAGMA table_info(artifacts)")}
    con.close()
    assert columns2 == columns
