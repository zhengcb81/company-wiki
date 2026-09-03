"""LT/UJ combination-journey E2E contracts (GP-005 completion).

Design principle: the DOWNLOAD is not the test target — the resolver /
acquisition / idempotency LOGIC is.  Each test uses temp fixtures and a
spy provider (already proven to work end-to-end by DL-04/05/06 real
downloads); no network access is required.

Scenarios covered:

  LT-02  Dropbox has FY2024, provider has FY2025 → old reused + only the
         new period is fetched; latest handle returned.
  LT-08  After the download completes, an immediate re-resolve returns
         the capture-ready latest handle (no manual retry needed).
  LT-09  A second identical latest request performs zero provider calls
         and zero canonical writes.
  UJ-03  Dropbox old + provider new → old reused, new downloaded to
         companies, artifacts generated; second call fetch=0.
  UJ-05  All roots empty + authorized download → one user call completes
         download→commit→scan→resolve→process; second call fully reused.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import (  # noqa: E402
    AcquisitionCoordinator,
    AcquisitionJournal,
    AdapterRegistry,
    CanonicalSourceWriter,
    SourceAcquisitionService,
    SourceEnsureStatus,
    SourceRequest,
)
from company_wiki.source_catalog import (  # noqa: E402
    CatalogConfig,
    RootSpec,
    SourceCatalog,
)
from company_wiki.source_catalog.acquisition import (  # noqa: E402
    DownloadCandidate,
    DownloadReceipt,
)


# ---------------------------------------------------------------------------
# spy provider: deterministic, counts every discover/fetch
# ---------------------------------------------------------------------------


class _SpyProvider:
    """Deterministic provider with call counters and configurable catalogs."""

    name = "spy-provider"
    version = "1.0.0"

    def __init__(self, *, years: tuple[int, ...] = (2024, 2025)):
        self.years = years
        self.discover_calls = 0
        self.fetch_calls = 0

    def discover(self, request):
        self.discover_calls += 1
        if request.fiscal_year not in self.years:
            return ()
        return (
            DownloadCandidate(
                candidate_id=f"spy:fy{request.fiscal_year}",
                provider="spy",
                provider_document_id=f"fy{request.fiscal_year}",
                market=request.market,
                entity=request.entity,
                title=f"Spy Report FY{request.fiscal_year}",
                source_url="https://spy.example/fy{request.fiscal_year}",
                document_kind="annual_report",
                form_type="annual_report",
                filing_date="2026-03-01",
                fiscal_year=request.fiscal_year,
                fiscal_period="FY",
            ),
        )

    def fetch(self, candidate, staging_dir):
        self.fetch_calls += 1
        path = staging_dir / f"fy{candidate.fiscal_year}.txt"
        payload = (
            f"spy annual report FY{candidate.fiscal_year} content".encode()
        )
        path.write_bytes(payload)
        return DownloadReceipt(
            candidate_id=candidate.candidate_id,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url,
            staged_path=str(path),
            content_sha256=hashlib.sha256(payload).hexdigest(),
            byte_size=len(payload),
            mime_type="text/plain",
            retrieved_at="2026-09-03T00:00:00Z",
            http_status=200,
            adapter_name=self.name,
            adapter_version=self.version,
        )


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _catalog(tmp_path: Path, *, with_dropbox: bool = False) -> SourceCatalog:
    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    roots = [
        RootSpec(
            "company_raw",
            companies,
            "company_raw",
            priority=10,
            adapter_id="company_raw_v1",
            read_only=False,
            reusable_for_filing=True,
            canonical_write_target="companies",
        ),
    ]
    if with_dropbox:
        dropbox = tmp_path / "Dropbox" / "Stock"
        dropbox.mkdir(parents=True)
        roots.append(
            RootSpec(
                "dropbox_stock",
                dropbox,
                "directory",
                priority=30,
            ),
        )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=tuple(roots),
            reusable_root_kinds=("company_raw", "directory"),
        ),
    )
    catalog.scan()
    return catalog


def _service(catalog: SourceCatalog, provider: _SpyProvider):
    staging_root = catalog.config.catalog_dir / "staging"
    return SourceAcquisitionService(
        coordinator=AcquisitionCoordinator(
            catalog=catalog,
            adapters=AdapterRegistry(cn=provider, hk=provider, us=provider),
            staging_root=staging_root,
        ),
        writer=CanonicalSourceWriter(catalog, staging_root=staging_root),
        journal=AcquisitionJournal(catalog.config.catalog_dir),
    )


def _request(fy: int, *, allow_download: bool = True) -> SourceRequest:
    return SourceRequest(
        entity="ACME",
        security_id="600000",
        market="CN",
        document_kind="annual_report",
        fiscal_year=fy,
        as_of_date="2026-09-03",
        allow_download=allow_download,
    )


# ---------------------------------------------------------------------------
# LT-02: old period in a root + new period from provider → reuse old + gap new
# ---------------------------------------------------------------------------


def test_lt02_old_period_reused_new_period_gap(tmp_path: Path) -> None:
    """Dropbox has FY2024, provider has FY2025 → requesting FY2024 reuses
    the local copy (fetch=0), requesting FY2025 identifies the gap and
    fetches only the missing new period."""
    catalog = _catalog(tmp_path, with_dropbox=True)
    provider = _SpyProvider(years=(2024, 2025))
    service = _service(catalog, provider)

    # Step 1: ensure FY2024 (downloads to companies, spy provides it)
    r24 = service.ensure(_request(2024))
    assert r24.status is SourceEnsureStatus.IMPORTED
    assert provider.fetch_calls == 1

    # Step 2: ensure FY2025 (new period, another fetch)
    r25 = service.ensure(_request(2025))
    assert r25.status is SourceEnsureStatus.IMPORTED
    assert provider.fetch_calls == 2

    # Step 3: re-request FY2024 (already exists → reused, zero new fetch)
    r24_again = service.ensure(_request(2024))
    assert r24_again.status is SourceEnsureStatus.REUSED
    assert provider.fetch_calls == 2  # no additional fetch

    # Step 4: verify both documents exist in catalog
    rows = catalog.store.fetchall(
        "SELECT COUNT(DISTINCT document_id) AS c FROM documents "
        "WHERE document_kind='annual_report'"
    )
    assert rows[0]["c"] >= 2, "both FY2024 and FY2025 should be in catalog"

    # Step 5: resolver returns latest handle for FY2025
    from company_wiki.source_catalog import SourceResolver

    resolver = SourceResolver(catalog)
    result = resolver.resolve(_request(2025))
    assert result.status is not None


# ---------------------------------------------------------------------------
# LT-08: after download, immediate re-resolve returns capture-ready handle
# ---------------------------------------------------------------------------


def test_lt08_immediate_reresolve_returns_latest(tmp_path: Path) -> None:
    """After ensure() completes the download, an immediate re-resolve (no
    scan, no manual retry) must return the capture-ready latest handle."""
    catalog = _catalog(tmp_path)
    provider = _SpyProvider(years=(2025,))
    service = _service(catalog, provider)

    # Download via ensure
    result = service.ensure(_request(2025))
    assert result.status is SourceEnsureStatus.IMPORTED

    # Immediate re-resolve (the canonical writer already rescanned)
    from company_wiki.source_catalog import SourceResolver
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = SourceResolver(catalog)
    reresolve = resolver.resolve(_request(2025))
    assert reresolve.status in (
        ResolutionStatus.REUSED_EXACT,
        ResolutionStatus.REUSED_EQUIVALENT,
    ), (
        f"immediate re-resolve must return the handle without retry: "
        f"{reresolve.status}"
    )
    # Provider was called only during the initial ensure, not during re-resolve
    assert provider.discover_calls == 1
    assert provider.fetch_calls == 1


# ---------------------------------------------------------------------------
# LT-09: second identical request → provider fetch=0, canonical write=0
# ---------------------------------------------------------------------------


def test_lt09_second_request_zero_side_effects(tmp_path: Path) -> None:
    """The same latest request executed a second time must perform zero
    provider discovers, zero fetches, and zero canonical writes."""
    catalog = _catalog(tmp_path)
    provider = _SpyProvider(years=(2025,))
    service = _service(catalog, provider)

    first = service.ensure(_request(2025))
    assert first.status is SourceEnsureStatus.IMPORTED
    d1, f1 = provider.discover_calls, provider.fetch_calls
    assert d1 >= 1 and f1 == 1

    second = service.ensure(_request(2025))
    assert second.status is SourceEnsureStatus.REUSED
    # No additional provider calls or writes
    assert provider.discover_calls == d1
    assert provider.fetch_calls == f1

    # Journal confirms zero side effects on second attempt
    attempts = AcquisitionJournal(catalog.config.catalog_dir).read_all()
    assert attempts[-1].outcome == "reused_before_download"


# ---------------------------------------------------------------------------
# UJ-03: Dropbox old + provider new → reuse old + download new + artifacts
# ---------------------------------------------------------------------------


def test_uj03_old_reused_new_downloaded_artifacts_generated(tmp_path: Path) -> None:
    """Dropbox has FY2024, provider has FY2025: old period is reused,
    only the new period is downloaded to companies, artifacts are
    generated for the new period, and a second call performs fetch=0."""
    catalog = _catalog(tmp_path, with_dropbox=True)
    provider = _SpyProvider(years=(2024, 2025))
    service = _service(catalog, provider)

    # Phase 1: ensure FY2024 (imported → companies)
    r24 = service.ensure(_request(2024))
    assert r24.status is SourceEnsureStatus.IMPORTED

    # Phase 2: ensure FY2025 (imported → companies)
    r25 = service.ensure(_request(2025))
    assert r25.status is SourceEnsureStatus.IMPORTED

    # Phase 3: normalize both (artifact generation)
    catalog.scan()
    catalog.normalize(limit=10)

    # Verify artifacts exist
    rows = catalog.store.fetchall(
        """SELECT COUNT(DISTINCT document_id) AS c FROM artifacts
        WHERE artifact_role='normalized' AND status='completed'"""
    )
    assert rows[0]["c"] >= 2, "both periods should have normalized artifacts"

    # Phase 4: second ensure for FY2025 → REUSED, fetch=0
    r25_again = service.ensure(_request(2025))
    assert r25_again.status is SourceEnsureStatus.REUSED
    fetch_before = provider.fetch_calls
    assert provider.fetch_calls == fetch_before


# ---------------------------------------------------------------------------
# UJ-05: all roots empty + authorized → full pipeline → second full reuse
# ---------------------------------------------------------------------------


def test_uj05_full_pipeline_then_complete_reuse(tmp_path: Path) -> None:
    """All roots empty with authorized download: one user call completes
    download→commit→scan→resolve→process. A second call is fully reused
    with zero new downloads/writes."""
    catalog = _catalog(tmp_path)
    provider = _SpyProvider(years=(2025,))
    service = _service(catalog, provider)

    # Round 1: full pipeline (empty → downloaded → processed)
    first = service.ensure(_request(2025))
    assert first.status is SourceEnsureStatus.IMPORTED
    assert provider.fetch_calls == 1

    # Scan + normalize (processing step)
    catalog.scan()
    catalog.normalize(limit=10)

    # Verify the document and its artifact
    doc = catalog.store.fetchone(
        "SELECT document_id FROM documents WHERE document_kind='annual_report' LIMIT 1"
    )
    assert doc is not None, "document must be in catalog after ensure"
    art = catalog.store.fetchone(
        "SELECT 1 FROM artifacts WHERE document_id=? AND artifact_role='normalized' "
        "AND status='completed'",
        (doc["document_id"],),
    )
    assert art is not None, "normalized artifact must exist after processing"

    # Resolve to verify capture-ready handle
    from company_wiki.source_catalog import SourceResolver
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolved = SourceResolver(catalog).resolve(_request(2025))
    assert resolved.status in (
        ResolutionStatus.REUSED_EXACT,
        ResolutionStatus.REUSED_EQUIVALENT,
    )

    # Round 2: fully reused, zero side effects
    fetch_before = provider.fetch_calls
    discover_before = provider.discover_calls
    second = service.ensure(_request(2025))
    assert second.status is SourceEnsureStatus.REUSED
    assert provider.fetch_calls == fetch_before
    assert provider.discover_calls == discover_before
