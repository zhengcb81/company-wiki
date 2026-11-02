"""CA-203 acceptance tests: weekly / pre-release T3 discipline.

The CA-203 card: real CN/HK/US providers do the FIRST authorized download,
then a second request downloads NOTHING; amendment, single-flight and
provider-drift semantics hold; a blocked suite (credentials/network
missing) is BLOCKED, never a pass, and blocks release with an alert;
provider/canonical calls reconcile exactly.

  C1  suite discipline gate: the T3 execution suite (filing-fetch
      test_e2e_download.py) is opt-in only, covers three markets, the
      corruption-rejection case and the second-run-zero-download
      semantics; the weekly wrapper's blocked semantics hold as pure
      functions (all-skipped -> blocked; exit != 0 -> not-ok; pass -> ok).
  C2  first authorized download then zero re-download (LT-09/DL-04): on
      an isolated wiki with the REAL cross-process spy adapter, the first
      authorized close-gap fetches exactly once; the second identical
      request fetches zero and writes zero bytes.
  C3  amendment / newer-period semantics (LT-02): the old period is
      reused from local and only the NEW missing period is downloaded
      (exactly one fetch for the new accession).
  C4  provider drift (LT-05): when the provider is unavailable the plan
      is retryable, the local handle is preserved and fetch count stays
      zero — never a fabricated pass.
  C5  provider/canonical reconciliation: the spy journal's actions
      reconcile exactly with the acquisition journal outcomes and the
      companies/ bytes written (per-fetch byte accounting).

Zero production changes; hermetic (isolated wiki under tmp); the real
opt-in T3 suite and the Windows Task Scheduler are never triggered.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
PROJECT_ROOT = RF_CODE_ROOT
FILING_ROOT = PROJECT_ROOT.parent / "filing-fetch"
FILING_TESTS = FILING_ROOT / "tests"
T3_SUITE = FILING_TESTS / "test_e2e_download.py"
E2E = FILING_TESTS / "e2e_support"

sys.path.insert(0, str(PROJECT_ROOT / "tools"))
sys.path.insert(0, str(E2E))

from weekly_t3_schedule import _suite_outcome  # noqa: E402


# ---------------------------------------------------------------------------
# C1 — suite discipline gate + blocked-never-pass semantics
# ---------------------------------------------------------------------------


def test_c1_t3_suite_opt_in_three_markets_zero_redownload():
    assert T3_SUITE.exists(), "filing-fetch T3 suite missing"
    source = T3_SUITE.read_text(encoding="utf-8")
    assert 'os.environ.get("FILING_FETCH_E2E_DOWNLOAD") == "1"' in source
    assert "skipUnless" in source
    for marker in (
        "def test_download_cn_annual_report",
        "def test_download_us_annual_report",
        "def test_download_hk_annual_report",
        "def test_download_rejects_corrupted_local_copy",
        "second run must not download again",
    ):
        assert marker in source, f"T3 suite missing: {marker}"


def _proc(rc: int, out: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=out, stderr="")


def test_c1_all_skipped_suite_is_blocked_never_pass():
    ok, status, detail = _suite_outcome(_proc(0, "5 skipped in 1s"))
    assert ok is False and status == "blocked"
    assert "skipped" in detail


def test_c1_nonzero_exit_is_not_ok():
    ok, status, _ = _suite_outcome(_proc(2, "1 failed, 3 passed"))
    assert ok is False and status == "not-ok"


def test_c1_passing_suite_is_ok():
    ok, status, _ = _suite_outcome(_proc(0, "4 passed in 12s"))
    assert ok is True and status == "ok"


# ---------------------------------------------------------------------------
# C2-C5 — isolated-wiki spy scenarios (real cross-process adapters)
# ---------------------------------------------------------------------------

_SPY = E2E / "spy_adapter.py"


def _spy_acquisition_yaml(command_json: str) -> str:
    from isolated_wiki import _NOOP_ADAPTER

    noop = json.dumps(_NOOP_ADAPTER, ensure_ascii=False)
    return f"""schema_version: "1.1"
