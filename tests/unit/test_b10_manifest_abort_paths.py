"""B10 / B-VR-B10R4-01: a damaged manifest column is a per-document failure, not a dead run.

The review measured that `SourceManifest.from_dict(json.loads(column))` sat in the MAIN path of
`normalize_catalog` and of `backfill_text_fingerprints` with no enclosing try, so a damaged
manifest aborted the WHOLE run and starved every document queued behind it - and it needed no
parser failure to fire (bad JSON -> JSONDecodeError, "{}" -> SourceManifestError, NULL ->
TypeError).

These tests pin BOTH halves: the helper's never-raises contract, and the run-level behaviour
that a healthy document behind the damaged one still gets normalized.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from company_wiki.source_catalog.config import CatalogConfig
from company_wiki.source_catalog.models import RootSpec
from company_wiki.source_catalog.normalizer import _manifest_from_column, normalize_catalog
from company_wiki.source_catalog.store import CatalogStore
from company_wiki.source_contract.source_manifest import source_id_for_sha256

ROOT = "urn:company-wiki:root:sha256:" + "r" * 64
BODY = b"# Test Filing\n\nTest Filing body text\n"
SHA = hashlib.sha256(BODY).hexdigest()
SRC = source_id_for_sha256(SHA)


def _manifest(sha: str, original_path: str = "reports/x.md") -> dict:
    return {
        "schema_version": "1.0.0", "source_id": SRC, "entity_ids": ["test-issuer"],
        "original_path": original_path, "content_sha256": sha,
        "source_type": "regulatory_filing", "published_date": "2026-06-18",
        "retrieved_at": "2026-06-18T00:00:00Z", "collector_name": "test",
        "collector_version": "1.0.0", "mime_type": "text/markdown", "byte_size": len(BODY),
        "immutable_status": "verified",
    }


def _insert(connection, table: str, values: dict) -> None:
    have = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    use = {key: value for key, value in values.items() if key in have}
    connection.execute(
        f"INSERT INTO {table} ({','.join(use)}) VALUES ({','.join('?' * len(use))})",
        tuple(use.values()),
    )


def test_b10_manifest_helper_never_raises_and_codes_the_problem() -> None:
    for raw, expected in (("not json", "manifest_column_unreadable"), ("{}", "manifest_invalid"),
                          (None, "manifest_invalid"), ("[1]", "manifest_column_not_object")):
        manifest, problem = _manifest_from_column(raw)
        assert manifest is None and problem == expected, (raw, manifest, problem)
    manifest, problem = _manifest_from_column(json.dumps(_manifest(SHA)))
    assert problem is None and manifest is not None, "a valid manifest must still load"


def _seed(tmp: Path) -> tuple[CatalogConfig, CatalogStore]:
    (tmp / "raw" / "reports").mkdir(parents=True, exist_ok=True)
    (tmp / "raw" / "reports" / "a.md").write_bytes(BODY)
    (tmp / "raw" / "reports" / "b.md").write_bytes(BODY)
    config = CatalogConfig(
        project_root=tmp, catalog_dir=tmp / "catalog",
        roots=(RootSpec(root_id=ROOT, path=tmp / "raw", kind="company_raw", priority=1),),
    )
    store = CatalogStore(tmp / "catalog.sqlite3")
    with store.transaction() as connection:
        _insert(connection, "roots", {"root_id": ROOT, "path": str(tmp / "raw"),
                                      "kind": "company_raw", "priority": 1})
        _insert(connection, "sources", {
            "source_id": SRC, "content_sha256": SHA, "byte_size": len(BODY),
            "mime_type": "text/markdown", "relative_path": "reports/a.md", "root_id": ROOT,
            "source_type": "regulatory_filing", "source_status": "active",
            "first_seen_at": "2026-01-01T00:00:00Z", "last_seen_at": "2026-01-01T00:00:00Z"})
        # Document A carries the DAMAGED manifest column; document B is healthy and queued
        # behind it, so a run abort would be visible as B having no normalized artifact.
        for suffix, manifest_json in (("a", "not json at all"),
                                      ("b", json.dumps(_manifest(SHA, "reports/b.md")))):
            document_id = "urn:company-wiki:document:sha256:" + (suffix * 64)
            _insert(connection, "documents", {
                "document_id": document_id, "primary_source_id": SRC, "title": "Test Filing",
                "source_type": "regulatory_filing", "document_kind": "annual_report",
                "published_date": "2026-06-18", "source_status": "active",
                "metadata_priority": 1, "metadata_json": "{}",
                "first_seen_at": "2026-01-01T00:00:00Z", "last_seen_at": "2026-01-01T00:00:00Z"})
            _insert(connection, "locations", {
                "location_id": f"loc-{suffix}", "root_id": ROOT,
                "relative_path": f"reports/{suffix}.md",
                "absolute_path": str(tmp / "raw" / "reports" / f"{suffix}.md"),
                "source_id": SRC, "document_id": document_id, "role": "original_primary",
                "location_status": "active", "last_seen_run": "run-1",
                "manifest_json": manifest_json, "metadata_json": "{}"})
    return config, store


def test_b10_damaged_manifest_is_a_per_document_failure(tmp_path: Path) -> None:
    config, store = _seed(tmp_path)
    report = normalize_catalog(config, store, force=True, retry_limit=3)
    # The report field is `terminal_reasons` (the module maps its internal `failure_reasons`
    # into it at the end) - r3 flagged the field-name confusion, so this test uses the real one.
    reasons = dict(getattr(report, "terminal_reasons", {}) or {})
    manifest_reasons = {key: value for key, value in reasons.items()
                        if key.startswith("manifest_")}
    assert manifest_reasons, (
        f"the damaged manifest must be recorded as a per-document failure; got {reasons}"
    )
    assert getattr(report, "completed", 0) >= 1, (
        "the HEALTHY document queued behind the damaged one must still be normalized - a run "
        "abort would leave it unprocessed (B-VR-B10R4-01)"
    )
    artifacts = store.fetchall("SELECT COUNT(*) AS n FROM artifacts WHERE artifact_role='normalized'")
    assert artifacts[0]["n"] >= 1, "no normalized artifact row was written"


def test_b10_missing_primary_file_is_a_per_document_failure(tmp_path: Path) -> None:
    """R1 / F-B10R2-MISSINGFILE: a document whose primary file is missing on disk must be
    recorded as a per-document failure, not abort the whole run and starve the healthy
    document behind it (the reviewer measured the escape: SourceManifestMismatchError from
    IngestService.ingest -> manifest.verify_file)."""
    (tmp_path / "raw" / "reports").mkdir(parents=True, exist_ok=True)
    # Write ONLY the healthy document's file; the damaged one's file does not exist.
    (tmp_path / "raw" / "reports" / "healthy.md").write_bytes(BODY)
    config = CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec(root_id=ROOT, path=tmp_path / "raw", kind="company_raw", priority=1),),
    )
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    with store.transaction() as connection:
        _insert(connection, "roots", {"root_id": ROOT, "path": str(tmp_path / "raw"),
                                      "kind": "company_raw", "priority": 1})
        _insert(connection, "sources", {
            "source_id": SRC, "content_sha256": SHA, "byte_size": len(BODY),
            "mime_type": "text/markdown", "relative_path": "reports/healthy.md",
            "root_id": ROOT, "source_type": "regulatory_filing", "source_status": "active",
            "first_seen_at": "2026-01-01T00:00:00Z", "last_seen_at": "2026-01-01T00:00:00Z"})
        _insert(connection, "sources", {
            "source_id": "urn:company-wiki:source:sha256:" + "d" * 64,
            "content_sha256": "d" * 64, "byte_size": 10, "mime_type": "text/markdown",
            "relative_path": "reports/missing.md", "root_id": ROOT,
            "source_type": "regulatory_filing", "source_status": "active",
            "first_seen_at": "2026-01-01T00:00:00Z", "last_seen_at": "2026-01-01T00:00:00Z"})
        manifest_healthy = _manifest(SHA, "reports/healthy.md")
        for suffix, source_id, manifest_json in (
            ("missing", "urn:company-wiki:source:sha256:" + "d" * 64,
             json.dumps(_manifest("d" * 64, "reports/missing.md"))),
            ("healthy", SRC, json.dumps(manifest_healthy)),
        ):
            document_id = "urn:company-wiki:document:sha256:" + (suffix * 64)
            _insert(connection, "documents", {
                "document_id": document_id, "primary_source_id": source_id,
                "title": "Test Filing", "source_type": "regulatory_filing",
                "document_kind": "annual_report", "published_date": "2026-06-18",
                "source_status": "active", "metadata_priority": 1, "metadata_json": "{}",
                "first_seen_at": "2026-01-01T00:00:00Z", "last_seen_at": "2026-01-01T00:00:00Z"})
            _insert(connection, "locations", {
                "location_id": f"loc-{suffix}", "root_id": ROOT,
                "relative_path": f"reports/{suffix}.md",
                "absolute_path": str(tmp_path / "raw" / "reports" / f"{suffix}.md"),
                "source_id": source_id, "document_id": document_id,
                "role": "original_primary", "location_status": "active",
                "last_seen_run": "run-1", "manifest_json": manifest_json, "metadata_json": "{}"})
    report = normalize_catalog(config, store, force=True, retry_limit=3)
    reasons = dict(getattr(report, "terminal_reasons", {}) or {})
    missing_reasons = {key: value for key, value in reasons.items()
                       if key == "primary_file_missing"}
    assert missing_reasons, (
        f"the missing-file document must be recorded as primary_file_missing; got {reasons}"
    )
    assert getattr(report, "completed", 0) >= 1, (
        "the HEALTHY document queued behind the missing one must still be normalized - a "
        "run abort would leave it unprocessed (R1 / F-B10R2-MISSINGFILE)"
    )
    artifacts = store.fetchall("SELECT COUNT(*) AS n FROM artifacts WHERE artifact_role='normalized'")
    assert artifacts[0]["n"] >= 1, "no normalized artifact row was written"
