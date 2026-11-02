"""ZR-805 acceptance tests (phase G): CN/HK/US T3 first-download + second
zero-download, with strict download authorization.

Layering (no duplication — the REAL T3 execution suite is owned by
filing-fetch `tests/test_e2e_download.py`, opt-in via
FILING_FETCH_E2E_DOWNLOAD=1, and runs CN/US/HK against real providers on a
temporary wiki with idempotent second-run reuse and no-residue checks):

  gate      the T3 suite exists, is opt-in ONLY (skipUnless gate), and
            covers all three markets plus a corruption-rejection case —
            a missing network or missing authorization is a designed
            blocked/skip, never a fake pass.
  journal   an unauthorized request for a missing source leaves the
            acquisition journal with ZERO downloaded_new outcomes and no
            new canonical bytes — the journal is the independent oracle
            against fabricated download=0 claims (AUD2-04).
  flag      the download path is reachable ONLY with the explicit
            --allow-download flag surfaced by the revenue entry; without
            it the chain refuses before any provider call.

Zero production changes; hermetic except the cross-repo structural read.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
from pathlib import Path

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
PROJECT_ROOT = RF_CODE_ROOT
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "e2e_support"))
FILING_FETCH_ROOT = Path.home() / "Projects" / "filing-fetch"
if not (FILING_FETCH_ROOT / "scripts" / "fetch_filing.py").is_file():
    FILING_FETCH_ROOT = PROJECT_ROOT.parent / "filing-fetch"
FILING_FETCH_TESTS = FILING_FETCH_ROOT / "tests" / "test_e2e_download.py"

AS_OF = (_dt.date.today() + _dt.timedelta(days=7)).isoformat()


# ---------------------------------------------------------------------------
# gate — T3 execution lives behind an explicit opt-in, all markets covered
# ---------------------------------------------------------------------------


def test_t3_suite_is_opt_in_and_covers_three_markets():
    assert FILING_FETCH_TESTS.exists(), "filing-fetch T3 suite missing"
    source = FILING_FETCH_TESTS.read_text(encoding="utf-8")
    # explicit opt-in gate — never runs real downloads by default
    assert 'os.environ.get("FILING_FETCH_E2E_DOWNLOAD") == "1"' in source
    assert "skipUnless" in source
    # three markets + corruption rejection are all present as scenarios
    for marker in (
        "def test_download_cn_annual_report",
        "def test_download_us_annual_report",
        "def test_download_hk_annual_report",
        "def test_download_rejects_corrupted_local_copy",
        # first download + second zero-download semantics
        "second run must not download again",
    ):
        assert marker in source, f"T3 suite missing: {marker}"


# ---------------------------------------------------------------------------
# journal — unauthorized missing-source request downloads nothing
# ---------------------------------------------------------------------------


def _journal_downloaded_new(catalog_dir: Path) -> int:
    """Independent oracle: acquisition journal outcomes (JSONL, upstream)."""
    journal = catalog_dir / "acquisition_attempts.jsonl"
    if not journal.is_file():
        return 0
    count = 0
    for line in journal.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        outcome = record.get("outcome") or (record.get("attempt") or {}).get("outcome")
        if outcome == "downloaded_new":
            count += 1
    return count


def test_unauthorized_missing_source_zero_downloads_in_journal(tmp_path):
    from e2e_support.isolated_lake import IsolatedLake

    IsolatedLake(tmp_path, seed="zr805").build()
    project = tmp_path / "lake" / "project"
    before = _journal_downloaded_new(project / ".source_catalog")

    wiki_cfg = tmp_path / "wiki.json"
    wiki_cfg.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "company_wiki_root": str(project),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    request = {
        "schema_version": "1.1",
        "company_query": "紫金矿业",
        "market": "CN",
        "document_kind": "annual_report",
        "fiscal_year": 2023,
        "as_of_date": AS_OF,
    }
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROJECT_ROOT / "scripts" / "source_preparation.py"),
            "--company-wiki-config",
            str(wiki_cfg),
            "--filing-fetch-root",
            str(FILING_FETCH_ROOT),
            "--company-wiki-catalog-config",
            str(project / "config" / "source_catalog.yaml"),
        ],
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        timeout=180,
        check=False,
    )
    # unauthorized missing source: structured refusal, no record
    assert proc.returncode != 0
    assert proc.stdout.strip() == ""
    lines = [line for line in proc.stderr.strip().splitlines() if line.strip()]
    payload = json.loads(lines[-1])
    assert "not_found" in payload["error"]
    # independent oracle: the journal recorded zero downloads
    assert (
        _journal_downloaded_new(project / ".source_catalog")
        == before
    )


# ---------------------------------------------------------------------------
# flag — the download path requires the explicit authorization flag
# ---------------------------------------------------------------------------


def test_download_flag_is_explicit_in_revenue_entry_surface():
    source = (PROJECT_ROOT / "scripts" / "source_preparation.py").read_text(
        encoding="utf-8"
    )
    # the authorization flag exists and is opt-in (default False)
    assert '"--allow-download"' in source
    assert "allow_download: bool = False" in source
    # the client it spawns is the filing-fetch entry (no second downloader)
    assert "filing_fetch_client.py" in source


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-q"])
