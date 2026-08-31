"""ZR-1005 acceptance tests: legacy artifact bucketing & minimal canary backfill.

Verifies FC-901 (artifact_backfill.py) dry-run/apply semantics (stage I
fifth card).  Production catalog dry-run is run once (slow, >10min); temp
catalogs with real artifact files and metadata are used for C2–C4.

  C1  real-catalog dry-run: result.closed == True, result_hash stable,
      production catalog row counts unchanged.
  C2  temp-catalog apply: shadow bindings INSERT OR IGNORE for bindable
      artifacts; legacy artifacts table never UPDATEd/DELETEd.
  C3  idempotency: re-apply skips already-bound artifacts; dry-run
      result_hash stable.
  C4  provability: only bindable artifacts get shadow bindings.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.artifact_backfill import (  # noqa: E402
    run_artifact_backfill,
)

PRODUCTION_CATALOG = Path(r"C:\Users\郑曾波\Projects\company-wiki\.source_catalog\catalog.sqlite3")
NOW = "2026-08-23T12:00:00Z"
_REGISTRY = {"source_catalog_normalizer": {"1.0.0"}}


def _row_counts(path: Path) -> dict[str, int]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    try:
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("documents", "sources", "locations")}
    finally:
        con.close()


def _table_count(path: Path, table: str) -> int:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        con.close()


def _seed_catalog(cat_path: Path, root: Path) -> None:
    """Seed a temp catalog with one bindable artifact (real file exists)."""
    artifact_file = root / "artifacts" / "a1.pdf"
    artifact_file.parent.mkdir(parents=True)
    artifact_file.write_bytes(b"fake-pdf-content-for-test")
    content_sha = hashlib.sha256(b"fake-pdf-content-for-test").hexdigest()

    con = sqlite3.connect(cat_path)
    con.executescript(
        "CREATE TABLE sources ("
        "  source_id TEXT PRIMARY KEY, content_sha256 TEXT, byte_size INTEGER,"
        "  mime_type TEXT, first_seen_at TEXT);"
        "CREATE TABLE documents ("
        "  document_id TEXT PRIMARY KEY, primary_source_id TEXT,"
        "  title TEXT, source_status TEXT, source_type TEXT,"
        "  document_kind TEXT, metadata_priority INTEGER,"
        "  metadata_json TEXT, first_seen_at TEXT, last_seen_at TEXT);"
        "CREATE TABLE artifacts ("
        "  artifact_id TEXT PRIMARY KEY, document_id TEXT,"
        "  source_id TEXT, artifact_role TEXT, path TEXT,"
        "  content_sha256 TEXT, byte_size INTEGER, mime_type TEXT,"
        "  generator_name TEXT, generator_version TEXT, status TEXT,"
        "  error TEXT, metadata_json TEXT, created_at TEXT);"
    )
    meta_bindable = json.dumps({
        "schema_version": "1.0", "source_sha256": content_sha})
    meta_unbound = json.dumps({
        "schema_version": "1.0", "source_sha256": "wrong_sha"})
    con.execute(
        "INSERT INTO sources VALUES (?, ?, ?, ?, ?)",
        ("s1", content_sha, len(b"fake-pdf-content-for-test"), "application/pdf", "2026-01-01"))
    con.execute(
        "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("d1", "s1", "Acme 2025", "active", "file", "annual_report", 10,
         '{"schema_version":"1.0"}', "2026-01-01", "2026-01-01"))
    # bindable: real file at path inside allowed_roots, valid metadata
    con.execute(
        "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("a1", "d1", "s1", "normalizer", str(artifact_file),
         content_sha, len(b"fake-pdf-content-for-test"), "application/pdf",
         "source_catalog_normalizer", "1.0.0", "completed", None,
         meta_bindable, "2026-01-01T00:00:00Z"))
    # legacy_unbound: source_sha256 mismatch (provenance unprovable)
    con.execute(
        "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("a2", "d1", "s1", "summary", "/nonexistent/path/b.pdf",
         "bbb", 10, "pdf", "source_catalog_llm_summary", "1.0.0", "completed", None,
         meta_unbound, "2026-01-01T00:00:00Z"))
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# C1 — real-catalog dry-run
# ---------------------------------------------------------------------------


@pytest.mark.timeout(900)
def test_c1_dry_run_real_catalog():
    before = _row_counts(PRODUCTION_CATALOG)
    result = run_artifact_backfill(
        PRODUCTION_CATALOG, registry=_REGISTRY,
        allowed_roots=(PRODUCTION_CATALOG.parent.parent / "companies",), now=NOW,
        mode="dry-run")
    assert result.input > 0
    assert result.closed, f"not closed: {result.input} {result.bindable} {result.legacy_unbound}"
    h1 = result.result_hash
    result2 = run_artifact_backfill(
        PRODUCTION_CATALOG, registry=_REGISTRY,
        allowed_roots=(PRODUCTION_CATALOG.parent.parent / "companies",), now=NOW,
        mode="dry-run")
    assert result2.result_hash == h1, "result_hash not stable"
    assert _row_counts(PRODUCTION_CATALOG) == before


# ---------------------------------------------------------------------------
# C2–C4 — temp catalog
# ---------------------------------------------------------------------------


def test_c2_apply_shadow_bindings(tmp_path):
    cat = tmp_path / "cat.sqlite3"
    root = tmp_path / "data"
    _seed_catalog(cat, root)
    artifacts_before = _table_count(cat, "artifacts")
    result = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(root,), now=NOW, mode="apply")
    assert result.closed
    assert result.bindable >= 1, "no bindable artifacts"
    assert result.created
    assert _table_count(cat, "artifacts") == artifacts_before, "zero-delete violation"
    assert _table_count(cat, "artifact_bindings") >= 1


def test_c3_idempotent_reapply(tmp_path):
    cat = tmp_path / "cat.sqlite3"
    root = tmp_path / "data"
    _seed_catalog(cat, root)
    first = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(root,), now=NOW, mode="apply")
    assert first.skipped_already_bound == 0
    assert first.created
    second = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(root,), now=NOW, mode="apply")
    assert second.skipped_already_bound > 0, "second apply must skip already-bound"
    assert second.created == []
    h1 = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(root,), now=NOW, mode="dry-run").result_hash
    h2 = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(root,), now=NOW, mode="dry-run").result_hash
    assert h1 == h2


def test_c4_only_bindable_get_bindings(tmp_path):
    cat = tmp_path / "cat.sqlite3"
    root = tmp_path / "data"
    _seed_catalog(cat, root)
    result = run_artifact_backfill(
        cat, registry=_REGISTRY, allowed_roots=(root,), now=NOW, mode="apply")
    con = sqlite3.connect(f"file:{cat}?mode=ro", uri=True, timeout=30)
    try:
        bound_ids = {r[0] for r in con.execute(
            "SELECT artifact_id FROM artifact_bindings").fetchall()}
        bindable_ids = {r["artifact_id"] for r in result.rows if r["bucket"] == "bindable"}
        assert bound_ids == bindable_ids
    finally:
        con.close()
