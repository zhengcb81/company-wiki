"""Contracts for immutable company-raw import after staging validation."""

from __future__ import annotations

import hashlib
from pathlib import Path


class _SingleCnAdapter:
    name = "stockinfo-cninfo"
    version = "1.0.0"

    def __init__(self):
        self.discover_calls = 0
        self.fetch_calls = 0

    def discover(self, request):
        from company_wiki.source_catalog import DownloadCandidate

        self.discover_calls += 1
        return (
            DownloadCandidate(
                candidate_id="cninfo:announcement-2025",
                provider="cninfo",
                provider_document_id="announcement-2025",
                market="CN",
                entity=request.entity,
                title="示例公司2025年年度报告",
                source_url="https://static.cninfo.com.cn/finalpage/2026-03-20/report.pdf",
                document_kind="annual_report",
                form_type="annual_report",
                filing_date="2026-03-20",
                fiscal_year=2025,
                fiscal_period="FY",
                language="zh-CN",
            ),
        )

    def fetch(self, candidate, staging_dir):
        from company_wiki.source_catalog import DownloadReceipt

        self.fetch_calls += 1
        path = staging_dir / "report.pdf"
        payload = b"%PDF-1.7\nservice downloaded annual report"
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


def _catalog(tmp_path: Path):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    companies = project / "companies"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec(
                    "company_raw",
                    companies,
                    "company_raw",
                    priority=10,
                    adapter_id="company_raw_v1",
                ),
            ),
        )
    )
    catalog.scan()
    return catalog


def _staged_contract(tmp_path: Path):
    from company_wiki.source_catalog import DownloadCandidate, DownloadReceipt, SourceRequest

    staging = tmp_path / "project" / ".source_catalog" / "staging" / "request" / "report.pdf"
    staging.parent.mkdir(parents=True)
    payload = b"%PDF-1.7\ncanonical annual report bytes"
    staging.write_bytes(payload)
    request = SourceRequest(
        entity="示例公司",
        security_id="600000",
        market="CN",
        document_kind="annual_report",
        fiscal_year=2025,
        fiscal_period="FY",
        as_of_date="2026-07-18",
        allow_download=True,
    )
    candidate = DownloadCandidate(
        candidate_id="cninfo:announcement-2025",
        provider="cninfo",
        provider_document_id="announcement-2025",
        market="CN",
        entity="示例公司",
        title="示例公司2025年年度报告",
        source_url="https://static.cninfo.com.cn/finalpage/2026-03-20/report.pdf",
        document_kind="annual_report",
        form_type="annual_report",
        filing_date="2026-03-20",
        fiscal_year=2025,
        fiscal_period="FY",
        language="zh-CN",
    )
    receipt = DownloadReceipt(
        candidate_id=candidate.candidate_id,
        provider=candidate.provider,
        provider_document_id=candidate.provider_document_id,
        source_url=candidate.source_url,
        staged_path=str(staging),
        content_sha256=hashlib.sha256(payload).hexdigest(),
        byte_size=len(payload),
        mime_type="application/pdf",
        retrieved_at="2026-07-18T12:00:00Z",
        http_status=200,
        adapter_name="stockinfo-cninfo",
        adapter_version="1.0.0",
    )
    return request, candidate, receipt, staging


def test_writer_atomically_imports_with_provenance_and_resolver_reuses_exact(tmp_path):
    from company_wiki.source_catalog import (
        CanonicalImportStatus,
        CanonicalSourceWriter,
        ResolutionStatus,
        SourceResolver,
    )

    catalog = _catalog(tmp_path)
    request, candidate, receipt, staged = _staged_contract(tmp_path)

    imported = CanonicalSourceWriter(catalog).import_staged(request, candidate, receipt)

    assert imported.status is CanonicalImportStatus.IMPORTED_NEW
    canonical = Path(imported.canonical_path)
    sidecar = Path(imported.provenance_path)
    assert canonical.is_file()
    assert canonical.is_relative_to(catalog.config.project_root / "companies" / "示例公司")
    assert sidecar == canonical.with_name(canonical.name + ".source.json")
    assert sidecar.is_file()
    assert not staged.exists()

    resolved = SourceResolver(catalog).resolve(
        request.__class__(
            entity=request.entity,
            security_id=request.security_id,
            market=request.market,
            document_kind=request.document_kind,
            fiscal_year=request.fiscal_year,
            fiscal_period=request.fiscal_period,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            as_of_date=request.as_of_date,
        )
    )
    assert resolved.status is ResolutionStatus.REUSED_EXACT
    assert len(resolved.matches) == 1
    assert resolved.matches[0].canonical_path == str(canonical.resolve())
    assert resolved.matches[0].capture_ready is True
    assert resolved.matches[0].https_url == candidate.source_url


