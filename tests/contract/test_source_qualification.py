"""Local inventory remains visible without becoming historical evidence."""

from __future__ import annotations

from dataclasses import replace
import json

import pytest

from company_wiki.source_catalog.resolver import ResolutionStatus, SourceRequest, SourceResolver
from company_wiki.source_catalog.source_reader import SourceVersionReader
from contract.test_source_version_reader import BODY, SHA, OTHER, OTHER_SHA, _fixture, _write
from contract.test_source_version_reader_cli import _fixture as cli_fixture, _run_query_cli


@pytest.fixture
def lake(tmp_path):
    catalog, paths, _, row = _fixture(tmp_path)
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(row["document_id"], row["source_id"], SHA)
    request = SourceRequest(entity="Acme", market="US", security_id="ACME",
                            document_kind="annual_report", fiscal_year=2025,
                            as_of_date="2026-10-08", allow_download=True)
    try:
        yield catalog, reader, ref, paths[0], request
    finally:
        catalog.close()


def set_publication(catalog, ref, value):
    return catalog.record_source_facts(
        ref=ref, facts={"published_date": value},
        evidence={"published_date": {"locator": "fixture:explicit-publication", "value": value}},
    )


@pytest.mark.parametrize("published,status", [(None, "unknown"), ("2026-10-09", "after_as_of")])
def test_query_shows_excluded_version_without_reading_or_granting_reuse(lake, monkeypatch, published, status):
    catalog, reader, ref, original, request = lake
    set_publication(catalog, ref, published)
    original.unlink()  # DB-only query must not assert the file is currently present.

    def no_open(*args, **kwargs):
        raise AssertionError("catalog query must not open raw bytes")

    monkeypatch.setattr(reader, "open_version", no_open)
    result = reader.query_local(request)
    assert result.status == "not_found" and result.matches == ()
    diagnostic, = result.excluded_candidates
    assert diagnostic["source_ref"]["content_sha256"] == SHA
    qualification = diagnostic["qualification"]
    assert qualification["publication_status"] == status
    assert qualification["local_bytes_status"] == "not_checked"
    assert qualification["historical_reuse_eligible"] is False
    assert "path" not in json.dumps(diagnostic)


def test_unknown_date_missing_bytes_may_reach_authorized_acquisition(lake):
    catalog, _, ref, original, request = lake
    set_publication(catalog, ref, None)
    original.unlink()
    result = SourceResolver(catalog).resolve(request)
    assert result.status is ResolutionStatus.MISSING
    assert result.download_required and result.download_allowed
    diagnostic, = result.excluded_candidates
    assert diagnostic["qualification"]["local_bytes_status"] == "unavailable"
    assert diagnostic["source_ref"]["content_sha256"] == SHA


def test_unknown_date_verified_bytes_stop_duplicate_download_but_allow_preview(lake):
    catalog, reader, ref, original, request = lake
    set_publication(catalog, ref, None)
    result = SourceResolver(catalog).resolve(request)
    assert result.status is ResolutionStatus.AMBIGUOUS and result.matches == ()
    assert not result.download_required
    diagnostic, = result.excluded_candidates
    assert diagnostic["qualification"]["local_bytes_status"] == "verified"
    assert diagnostic["qualification"]["historical_reuse_eligible"] is False
    assert reader.open_version(ref, purpose="preview").data == BODY
    assert original.read_bytes() == BODY


def test_claim_only_corrupt_bytes_are_not_called_verified(lake):
    catalog, _, ref, original, request = lake
    set_publication(catalog, ref, None)
    original.write_bytes(b"%PDF-1.4 a corrupted replacement")
    result = SourceResolver(catalog).resolve(request)
    assert result.status is ResolutionStatus.MISSING
    diagnostic, = result.excluded_candidates
    assert diagnostic["qualification"]["local_bytes_status"] == "unavailable"


def test_invalid_indexed_date_is_visible_but_never_historically_eligible(lake):
    catalog, reader, ref, _, request = lake
    with catalog.store.transaction() as connection:
        connection.execute("UPDATE documents SET published_date=? WHERE document_id=?",
                           ("2026-02-30", ref.document_id))
    query = reader.query_local(request)
    assert query.matches == ()
    diagnostic, = query.excluded_candidates
    assert diagnostic["qualification"]["publication_status"] == "invalid"
    result = SourceResolver(catalog).resolve(request)
    assert result.status is ResolutionStatus.AMBIGUOUS and result.matches == ()


def test_same_version_publication_correction_keeps_source_and_capture(lake):
    catalog, reader, ref, original, request = lake
    set_publication(catalog, ref, None)
    before = dict(catalog.reader.exact_source_version(ref.document_id))
    captures = [dict(row) for row in catalog.reader.exact_source_locations(ref.document_id, ref.source_id)]
    assert reader.query_local(request).excluded_candidates
    set_publication(catalog, ref, "2026-10-01")
    query = reader.query_local(request)
    assert query.status == "found" and query.matches == (ref,)
    assert query.excluded_candidates == ()
    resolved = SourceResolver(catalog).resolve(request)
    assert resolved.status is ResolutionStatus.REUSED_EQUIVALENT
    assert not resolved.download_required
    after = dict(catalog.reader.exact_source_version(ref.document_id))
    assert before["content_sha256"] == after["content_sha256"] == SHA
    assert before["metadata_json"] == after["metadata_json"]
    assert captures == [dict(row) for row in catalog.reader.exact_source_locations(ref.document_id, ref.source_id)]
    assert original.read_bytes() == BODY
    assert SourceResolver(catalog).resolve(replace(request, as_of_date="2026-09-30")).matches == ()


