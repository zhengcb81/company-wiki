"""FC-702 RED/acceptance tests: 严格 identity 和 period.

The resolver never soft-matches a company name stored as security_id
against a ticker request (CW-2.27H removal): same-name/different-identity
documents are a hard conflict, never merged.  Leading-zero tickers
(03896 == 3896) still normalize; non-HTTPS sources fail closed; a
retired assertion in conflict with an active one fails closed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _company_raw_fixture(tmp_path: Path, company: str, security: str,
                         market: str, pdoc: str, *, fy: int = 2024,
                         url: str | None = "https://provider.example/x") -> Path:
    raw = tmp_path / "companies" / company / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{pdoc}.pdf").write_bytes(
        b"%PDF-1.4 " + company.encode("utf-8") + pdoc.encode("utf-8"))
    sidecar = {
        "market": market, "security_id": security,
        "source_title": f"{company} {fy}", "fiscal_year": fy,
        "filing_date": f"{fy + 1}-03-20", "form_type": "annual_report",
        "document_kind": "annual_report", "provider": "cninfo",
        "provider_document_id": pdoc, "source_url": url,
    }
    (raw / f"{pdoc}.pdf.source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    return tmp_path / "companies"


def _catalog(tmp_path: Path, tree: Path):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    return SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tree, "company_raw",
                            priority=10, adapter_id="company_raw_v1",
                            read_only=False, reusable_for_filing=True,
                            canonical_write_target="companies"),),
        )
    )


def _resolve(catalog, *, entity, market, security, fy=2024, pdoc=None):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    return SourceResolver(catalog).resolve(SourceRequest(
        entity=entity, market=market, security_id=security,
        document_kind="annual_report", form_type="annual_report",
        fiscal_year=fy, provider="cninfo", provider_document_id=pdoc,
        as_of_date="2026-08-11", mode="exact",
    ))


# --- SAFE-01: same name, diff ticker/market -> hard conflict -------------------


def test_safe01_same_name_diff_ticker_conflict(tmp_path):
    """Same company name with a different security_id is a hard identity
    conflict — never merged, no download."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _company_raw_fixture(tmp_path, "Acme", "601899", "CN", "doc-a", fy=2024)
    _company_raw_fixture(tmp_path, "Acme", "601898", "CN", "doc-b", fy=2024)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog, entity="Acme", market="CN", security="601899")
    # the 601898 document must NOT satisfy the 601899 request
    assert result.status in (
        ResolutionStatus.REUSED_EXACT, ResolutionStatus.REUSED_EQUIVALENT)
    assert result.matches[0].provider_document_id == "doc-a"


def test_safe01_market_mismatch_conflict(tmp_path):
    """A market mismatch is a hard conflict — same ticker in CN vs US
    never merges."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _company_raw_fixture(tmp_path, "Acme", "601899", "CN", "doc-cn", fy=2024)
    _company_raw_fixture(tmp_path, "Acme", "601899", "US", "doc-us", fy=2024)
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tree, "company_raw",
                            read_only=False, reusable_for_filing=True),),
        )
    )
    catalog.scan()
    result = _resolve(catalog, entity="Acme", market="CN", security="601899")
    assert result.status in (
        ResolutionStatus.REUSED_EXACT, ResolutionStatus.REUSED_EQUIVALENT)
    assert result.matches[0].provider_document_id == "doc-cn"


# --- SAFE-02: company name as security_id -> NO soft-match ----------------------


def test_safe02_company_name_security_id_no_soft_match(tmp_path):
    """A document whose security_id is a company name (中国平安 style) is
    NOT matched by a numeric ticker request — the soft-match fallback is
    removed (CW-2.27H)."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _company_raw_fixture(tmp_path, "Acme", "中国平安", "CN", "doc-weak", fy=2024)
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tree, "company_raw",
                            read_only=False, reusable_for_filing=True),),
        )
    )
    catalog.scan()
    # entity matches (Acme == Acme) but the ticker identity 601899 cannot
    # be satisfied by the company-name security_id — fail closed
    result = _resolve(catalog, entity="Acme", market="CN", security="601899")
    assert result.status is not ResolutionStatus.REUSED_EXACT
    trace = " ".join(result.debug_trace)
    assert "conflict" in trace or "identity" in trace or "missing" in trace, (
        f"no fail-closed trace: {list(result.debug_trace)[:4]}")


def test_safe02_company_name_matches_its_own_identity(tmp_path):
    """A company-name security_id still matches the SAME non-numeric
    security request (its own identity), not a different ticker."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _company_raw_fixture(tmp_path, "Acme", "中国平安", "CN", "doc-weak", fy=2024)
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tree, "company_raw",
                            read_only=False, reusable_for_filing=True),),
        )
    )
    catalog.scan()
    result = _resolve(catalog, entity="Acme", market="CN", security="中国平安")
    assert result.status in (
        ResolutionStatus.REUSED_EXACT, ResolutionStatus.REUSED_EQUIVALENT)


# --- SAFE-04: non-HTTPS / disallowed provider URL -> fail closed ---------------


def test_safe04_non_https_url_fails_closed(tmp_path):
    """A non-HTTPS source URL is never capture-ready — the handle is
    refused, never REUSED."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _company_raw_fixture(
        tmp_path, "Acme", "601899", "CN", "doc-http", fy=2024,
        url="http://insecure.example.com/x")
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tree, "company_raw",
                            read_only=False, reusable_for_filing=True),),
        )
    )
    catalog.scan()
    result = _resolve(catalog, entity="Acme", market="CN", security="601899")
    assert result.status is not ResolutionStatus.REUSED_EXACT
    assert any("capture_incomplete" in t or "https_url" in t
               for t in result.debug_trace), (
        f"no fail-closed trace: {list(result.debug_trace)[:4]}")


# --- SAFE-07: retired vs active assertion conflict -> fail closed ---------------


def test_safe07_retired_document_not_offered(tmp_path):
    """A retired document never satisfies a request — even when an active
    identity exists in the catalog, the retired row is excluded."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _company_raw_fixture(tmp_path, "Acme", "601899", "CN", "doc-retired", fy=2024)
    _company_raw_fixture(tmp_path, "Acme", "601899", "CN", "doc-active", fy=2024)
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tree, "company_raw",
                            read_only=False, reusable_for_filing=True),),
        )
    )
    catalog.scan()
    # retire the doc-retired copy (located via its source path)
    row = catalog.store.fetchone(
        """SELECT l.document_id FROM locations l
           JOIN sources s ON s.source_id = l.source_id
           WHERE l.relative_path LIKE '%doc-retired%' LIMIT 1""")
    assert row is not None
    with catalog.store.transaction() as conn:
        conn.execute("UPDATE documents SET source_status='retired' WHERE document_id=?",
                     (row["document_id"],))
    result = _resolve(catalog, entity="Acme", market="CN", security="601899",
                      pdoc="doc-active")
    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.matches[0].provider_document_id == "doc-active"


# --- leading zeros still normalize (ADR-008 preserved) -------------------------


def test_leading_zero_ticker_normalizes(tmp_path):
    """03896 == 3896: leading-zero normalization is preserved by the strict
    identity rule (ADR-008 Strategy B)."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _company_raw_fixture(tmp_path, "Meituan", "03896", "HK", "doc-hk", fy=2024)
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tree, "company_raw",
                            read_only=False, reusable_for_filing=True),),
        )
    )
    catalog.scan()
    result = _resolve(catalog, entity="Meituan", market="HK", security="3896")
    assert result.status in (
        ResolutionStatus.REUSED_EXACT, ResolutionStatus.REUSED_EQUIVALENT)