def test_writer_reactivates_previously_retired_same_content_document(tmp_path):
    """A user-authorized re-download of bytes whose content-addressed document
    was retired must succeed and reactivate that document (Phase 15.6 batch
    governance: retire takes a record out of visibility; an explicit
    re-download brings the same content back as active)."""
    from company_wiki.source_catalog import (
        CanonicalImportStatus,
        CanonicalSourceWriter,
        ResolutionStatus,
        SourceResolver,
    )
    from company_wiki.source_catalog.store import retire_document

    catalog = _catalog(tmp_path)
    request, candidate, receipt, staged = _staged_contract(tmp_path)
    writer = CanonicalSourceWriter(catalog)

    first = writer.import_staged(request, candidate, receipt)
    assert first.status is CanonicalImportStatus.IMPORTED_NEW
    document_id = first.source_id.replace(
        "urn:company-wiki:source:", "urn:company-wiki:document:"
    )
    retire_document(
        catalog.store,
        document_id=document_id,
        reason="test-retire-then-redownload",
        created_by="test",
    )
    assert catalog.query(limit=10) == []

    # re-import the exact same bytes: must succeed and become active again
    # (either a fresh import or an exact dedup against the reactivated record)
    staged.write_bytes(b"%PDF-1.7\ncanonical annual report bytes")
    reimported = writer.import_staged(request, candidate, receipt)
    assert reimported.status in {
        CanonicalImportStatus.IMPORTED_NEW,
        CanonicalImportStatus.DEDUPLICATED_AFTER_DOWNLOAD,
    }

    resolved = SourceResolver(catalog).resolve(
        request.__class__(
            entity=request.entity,
            security_id=request.security_id,
            market=request.market,
            document_kind=request.document_kind,
            fiscal_year=request.fiscal_year,
            fiscal_period=request.fiscal_period,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            as_of_date=request.as_of_date,
        )
    )
    assert resolved.status is ResolutionStatus.REUSED_EXACT
    assert resolved.matches[0].capture_ready is True


def test_writer_reactivates_retired_document_via_dedup_when_location_is_active(tmp_path):
    """A retired document whose location stayed active (partial state left by
    a failed import) must be reactivated by the dedup re-acquisition path —
    the exact production shape seen for CATL FY2024 (Phase 15.6)."""
    from company_wiki.source_catalog import (
        CanonicalImportStatus,
        CanonicalSourceWriter,
        ResolutionStatus,
        SourceResolver,
    )
    from company_wiki.source_catalog.store import retire_document

    catalog = _catalog(tmp_path)
    request, candidate, receipt, staged = _staged_contract(tmp_path)
    writer = CanonicalSourceWriter(catalog)

    first = writer.import_staged(request, candidate, receipt)
    document_id = first.source_id.replace(
        "urn:company-wiki:source:", "urn:company-wiki:document:"
    )
    retire_document(
        catalog.store,
        document_id=document_id,
        reason="test-partial-state",
        created_by="test",
    )
    # simulate the partial state left by a failed import: document retired
    # but one location still active
    with catalog.store.transaction() as connection:
        connection.execute(
            "UPDATE locations SET location_status='active' WHERE document_id=?",
            (document_id,),
        )

    staged.write_bytes(b"%PDF-1.7\ncanonical annual report bytes")
    reimported = writer.import_staged(request, candidate, receipt)
    assert reimported.status is CanonicalImportStatus.DEDUPLICATED_AFTER_DOWNLOAD

    resolved = SourceResolver(catalog).resolve(
        request.__class__(
            entity=request.entity,
            security_id=request.security_id,
            market=request.market,
            document_kind=request.document_kind,
            fiscal_year=request.fiscal_year,
            fiscal_period=request.fiscal_period,
            provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            as_of_date=request.as_of_date,
        )
    )
    assert resolved.status is ResolutionStatus.REUSED_EXACT
    assert resolved.matches[0].capture_ready is True


def test_writer_deduplicates_downloaded_bytes_without_second_canonical_file(tmp_path):
    from company_wiki.source_catalog import CanonicalImportStatus, CanonicalSourceWriter

    catalog = _catalog(tmp_path)
    request, candidate, receipt, _ = _staged_contract(tmp_path)
    writer = CanonicalSourceWriter(catalog)
    first = writer.import_staged(request, candidate, receipt)

    duplicate = tmp_path / "project" / ".source_catalog" / "staging" / "replay" / "same.pdf"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_bytes(Path(first.canonical_path).read_bytes())
    replay_receipt = receipt.__class__(
        **{**receipt.to_dict(), "staged_path": str(duplicate)}
    )
    replay = writer.import_staged(request, candidate, replay_receipt)

    assert replay.status is CanonicalImportStatus.DEDUPLICATED_AFTER_DOWNLOAD
    assert replay.canonical_path == first.canonical_path
    assert not duplicate.exists()
    raw_files = [
        path
        for path in (catalog.config.project_root / "companies" / "示例公司" / "raw").rglob("*")
        if path.is_file() and not path.name.endswith(".source.json")
    ]
    assert raw_files == [Path(first.canonical_path)]


