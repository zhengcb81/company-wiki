"""Non-author, synthetic public API acceptance of the frozen CWP scope fix.

All file mutation belongs to a fresh test lake. No supplier network, real keys,
installed skills, production config, or original material is accessed.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import sys

import fitz
import pytest

TREE = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root")
sys.path.insert(0, str(TREE / "src"))

from company_wiki.source_catalog.acquisition import (
    AcquisitionCoordinator, AdapterRegistry, DownloadCandidate, DownloadReceipt,
)
from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
from company_wiki.source_catalog.assertion_service import get_verified_assertion
from company_wiki.source_catalog.canonical_scope import (
    HistoricalCaptureScopes, ScopeRelation, qualified_source_scope, scope_relatedness,
)
from company_wiki.source_catalog.canonical_writer import CanonicalImportError, CanonicalSourceWriter
from company_wiki.source_catalog.local_inventory import LocalReadBudget, LocalPrepareLimits
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.security_identity import SecurityMasterStore, SecurityRecord
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_operation import project_operation_result
from company_wiki.source_catalog.source_reader import SourceReadError, SourceVersionReader
from company_wiki.source_catalog.store import retire_document

TRACE = Path(__file__).with_name("public-api-trace.jsonl")


def note(event, **data):
    with TRACE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": event, **data}, ensure_ascii=False, default=str) + "\n")


def denied_network(*args, **kwargs):
    raise AssertionError("offline acceptance may not access a network")


@pytest.fixture(autouse=True)
def network_denied(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", denied_network)
    monkeypatch.setattr(socket, "create_connection", denied_network)
    monkeypatch.setattr(socket, "getaddrinfo", denied_network)


def pdf(label):
    with fitz.open() as doc:
        doc.new_page().insert_text((45, 55), label)
        return doc.tobytes(no_new_id=True)


def req(market="CN", year=2022, period="FY", kind="annual_report", *, allow_download=True):
    return SourceRequest(entity="Beta Systems", document_kind=kind, as_of_date="2029-12-31",
                         market=market, security_id={"CN": "688777", "HK": "07777", "US": "BETA"}[market],
                         fiscal_year=year, fiscal_period=period, allow_download=allow_download)


class IndependentProvider:
    name = "independent-source-review"
    version = "1.0.0"
    supports_acquisition_budget = True

    def __init__(self, *, sec=False, override_bytes=None, declared_year=None):
        self.sec, self.override_bytes, self.declared_year = sec, override_bytes, declared_year
        self.calls = []

    def discover(self, request):
        return self.discover_bounded(request, budget())

    def fetch(self, candidate, staging_dir):
        return self.fetch_bounded(candidate, staging_dir, budget())

    def discover_bounded(self, request, budget):
        budget.ensure_open()
        self.calls.append(("discover", request.fiscal_year, request.fiscal_period))
        year = self.declared_year if self.declared_year is not None else request.fiscal_year
        accession = f"{request.market}-{year}-{request.fiscal_period}"
        return (DownloadCandidate(
            candidate_id=f"candidate-{accession}", provider="sec" if self.sec else "independent-fixture",
            provider_document_id=accession, market=request.market, entity=request.entity,
            title=f"{year} {request.fiscal_period} {request.entity} original",
            source_url=(f"https://www.sec.gov/Archives/edgar/data/77777/{year}/original.htm" if self.sec
                        else f"https://fixture.invalid/{accession}.pdf"),
            document_kind=request.document_kind, filing_date=f"{year + 1}-04-15",
            fiscal_year=year, fiscal_period=request.fiscal_period,
            form_type="10-K" if self.sec else request.document_kind, language="en",
        ),)

    def fetch_bounded(self, candidate, staging_dir, budget):
        budget.ensure_open()
        self.calls.append(("fetch", candidate.fiscal_year, candidate.fiscal_period))
        if self.override_bytes is not None:
            data = self.override_bytes
        elif self.sec:
            data = (f'<html><head><title>Beta Systems 10-K</title></head><body>'
                    f'<ix:nonNumeric name="dei:EntityCentralIndexKey">77777</ix:nonNumeric>'
                    f'<ix:nonNumeric name="dei:DocumentFiscalYearFocus">{candidate.fiscal_year}</ix:nonNumeric>'
                    f'<ix:nonNumeric name="dei:DocumentFiscalPeriodFocus">FY</ix:nonNumeric>'
                    f'<ix:nonNumeric name="dei:DocumentPeriodEndDate">{candidate.fiscal_year}-12-31</ix:nonNumeric>'
                    f'<ix:nonNumeric name="dei:DocumentType">10-K</ix:nonNumeric>'
                    f'<p>Beta Systems original business discussion.</p></body></html>').encode()
        else:
            data = pdf(f"{candidate.entity} {candidate.market} {candidate.fiscal_year} {candidate.fiscal_period}")
        budget.consume_response_bytes(len(data))
        staging_dir.mkdir(parents=True, exist_ok=True)
        path = staging_dir / ("document.htm" if self.sec else "document.pdf")
        path.write_bytes(data)
        return DownloadReceipt(candidate_id=candidate.candidate_id, provider=candidate.provider,
            provider_document_id=candidate.provider_document_id, source_url=candidate.source_url,
            staged_path=str(path), content_sha256=hashlib.sha256(data).hexdigest(), byte_size=len(data),
            mime_type="text/html" if self.sec else "application/pdf", retrieved_at="2028-02-02T00:00:00Z",
            http_status=200, adapter_name=self.name, adapter_version=self.version)


@pytest.fixture
def lake(tmp_path):
    originals = tmp_path / "raw"
    originals.mkdir()
    catalog = SourceCatalog(CatalogConfig(project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec("company_raw", originals, "company_raw", adapter_id="company_raw_v1"),)))
    catalog.scan()
    try:
        yield catalog
    finally:
        catalog.close()


def service(catalog, provider):
    return SourceAcquisitionService(coordinator=AcquisitionCoordinator(catalog=catalog,
        adapters=AdapterRegistry(cn=provider, hk=provider, us=provider),
        staging_root=catalog.config.catalog_dir / "staging"), writer=CanonicalSourceWriter(catalog),
        journal=AcquisitionJournal(catalog.config.catalog_dir))


def ensure(svc, request):
    result = svc.ensure(request, budget=budget())
    note("ensure", request=request.to_dict(), response=result.to_dict(), provider_calls=svc.coordinator.adapters.cn.calls)
    return result


def budget():
    return AcquisitionBudget.from_limits(max_response_bytes=150000, max_seconds=12, max_cost_usd="0")


from company_wiki.source_catalog.download_budget import AcquisitionBudget


def statement(catalog, ref):
    return get_verified_assertion(catalog.reader, ref.source_id, ref.content_sha256, reader="steady")


def candidate_document(catalog, ref):
    return next(item for item in catalog.query_filing_candidates(document_kind="annual_report",
        source_statuses=("active", "retired"), limit=20) if item["document_id"] == ref.document_id)


@pytest.mark.parametrize("market,kind,p0,p1,y0,y1", [
    ("CN", "annual_report", "FY", "FY", 2022, 2023),
    ("HK", "annual_report", "FY", "FY", 2025, 2026),
    ("US", "annual_report", "FY", "FY", 2023, 2024),
    ("HK", "quarterly_report", "Q1", "Q2", 2024, 2024),
    ("HK", "semi_annual_report", "H1", "H1", 2023, 2024),
])
def test_public_capture_reuse_and_new_scope(lake, market, kind, p0, p1, y0, y1):
    provider = IndependentProvider()
    svc = service(lake, provider)
    first = ensure(svc, req(market, y0, p0, kind))
    assert first.status.value == "imported"
    ref = first.canonical_import.source_ref
    path = Path(first.canonical_import.canonical_path)
    original = path.read_bytes()
    same = ensure(svc, req(market, y0, p0, kind, allow_download=False))
    assert same.status.value == "reused"
    assert len(provider.calls) == 2
    new = ensure(svc, req(market, y1, p1, kind))
    assert new.status.value == "imported", new.to_dict()
    assert len(provider.calls) == 4
    assert new.canonical_import.source_ref.content_sha256 != ref.content_sha256
    assert ensure(svc, req(market, y1, p1, kind, allow_download=False)).status.value == "reused"
    assert len(provider.calls) == 4
    assert path.read_bytes() == original
    assert SourceVersionReader(lake).open_version(ref, purpose="source_export").data == original
    assert statement(lake, ref)["evidence_basis"] == "source-facts"


def legacy(lake, monkeypatch):
    provider = IndependentProvider()
    svc = service(lake, provider)
    with monkeypatch.context() as patch:
        patch.setattr(svc.writer, "_record_validated_capture", lambda *args: None)
        first = ensure(svc, req())
    assert first.status.value == "imported"
    ref = first.canonical_import.source_ref
    assert statement(lake, ref) is None
    return provider, svc, first


def test_legacy_genuine_success_scope_promotes_no_publication(lake, monkeypatch):
    provider, svc, first = legacy(lake, monkeypatch)
    ref = first.canonical_import.source_ref
    history = HistoricalCaptureScopes(lake, LocalReadBudget(LocalPrepareLimits()))
    scope = qualified_source_scope(lake, ref, candidate_document(lake, ref), historical=history)
    assert scope.authority == "historical-canonical-request"
    assert "published_date" not in scope.facts and "filing_date" not in scope.facts and "title" not in scope.facts
    assert scope_relatedness(scope, req(year=2023)) is ScopeRelation.NOT_RELEVANT
    assert statement(lake, ref) is None
    # Scope exclusion must not re-run the master lookup or parse an irrelevant original.
    from company_wiki.source_catalog import local_reconcile
    with monkeypatch.context() as patch:
        patch.setattr(local_reconcile, "_identity", lambda *args: pytest.fail("irrelevant old period identity lookup"))
        patch.setattr(local_reconcile, "restore_document_facts", lambda *args, **kwargs: pytest.fail("irrelevant old period reread"))
        assert ensure(svc, req(year=2023)).status.value == "imported"
    assert len(provider.calls) == 4
    note("historical_scope", facts=scope.facts, authority=scope.authority)


def test_legacy_attempt_hash_is_not_a_declaration_receipt(lake, monkeypatch):
    provider, svc, first = legacy(lake, monkeypatch)
    journal = AcquisitionJournal(lake.config.catalog_dir).path
    item = json.loads(journal.read_text(encoding="utf-8"))
    item["candidate_id"] = "not-the-candidate"  # Deliberately leave the genuine digest unchanged.
    journal.write_text(json.dumps(item) + "\n", encoding="utf-8")
    history = HistoricalCaptureScopes(lake, LocalReadBudget(LocalPrepareLimits()))
    ref = first.canonical_import.source_ref
    scope = qualified_source_scope(lake, ref, candidate_document(lake, ref), historical=history)
    assert scope.authority == "unverified-declaration"
    assert scope_relatedness(scope, req(year=2023)) is ScopeRelation.UNKNOWN
    result = ensure(svc, req(year=2023))
    assert result.status.value == "missing" and result.acquisition.local_preparation["blocks_download"] is True
    assert len(provider.calls) == 2


def test_unverified_scanned_sidecar_cannot_be_trusted(lake):
    provider = IndependentProvider()
    candidate = provider.discover_bounded(req(), budget())[0]
    receipt = provider.fetch_bounded(candidate, lake.config.project_root / "loose", budget())
    path = lake.config.roots[0].path / "Beta Systems" / "2022_annual_report.pdf"
    path.parent.mkdir()
    path.write_bytes(Path(receipt.staged_path).read_bytes())
    declaration = dict(candidate.to_dict(), company_name="Beta Systems", security_id="688777",
        request=req().to_dict(), candidate=candidate.to_dict(), receipt=receipt.to_dict(),
        request_id=req().request_id, content_sha256=receipt.content_sha256, byte_size=receipt.byte_size,
        mime_type=receipt.mime_type, capture_ready=True, created_by="canonical-writer")
    path.with_name(path.name + ".source.json").write_text(json.dumps(declaration), encoding="utf-8")
    lake.scan()
    provider.calls.clear()
    result = ensure(service(lake, provider), req(year=2023))
    assert result.status.value == "missing"
    assert result.acquisition.local_preparation["blocks_download"] is True
    assert provider.calls == []
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 0
    dto = project_operation_result(result.to_dict(), operation="ensure", reader=SourceVersionReader(lake))
    assert dto["local_preparation"]["blocks_download"] is True
    assert dto["status"] in {"blocked", "unavailable"}
    note("unknown_sidecar_diagnostic", dto=dto)


def test_bad_same_size_bytes_cannot_record_successful_reuse(lake):
    provider = IndependentProvider()
    svc = service(lake, provider)
    first = ensure(svc, req())
    path = Path(first.canonical_import.canonical_path)
    original = path.read_bytes()
    broken = bytearray(original)
    broken[-9] ^= 1
    assert len(original) == len(broken)
    path.write_bytes(broken)
    with pytest.raises(SourceReadError) as error:
        ensure(svc, req())
    outcomes = [item.outcome for item in svc.journal.read_all()]
    assert outcomes == ["downloaded_new", "failed"]
    assert len(provider.calls) == 2
    note("bad_sha", reason=error.value.reason, journal_outcomes=outcomes)


def test_same_bytes_two_fiscal_years_reject_without_rewrite(lake):
    provider = IndependentProvider()
    svc = service(lake, provider)
    first = ensure(svc, req())
    path = Path(first.canonical_import.canonical_path)
    sidecar = Path(first.canonical_import.provenance_path)
    before = (path.read_bytes(), sidecar.read_bytes(), statement(lake, first.canonical_import.source_ref))
    other = IndependentProvider(override_bytes=before[0])
    candidate = other.discover_bounded(req(year=2023), budget())[0]
    receipt = other.fetch_bounded(candidate, svc.writer.staging_root, budget())
    with pytest.raises(CanonicalImportError, match="canonical_scope_conflict:fiscal_year"):
        svc.writer.import_staged(req(year=2023), candidate, receipt)
    assert (path.read_bytes(), sidecar.read_bytes(), statement(lake, first.canonical_import.source_ref)) == before
    assert lake.store.fetchone("SELECT count(*) n FROM source_metadata_assertions")["n"] == 1


def test_real_dei_rejects_provider_period_override(lake):
    # Register synthetic SEC issuer identity once in this lake only, never production.
    SecurityMasterStore(lake.config.catalog_dir / "security_master").write_market("US", (
        SecurityRecord("Beta Systems", "US", "NASDAQ", "BETA", "BETA", (), True, "sec",
                       "https://www.sec.gov/files/company_tickers.json", "77777", {"cik": "77777"}),
    ), retrieved_at="2028-02-02T00:00:00Z", sources=("sec",))
    provider = IndependentProvider(sec=True)
    svc = service(lake, provider)
    first = ensure(svc, req("US", 2023))
    assert first.status.value == "imported", first.to_dict()
    assert ensure(svc, req("US", 2023, allow_download=False)).status.value == "reused"
    path = Path(first.canonical_import.canonical_path)
    before = path.read_bytes()
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    assert prepare_local_source(lake, req("US", 2023))["status"] == "ready"
    assertion = statement(lake, first.canonical_import.source_ref)
    primary = json.loads(assertion["evidence_json"])["source_fact_patch"]
    assert primary["fiscal_year"] == 2023 and primary["fiscal_period"] == "FY"
    false_provider = IndependentProvider(sec=True, override_bytes=before)
    # Incoming 2024 metadata with actual 2023 DEI may not replace the established scope.
    candidate = false_provider.discover_bounded(req("US", 2024), budget())[0]
    receipt = false_provider.fetch_bounded(candidate, svc.writer.staging_root, budget())
    with pytest.raises(CanonicalImportError, match="canonical_scope_conflict:fiscal_year"):
        svc.writer.import_staged(req("US", 2024), candidate, receipt)
    assert statement(lake, first.canonical_import.source_ref) == assertion
    assert path.read_bytes() == before
    # Also exercise SEC's native primary parser on a genuine different original,
    # rather than claiming that the generic US/PDF market vector covers it.
    assert ensure(svc, req("US", 2024)).status.value == "imported"
    assert ensure(svc, req("US", 2024, allow_download=False)).status.value == "reused"
    assert len(provider.calls) == 4
    assert path.read_bytes() == before
    note("strong_dei_preserved", fiscal_year=primary["fiscal_year"], evidence_basis=assertion["evidence_basis"])


def test_callback_failure_rolls_back_new_registration_and_fact_row(lake, monkeypatch):
    provider = IndependentProvider()
    writer = CanonicalSourceWriter(lake)
    candidate = provider.discover_bounded(req(), budget())[0]
    receipt = provider.fetch_bounded(candidate, writer.staging_root, budget())
    original_record = writer._record_validated_capture
    def fail_after_fact(*args):
        original_record(*args)
        raise RuntimeError("independent post-fact injected failure")
    with monkeypatch.context() as patch:
        patch.setattr(writer, "_record_validated_capture", fail_after_fact)
        with pytest.raises(RuntimeError, match="post-fact injected"):
            writer.import_staged(req(), candidate, receipt)
    counts = {table: lake.store.fetchone(f"SELECT count(*) n FROM {table}")["n"]
              for table in ("documents", "sources", "locations", "source_metadata_assertions")}
    assert counts == dict.fromkeys(counts, 0)
    assert Path(receipt.staged_path).is_file()
    recovered = writer.import_staged(req(), candidate, receipt)
    assert recovered.source_ref.content_sha256 == receipt.content_sha256
    assert statement(lake, recovered.source_ref)["decision"] == "verified"
    note("atomic_new_registration_failure", rolled_back_counts=counts, retry=recovered.to_dict())


def test_callback_failure_rolls_back_retirement_reactivation(lake, monkeypatch):
    provider = IndependentProvider()
    svc = service(lake, provider)
    first = ensure(svc, req())
    ref = first.canonical_import.source_ref
    retire_document(lake.store, document_id=ref.document_id, reason="independent explicit withdrawal", created_by="test")
    before = (dict(lake.reader.exact_source_version(ref.document_id)),
              [dict(row) for row in lake.reader.exact_source_locations(ref.document_id, ref.source_id)],
              statement(lake, ref), Path(first.canonical_import.canonical_path).read_bytes())
    candidate = provider.discover_bounded(req(), budget())[0]
    receipt = provider.fetch_bounded(candidate, svc.writer.staging_root, budget())
    original_complete = svc.writer._complete_registration
    def fail_after_reactivation(*args, **kwargs):
        original_complete(*args, **kwargs)
        raise RuntimeError("independent post-reactivation injected failure")
    with monkeypatch.context() as patch:
        patch.setattr(svc.writer, "_complete_registration", fail_after_reactivation)
        with pytest.raises(RuntimeError, match="post-reactivation injected"):
            svc.writer.import_staged(req(), candidate, receipt)
    after = (dict(lake.reader.exact_source_version(ref.document_id)),
             [dict(row) for row in lake.reader.exact_source_locations(ref.document_id, ref.source_id)],
             statement(lake, ref), Path(first.canonical_import.canonical_path).read_bytes())
    assert after == before
    assert after[0]["source_status"] == "retired"
    assert Path(receipt.staged_path).is_file()
    note("atomic_reactivation_failure", source_status=after[0]["source_status"], unchanged=True)