def test_import_reference_uses_committed_period_even_when_older_filing_is_eligible(lake):
    from company_wiki.source_catalog.acquisition import DownloadCandidate
    from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter

    catalog, _, ref, original, request = lake
    set_publication(catalog, ref, None)
    _write(original.parent, name="old-2024.pdf", body=OTHER, sha=OTHER_SHA,
           provider_id="doc-old", fiscal_year=2024, period_end="2024-12-31",
           filing_date="2025-02-20")
    catalog.scan()
    candidate = DownloadCandidate(candidate_id="selected", provider="sec", provider_document_id="doc-1",
                                  market="US", entity="Acme", title="2025",
                                  source_url="https://sec.gov/x/2025", document_kind="annual_report",
                                  form_type="10-K", filing_date="2026-02-20", fiscal_year=2025)
    broad_request = replace(request, fiscal_year=None)
    assert SourceResolver(catalog).resolve(broad_request).matches[0].fiscal_year == 2024
    assert CanonicalSourceWriter(catalog).source_ref_for_import(broad_request, candidate, SHA) == ref


@pytest.mark.parametrize("published", [None, "2027-01-01"])
@pytest.mark.parametrize("metadata", ["{}", '["incomplete legacy capture"]'])
def test_committed_reference_needs_no_semantic_selection_or_capture_receipt(lake, monkeypatch, published, metadata):
    from company_wiki.source_catalog.acquisition import DownloadCandidate
    from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter

    catalog, _, ref, _, request = lake
    set_publication(catalog, ref, published)
    with catalog.store.transaction() as connection:
        connection.execute("UPDATE documents SET metadata_json=? WHERE document_id=?", (metadata, ref.document_id))
    candidate = DownloadCandidate(candidate_id="selected", provider="sec", provider_document_id="doc-1",
                                  market="US", entity="Acme", title="2025",
                                  source_url="https://sec.gov/x/2025", document_kind="annual_report",
                                  form_type="10-K", filing_date="2026-02-20", fiscal_year=2025)

    def no_semantic_selection(*args, **kwargs):
        pytest.fail("committed source reference must not re-select business identity")

    monkeypatch.setattr(SourceResolver, "resolve", no_semantic_selection)
    assert CanonicalSourceWriter(catalog).source_ref_for_import(request, candidate, SHA) == ref


@pytest.mark.parametrize("missing_fields", [("market",), ("security_id",), ("market", "security_id")])
def test_company_owned_source_missing_auxiliary_identity_reuses_without_assertion(lake, missing_fields):
    catalog, reader, ref, original, request = lake
    row = catalog.reader.exact_source_version(ref.document_id)
    metadata = json.loads(row["metadata_json"])
    # Keep the source's actual company and period; remove only auxiliary identifiers.
    for field in missing_fields:
        metadata.pop(field, None)
        for payload in metadata.values():
            if isinstance(payload, dict):
                payload.pop(field, None)
    with catalog.store.transaction() as connection:
        connection.execute("UPDATE documents SET metadata_json=? WHERE document_id=?",
                           (json.dumps(metadata), ref.document_id))
    assert reader.query_local(request).matches == (ref,)
    result = SourceResolver(catalog).resolve(request)
    assert result.status is ResolutionStatus.REUSED_EQUIVALENT
    assert len(result.matches) == 1 and result.matches[0].content_sha256 == SHA
    assert not result.download_required and original.read_bytes() == BODY


def test_wrong_local_candidate_does_not_prohibit_fetching_correct_target(lake):
    catalog, reader, ref, _, request = lake
    row = catalog.reader.exact_source_version(ref.document_id)
    metadata = json.loads(row["metadata_json"])
    metadata["security_id"] = "OTHER"
    for payload in metadata.values():
        if isinstance(payload, dict) and "security_id" in payload:
            payload["security_id"] = "OTHER"
    with catalog.store.transaction() as connection:
        connection.execute("UPDATE documents SET metadata_json=? WHERE document_id=?", (json.dumps(metadata), ref.document_id))
    assert reader.query_local(request).matches == ()
    result = SourceResolver(catalog).resolve(replace(request, allow_download=True))
    assert result.matches == ()
    assert result.status is ResolutionStatus.MISSING
    assert result.download_required and result.download_allowed


def test_real_query_cli_emits_pathless_exclusion(tmp_path):
    config, _, row = cli_fixture(tmp_path)
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.service import SourceCatalog

    catalog = SourceCatalog(load_catalog_config(config))
    try:
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(row["document_id"], row["source_id"], row["content_sha256"])
        set_publication(catalog, ref, None)
    finally:
        catalog.close()
    completed = _run_query_cli(config, tmp_path)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["matches"] == [] and result["candidates"] == []
    diagnostic, = result["excluded_candidates"]
    assert diagnostic["qualification"]["publication_status"] == "unknown"
    assert str(tmp_path) not in json.dumps(result)
