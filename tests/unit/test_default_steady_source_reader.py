"""New catalogs expose verified assertions without a rollout configuration."""

import hashlib
import json

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.policy_2x import export_policy_2x
from company_wiki.source_catalog.runtime_policy import build_snapshot
from company_wiki.source_catalog.source_reader import SourceVersionReader


@pytest.fixture
def indexed_source(tmp_path):
    root = tmp_path / "lake"
    root.mkdir()
    raw = root / "2025.txt"
    body = b"Acme expanded its product portfolio."
    digest = hashlib.sha256(body).hexdigest()
    raw.write_bytes(body)
    raw.with_name(raw.name + ".source.json").write_text(json.dumps({
        "schema_version": "1.0", "canonical_entity_id": "ent-acme",
        "display_name": "Acme", "market": "US", "security_id": "ACME",
        "document_kind": "annual_report", "source_title": "Acme annual report",
        "fiscal_year": 2025, "period_end": "2025-12-31", "filing_date": "2026-02-20",
        "form_type": "10-K", "provider": "sec", "provider_document_id": "doc-1",
        "content_sha256": digest,
    }), encoding="utf-8")
    config = CatalogConfig(tmp_path, tmp_path / "catalog", (
        RootSpec("lake", root, "directory", adapter_id="sidecar_filing_v1",
                 reusable_for_filing=True),
    ), ("directory",))
    catalog = SourceCatalog(config)
    try:
        catalog.scan()
        row = catalog.reader.fetchone(
            "SELECT d.document_id,d.primary_source_id AS source_id FROM documents d "
            "JOIN sources s ON s.source_id=d.primary_source_id WHERE s.content_sha256=?",
            (digest,),
        )
        assert row is not None
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(row["document_id"], row["source_id"], digest)
        yield catalog, reader, ref, raw, body
    finally:
        catalog.close()


@pytest.mark.parametrize("visibility,decision,same_sha", [
    ("active", "verified", True), ("legacy", "verified", True),
    ("shadow", "verified", True), ("candidate", "verified", True),
    ("active", "rejected", True), ("active", "verified", False),
])
def test_default_read_preserves_verified_facts_and_matches_explicit_steady(
    indexed_source, visibility, decision, same_sha,
):
    catalog, reader, ref, raw, body = indexed_source
    policy_path = catalog.config.catalog_dir / "runtime_policy.json"
    with catalog.store.transaction() as conn:
        conn.execute("""INSERT INTO source_metadata_assertions
            (assertion_id,source_id,document_id,content_sha256,evidence_basis,evidence_json,
             decision,created_at,created_by,schema_version,visibility_state,activation_epoch,
             cohort,market,security_id,fiscal_year,period_end,language)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                "default-assertion", ref.source_id, ref.document_id,
                ref.content_sha256 if same_sha else "a" * 64, "verified_bytes", "{}",
                decision, "2026-10-07T00:00:00Z", "test", "2.0", visibility,
                "retired-canary", "retired-cohort", "US", "ACME", 2024, "2024-12-31", "en",
            ))
    before = raw.stat()
    manifest = reader.describe_version(ref)
    accepted = visibility in {"active", "legacy"} and decision == "verified" and same_sha
    assert manifest["fiscal_year"] == (2024 if accepted else 2025)
    assert manifest["period_end"] == ("2024-12-31" if accepted else "2025-12-31")
    assert manifest["title"] == "Acme annual report"
    default_pin = reader.read_policy_sha256()
    assert reader.open_version(ref, expected_read_policy_sha256=default_pin).data == body
    assert not policy_path.exists()  # A read does not manufacture rollout state.
    policy_path.write_text(json.dumps(build_snapshot({
        "schema_version": "2.0", "mode": "steady",
        "policy_hash": export_policy_2x(catalog.config)[0],
        "updated_at": "2026-10-07T00:00:00Z",
    })), encoding="utf-8")
    assert reader.describe_version(ref) == manifest
    assert reader.read_policy_sha256() == default_pin
    assert reader.open_version(ref, expected_read_policy_sha256=default_pin).data == body
    assert raw.stat().st_mtime_ns == before.st_mtime_ns
