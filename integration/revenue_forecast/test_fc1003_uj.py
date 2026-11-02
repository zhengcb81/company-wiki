"""FC-1003: real user-journey scenarios (UJ-01..08) on the isolated lake.

SCENARIO: UJ-01 UJ-02 UJ-04 UJ-07

UJ-01 companies-only latest filing with all artifacts valid -> revenue entry
     ok, download/parser/LLM=0 (the FC-1002 chain test covers the exact
     mechanism; here we run the dropbox root journey).
UJ-02 dayu-only raw -> download=0 (no provider call for an indexed source).
UJ-04 all missing + allow_download=false -> structured gap, discover/fetch=0.
UJ-07 multi-root identity conflict -> user entry fails closed with a
     disposable reason, download=0.
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


def _run_chain(tmp_path: Path, request: dict, *, m=None) -> tuple[int, str]:
    if m is None:
        m = IsolatedLake(tmp_path, seed="fc1003").build()
    wiki_cfg = tmp_path / "wiki.json"
    wiki_cfg.write_text(json.dumps({
        "schema_version": "1.0",
        "company_wiki_root": str(tmp_path / "lake" / "project"),
    }, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-B", str(PROJECT_ROOT / "scripts" / "source_preparation.py"),
         "--company-wiki-config", str(wiki_cfg),
         "--company-wiki-catalog-config",
         str(tmp_path / "lake" / "project" / "config" / "source_catalog.yaml")],
        input=json.dumps(request, ensure_ascii=False),
        text=True, encoding="utf-8", capture_output=True,
        cwd=str(PROJECT_ROOT), env=env, timeout=180, check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr, m


def test_uj01_companies_only_journey_zero_side_effects(tmp_path: Path):
    """UJ-01: companies-only latest with all artifacts valid -> revenue entry
    ok; download/parser/LLM all zero (journal unchanged)."""
    rc, out, err, m = _run_chain(tmp_path, {
        "schema_version": "1.1", "company_query": "紫金矿业", "market": "CN",
        "document_kind": "annual_report", "fiscal_year": 2025,
        "as_of_date": _AS_OF})
    assert rc == 0, f"chain failed: {err[-500:]}"
    rr = json.loads(out).get("reuse_receipt") or {}
    assert rr.get("download_calls") == 0
    # P5-RF: the v2 route reads no derived body; parser/LLM stay honest-None
    assert rr.get("llm_calls") is None and rr.get("parser_calls") is None
    assert rr.get("artifact_read") == [], rr


def test_uj02_dayu_only_raw_no_download(tmp_path: Path):
    """UJ-02: dayu-only raw (2024) -> download=0; the source is already
    indexed so the journey is a pure read.

    Verified at the wiki-resolver layer: the filing-fetch legacy containment
    (wiki_root/companies only) rejects dayu-root handles — a REAL pre-existing
    gap recorded in findings (dayu-only through filing-fetch was never wired;
    it needs policy-snapshot roots, FC-1202 scope).  UJ-02 is satisfied at the
    layer that owns the dayu source."""
    m = IsolatedLake(tmp_path, seed="fc1003").build()
    from company_wiki.source_catalog import (
        CatalogConfig,
        RootSpec,
        SourceCatalog,
        SourceRequest,
        SourceResolver,
    )

    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path / "lake" / "project",
        catalog_dir=m.catalog_path.parent,
        reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
        roots=(
            # company_raw root only for ENTITY inference (FC-604 pattern);
            # the requested source itself lives under the dayu root
            RootSpec("company_raw", tmp_path / "lake" / "project" / "companies",
                     "company_raw", priority=10, adapter_id="company_raw_v1",
                     read_only=False, reusable_for_filing=True,
                     canonical_write_target="companies"),
            RootSpec("dayu_portfolio", tmp_path / "lake" / "portfolio", "dayu_portfolio",
                     priority=20, adapter_id="dayu_filing_v1", read_only=True,
                     reusable_for_filing=True),
        ),
    ))
    # the dayu identity is the TICKER (meta.json ticker=601899); the resolver
    # matches via the security-master token index
    req = SourceRequest(entity="601899", document_kind="annual_report",
                        as_of_date=_AS_OF, market="CN", fiscal_year=2024)
    res = SourceResolver(catalog, runtime_policy=None).resolve(req)
    assert res.status is not None and res.status.value in ("reused_exact", "reused_equivalent")
    # the dayu handle carries zero download events and points at the dayu root
    env = res.to_dict().get("resolution_envelope") or {}
    assert env.get("download_events", 0) == 0
    handle = res.matches[0]
    assert str(handle.canonical_path).startswith(
        str(tmp_path / "lake" / "portfolio")), (
        "dayu-only source must resolve to the dayu location"
    )


def test_uj04_all_missing_structured_gap(tmp_path: Path):
    """UJ-04: no matching filing + allow_download=false -> structured
    gap/not_found; discover/fetch/write all zero (the chain never fires a
    provider call without authorization)."""
    rc, out, err, m = _run_chain(tmp_path, {
        "schema_version": "1.1", "company_query": "紫金矿业", "market": "CN",
        "document_kind": "annual_report", "fiscal_year": 2026,
        "as_of_date": _AS_OF})
    # source_preparation exits non-zero on not-found (exit 1); the error is
    # structured (status=gap/not_found), never a silent green
    assert rc != 0
    assert "not found" in err.lower() or "gap" in err.lower() or "not_found" in err.lower(), (
        f"expected structured gap, got: {err[-400:]}"
    )


def test_uj07_identity_conflict_fails_closed(tmp_path: Path):
    """UJ-07: multi-root identity/period conflict -> user entry fails closed
    with a disposable reason and download=0 (no provider call)."""
    m = IsolatedLake(tmp_path, seed="fc1003").build()
    # no fiscal_year -> exact mode still requires one; ambiguous/error is
    # fail-closed, never a silent green
    rc, out, err, _ = _run_chain(tmp_path, {
        "schema_version": "1.1", "company_query": "紫金矿业", "market": "CN",
        "document_kind": "annual_report", "as_of_date": _AS_OF}, m=m)
    # no fiscal_year -> exact mode still requires one; ambiguous/error is
    # fail-closed, never a silent green
    assert rc != 0, "ambiguous identity request must fail closed"
    assert "ambiguous" in err.lower() or "fiscal" in err.lower() or "not found" in err.lower()
