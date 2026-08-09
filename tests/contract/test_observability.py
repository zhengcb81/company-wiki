"""WU-1305 RED/audit tests: reason taxonomy + privacy-safe metrics.

Mutations guarded:
  M-01  recording an UNKNOWN reason code must be refused (fail closed)
  M-02  exporter leaking absolute paths / company content must fail
  M-03  legacy_bridge_hits must be observable (dropping it is a mutation)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.observability import (  # noqa: E402
    MetricsCollector,
    REDACT,
    REASONS,
    validate_reason,
)


def test_obs01_unknown_reason_refused():
    """M-01: unknown/free-text reasons never enter the ledger."""
    collector = MetricsCollector()
    ok = collector.record_reason("totally_made_up_reason")
    assert ok is False
    ok = collector.record_reason("admitted")  # registered
    assert ok is True
    reasons = collector.snapshot().aggregate("reason")
    assert "totally_made_up_reason" not in reasons
    assert reasons["admitted"] == 1


def test_obs02_validate_reason_fail_closed():
    assert validate_reason("admitted") is True
    assert validate_reason("exact_hit") is True
    assert validate_reason("") is False
    assert validate_reason("free text reason") is False
    assert validate_reason("exact_hit; dropped; sql") is False


def test_obs03_absolute_path_redacted():
    """M-02: a path/company token must never survive in metrics."""
    collector = MetricsCollector()
    collector.record("root_id", r"C:\Users\郑曾波\Dropbox\Stock\金融\保险\中国平安\x.pdf")
    collector.record("route", "/home/runner/work/revenue-forecast/secret.docx")
    collector.record("adapter_id", "sidecar_filing_v1")  # benign
    for metric in collector.snapshot().metrics:
        assert REDACT in metric.key or "sidecar_filing_v1" in metric.key
        assert "中国平安" not in metric.key
        assert "Dropbox" not in metric.key
        assert "revenue-forecast" not in metric.key


def test_obs04_legacy_bridge_hits_observable():
    """M-03: bridge hits and shadow diffs are first-class counters."""
    collector = MetricsCollector()
    assert collector.record_reason("legacy_bridge_hit") is True
    assert collector.record_reason("legacy_bridge_hit") is True
    assert collector.record_reason("shadow_diff") is True
    report = collector.snapshot()
    assert report.legacy_bridge_hits == 2
    assert report.shadow_diffs == 1


def test_obs05_latency_percentiles():
    collector = MetricsCollector()
    collector.record_latency([10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
                              110, 120, 130, 140, 150, 160, 170, 180, 190, 200])
    report = collector.snapshot()
    assert report.latency_p50 == 100  # nearest-rank: ceil(0.5*20)-1 = 9
    assert report.latency_p95 == 190  # ceil(0.95*20)-1 = 18
    assert report.latency_p99 == 200  # ceil(0.99*20)-1 = 19 (max)
    collector.record_latency([])  # no-op, no crash
    assert collector.snapshot().latency_p50 == 100


def test_obs06_exporter_off_no_effect_on_core():
    """Telemetry never raises; a missing exporter changes nothing."""
    collector = MetricsCollector()
    # snapshot/to_dict work without any exporter attached
    data = collector.snapshot().to_dict()
    assert data["schema_version"].startswith("reason-taxonomy-")
    assert data["legacy_bridge_hits"] == 0
    assert isinstance(data["metrics"], list)


def test_obs07_taxonomy_versioned_and_additive():
    """Every documented dimension has a versioned code; no removal ever."""
    for code in ("admitted", "identity_missing", "kind_missing",
                 "period_missing", "hash_missing", "content_hash_mismatch",
                 "status_not_active", "policy_denied", "non_filing_kind",
                 "exact_hit", "latest_selected", "ambiguous_issuer",
                 "download_suppressed", "downloaded", "artifact_selected",
                 "artifact_rejected", "recomputed", "legacy_bridge_hit",
                 "shadow_diff", "migration_remaining"):
        assert code in REASONS, f"{code} missing from taxonomy"