def test_writer_dedup_ignores_dayu_portfolio_locations(tmp_path):
    """Dedup must only match canonical company_raw locations: a same-hash file
    ingested from the dayu portfolio lives outside companies/ and must not be
    offered as the canonical path (MongoDB finding)."""
    from company_wiki.source_catalog import (
        CanonicalImportStatus,
        CanonicalSourceWriter,
        CatalogConfig,
        RootSpec,
        SourceCatalog,
    )

    project = tmp_path / "project"
    companies = project / "companies"
    portfolio = tmp_path / "dayu" / "portfolio"
    companies.mkdir(parents=True)
    filing = portfolio / "MDB" / "filings" / "fil_x"
    filing.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                RootSpec("company_raw", companies, "company_raw", priority=10),
                RootSpec("dayu", portfolio, "dayu_portfolio", priority=20),
            ),
        )
    )
    request, candidate, receipt, staged = _staged_contract(tmp_path)

    # a same-hash file exists only under the dayu portfolio root
    dayu_copy = filing / "same.htm"
    dayu_copy.write_bytes(staged.read_bytes())
    catalog.scan()

    writer = CanonicalSourceWriter(catalog)
    imported = writer.import_staged(request, candidate, receipt)

    assert imported.status is CanonicalImportStatus.IMPORTED_NEW
    canonical = Path(imported.canonical_path)
    assert canonical.is_relative_to(companies / "示例公司")
    assert not str(canonical).startswith(str(portfolio))


def test_ensure_service_records_download_and_later_zero_call_reuse(tmp_path):
    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionJournal,
        AdapterRegistry,
        CanonicalSourceWriter,
        SourceAcquisitionService,
        SourceEnsureStatus,
        SourceRequest,
    )

    catalog = _catalog(tmp_path)
    adapter = _SingleCnAdapter()
    staging_root = catalog.config.catalog_dir / "staging"
    service = SourceAcquisitionService(
        coordinator=AcquisitionCoordinator(
            catalog=catalog,
            adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
            staging_root=staging_root,
        ),
        writer=CanonicalSourceWriter(catalog, staging_root=staging_root),
        journal=AcquisitionJournal(catalog.config.catalog_dir),
    )
    request = SourceRequest(
        entity="示例公司",
        security_id="600000",
        market="CN",
        document_kind="annual_report",
        fiscal_year=2025,
        as_of_date="2026-07-18",
        allow_download=True,
    )

    first = service.ensure(request)
    second = service.ensure(request)

    assert first.status is SourceEnsureStatus.IMPORTED
    assert second.status is SourceEnsureStatus.REUSED
    assert adapter.discover_calls == 1
    assert adapter.fetch_calls == 1
    attempts = AcquisitionJournal(catalog.config.catalog_dir).read_all()
    assert [item.outcome for item in attempts] == [
        "downloaded_new",
        "reused_before_download",
    ]
    exported = catalog.export_indexes()
    attempts_csv = Path(exported["acquisition_attempts_csv"]).read_text(
        encoding="utf-8-sig"
    )
    assert "downloaded_new" in attempts_csv
    assert "reused_before_download" in attempts_csv


def test_writer_post_import_rescan_follows_snapshot_v2_flag(tmp_path, monkeypatch):
    """GP-002 O1: the post-import rescan inside CanonicalSourceWriter must
    follow the activation snapshot's v2_scan_shadow — once v2 is activated
    there must not be a second catalog writer still scanning v1 semantics
    (a v1-only scan inside a v2-activated directory would be a parity
    blind spot)."""
    import json

    from company_wiki.source_catalog import (
        CanonicalImportStatus,
        CanonicalSourceWriter,
    )
    from company_wiki.source_catalog import canonical_writer as cw_module
    from company_wiki.source_catalog.runtime_policy import snapshot_hash

    catalog = _catalog(tmp_path)
    project = tmp_path / "project"
    payload = {
        "schema_version": "1.0",
        "policy_hash": "d" * 64,
        "flags": {
            "v2_scan_shadow": True,
            "v2_persist_assertions": True,
            "v2_resolve_shadow": True,
            "v2_resolve_active": True,
            "v2_bundle_active": False,
            "legacy_bridge_enabled": False,
        },
        "current_epoch": "e1",
        "active_cohorts": ["c1"],
        "updated_at": "2026-09-02T00:00:00Z",
    }
    payload["snapshot_sha256"] = snapshot_hash(payload)
    (project / ".source_catalog" / "runtime_policy.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    request, candidate, receipt, staged = _staged_contract(tmp_path)

    observed: list[bool | None] = []
    original = cw_module.scan_catalog

    def spy(*args, **kwargs):
        observed.append(kwargs.get("v2_scan_shadow"))
        return original(*args, **kwargs)

    monkeypatch.setattr(cw_module, "scan_catalog", spy)
    imported = CanonicalSourceWriter(catalog).import_staged(
        request, candidate, receipt
    )
    assert imported.status is CanonicalImportStatus.IMPORTED_NEW
    assert observed and all(flag is True for flag in observed), (
        f"canonical writer rescan must follow snapshot v2_scan_shadow "
        f"(got {observed})"
    )
