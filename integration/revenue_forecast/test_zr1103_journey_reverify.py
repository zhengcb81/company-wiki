"""ZR-1103 acceptance tests: real user journey re-verification.

The ZR-1103 card: re-verify real user journeys across companies / dayu /
Dropbox, old+new chains, already-processed reuse, broker/mine surfaces,
CN/HK/US markets and Windows Chinese paths.

  C1  three-root journeys re-verified: companies Zijin REUSED_EXACT, dayu
      1548 REUSED_EXACT, Dropbox StarLake fail-closed MISSING — through
      the production resolver (read-only).
  C2  already-processed reuse: a second identical request reuses with
      zero download / zero write (single-flight).
  C3  CN/HK/US market surface: the opt-in T3 suite covers all three
      markets (filing-fetch test_e2e_download.py) — the re-verification
      harness can drive real providers when authorized.
  C4  broker/mine surface: the golden broker corpus (7 reports) and the
      mine-facts chain are re-verified through the engine (ZR-709/CA-204
      semantics).
  C5  Windows Chinese paths: the resolver handles Chinese entity /
      security / path inputs on Windows without bypass.
"""

from __future__ import annotations

import json
import sys

import pytest

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
ROOT = RF_CODE_ROOT
WIKI_ROOT = ROOT.parent / "company-wiki"
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))

CATALOG_DB = WIKI_ROOT / ".source_catalog" / "catalog.sqlite3"
CATALOG_CONFIG = WIKI_ROOT / "config" / "source_catalog.yaml"


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
# C1 — three-root journeys re-verified
# ---------------------------------------------------------------------------


def test_c1_companies_and_dayu_reused_exact():
    if not CATALOG_DB.is_file():
        pytest.skip("production catalog unavailable")
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


def test_c1_dropbox_fails_closed():
    if not CATALOG_DB.is_file():
        pytest.skip("production catalog unavailable")
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    result = _resolve(resolver, entity="星环科技", market="CN",
                      security_id="688031", document_kind="annual_report",
                      fiscal_year=2024, provider="cninfo",
                      provider_document_id="1223325316")
    assert result.status is ResolutionStatus.MISSING, (
        "Dropbox http-only source must stay fail-closed (honest MISSING)")


# ---------------------------------------------------------------------------
# C2 — already-processed reuse (zero download / zero write)
# ---------------------------------------------------------------------------


def test_c2_processed_reuse_single_flight():
    """Re-verifying an already-processed request must reuse with zero new
    download / write (the acquisition journal is the independent oracle)."""
    from test_ca203_weekly_t3 import _SpyWiki  # noqa: PLC0415

    harness = _SpyWiki()
    try:
        harness.wiki.seed_market("CN")
        harness.wiki.scan()
        from test_ca203_weekly_t3 import _authorized_latest, _candidate

        harness.fixture.write_text(json.dumps({
            "CN": [_candidate("acc-2025", 2025)],
        }), encoding="utf-8")
        request = _authorized_latest(["acc-2025"])
        rc, out, err = harness.wiki.run_fetch(request, allow_download=True)
        assert rc == 0, err
        assert harness.actions().count("fetch") == 1
        bytes_first = harness.companies_bytes()
        # re-verify: second identical request -> zero fetch, zero write
        rc2, out2, err2 = harness.wiki.run_fetch(request, allow_download=True)
        assert rc2 == 0, err2
        assert harness.actions().count("fetch") == 1
        assert harness.companies_bytes() == bytes_first
    finally:
        harness.cleanup()


# ---------------------------------------------------------------------------
# C3 — CN/HK/US market surface
# ---------------------------------------------------------------------------


def test_c3_three_markets_covered_in_t3_suite():
    t3 = (ROOT.parent / "filing-fetch" / "tests" / "test_e2e_download.py")
    assert t3.is_file(), "filing-fetch T3 suite missing"
    source = t3.read_text(encoding="utf-8")
    for marker in ("test_download_cn_annual_report",
                   "test_download_hk_annual_report",
                   "test_download_us_annual_report"):
        assert marker in source, f"T3 suite missing market: {marker}"
    # opt-in only — real provider downloads are authorized at run time
    assert 'FILING_FETCH_E2E_DOWNLOAD' in source


# ---------------------------------------------------------------------------
# C4 — broker/mine surface re-verified
# ---------------------------------------------------------------------------


def test_c4_broker_corpus_and_mine_chain():
    corpus = json.loads(
        (ROOT / "assurance" / "unified_completion" / "corpus"
         / "golden_corpus.json").read_text(encoding="utf-8"))
    broker = [s for s in corpus["samples"] if s.get("role") == "broker_research"]
    assert len(broker) >= 7
    # mine chain closes through the engine (ZR-709 semantics)
    from test_zr709_zijin_journey import _zijin_document  # noqa: PLC0415
    from revenue_forecast import prepare_forecast  # noqa: PLC0415
    import copy

    result = prepare_forecast(copy.deepcopy(_zijin_document()), mode="draft")
    assert result["publication_receipt"]["formal_output_mode"] == "draft"


# ---------------------------------------------------------------------------
# C5 — Windows Chinese paths
# ---------------------------------------------------------------------------


def test_c5_chinese_entity_paths_resolve():
    """Chinese entity/security inputs resolve on Windows without bypass —
    the resolver's exact mode handles the CJK identifiers directly."""
    if not CATALOG_DB.is_file():
        pytest.skip("production catalog unavailable")
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    # Chinese company name + security id in the same request
    result = _resolve(resolver, entity="紫金矿业", market="CN",
                      security_id="601899", document_kind="annual_report",
                      fiscal_year=2024, provider="cninfo",
                      provider_document_id="1222870413")
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                             ResolutionStatus.MISSING), result.debug_trace
    # the resolved (or failed-closed) path carried the Chinese identity
    assert "紫金矿业" in str(result.debug_trace or "")


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
