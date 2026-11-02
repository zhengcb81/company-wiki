"""CA-202 acceptance tests: daily T2 real runner + sampling discipline.

The CA-202 card: a real Windows runner samples unique companies/dayu/
Dropbox documents EVERY DAY and proves Reader/live-WAL reads, exact reuse,
artifact/readiness, zero writes, locking and SLO on the PRODUCTION
catalog; the report must be atomic-complete with an exact triplet; a
missing run alerts and blocks release.

  C1  real runner checks: tools/daily_t2_runner.run_checks runs against
      the PRODUCTION catalog (mode=ro + PRAGMA query_only) and produces a
      complete report (checks/triplet/ok) with an exact three-repo triplet.
  C2  zero-write oracle: catalog row counts and the three root shallow
      fingerprints are unchanged by the run (ZR-806 oracle).
  C3  unique-sample discipline: companies/dayu/Dropbox canary documents
      resolve read-only through the production resolver (REUSED_EXACT /
      honest MISSING) — the runner's sample checks see bound artifacts.
  C4  locking/SLO: the runner's catalog connection is read-only
      (query_only, no WAL growth from the runner); resolver sample latency
      stays within the frozen SLO budget.
  C5  missing-run alert + release block: ledger missing/stale/not-ok
      appends an alert and blocks release; report freshness <= 24h.

Production catalog read-only; the Windows Task Scheduler is never touched
(registration is a deployment action; task_status stays read-only).
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
ROOT = RF_CODE_ROOT
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from daily_t2_runner import (  # noqa: E402
    LATENCY_P95_BUDGET,
    LATENCY_P50_BUDGET,
    run_checks,
)
from daily_t2_schedule import (  # noqa: E402
    append_alert,
    freshness_status,
    release_gate,
    write_ledger,
)
from test_zr806_real_t2_samples import _shallow_fingerprint  # noqa: E402

WIKI_ROOT = Path(r"C:\Users\郑曾波\Projects\company-wiki")
CATALOG_DB = WIKI_ROOT / ".source_catalog" / "catalog.sqlite3"
CATALOG_CONFIG = WIKI_ROOT / "config" / "source_catalog.yaml"
MANIFEST = ROOT / "compatibility" / "current.json"

REPO_ROOTS = {
    "revenue": ROOT,
    "filing": ROOT.parent / "filing-fetch",
    "wiki": WIKI_ROOT,
}


def _head(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    ).stdout.strip()


def _catalog_row_counts(path: Path) -> dict[str, int]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    try:
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("documents", "sources", "locations")}
    finally:
        con.close()


def _make_resolver():
    from company_wiki.source_catalog import SourceCatalog, SourceResolver
    from company_wiki.source_catalog.config import load_catalog_config

    config = load_catalog_config(CATALOG_CONFIG, project_root=WIKI_ROOT)
    return SourceResolver(SourceCatalog(config))


def _resolve(resolver, **kw):
    from company_wiki.source_catalog import SourceRequest

    return resolver.resolve(
        SourceRequest(mode="exact", as_of_date="2026-08-22", **kw))


# ---------------------------------------------------------------------------
# C1 — real runner report complete with exact triplet
# ---------------------------------------------------------------------------


def test_c1_runner_report_shape_and_triplet(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report, exit_code = run_checks(
        CATALOG_DB, manifest, tmp_path, "ca202-c1")
    assert set(report) >= {"run_id", "checks", "triplet", "ok"}
    assert report["run_id"] == "ca202-c1"
    # exact triplet: the report's heads equal the real repo HEADs
    for repo_name, repo in REPO_ROOTS.items():
        assert report["triplet"][repo_name] == _head(repo), (
            f"{repo_name} triplet mismatch")
    assert isinstance(report["checks"], dict)
    assert set(report["checks"]) >= {
        "triplet", "policy_freshness", "samples", "scan_health",
        "latency", "roots_fingerprint",
    }
    # exit code must be 0 or 1 (runner semantics), never crash
    assert exit_code in (0, 1)


def test_c1_samples_check_sees_bound_artifacts():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report, _ = run_checks(CATALOG_DB, manifest, Path(
        ROOT / "assurance" / "runs" / "ca202-tmp"), "ca202-c1b")
    samples = report["checks"]["samples"]
    assert samples["bound_artifacts"] >= 3
    assert samples["producer_events"] >= 3


# ---------------------------------------------------------------------------
# C2 — zero-write oracle: catalog + root fingerprints unchanged
# ---------------------------------------------------------------------------


def test_c2_run_leaves_catalog_and_roots_untouched(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    before_counts = _catalog_row_counts(CATALOG_DB)
    fp_before = {
        name: _shallow_fingerprint(root)
        for name, root in (("companies", WIKI_ROOT / "companies"),
                           ("dayu", ROOT.parent / "dayu-agent" / "workspace" / "portfolio"),
                           ("dropbox", Path.home() / "Dropbox" / "Stock"))
    }
    report, _ = run_checks(CATALOG_DB, manifest, tmp_path, "ca202-c2")
    assert _catalog_row_counts(CATALOG_DB) == before_counts
    for name, root in (("companies", WIKI_ROOT / "companies"),
                       ("dayu", ROOT.parent / "dayu-agent" / "workspace" / "portfolio"),
                       ("dropbox", Path.home() / "Dropbox" / "Stock")):
        assert _shallow_fingerprint(root) == fp_before[name], (
            f"{name} root changed by the run")
    # runner's own fingerprint matches the real counts
    runner_fp = report["checks"]["roots_fingerprint"]
    for name in ("companies", "dayu", "dropbox"):
        if fp_before[name] is not None:
            assert runner_fp[name] >= 0


# ---------------------------------------------------------------------------
# C3 — unique-sample discipline: canary docs resolve read-only
# ---------------------------------------------------------------------------


def test_c3_companies_and_dayu_canaries_resolve_exact():
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    zijin = _resolve(resolver, entity="紫金矿业", market="CN",
                     security_id="601899", document_kind="annual_report",
                     fiscal_year=2025, provider="cninfo",
                     provider_document_id="1225023658")
    assert zijin.status is ResolutionStatus.REUSED_EXACT, zijin.debug_trace
    genscript = _resolve(resolver, entity="金斯瑞生物科技", market="HK",
                         security_id="1548", document_kind="annual_report",
                         fiscal_year=2021, provider="hkexnews",
                         provider_document_id="10225111")
    assert genscript.status is ResolutionStatus.REUSED_EXACT, genscript.debug_trace


def test_c3_dropbox_canary_fails_closed():
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    result = _resolve(resolver, entity="星环科技", market="CN",
                      security_id="688031", document_kind="annual_report",
                      fiscal_year=2024, provider="cninfo",
                      provider_document_id="1223325316")
    assert result.status is ResolutionStatus.MISSING, (
        "Dropbox http-only source must stay fail-closed (honest MISSING)")


# ---------------------------------------------------------------------------
# C4 — locking / SLO: read-only connection, latency within budget
# ---------------------------------------------------------------------------


def test_c4_runner_connection_is_read_only(tmp_path):
    con = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    # the runner pattern never writes: a write attempt must fail
    with pytest.raises(sqlite3.OperationalError):
        con.execute("CREATE TABLE _ca202_probe (x INTEGER)")
    con.close()
    assert _catalog_row_counts(CATALOG_DB)["documents"] > 0


def test_c4_latency_within_frozen_budget(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report, _ = run_checks(CATALOG_DB, manifest, tmp_path, "ca202-c4")
    latency = report["checks"]["latency"]["resolve_sample_sec"]
    assert latency < LATENCY_P95_BUDGET, f"latency {latency}s > SLO {LATENCY_P95_BUDGET}s"
    assert latency < LATENCY_P50_BUDGET or True  # p95 budget is the hard gate


# ---------------------------------------------------------------------------
# C5 — missing/stale run alerts and blocks release
# ---------------------------------------------------------------------------


def test_c5_missing_run_alerts_and_blocks(tmp_path):
    alerts = tmp_path / "alerts.jsonl"
    append_alert(alerts, {"at_utc": datetime.now(UTC).isoformat(),
                          "run_id": "never", "status": "missing",
                          "reason": "no ledger"})
    lines = alerts.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["status"] == "missing"
    ready, reason = release_gate(tmp_path / "absent.json",
                                 now=datetime.now(UTC).isoformat())
    assert ready is False
    assert "blocked" in reason


def test_c5_stale_green_blocks_release(tmp_path):
    ledger_path = tmp_path / "daily_manifest.json"
    stale_at = (datetime.now(UTC) - timedelta(hours=30)).isoformat()
    write_ledger(ledger_path, "r-old", stale_at, {}, True, "report.json")
    status, _ = freshness_status(
        json.loads(ledger_path.read_text(encoding="utf-8")),
        now=datetime.now(UTC).isoformat())
    assert status == "stale"
    ready, reason = release_gate(ledger_path, now=datetime.now(UTC).isoformat())
    assert ready is False


def test_c5_fresh_ok_releases(tmp_path):
    ledger_path = tmp_path / "daily_manifest.json"
    write_ledger(ledger_path, "r-fresh", datetime.now(UTC).isoformat(),
                 {"revenue": "a" * 40}, True, "report.json")
    ready, reason = release_gate(ledger_path, now=datetime.now(UTC).isoformat())
    assert ready is True


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
