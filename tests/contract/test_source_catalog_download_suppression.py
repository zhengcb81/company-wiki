"""RED contracts for Phase 3: download suppression and Dayu request minimization.

Ensures: resolver hit → discover/fetch=0; missing+no_download → adapter=0;
identity conflict → adapter=0.
"""

from __future__ import annotations

from pathlib import Path


class _SpyAdapter:
    """Adapter that counts calls but never downloads."""

    def __init__(self, name: str = "spy"):
        self.name = name
        self.version = "1.0"
        self.discover_calls = 0
        self.fetch_calls = 0

    def discover(self, request):
        self.discover_calls += 1
        return iter([])

    def fetch(self, candidate, staging_root):
        self.fetch_calls += 1
        raise AssertionError("fetch must not be called")


def _catalog_with_identity(tmp_path: Path):
    """Catalog with a document that has market/security_id."""

    from helpers.source_factory import canonical_source, company_raw_catalog

    canonical_source(
        tmp_path,
        filename="2026-02-20_Acme_annual.txt",
    )
    catalog = company_raw_catalog(tmp_path)
    return catalog


def _catalog_empty(tmp_path: Path):
    """Empty catalog with no documents."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
        )
    )
    catalog.scan()
    return catalog


# ---------------------------------------------------------------------------
# RED 1: resolver hit → discover/fetch = 0
# ---------------------------------------------------------------------------


class TestResolverHitSuppressesDownload:
    """已有 capture-ready source 时，adapter 调用次数为 0。"""

    def test_existing_source_adapter_zero_calls(self, tmp_path):
        from company_wiki.source_catalog import (
            AcquisitionCoordinator,
            AcquisitionStatus,
            AdapterRegistry,
            SourceRequest,
        )

        catalog = _catalog_with_identity(tmp_path)
        spy = _SpyAdapter()
        coordinator = AcquisitionCoordinator(
            catalog=catalog,
            adapters=AdapterRegistry(cn=spy, hk=spy, us=spy),
            staging_root=tmp_path / "staging",
        )
        result = coordinator.resolve_or_stage(
            SourceRequest(
                entity="Acme",
                market="CN",
                document_kind="annual_report",
                fiscal_year=2025,
                as_of_date="2026-07-18",
                allow_download=True,
            )
        )
        assert result.status is AcquisitionStatus.REUSED
        assert spy.discover_calls == 0
        assert spy.fetch_calls == 0


# ---------------------------------------------------------------------------
# RED 2: missing + allow_download=False → adapter = 0
# ---------------------------------------------------------------------------


class TestMissingNoDownload:
    """missing 且未授权下载时，adapter 调用次数为 0。"""

    def test_missing_no_download_adapter_zero(self, tmp_path):
        from company_wiki.source_catalog import (
            AcquisitionCoordinator,
            AcquisitionStatus,
            AdapterRegistry,
            SourceRequest,
        )

        catalog = _catalog_empty(tmp_path)
        spy = _SpyAdapter()
        coordinator = AcquisitionCoordinator(
            catalog=catalog,
            adapters=AdapterRegistry(cn=spy, hk=spy, us=spy),
            staging_root=tmp_path / "staging",
        )
        result = coordinator.resolve_or_stage(
            SourceRequest(
                entity="Acme",
                market="CN",
                document_kind="annual_report",
                fiscal_year=2025,
                as_of_date="2026-07-18",
                allow_download=False,
            )
        )
        assert result.status is AcquisitionStatus.MISSING
        assert spy.discover_calls == 0
        assert spy.fetch_calls == 0


# ---------------------------------------------------------------------------
# RED 3: identity conflict → adapter = 0
# ---------------------------------------------------------------------------


class TestIdentityConflictNoDownload:
    """identity 冲突时，adapter 不应被调用。"""

    def test_wrong_market_adapter_zero(self, tmp_path):
        from company_wiki.source_catalog import (
            AcquisitionCoordinator,
            AcquisitionStatus,
            AdapterRegistry,
            SourceRequest,
        )

        catalog = _catalog_with_identity(tmp_path)
        spy = _SpyAdapter()
        coordinator = AcquisitionCoordinator(
            catalog=catalog,
            adapters=AdapterRegistry(cn=spy, hk=spy, us=spy),
            staging_root=tmp_path / "staging",
        )
        # Request HK but catalog only has CN → identity conflict
        result = coordinator.resolve_or_stage(
            SourceRequest(
                entity="Acme",
                market="HK",
                document_kind="annual_report",
                fiscal_year=2025,
                as_of_date="2026-07-18",
                allow_download=True,
            )
        )
        assert result.status is AcquisitionStatus.MISSING
        assert spy.discover_calls == 0
        assert spy.fetch_calls == 0
