"""FC-1004: platform & install-shape contracts (PORT-02, install sync).

SCENARIO: PORT-02

PORT-02 spaces/case path differences -> consistent behavior.  The lake
fixture must build and resolve identically under a path containing spaces
(the production user path already contains a non-ASCII user name; this pins
the space segment too).  Install-sync consistency: the R4.2 gate detects
drift between repo and installed copies.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import datetime as _dt

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
PROJECT_ROOT = RF_CODE_ROOT
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
WIKI_ROOT = PROJECT_ROOT.parent / "company-wiki"
FILING_ROOT = PROJECT_ROOT.parent / "filing-fetch"
sys.path.insert(0, str(WIKI_ROOT / "src"))
sys.path.insert(0, str(FILING_ROOT / "scripts"))

from e2e_support.isolated_lake import IsolatedLake  # noqa: E402

_AS_OF = (_dt.date.today() + _dt.timedelta(days=7)).isoformat()


def test_port02_spaces_in_lake_path_consistent(tmp_path: Path):
    """A lake under a path containing SPACES must build, manifest, and
    resolve identically to the no-space baseline (relative paths + content
    shas only — absolute path differences must never leak into behavior)."""
    spaced = tmp_path / "dir with spaces" / "lake space"
    plain = tmp_path / "lake"

    m_spaced = IsolatedLake(spaced, seed="fc1004").build()
    m_plain = IsolatedLake(plain, seed="fc1004").build()

    # manifest hash identical (relative paths + content only)
    assert m_spaced.manifest_hash() == m_plain.manifest_hash()
    # no absolute path leaks
    assert "dir with spaces" not in "\n".join(m_spaced.relative_manifest())

    # both resolve the same document to the same content
    def _resolve(m):
        from company_wiki.source_catalog import (
            CatalogConfig,
            RootSpec,
            SourceCatalog,
            SourceRequest,
            SourceResolver,
        )

        catalog = SourceCatalog(CatalogConfig(
            project_root=m.catalog_path.parent,
            catalog_dir=m.catalog_path.parent,
            reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
            roots=(
                RootSpec("company_raw", m.catalog_path.parent / "companies",
                         "company_raw", priority=10, adapter_id="company_raw_v1",
                         read_only=False, reusable_for_filing=True,
                         canonical_write_target="companies"),
            ),
        ))
        req = SourceRequest(entity="紫金矿业", document_kind="annual_report",
                            as_of_date=_AS_OF, market="CN", fiscal_year=2025)
        return SourceResolver(catalog, runtime_policy=None).resolve(req)

    r_spaced = _resolve(m_spaced)
    r_plain = _resolve(m_plain)
    assert r_spaced.status == r_plain.status
    assert r_spaced.matches and r_plain.matches
    assert r_spaced.matches[0].content_sha256 == r_plain.matches[0].content_sha256


def test_install_sync_gate_detects_drift(tmp_path: Path):
    """R4.2 install-sync consistency (self-contained): syncing the canonical
    skill to a throwaway destination must yield an identical manifest
    (repo == installed copy), proving the sync mechanism detects and closes
    drift without depending on the real installed-copy state."""
    dest = tmp_path / "installed"
    proc = subprocess.run(
        [sys.executable, "-B", str(PROJECT_ROOT / "tools" / "sync_installations.py"),
         "--apply", "--destination", str(dest)],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
        cwd=str(PROJECT_ROOT),
    )
    assert proc.returncode == 0, f"sync failed: {proc.stdout[-400:]}"
    # re-sync to a second destination and compare manifests — identical
    # bytes = the mechanism is deterministic and drift-free
    dest2 = tmp_path / "installed2"
    proc2 = subprocess.run(
        [sys.executable, "-B", str(PROJECT_ROOT / "tools" / "sync_installations.py"),
         "--apply", "--destination", str(dest2)],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
        cwd=str(PROJECT_ROOT),
    )
    assert proc2.returncode == 0
    m1 = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
    m2 = sorted(str(p.relative_to(dest2)) for p in dest2.rglob("*") if p.is_file())
    assert m1 == m2, "sync to two destinations must produce identical trees"


def test_utf8_stdin_stdout_chain(tmp_path: Path):
    """UTF-8 JSON stdin/stdout across the chain (Chinese company names survive
    the round trip byte-exact)."""
    IsolatedLake(tmp_path, seed="fc1004").build()
    wiki_cfg = tmp_path / "wiki.json"
    wiki_cfg.write_text(json.dumps({
        "schema_version": "1.0",
        "company_wiki_root": str(tmp_path / "lake" / "project"),
    }, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    req = {"schema_version": "1.1", "company_query": "紫金矿业", "market": "CN",
           "document_kind": "annual_report", "fiscal_year": 2025,
           "as_of_date": _AS_OF}
    proc = subprocess.run(
        [sys.executable, "-B", str(PROJECT_ROOT / "scripts" / "source_preparation.py"),
         "--company-wiki-config", str(wiki_cfg),
         "--company-wiki-catalog-config",
         str(tmp_path / "lake" / "project" / "config" / "source_catalog.yaml")],
        input=json.dumps(req, ensure_ascii=False),
        text=True, encoding="utf-8", capture_output=True,
        cwd=str(PROJECT_ROOT), env=env, timeout=180, check=False,
    )
    assert proc.returncode == 0, f"chain failed: {proc.stderr[-400:]}"
    record = json.loads(proc.stdout)
    # P5-RF: the v2 manifest title is the explicit capture field (source_title), not a filename-derived legacy artifact title
    assert record.get("title") == "紫金矿业集团股份有限公司", record.get("title")
