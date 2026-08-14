"""ZR-202 gate tests: typed read queries on the zero-write CatalogReader.

Seeding happens through CatalogStore's own transaction (the TEST may write;
the READER never does).  Every typed method is exercised against seeded
rows, schema mismatch fails closed, and query_only stays True.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from company_wiki.source_catalog.reader import (
    CatalogReaderUnavailable,
    ReadOnlyCatalogReader,
)
from company_wiki.source_catalog.store import CatalogStore


def _seed_typed(tmp_path: Path) -> Path:
    db = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db)
    source_id = "src-1"
    doc_id = "doc-1"
    doc2_id = "doc-2"
    entity_id = "ent-zijin"
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources(source_id, content_sha256, byte_size, mime_type, first_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (source_id, "a" * 64, 123, "application/pdf", "2026-01-01T00:00:00Z"),
        )
        for did, kind, title in (
            (doc_id, "annual_report", "Zijin Annual 2025"),
            (doc2_id, "broker_research", "Broker note"),
        ):
            conn.execute(
                "INSERT INTO documents(document_id, primary_source_id, title, source_type, "
                "document_kind, published_date, source_status, metadata_priority, metadata_json, "
                "text_fingerprint, first_seen_at, last_seen_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    did,
                    source_id if did == doc_id else None,
                    title,
                    "pdf",
                    kind,
                    "2026-03-20" if did == doc_id else None,
                    "active" if did == doc_id else "pending",
                    0,
                    "{}",
                    "",
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:00Z",
                ),
            )
        conn.execute(
            "INSERT INTO artifacts(artifact_id, document_id, source_id, artifact_role, path, "
            "content_sha256, byte_size, mime_type, generator_name, generator_version, status, "
            "error, metadata_json, created_at, schema_version, source_sha256) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "art-1",
                doc_id,
                source_id,
                "normalized",
                "artifacts/doc-1/normalized.md",
                "b" * 64,
                10,
                "text/markdown",
                "source_catalog_normalizer",
                "1.0",
                "completed",
                None,
                "{}",
                "2026-01-02T00:00:00Z",
                "1.0",
                "a" * 64,
            ),
        )
        conn.execute(
            "INSERT INTO roots(root_id, path, kind, priority, last_scan_run, last_scanned_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("company_raw", "C:/tmp/companies", "company_raw", 10, None, None),
        )
        conn.execute(
            "INSERT INTO locations(location_id, root_id, relative_path, absolute_path, "
            "source_id, document_id, role, location_status, observed_size, observed_mtime_ns, "
            "last_seen_run, manifest_json, metadata_json, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "loc-1",
                "company_raw",
                "rel/annual.pdf",
                "abs/annual.pdf",
                source_id,
                doc_id,
                "original_primary",
                "active",
                123,
                1,
                "scan-1",
                None,
                "{}",
                None,
            ),
        )
        conn.execute(
            "INSERT INTO entities(entity_id, name, entity_kind) VALUES (?, ?, ?)",
            (entity_id, "紫金矿业集团股份有限公司", "company"),
        )
        conn.execute(
            "INSERT INTO document_entities(document_id, entity_id, confidence, method) "
            "VALUES (?, ?, ?, ?)",
            (doc_id, entity_id, 1.0, "company_raw_path"),
        )
    del store
    return db


@pytest.fixture()
def seeded(tmp_path: Path) -> Path:
    return _seed_typed(tmp_path)


def test_query_only_property_is_true(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        assert reader.query_only is True


def test_document_typed_query(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        row = reader.document("doc-1")
        assert row is not None
        assert row["document_kind"] == "annual_report"
        assert reader.document("missing") is None


def test_source_sha_typed_query(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        assert reader.source_sha("src-1") == "a" * 64
        assert reader.source_sha("missing") is None


def test_artifacts_for_typed_query(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        rows = reader.artifacts_for("doc-1")
        assert len(rows) == 1
        assert rows[0]["artifact_role"] == "normalized"
        assert reader.artifacts_for("missing") == []


def test_location_counts_typed_query(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        assert reader.location_counts("company_raw") == {"active": 1}
        assert reader.location_counts("dropbox_stock") == {}


def test_status_typed_query(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        status = reader.status()
        assert set(status) == {
            "sources",
            "documents",
            "active_locations",
            "missing_locations",
            "normalized_artifacts",
            "summary_artifacts",
            "llm_summary_artifacts",
            "evidence_spans",
        }
        assert status["documents"] == 2
        assert status["active_locations"] == 1


def test_query_filters(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        active = reader.query()
        assert {row["document_id"] for row in active} == {"doc-1"}
        kind = reader.query(document_kind="broker_research", source_status="pending")
        assert [row["document_id"] for row in kind] == ["doc-2"]
        text = reader.query(text="Zijin")
        assert [row["document_id"] for row in text] == ["doc-1"]


def test_entities_like_identify(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        rows = reader.entities_like("紫金")
        assert len(rows) == 1
        assert rows[0]["entity_id"] == "ent-zijin"
        assert rows[0]["docs"] == 1


def test_resolve_handle_and_drift_fail_closed(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        handle = reader.resolve_handle("doc-1")
        assert handle is not None
        assert handle["content_sha256"] == "a" * 64
        # claimed hash drift -> None (fail closed)
        assert reader.resolve_handle("doc-1", expected_content_sha256="f" * 64) is None
        assert reader.resolve_handle("missing") is None


def test_bundle_typed_query(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        bundle = reader.bundle(
            "doc-1",
            registry={},
            allowed_roots=(),
            now="2026-03-21T00:00:00Z",
        )
        assert bundle is not None
        assert bundle["source"]["document_id"] == "doc-1"
        assert (
            reader.bundle(
                "doc-1",
                registry={},
                allowed_roots=(),
                now="2026-03-21T00:00:00Z",
                expected_content_sha256="f" * 64,
            )
            is None
        )


def test_health_typed_query(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        health = reader.health()
        assert health["query_only"] is True
        assert health["status"]["documents"] == 2
        assert isinstance(health["scan_health"], dict)


def test_schema_mismatch_fails_closed(seeded: Path) -> None:
    store = CatalogStore(seeded)
    with store.transaction() as conn:
        conn.execute("UPDATE catalog_meta SET value='9.9.9' WHERE key='schema_version'")
    del store
    with ReadOnlyCatalogReader(seeded) as reader:
        with pytest.raises(CatalogReaderUnavailable):
            reader.schema_version()
        with pytest.raises(CatalogReaderUnavailable):
            reader.health()


def test_no_public_write_surface_after_typed_layer(seeded: Path) -> None:
    with ReadOnlyCatalogReader(seeded) as reader:
        public = {name for name in dir(reader) if not name.startswith("_")}
        forbidden = {"execute", "executescript", "commit", "rollback", "migrate"}
        assert not (public & forbidden), public & forbidden
