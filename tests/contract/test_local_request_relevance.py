"""Unrelated obsolete source gaps cannot veto a genuinely absent requested period."""

import pytest
from helpers.source_fact_fixture import lake, html, imported, close
from company_wiki.source_catalog.local_reconcile import prepare_local_source
from company_wiki.source_catalog.resolver import SourceRequest


def request(**kwargs):
    return SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        fiscal_year=2026,
        form_type="10-K",
        as_of_date="2026-10-08",
        mode="exact",
        **kwargs,
    )


@pytest.mark.parametrize(
    "year,period,form", [(2022, "FY", "10-K"), (2026, "Q1", "10-Q")]
)
def test_actual_wrong_scope_is_excluded_before_irrelevant_date_error(
    tmp_path, year, period, form
):
    cat = lake(tmp_path)
    try:
        ref, path = imported(
            cat,
            html(
                year=year,
                period=period,
                form=form,
                end="June 30, 2022",
                transform="unknown:date-format",
            ),
        )
        result = prepare_local_source(cat, request())
        assert result["status"] == "not_found" and not result["blocks_download"]
        assert result["reason"] == "no_matching_local_period"
        assert result["download_events"] == 0
        assert (
            cat.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions")[0]
            == 1
        )
    finally:
        close(cat)


@pytest.mark.parametrize(
    "mutation", ["bad_date", "unknown_publication", "wrong_cik", "bad_sha"]
)
def test_genuine_target_gap_never_becomes_byte_absence(tmp_path, mutation):
    cat = lake(tmp_path)
    try:
        data = (
            html(end="June 30, 2026", transform="unknown:date-format")
            if mutation == "bad_date"
            else html(cik="99999" if mutation == "wrong_cik" else "12345")
        )
        ref, path = imported(cat, data)
        if mutation == "bad_sha":
            path.write_bytes(data + b"changed")
        result = prepare_local_source(cat, request())
        assert result["blocks_download"] and result["status"] in {
            "blocked",
            "unavailable",
        }
        assert result["download_events"] == 0
        assert result["reason"] != "no_matching_local_period"
    finally:
        close(cat)


def test_known_wrong_cache_year_is_not_an_exclusion_proof(tmp_path):
    cat = lake(tmp_path)
    try:
        ref, path = imported(cat, html())
        import json

        meta = {
            "company_id": "12345",
            "accession_number": "0000012345-26-000007",
            "primary_document": path.name,
            "form_type": "10-K",
            "report_date": "2026-06-30",
            "filing_date": "2026-07-30",
            "fiscal_year": 2025,
            "ingest_complete": True,
            "is_deleted": False,
            "files": [
                {
                    "name": path.name,
                    "sha256": ref.content_sha256,
                    "size": ref.byte_size,
                    "source_url": "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/"
                    + path.name,
                }
            ],
        }
        path.with_name("meta.json").write_text(json.dumps(meta))
        result = prepare_local_source(cat, request())
        assert (
            result["status"] == "ready"
            and result["source_ref"]["content_sha256"] == ref.content_sha256
        )
        from company_wiki.source_catalog.source_reader import SourceVersionReader

        manifest = SourceVersionReader(cat).describe_version(ref)
        assert (manifest["fiscal_year"], manifest["form_type"], manifest["title"]) == (
            2026,
            "10-K",
            "10-K",
        )
        assert result["download_events"] == 0
    finally:
        close(cat)


def test_unknown_title_is_description_not_eligibility(tmp_path):
    cat = lake(tmp_path)
    try:
        ref, path = imported(cat, html(title=""))
        import json

        meta = {
            "company_id": "12345",
            "accession_number": "0000012345-26-000007",
            "primary_document": path.name,
            "form_type": "10-K",
            "report_date": "2026-06-30",
            "filing_date": "2026-07-30",
            "ingest_complete": True,
            "is_deleted": False,
            "files": [
                {
                    "name": path.name,
                    "sha256": ref.content_sha256,
                    "size": ref.byte_size,
                    "source_url": "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/"
                    + path.name,
                }
            ],
        }
        path.with_name("meta.json").write_text(json.dumps(meta))
        result = prepare_local_source(cat, request())
        assert result["status"] == "ready" and result["download_events"] == 0
        from company_wiki.source_catalog.source_reader import SourceVersionReader

        assert SourceVersionReader(cat).describe_version(ref)["title"] is None
        assert (
            SourceVersionReader(cat).open_version(ref, purpose="source_export").data
            == path.read_bytes()
        )
    finally:
        close(cat)
