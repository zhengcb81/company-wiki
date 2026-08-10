"""WU-801 RED/audit tests: resolver normalized-only metadata (v2 first)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.assertion_service import upsert_verified_assertion  # noqa: E402
from company_wiki.source_catalog.normalized_meta import canonical_hash  # noqa: E402
from company_wiki.source_catalog.resolver import _source_metadata  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402


def _seed_parents(store) -> None:
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) "
            "VALUES ('s1', 'src-hash', 10, 'application/pdf', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO documents (document_id, title, source_status, "
            "source_type, document_kind, metadata_priority, metadata_json, "
            "first_seen_at, last_seen_at) "
            "VALUES ('d1', 'Acme 2025', 'active', 'file', 'annual_report', 10, "
            "'{}', '2026-01-01', '2026-01-01')"
        )




def _activate(store, assertion_id: str) -> None:
    """Simulate R6 cutover: flip a shadow assertion to active visibility
    (FC-202: activation must carry epoch AND cohort)."""
    with store.transaction() as conn:
        conn.execute(
            "UPDATE source_metadata_assertions SET visibility_state='active', "
            "activation_epoch='epoch-1', cohort='cohort-a' WHERE assertion_id=?",
            (assertion_id,),
        )


def _v2_args():
    """FC-202 visibility contract: v2 reader requires pinned epoch + cohort."""
    return dict(reader="v2", current_epoch="epoch-1", active_cohorts=("cohort-a",))


def test_legacy_container_still_reads(tmp_path):
    """v1 行为不变：无 v2 assertion 时读 legacy acquisition 容器。"""
    document = {"metadata": {"acquisition": {"fiscal_year": 2025,
                                             "provider": "example"}}}
    metadata = _source_metadata(document)
    assert metadata["fiscal_year"] == 2025


def test_legacy_empty_when_no_container(tmp_path):
    assert _source_metadata({"metadata": {}}) == {}


def test_v2_assertion_metadata_query(tmp_path):
    from company_wiki.source_catalog.resolver import _v2_assertion_metadata

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    normalized = {
        "schema_version": "2.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "US123",
        "document_kind": "annual_report",
        "fiscal_year": "2025",
        "period_end": "2025-12-31",
        "provider": "example-filing",
        "provider_document_id": "acc-1",
        "content_sha256": "c" * 64,
        "adapter_id": "sidecar_filing_v1",
        "adapter_version": "1.0.0",
        "normalization_status": "capture_ready",
        "evidence": {"fiscal_year": {"origin": "sidecar",
                                     "source_pointer": "fiscal_year"}},
    }
    normalized["metadata_sha256"] = canonical_hash(normalized)
    assertion = upsert_verified_assertion(
        store, source_id="s1", document_id="d1", content_sha256="c" * 64,
        adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized), normalized=normalized,
    )
    _activate(store, assertion["assertion_id"])
    metadata = _v2_assertion_metadata(store, "s1", **_v2_args())
    assert metadata["fiscal_year"] == 2025
    assert metadata["provider"] == "example-filing"
    assert metadata["security_id"] == "US123"


def test_v2_assertion_missing_returns_none(tmp_path):
    from company_wiki.source_catalog.resolver import _v2_assertion_metadata

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    assert _v2_assertion_metadata(store, "s1", **_v2_args()) is None


def test_v2_preferred_over_legacy(tmp_path):
    """WU-801: verified v2 assertion wins over the legacy container."""
    from company_wiki.source_catalog.resolver import _v2_assertion_metadata

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    normalized = {
        "schema_version": "2.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "US123",
        "document_kind": "annual_report",
        "fiscal_year": "2026",
        "period_end": "2026-12-31",
        "provider": "example-filing",
        "provider_document_id": "acc-2",
        "content_sha256": "c" * 64,
        "adapter_id": "sidecar_filing_v1",
        "adapter_version": "1.0.0",
        "normalization_status": "capture_ready",
    }
    normalized["metadata_sha256"] = canonical_hash(normalized)
    assertion = upsert_verified_assertion(
        store, source_id="s1", document_id="d1", content_sha256="c" * 64,
        adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized), normalized=normalized,
    )
    _activate(store, assertion["assertion_id"])
    v2 = _v2_assertion_metadata(store, "s1", **_v2_args())
    assert v2["fiscal_year"] == 2026  # v2 wins over any legacy container
