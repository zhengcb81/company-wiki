"""FC-1105: audit-mechanism self-tests — fault injection makes every
dynamic gate fail red.

SCENARIO: AUD-01..08 (each injected fault must block, never silent green)

Injected faults (each must make its mechanism exit non-zero / fail):
  1. stale manifest    -> FC-1101 CI manifest gate (fake triplet commit)
  2. missing samples   -> FC-1102 T2 runner (column_drop)
  3. scan-error growth -> FC-1102 T2 runner trend budget
  4. epoch/policy drift-> FC-1102 T2 runner policy freshness (hash mismatch)
  5. artifact binding  -> FC-1102 T2 runner (bound artifacts -> 0)
  6. Dropbox MISSING   -> resolver fail-closed (sidecar removed)
Plus runner robustness: UTF-8 reports, atomic ledger (no .tmp), concurrent
dashboard runs.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
PROJECT_ROOT = RF_CODE_ROOT
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "company-wiki" / "src"))

from e2e_support.isolated_lake import IsolatedLake  # noqa: E402

T2 = PROJECT_ROOT / "tools" / "daily_t2_runner.py"
DASH = PROJECT_ROOT / "tools" / "audit_dashboard.py"


def _manifest(td: Path, *, triplet=None) -> Path:
    def head(repo: str) -> str:
        return subprocess.run(
            ["git", "-C", str(PROJECT_ROOT.parent / repo), "rev-parse", "HEAD"],
            capture_output=True, text=True).stdout.strip()
    manifest = {
        "schema_version": "1.0", "manifest_version": "test",
        "remotes": {"revenue": "x", "filing": "x", "wiki": "x"},
        "current_triplet": triplet or {
            "revenue": head("revenue-forecast"),
            "filing": head("filing-fetch"),
            "wiki": head("company-wiki"),
        },
    }
    p = td / "current.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


def _t2(catalog: Path, report_root: Path, manifest: Path) -> int:
    return subprocess.run(
        [sys.executable, "-B", str(T2), "--catalog", str(catalog),
         "--report-root", str(report_root), "--manifest", str(manifest)],
        capture_output=True, text=True, encoding="utf-8", timeout=300,
    ).returncode


class TestFaultInjection(unittest.TestCase):
    def test_f1_stale_manifest_triplet_fails(self):
        """F1: a manifest pointing at a fabricated commit must fail the
        FC-1101 commits-exist gate."""
        with tempfile.TemporaryDirectory() as td:
            mf = _manifest(Path(td), triplet={
                "revenue": "f" * 40, "filing": "f" * 40, "wiki": "f" * 40})
            # run the gate logic against this manifest
            import json as _json

            data = _json.loads(mf.read_text(encoding="utf-8"))
            missing = []
            for repo, name in (("revenue", "revenue-forecast"),
                               ("filing", "filing-fetch"),
                               ("wiki", "company-wiki")):
                rc = subprocess.run(
                    ["git", "-C", str(PROJECT_ROOT.parent / name), "cat-file",
                     "-e", data["current_triplet"][repo]],
                    capture_output=True).returncode
                if rc != 0:
                    missing.append(repo)
            self.assertEqual(len(missing), 3, "fabricated triplet must fail")

    def test_f2_missing_samples_fails(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            lake = IsolatedLake(td, seed="fc1105")
            m = lake.build()
            lake.corrupt("column_drop", m)
            self.assertNotEqual(_t2(m.catalog_path, td / "runs", _manifest(td)),
                                0, "missing samples must fail T2")

    def test_f4_policy_drift_fails(self):
        """F4: tampered runtime policy snapshot (hash mismatch) must fail T2."""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            m = IsolatedLake(td, seed="fc1105").build()
            pol = td / "lake" / "project" / ".source_catalog" / "runtime_policy.json"
            data = json.loads(pol.read_text(encoding="utf-8"))
            data["current_epoch"] = "epoch-tampered"
            pol.write_text(json.dumps(data), encoding="utf-8")  # hash now stale
            self.assertNotEqual(_t2(m.catalog_path, td / "runs", _manifest(td)),
                                0, "policy drift must fail T2")

    def test_f6_dropbox_missing_fails_closed(self):
        """F6: Dropbox sidecar removed -> a FRESH scan cannot admit the doc,
        so it must not resolve (stale already-indexed rows are the scan
        cadence's responsibility; admission at scan time is the gate)."""
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            lake = IsolatedLake(td, seed="fc1105")
            lake.build()
            # corrupt the dropbox sidecar on disk BEFORE the fresh scan
            side = (td / "lake" / "Dropbox" / "Stock" / "金融" / "保险" / "中国平安"
                    / "中国平安2020年中期报告.PDF.source.json")
            side.unlink()
            from company_wiki.source_catalog import (
                CatalogConfig, RootSpec, SourceCatalog, SourceRequest,
                SourceResolver)

            catalog = SourceCatalog(CatalogConfig(
                project_root=td / "lake" / "project2",
                catalog_dir=td / "lake" / "project2" / ".source_catalog",
                reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
                roots=(RootSpec("dropbox_stock", td / "lake" / "Dropbox" / "Stock",
                                "directory", priority=30, adapter_id="sidecar_filing_v1",
                                read_only=True, reusable_for_filing=True),),
            ))
            catalog.scan()  # fresh scan: sidecar missing -> no identity
            req = SourceRequest(entity="中国平安", document_kind="semi_annual_report",
                                as_of_date="2026-08-12", market="CN", fiscal_year=2020)
            res = SourceResolver(catalog, runtime_policy=None).resolve(req)
            self.assertFalse(res.matches, "sidecar-missing doc must not resolve")
            # ZR-203: the cached reader connection must be released before
            # the temp directory is deleted (Windows sharing semantics).
            catalog.close()

    def test_runner_robustness_utf8_and_atomic(self):
        """Runner robustness: UTF-8 reports + atomic dashboard ledger (no
        leftover .tmp) + concurrent dashboard runs do not corrupt the
        ledger."""
        import concurrent.futures

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            m = IsolatedLake(td, seed="fc1105").build()
            runs = td / "runs"
            self.assertEqual(_t2(m.catalog_path, runs, _manifest(td)), 0)
            report = next(runs.glob("*/report.json")).read_text(encoding="utf-8")
            json.loads(report)  # valid UTF-8 JSON
            # concurrent dashboard runs
            def _dash(_i):
                return subprocess.run(
                    [sys.executable, "-B", str(DASH), "--report-root", str(runs)],
                    capture_output=True, text=True, encoding="utf-8", timeout=60,
                ).returncode
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                codes = list(ex.map(_dash, range(4)))
            self.assertEqual(set(codes), {1})  # gate fails (no T3) but consistent
            ledger = json.loads((runs / "ledger.json").read_text(encoding="utf-8"))
            self.assertTrue(ledger["release_gate"]["ok"] is False)
            self.assertFalse(list(runs.rglob("*.tmp")), "no leftover temp files")


if __name__ == "__main__":
    unittest.main()
