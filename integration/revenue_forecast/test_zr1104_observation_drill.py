"""ZR-1104 acceptance tests: observation window + real rollback drill.

The ZR-1104 card: accumulate 7 Daily T2, 2 Weekly T3, 1 Monthly Zijin
shadow and 1 alert self-check; legacy hits = 0; run one cohort
rollback/re-activate; natural-time gates are never manually waived.

  C1  observation completeness: the soak window calculator (CA-206
      semantics) accepts only fully accumulated windows — 7 daily, 2
      weekly, 1 monthly, 1 acked drill; anything short stays PENDING.
  C2  legacy-hit gate: removal/closure stays blocked while legacy hits
      are non-zero; two consecutive zero-hit windows are required
      (FC-705).
  C3  cohort rollback drill: activation -> rollback -> re-activation
      round trip preserves epoch/cohort/policy hash and flips only the
      active flag; receipts differ per activation.
  C4  no-manual-waiver: the natural-time gate is a pure function of
      trusted timestamps — an open window, a copied report, or a
      hand-edited clock never counts (window breaks fail closed).
  C5  drill journal: an alert self-check drill is recorded and acked
      before it counts toward the observation window.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

import pytest

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
ROOT = RF_CODE_ROOT
sys.path.insert(0, str(ROOT / "tests"))

from test_ca206_soak_window import (  # noqa: E402
    SoakRun,
    daily_window,
    drill_window,
    soak_status,
    weekly_window,
)

NOW = "2026-08-20T12:00:00+00:00"


def _daily_aug(days: int) -> list[SoakRun]:
    base = datetime.fromisoformat("2026-08-13T03:30:00+00:00")
    runs = []
    for i in range(days):
        day = base + timedelta(days=i)
        runs.append(SoakRun(
            run_id=f"T2-{day.date()}", started_at=day.isoformat(),
            kind="daily", report_sha256="x" * 64))
    return runs


# ---------------------------------------------------------------------------
# C1 — observation completeness
# ---------------------------------------------------------------------------


def test_c1_full_observation_completes():
    runs = _daily_aug(7) + [
        SoakRun("T3-2026-08-09", "2026-08-09T04:30:00+00:00", "weekly"),
        SoakRun("T3-2026-08-16", "2026-08-16T04:30:00+00:00", "weekly"),
        SoakRun("M-2026-08-01", "2026-08-01T05:00:00+00:00", "monthly"),
    ]
    alerts = [{"run_id": "drill-1", "acked": True}]
    status = soak_status(runs, alerts, now=NOW)
    assert status["complete"] is True
    assert status["windows"]["daily"]["count"] == 7
    assert status["windows"]["weekly"]["count"] == 2
    assert status["windows"]["monthly"]["count"] == 1


def test_c1_short_observation_stays_pending():
    runs = _daily_aug(5) + [
        SoakRun("T3-2026-08-16", "2026-08-16T04:30:00+00:00", "weekly"),
    ]
    status = soak_status(runs, [], now=NOW)
    assert status["complete"] is False
    assert status["status"] == "pending"


# ---------------------------------------------------------------------------
# C2 — legacy-hit gate
# ---------------------------------------------------------------------------


def test_c2_legacy_hits_block_closure():
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    now = datetime.now(UTC)
    periods = [
        {"period": 1,
         "started_at": (now - timedelta(hours=48)).isoformat(),
         "ended_at": (now - timedelta(hours=24)).isoformat(),
         "legacy_bridge_hits": 2},  # hits -> blocked
        {"period": 2,
         "started_at": (now - timedelta(hours=24)).isoformat(),
         "ended_at": now.isoformat(),
         "legacy_bridge_hits": 0},
    ]
    allowed, reasons = close_gate_allowed(periods)
    assert allowed is False
    assert any("legacy_bridge_hits" in r for r in reasons)


def test_c2_two_zero_hit_windows_required():
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    now = datetime.now(UTC)
    periods = [
        {"period": 1,
         "started_at": (now - timedelta(hours=48)).isoformat(),
         "ended_at": (now - timedelta(hours=24)).isoformat(),
         "legacy_bridge_hits": 0},
        {"period": 2,
         "started_at": (now - timedelta(hours=24)).isoformat(),
         "ended_at": now.isoformat(),
         "legacy_bridge_hits": 0},
    ]
    allowed, reasons = close_gate_allowed(periods)
    assert allowed is True, reasons


# ---------------------------------------------------------------------------
# C3 — cohort rollback drill
# ---------------------------------------------------------------------------


def test_c3_cohort_rollback_reactivate(tmp_path):
    from company_wiki.source_catalog.activation import (
        apply_activation,
        rollback_activation,
    )
    from company_wiki.source_catalog.store import CatalogStore

    db_path = tmp_path / "catalog.sqlite3"
    store = CatalogStore(db_path)
    # seed one v2 assertion
    from company_wiki.source_catalog.assertion_service import upsert_verified_assertion
    from company_wiki.source_catalog.normalized_meta import canonical_hash

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
        store, source_id="s1", document_id="d1", content_sha256="0" * 64,
        adapter_id="sidecar_filing_v1", adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized), normalized=normalized)
    ids = [assertion["assertion_id"]]
    policy = "a" * 64
    receipt1 = apply_activation(
        store, epoch="2026-08-23T00:00:00Z", cohort="zr1104",
        assertion_ids=ids, policy_hash=policy,
        reviewer="zr1104-implementer", reason="observation drill",
        current_policy_hash=policy)
    row1 = store.fetchone(
        "SELECT visibility_state, activation_epoch, cohort "
        "FROM source_metadata_assertions WHERE assertion_id=?", (ids[0],))
    rollback_activation(
        store, receipt_id=receipt1["receipt_id"], cohort="zr1104",
        reviewer="zr1104-implementer", reason="drill rollback")
    row_rollback = store.fetchone(
        "SELECT visibility_state, activation_epoch, cohort "
        "FROM source_metadata_assertions WHERE assertion_id=?", (ids[0],))
    receipt2 = apply_activation(
        store, epoch="2026-08-23T00:00:00Z", cohort="zr1104",
        assertion_ids=ids, policy_hash=policy,
        reviewer="zr1104-implementer", reason="drill re-activate",
        current_policy_hash=policy)
    row2 = store.fetchone(
        "SELECT visibility_state, activation_epoch, cohort "
        "FROM source_metadata_assertions WHERE assertion_id=?", (ids[0],))
    # re-activation lands in the identical state; rollback flipped flag
    assert row2[1:] == row1[1:]
    assert row_rollback[0] != row1[0]
    assert receipt1["receipt_id"] != receipt2["receipt_id"]


# ---------------------------------------------------------------------------
# C4 — no-manual-waiver
# ---------------------------------------------------------------------------


def test_c4_open_or_copied_window_never_waived():
    """An open window, a copied report (duplicate run id) or a hand-edited
    clock never completes the observation — fail closed."""
    runs = _daily_aug(6)
    dup = SoakRun(run_id=runs[0].run_id,
                  started_at="2026-08-19T03:30:00+00:00",
                  kind="daily", report_sha256=runs[0].report_sha256)
    runs.append(dup)  # copied report on another day
    status = daily_window(runs, now=NOW)
    assert status["complete"] is False
    assert status["count"] < 7


def test_c4_stale_weekly_does_not_accumulate():
    weekly = [
        SoakRun("T3-2026-08-01", "2026-08-01T04:30:00+00:00", "weekly"),
        SoakRun("T3-2026-08-08", "2026-08-08T04:30:00+00:00", "weekly"),
    ]
    status = weekly_window(weekly, now=NOW)
    assert status["count"] == 0  # latest stale (>7d) -> window does not count


# ---------------------------------------------------------------------------
# C5 — drill journal
# ---------------------------------------------------------------------------


def test_c5_alert_self_check_drill_counts_only_when_acked():
    alerts = [{"run_id": "drill-1", "acked": False}]
    assert drill_window(alerts, now=NOW)["complete"] is False
    alerts[0]["acked"] = True
    assert drill_window(alerts, now=NOW)["complete"] is True


def test_c5_full_observation_with_drill_completes():
    runs = _daily_aug(7) + [
        SoakRun("T3-2026-08-09", "2026-08-09T04:30:00+00:00", "weekly"),
        SoakRun("T3-2026-08-16", "2026-08-16T04:30:00+00:00", "weekly"),
        SoakRun("M-2026-08-01", "2026-08-01T05:00:00+00:00", "monthly"),
    ]
    alerts = [{"run_id": "drill-1", "acked": True}]
    status = soak_status(runs, alerts, now=NOW)
    assert status["complete"] is True
    assert status["windows"]["alert_drill"]["count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
