"""ZR-804 acceptance tests (phase G): platform & install shape —
Windows case-insensitivity, no silent sibling fallback, installed-copy
executability, cross-platform portability surface.

fc1004 already pins spaces-in-path, UTF-8 stdio and the install-sync drift
gate; this suite closes the remaining gaps:

  case      a lake reached through a case-swapped project directory name
             (Windows-insensitive filesystem) runs the identical journey.
  sibling   without explicit --company-wiki-config the chain FAILS CLOSED
             (structured upstream error) — it must never silently resolve
             a hard-coded sibling location.
  installed each isolated installation copy (agents/claude/codex) executes as an
             entrypoint and reports the SAME engine version + manifest hash
             as the canonical tree (R4.2 drift made visible at runtime).
  portable  active production scripts carry no Windows-only constructs
             (os.system / process-attribute structs) — Linux semantic parity.

Zero production changes; hermetic T1 (installed-copy probe writes only tmp_path).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
PROJECT_ROOT = RF_CODE_ROOT
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "e2e_support"))
FILING_ROOT = Path.home() / "Projects" / "filing-fetch"
if not (FILING_ROOT / "scripts" / "fetch_filing.py").is_file():
    FILING_ROOT = PROJECT_ROOT.parent / "filing-fetch"
sys.path.insert(0, str(FILING_ROOT))
sys.path.insert(0, str(FILING_ROOT.parent / "company-wiki" / "src"))

AS_OF = (_dt.date.today() + _dt.timedelta(days=7)).isoformat()
ACTIVE_SCRIPTS = (
    "source_preparation.py",
    "filing_fetch_client.py",
    "revenue_forecast.py",
    "revenue_backtest.py",
    "publication_registry.py",
    "company_wiki_source.py",
)


def _chain(
    project: Path,
    tmp_path: Path,
    *,
    wiki_root: Path | None = None,
    with_config: bool = True,
):
    if with_config:
        cfg = tmp_path / f"wiki-{abs(hash(str(wiki_root)))}.json"
        cfg.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "company_wiki_root": str(wiki_root),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        config_args = ["--company-wiki-config", str(cfg)]
    else:
        config_args = []
    request = {
        "schema_version": "1.1",
        "company_query": "紫金矿业",
        "market": "CN",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "as_of_date": AS_OF,
    }
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    catalog_args = []
    if wiki_root is not None:
        catalog_yaml = wiki_root / "config" / "source_catalog.yaml"
        if catalog_yaml.is_file():
            catalog_args = ["--company-wiki-catalog-config", str(catalog_yaml)]
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROJECT_ROOT / "scripts" / "source_preparation.py"),
            *config_args,
            *catalog_args,
            "--filing-fetch-root",
            str(FILING_ROOT),
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


# ---------------------------------------------------------------------------
# case — Windows-insensitive path variant runs the identical journey
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    sys.platform != "win32", reason="case-insensitive resolution is Windows semantics"
)
def test_case_swapped_project_dir_runs_identical_journey(tmp_path):
    from e2e_support.isolated_lake import IsolatedLake

    IsolatedLake(tmp_path, seed="zr804").build()
    project = tmp_path / "lake" / "project"
    variant = tmp_path / "lake" / project.name.swapcase()
    assert variant.exists()  # same physical dir under swapped case

    proc = _chain(project, tmp_path, wiki_root=variant)
    assert proc.returncode == 0, proc.stderr[-400:]
    record = json.loads(proc.stdout)
    receipt = record["reuse_receipt"]
    assert receipt["outcome"] == "reused_existing"
    assert receipt["download_calls"] == 0
    # golden-trace semantics identical to the canonical-case journey: same
    # source identity fields regardless of path casing used to reach it.
    canonical = json.loads(_chain(project, tmp_path, wiki_root=project).stdout)
    assert canonical["source_id"] == record["source_id"]


# ---------------------------------------------------------------------------
# sibling — missing explicit config fails closed (never a fixed fallback)
# ---------------------------------------------------------------------------


def test_missing_explicit_config_fails_closed_without_record(tmp_path, monkeypatch):
    # The checked-in filing-fetch config expands USER_PROFILE to locate the
    # canonical wiki. Isolate that default too, otherwise this test can read
    # real owner-host filings and pass/fail based on the developer's library.
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "isolated-profile"))
    proc = _chain(tmp_path, tmp_path, with_config=False)
    assert proc.returncode != 0
    assert proc.stdout.strip() == ""  # never a fabricated handle/record
    lines = [line for line in proc.stderr.strip().splitlines() if line.strip()]
    payload = json.loads(lines[-1])
    assert payload["error_code"] in {"upstream", "bad_request"}
    # structured reason, not a crash dump
    assert "error" in payload


# ---------------------------------------------------------------------------
# installed — synced copies execute and report identical identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("surface", ("agents", "claude", "codex"))
def test_installed_copy_executes_with_canonical_identity(tmp_path, surface):
    # Exercise the real sync command against an isolated installation only.
    destination = tmp_path / surface / "skills"
    sync = subprocess.run(
        [sys.executable, '-B', str(PROJECT_ROOT / 'tools/sync_installations.py'),
         '--apply', '--destination', str(destination)],
        capture_output=True, text=True, encoding='utf-8', timeout=30,
    )
    assert sync.returncode == 0, sync.stderr
    install_root = destination / 'revenue-forecast'
    assert not (install_root / 'tests').exists()
    assert not (install_root / 'tools').exists()
    entry = install_root / 'scripts' / 'revenue_forecast.py'
    assert entry.is_file()
    canonical_out = subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROJECT_ROOT / "scripts" / "revenue_forecast.py"),
            "--version",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(PROJECT_ROOT),
        timeout=120,
    )
    copy_out = subprocess.run(
        [sys.executable, "-B", str(entry), "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert canonical_out.returncode == 0
    assert copy_out.returncode == 0
    # golden trace semantic equality: same engine + manifest identity line
    assert copy_out.stdout.strip() == canonical_out.stdout.strip()
    assert copy_out.stdout.startswith("revenue-forecast ")
    assert "manifest_sha256=" in copy_out.stdout


# ---------------------------------------------------------------------------
# portable — no Windows-only constructs in active production scripts
# ---------------------------------------------------------------------------


def test_active_scripts_carry_no_windows_only_constructs():
    # CREATE_NO_WINDOW is a deliberate cross-platform guard (suppresses
    # console popups on Windows subprocesses only) — allowed.
    forbidden = (
        "os.system",
        "startupinfo",
        "SetConsoleCtrlHandler",
        "shell=True",
    )
    for name in ACTIVE_SCRIPTS:
        source = (PROJECT_ROOT / "scripts" / name).read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in source, f"{name} uses {marker}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
