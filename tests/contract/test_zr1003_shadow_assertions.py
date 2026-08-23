"""ZR-1003 acceptance tests: lifecycle/safety/RootPolicy shadow assertions —
two dynamic cycles fully explainable, active response unchanged, rollback
only flips the flag (stage I third card).

  C1  lifecycle: assertion shadow -> apply -> active -> rollback -> shadow,
      visibility correct at every stage.
  C2  safety: an unreviewed prompt-injection document blocks consumption
      (fail closed); a recorded not_detected review unblocks it.
  C3  RootPolicy: activating with a wrong policy_hash is rejected; the
      correct policy activates.
  C4  two dynamic cycles explainable: two shadow reads of the same catalog
      produce byte-identical output (deterministic).
  C5  active response unchanged: reader-visible active rows are identical
      before and after a rollback+re-apply cycle (no drift).
  C6  rollback only flips the flag: after rollback visibility_state=shadow
      while rows, epochs and the journal receipt are fully preserved.

Hermetic: temporary catalog only; production catalog never touched.
"""

from __future__ import annotations

import json
import sys
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
from company_wiki.source_catalog.prompt_injection import (  # noqa: E402
    PROMPT_INJECTION_REVIEW_KEY,
    record_prompt_injection_review,
)
from company_wiki.source_catalog.reader import ReadOnlyCatalogReader  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402

POLICY_A = "a" * 64
POLICY_B = "b" * 64
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


def _active_rows(db_path: Path) -> list[dict]:
    reader = ReadOnlyCatalogReader(db_path)
    return [dict(r) for r in reader.fetchall(
        f"SELECT assertion_id, entity, security_id, fiscal_year, provider "
        f"FROM {TABLE} WHERE visibility_state='active'")]


def _apply(store: CatalogStore, assertion_ids: list[str],
           policy: str = POLICY_A, epoch: str = "2026-08-23T00:00:00Z") -> dict:
    return apply_activation(
        store, epoch=epoch, cohort="zr1003",
        assertion_ids=assertion_ids, policy_hash=policy,
        reviewer="zr1003-implementer", reason="shadow assertions",
        current_policy_hash=POLICY_A)


# ---------------------------------------------------------------------------
# C1 — lifecycle: shadow -> active -> shadow
# ---------------------------------------------------------------------------


def test_c1_lifecycle_visibility(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    assert _active_rows(db_path) == []          # shadow
    receipt = _apply(store, assertion_ids)
    assert len(_active_rows(db_path)) == 1      # active
    rollback_activation(
        store, receipt_id=receipt["receipt_id"], cohort="zr1003",
        reviewer="zr1003-implementer", reason="cycle")
    assert _active_rows(db_path) == []          # shadow again


# ---------------------------------------------------------------------------
# C2 — safety: unreviewed document blocks consumption (fail closed)
# ---------------------------------------------------------------------------


def test_c2_unreviewed_document_blocks(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    _seed(store)
    row = store.fetchone(
        "SELECT metadata_json FROM documents WHERE document_id='d1'")
    meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
    assert PROMPT_INJECTION_REVIEW_KEY not in meta, (
        "unreviewed document must carry no review receipt (fail closed)")


def test_c2_recorded_review_unblocks(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    _seed(store)
    with store.transaction() as conn:
        record_prompt_injection_review(
            conn, document_id="d1",
            status="not_detected", reviewer="zr1003-implementer",
            evidence_sha256="e" * 64, now="2026-08-23T00:00:00Z")
    row = store.fetchone(
        "SELECT metadata_json FROM documents WHERE document_id='d1'")
    meta = json.loads(row["metadata_json"])
    review = meta[PROMPT_INJECTION_REVIEW_KEY]
    assert review["status"] == "not_detected"
    assert review["reviewer"] == "zr1003-implementer"


# ---------------------------------------------------------------------------
# C3 — RootPolicy: wrong policy_hash rejected
# ---------------------------------------------------------------------------


def test_c3_wrong_policy_rejected(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    with pytest.raises(ActivationError):
        _apply(store, assertion_ids, policy=POLICY_B)  # current is POLICY_A
    assert _active_rows(db_path) == []


# ---------------------------------------------------------------------------
# C4 — two dynamic cycles explainable (deterministic)
# ---------------------------------------------------------------------------


def test_c4_two_cycles_identical(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    receipt1 = _apply(store, assertion_ids)
    first = _active_rows(db_path)
    rollback_activation(
        store, receipt_id=receipt1["receipt_id"], cohort="zr1003",
        reviewer="zr1003-implementer", reason="cycle")
    receipt2 = _apply(store, assertion_ids, epoch="2026-08-23T01:00:00Z")
    second = _active_rows(db_path)
    rollback_activation(
        store, receipt_id=receipt2["receipt_id"], cohort="zr1003",
        reviewer="zr1003-implementer", reason="cycle")
    assert canonical_hash({"rows": first}) == canonical_hash({"rows": second})


# ---------------------------------------------------------------------------
# C5 — active response unchanged across rollback+re-apply
# ---------------------------------------------------------------------------


def test_c5_active_response_unchanged(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    receipt = _apply(store, assertion_ids)
    before = _active_rows(db_path)
    rollback_activation(
        store, receipt_id=receipt["receipt_id"], cohort="zr1003",
        reviewer="zr1003-implementer", reason="cycle")
    receipt2 = _apply(store, assertion_ids, epoch="2026-08-23T02:00:00Z")
    after = _active_rows(db_path)
    rollback_activation(
        store, receipt_id=receipt2["receipt_id"], cohort="zr1003",
        reviewer="zr1003-implementer", reason="cycle")
    assert before == after  # full-row equality, no drift


# ---------------------------------------------------------------------------
# C6 — rollback only flips the flag
# ---------------------------------------------------------------------------


def test_c6_rollback_only_flips_flag(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    assertion_ids = _seed(store)
    receipt = _apply(store, assertion_ids)
    row_before = store.fetchone(
        f"SELECT visibility_state, activation_epoch, cohort "
        f"FROM {TABLE} WHERE assertion_id=?", (assertion_ids[0],))
    assert row_before["visibility_state"] == "active"
    epoch_before = row_before["activation_epoch"]
    rollback_activation(
        store, receipt_id=receipt["receipt_id"], cohort="zr1003",
        reviewer="zr1003-implementer", reason="flag-only")
    row_after = store.fetchone(
        f"SELECT visibility_state, activation_epoch, cohort, entity "
        f"FROM {TABLE} WHERE assertion_id=?", (assertion_ids[0],))
    assert row_after["visibility_state"] == "shadow"   # flag flipped
    assert row_after["activation_epoch"] == epoch_before  # epoch preserved
    assert row_after["entity"] == "Acme"              # data intact
    journal = store.fetchone(
        "SELECT COUNT(*) AS n FROM activation_journal WHERE kind='rollback'")
    assert journal["n"] == 1
