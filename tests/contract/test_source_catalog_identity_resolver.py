"""RED contracts for identity-aware Source Resolver.

CW-2.24 Phase 2: resolver must filter by market/security_id, not just serialize them.
"""

from __future__ import annotations

import json
from pathlib import Path


def _multi_market_catalog(tmp_path: Path):
    """Create a catalog with one company having CN and HK listings in separate dirs."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"

    # CN listing — separate directory to avoid being grouped with HK
    cn_dir = project / "companies" / "Acme" / "raw" / "cn_annual"
    cn_dir.mkdir(parents=True)
    cn = cn_dir / "2026-03-01_Acme_CN_annual.txt"
    cn.write_text("CN annual report content", encoding="utf-8")
    cn_sidecar = cn.with_suffix(".txt.source.json")
    cn_sidecar.write_text(
        json.dumps(
            {
                "market": "CN",
                "security_id": "600519",
                "ticker": "600519",
                "source_title": "Acme 2025 Annual Report",
                "form_type": "年报",
                "filing_date": "2026-03-01",
                "fiscal_year": 2025,
            }
        ),
        encoding="utf-8",
    )

    # HK listing — separate directory
    hk_dir = project / "companies" / "Acme" / "raw" / "hk_annual"
    hk_dir.mkdir(parents=True)
    hk = hk_dir / "2026-03-05_Acme_HK_annual.txt"
    hk.write_text("HK annual report content", encoding="utf-8")
    hk_sidecar = hk.with_suffix(".txt.source.json")
    hk_sidecar.write_text(
        json.dumps(
            {
                "market": "HK",
                "security_id": "00700",
                "ticker": "00700",
                "source_title": "Acme 2025 Annual Report",
                "form_type": "annual",
                "filing_date": "2026-03-05",
                "fiscal_year": 2025,
            }
        ),
        encoding="utf-8",
    )

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec(
                    "company_raw", project / "companies", "company_raw", priority=10
                ),
            ),
        )
    )
    catalog.scan()
    return catalog, cn, hk


def _no_identity_catalog(tmp_path: Path):
    """Catalog with a document that has no market/security_id metadata."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    company = project / "companies" / "Beta" / "raw" / "research"
    company.mkdir(parents=True)
    doc = company / "2026-01-15_Beta_report.txt"
    doc.write_text("some report", encoding="utf-8")

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec(
                    "company_raw", project / "companies", "company_raw", priority=10
                ),
            ),
        )
    )
    catalog.scan()
    return catalog, doc


# ---------------------------------------------------------------------------
# RED 1: same company, different markets — request must match correct market
# ---------------------------------------------------------------------------