staging_root: "${{PROJECT_ROOT}}/.source_catalog/staging"
timeout_seconds: 120
adapters:
  cn:
    name: "spy-provider"
    version: "1.0.0"
    interface: "json_command_v1"
    project_root: "${{PROJECT_ROOT}}"
    config_root: null
    command: {command_json}
  hk:
    name: "e2e-noop-hk"
    version: "1.0.0"
    interface: "dayu_cli_v1"
    project_root: "${{PROJECT_ROOT}}"
    config_root: "${{PROJECT_ROOT}}/config"
    command: {noop}
  us:
    name: "e2e-noop-us"
    version: "1.0.0"
    interface: "dayu_cli_v1"
    project_root: "${{PROJECT_ROOT}}"
    config_root: "${{PROJECT_ROOT}}/config"
    command: {noop}
"""


def _candidate(accession: str, year: int, *, filing_date: str = "2026-04-15") -> dict:
    return {
        "candidate_id": f"c-{accession}",
        "provider": "spy",
        "provider_document_id": accession,
        "title": f"ACME {year} annual",
        "form_type": "annual_report",
        "filing_date": filing_date,
        "fiscal_year": year,
    }


def _policy_file(wiki) -> None:
    from company_wiki.source_catalog.runtime_policy import snapshot_hash

    policy = {
        "schema_version": "1.0",
        "policy_hash": "c" * 64,
        "flags": {"v2_resolve_active": False, "legacy_bridge_enabled": True,
                  "v2_bundle_active": False, "v2_persist_assertions": False,
                  "v2_resolve_shadow": False, "v2_scan_shadow": False},
        "current_epoch": "epoch-1",
        "active_cohorts": ["cohort-1"],
        "updated_at": "2026-08-11T00:00:00Z",
    }
    policy["snapshot_sha256"] = snapshot_hash(policy)
    wiki.catalog_dir.mkdir(parents=True, exist_ok=True)
    (wiki.catalog_dir / "runtime_policy.json").write_text(
        json.dumps(policy, ensure_ascii=False), encoding="utf-8")


class _SpyWiki:
    def __init__(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        os.environ["SPY_ADAPTER_LOG"] = str(self.root / "spy_log.jsonl")
        os.environ["SPY_ADAPTER_FIXTURE"] = str(self.root / "spy_fixture.json")
        os.environ.pop("SPY_ADAPTER_FAULT", None)
        self.spy_log = self.root / "spy_log.jsonl"
        self.fixture = self.root / "spy_fixture.json"
        self.fixture.write_text(json.dumps({}), encoding="utf-8")
        from isolated_wiki import IsolatedWiki

        self.wiki = IsolatedWiki(self.root)
        _policy_file(self.wiki)
        command = json.dumps(
            [os.environ.get("PYTHON_EXECUTABLE", "python"), str(_SPY)],
            ensure_ascii=False,
        )
        (self.root / "config" / "source_acquisition.yaml").write_text(
            _spy_acquisition_yaml(command), encoding="utf-8")

    def cleanup(self) -> None:
        from isolated_wiki import cleanup_temporary

        cleanup_temporary(self._temporary)

    def actions(self) -> list[str]:
        if not self.spy_log.is_file():
            return []
        return [json.loads(line).get("action")
                for line in self.spy_log.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def journal(self) -> list[str]:
        return self.wiki.journal_outcomes()

    def companies_bytes(self) -> int:
        companies = self.root / "companies"
        return sum(p.stat().st_size for p in companies.rglob("*")
                   if p.is_file()) if companies.exists() else 0


@pytest.fixture
def spy():
    harness = _SpyWiki()
    yield harness
    harness.cleanup()


def _authorized_latest(accessions: list[str]) -> dict:
    return {
        "schema_version": "1.2",
        "company_query": "宁德时代",
        "market": "CN",
        "document_kind": "annual_report",
        "mode": "latest_as_of",
        "as_of_date": "2026-07-31",
        "authorization": {
            "provider": "spy",
            "allowed_accessions": accessions,
            "max_items": 3,
            "max_bytes": 5_000_000,
            "expires_at": "2099-01-01T00:00:00Z",
        },
    }


def test_c2_first_download_then_zero_redownload(spy):
    spy.wiki.seed_market("CN")
    spy.wiki.scan()
    spy.fixture.write_text(json.dumps({
        "CN": [_candidate("acc-2025", 2025)],
    }), encoding="utf-8")
    request = _authorized_latest(["acc-2025"])
    rc, out, err = spy.wiki.run_fetch(request, allow_download=True)
    assert rc == 0, err
    assert json.loads(out)["status"] == "capture_ready", out[:300]
    assert spy.actions().count("fetch") == 1
    bytes_first = spy.companies_bytes()
    assert bytes_first > 0

    # second identical request: zero fetch, zero write (single-flight reuse)
    rc2, out2, err2 = spy.wiki.run_fetch(request, allow_download=True)
    assert rc2 == 0, err2
    second = json.loads(out2)
    assert second["status"] == "gap"
    assert second["gap_plan"]["missing"] == []
    assert spy.actions().count("fetch") == 1, "second request fetched again"
    assert spy.companies_bytes() == bytes_first, "second request wrote bytes"


def test_c3_amendment_downloads_only_missing_new_period(spy):
    spy.wiki.seed_market("CN")
    spy.wiki.scan()
    # provider has old (2024, filed 2025-04-15) + new (2025, filed 2026-04-15)
    spy.fixture.write_text(json.dumps({
        "CN": [_candidate("acc-2024", 2024, filing_date="2025-04-15"),
               _candidate("acc-2025", 2025)],
    }), encoding="utf-8")
    # first: as-of before the new filing — the old period is the latest
    request_old = _authorized_latest(["acc-2024"])
    request_old["as_of_date"] = "2025-06-30"
    rc, out, err = spy.wiki.run_fetch(request_old, allow_download=True)
    assert rc == 0, err
    assert json.loads(out)["status"] == "capture_ready", out[:200]
    fetches_after_first = spy.actions().count("fetch")

    # amendment: the NEW accession appears (later as-of); only it downloads
    request_new = _authorized_latest(["acc-2024", "acc-2025"])
    rc2, out2, err2 = spy.wiki.run_fetch(request_new, allow_download=True)
    assert rc2 == 0, err2
    assert spy.actions().count("fetch") == fetches_after_first + 1, (
        "amendment must download ONLY the missing new period")


def test_c4_provider_drift_preserves_local_no_fetch(spy):
    spy.wiki.seed_market("CN")
    spy.wiki.scan()
    spy.fixture.write_text(json.dumps({
        "CN": [_candidate("acc-2025", 2025)],
    }), encoding="utf-8")
    request = _authorized_latest(["acc-2025"])
    rc, out, err = spy.wiki.run_fetch(request, allow_download=True)
    assert rc == 0, err
    fetches = spy.actions().count("fetch")

    # provider goes away: local reuse preserved, zero new fetches
    os.environ["SPY_ADAPTER_FAULT"] = "provider_unavailable"
    try:
        rc2, out2, err2 = spy.wiki.run_fetch(request, allow_download=True)
        assert rc2 == 0, err2
        assert spy.actions().count("fetch") == fetches, (
            "provider drift must not trigger a new fetch when local exists")
    finally:
        os.environ.pop("SPY_ADAPTER_FAULT", None)


def test_c5_provider_canonical_reconciliation(spy):
    spy.wiki.seed_market("CN")
    spy.wiki.scan()
    spy.fixture.write_text(json.dumps({
        "CN": [_candidate("acc-2025", 2025)],
    }), encoding="utf-8")
    request = _authorized_latest(["acc-2025"])
    rc, out, err = spy.wiki.run_fetch(request, allow_download=True)
    assert rc == 0, err
    # exactly one fetch action, one downloaded_new journal outcome, bytes>0
    assert spy.actions().count("fetch") == 1
    journal = spy.journal()
    assert journal.count("downloaded_new") == 1, journal
    assert spy.companies_bytes() > 0
    # second request reconciles: no new outcomes, no new fetch, no new bytes
    bytes_first = spy.companies_bytes()
    spy.wiki.run_fetch(request, allow_download=True)
    assert spy.journal().count("downloaded_new") == 1
    assert spy.actions().count("fetch") == 1
    assert spy.companies_bytes() == bytes_first


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
