"""Company existence must be proved or refused when its real scan budget ends."""

import json
import sqlite3

import pytest

from company_wiki.source_catalog import company_source_index as index_module
from company_wiki.source_catalog.company_source_index import (
    CompanyIdentity,
    CompanySourceIndex,
    CompanySourceIndexError,
    CompanySourceIndexRequest,
)
from contract.test_source_catalog_acquisition import _catalog


def _dirty_unrelated_rows(catalog, count):
    # A normal SQLite writer marks these dirty. The query must qualify them
    # until the source owner can refresh its derived projection.
    connection = sqlite3.connect(catalog.config.database_path)
    try:
        connection.executemany(
            """INSERT INTO documents
               (document_id, title, source_type, document_kind, published_date, source_status,
                metadata_priority, metadata_json, first_seen_at, last_seen_at)
               VALUES (?, ?, 'regulatory_filing', 'annual_report', '2026-04-01', 'active',
                       0, ?, '2026-04-01', '2026-04-01')""",
            [(f"before-issuer-{number:05d}", f"Other {number}", json.dumps({
                "acquisition": {"company_name": f"Other {number}"},
            })) for number in range(count)],
        )
        connection.commit()
        assert connection.execute("SELECT COUNT(*) FROM source_identity_dirty").fetchone()[0] == count
    finally:
        connection.close()


def _quarterly_request(entity="Acme"):
    return CompanySourceIndexRequest(
        company=CompanyIdentity(entity), as_of_date="2026-08-01", document_kinds=("quarterly_report",),
    )


def test_known_company_with_no_matching_kind_is_found_past_first_dirty_page(tmp_path, monkeypatch):
    catalog = _catalog(tmp_path, with_source=True)
    try:
        index = CompanySourceIndex(catalog)
        request = _quarterly_request()
        assert index.page(request)["status"] == "ok"
        _dirty_unrelated_rows(catalog, 500)
        authority = index._resolver.issuer_identity_tokens
        calls = []

        def observe_identity(entity):
            calls.append(entity)
            return authority(entity)

        monkeypatch.setattr(index._resolver, "issuer_identity_tokens", observe_identity)
        result = index.page(request)
        assert result["status"] == "ok" and result["sources"] == []
        assert calls == ["Acme"]
    finally:
        catalog.close()


def test_company_existence_scan_distinguishes_exhausted_budget_from_exact_eof(tmp_path, monkeypatch):
    catalog = _catalog(tmp_path, with_source=True)
    try:
        _dirty_unrelated_rows(catalog, 3)
        monkeypatch.setattr(index_module, "MAX_CANDIDATES", 3)
        index = CompanySourceIndex(catalog)
        with pytest.raises(CompanySourceIndexError) as caught:
            index.page(_quarterly_request())
        assert (caught.value.status, caught.value.reason) == ("unavailable", "candidate_budget_exceeded")

        absent = index.page(_quarterly_request("No such issuer"))
        assert absent["status"] == "not_found" and absent["reason"] == "company_not_indexed"
    finally:
        catalog.close()
