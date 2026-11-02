"""FC-1302: increment-based scan-health checks in the T2 runner.

findings 62: production scan errors grew 155 -> 242 from ONE recurring
empty user file in the Dropbox root (unchanged=true, new_errors=0 every
run).  Cumulative error-run counts must not compound severity; the failure
signals are NEW errors in the last 24h and interrupted growth.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from e2e_support.isolated_lake import IsolatedLake  # noqa: E402

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
PROJECT_ROOT = RF_CODE_ROOT
TOOL = PROJECT_ROOT / "tools" / "daily_t2_runner.py"


def _manifest(tmp: Path) -> Path:
    # minimal manifest: triplet commits must exist
    heads = {}
    for name in ("revenue-forecast", "filing-fetch", "company-wiki"):
        repo = PROJECT_ROOT.parent / name
        heads[name] = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True).stdout.strip()
    manifest = {
        "schema_version": "1.0",
        "current_triplet": {
            "revenue": heads["revenue-forecast"],
            "filing": heads["filing-fetch"],
            "wiki": heads["company-wiki"],
        },
    }
    path = tmp / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _run(catalog: Path, runs: Path, manifest: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), "--catalog", str(catalog),
         "--manifest", str(manifest), "--report-root", str(runs),
         "--run-id", "fc1302-test"],
        capture_output=True, text=True, timeout=180)


def _inject(catalog: Path, status: str, report: dict) -> None:
    con = sqlite3.connect(catalog)
    con.execute(
        "INSERT INTO scan_runs(run_id, status, started_at, report_json) "
        "VALUES(?,?,datetime('now'),?)",
        ("scan-fc1302", status, json.dumps(report)))
    con.commit()
    con.close()


def test_recurring_unchanged_errors_do_not_fail(tmp_path: Path):
    """The production case (findings 62): an empty user file re-reported
    unchanged every scan must NOT fail the health check."""
    m = IsolatedLake(tmp_path, seed="fc1302").build()
    runs = tmp_path / "runs"
    manifest = _manifest(tmp_path)
    _inject(m.catalog_path, "completed_with_errors", {
        "errors": 1,
        "new_errors": 0,
        "error_details": [
            {"error": "SourceManifestError: source file is empty",
             "relative_path": "医药健康/医疗器械选股/data/Product_Revenue_Forecast_Model.xlsx",
             "root_id": "dropbox_stock",
             "unchanged": True},
        ],
    })
    proc = _run(m.catalog_path, runs, manifest)
    assert proc.returncode == 0, f"recurring unchanged error must not fail: {proc.stdout}"
    report = json.loads((runs / "fc1302-test" / "report.json").read_text(encoding="utf-8"))
    health = report["checks"]["scan_health"]
    assert health["new_errors_24h"] == 0
    assert health["recurring_unchanged_runs_24h"] == 1
    assert health["completed_with_errors"] == 1  # total stays informational


def test_new_errors_in_24h_fail(tmp_path: Path):
    """A NEW scan error must fail the check (increment semantics)."""
    m = IsolatedLake(tmp_path, seed="fc1302").build()
    runs = tmp_path / "runs"
    manifest = _manifest(tmp_path)
    _inject(m.catalog_path, "completed_with_errors", {
        "errors": 1,
        "new_errors": 2,
        "error_details": [{"error": "SourceManifestError: unreadable", "unchanged": False}],
    })
    proc = _run(m.catalog_path, runs, manifest)
    assert proc.returncode != 0, "new errors must fail the T2 run"
    assert "scan health" in proc.stderr


def test_interrupted_delta_beyond_budget_fails(tmp_path: Path):
    """Interrupted growth beyond the frozen budget fails via the previous
    report comparison."""
    m = IsolatedLake(tmp_path, seed="fc1302").build()
    runs = tmp_path / "runs"
    manifest = _manifest(tmp_path)
    p1 = _run(m.catalog_path, runs, manifest)
    assert p1.returncode == 0
    # forge the previous report to say interrupted=0, then inject 10 rows
    prev = next(runs.glob("*/report.json"))
    report = json.loads(prev.read_text(encoding="utf-8"))
    report["checks"]["scan_health"]["interrupted"] = 0
    prev.write_text(json.dumps(report), encoding="utf-8")
    con = sqlite3.connect(m.catalog_path)
    for i in range(10):
        con.execute(
            "INSERT INTO scan_runs(run_id, status, started_at) VALUES(?,?,datetime('now'))",
            (f"scan-int-{i}", "interrupted"))
    con.commit()
    con.close()
    p2 = _run(m.catalog_path, runs, manifest)
    assert p2.returncode != 0, "interrupted growth beyond budget must fail"
    assert "interrupted" in p2.stderr
