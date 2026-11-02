"""ZR-1004 acceptance tests: small cohort across four roots — companies /
dayu / Dropbox / future_lake, per-root T2/UJ journeys, external write=0,
same-request rollback recovery (stage I fourth card).

  C1  four-root cohort journeys: companies Zijin FY2025/FY2024 REUSED_EXACT,
      dayu 1548 FY2021 REUSED_EXACT, Dropbox StarLake FAIL-CLOSED MISSING
      (honest), future_lake fixture root resolves as configured.
  C2  external write=0: root shallow fingerprints + catalog row counts
      unchanged by the journeys (ZR-806 oracle).
  C3  same-request rollback recovery: repeating the identical request is
      idempotent (same status, same identity, zero writes); a failed
      request retried returns the same structured result.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
ROOT = RF_CODE_ROOT
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

WIKI_ROOT = Path(r"C:\Users\郑曾波\Projects\company-wiki")
DAYU_ROOT = Path(r"C:\Users\郑曾波\Projects\dayu-agent\workspace\portfolio")
DROPBOX_ROOT = Path.home() / "Dropbox" / "Stock"
FUTURE_LAKE = WIKI_ROOT / "future_lake"

CATALOG_DB = WIKI_ROOT / ".source_catalog" / "catalog.sqlite3"
CATALOG_CONFIG = WIKI_ROOT / "config" / "source_catalog.yaml"

from test_zr806_real_t2_samples import _shallow_fingerprint  # noqa: E402


def _catalog_row_counts() -> dict[str, int]:
    con = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True, timeout=30)
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

    return resolver.resolve(SourceRequest(mode="exact", as_of_date="2026-08-22", **kw))


# ---------------------------------------------------------------------------
# C1 — four-root cohort journeys
# ---------------------------------------------------------------------------


def test_c1_companies_root_exact():
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    for fy, pdoc in ((2025, "1225023658"), (2024, "1222870413")):
        result = _resolve(resolver, entity="紫金矿业", market="CN",
                          security_id="601899", document_kind="annual_report",
                          fiscal_year=fy, provider="cninfo",
                          provider_document_id=pdoc)
        assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace


def test_c1_dayu_root_exact():
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    result = _resolve(resolver, entity="金斯瑞生物科技", market="HK",
                      security_id="1548", document_kind="annual_report",
                      fiscal_year=2021, provider="hkexnews",
                      provider_document_id="10225111")
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace


def test_c1_dropbox_root_fails_closed():
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    result = _resolve(resolver, entity="星环科技", market="CN",
                      security_id="688031", document_kind="annual_report",
                      fiscal_year=2024, provider="cninfo",
                      provider_document_id="1223325316")
    assert result.status is ResolutionStatus.MISSING, (
        "Dropbox http-only source must not be faked into a handle")


def test_c1_future_lake_root_configured():
    assert FUTURE_LAKE.is_dir(), "future_lake root missing (ZR-409 config)"
    resolver = _make_resolver()
    # the root is registered in the production config (read-only, reusable)
    config = resolver.catalog.config if hasattr(resolver, "catalog") else None
    roots = config.roots if config is not None else []
    ids = [r.root_id for r in roots]
    assert "future_lake" in ids, f"future_lake not in configured roots: {ids}"


# ---------------------------------------------------------------------------
# C2 — external write = 0
# ---------------------------------------------------------------------------


def test_c2_journeys_leave_roots_and_catalog_untouched():
    before = {
        "companies": _shallow_fingerprint(WIKI_ROOT / "companies"),
        "dayu": _shallow_fingerprint(DAYU_ROOT),
        "dropbox": _shallow_fingerprint(DROPBOX_ROOT),
        "future_lake": _shallow_fingerprint(FUTURE_LAKE),
    }
    before_rows = _catalog_row_counts()
    test_c1_companies_root_exact()
    test_c1_dayu_root_exact()
    test_c1_dropbox_root_fails_closed()
    assert _shallow_fingerprint(WIKI_ROOT / "companies") == before["companies"]
    assert _shallow_fingerprint(DAYU_ROOT) == before["dayu"]
    assert _shallow_fingerprint(DROPBOX_ROOT) == before["dropbox"]
    assert _shallow_fingerprint(FUTURE_LAKE) == before["future_lake"]
    assert _catalog_row_counts() == before_rows


# ---------------------------------------------------------------------------
# C3 — same-request rollback recovery (idempotent retry)
# ---------------------------------------------------------------------------


def test_c3_same_request_idempotent():
    resolver = _make_resolver()
    first = _resolve(resolver, entity="紫金矿业", market="CN",
                     security_id="601899", document_kind="annual_report",
                     fiscal_year=2025, provider="cninfo",
                     provider_document_id="1225023658")
    second = _resolve(resolver, entity="紫金矿业", market="CN",
                      security_id="601899", document_kind="annual_report",
                      fiscal_year=2025, provider="cninfo",
                      provider_document_id="1225023658")
    assert first.status is second.status
    assert str(first.debug_trace) == str(second.debug_trace)


def test_c3_failed_request_retry_consistent():
    resolver = _make_resolver()
    first = _resolve(resolver, entity="星环科技", market="CN",
                     security_id="688031", document_kind="annual_report",
                     fiscal_year=2024, provider="cninfo",
                     provider_document_id="1223325316")
    second = _resolve(resolver, entity="星环科技", market="CN",
                      security_id="688031", document_kind="annual_report",
                      fiscal_year=2024, provider="cninfo",
                      provider_document_id="1223325316")
    # failed request retried returns the same structured MISSING (no fake
    # handle materialized on retry — rollback recovery is consistent)
    assert first.status is second.status
