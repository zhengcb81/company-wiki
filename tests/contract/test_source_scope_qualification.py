"""All filing read/reuse paths consume the one source-owner scope qualification."""

import pytest
from helpers.source_fact_fixture import lake, html, imported, evidence, close
from test_local_request_relevance import request
from company_wiki.source_catalog.source_reader import SourceVersionReader, SourceReadError
from company_wiki.source_catalog.resolver import SourceResolver
from company_wiki.source_catalog.local_inventory import LocalReadBudget, LocalPrepareLimits


def cached(cat, actual):
    data = html(cik="99999") if actual == "wrong_cik" else html(year=2022, end="2022-06-30") if actual == "wrong_year" else html()
    if actual == "wrong_company_binding":
        data = html(cik="99999").replace(b"Acme actual original.", b"Other issuer B actual original.")
    source_url = "https://www.sec.gov/Archives/edgar/data/99999/000009999926000007/original.htm" if actual == "wrong_company_binding" else None
    ref, path = imported(cat, data, published="2026-07-30", declared_year=2026, source_url=source_url)
    facts = {"form_type": "10-K", "fiscal_period": "FY", "provider": "official", "provider_document_id": "p-1"}
    cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
    return ref, path, data


@pytest.mark.parametrize("actual", ["wrong_cik", "wrong_year", "wrong_company_binding"])
@pytest.mark.parametrize("entry", ["open", "verify", "resolver", "ensure", "stage"])
def test_false_cached_scope_is_rejected_at_every_filing_reuse_entry(tmp_path, actual, entry):
    cat = lake(tmp_path)
    try:
        empty = SourceResolver(cat).resolve(request()) if entry == "stage" else None
        ref, path, data = cached(cat, actual)
        reader = SourceVersionReader(cat)
        assert reader.query_local(request()).status == "found"
        before = cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0]
        with pytest.raises(SourceReadError) as error:
            if entry == "open":
                reader.open_version(ref, purpose="filing_reuse")
            elif entry == "verify":
                reader.verify_version(ref, purpose="filing_reuse")
            elif entry == "resolver":
                SourceResolver(cat).resolve(request())
            else:
                from company_wiki.source_catalog.acquisition import AcquisitionCoordinator, AdapterRegistry
                from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
                from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
                from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
                class NoSupplier:
                    name = "offline"
                    version = "1"
                    def discover(self, *_):
                        raise AssertionError("invalid cache cannot initiate supplier")
                    def fetch(self, *_):
                        raise AssertionError("invalid cache cannot initiate supplier")
                supplier = NoSupplier()
                service = SourceAcquisitionService(coordinator=AcquisitionCoordinator(catalog=cat, adapters=AdapterRegistry(supplier, supplier, supplier), staging_root=cat.config.catalog_dir / "staging"), writer=CanonicalSourceWriter(cat), journal=AcquisitionJournal(cat.config.catalog_dir))
                if entry == "ensure":
                    service.ensure(request())
                else:
                    from dataclasses import replace
                    from company_wiki.source_catalog.acquisition import AcquisitionResult, AcquisitionStatus, DownloadCandidate
                    candidate = DownloadCandidate("c-1", "official", "p-1", "US", "Acme", "annual", "https://www.sec.gov/Archives/edgar/data/12345/original.htm", "annual_report", "2026-07-30", 2026, form_type="10-K", fiscal_period="FY")
                    selection = AcquisitionResult("1.0", AcquisitionStatus.SELECTED, empty, candidate=candidate)
                    service.coordinator.stage_selected(replace(request(), allow_download=True), selection)
        assert error.value.status == "blocked"
        assert error.value.reason == ("primary_scope_conflict" if actual == "wrong_year" else "primary_issuer_conflict")
        assert path.read_bytes() == data
        assert cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0] == before
    finally:
        close(cat)