class TestMultiMarketIdentity:
    """同公司不同上市地，请求指定 market 只命中对应上市地。"""

    def test_cn_request_matches_cn_document(self, tmp_path):
        from company_wiki.source_catalog import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        catalog, cn, hk = _multi_market_catalog(tmp_path)
        request = SourceRequest(
            entity="Acme",
            market="CN",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        assert result.status is ResolutionStatus.REUSED_EQUIVALENT
        assert len(result.matches) == 1
        assert (
            "CN" in result.matches[0].canonical_path
            or "600519" in result.matches[0].canonical_path
        )

    def test_hk_request_matches_hk_document(self, tmp_path):
        from company_wiki.source_catalog import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        catalog, cn, hk = _multi_market_catalog(tmp_path)
        request = SourceRequest(
            entity="Acme",
            market="HK",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        assert result.status is ResolutionStatus.REUSED_EQUIVALENT
        assert len(result.matches) == 1
        assert (
            "HK" in result.matches[0].canonical_path
            or "00700" in result.matches[0].canonical_path
        )

    def test_cn_request_does_not_match_hk_document(self, tmp_path):
        """CN 请求不得命中 HK 文档。"""
        from company_wiki.source_catalog import SourceRequest, SourceResolver

        catalog, cn, hk = _multi_market_catalog(tmp_path)
        request = SourceRequest(
            entity="Acme",
            market="CN",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        for m in result.matches:
            assert "HK" not in m.canonical_path


# ---------------------------------------------------------------------------
# RED 2: security_id filtering
# ---------------------------------------------------------------------------


class TestSecurityIdFiltering:
    """security_id 不匹配时不得复用。"""

    def test_wrong_security_id_excluded(self, tmp_path):
        from company_wiki.source_catalog import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        catalog, cn, hk = _multi_market_catalog(tmp_path)
        request = SourceRequest(
            entity="Acme",
            market="CN",
            security_id="999999",  # wrong ID
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        # CN document has security_id=600519, not 999999
        assert result.status is ResolutionStatus.IDENTITY_CONFLICT

    def test_correct_security_id_matches(self, tmp_path):
        from company_wiki.source_catalog import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        catalog, cn, hk = _multi_market_catalog(tmp_path)
        request = SourceRequest(
            entity="Acme",
            market="CN",
            security_id="600519",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        assert result.status is ResolutionStatus.REUSED_EQUIVALENT


# ---------------------------------------------------------------------------
# RED 3: candidate identity missing — must fail closed
# ---------------------------------------------------------------------------


class TestIdentityMissingFailClosed:
    """CW-3.5: truly empty identity → fail_closed (strict)."""

    def test_request_with_market_but_candidate_no_identity(self, tmp_path):
        from company_wiki.source_catalog import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        catalog, doc = _no_identity_catalog(tmp_path)
        request = SourceRequest(
            entity="Beta",
            market="CN",
            document_kind="other",
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        # CW-3.5: empty security_id → fail_closed
        assert result.status == ResolutionStatus.IDENTITY_CONFLICT


# ---------------------------------------------------------------------------
# RED 4: backward compatibility — no identity in request still works
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """request 未提供 market/security_id 时保持向后兼容。"""

    def test_no_market_still_matches(self, tmp_path):
        from company_wiki.source_catalog import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        catalog, cn, hk = _multi_market_catalog(tmp_path)
        request = SourceRequest(
            entity="Acme",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        # Without market filter, both CN and HK match → ambiguous
        assert result.status is ResolutionStatus.AMBIGUOUS
        assert len(result.matches) == 2

    def test_no_market_old_entity_path(self, tmp_path):
        """旧式 entity 路径不提供 market 时仍兼容。"""
        from company_wiki.source_catalog import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        catalog, doc = _no_identity_catalog(tmp_path)
        request = SourceRequest(
            entity="Beta",
            document_kind="other",
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        # Should find the document (backward compatible)
        assert result.status is ResolutionStatus.REUSED_EQUIVALENT


# ---------------------------------------------------------------------------
# RED 5: existing fiscal/form/kind gates still hold
# ---------------------------------------------------------------------------


class TestExistingGatesPreserved:
    """fiscal_year/form_type/document_kind/as_of_date 门禁继续成立。"""

    def test_wrong_fiscal_year_excluded(self, tmp_path):
        from company_wiki.source_catalog import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        catalog, doc = _no_identity_catalog(tmp_path)
        request = SourceRequest(
            entity="Beta",
            document_kind="other",
            fiscal_year=2024,  # wrong year (doc is 2026)
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        assert result.status is ResolutionStatus.MISSING

    def test_wrong_document_kind_excluded(self, tmp_path):
        from company_wiki.source_catalog import (
            ResolutionStatus,
            SourceRequest,
            SourceResolver,
        )

        catalog, cn, hk = _multi_market_catalog(tmp_path)
        request = SourceRequest(
            entity="Acme",
            market="CN",
            document_kind="broker_research",  # wrong kind
            fiscal_year=2025,
            as_of_date="2026-07-18",
        )
        result = SourceResolver(catalog).resolve(request)
        assert result.status is ResolutionStatus.MISSING
