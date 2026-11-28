"""Latest selection through the portable public source-version reader."""

from dataclasses import replace

from company_wiki.source_catalog import SourceRequest, SourceVersionReader
from contract.test_source_version_reader import BODY, OTHER, OTHER_SHA, _fixture, _write


def _request(as_of_date):
    return SourceRequest(
        entity="Acme", market="US", security_id="ACME",
        document_kind="annual_report", form_type="10-K",
        as_of_date=as_of_date, mode="latest_as_of",
    )


def test_latest_revision_keeps_as_of_and_reads_exact_original(tmp_path):
    catalog, paths, _, _ = _fixture(tmp_path)
    original = paths[0]
    revision = _write(
        original.parent, name="amendment.pdf", body=OTHER, sha=OTHER_SHA,
        provider_id="doc-2", filing_date="2026-04-15",
    )
    try:
        catalog.scan()
        reader = SourceVersionReader(catalog)
        request = _request("2026-08-10")
        latest = reader.query_local(request)
        assert latest.status == "found"
        (ref,) = latest.matches
        assert reader.open_version(ref, purpose="filing_reuse").data == OTHER

        prior = reader.query_local(replace(request, as_of_date="2026-02-28"))
        assert prior.status == "found"
        (ref,) = prior.matches
        assert reader.open_version(ref, purpose="filing_reuse").data == BODY

        assert reader.query_local(replace(request, as_of_date="2026-01-01")).status == "not_found"
        assert original.read_bytes() == BODY and revision.read_bytes() == OTHER
    finally:
        catalog.close()


def test_legacy_dated_ties_stable_when_scan_order_changes(tmp_path):
    catalog, paths, _, _ = _fixture(tmp_path)
    original = paths[0]
    _write(original.parent, name="000-first-name.pdf", body=OTHER,
           sha=OTHER_SHA, provider_id="doc-2")
    try:
        catalog.scan()
        reader = SourceVersionReader(catalog)
        request = _request("2026-08-10")
        first = reader.query_local(request)
        assert first.status == "found"
        assert first.matches[0].content_sha256 == OTHER_SHA
        catalog.scan()
        assert reader.query_local(request).matches == first.matches
    finally:
        catalog.close()
