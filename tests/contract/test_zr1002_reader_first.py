"""ZR-1002 acceptance tests: Reader-first release — the zero-write
``CatalogReader`` path goes live while the writer keeps legacy behavior
(read shadow/golden/SLO; rollback routing; no schema/data migration).

  C1  golden: after apply_activation the reader path (ReadOnlyCatalogReader
      + resolver) returns EXACTLY the golden values that the pre-activation
      store queries returned — the active assertions are what the reader
      consumes (shadow -> active, no byte drift).
  C2  writer unchanged: after activation the legacy writer still works
      (new assertion upsert + activation journal rows intact).
  C3  SLO: reader queries stay within a frozen latency budget.
  C4  rollback routing: rollback_activation flips visibility back to
      shadow — active rows are invisible to the reader again, rows are NOT
      deleted, and a second rollback of the same receipt is rejected.
  C5  no schema/data migration: catalog schema version and row counts are
      unchanged across activate -> golden -> rollback.

Hermetic: temporary catalog only; production catalog never touched.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.activation import (  # noqa: E402
    ActivationError,
    apply_activation,
    rollback_activation,
)
from company_wiki.source_catalog.assertion_service import (  # noqa: E402
    upsert_verified_assertion,
)
from company_wiki.source_catalog.normalized_meta import canonical_hash  # noqa: E402
from company_wiki.source_catalog.reader import ReadOnlyCatalogReader  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402

POLICY_HASH = "b" * 64
READER_SLO_SECONDS = 5.0
TABLE = "source_metadata_assertions"


def _seed(store: CatalogStore) -> list[str]:
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) "
            "VALUES ('s1', 'src-hash', 10, 'application/pdf', '2026-01-01')")
        conn.execute(
            "INSERT INTO documents (document_id, title, source_status, "
            "source_type, document_kind, metadata_priority, metadata_json, "
            "first_seen_at, last_seen_at) "
            "VALUES ('d1', 'Acme 2025', 'active', 'file', 'annual_report', "
            "10, '{}', '2026-01-01', '2026-01-01')")
    normalized = {
        "schema_version": "2.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "CN",
        "security_id": "601899",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "provider": "cninfo",
        "provider_document_id": "1225023658",
        "content_sha256": "0" * 64,
        "adapter_id": "sidecar_filing_v1",
        "adapter_version": "1.0.0",
        "normalization_status": "capture_ready",
    }
    normalized["metadata_sha256"] = canonical_hash(normalized)
    assertion = upsert_verified_assertion(
        store, source_id="s1", document_id="d1",
        content_sha256="0" * 64,
        adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized), normalized=normalized,
    )
    return [assertion["assertion_id"]]


def _golden(store: CatalogStore, assertion_id: str) -> dict:
    row = store.fetchone(
        f"SELECT entity, security_id, fiscal_year, provider "
        f"FROM {TABLE} WHERE assertion_id=?", (assertion_id,))
    return dict(row)


def _reader_rows(db_path: Path, assertion_id: str) -> list[dict]:
    reader = ReadOnlyCatalogReader(db_path)
    rows = reader.fetchall(
        f"SELECT entity, security_id, fiscal_year, provider "
        f"FROM {TABLE} WHERE assertion_id=? AND visibility_state='active'",
        (assertion_id,))
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# C1 — golden: reader path returns exactly the pre-activation values
# ---------------------------------------------------------------------------


def test_c1_reader_path_matches_golden_after_activation(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    golden = _golden(store, assertion_ids[0])
    assert _reader_rows(db_path, assertion_ids[0]) == []
    apply_activation(
        store, epoch="2026-08-23T00:00:00Z", cohort="zr1002",
        assertion_ids=assertion_ids, policy_hash=POLICY_HASH,
        reviewer="zr1002-implementer", reason="reader-first release",
        current_policy_hash=POLICY_HASH)
    rows = _reader_rows(db_path, assertion_ids[0])
    assert len(rows) == 1
    assert rows[0]["entity"] == golden["entity"]
    assert rows[0]["security_id"] == golden["security_id"]
    assert rows[0]["fiscal_year"] == golden["fiscal_year"]
    assert rows[0]["provider"] == golden["provider"]


# ---------------------------------------------------------------------------
# C2 — writer keeps legacy behavior
# ---------------------------------------------------------------------------


def test_c2_writer_works_after_activation(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    apply_activation(
        store, epoch="2026-08-23T00:00:00Z", cohort="zr1002",
        assertion_ids=assertion_ids, policy_hash=POLICY_HASH,
        reviewer="zr1002-implementer", reason="reader-first release",
        current_policy_hash=POLICY_HASH)
    normalized2 = {
        "schema_version": "2.0",
        "canonical_entity_id": "ent-acme2",
        "display_name": "Acme Two",
        "market": "HK",
        "security_id": "1548",
        "document_kind": "annual_report",
        "fiscal_year": 2021,
        "period_end": "2021-12-31",
        "provider": "hkexnews",
        "provider_document_id": "10225111",
        "content_sha256": "1" * 64,
        "adapter_id": "sidecar_filing_v1",
        "adapter_version": "1.0.0",
        "normalization_status": "capture_ready",
    }
    normalized2["metadata_sha256"] = canonical_hash(normalized2)
    new = upsert_verified_assertion(
        store, source_id="s1", document_id="d1",
        content_sha256="1" * 64,
        adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized2), normalized=normalized2,
    )
    assert store.fetchone(
        f"SELECT 1 FROM {TABLE} WHERE assertion_id=?", (new["assertion_id"],)) is not None
    journal = store.fetchone(
        "SELECT COUNT(*) AS n FROM activation_journal WHERE kind='apply'")
    assert journal["n"] == 1


# ---------------------------------------------------------------------------
# C3 — SLO: reader queries within budget
# ---------------------------------------------------------------------------


def test_c3_reader_query_within_slo(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    apply_activation(
        store, epoch="2026-08-23T00:00:00Z", cohort="zr1002",
        assertion_ids=assertion_ids, policy_hash=POLICY_HASH,
        reviewer="zr1002-implementer", reason="reader-first release",
        current_policy_hash=POLICY_HASH)
    reader = ReadOnlyCatalogReader(db_path)
    started = time.perf_counter()
    reader.fetchall(f"SELECT COUNT(*) AS n FROM {TABLE}")
    elapsed = time.perf_counter() - started
    assert elapsed < READER_SLO_SECONDS, f"reader query took {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# C4 — rollback routing
# ---------------------------------------------------------------------------


def test_c4_rollback_returns_to_shadow_without_deleting(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    receipt = apply_activation(
        store, epoch="2026-08-23T00:00:00Z", cohort="zr1002",
        assertion_ids=assertion_ids, policy_hash=POLICY_HASH,
        reviewer="zr1002-implementer", reason="reader-first release",
        current_policy_hash=POLICY_HASH)
    assert len(_reader_rows(db_path, assertion_ids[0])) == 1
    rollback_activation(
        store, receipt_id=receipt["receipt_id"], cohort="zr1002",
        reviewer="zr1002-implementer", reason="release rollback")
    assert _reader_rows(db_path, assertion_ids[0]) == []
    assert store.fetchone(
        f"SELECT 1 FROM {TABLE} WHERE assertion_id=?", (assertion_ids[0],)) is not None
    with pytest.raises(ActivationError):
        rollback_activation(
            store, receipt_id=receipt["receipt_id"], cohort="zr1002",
            reviewer="zr1002-implementer", reason="double rollback")


# ---------------------------------------------------------------------------
# C5 — no schema/data migration
# ---------------------------------------------------------------------------


def test_c5_no_schema_or_row_count_change(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    schema_before = store.fetchone(
        "SELECT value FROM catalog_meta WHERE key='schema_version'")
    rows_before = store.fetchone(
        f"SELECT COUNT(*) AS n FROM {TABLE}")["n"]
    receipt = apply_activation(
        store, epoch="2026-08-23T00:00:00Z", cohort="zr1002",
        assertion_ids=assertion_ids, policy_hash=POLICY_HASH,
        reviewer="zr1002-implementer", reason="reader-first release",
        current_policy_hash=POLICY_HASH)
    rollback_activation(
        store, receipt_id=receipt["receipt_id"], cohort="zr1002",
        reviewer="zr1002-implementer", reason="release rollback")
    schema_after = store.fetchone(
        "SELECT value FROM catalog_meta WHERE key='schema_version'")
    rows_after = store.fetchone(
        f"SELECT COUNT(*) AS n FROM {TABLE}")["n"]
    assert schema_before["value"] == schema_after["value"]
    assert rows_before == rows_after