@pytest.mark.parametrize("entry", ["reader", "resolver"])
def test_unproven_correct_scope_uses_single_sha_buffer_under_remaining_budget(tmp_path, monkeypatch, entry):
    from pathlib import Path
    cat = lake(tmp_path)
    try:
        ref, path, data = cached(cat, "correct")
        budget = LocalReadBudget(LocalPrepareLimits(max_bytes=ref.byte_size + 2))
        budget.charge(2)
        raw_open = Path.open
        opened = []
        def observe(self, *args, **kwargs):
            if self == path and args and args[0] == "rb":
                opened.append(self)
            return raw_open(self, *args, **kwargs)
        monkeypatch.setattr(Path, "open", observe)
        from company_wiki.source_catalog import dayu_fiscal_metadata
        original_extract = dayu_fiscal_metadata.extract_sec_scope
        parsed = []
        from company_wiki.source_catalog import assertion_service
        original_identity = assertion_service.source_issuer_identity
        identities = []
        def identity(*args, **kwargs):
            identities.append(args)
            return original_identity(*args, **kwargs)
        monkeypatch.setattr(assertion_service, "source_issuer_identity", identity)
        def extract(data):
            parsed.append(data)
            return original_extract(data)
        monkeypatch.setattr(dayu_fiscal_metadata, "extract_sec_scope", extract)
        if entry == "reader":
            SourceVersionReader(cat).verify_version(ref, purpose="filing_reuse", budget=budget)
        else:
            result = SourceResolver(cat, read_budget=budget).resolve(request())
            assert result.matches
        assert len(opened) == len(parsed) == len(identities) == 1 and budget.bytes_read == ref.byte_size + 2
    finally:
        close(cat)


def test_raw_preview_remains_byte_only_for_false_filing_labels(tmp_path):
    cat = lake(tmp_path)
    try:
        ref, path, data = cached(cat, "wrong_cik")
        assert SourceVersionReader(cat).open_version(ref, purpose="source_export").data == data
    finally:
        close(cat)


@pytest.mark.parametrize("entry", ["reader", "resolver", "prepare"])
def test_complete_original_scope_proof_streams_sha_without_master_or_reparse(tmp_path, monkeypatch, entry):
    from pathlib import Path
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    from company_wiki.source_catalog import assertion_service, dayu_fiscal_metadata
    cat = lake(tmp_path)
    try:
        ref, path, data = cached(cat, "correct")
        assert prepare_local_source(cat, request())["status"] == "ready"
        def forbidden(*args, **kwargs):
            raise AssertionError("complete scope proof must not reload master or parse again")
        monkeypatch.setattr(assertion_service, "source_issuer_identity", forbidden)
        from company_wiki.source_catalog import local_reconcile
        monkeypatch.setattr(local_reconcile, "_identity", forbidden)
        monkeypatch.setattr(dayu_fiscal_metadata, "extract_sec_scope", forbidden)
        raw_open = Path.open
        opened = []
        def observe(self, *args, **kwargs):
            if self == path and args and args[0] == "rb":
                opened.append(self)
            return raw_open(self, *args, **kwargs)
        monkeypatch.setattr(Path, "open", observe)
        budget = LocalReadBudget(LocalPrepareLimits(max_bytes=ref.byte_size))
        if entry == "reader":
            SourceVersionReader(cat).verify_version(ref, purpose="filing_reuse", budget=budget)
        elif entry == "resolver":
            assert SourceResolver(cat, read_budget=budget).resolve(request()).matches
        else:
            assert local_reconcile._prepare_local_source(cat, request(), _budget=budget)["status"] == "ready"
        assert len(opened) == 1 and budget.bytes_read == ref.byte_size
    finally:
        close(cat)


