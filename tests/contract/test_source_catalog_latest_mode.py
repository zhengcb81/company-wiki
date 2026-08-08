"""WU-4.1: explicit mode semantics in the resolver.

- ``mode="latest_as_of"`` with multiple periods → the most recent published
  handle (≤ as_of_date) is reused, NOT AMBIGUOUS.
- ``mode="exact"`` (default) with multiple periods and no fiscal_year →
  AMBIGUOUS (legacy behavior, no guessing).
- An as-of cut: a handle published after as_of_date is never picked.
"""

from __future__ import annotations

import json
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
        """
    )
    con.execute(
        "INSERT INTO roots VALUES ('company_raw', ?, 'company_raw', 10, NULL, NULL)",
        (str(companies),),
    )
    con.execute("INSERT INTO entities VALUES ('ticker:ACME', 'ACME', 'ticker')")
    for i, (fy, published) in enumerate(
        [(2022, "2023-04-15"), (2023, "2024-04-15"), (2024, "2025-04-15")]
    ):
        did, sid = f"doc-{i}", f"src-{i}"
        body = f"%PDF-{i}".encode()
        f = companies / "ACME" / f"{i}.pdf"
        f.write_bytes(body)
        meta = json.dumps(
            {
                "acquisition": {
                    "fiscal_year": fy,
                    "market": "US",
                    "security_id": "ACME",
                    "form_type": "10-K",
                    "source_url": f"https://x/{i}.pdf",
                    "retrieved_at": "2025-05-01T10:00:00Z",
                    "collector_name": "t",
                    "collector_version": "1.0.0",
                }
            }
        )
        import hashlib

        sha = hashlib.sha256(body).hexdigest()
        manifest = json.dumps(
            {
                "content_sha256": sha,
                "retrieved_at": "2025-05-01T10:00:00Z",
                "collector_name": "t",
                "collector_version": "1.0.0",
                "mime_type": "application/pdf",
                "byte_size": len(body),
            }
        )
        con.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?)",
            (sid, sha, len(body), "application/pdf", "2025-01-01"),
        )
        con.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (did, sid, f"ACME {fy} annual", "filing", "annual_report",
             published, "active", 1, meta, None, "2025-01-01", "2026-08-08"),
        )
        con.execute(
            "INSERT INTO document_entities VALUES (?,?,?,?)",
            (did, "ticker:ACME", 1.0, "path_ticker"),
        )
        con.execute(
            "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"loc-{i}", "company_raw", f"ACME/{i}.pdf", str(f), sid, did,
             "original_primary", "active", len(body), 1, "scan-x",
             manifest, "{}", None),
        )
    con.commit()
    con.close()
    return catalog


def _request(mode: str | None = None, as_of: str = "2026-07-18"):
    from company_wiki.source_catalog import SourceRequest

    return SourceRequest(
        entity="ACME",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        form_type="10-K",
        as_of_date=as_of,
        mode=mode,
    )


def test_latest_as_of_picks_most_recent(tmp_path):
    """Three annuals (2022/2023/2024): latest_as_of reuses the 2024 one."""
    from company_wiki.source_catalog import SourceResolver

    catalog = _catalog(tmp_path)
    result = SourceResolver(catalog).resolve(_request(mode="latest_as_of"))
    assert result.status.value in {"reused_exact", "reused_equivalent"}, (
        result.debug_trace
    )
    assert len(result.matches) == 1
    handle = result.matches[0]
    assert handle.fiscal_year == 2024, handle


def test_latest_as_of_respects_as_of_cutoff(tmp_path):
    """An as_of date before the newest annual excludes it and picks the
    previous one."""
    from company_wiki.source_catalog import SourceResolver

    catalog = _catalog(tmp_path)
    result = SourceResolver(catalog).resolve(
        _request(mode="latest_as_of", as_of="2025-01-01")
    )
    assert result.status.value in {"reused_exact", "reused_equivalent"}
    assert result.matches[0].fiscal_year == 2023, result.matches[0]


def test_exact_mode_multiple_periods_is_ambiguous(tmp_path):
    """mode=exact (default) with no fiscal_year and multiple periods stays
    AMBIGUOUS — no guessing."""
    from company_wiki.source_catalog import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path)
    result = SourceResolver(catalog).resolve(_request())
    assert result.status is ResolutionStatus.AMBIGUOUS, result.debug_trace
    assert len(result.matches) == 3
