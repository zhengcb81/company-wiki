"""FF-1 B2: the ensure flow self-heals undated groups once, declaration-driven.

An isolated catalog instance (no network, no downloads) with an undated
document whose group sidecar LATER declared a filing date: one ensure call
repairs it through the directed registration and reuses the source.  An
undeclaring sidecar fails immediately with the named reason — no repair, no
retry, no spin.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import (  # noqa: E402
    AcquisitionCoordinator,
    AdapterRegistry,
    CatalogConfig,
    RootSpec,
    SourceCatalog,
)
from company_wiki.source_catalog.acquisition_service import (  # noqa: E402
    SourceAcquisitionService,
    SourceEnsureStatus,
)
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter  # noqa: E402
from company_wiki.source_catalog.download_budget import AcquisitionBudget  # noqa: E402
from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal  # noqa: E402
from contract.test_source_version_reader import _sidecar  # noqa: E402

BODY = b"%PDF-1.4 ff1 ensure catalog repair fixture"
SHA = hashlib.sha256(BODY).hexdigest()


class _MustNotFetchAdapter:
    """Any discovery or fetch attempt is a test failure."""

    name = "must_not_fetch"
    version = "1.0.0"

    def discover(self, request):
        raise AssertionError("repair must turn the retry into a reuse, not a discovery")

    def fetch(self, candidate, staging_dir):
        raise AssertionError("repair must turn the retry into a reuse, not a download")


def _write_undated_annual(root: Path) -> Path:
    """Stage the annual original with an UNDECLARING sidecar (no filing date)."""
    directory = root / "Acme" / "raw" / "financial_reports" / "annual"
    directory.mkdir(parents=True, exist_ok=True)
    document = directory / "2025.pdf"
    document.write_bytes(BODY)
    _persist_sidecar(document, None)
    return document


def _persist_sidecar(document: Path, filing_date: str | None) -> None:
    payload = _sidecar(sha=SHA, provider_id="doc-1", fiscal_year=2025,
                       filing_date=filing_date or "")
    if not filing_date:
        payload["filing_date"] = None
    (document.with_name(document.name + ".source.json")).write_text(
        json.dumps(payload), encoding="utf-8",
    )


def _service(tmp_path: Path, catalog: SourceCatalog) -> tuple[SourceAcquisitionService, list]:
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=_MustNotFetchAdapter(), hk=_MustNotFetchAdapter(), us=_MustNotFetchAdapter()),
        staging_root=tmp_path / "staging",
    )
    calls: list = []
    original = coordinator.select_for_ensure

    def counting_select(request, **kwargs):
        calls.append(request.request_id)
        return original(request, **kwargs)

    coordinator.select_for_ensure = counting_select  # type: ignore[method-assign]
    service = SourceAcquisitionService(
        coordinator=coordinator,
        writer=CanonicalSourceWriter(catalog, staging_root=tmp_path / "staging"),
        journal=AcquisitionJournal(catalog.config.catalog_dir),
    )
    return service, calls


def _request(**overrides):
    from company_wiki.source_catalog.resolver import SourceRequest

    values = dict(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", fiscal_year=2025,
        as_of_date="2026-10-08", allow_download=True,
    )
    values.update(overrides)
    return SourceRequest(**values)


def _catalog(tmp_path: Path) -> SourceCatalog:
    companies = tmp_path / "companies"
    companies.mkdir(parents=True, exist_ok=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10,
                         adapter_id="company_raw_v1", read_only=False,
                         reusable_for_filing=True, canonical_write_target="companies"),
            ),
        )
    )
    return catalog


def _budget() -> AcquisitionBudget:
    return AcquisitionBudget.from_limits(
        max_response_bytes=1_000_000, max_seconds=60, max_cost_usd="0",
    )


def test_ensure_repairs_declared_group_once_and_reuses(tmp_path):
    catalog = _catalog(tmp_path)
    document = _write_undated_annual(tmp_path / "companies")
    try:
        catalog.scan()
        stored = catalog.reader.exact_source_version(
            "urn:company-wiki:document:sha256:" + SHA
        )
        assert stored is not None and stored["published_date"] is None
        # The declaration arrives AFTER the undated row was stored.
        _persist_sidecar(document, "2026-02-20")

        service, calls = _service(tmp_path, catalog)
        result = service.ensure(_request(), budget=_budget())

        assert result.status is SourceEnsureStatus.REUSED
        assert result.resolution.status.value == "reused_equivalent"
        # Exactly one retry after the repair.
        assert len(calls) == 2
        repaired = catalog.reader.exact_source_version(
            "urn:company-wiki:document:sha256:" + SHA
        )
        assert repaired["published_date"] == "2026-02-20"
        events = json.loads(
            (tmp_path / ".source_catalog" / "catalog_repairs.jsonl").read_text("utf-8").splitlines()[0]
        )
        assert events["event"] == "catalog_repair_applied"
        assert events["data_source"] == "group_sidecar_declaration"
        assert events["resolution_reason"] == "unique_match_published_date_unknown"
        assert events["registered"] == [{
            "root_id": "company_raw",
            "relative_path": document.relative_to(tmp_path / "companies").as_posix(),
            "sidecar_kind": "acquisition_sidecar",
            "filing_date": "2026-02-20",
        }]
    finally:
        catalog.close()


def test_ensure_without_declaration_fails_named_without_retry(tmp_path):
    catalog = _catalog(tmp_path)
    _write_undated_annual(tmp_path / "companies")
    try:
        catalog.scan()
        service, calls = _service(tmp_path, catalog)
        result = service.ensure(_request(), budget=_budget())

        assert result.status is SourceEnsureStatus.AMBIGUOUS
        assert result.resolution.reason == "unique_match_published_date_unknown"
        # No declared sidecar: no repair, no retry, no journal event.
        assert len(calls) == 1
        assert not (tmp_path / ".source_catalog" / "catalog_repairs.jsonl").exists()
    finally:
        catalog.close()


def test_declared_dayu_group_repairs_through_meta_json(tmp_path):
    portfolio = tmp_path / "portfolio"
    group_dir = portfolio / "HK00700" / "filings" / "fil_ff1-0001"
    group_dir.mkdir(parents=True)
    (group_dir / "hk-2025.htm").write_bytes(BODY)
    meta = group_dir / "meta.json"

    def persist_meta(filing_date: str | None) -> None:
        payload = {
            "form_type": "annual report",
            "market": "HK",
            "security_id": "00700",
            "ticker": "00700",
            "ingest_complete": True,
        }
        if filing_date:
            payload["filing_date"] = filing_date
        meta.write_text(json.dumps(payload), encoding="utf-8")

    persist_meta(None)
    companies = tmp_path / "companies"
    companies.mkdir(parents=True, exist_ok=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10,
                         adapter_id="company_raw_v1", read_only=False,
                         reusable_for_filing=True, canonical_write_target="companies"),
                RootSpec("dayu_portfolio", portfolio, "dayu_portfolio", priority=20,
                         reusable_for_filing=True),
            ),
        )
    )
    try:
        catalog.scan()
        undated = [
            row for row in catalog.reader.fetchall(
                "SELECT document_id, published_date FROM documents"
            ) if row["published_date"] is None
        ]
        assert len(undated) == 1
        # The group meta.json gains its filing_date declaration later.
        persist_meta("2026-02-20")

        service, calls = _service(tmp_path, catalog)
        result = service.ensure(
            _request(entity="00700", market="HK", security_id="00700"), budget=_budget(),
        )

        assert result.status is SourceEnsureStatus.REUSED
        assert len(calls) == 2
        repaired = catalog.reader.fetchall(
            "SELECT published_date FROM documents WHERE document_id=?",
            (undated[0]["document_id"],),
        )[0]
        assert repaired["published_date"] == "2026-02-20"
        events = json.loads(
            (tmp_path / ".source_catalog" / "catalog_repairs.jsonl").read_text("utf-8").splitlines()[0]
        )
        assert events["registered"][0]["sidecar_kind"] == "group_meta_json"
        assert events["registered"][0]["relative_path"].startswith("HK00700/filings/fil_ff1-0001/")
    finally:
        catalog.close()


def test_planner_is_read_only_for_the_catalog_database(tmp_path):
    """The precheck reads only: no row changes, no journal, no repair applied."""
    from company_wiki.source_catalog.catalog_repair import plan_undated_group_repairs
    from company_wiki.source_catalog.resolver import ResolutionStatus, SourceResolver

    catalog = _catalog(tmp_path)
    document = _write_undated_annual(tmp_path / "companies")
    try:
        catalog.scan()
        document_id = "urn:company-wiki:document:sha256:" + SHA
        resolution = SourceResolver(catalog).resolve(_request())
        assert resolution.status is ResolutionStatus.AMBIGUOUS
        assert resolution.reason == "unique_match_published_date_unknown"

        # The declaration arrives while the catalog row stays undated.
        _persist_sidecar(document, "2026-02-20")
        repairs = plan_undated_group_repairs(catalog, resolution)

        assert len(repairs) == 1
        assert repairs[0].filing_date == "2026-02-20"
        assert repairs[0].root_id == "company_raw"
        # Planning changed nothing.
        still = catalog.reader.exact_source_version(document_id)
        assert still["published_date"] is None
        assert not (tmp_path / ".source_catalog" / "catalog_repairs.jsonl").exists()
    finally:
        catalog.close()
