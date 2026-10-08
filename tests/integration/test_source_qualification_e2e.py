"""One source version: retrieval recovery and reuse after factual correction."""

from dataclasses import replace
import hashlib

import pytest

from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest, NarrativeTransportError
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_catalog.source_reader import SourceRef
from contract.test_single_intent_latest_acquisition import BoundedAdapter, _budget, _request, _service
from support.narrative_transport_fixture import published_fixture


def _publication(catalog, ref, value):
    if not isinstance(ref, SourceRef):
        ref = SourceRef(**ref.to_dict())
    return catalog.record_source_facts(ref=ref, facts={"published_date": value}, evidence={
        "published_date": {"value": value, "locator": "fixture:independent-publication-record"},
    })


@pytest.mark.parametrize("missing", [False, True])
def test_real_ensure_never_confuses_indexed_with_verified_local_bytes(tmp_path, missing):
    adapter = BoundedAdapter()
    transaction, service = _service(tmp_path, adapter)
    try:
        request = replace(_request(), allow_download=True)
        imported = service.ensure(request, budget=_budget())
        handle, = imported.resolution.matches
        reader = SourceVersionReader(transaction.catalog)
        ref = reader.query_ref(handle.document_id, handle.source_id, handle.content_sha256)
        original = reader.open_version(ref, purpose="preview").data
        _publication(transaction.catalog, ref, None)
        if missing:
            from pathlib import Path
            path = Path(handle.canonical_path).resolve()
            assert path.is_relative_to(tmp_path.resolve())
            path.unlink()
        result = service.ensure(request, budget=_budget())
        assert result.resolution.matches == ()  # Unknown publication never becomes historical evidence.
        assert adapter.fetch_calls == (2 if missing else 1)
        assert adapter.discover_calls == (2 if missing else 1)
        assert reader.open_version(ref, purpose="preview").data == original
        again = service.ensure(request, budget=_budget())
        assert again.resolution.matches == ()
        assert adapter.fetch_calls == (2 if missing else 1)
    finally:
        transaction.catalog.close()


def test_new_import_resolves_only_for_selection_lock_recheck_and_result(tmp_path, monkeypatch):
    from company_wiki.source_catalog import SourceResolver

    adapter = BoundedAdapter()
    transaction, service = _service(tmp_path, adapter)
    original_resolve = SourceResolver.resolve
    resolutions = []

    def observed(self, request):
        resolutions.append(request.request_id)
        return original_resolve(self, request)

    monkeypatch.setattr(SourceResolver, "resolve", observed)
    try:
        result = service.ensure(replace(_request(), allow_download=True), budget=_budget())
        assert result.canonical_import is not None and adapter.fetch_calls == 1
        assert len(resolutions) == 3
        assert result.resolution.matches[0].content_sha256 == result.canonical_import.source_ref.content_sha256
    finally:
        transaction.catalog.close()


def test_unknown_publication_annual_ensure_stores_once_then_skips_provider(tmp_path):
    from company_wiki.source_catalog.acquisition_service import SourceEnsureStatus

    adapter = BoundedAdapter(mutation={"filing_date": None})
    transaction, service = _service(tmp_path, adapter)
    try:
        request = replace(_request(), allow_download=True)
        first = service.ensure(request, budget=_budget())
        assert first.status is SourceEnsureStatus.AMBIGUOUS
        assert first.attempt.outcome == "downloaded_new"
        reader = SourceVersionReader(transaction.catalog)
        ref = first.canonical_import.source_ref
        assert reader.describe_version(ref)["published_date"] is None
        assert reader.open_version(ref, purpose="preview").data == b"%PDF-2025"
        second = service.ensure(request, budget=_budget())
        assert second.resolution.matches == ()
        assert adapter.fetch_calls == adapter.discover_calls == 1
    finally:
        transaction.catalog.close()


def test_wrong_local_identity_is_excluded_and_correct_provider_can_import(tmp_path):
    import json
    from contract.test_source_version_reader import OTHER, OTHER_SHA, _write

    adapter = BoundedAdapter()
    transaction, service = _service(tmp_path, adapter)
    try:
        request = replace(_request(), allow_download=True)
        root = transaction.catalog.config.roots[0].path
        original = _write(root / request.entity / "raw" / "financial_reports" / "annual",
                          name="unrelated.pdf", body=OTHER, sha=OTHER_SHA,
                          provider_id="old-conflicting-source")
        sidecar = original.with_name(original.name + ".source.json")
        facts = json.loads(sidecar.read_text(encoding="utf-8"))
        facts.update(market="HK", security_id="OTHER")
        sidecar.write_text(json.dumps(facts), encoding="utf-8")
        transaction.catalog.scan()
        result = service.ensure(request, budget=_budget())
        assert result.resolution.matches[0].content_sha256 != OTHER_SHA
        assert adapter.fetch_calls == adapter.discover_calls == 1
        assert original.read_bytes() == OTHER
        repeated = service.ensure(request, budget=_budget())
        assert repeated.resolution.matches == result.resolution.matches
        assert adapter.fetch_calls == adapter.discover_calls == 1
    finally:
        transaction.catalog.close()


def test_metadata_correction_replays_existing_artifact_without_regeneration(tmp_path):
    with published_fixture(tmp_path, scoped_policy=True) as fixture:
        raw_sha = hashlib.sha256(fixture.raw_path.read_bytes()).hexdigest()
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        _publication(fixture.catalog, fixture.source_ref, None)
        current_request = NarrativeReadRequest.from_dict(fixture.read_request(reference, as_of_date=None))
        current = transport.read(current_request)
        assert current.data == fixture.payload
        historic = NarrativeReadRequest.from_dict(fixture.read_request(reference))
        with pytest.raises(NarrativeTransportError, match="source_publication_unknown"):
            transport.read(historic)
        correction = _publication(fixture.catalog, fixture.source_ref, "2026-08-01")
        repeated = _publication(fixture.catalog, fixture.source_ref, "2026-08-01")
        assert repeated["status"] == "unchanged" and repeated["assertion_id"] == correction["assertion_id"]
        accepted = transport.read(historic)
        assert accepted.data == fixture.payload
        assert accepted.receipt["locator_count"] == current.receipt["locator_count"]
        assert transport.reference(fixture.source_ref).to_dict() == reference.to_dict()
        assert hashlib.sha256(fixture.raw_path.read_bytes()).hexdigest() == raw_sha
        _publication(fixture.catalog, fixture.source_ref, "2026-09-02")
        with pytest.raises(NarrativeTransportError, match="source_after_as_of"):
            transport.read(historic)
