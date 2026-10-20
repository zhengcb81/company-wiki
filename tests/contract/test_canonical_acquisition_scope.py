"""Public canonical intake must not turn a trusted old period into a new-period veto."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pymupdf as fitz
import pytest

from company_wiki.source_catalog.acquisition import (
    AcquisitionCoordinator, AdapterRegistry, DownloadCandidate, DownloadReceipt,
)
from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
from company_wiki.source_catalog.download_budget import AcquisitionBudget
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_operation import project_operation_result
from company_wiki.source_catalog.source_reader import SourceVersionReader


def pdf_bytes(label):
    with fitz.open() as pdf:
        pdf.new_page().insert_text((30, 40), label)
        return pdf.tobytes(no_new_id=True)


class PeriodAdapter:
    name = "scope-fixture"
    version = "1.0.0"
    supports_acquisition_budget = True

    def discover_bounded(self, request, budget):
        budget.ensure_open()
        return self.discover(request)

    def fetch_bounded(self, candidate, staging_dir, budget):
        budget.ensure_open()
        receipt = self.fetch(candidate, staging_dir)
        budget.consume_response_bytes(receipt.byte_size)
        return receipt

    def __init__(self):
        self.discoveries = self.fetches = 0

    def discover(self, request):
        self.discoveries += 1
        year = request.fiscal_year
        period = request.fiscal_period
        return (DownloadCandidate(
            candidate_id=f"c-{year}-{period}", provider="fixture",
            provider_document_id=f"{request.market}-{year}-{period}",
            market=request.market, entity=request.entity,
            title=f"{request.entity} {year} {period} business report",
            source_url=f"https://example.test/{request.market}/{year}/{period}.pdf",
            document_kind=request.document_kind, fiscal_year=year,
            fiscal_period=period, form_type=request.document_kind,
            filing_date=f"{year + 1}-03-01", language="en",
        ),)

    def fetch(self, candidate, staging_dir):
        self.fetches += 1
        staging_dir.mkdir(parents=True, exist_ok=True)
        staged = staging_dir / "original.pdf"
        data = pdf_bytes(f"{candidate.entity} {candidate.market} {candidate.fiscal_year} {candidate.fiscal_period}")
        staged.write_bytes(data)
        return DownloadReceipt(
            candidate_id=candidate.candidate_id, provider=candidate.provider,
            provider_document_id=candidate.provider_document_id,
            source_url=candidate.source_url, staged_path=str(staged),
            content_sha256=hashlib.sha256(data).hexdigest(), byte_size=len(data),
            mime_type="application/pdf", retrieved_at="2026-01-01T00:00:00Z",
            http_status=200, adapter_name=self.name, adapter_version=self.version,
        )


@pytest.fixture
def lake(tmp_path):
    companies = tmp_path / "companies"
    companies.mkdir()
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", adapter_id="company_raw_v1"),),
    ))
    catalog.scan()
    try:
        yield catalog
    finally:
        catalog.close()


def request(market="CN", year=2024, period="FY", kind="annual_report"):
    return SourceRequest(entity="Acme", document_kind=kind, as_of_date="2026-12-31",
        market=market, security_id={"CN": "600000", "HK": "09999", "US": "ACME"}[market],
        fiscal_year=year, fiscal_period=period, allow_download=True)


def service(catalog, adapter):
    return SourceAcquisitionService(
        coordinator=AcquisitionCoordinator(catalog=catalog,
            adapters=AdapterRegistry(cn=adapter, hk=adapter, us=adapter),
            staging_root=catalog.config.catalog_dir / "staging"),
        writer=CanonicalSourceWriter(catalog), journal=AcquisitionJournal(catalog.config.catalog_dir),
    )


def ensure(svc, req):
    return svc.ensure(req, budget=AcquisitionBudget.from_limits(
        max_response_bytes=200000, max_seconds=10, max_cost_usd="0"))


@pytest.mark.parametrize("market", ["CN", "HK", "US"])
def test_public_writer_old_annual_does_not_block_next_year(lake, market):
    adapter = PeriodAdapter()
    svc = service(lake, adapter)
    old = ensure(svc, request(market))
    assert old.status.value == "imported"
    old_ref = old.canonical_import.source_ref
    old_sha = hashlib.sha256(Path(old.canonical_import.canonical_path).read_bytes()).hexdigest()
    assert ensure(svc, request(market)).status.value == "reused"
    assert (adapter.discoveries, adapter.fetches) == (1, 1)
    newer = ensure(svc, request(market, 2025))
    assert newer.status.value == "imported", newer.to_dict()
    assert (adapter.discoveries, adapter.fetches) == (2, 2)
    assert newer.canonical_import.source_ref.content_sha256 != old_sha
    assert ensure(svc, request(market, 2025)).status.value == "reused"
    assert (adapter.discoveries, adapter.fetches) == (2, 2)
    checked = SourceVersionReader(lake).open_version(old_ref, purpose="source_export").data
    assert hashlib.sha256(checked).hexdigest() == old_sha


@pytest.mark.parametrize("kind,old_period,new_period,new_year", [
    ("quarterly_report", "Q2", "Q3", 2024),
    ("semi_annual_report", "H1", "H1", 2025),
])
def test_public_writer_nonannual_cross_period(lake, kind, old_period, new_period, new_year):
    adapter = PeriodAdapter()
    svc = service(lake, adapter)
    assert ensure(svc, request("HK", 2024, old_period, kind)).status.value == "imported"
    new = ensure(svc, request("HK", new_year, new_period, kind))
    assert new.status.value == "imported", new.to_dict()
    assert adapter.fetches == 2


def test_scan_shape_alone_cannot_claim_canonical_scope(lake):
    req = request()
    adapter = PeriodAdapter()
    candidate = adapter.discover(req)[0]
    staged = adapter.fetch(candidate, lake.config.project_root / "staging")
    destination = lake.config.roots[0].path / "Acme" / "old.pdf"
    destination.parent.mkdir()
    destination.write_bytes(Path(staged.staged_path).read_bytes())
    sidecar = dict(candidate.to_dict(), company_name=req.entity, security_id=req.security_id,
        content_sha256=staged.content_sha256, byte_size=staged.byte_size, mime_type=staged.mime_type,
        request=req.to_dict(), candidate=candidate.to_dict(), receipt=staged.to_dict(),
        request_id=req.request_id, capture_ready=True, created_by="canonical-writer")
    destination.with_name(destination.name + ".source.json").write_text(json.dumps(sidecar), encoding="utf-8")
    lake.scan()
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 0
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    result = prepare_local_source(lake, request(year=2025))
    assert result["blocks_download"] is True
    assert result["status"] in {"blocked", "unavailable"}


def test_local_unknown_diagnostic_survives_pathless_projection(lake):
    source = lake.config.roots[0].path / "Acme" / "2024_annual_report.pdf"
    source.parent.mkdir()
    source.write_bytes(pdf_bytes("Acme 2024 report"))
    source.with_name(source.name + ".source.json").write_text(json.dumps({
        "company_name": "Acme", "document_kind": "annual_report", "fiscal_year": 2024,
        "market": "CN", "security_id": "600000", "fiscal_period": "FY",
    }), encoding="utf-8")
    lake.scan()
    adapter = PeriodAdapter()
    result = ensure(service(lake, adapter), request(year=2025))
    assert adapter.fetches == 0
    dto = project_operation_result(result.to_dict(), operation="ensure", reader=SourceVersionReader(lake))
    assert dto["status"] in {"blocked", "unavailable"}
    assert dto["local_preparation"]["blocks_download"] is True
    assert dto["local_preparation"]["reason"] == "verified_issuer_unavailable"
    assert dto["acquisition_observation"]["provider_started"] is False


def warm_legacy(lake, monkeypatch):
    adapter = PeriodAdapter()
    svc = service(lake, adapter)
    # The old public writer validated and registered bytes, but had no automatic fact projection.
    with monkeypatch.context() as patch:
        patch.setattr(svc.writer, "_record_validated_capture", lambda *args: None)
        old = ensure(svc, request())
    assert old.status.value == "imported"
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 0
    assert AcquisitionJournal(lake.config.catalog_dir).read_all()[0].outcome == "downloaded_new"
    return svc, adapter, old


def test_real_historical_commit_request_excludes_old_period(lake, monkeypatch):
    svc, adapter, old = warm_legacy(lake, monkeypatch)
    from company_wiki.source_catalog import local_reconcile
    monkeypatch.setattr(local_reconcile,"_identity",lambda *args: pytest.fail("old trusted scope cannot relookup identity"))
    monkeypatch.setattr(local_reconcile,"restore_document_facts",lambda *args,**kw: pytest.fail("old scope cannot reread bytes"))
    newer = ensure(svc, request(year=2025))
    assert newer.status.value == "imported"
    assert adapter.fetches == 2
    assert Path(old.canonical_import.canonical_path).is_file()
    assert ensure(svc,request(year=2025)).status.value == "reused"


@pytest.mark.parametrize("tamper", ["journal_digest", "request_scope", "version_sha", "candidate_binding"])
def test_historical_origin_requires_real_attempt_request_and_version_binding(lake, monkeypatch, tamper):
    svc, adapter, old = warm_legacy(lake, monkeypatch)
    if tamper == "journal_digest":
        journal = AcquisitionJournal(lake.config.catalog_dir).path
        item = json.loads(journal.read_text(encoding="utf-8"))
        item["attempt_id"] = "urn:company-wiki:acquisition-attempt:sha256:" + "a"*64
        journal.write_text(json.dumps(item)+"\n",encoding="utf-8")
    else:
        sidecar = Path(old.canonical_import.provenance_path)
        item = json.loads(sidecar.read_text(encoding="utf-8"))
        if tamper == "request_scope":
            item["request"]["fiscal_year"] = 2023
        elif tamper == "version_sha":
            item["receipt"]["content_sha256"] = "f"*64
        else:
            item["candidate"]["provider_document_id"] = "forged"
        sidecar.write_text(json.dumps(item),encoding="utf-8")
        # A re-scan deliberately retains the first equal-priority declaration.
        # Exercise first registration in a distinct catalog, with the genuine
        # historical operation log and modified external sidecar.
        probe = SourceCatalog(CatalogConfig(
            project_root=lake.config.project_root / "probe",
            catalog_dir=lake.config.project_root / "probe" / ".source_catalog",
            roots=lake.config.roots))
        probe.scan()
        AcquisitionJournal(probe.config.catalog_dir).path.write_bytes(
            AcquisitionJournal(lake.config.catalog_dir).path.read_bytes())
        try:
            newer = ensure(service(probe,adapter),request(year=2025))
        finally:
            probe.close()
    if tamper == "journal_digest":
        newer = ensure(svc,request(year=2025))
    assert newer.status.value == "missing"
    assert adapter.fetches == 1
    assert newer.acquisition.local_preparation["blocks_download"] is True


def test_trusted_old_retirement_does_not_block_or_restore_new_period(lake):
    from company_wiki.source_catalog.store import retire_document
    adapter = PeriodAdapter()
    svc = service(lake,adapter)
    old = ensure(svc,request())
    retire_document(lake.store,document_id=old.canonical_import.source_ref.document_id,
                    reason="explicit withdrawal",created_by="test")
    assert ensure(svc,request(year=2025)).status.value == "imported"
    row = lake.reader.exact_source_version(old.canonical_import.source_ref.document_id)
    assert row["source_status"] == "retired"
    assert lake.store.fetchone("SELECT count(*) n FROM document_restore_audit")["n"] == 0


def test_target_tampering_remains_unavailable_and_never_downloads(lake):
    from company_wiki.source_catalog.source_reader import SourceReadError
    adapter = PeriodAdapter()
    svc = service(lake,adapter)
    old = ensure(svc,request())
    path = Path(old.canonical_import.canonical_path)
    before = path.read_bytes()
    path.write_bytes(before.replace(b"Acme",b"Else"))
    # PDF text may be compressed; use a same-size mutation guaranteed to change actual bytes.
    changed = bytearray(before)
    changed[-8] ^= 1
    path.write_bytes(changed)
    with pytest.raises(SourceReadError):
        ensure(svc,request())
    assert adapter.fetches == 1
    outcomes=[item.outcome for item in AcquisitionJournal(lake.config.catalog_dir).read_all()]
    assert outcomes == ["downloaded_new","failed"]


def test_unknown_publication_for_target_is_not_a_cold_download(lake):
    adapter = PeriodAdapter()
    candidate = replace(adapter.discover(request())[0],filing_date=None)
    writer = CanonicalSourceWriter(lake)
    receipt = adapter.fetch(candidate,writer.staging_root)
    old = writer.import_staged(request(),candidate,receipt)
    result = ensure(service(lake,adapter),request())
    assert result.status.value in {"missing","ambiguous"}
    if result.acquisition.local_preparation is not None:
        assert result.acquisition.local_preparation["blocks_download"] is True
    assert not result.resolution.matches
    assert adapter.fetches == 1
    assert Path(old.canonical_path).is_file()


def test_writer_failure_rolls_back_registered_rows_and_facts_then_recovers(lake,monkeypatch):
    writer = CanonicalSourceWriter(lake)
    adapter = PeriodAdapter()
    candidate = adapter.discover(request())[0]
    receipt = adapter.fetch(candidate,writer.staging_root)
    original = writer._record_validated_capture
    with monkeypatch.context() as patch:
        patch.setattr(writer,"_record_validated_capture",lambda *args: (_ for _ in ()).throw(RuntimeError("fact transaction failed")))
        with pytest.raises(RuntimeError,match="fact transaction failed"):
            writer.import_staged(request(),candidate,receipt)
    assert lake.store.fetchone("SELECT count(*) n FROM documents")["n"] == 0
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 0
    assert Path(receipt.staged_path).is_file()
    assert writer._record_validated_capture == original
    restored = writer.import_staged(request(),candidate,receipt)
    assert restored.source_ref.content_sha256 == receipt.content_sha256
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 1


def test_same_bytes_conflicting_period_does_not_rewrite_facts_or_original(lake):
    from company_wiki.source_catalog.canonical_writer import CanonicalImportError
    adapter = PeriodAdapter()
    svc = service(lake,adapter)
    old = ensure(svc,request())
    source = Path(old.canonical_import.canonical_path)
    sidecar = Path(old.canonical_import.provenance_path)
    before = (source.read_bytes(),sidecar.read_bytes())
    candidate = adapter.discover(request(year=2025))[0]
    writer = svc.writer
    receipt = adapter.fetch(candidate,writer.staging_root)
    Path(receipt.staged_path).write_bytes(before[0])
    receipt = replace(receipt,content_sha256=old.canonical_import.content_sha256,byte_size=len(before[0]))
    with pytest.raises(CanonicalImportError,match="canonical_scope_conflict:fiscal_year"):
        writer.import_staged(request(year=2025),candidate,receipt)
    assert (source.read_bytes(),sidecar.read_bytes()) == before
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 1


def test_scan_does_not_erase_automatic_canonical_facts(lake):
    adapter = PeriodAdapter()
    svc = service(lake,adapter)
    old = ensure(svc,request())
    lake.scan()
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 1
    assert ensure(svc,request(year=2025)).status.value == "imported"
    assert Path(old.canonical_import.canonical_path).is_file()


def test_public_writer_pdf_receipt_with_html_bytes_is_rejected(lake):
    from company_wiki.source_catalog.canonical_writer import CanonicalImportError
    writer=CanonicalSourceWriter(lake)
    adapter=PeriodAdapter()
    candidate=adapter.discover(request())[0]
    receipt=adapter.fetch(candidate,writer.staging_root)
    html=b"<html><body>Acme report</body></html>"
    Path(receipt.staged_path).write_bytes(html)
    receipt=replace(receipt,content_sha256=hashlib.sha256(html).hexdigest(),byte_size=len(html))
    with pytest.raises(CanonicalImportError,match="PDF magic"):
        writer.import_staged(request(),candidate,receipt)
    assert lake.store.fetchone("SELECT count(*) n FROM documents")["n"] == 0


def test_failed_explicit_reacquisition_does_not_reactivate_retired_source(lake,monkeypatch):
    from company_wiki.source_catalog.store import retire_document
    adapter=PeriodAdapter()
    svc=service(lake,adapter)
    old=ensure(svc,request())
    retire_document(lake.store,document_id=old.canonical_import.source_ref.document_id,
                    reason="withdrawn",created_by="test")
    candidate=adapter.discover(request())[0]
    receipt=adapter.fetch(candidate,svc.writer.staging_root)
    with monkeypatch.context() as patch:
        patch.setattr(svc.writer,"_record_validated_capture",lambda *args: (_ for _ in ()).throw(RuntimeError("fact write failed")))
        with pytest.raises(RuntimeError,match="fact write failed"):
            svc.writer.import_staged(request(),candidate,receipt)
    assert lake.reader.exact_source_version(old.canonical_import.source_ref.document_id)["source_status"] == "retired"


def test_canonical_scope_claim_is_version_bound_and_conflict_is_named(lake):
    adapter=PeriodAdapter()
    svc=service(lake,adapter)
    old=ensure(svc,request())
    # Catalog corruption is not scan metadata: it must never become exclusion proof.
    row=lake.store.fetchone("SELECT assertion_id,evidence_json FROM source_metadata_assertions")
    payload=json.loads(row["evidence_json"])
    payload["canonical_commit"]["receipt"]["byte_size"] += 1
    with lake.store.transaction() as connection:
        connection.execute("UPDATE source_metadata_assertions SET evidence_json=? WHERE assertion_id=?",
                           (json.dumps(payload),row["assertion_id"]))
    result=ensure(svc,request(year=2025))
    assert result.status.value == "missing"
    assert result.acquisition.local_preparation["reason"] == "canonical_capture_binding_conflict"
    assert adapter.fetches == 1
    assert Path(old.canonical_import.canonical_path).is_file()


def test_original_extracted_fact_is_not_overwritten_by_provider_declaration(lake):
    from company_wiki.source_catalog.assertion_service import record_source_facts,get_verified_assertion
    from company_wiki.source_catalog.canonical_writer import CanonicalImportError
    adapter=PeriodAdapter()
    svc=service(lake,adapter)
    old=ensure(svc,request())
    ref=old.canonical_import.source_ref
    record_source_facts(lake,ref=ref,facts={"fiscal_year":2024},evidence={"fiscal_year":{
        "value":2024,"content_sha256":ref.content_sha256,"locator":"pdf:/page/1",
        "extraction_method":"original-cover/1"}})
    assertion=get_verified_assertion(lake.reader,ref.source_id,ref.content_sha256,reader="steady")
    candidate=adapter.discover(request(year=2025))[0]
    receipt=adapter.fetch(candidate,svc.writer.staging_root)
    data=Path(old.canonical_import.canonical_path).read_bytes()
    Path(receipt.staged_path).write_bytes(data)
    receipt=replace(receipt,content_sha256=ref.content_sha256,byte_size=ref.byte_size)
    with pytest.raises(CanonicalImportError,match="canonical_scope_conflict:fiscal_year"):
        svc.writer.import_staged(request(year=2025),candidate,receipt)
    assert get_verified_assertion(lake.reader,ref.source_id,ref.content_sha256,reader="steady") == assertion
