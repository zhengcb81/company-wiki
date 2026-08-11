"""FC-906-c RED: normalize queue must skip documents without an active
original_primary location.

Production reality (2026-08-12): 9506/23521 documents have ZERO active
locations; they sit at the head of the normalize queue forever, fail with
`primary is None` (no artifact row, no last_failed recorded), and starve every
real document behind them. FC-906-c needs real canary documents processed, so
this must be fixed first: the queue SQL excludes documents without an active
original_primary location, and the primary-None branch records diagnostics
(defense in depth — a document slipping past the queue filter must be visible
in the report, not silently counted).

RED before fix: normalize(limit=1) picks the location-less document (priority
ordering) and fails; after fix it picks the location-bearing document.
"""

from __future__ import annotations

import json
from pathlib import Path

from company_wiki.source_catalog import (
    CatalogConfig,
    RootSpec,
    SourceCatalog,
)

# Location-bearing document (real parser path would run; we only assert queue
# ORDER/selection, so a tiny text file is fine and fast).
_SOURCE = "有主营业务内容且包含足够事实陈述的公司简介文本。\n"


def _catalog(tmp_path: Path) -> SourceCatalog:
    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    (source_root / "annual.txt").write_text(_SOURCE, encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("external", source_root, "directory"),),
        )
    )
    catalog.scan()
    return catalog


def _insert_locationless_document(catalog: SourceCatalog) -> str:
    """Insert a documents+sources row with NO locations row (simulates the
    production 9506 docs: source row exists, location deactivated/absent)."""
    import hashlib

    doc_id = "urn:company-wiki:document:sha256:" + hashlib.sha256(
        b"locationless-doc"
    ).hexdigest()
    src_id = "urn:company-wiki:source:sha256:" + hashlib.sha256(
        b"locationless-src"
    ).hexdigest()
    con = catalog.store._connect()
    try:
        con.execute(
            """INSERT INTO sources(source_id, content_sha256, byte_size, mime_type, first_seen_at)
               VALUES(?,?,?,?,datetime('now'))""",
            (src_id, "0" * 64, 100, "text/plain"),
        )
        con.execute(
            """INSERT INTO documents(document_id, primary_source_id, title, source_type,
               document_kind, published_date, source_status, metadata_priority, metadata_json,
               first_seen_at, last_seen_at)
               VALUES(?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))""",
            (doc_id, src_id, "locationless doc", "external",
             "annual_report", "2025-12-31", "active", 100,
             json.dumps({}, ensure_ascii=False)),
        )
        con.commit()
    finally:
        con.close()
    return doc_id


def test_normalize_queue_prefers_document_with_active_location(tmp_path: Path):
    """RED target: the location-bearing doc is processed, the location-less doc
    is NOT picked (it must not sit at the queue head and fail)."""
    catalog = _catalog(tmp_path)
    locless = _insert_locationless_document(catalog)

    report = catalog.normalize(limit=1)
    # The location-less document must NOT be the one picked & failed.
    assert report.failed == 0, (
        f"queue picked the location-less document and failed: {report!r}"
    )
    assert report.completed + report.skipped + report.partial >= 1, (
        "queue must process a real (location-bearing) document instead"
    )
    assert locless not in (report.last_failed_document_id or ""), (
        "location-less document must not be the failed one"
    )
    # The location-less document must not be stuck as 'eligible' forever:
    # a second run with limit=1 must NOT keep failing on it either.
    report2 = catalog.normalize(limit=1)
    assert report2.failed == 0, f"second run still fails: {report2!r}"


def test_primary_none_is_recorded_diagnostically(tmp_path: Path):
    """Defense-in-depth: a doc that slips past the queue filter (active
    original_primary location exists, but its source_id does not match the
    document's primary_source_id) must be VISIBLE in the report — reason,
    document id, path — never a silent failure count."""
    import hashlib

    catalog = _catalog(tmp_path)
    real_doc = catalog.store.fetchone("SELECT document_id FROM documents")["document_id"]

    # Build a doc with an active original_primary location pointing at a
    # DIFFERENT source: EXISTS filter passes, primary check fails.
    doc_id = "urn:company-wiki:document:sha256:" + hashlib.sha256(b"mismatch-doc").hexdigest()
    src_id = "urn:company-wiki:source:sha256:" + hashlib.sha256(b"mismatch-src").hexdigest()
    other_src = "urn:company-wiki:source:sha256:" + hashlib.sha256(b"other-src").hexdigest()
    con = catalog.store._connect()
    try:
        con.execute(
            "INSERT OR IGNORE INTO roots(root_id, path, kind, priority) VALUES(?,?,?,?)",
            ("external", str(tmp_path / "sources"), "directory", 10),
        )
        con.execute(
            """INSERT INTO sources(source_id, content_sha256, byte_size, mime_type, first_seen_at)
               VALUES(?,?,?,?,datetime('now'))""",
            (src_id, "1" * 64, 100, "text/plain"),
        )
        con.execute(
            """INSERT INTO sources(source_id, content_sha256, byte_size, mime_type, first_seen_at)
               VALUES(?,?,?,?,datetime('now'))""",
            (other_src, "2" * 64, 100, "text/plain"),
        )
        con.execute(
            """INSERT INTO documents(document_id, primary_source_id, title, source_type,
               document_kind, published_date, source_status, metadata_priority, metadata_json,
               first_seen_at, last_seen_at)
               VALUES(?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))""",
            (doc_id, src_id, "mismatch doc", "external",
             "annual_report", "2025-12-31", "active", 5,
             json.dumps({}, ensure_ascii=False)),
        )
        loc_id = "loc-" + hashlib.sha256(b"mismatch-loc").hexdigest()
        con.execute(
            """INSERT INTO locations(location_id, root_id, relative_path, absolute_path,
               source_id, document_id, role, location_status, observed_size,
               observed_mtime_ns, last_seen_run, manifest_json, metadata_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (loc_id, "external", "mismatch.txt", str(tmp_path / "mismatch.txt"),
             other_src, doc_id, "original_primary", "active", 100, 0, "scan-x",
             json.dumps({"byte_size": 100}, ensure_ascii=False), "{}"),
        )
        (tmp_path / "mismatch.txt").write_text("x", encoding="utf-8")
        con.commit()
    finally:
        con.close()

    # Make the mismatch doc the ONLY eligible one (give the real doc a
    # completed normalized artifact so it drops out of the queue).
    import sqlite3 as _sqlite3
    con2 = _sqlite3.connect(catalog.store.database_path)
    con2.execute(
        """INSERT INTO artifacts(artifact_id, document_id, source_id, artifact_role, path,
           content_sha256, byte_size, mime_type, generator_name, generator_version,
           status, error, metadata_json, created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'))""",
        ("art-done", real_doc, "src", "normalized", "x", "0" * 64, 1, "text/markdown",
         "source_catalog_normalizer", "1.0.0", "completed", None,
         json.dumps({"schema_version": "1.0"}, ensure_ascii=False)),
    )
    con2.commit()
    con2.close()

    report = catalog.normalize(limit=1)
    assert report.failed == 1, f"mismatch doc must fail primary check: {report!r}"
    assert report.last_failed_document_id == doc_id, (
        "primary-None failure must record the document id"
    )
    assert report.last_failure_code == "no_active_primary_location", (
        "primary-None failure must record the reason code"
    )