@pytest.mark.parametrize("scope", ["unknown", "conflict"])
def test_registered_provenance_cannot_stand_in_for_actual_dei_scope(tmp_path, scope):
    cat = lake(tmp_path)
    try:
        if scope == "unknown":
            data = b"<html><title>FY2026 10-K</title><body>No DEI original facts</body></html>"
        else:
            data = html(cik="99999")
        ref, path = imported(cat, data, published="2026-07-30", declared_year=2026)
        facts = {"form_type": "10-K", "fiscal_period": "FY"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        with pytest.raises(SourceReadError) as error:
            SourceVersionReader(cat).verify_version(ref, purpose="filing_reuse")
        assert error.value.status == "blocked"
        assert error.value.reason == ("fiscal_period_unresolved" if scope == "unknown" else "primary_issuer_conflict")
    finally:
        close(cat)


def test_conflicting_registered_issuer_observations_are_named(tmp_path):
    from company_wiki.source_catalog.assertion_service import source_scope_qualification
    cat = lake(tmp_path)
    try:
        ref, path, data = cached(cat, "correct")
        metadata = SourceVersionReader(cat).describe_version(ref)
        metadata["company_id"] = "99999"
        with pytest.raises(SourceReadError) as error:
            source_scope_qualification(cat, ref, metadata=metadata)
        assert error.value.reason == "primary_issuer_conflict"
    finally:
        close(cat)


@pytest.mark.parametrize("record_id", [None, "another-record"])
def test_incomplete_issuer_record_binding_observes_registered_company_once(tmp_path, monkeypatch, record_id):
    import json
    from company_wiki.source_catalog import assertion_service, dayu_fiscal_metadata
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    cat = lake(tmp_path)
    try:
        ref, path, data = cached(cat, "correct")
        assert prepare_local_source(cat, request())["status"] == "ready"
        prior = assertion_service.get_verified_assertion(cat.reader, ref.source_id, ref.content_sha256, reader="steady")
        proof = json.loads(prior["evidence_json"])["source_fact_evidence"]["entity"]
        proof["issuer_record_id"] = record_id
        cat.record_source_facts(ref=ref, facts={"entity": "Acme"}, evidence={"entity": proof})
        original_identity = assertion_service.source_issuer_identity
        original_extract = dayu_fiscal_metadata.extract_sec_scope
        calls = []
        def identity(*args, **kwargs):
            calls.append("identity")
            return original_identity(*args, **kwargs)
        def extract(data):
            calls.append("parse")
            return original_extract(data)
        monkeypatch.setattr(assertion_service, "source_issuer_identity", identity)
        monkeypatch.setattr(dayu_fiscal_metadata, "extract_sec_scope", extract)
        budget = LocalReadBudget(LocalPrepareLimits(max_bytes=ref.byte_size))
        SourceVersionReader(cat).verify_version(ref, purpose="filing_reuse", budget=budget)
        assert calls == ["identity", "parse"] and budget.bytes_read == ref.byte_size
    finally:
        close(cat)


def test_complete_original_company_proof_still_rejects_conflicting_url_provenance(tmp_path, monkeypatch):
    from company_wiki.source_catalog import assertion_service, dayu_fiscal_metadata
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    cat = lake(tmp_path)
    try:
        ref, path, data = cached(cat, "correct")
        assert prepare_local_source(cat, request())["status"] == "ready"
        facts = {"source_url": "https://www.sec.gov/Archives/edgar/data/99999/000009999926000007/original.htm"}
        cat.record_source_facts(ref=ref, facts=facts, evidence=evidence(ref, facts))
        def forbidden(*args, **kwargs):
            raise AssertionError("complete company proof must not reload master or parse")
        monkeypatch.setattr(assertion_service, "source_issuer_identity", forbidden)
        monkeypatch.setattr(dayu_fiscal_metadata, "extract_sec_scope", forbidden)
        with pytest.raises(SourceReadError) as error:
            SourceVersionReader(cat).verify_version(ref, purpose="filing_reuse")
        assert error.value.reason == "primary_issuer_conflict"
    finally:
        close(cat)
