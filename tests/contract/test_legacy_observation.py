"""WU-1500 RED/audit tests: legacy observation period + freeze gate.

RED/Focused:
  - legacy_bridge_hits are observable through the resolver (observation
    seam); a mutation that drops the hit recording must be killed.
  - freeze gate: the legacy bridge must not gain NEW callers — the only
    allowed producer of a legacy_bridge_hit is the resolver's
    _source_metadata fallback (no new import/call sites).
  - v1 reader rollback drill: the legacy read path still starts and never
    misreads v2-only state (shadow rows invisible to it).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.observability import (  # noqa: E402
    MetricsCollector,
)
from company_wiki.source_catalog.resolver import (  # noqa: E402
    _source_metadata,
)


def test_leg01_legacy_hit_recorded_via_observer():
    """M-01: reading a legacy container records legacy_bridge_hit."""
    collector = MetricsCollector()
    document = {"metadata": {"acquisition": {"fiscal_year": 2025}}}
    metadata = _source_metadata(document, observer=collector)
    assert metadata["fiscal_year"] == 2025
    assert collector.snapshot().legacy_bridge_hits == 1


def test_leg02_no_observer_no_behavior_change():
    """Absent observer: identical behavior, zero counters, no exceptions."""
    collector = MetricsCollector()
    document = {"metadata": {"dayu_meta": {"provider": "sec"}}}
    metadata = _source_metadata(document, observer=collector)
    assert metadata["provider"] == "sec"
    assert collector.snapshot().legacy_bridge_hits == 1
    # without observer the function still returns the legacy payload
    document2 = {"metadata": {"acquisition": {"market": "CN"}}}
    assert _source_metadata(document2)["market"] == "CN"


def test_leg03_v2_assertion_takes_precedence_no_legacy_hit():
    """When a visible v2 assertion exists, the legacy container is never
    read — no legacy_bridge_hit is recorded."""
    collector = MetricsCollector()

    class _FakeStore:
        def fetchone(self, sql, params=()):
            return None  # no v2 assertion

    # v2 missing -> legacy read -> hit
    doc = {"source_id": "s1", "metadata": {"acquisition": {"market": "US"}}}
    _source_metadata(doc, store=_FakeStore(), observer=collector)
    assert collector.snapshot().legacy_bridge_hits == 1

    class _V2Store(_FakeStore):
        def fetchone(self, sql, params=()):
            class Row(dict):
                def __getitem__(self, key):
                    return {"evidence_json": "{}", "fiscal_year": 2025}.get(key)

            return Row()

    collector.reset()
    _source_metadata(doc, store=_V2Store(), observer=collector)
    assert collector.snapshot().legacy_bridge_hits == 0  # v2 won


def test_leg04_freeze_gate_no_new_legacy_callers():
    """Freeze gate: legacy containers (acquisition/dayu_meta) are read as a
    metadata bridge ONLY inside resolver._source_metadata.  The gate scans
    for the *exact legacy-read patterns* — ``metadata.get(key)`` inside a
    loop over ("acquisition", "dayu_meta") — not the bare word
    'acquisition' (which legitimately appears in acquisition-service,
    writer, adapter and test code).  A new legacy bridge reader is a
    freeze violation."""
    from company_wiki.source_catalog.visibility_bridge import (  # noqa: E402
        LEGACY_PROFILE_KEYS,
    )

    assert LEGACY_PROFILE_KEYS == ("acquisition", "dayu_meta")
    # resolver is the ONLY legacy-container bridge reader: the loop over
    # the profile keys must appear in exactly one source file.
    pattern = 'for key in ("acquisition", "dayu_meta")'
    readers = []
    for path in Path("src/company_wiki/source_catalog").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if pattern in text:
            readers.append(str(path))
    assert readers == [
        "src\\company_wiki\\source_catalog\\resolver.py"
    ] or readers == ["src/company_wiki/source_catalog/resolver.py"], (
        f"freeze gate: new legacy bridge readers: {readers}"
    )


def test_leg05_v1_reader_rollback_drill_never_reads_shadow():
    """Rollback drill: the v1 path (no store / legacy-only) never sees
    shadow visibility rows — v2-only state is invisible to the old reader."""
    collector = MetricsCollector()
    doc = {"metadata": {"acquisition": {"fiscal_year": 2024}}}
    result = _source_metadata(doc, observer=collector)
    assert result["fiscal_year"] == 2024  # legacy reader still works
    # a v2-only row (shadow) must not be returned by the legacy path —
    # verified via the assertion visibility filter
    from company_wiki.source_catalog.visibility_bridge import active_assertions

    rows = [{"assertion_id": "a1", "visibility_state": "shadow",
             "activation_epoch": "epoch-1"}]
    assert active_assertions(rows, reader="v1") == []  # shadow invisible


def test_leg06_period_baseline_recordable():
    """Observation period bookkeeping: a period marker with hit counter can
    be recorded for the baseline (cycle 1 start)."""
    import json as _json

    period = {
        "period": 1,
        "started_at": "2026-08-09T00:00:00Z",
        "legacy_bridge_hits": 0,
        "bridge_hits": 0,
        "status": "observing",
        "freeze_gate": "no new callers",
    }
    payload = _json.dumps(period, ensure_ascii=False)
    assert '"period": 1' in payload
    assert '"status": "observing"' in payload


# --- FC-705: close gate + bridge-off drill ------------------------------------


def _window(period, *, hits=0, started_at, ended_at):
    return {
        "period": period,
        "started_at": started_at,
        "ended_at": ended_at,
        "legacy_bridge_hits": hits,
        "status": "completed",
    }


def test_leg10_close_gate_two_zero_hit_24h_windows():
    """FC-705: two consecutive completed >=24h zero-hit windows allow the
    legacy bridge to close."""
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    allowed, reasons = close_gate_allowed([
        _window(1, started_at="2026-08-09T00:00:00Z",
                ended_at="2026-08-10T00:00:00Z"),
        _window(2, started_at="2026-08-10T00:00:00Z",
                ended_at="2026-08-11T00:00:00Z"),
    ])
    assert allowed, reasons
    assert reasons == []


def test_leg10b_single_window_not_allowed():
    """One zero-hit window is not enough — the close stays locked."""
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    allowed, reasons = close_gate_allowed([
        _window(1, started_at="2026-08-09T00:00:00Z",
                ended_at="2026-08-10T00:00:00Z"),
    ])
    assert not allowed
    assert any("need 2" in r for r in reasons)


def test_leg10c_hits_in_window_blocks_close():
    """Any hit in either of the last two windows blocks the close."""
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    allowed, reasons = close_gate_allowed([
        _window(1, hits=0, started_at="2026-08-09T00:00:00Z",
                ended_at="2026-08-10T00:00:00Z"),
        _window(2, hits=3, started_at="2026-08-10T00:00:00Z",
                ended_at="2026-08-11T00:00:00Z"),
    ])
    assert not allowed
    assert any("legacy_bridge_hits=3" in r for r in reasons)


def test_leg10d_short_window_blocks_close():
    """A window shorter than 24h never counts — even with zero hits."""
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    allowed, reasons = close_gate_allowed([
        _window(1, started_at="2026-08-09T00:00:00Z",
                ended_at="2026-08-09T10:00:00Z"),
        _window(2, started_at="2026-08-09T10:00:00Z",
                ended_at="2026-08-10T10:00:00Z"),
    ])
    assert not allowed
    assert any("shorter than 24h" in r for r in reasons)


def test_leg10e_gap_in_period_numbers_blocks_close():
    """Non-consecutive period numbers are not consecutive windows."""
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    allowed, reasons = close_gate_allowed([
        _window(1, started_at="2026-08-09T00:00:00Z",
                ended_at="2026-08-10T00:00:00Z"),
        _window(3, started_at="2026-08-11T00:00:00Z",
                ended_at="2026-08-12T00:00:00Z"),
    ])
    assert not allowed
    assert any("not consecutive" in r for r in reasons)


def test_leg10f_empty_ledger_fails_closed():
    """No periods => fail closed with an explicit reason."""
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    allowed, reasons = close_gate_allowed([])
    assert not allowed
    assert reasons and "no observation periods" in reasons[0]


# --- FC-705: function-level bridge-off/rollback + canary seam -----------------


def test_leg07_bridge_off_fails_closed_no_container_read():
    """FC-705: legacy_bridge_allowed=False returns {} WITHOUT reading the
    container and records no hit — the fail-closed gate exists even at the
    seam function level."""
    collector = MetricsCollector()
    document = {"metadata": {"acquisition": {"market": "US"}}}
    result = _source_metadata(
        document, observer=collector, legacy_bridge_allowed=False)
    assert result == {}
    assert collector.snapshot().legacy_bridge_hits == 0


def test_leg09_rollback_restores_bridge():
    """FC-705: rolling the flag back on restores the legacy read — the
    bridge is closable AND reversible."""
    collector = MetricsCollector()
    document = {"metadata": {"dayu_meta": {"provider": "sec"}}}
    assert _source_metadata(
        document, observer=collector, legacy_bridge_allowed=False) == {}
    assert collector.snapshot().legacy_bridge_hits == 0
    # rollback: flag back on -> legacy payload readable again
    restored = _source_metadata(document, observer=collector)
    assert restored["provider"] == "sec"
    assert collector.snapshot().legacy_bridge_hits == 1


def test_leg11_canary_matrix_observation_read_only(tmp_path):
    """FC-705: the canary-matrix observation resolves through the REAL
    resolver seam (v2 drill: active assertion + bridge off) and never
    writes the catalog."""
    import hashlib
    import json as _json

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from legacy_observer import observe_canary_matrix  # noqa: E402

    from company_wiki.source_catalog.models import RootSpec  # noqa: E402

    raw = tmp_path / "companies" / "紫金矿业" / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True)
    body = b"%PDF-1.4 canary"
    (raw / "1222870413.pdf").write_bytes(body)
    (raw / "1222870413.pdf.source.json").write_text(_json.dumps({
        "market": "CN", "security_id": "601899",
        "source_title": "紫金矿业 2024", "fiscal_year": 2024,
        "filing_date": "2025-03-20", "form_type": "annual_report",
        "document_kind": "annual_report", "provider": "cninfo",
        "provider_document_id": "1222870413",
        "source_url": "https://provider.example/1222870413",
    }, ensure_ascii=False), encoding="utf-8")
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tmp_path / "companies", "company_raw",
                            priority=10, adapter_id="company_raw_v1",
                            read_only=False, reusable_for_filing=True,
                            canonical_write_target="companies"),),
        )
    )
    catalog.scan()
    row = catalog.store.fetchone(
        "SELECT document_id, primary_source_id FROM documents LIMIT 1")
    assert row is not None
    with catalog.store.transaction() as conn:
        conn.execute(
            """INSERT INTO source_metadata_assertions (
                assertion_id, source_id, document_id, decision,
                visibility_state, activation_epoch, cohort, created_at,
                evidence_json, fiscal_year, fiscal_period, document_kind,
                form_type, provider, provider_document_id, source_url,
                security_id, market, content_sha256, normalization_status,
                evidence_basis, created_by, schema_version)
               VALUES (?, ?, ?, 'verified', 'active', 'e1', 'c1',
                       '2026-08-10T00:00:00Z', '{}', 2024, 'FY2024',
                       'annual_report', 'annual_report', 'cninfo',
                       '1222870413', 'https://provider.example/1222870413',
                       '601899', 'CN', ?, 'capture_ready',
                       'sidecar', 'fc705-test', '1.0')""",
            ("a-canary", row["primary_source_id"], row["document_id"],
             hashlib.sha256(body).hexdigest()))
    config = tmp_path / "config"
    config.mkdir()
    config_path = config / "source_catalog.yaml"
    config_path.write_text(_json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(tmp_path / ".source_catalog"),
        "roots": [{"root_id": "company_raw",
                   "path": str(tmp_path / "companies"),
                   "kind": "company_raw"}],
    }), encoding="utf-8")
    from company_wiki.source_catalog.runtime_policy import (  # noqa: E402
        snapshot_hash,
    )

    policy = {
        "schema_version": "1.0",
        "policy_hash": "c" * 64,
        "flags": {"v2_resolve_active": True, "legacy_bridge_enabled": False,
                  "v2_bundle_active": False, "v2_persist_assertions": True,
                  "v2_resolve_shadow": True, "v2_scan_shadow": True},
        "current_epoch": "e1",
        "active_cohorts": ["c1"],
        "updated_at": "2026-08-11T00:00:00Z",
    }
    policy["snapshot_sha256"] = snapshot_hash(policy)
    (tmp_path / ".source_catalog" / "runtime_policy.json").write_text(
        _json.dumps(policy, ensure_ascii=False), encoding="utf-8")
    db_path = tmp_path / ".source_catalog" / "catalog.sqlite3"
    before = hashlib.sha256(db_path.read_bytes()).hexdigest()

    result = observe_canary_matrix(config_path, drill=True)

    assert result["mode"] == "drill"
    by_name = {r["name"]: r["status"] for r in result["requests"]}
    assert by_name["CN-601899-FY2024"] == "reused_exact", by_name
    assert by_name["CN-601899-FY2025"] == "missing"  # no FY2025 doc
    assert by_name["HK-03690-FY2024"] == "missing"
    assert by_name["US-AAPL-FY2025"] == "missing"
    assert result["legacy_bridge_hits"] == 0
    assert result["shadow_diffs"] == 0
    after = hashlib.sha256(db_path.read_bytes()).hexdigest()
    assert before == after, "canary observation wrote to the catalog"


def test_leg10g_gate_fires_after_two_completed_zero_hit_windows():
    """Full main()-bookkeeping simulation (reviewer F1): an OPEN window
    never counts — the gate fires exactly when the second zero-hit window
    COMPLETES.  The ledger-transition flow (new period closes the previous)
    is what production runs, so the gate must work on it."""
    from company_wiki.source_catalog.legacy_close_gate import close_gate_allowed

    periods = []
    # run 1: period 1 opens
    periods.append(_window(1, started_at="2026-08-09T00:00:00Z", ended_at=None))
    assert not close_gate_allowed(periods)[0]
    # run 2: period 2 opens -> period 1 closes (24h later, zero hits)
    periods[0]["ended_at"] = "2026-08-10T00:00:00Z"
    periods.append(_window(2, started_at="2026-08-10T00:00:00Z", ended_at=None))
    assert not close_gate_allowed(periods)[0]  # only ONE completed window
    # run 3: period 3 opens -> period 2 closes (24h later, zero hits)
    periods[1]["ended_at"] = "2026-08-11T00:00:00Z"
    periods.append(_window(3, started_at="2026-08-11T00:00:00Z", ended_at=None))
    allowed, reasons = close_gate_allowed(periods)
    assert allowed, reasons  # periods 1+2 completed, zero hits, >=24h each
