"""WU-3.3: multi-candidate determinism and conflict semantics.

Rules under test (from task_plan WU-3.3):

- same content hash across roots → equivalent; primary chosen by root
  priority but ALL equivalent locations are preserved in the handle.
- same period, different hash, no revision evidence → AMBIGUOUS (never
  guess by scan order or file mtime).
- randomizing the catalog INSERT order 100 times must produce the same
  result status + reason + handle hash (determinism gate).
"""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from pathlib import Path


def _build_catalog(tmp_path: Path, insert_order: list[int]):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    portfolio = tmp_path / "portfolio"
    dropbox = tmp_path / "dropbox"
    (companies / "ACME" / "raw").mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10),
                RootSpec("dayu_portfolio", portfolio, "dayu_portfolio", priority=20),
                RootSpec("dropbox_stock", dropbox, "directory", priority=30),
            ),
            reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
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
    con.execute(
        "INSERT INTO roots VALUES ('dayu_portfolio', ?, 'dayu_portfolio', 20, NULL, NULL)",
        (str(portfolio),),
    )
    con.execute(
        "INSERT INTO roots VALUES ('dropbox_stock', ?, 'directory', 30, NULL, NULL)",
        (str(dropbox),),
    )
    con.execute("INSERT INTO entities VALUES ('ticker:ACME', 'ACME', 'ticker')")

    def insert(
        i: int, root_id: str, root_dir: Path, sha: str, fy: int,
        document_id: str | None = None,
    ) -> None:
        # Production model: same content hash → same source → same logical
        # document with multiple locations across roots (scanner merges by
        # source). The fixture mirrors that: same sha shares document_id.
        did = document_id or f"doc-{i}"
        sid = f"src-{sha[:8]}"
        body = b"%PDF-fake"
        f = root_dir / "ACME" / f"{i}.pdf"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(body)
        meta = json.dumps(
            {
                "acquisition": {
                    "fiscal_year": fy,
                    "market": "US",
                    "security_id": "ACME",
                    "form_type": "10-K",
                    "source_url": f"https://x/{i}.pdf",
                    "retrieved_at": "2026-02-21T10:00:00Z",
                    "collector_name": "t",
                    "collector_version": "1.0.0",
                }
            }
        )
        manifest = json.dumps(
            {
                "content_sha256": sha,
                "retrieved_at": "2026-02-21T10:00:00Z",
                "collector_name": "t",
                "collector_version": "1.0.0",
                "mime_type": "application/pdf",
                "byte_size": len(body),
            }
        )
        con.execute(
            "INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?)",
            (sid, sha, len(body), "application/pdf", "2025-01-01"),
        )
        con.execute(
            "INSERT OR IGNORE INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (did, sid, f"ACME {fy} annual", "filing", "annual_report",
             f"{fy}-04-15", "active", 1, meta, None, "2025-01-01", "2026-08-08"),
        )
        con.execute(
            "INSERT OR IGNORE INTO document_entities VALUES (?,?,?,?)",
            (did, "ticker:ACME", 1.0, "path_ticker"),
        )
        con.execute(
            "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"loc-{i}", root_id, f"ACME/{i}.pdf", str(f), sid, did,
             "original_primary", "active", len(body), 1, "scan-x",
             manifest, "{}", None),
        )

    SAME_HASH = hashlib.sha256(b"same-bytes").hexdigest()
    OTHER_HASH = hashlib.sha256(b"other-bytes").hexdigest()
    # Reviewer finding (WU-3.3): the insert_order parameter must actually
    # drive the INSERT sequence, else 100 'random' runs build identical
    # catalogs and the determinism gate is a tautology. Each insertion is
    # defined here; the caller's order argument reorders the executions.
    steps = {
        1: lambda: insert(1, "company_raw", companies, SAME_HASH, 2025, document_id="doc-same"),
        2: lambda: insert(2, "dayu_portfolio", portfolio, SAME_HASH, 2025, document_id="doc-same"),
        3: lambda: insert(3, "dropbox_stock", dropbox, SAME_HASH, 2025, document_id="doc-same"),
        4: lambda: insert(4, "company_raw", companies, OTHER_HASH, 2024),
        5: lambda: insert(5, "dayu_portfolio", portfolio, hashlib.sha256(b"third").hexdigest(), 2024),
    }
    for step in insert_order:
        steps[step]()
    con.commit()
    con.close()
    return catalog


def _resolve(catalog, fiscal_year: int | None = None):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    return SourceResolver(catalog).resolve(
        SourceRequest(
            entity="ACME",
            market="US",
            security_id="ACME",
            document_kind="annual_report",
            form_type="10-K",
            fiscal_year=fiscal_year,
            as_of_date="2026-07-18",
        )
    )


def _result_sig(result) -> str:
    digest = hashlib.sha256()
    digest.update(result.status.value.encode())
    digest.update(result.reason.encode())
    for handle in result.matches:
        # tmp dirs differ per run; hash the root-relative tail only.
        tail = Path(handle.canonical_path).parts[-3:]
        digest.update("/".join(tail).encode())
        digest.update(handle.content_sha256.encode())
        digest.update(str(handle.exact_duplicate_location_count).encode())
    return digest.hexdigest()


def test_same_hash_three_roots_picks_priority_primary_preserves_all(tmp_path):
    """Same content hash on all three roots: primary location = company_raw
    (priority 10), all three locations preserved as equivalent. Without a
    provider identity in metadata the reuse is REUSED_EQUIVALENT — a
    successful reuse either way; identity strength only picks EXACT vs
    EQUIVALENT, not whether reuse happens."""
    catalog = _build_catalog(tmp_path, [1, 2, 3, 4, 5])
    result = _resolve(catalog, fiscal_year=2025)
    assert result.status.value in {"reused_exact", "reused_equivalent"}, (
        result.debug_trace
    )
    handle = result.matches[0]
    # canonical_path is a file path under the company_raw root directory
    # (companies/); root_id "company_raw" maps to that directory.
    assert "companies" in handle.canonical_path, handle.canonical_path
    # _annotate_locations keeps all locations on the document; the handle
    # exposes the canonical path + duplicate count.
    assert handle.exact_duplicate_location_count >= 2, handle


def test_same_period_different_hash_is_ambiguous(tmp_path):
    """FY2024 has two docs with different hashes and no revision evidence:
    must be AMBIGUOUS, never a guess by scan order."""
    catalog = _build_catalog(tmp_path, [1, 2, 3, 4, 5])
    result = _resolve(catalog, fiscal_year=2024)
    assert result.status.value == "ambiguous", result.debug_trace
    assert result.download_required is False
    assert len(result.matches) == 2


def test_determinism_across_100_random_insert_orders(tmp_path):
    """Randomizing the INSERT order must not change the resolution result.
    Each request (FY2025 / FY2024) is tracked separately: its signature must
    be identical across all 100 runs."""
    random.seed(20260808)
    sigs_2025: set[str] = set()
    sigs_2024: set[str] = set()
    for run in range(100):
        order = list(range(1, 6))
        random.shuffle(order)
        catalog = _build_catalog(tmp_path / f"run-{run}", order)
        sigs_2025.add(_result_sig(_resolve(catalog, fiscal_year=2025)))
        sigs_2024.add(_result_sig(_resolve(catalog, fiscal_year=2024)))
    assert len(sigs_2025) == 1, f"FY2025 non-deterministic: {len(sigs_2025)} sigs"
    assert len(sigs_2024) == 1, f"FY2024 non-deterministic: {len(sigs_2024)} sigs"
