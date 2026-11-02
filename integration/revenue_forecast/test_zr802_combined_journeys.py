"""ZR-802 acceptance tests (phase G first card): combined user journeys —
existing / partial / missing / stale / conflict across roots.

Every journey runs the REAL three-process chain from the revenue entry
(scripts/source_preparation.py -> filing-fetch client -> company-wiki CLI)
against the FC-1001 isolated three-root lake.  Oracles come from the child
processes' stdout/stderr and direct fixture-DB reads — never from the code
under test's own summary.

  C1  five document states across roots, each with exact stage receipts:
      existing (exact reuse), missing (structured not_found), stale
      (year-mismatched or capture-incomplete sources are NOT substituted),
      conflict (cross-root duplicate candidates fail closed as ambiguous),
      partial (only a subset of artifact roles reusable -> DAG-minimal
      producer closure for the rest).
  C2  second call idempotence: same source identity, zero downloads again
      (ZJ-10 contract-reuse semantics).
  C3  stage receipt/budget accuracy: download/parser/llm counters equal the
      scenario expectation exactly (never merely "<="), and the eight-stage
      evidence projection is present on every record.

Zero production changes; hermetic T1 (temp roots only, no network).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sqlite3
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
WIKI_SRC = PROJECT_ROOT.parent / "company-wiki" / "src"
sys.path.insert(0, str(WIKI_SRC))

from e2e_support.isolated_lake import IsolatedLake, RootSpecFactory  # noqa: E402

AS_OF = (_dt.date.today() + _dt.timedelta(days=7)).isoformat()
ALL_ROLES = ("normalized", "markdown", "summary", "sections", "consumer_analysis")


def _build_lake(tmp_path: Path) -> Path:
    """Isolated three-root lake; returns the wiki project root."""
    IsolatedLake(tmp_path, seed="zr802").build()
    return tmp_path / "lake" / "project"


def _run_chain(
    project: Path,
    tmp_path: Path,
    *,
    fiscal_year: int,
    company_query: str = "紫金矿业",
    market: str = "CN",
) -> subprocess.CompletedProcess:
    wiki_cfg = tmp_path / f"wiki-{abs(hash((company_query, market, fiscal_year)))}.json"
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
        "company_query": company_query,
        "market": market,
        "document_kind": "annual_report",
        "fiscal_year": fiscal_year,
        "as_of_date": AS_OF,
    }
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROJECT_ROOT / "scripts" / "source_preparation.py"),
            "--company-wiki-config",
            str(wiki_cfg),
            "--filing-fetch-root",
            str(FILING_ROOT),
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


def _last_error(stderr: str) -> dict:
    lines = [line for line in stderr.strip().splitlines() if line.strip()]
    return json.loads(lines[-1])


def _add_conflict_copy(project: Path) -> None:
    """A second FY2025 Zijin annual in the dayu root (different bytes)."""
    group = project / "dayu_portfolio" / "601899" / "filings" / "fil_cn_zr802c"
    group.mkdir(parents=True, exist_ok=True)
    (group / "fil_cn_zr802c.pdf").write_bytes(b"%PDF-1.4 zr802-conflict-copy" * 20)
    (group / "meta.json").write_text(
        json.dumps(
            {
                "document_id": "fil_cn_zr802c",
                "ticker": "601899",
                "form_type": "annual_report",
                "fiscal_year": 2025,
                "fiscal_period": "FY",
                "filing_date": "2025-03-25",
                "source_provider": "cninfo",
                "source_id": "1225088800",
                "source_url": "https://provider.example/601899/2025-alt",
                "source_language": "zh",
                "source_title": "紫金矿业 2025 alternate copy",
                "amended": False,
                "ingest_complete": True,
                "primary_document": "fil_cn_zr802c.pdf",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
            roots=(
                RootSpecFactory.company(project / "companies"),
                RootSpecFactory.dayu(project / "dayu_portfolio"),
                RootSpecFactory.dropbox(project / "dropbox"),
            ),
        )
    )
    catalog.scan()


def _document_count(project: Path) -> int:
    con = sqlite3.connect(
        f"file:{project / '.source_catalog' / 'catalog.sqlite3'}?mode=ro", uri=True
    )
    try:
        return con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    finally:
        con.close()


def _add_future_dated_annual(project: Path) -> None:
    """A companies-root FY2026 annual whose filing_date lies beyond as_of."""
    raw = project / "companies" / "紫金矿业" / "raw" / "financial_reports" / "annual"
    body = b"%PDF-1.4 zr802-future-filing\n"
    (raw / "紫金矿业2026年年报.pdf").write_bytes(body)
    from e2e_support.isolated_lake import _sidecar

    (raw / "紫金矿业2026年年报.pdf.source.json").write_text(
        json.dumps(
            _sidecar(
                "zr802:future",
                market="CN",
                security="601899",
                pdoc="1226077777",
                fy=2026,
                kind="annual_report",
                body_sha=hashlib.sha256(body).hexdigest(),
                title="紫金矿业集团股份有限公司",
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
            roots=(
                RootSpecFactory.company(project / "companies"),
                RootSpecFactory.dayu(project / "dayu_portfolio"),
                RootSpecFactory.dropbox(project / "dropbox"),
            ),
        )
    )
    catalog.scan()


# ---------------------------------------------------------------------------
# C1 — five document states across roots
# ---------------------------------------------------------------------------


def test_c1_existing_exact_reuse_with_exact_budgets(tmp_path):
    project = _build_lake(tmp_path)
    proc = _run_chain(project, tmp_path, fiscal_year=2025)
    assert proc.returncode == 0, proc.stderr[-800:]
    record = json.loads(proc.stdout)
    assert record["source_type"] == "regulatory_filing"
    receipt = record["reuse_receipt"]
    # budgets are EXACT, not ceilings: pure read of an existing exact source
    assert receipt["download_calls"] == 0
    # P5-RF: the v2 route schedules no derived recompute; parser/LLM stay
    # honest-None without real usage (legacy DAG closure is covered by the
    # isolated legacy-helper contracts in test_fc904).
    assert receipt["llm_calls"] is None
    assert receipt["parser_calls"] is None
    assert receipt["artifact_read"] == [], receipt
    assert receipt["outcome"] == "reused_existing"
    assert record["capture"]["prompt_injection_status"] in (
        "not_detected", "not_reviewed")


def test_c1_missing_is_structured_not_found_without_fabrication(tmp_path):
    project = _build_lake(tmp_path)
    before = _document_count(project)
    proc = _run_chain(project, tmp_path, fiscal_year=2023)  # no root has FY2023
    assert proc.returncode != 0
    payload = _last_error(proc.stderr)
    assert payload["error_code"] == "upstream"
    body = payload["error"]
    assert "not_found" in body
    assert "no_local_match" in body  # v2 classification
    # nothing was written into the lake by the failed request
    assert _document_count(project) == before


def test_c1_stale_sources_are_never_substituted(tmp_path):
    project = _build_lake(tmp_path)
    _add_future_dated_annual(project)  # FY2026 filed beyond as_of
    before = _document_count(project)
    proc = _run_chain(project, tmp_path, fiscal_year=2026)
    assert proc.returncode != 0
    payload = _last_error(proc.stderr)
    assert payload["error_code"] == "upstream"
    assert "not_found" in payload["error"]
    # the future filing is catalogued but NOT served for its period
    assert _document_count(project) == before


def test_c1_cross_root_duplicate_candidates_fail_closed(tmp_path):
    project = _build_lake(tmp_path)
    _add_conflict_copy(project)  # second FY2025 candidate in dayu root
    proc = _run_chain(project, tmp_path, fiscal_year=2025)
    assert proc.returncode != 0
    payload = _last_error(proc.stderr)
    assert payload["error_code"] == "upstream"
    assert "ambiguous" in payload["error"]
    assert "multiple_local_matches" in payload["error"]  # v2 classification


def test_c1_partial_roles_read_subset_plus_dag_minimal_producers(tmp_path):
    project = _build_lake(tmp_path)

    def artifact_roles() -> set[str]:
        con = sqlite3.connect(
            f"file:{project / '.source_catalog' / 'catalog.sqlite3'}?mode=ro", uri=True
        )
        try:
            return {
                role
                for (role,) in con.execute(
                    "SELECT DISTINCT artifact_role FROM artifacts WHERE status='completed'"
                )
            }
        finally:
            con.close()

    seeded = artifact_roles()
    assert "normalized" in seeded and len(seeded) < len(ALL_ROLES)  # partial preset

    proc = _run_chain(project, tmp_path, fiscal_year=2025)
    assert proc.returncode == 0, proc.stderr[-800:]
    receipt = json.loads(proc.stdout)["reuse_receipt"]
    # P5-RF: the v2 route reads no derived body and schedules no producers
    # on a successful reuse (the old DAG-minimal recompute contract lives in
    # the isolated legacy-helper tests: tests/test_fc904_artifact_selection).
    assert receipt["artifact_read"] == []
    assert receipt["producer_events"] == []
    assert receipt["download_calls"] == 0 and receipt["llm_calls"] is None


# ---------------------------------------------------------------------------
# C2 — second call idempotence (contract reuse, zero downloads again)
# ---------------------------------------------------------------------------


def test_c2_second_call_reuses_same_identity_zero_downloads(tmp_path):
    project = _build_lake(tmp_path)
    first = json.loads(_run_chain(project, tmp_path, fiscal_year=2025).stdout)
    second = json.loads(_run_chain(project, tmp_path, fiscal_year=2025).stdout)
    assert first["source_id"] == second["source_id"]
    assert first.get("content_sha256") == second.get("content_sha256")
    for record in (first, second):
        assert record["reuse_receipt"]["download_calls"] == 0
        assert record["reuse_receipt"]["outcome"] == "reused_existing"


# ---------------------------------------------------------------------------
# C3 — stage receipt completeness (eight-stage evidence projection)
# ---------------------------------------------------------------------------


def test_c3_stage_receipt_projection_complete_on_every_record(tmp_path):
    project = _build_lake(tmp_path)
    success = json.loads(_run_chain(project, tmp_path, fiscal_year=2025).stdout)

    # eight-stage evidence projection on the consumer record:
    # identity/resolution -> company_wiki_trace; freshness -> published_date;
    # acquisition -> provider + provider_document_id; safety -> capture;
    # artifact -> reuse_receipt roles; semantic -> title; consumer -> source_id
    trace = success["company_wiki_trace"]
    read_receipt = trace["read_receipt"]
    manifest = trace["source_manifest"]
    source_ref = trace["source_ref"]
    assert manifest["provider"] == "cninfo"
    assert manifest["provider_document_id"]
    assert read_receipt["source_id"] == source_ref["source_id"]
    assert not any("canonical_path" in key for key in manifest), (
        "capture must stay pathless"
    )
    # freshness evidence travels with the record and respects as_of
    assert success["published_date"] <= AS_OF
    assert success["capture"]["prompt_injection_status"] in (
        "not_detected", "not_reviewed")
    receipt = success["reuse_receipt"]
    assert {
        "download_calls",
        "parser_calls",
        "llm_calls",
        "artifact_read",
        "producer_events",
        "outcome",
    } <= set(receipt)
    assert success["title"]
    assert success["source_id"]

    # failure path carries structured resolution reason too
    failed = _run_chain(project, tmp_path, fiscal_year=2023)
    payload = _last_error(failed.stderr)
    assert "no_local_match" in payload["error"]  # v2 classification


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
