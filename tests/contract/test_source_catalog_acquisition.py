"""Contracts for query-first routing and staging-only download adapters."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


class _ExplodingAdapter:
    name = "must_not_be_called"
    version = "1.0.0"
    discover_calls = 0
    fetch_calls = 0

    def discover(self, request):
        self.discover_calls += 1
        raise AssertionError("discovery must not run when the source is reusable")

    def fetch(self, candidate, staging_dir):
        self.fetch_calls += 1
        raise AssertionError("fetch must not run when the source is reusable")


class _FakeAdapter:
    name = "fake_hkex"
    version = "1.2.3"

    def __init__(self, *, outside_path: Path | None = None):
        self.discover_calls = 0
        self.fetch_calls = 0
        self.outside_path = outside_path

    def discover(self, request):
        from company_wiki.source_catalog import DownloadCandidate

        self.discover_calls += 1
        return (
            DownloadCandidate(
                candidate_id="hkex:2025:12345",
                provider="hkex",
                provider_document_id="12345",
                market="HK",
                entity=request.entity,
                title="ACME 2025 Annual Report",
                source_url="https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0320/12345.pdf",
                document_kind="annual_report",
                form_type="annual_report",
                filing_date="2026-03-20",
                fiscal_year=2025,
                fiscal_period="FY",
                language="en",
                amended=False,
            ),
        )

    def fetch(self, candidate, staging_dir):
        from company_wiki.source_catalog import DownloadReceipt

        self.fetch_calls += 1
        path = self.outside_path or (staging_dir / "report.pdf")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = b"%PDF-1.7\nsource bytes"
        path.write_bytes(payload)
        return DownloadReceipt(
            candidate_id=candidate.candidate_id,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url,
            staged_path=str(path),
            content_sha256=hashlib.sha256(payload).hexdigest(),
            byte_size=len(payload),
            mime_type="application/pdf",
            retrieved_at="2026-07-18T12:00:00Z",
            http_status=200,
            adapter_name=self.name,
            adapter_version=self.version,
        )


def _catalog(tmp_path: Path, *, with_source: bool):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    companies.mkdir(parents=True)
    if with_source:
        report = (
            companies
            / "Acme"
            / "raw"
            / "financial_reports"
            / "annual"
            / "2026-02-20_Acme_2025_annual_report.txt"
        )
        report.parent.mkdir(parents=True)
        report.write_text("existing audited annual report", encoding="utf-8")
        sidecar = report.with_suffix(".txt.source.json")
        sidecar.write_text(
            '{"market": "CN", "security_id": "600519", "source_title": "Acme 2025 Annual Report", "source_url": "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=600519&announcementId=1"}',
            encoding="utf-8",
        )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
        )
    )
    catalog.scan()
    return catalog


def test_existing_source_short_circuits_discovery_and_fetch(tmp_path):
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionStatus,
        AdapterRegistry,
        SourceRequest,
    )

    catalog = _catalog(tmp_path, with_source=True)
    adapter = _ExplodingAdapter()
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
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
    assert result.resolution.download_required is False
    assert result.adapter_name is None
    assert adapter.discover_calls == 0
    assert adapter.fetch_calls == 0
    assert not (tmp_path / "staging").exists()


def test_missing_hk_source_routes_to_adapter_and_only_writes_request_staging(tmp_path):
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionStatus,
        AdapterRegistry,
        SourceRequest,
    )

    catalog = _catalog(tmp_path, with_source=False)
    adapter = _FakeAdapter()
    staging_root = tmp_path / "staging"
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=_ExplodingAdapter(), hk=adapter, us=_ExplodingAdapter()),
        staging_root=staging_root,
    )

    result = coordinator.resolve_or_stage(
        SourceRequest(
            entity="ACME",
            market="HK",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
            allow_download=True,
        )
    )

    assert result.status is AcquisitionStatus.STAGED
    assert result.adapter_name == "fake_hkex"
    assert adapter.discover_calls == 1
    assert adapter.fetch_calls == 1
    assert result.receipt is not None
    staged = Path(result.receipt.staged_path)
    assert staged.is_file()
    assert staged.is_relative_to(staging_root)
    assert len(staged.parent.name) == 64
    assert staged.parent.parent == staging_root
    assert not list(catalog.config.project_root.rglob("*.pdf"))


def test_bounded_adapter_consumes_one_budget_for_discovery_and_fetch(tmp_path):
    from decimal import Decimal
    import time

    from company_wiki.source_catalog import (
        AcquisitionBudget,
        AcquisitionCoordinator,
        AcquisitionStatus,
        AdapterRegistry,
        SourceRequest,
    )

    class _BudgetedFakeAdapter(_FakeAdapter):
        supports_acquisition_budget = True

        def discover_bounded(self, request, budget):
            budget.consume_response_bytes(8)
            return self.discover(request)

        def fetch_bounded(self, candidate, staging_dir, budget):
            payload = b"%PDF-1.7\nsource bytes"
            budget.consume_response_bytes(len(payload))
            return self.fetch(candidate, staging_dir)

    catalog = _catalog(tmp_path, with_source=False)
    adapter = _BudgetedFakeAdapter()
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=_ExplodingAdapter(), hk=adapter, us=_ExplodingAdapter()),
        staging_root=tmp_path / "staging",
    )
    budget = AcquisitionBudget(
        max_response_bytes=64,
        deadline_monotonic=time.monotonic() + 30,
        max_cost_usd=Decimal("0.00"),
    )

    result = coordinator.resolve_or_stage(
        SourceRequest(
            entity="ACME",
            market="HK",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
            allow_download=True,
        ),
        budget=budget,
    )

    assert result.status is AcquisitionStatus.STAGED
    assert budget.response_bytes_used == 8 + len(b"%PDF-1.7\nsource bytes")


def test_bounded_receipt_must_be_charged_against_remaining_budget(tmp_path):
    from decimal import Decimal
    import time

    from company_wiki.source_catalog import (
        AcquisitionBudget,
        AcquisitionCoordinator,
        AcquisitionError,
        AdapterRegistry,
        SourceRequest,
    )

    class _UnderreportingAdapter(_FakeAdapter):
        supports_acquisition_budget = True

        def discover_bounded(self, request, budget):
            budget.consume_response_bytes(20)
            return self.discover(request)

        def fetch_bounded(self, candidate, staging_dir, budget):
            # Simulate an adapter that produced a real staged file but forgot
            # to charge the response body it read from its provider.
            return self.fetch(candidate, staging_dir)

    catalog = _catalog(tmp_path, with_source=False)
    adapter = _UnderreportingAdapter()
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=_ExplodingAdapter(), hk=adapter, us=_ExplodingAdapter()),
        staging_root=tmp_path / "staging",
    )
    budget = AcquisitionBudget(
        max_response_bytes=30,
        deadline_monotonic=time.monotonic() + 30,
        max_cost_usd=Decimal("0.00"),
    )

    with pytest.raises(AcquisitionError, match="did not charge"):
        coordinator.resolve_or_stage(
            SourceRequest(
                entity="ACME",
                market="HK",
                document_kind="annual_report",
                fiscal_year=2025,
                as_of_date="2026-07-18",
                allow_download=True,
            ),
            budget=budget,
        )


def test_unbounded_json_command_adapter_is_rejected_before_process_launch(tmp_path):
    from decimal import Decimal
    import sys
    import time

    from company_wiki.source_catalog import (
        AcquisitionBudget,
        AcquisitionCoordinator,
        AcquisitionError,
        AdapterRegistry,
        JsonCommandAdapter,
        SourceRequest,
    )

    marker = tmp_path / "provider_process_started"
    command = (
        sys.executable,
        "-c",
        "from pathlib import Path; import sys; Path(sys.argv[1]).touch()",
        str(marker),
    )
    adapter = JsonCommandAdapter(
        name="unbounded-json-provider",
        version="1.0",
        command=command,
        project_root=tmp_path,
    )
    coordinator = AcquisitionCoordinator(
        catalog=_catalog(tmp_path, with_source=False),
        adapters=AdapterRegistry(
            cn=adapter, hk=_ExplodingAdapter(), us=_ExplodingAdapter()
        ),
        staging_root=tmp_path / "staging",
    )
    budget = AcquisitionBudget(
        max_response_bytes=1024,
        deadline_monotonic=time.monotonic() + 30,
        max_cost_usd=Decimal("0.00"),
    )

    with pytest.raises(AcquisitionError, match="bounded acquisition"):
        coordinator.resolve_or_stage(
            SourceRequest(
                entity="ACME",
                market="CN",
                document_kind="annual_report",
                fiscal_year=2025,
                as_of_date="2026-07-18",
                allow_download=True,
            ),
            budget=budget,
        )

    assert not marker.exists(), "unsupported CN adapter launched external work"


def test_adapter_receipt_outside_allocated_staging_fails_closed(tmp_path):
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AdapterRegistry,
        AcquisitionError,
        SourceRequest,
    )

    catalog = _catalog(tmp_path, with_source=False)
    outside = tmp_path / "outside" / "escaped.pdf"
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(
            cn=_ExplodingAdapter(),
            hk=_FakeAdapter(outside_path=outside),
            us=_ExplodingAdapter(),
        ),
        staging_root=tmp_path / "staging",
    )

    with pytest.raises(AcquisitionError, match="outside allocated staging"):
        coordinator.resolve_or_stage(
            SourceRequest(
                entity="ACME",
                market="HK",
                document_kind="annual_report",
                fiscal_year=2025,
                as_of_date="2026-07-18",
                allow_download=True,
            )
        )


def test_placeholder_with_missing_identity_metadata_can_reach_adapter(tmp_path):
    """A document with missing identity metadata (no assertion, no canonical
    file) resolves MISSING, so an authorized download reaches the adapter
    instead of being blocked as identity_conflict_no_download (Phase 15.3)."""
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionStatus,
        AdapterRegistry,
        CatalogConfig,
        ResolutionStatus,
        RootSpec,
        SourceCatalog,
        SourceRequest,
    )

    project = tmp_path / "project"
    portfolio = tmp_path / "dayu" / "portfolio"
    filing = portfolio / "Zijin" / "filings" / "fil_2025"
    filing.mkdir(parents=True)
    (filing / "meta.json").write_text(
        json.dumps(
            {
                "ticker": "Zijin",
                "document_id": "fil_2025",
                "document_kind": "annual_report",
                "source_title": "Zijin 2025 Annual Report",
                "filing_date": "2026-03-20",
                "fiscal_year": 2025,
                "ingest_complete": False,
                "files": [],
            }
        ),
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),),
        )
    )
    catalog.scan()
    adapter = _FakeAdapter()
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
        staging_root=tmp_path / "staging",
    )

    result = coordinator.resolve_or_stage(
        SourceRequest(
            entity="Zijin",
            market="HK",
            security_id="02899",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-31",
            allow_download=True,
        )
    )

    assert result.resolution.status is ResolutionStatus.MISSING
    assert result.status is AcquisitionStatus.STAGED
    assert adapter.discover_calls == 1
    assert adapter.fetch_calls == 1


def test_market_router_is_explicit_and_rejects_unknown_market():
    from company_wiki.source_catalog import AdapterRegistry, MarketRoutingError

    cn = _ExplodingAdapter()
    hk = _FakeAdapter()
    us = _ExplodingAdapter()
    registry = AdapterRegistry(cn=cn, hk=hk, us=us)

    assert registry.for_market("CN") is cn
    assert registry.for_market("HK") is hk
    assert registry.for_market("US") is us
    with pytest.raises(MarketRoutingError, match="unsupported market"):
        registry.for_market("GB")


def test_e2e_f01_html_disguised_as_pdf_is_quarantined(tmp_path):
    """E2E-F01: an adapter returning HTML bytes claimed as a PDF must be
    rejected (no PDF magic) — never a capture-ready handle."""
    import hashlib

    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionError,
        AcquisitionStatus,
        AdapterRegistry,
        DownloadCandidate,
        DownloadReceipt,
        SourceRequest,
    )

    class _HtmlAdapter:
        name = "fake_html"
        version = "1.0.0"

        def discover(self, request):
            return (
                DownloadCandidate(
                    candidate_id="c-1", provider="sec",
                    provider_document_id="acc-1", market="US",
                    entity=request.entity, title="ACME annual",
                    source_url="https://www.sec.gov/x.pdf",
                    document_kind="annual_report", filing_date="2026-04-15",
                    fiscal_year=2025,
                ),
            )

        def fetch(self, candidate, staging_dir):
            path = staging_dir / "x.pdf"
            payload = b"<html><body>not a pdf</body></html>"
            path.write_bytes(payload)
            return DownloadReceipt(
                candidate_id=candidate.candidate_id,
                provider=candidate.provider,
                provider_document_id=candidate.provider_document_id,
                source_url=candidate.source_url,
                staged_path=str(path),
                content_sha256=hashlib.sha256(payload).hexdigest(),
                byte_size=len(payload),
                mime_type="application/pdf",  # claims PDF but bytes are HTML
                retrieved_at="2026-08-08T12:00:00Z",
                http_status=200,
                adapter_name=self.name,
                adapter_version=self.version,
            )

    catalog = _catalog(tmp_path, with_source=False)
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=_HtmlAdapter(), hk=_HtmlAdapter(), us=_HtmlAdapter()),
        staging_root=tmp_path / "staging",
    )
    request = SourceRequest(
        entity="ACME", market="US", security_id="ACME",
        document_kind="annual_report", as_of_date="2026-07-31",
        allow_download=True,
    )
    try:
        result = coordinator.resolve_or_stage(request)
    except AcquisitionError as exc:
        assert "PDF magic" in str(exc), exc
    else:
        assert result.status is not AcquisitionStatus.STAGED, result


def test_e2e_f02_same_accession_second_request_reuses(tmp_path):
    """E2E-F02: two sequential ensure() calls for the same accession — the
    first downloads once (IMPORTED), the second reuses the catalog entry
    (fetch=0). Sequential dedup under the single-threaded architecture."""
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionJournal,
        AdapterRegistry,
        CanonicalSourceWriter,
        SourceAcquisitionService,
        SourceRequest,
    )

    catalog = _catalog(tmp_path, with_source=False)
    adapter = _FakeAdapter()
    staging_root = tmp_path / "staging"
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=_ExplodingAdapter(), hk=adapter, us=_ExplodingAdapter()),
        staging_root=staging_root,
    )
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    service = SourceAcquisitionService(
        coordinator=coordinator,
        journal=AcquisitionJournal(journal_dir),
        writer=CanonicalSourceWriter(catalog, staging_root=staging_root),
    )
    request = SourceRequest(
        entity="ACME", market="HK", document_kind="annual_report",
        fiscal_year=2025, as_of_date="2026-07-18", allow_download=True,
    )
    first = service.ensure(request)
    assert first.status.value in {"imported", "deduplicated"}, first
    assert adapter.fetch_calls == 1
    # second ensure: same accession — the canonical file is now reusable
    second = service.ensure(request)
    assert second.status.value in {"reused", "deduplicated", "imported"}, second
    assert adapter.fetch_calls == 1, "second request must not fetch again"


def test_source_acquisition_service_passes_budget_to_provider(tmp_path):
    from decimal import Decimal
    import time

    from company_wiki.source_catalog import (
        AcquisitionBudget,
        AcquisitionCoordinator,
        AcquisitionJournal,
        AdapterRegistry,
        CanonicalSourceWriter,
        SourceAcquisitionService,
        SourceRequest,
    )

    class _BudgetedFakeAdapter(_FakeAdapter):
        supports_acquisition_budget = True

        def discover_bounded(self, request, budget):
            budget.consume_response_bytes(8)
            return self.discover(request)

        def fetch_bounded(self, candidate, staging_dir, budget):
            payload = b"%PDF-1.7\nsource bytes"
            budget.consume_response_bytes(len(payload))
            return self.fetch(candidate, staging_dir)

    catalog = _catalog(tmp_path, with_source=False)
    adapter = _BudgetedFakeAdapter()
    staging_root = tmp_path / "staging"
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    service = SourceAcquisitionService(
        coordinator=AcquisitionCoordinator(
            catalog=catalog,
            adapters=AdapterRegistry(
                cn=_ExplodingAdapter(), hk=adapter, us=_ExplodingAdapter()
            ),
            staging_root=staging_root,
        ),
        journal=AcquisitionJournal(journal_dir),
        writer=CanonicalSourceWriter(catalog, staging_root=staging_root),
    )
    budget = AcquisitionBudget(
        max_response_bytes=64,
        deadline_monotonic=time.monotonic() + 30,
        max_cost_usd=Decimal("0.00"),
    )

    result = service.ensure(
        SourceRequest(
            entity="ACME",
            market="HK",
            document_kind="annual_report",
            fiscal_year=2025,
            as_of_date="2026-07-18",
            allow_download=True,
        ),
        budget=budget,
    )

    assert result.status.value == "imported"
    assert budget.response_bytes_used == 8 + len(b"%PDF-1.7\nsource bytes")
