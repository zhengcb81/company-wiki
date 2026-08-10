"""FC-202 RED/acceptance tests: resolver enforces ActivationSnapshot.

Request start pins the RuntimePolicySnapshot (policy hash + activation
epoch + cohort).  The v2 SQL path must filter decision AND visibility AND
epoch AND cohort; flag=false hides active rows even when present (CTRL-01);
epoch mismatch makes rows invisible (CTRL-02); the legacy bridge is only
consulted when the snapshot explicitly allows it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.assertion_service import (  # noqa: E402
    upsert_verified_assertion,
)
from company_wiki.source_catalog.normalized_meta import canonical_hash  # noqa: E402
from company_wiki.source_catalog.resolver import _source_metadata  # noqa: E402
from company_wiki.source_catalog.resolver import _v2_assertion_metadata  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402

_POLICY_HASH = "a" * 64


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


def _seed_active_assertion(store, *, epoch: str, cohort: str | None) -> str:
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
    }
    normalized["metadata_sha256"] = canonical_hash(normalized)
    assertion = upsert_verified_assertion(
        store, source_id="s1", document_id="d1", content_sha256="c" * 64,
        adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized), normalized=normalized,
    )
    with store.transaction() as conn:
        conn.execute(
            "UPDATE source_metadata_assertions SET visibility_state='active', "
            "activation_epoch=?, cohort=? WHERE assertion_id=?",
            (epoch, cohort, assertion["assertion_id"]),
        )
    return assertion["assertion_id"]


def _v1_snapshot(**overrides):
    payload = {
        "schema_version": "1.0",
        "flags": {
            "v2_scan_shadow": False,
            "v2_persist_assertions": False,
            "v2_resolve_shadow": False,
            "v2_resolve_active": False,
            "v2_bundle_active": False,
            "legacy_bridge_enabled": True,
        },
        "current_epoch": None,
        "active_cohorts": [],
        "policy_hash": _POLICY_HASH,
        "updated_at": "2026-08-10T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def _v2_snapshot(**overrides):
    payload = _v1_snapshot(
        flags={
            "v2_scan_shadow": True,
            "v2_persist_assertions": True,
            "v2_resolve_shadow": True,
            "v2_resolve_active": True,
            "v2_bundle_active": False,
            "legacy_bridge_enabled": False,
        },
        current_epoch="epoch-2",
        active_cohorts=["cohort-a"],
    )
    payload.update(overrides)
    return payload


# --- CTRL-01: flag off hides active rows even when present ----------------


def test_ctrl01_v1_reader_never_returns_active_row(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-2", cohort="cohort-a")
    # v1 reader (flag off): active row must be invisible
    assert _v2_assertion_metadata(
        store, "s1", reader="v1", current_epoch=None, active_cohorts=()
    ) is None


def test_ctrl01_source_metadata_flag_off_ignores_active_row(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-2", cohort="cohort-a")
    document = {"source_id": "s1", "metadata": {}}
    # legacy bridge allowed but no legacy container -> empty, NOT the active v2 row
    metadata = _source_metadata(
        document, store=store, reader="v1", current_epoch=None,
        active_cohorts=(), legacy_bridge_allowed=True,
    )
    assert metadata == {}


# --- CTRL-02: activation epoch / cohort mismatch -> invisible --------------


def test_ctrl02_epoch_mismatch_hides_active_row(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-1", cohort="cohort-a")
    # snapshot says current epoch epoch-2: row activated in epoch-1 invisible
    assert _v2_assertion_metadata(
        store, "s1", reader="v2", current_epoch="epoch-2",
        active_cohorts=["cohort-a"],
    ) is None


def test_ctrl02_epoch_match_row_visible(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-2", cohort="cohort-a")
    metadata = _v2_assertion_metadata(
        store, "s1", reader="v2", current_epoch="epoch-2",
        active_cohorts=["cohort-a"],
    )
    assert metadata is not None
    assert metadata["fiscal_year"] == 2025


def test_ctrl02_cohort_mismatch_hides_active_row(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-2", cohort="cohort-b")
    # snapshot only activates cohort-a: cohort-b row invisible
    assert _v2_assertion_metadata(
        store, "s1", reader="v2", current_epoch="epoch-2",
        active_cohorts=["cohort-a"],
    ) is None


def test_ctrl02_cohort_match_row_visible(tmp_path):
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-2", cohort="cohort-a")
    metadata = _v2_assertion_metadata(
        store, "s1", reader="v2", current_epoch="epoch-2",
        active_cohorts=["cohort-a"],
    )
    assert metadata is not None


def test_ctrl02_v2_reader_requires_epoch_and_cohort(tmp_path):
    """V2 visibility needs BOTH epoch and cohort filters; empty cohorts
    fail closed (no active cohort -> nothing visible)."""
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-2", cohort="cohort-a")
    assert _v2_assertion_metadata(
        store, "s1", reader="v2", current_epoch="epoch-2", active_cohorts=()
    ) is None


def test_ctrl02_v2_reader_epoch_missing_fails_closed(tmp_path):
    """V2 reader with cohorts but NO pinned epoch must fail closed
    (dropping the epoch guard must be killed)."""
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-2", cohort="cohort-a")
    assert _v2_assertion_metadata(
        store, "s1", reader="v2", current_epoch=None, active_cohorts=("cohort-a",)
    ) is None


# --- legacy bridge gating --------------------------------------------------


def test_legacy_bridge_blocked_when_snapshot_disallows(tmp_path):
    document = {"source_id": "s1", "metadata": {
        "acquisition": {"fiscal_year": 2025, "provider": "example"}}}
    # snapshot says legacy_bridge_enabled=false -> legacy container NOT read
    metadata = _source_metadata(
        document, store=None, reader="v1", current_epoch=None,
        active_cohorts=(), legacy_bridge_allowed=False,
    )
    assert metadata == {}


def test_legacy_bridge_allowed_when_snapshot_allows(tmp_path):
    document = {"source_id": "s1", "metadata": {
        "acquisition": {"fiscal_year": 2025, "provider": "example"}}}
    metadata = _source_metadata(
        document, store=None, reader="v1", current_epoch=None,
        active_cohorts=(), legacy_bridge_allowed=True,
    )
    assert metadata["fiscal_year"] == 2025


# --- snapshot dict -> resolver parameters ----------------------------------


# --- assertion-service path honors the same visibility contract ------------


def test_assertion_service_v1_reader_hides_active_row(tmp_path):
    from company_wiki.source_catalog.assertion_service import get_verified_assertion

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-2", cohort="cohort-a")
    # v1 reader (flag off): active row must be invisible via the
    # assertion-service path too (no bypass of the resolver gate)
    assert get_verified_assertion(
        store, "s1", "c" * 64, reader="v1", current_epoch=None,
        active_cohorts=(),
    ) is None


def test_assertion_service_v2_reader_epoch_cohort_match(tmp_path):
    from company_wiki.source_catalog.assertion_service import get_verified_assertion

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-2", cohort="cohort-a")
    found = get_verified_assertion(
        store, "s1", "c" * 64, reader="v2", current_epoch="epoch-2",
        active_cohorts=("cohort-a",),
    )
    assert found is not None
    assert found["fiscal_year"] == 2025


def test_assertion_service_v2_epoch_mismatch_hidden(tmp_path):
    from company_wiki.source_catalog.assertion_service import get_verified_assertion

    store = CatalogStore(tmp_path / "catalog.sqlite3")
    _seed_parents(store)
    _seed_active_assertion(store, epoch="epoch-1", cohort="cohort-a")
    assert get_verified_assertion(
        store, "s1", "c" * 64, reader="v2", current_epoch="epoch-2",
        active_cohorts=("cohort-a",),
    ) is None


def test_v1_snapshot_derives_v1_reader(tmp_path):
    from company_wiki.source_catalog.resolver import resolver_visibility

    snapshot = _v1_snapshot()
    reader, epoch, cohorts, bridge = resolver_visibility(snapshot)
    assert reader == "v1"
    assert epoch is None
    assert cohorts == ()
    assert bridge is True


def test_v2_snapshot_derives_v2_reader(tmp_path):
    from company_wiki.source_catalog.resolver import resolver_visibility

    snapshot = _v2_snapshot()
    reader, epoch, cohorts, bridge = resolver_visibility(snapshot)
    assert reader == "v2"
    assert epoch == "epoch-2"
    assert cohorts == ("cohort-a",)
    assert bridge is False
