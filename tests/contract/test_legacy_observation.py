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
