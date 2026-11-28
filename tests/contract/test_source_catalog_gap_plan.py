"""WU-4.2: metadata-only discovery alignment and GapPlan (RED first).

The GapPlan builder is a pure function: given the local reusable candidates
(already resolved handles) and the remote provider metadata (discovered
DownloadCandidates, NEVER downloaded), it produces the gap plan:

- reuse: local candidate that is already the latest for its period;
- missing: periods the provider has published (by as_of) that local lacks;
- newer_revision: same period, provider accession newer than local;
- not_published: provider has nothing newer than the latest local;
- provider_unavailable: discovery failed/rate-limited → incomplete, keep
  local, never claim up-to-date;
- future: provider metadata published after as_of is excluded.

RED phase: the module does not exist (ImportError → RED).
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.source_catalog import (
    AcquisitionCoordinator, AcquisitionJournal, AcquisitionStatus, AdapterRegistry,
    CanonicalSourceWriter, CatalogConfig, DownloadCandidate, DownloadReceipt, RootSpec,
    SourceAcquisitionService, SourceCatalog, SourceEnsureStatus, SourceRequest,
)
from company_wiki.source_catalog.download_budget import AcquisitionBudget
from company_wiki.source_catalog.gap_plan import build_gap_plan


class _Local:
    """Minimal stand-in for a resolved SourceHandle (fiscal_year/published)."""

    def __init__(self, fiscal_year: int, published_date: str, accession: str = ""):
        self.fiscal_year = fiscal_year
        self.published_date = published_date
        self.provider_document_id = accession or f"acc-{fiscal_year}"

    def to_dict(self):
        return {
            "fiscal_year": self.fiscal_year,
            "published_date": self.published_date,
            "provider_document_id": self.provider_document_id,
        }


class _Remote:
    """Minimal stand-in for a DownloadCandidate (metadata only)."""

    def __init__(
        self,
        fiscal_year: int,
        filing_date: str,
        accession: str,
        amended: bool = False,
    ):
        self.fiscal_year = fiscal_year
        self.filing_date = filing_date
        self.provider_document_id = accession
        self.amended = amended

    def to_dict(self):
        return {
            "fiscal_year": self.fiscal_year,
            "filing_date": self.filing_date,
            "provider_document_id": self.provider_document_id,
            "amended": self.amended,
        }


def _plan(local, remote, provider_error=None):
    return build_gap_plan(
        request_id="req-1",
        as_of_date="2026-07-31",
        document_kind="annual_report",
        entity="ACME",
        market="US",
        local_handles=local,
        remote_candidates=remote,
        provider_error=provider_error,
    )


def test_local_old_gap_new_period(tmp_path):
    """Local has 2024; provider published 2025 (by as_of): gap = 2025 only."""
    plan = _plan(
        [_Local(2024, "2025-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    assert plan.not_published is False
    assert [c.fiscal_year for c in plan.reuse] == [2024]
    assert [c.fiscal_year for c in plan.missing] == [2025]
    assert plan.newer_revision == ()


def test_local_up_to_date_zero_gap(tmp_path):
    """Local has the latest the provider knows: download=0, reuse kept."""
    plan = _plan(
        [_Local(2025, "2026-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    assert plan.not_published is True
    assert plan.missing == ()
    assert plan.newer_revision == ()
    assert [c.fiscal_year for c in plan.reuse] == [2025]


def test_new_period_not_yet_published(tmp_path):
    """Provider has nothing beyond local latest: gap=0, not_published."""
    plan = _plan(
        [_Local(2025, "2026-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    assert plan.not_published is True
    assert plan.missing == ()


def test_older_revision_listed_not_downloaded(tmp_path):
    """Same period, provider accession newer than local: only the newer
    revision is listed as a gap; old revision stays in provenance."""
    plan = _plan(
        [_Local(2025, "2026-04-15", accession="acc-old")],
        [_Remote(2025, "2026-04-15", "acc-new")],
    )
    assert [c.provider_document_id for c in plan.newer_revision] == ["acc-new"]
    assert plan.missing == ()


def test_provider_unavailable_keeps_local_and_incomplete(tmp_path):
    """Provider offline/rate-limited: keep local, return incomplete, never
    claim up-to-date."""
    plan = _plan(
        [_Local(2024, "2025-04-15")],
        [],
        provider_error="rate_limit_exceeded",
    )
    assert plan.provider_unavailable is True
    assert plan.provider_reason == "rate_limit_exceeded"
    assert plan.not_published is False  # must not claim up-to-date
    assert [c.fiscal_year for c in plan.reuse] == [2024]


def test_remote_after_as_of_excluded(tmp_path):
    """Provider metadata published after as_of is excluded from the gap."""
    plan = _plan(
        [_Local(2024, "2025-04-15")],
        [_Remote(2025, "2026-08-15", "acc-2025")],  # after as_of 2026-07-31
    )
    assert [c.fiscal_year for c in plan.future] == [2025]
    assert plan.missing == ()
    assert plan.not_published is True  # nothing eligible to download


def test_gap_hash_deterministic(tmp_path):
    plan1 = _plan(
        [_Local(2024, "2025-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    plan2 = _plan(
        [_Local(2024, "2025-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    assert plan1.gap_hash == plan2.gap_hash
    assert len(plan1.gap_hash) == 64


def test_gap_hash_order_independent_same_period_multi_accession(tmp_path):
    """Reviewer finding: two local handles sharing a period with different
    accessions must hash identically regardless of input order."""
    a = _Local(2025, "2026-04-15", accession="acc-old")
    b = _Local(2025, "2026-04-15", accession="acc-new")
    remote = [_Remote(2025, "2026-04-15", "acc-new")]
    p1 = _plan([a, b], remote)
    p2 = _plan([b, a], remote)
    assert p1.gap_hash == p2.gap_hash


class _GapProvider:
    name = "gap-test"
    version = "1.0.0"
    supports_acquisition_budget = True

    def __init__(self, fiscal_year=2025):
        self.year = fiscal_year
        self.discover_calls = 0
        self.fetch_calls = 0

    def discover(self, request):
        self.discover_calls += 1
        return (
            DownloadCandidate(
                candidate_id=f"c-{self.year}", provider="sec",
                provider_document_id=f"acc-{self.year}", market="US", entity="ACME",
                security_id="ACME", title=f"ACME {self.year} Annual Report",
                source_url=f"https://www.sec.gov/x/{self.year}.pdf",
                document_kind="annual_report", form_type="annual_report",
                filing_date=f"{self.year + 1}-04-15", fiscal_year=self.year,
            ),
        )

    def discover_bounded(self, request, budget):
        budget.consume_response_bytes(1)
        return self.discover(request)

    def fetch_bounded(self, candidate, staging_dir, budget):
        budget.consume_response_bytes(len(f"%PDF-{self.year}"))
        return self.fetch(candidate, staging_dir)

    def fetch(self, candidate, staging_dir):
        self.fetch_calls += 1
        body = f"%PDF-{self.year}".encode("ascii")
        path = staging_dir / "annual.pdf"
        path.write_bytes(body)
        return DownloadReceipt(
            candidate_id=candidate.candidate_id, provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url, staged_path=str(path),
            content_sha256=hashlib.sha256(body).hexdigest(), byte_size=len(body),
            mime_type="application/pdf", retrieved_at="2026-07-30T10:00:00Z",
            http_status=200, adapter_name=self.name, adapter_version=self.version,
        )


@pytest.fixture
def acquisition_gap(tmp_path):
    companies = tmp_path / "companies"
    companies.mkdir()
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
        roots=(RootSpec(
            "company_raw", companies, "company_raw", priority=10, adapter_id="company_raw_v1",
            reusable_for_filing=True, canonical_write_target="companies",
        ),),
        reusable_root_kinds=("company_raw",),
    ))
    provider = _GapProvider()
    coordinator = AcquisitionCoordinator(
        catalog=catalog, adapters=AdapterRegistry(cn=_GapProvider(), hk=_GapProvider(), us=provider),
        staging_root=tmp_path / "staging",
    )
    request = SourceRequest(
        entity="ACME", market="US", security_id="ACME", mode="latest_as_of",
        document_kind="annual_report", as_of_date="2026-07-31",
    )
    try:
        catalog.scan()
        seed_provider = _GapProvider(2024)
        staging = tmp_path / "seed-staging"
        seed = SourceAcquisitionService(
            coordinator=AcquisitionCoordinator(
                catalog=catalog, adapters=AdapterRegistry(
                    cn=_GapProvider(), hk=_GapProvider(), us=seed_provider,
                ), staging_root=staging,
            ),
            writer=CanonicalSourceWriter(catalog, staging_root=staging),
            journal=AcquisitionJournal(tmp_path / "seed-journal"),
        )
        seeded = seed.ensure(
            replace(request, mode="exact", fiscal_year=2024, allow_download=True),
            budget=AcquisitionBudget.from_limits(
                max_response_bytes=4096, max_seconds=30, max_cost_usd="0",
            ),
        )
        assert seeded.status is SourceEnsureStatus.IMPORTED
        path = Path(seeded.canonical_import.canonical_path)
        yield catalog, coordinator, provider, request
        assert path.read_bytes() == b"%PDF-2024"
    finally:
        catalog.close()


def test_latest_as_of_download_intent_stages_discovered_gap(tmp_path, acquisition_gap):
    _, coordinator, provider, request = acquisition_gap
    result = coordinator.resolve_or_stage(replace(request, allow_download=True))

    assert result.status is AcquisitionStatus.STAGED, result
    assert result.gap_plan is not None
    assert [item.fiscal_year for item in result.gap_plan.reuse] == [2024]
    assert [item.fiscal_year for item in result.gap_plan.missing] == [2025]
    assert (provider.discover_calls, provider.fetch_calls) == (1, 1)
    path = Path(result.receipt.staged_path)
    assert path.is_relative_to(tmp_path / "staging")
    assert path.read_bytes() == b"%PDF-2025"


def test_coordinator_latest_as_of_returns_gap_without_fetch(tmp_path, acquisition_gap):
    _, coordinator, provider, request = acquisition_gap
    result = coordinator.resolve_or_stage(request)

    assert result.status is AcquisitionStatus.GAP, result
    assert result.gap_plan is not None
    assert [item.fiscal_year for item in result.gap_plan.reuse] == [2024]
    assert [item.fiscal_year for item in result.gap_plan.missing] == [2025]
    assert (provider.discover_calls, provider.fetch_calls) == (1, 0)
    assert not (tmp_path / "staging").exists()


def test_service_ensure_latest_as_of_returns_gap(tmp_path, acquisition_gap):
    catalog, coordinator, provider, request = acquisition_gap
    journal = AcquisitionJournal(catalog.config.catalog_dir)
    service = SourceAcquisitionService(
        coordinator=coordinator, journal=journal,
        writer=CanonicalSourceWriter(catalog, staging_root=tmp_path / "staging"),
    )
    result = service.ensure(request)

    assert result.status is SourceEnsureStatus.GAP, result
    assert result.acquisition.gap_plan is not None
    assert [item.fiscal_year for item in result.acquisition.gap_plan.missing] == [2025]
    assert (provider.discover_calls, provider.fetch_calls) == (1, 0)
    records = [json.loads(line) for line in journal.path.read_text(encoding="utf-8").splitlines()]
    assert any(record.get("outcome") == "gap_plan" for record in records), records


def test_unknown_remote_date_is_inventory_not_historical_gap_or_proof_of_latest():
    unknown = _Remote(2026, None, "unknown")
    plan = _plan([_Local(2025, "2026-04-15")], [unknown])
    assert plan.missing == plan.newer_revision == plan.future == ()
    assert not plan.not_published
    assert plan.publication_unknown == (unknown,)
    assert plan.to_dict()["publication_unknown"][0]["filing_date"] is None
    assert plan.gap_hash != _plan([_Local(2025, "2026-04-15")], []).gap_hash


def test_known_unknown_invalid_future_remote_dates_are_classified_once():
    known = _Remote(2025, "2026-04-15", "acc-2025")
    unknown = _Remote(2026, None, "unknown")
    invalid = _Remote(2026, "2026-02-30", "invalid")
    future = _Remote(2026, "2026-12-01", "future")
    plan = _plan([_Local(2025, "2026-04-15")], [known, unknown, invalid, future])
    assert plan.missing == plan.newer_revision == ()
    assert plan.future == (future,)
    assert plan.publication_unknown == (unknown, invalid)
    assert not plan.not_published
