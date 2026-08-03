"""Contract tests for portfolio -> company_raw promotion (reuse without re-download).

Covers: promotion mechanics through CanonicalSourceWriter.import_staged,
identity normalization (G2), the prefer-new metadata merge (G1 regression:
sidecar must carry top-level market), idempotency, dry-run, filters, and
fail-fast guards.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
from company_wiki.source_catalog.portfolio_promoter import (
    PortfolioPromotionError,
    PromotionIdentity,
    promote_all_for_entity,
    promote_from_portfolio,
)
from company_wiki.source_catalog.resolver import (
    ResolutionStatus,
    SourceRequest,
    SourceResolver,
)

IDENTITY = PromotionIdentity(canonical_name="金山雲", market="HK", security_id="03896")
AS_OF = "2026-08-02"
SHA = "efe2ccd923b744eb69166aebf5f9b32ab7560efe3f6c44f2c6bcf4672fec1fa8"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _portfolio_meta(*, pdf_sha: str, source_url: str | None = None) -> dict:
    return {
        "document_id": "fil_cn_test",
        "ticker": "3896",
        "company_id": "3896_HKEX",
        "company_name": "金山雲",
        "form_type": "FY",
        "fiscal_year": 2025,
        "fiscal_period": "FY",
        "filing_date": "2026-04-23",
        "first_ingested_at": "2026-06-04T20:51:46+00:00",
        "source_provider": "hkexnews",
        "source_id": "12118317",
        "source_url": source_url
        or "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0423/2026042301428_c.pdf",
        "source_language": "zh",
        "source_title": "2025 年度報告",
        "pdf_sha256": pdf_sha,
        "amended": False,
    }


def _env(tmp_path: Path):
    """Temp catalog with a dayu_portfolio root + company_raw root and one
    indexed portfolio filing (first seen via the dayu scan, so it starts with
    dayu_meta metadata and NO market/security_id — the promotion must upgrade
    it via the prefer-new merge)."""
    project = tmp_path / "project"
    companies = project / "companies"
    portfolio = tmp_path / "dayu" / "portfolio"
    entity_dir = portfolio / "3896"
    entity_dir.mkdir(parents=True)
    (entity_dir / "meta.json").write_text(
        json.dumps(
            {
                "company_id": "3896_HKEX",
                "company_name": "金山雲",
                "ticker": "3896",
                "market": "HK",
            }
        ),
        encoding="utf-8",
    )
    filing = entity_dir / "filings" / "fil_cn_test"
    filing.mkdir(parents=True)
    (filing / "fil_cn_test.pdf").write_bytes(b"portfolio annual report bytes")
    (filing / "meta.json").write_text(
        json.dumps(_portfolio_meta(pdf_sha=_sha("portfolio annual report bytes"))),
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10),
                RootSpec("dayu_portfolio", portfolio, "dayu_portfolio", priority=20),
            ),
        )
    )
    catalog.scan()
    staging = tmp_path / "staging"
    writer = CanonicalSourceWriter(catalog, staging_root=staging)
    return catalog, writer, portfolio


def _resolve(catalog, request: SourceRequest):
    return SourceResolver(catalog).resolve(request)


def test_promote_creates_canonical_location_and_resolves_reused_exact(tmp_path):
    catalog, writer, portfolio = _env(tmp_path)

    result = promote_from_portfolio(
        catalog, writer, portfolio, IDENTITY,
        document_id="fil_cn_test", as_of_date=AS_OF,
    )

    assert result.status == "imported_new"
    assert result.content_sha256 == _sha("portfolio annual report bytes")
    canonical = Path(result.canonical_path)
    assert "companies" in str(canonical).replace("\\", "/")
    assert canonical.is_file()
    assert canonical.with_name(canonical.name + ".source.json").is_file()

    resolution = _resolve(
        catalog,
        SourceRequest(
            entity=IDENTITY.canonical_name,
            market=IDENTITY.market,
            security_id=IDENTITY.security_id,
            document_kind="annual_report",
            form_type="FY",
            fiscal_year=2025,
            fiscal_period="FY",
            language="zh",
            provider="hkexnews",
            provider_document_id="12118317",
            as_of_date=AS_OF,
        ),
    )
    assert resolution.status is ResolutionStatus.REUSED_EXACT
    assert resolution.matches[0].capture_ready is True
    assert resolution.matches[0].snapshot_sha256 == result.content_sha256
    assert resolution.matches[0].https_url.startswith("https://")


def test_promote_is_idempotent(tmp_path):
    catalog, writer, portfolio = _env(tmp_path)
    promote_from_portfolio(
        catalog, writer, portfolio, IDENTITY,
        document_id="fil_cn_test", as_of_date=AS_OF,
    )
    second = promote_from_portfolio(
        catalog, writer, portfolio, IDENTITY,
        document_id="fil_cn_test", as_of_date=AS_OF,
    )
    assert second.status == "deduplicated_after_download"
    # No second copy was written.
    annual = (
        catalog.config.roots[0].path
        / "金山雲" / "raw" / "financial_reports" / "annual"
    )
    assert len(list(annual.glob("*.pdf"))) == 1


def test_dry_run_writes_nothing(tmp_path):
    catalog, writer, portfolio = _env(tmp_path)
    result = promote_from_portfolio(
        catalog, writer, portfolio, IDENTITY,
        document_id="fil_cn_test", as_of_date=AS_OF, dry_run=True,
    )
    assert result.status == "dry_run"
    annual = (
        catalog.config.roots[0].path
        / "金山雲" / "raw" / "financial_reports" / "annual"
    )
    assert not annual.exists() or not list(annual.glob("*.pdf"))


def test_promoted_document_metadata_carries_acquisition_identity(tmp_path):
    """G1/G2 regression: the promoted document's metadata must expose the
    resolver vocabulary (market/security_id/language/provider/pdid) after the
    prefer-new merge."""
    catalog, writer, portfolio = _env(tmp_path)
    promote_from_portfolio(
        catalog, writer, portfolio, IDENTITY,
        document_id="fil_cn_test", as_of_date=AS_OF,
    )
    rows = catalog.store.fetchall(
        """SELECT d.metadata_json FROM documents d
        JOIN locations l ON l.document_id=d.document_id
        JOIN sources s ON s.source_id=l.source_id
        WHERE s.content_sha256=? AND l.root_id='company_raw'""",
        (_sha("portfolio annual report bytes"),),
    )
    assert rows
    acquisition = json.loads(rows[0]["metadata_json"]).get("acquisition") or {}
    assert acquisition.get("market") == "HK"
    assert acquisition.get("security_id") == "03896"
    assert acquisition.get("language") == "zh"
    assert acquisition.get("provider") == "hkexnews"
    assert acquisition.get("provider_document_id") == "12118317"
    assert acquisition.get("source_url", "").startswith("https://")


def test_promote_all_filters_by_kind_and_year(tmp_path):
    catalog, writer, portfolio = _env(tmp_path)
    # second document: H1 2025 (semi-annual)
    filing = portfolio / "3896" / "filings" / "fil_h1_2025"
    filing.mkdir(parents=True)
    (filing / "fil_h1_2025.pdf").write_bytes(b"interim bytes")
    meta = _portfolio_meta(pdf_sha=_sha("interim bytes"))
    meta.update(document_id="fil_h1_2025", form_type="H1", filing_date="2025-09-26")
    (filing / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    catalog.scan()

    only_annual = promote_all_for_entity(
        catalog, writer, portfolio, IDENTITY,
        as_of_date=AS_OF, document_kind="annual_report",
    )
    assert {p.document_id for p in only_annual} == {"fil_cn_test"}
    only_2025 = promote_all_for_entity(
        catalog, writer, portfolio, IDENTITY,
        as_of_date=AS_OF, fiscal_year=2025,
    )
    assert {p.document_id for p in only_2025} == {"fil_cn_test", "fil_h1_2025"}


def test_missing_pdf_fails_fast(tmp_path):
    catalog, writer, portfolio = _env(tmp_path)
    (portfolio / "3896" / "filings" / "fil_cn_test" / "fil_cn_test.pdf").unlink()
    try:
        promote_from_portfolio(
            catalog, writer, portfolio, IDENTITY,
            document_id="fil_cn_test", as_of_date=AS_OF,
        )
    except PortfolioPromotionError:
        return
    raise AssertionError("expected PortfolioPromotionError for missing PDF")


def test_pdf_sha_mismatch_fails_fast(tmp_path):
    catalog, writer, portfolio = _env(tmp_path)
    meta_path = portfolio / "3896" / "filings" / "fil_cn_test" / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["pdf_sha256"] = "0" * 64
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    try:
        promote_from_portfolio(
            catalog, writer, portfolio, IDENTITY,
            document_id="fil_cn_test", as_of_date=AS_OF,
        )
    except PortfolioPromotionError:
        return
    raise AssertionError("expected PortfolioPromotionError for sha mismatch")


def test_non_https_source_url_fails_fast(tmp_path):
    catalog, writer, portfolio = _env(tmp_path)
    meta_path = portfolio / "3896" / "filings" / "fil_cn_test" / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["source_url"] = "http://www1.hkexnews.hk/x.pdf"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    try:
        promote_from_portfolio(
            catalog, writer, portfolio, IDENTITY,
            document_id="fil_cn_test", as_of_date=AS_OF,
        )
    except PortfolioPromotionError:
        return
    raise AssertionError("expected PortfolioPromotionError for non-HTTPS url")
