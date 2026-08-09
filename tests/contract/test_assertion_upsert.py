"""WU-402 RED/audit tests: transactional idempotent assertion upsert
(TX-01..03)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.assertion_service import upsert_verified_assertion  # noqa: E402
from company_wiki.source_catalog.normalized_meta import canonical_hash  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402


def _normalized(**overrides) -> dict:
    fields = {
        "schema_version": "2.0",
        "canonical_entity_id": "ent-1",
        "display_name": "Acme",
        "market": "US",
        "security_id": "US123",
        "document_kind": "annual",
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
    fields.update(overrides)
    fields["metadata_sha256"] = canonical_hash(fields)
    return fields


def _seed_parents(store) -> None:
    """sources/documents 父行（source_metadata_assertions 的 FK 依赖）。"""
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
            "VALUES ('d1', 'Acme 2025', 'active', 'file', 'annual', 10, '{}', "
            "'2026-01-01', '2026-01-01')"
        )


@pytest.fixture()
def store(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    return store


def test_tx01_failure_rolls_back_everything(tmp_path):
    """TX-01: exception inside the transaction => zero partial writes."""
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    with pytest.raises(RuntimeError, match="injected"):
        with store.transaction() as conn:
            conn.execute(
                "UPDATE documents SET title='tampered' WHERE document_id='d1'"
            )
            raise RuntimeError("injected mid-transaction failure")
    # the injected write must not survive
    row = store.fetchone("SELECT title FROM documents WHERE document_id='d1'")
    assert row["title"] != "tampered"


def test_tx02_same_key_upserts_once(store):
    """TX-02: same idempotency key twice => one active verified assertion."""
    normalized = _normalized()
    meta_hash = canonical_hash(normalized)
    first = upsert_verified_assertion(
        store, source_id="s1", document_id="d1",
        content_sha256="c" * 64, adapter_id="sidecar_filing_v1",
        adapter_version="1.0.0", metadata_hash=meta_hash, normalized=normalized,
    )
    second = upsert_verified_assertion(
        store, source_id="s1", document_id="d1",
        content_sha256="c" * 64, adapter_id="sidecar_filing_v1",
        adapter_version="1.0.0", metadata_hash=meta_hash, normalized=normalized,
    )
    assert second["assertion_id"] == first["assertion_id"]
    rows = store.fetchall(
        "SELECT COUNT(*) AS n FROM source_metadata_assertions "
        "WHERE source_id='s1' AND decision='verified'"
    )
    assert rows[0]["n"] == 1


def test_tx03_metadata_change_appends_new_assertion_keeps_old(store):
    """TX-03: different metadata hash => new assertion coexists; history
    is never overwritten (auditable)."""
    first = _normalized()
    first_hash = canonical_hash(first)
    upsert_verified_assertion(
        store, source_id="s1", document_id="d1", content_sha256="c" * 64,
        adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
        metadata_hash=first_hash, normalized=first,
    )
    second = _normalized(fiscal_year="2024")  # metadata changed
    second_hash = canonical_hash(second)
    upsert_verified_assertion(
        store, source_id="s1", document_id="d1", content_sha256="c" * 64,
        adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
        metadata_hash=second_hash, normalized=second,
    )
    rows = store.fetchall(
        "SELECT normalized_sha256 FROM source_metadata_assertions "
        "WHERE source_id='s1' ORDER BY created_at"
    )
    assert len(rows) == 2
    assert {r["normalized_sha256"] for r in rows} == {first_hash, second_hash}


def test_shadow_visibility_never_active(store):
    """WU-404 base: shadow assertions must not be returned by active readers."""
    normalized = _normalized()
    assertion = upsert_verified_assertion(
        store, source_id="s1", document_id="d1", content_sha256="c" * 64,
        adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized), normalized=normalized,
    )
    assert assertion["visibility_state"] == "shadow"
    row = store.fetchone(
        "SELECT visibility_state FROM source_metadata_assertions "
        "WHERE assertion_id=?", (assertion["assertion_id"],)
    )
    assert row["visibility_state"] == "shadow"
