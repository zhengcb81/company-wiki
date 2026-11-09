"""Precise source queries scale with relevant candidates, not the whole lake."""

import json
import sqlite3

import pytest

from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.source_reader import (
    SourceReadError,
    SourceVersionReader,
)
from contract.test_source_version_reader import _fixture


def request(entity="Acme", security="ACME"):
    return SourceRequest(
        entity=entity,
        document_kind="annual_report",
        as_of_date="2026-10-21",
        market="US",
        security_id=security,
        fiscal_year=2025,
    )


def add_noise(catalog, count):
    with catalog.store.transaction() as conn:
        conn.executemany(
            """INSERT INTO documents
            (document_id,title,source_status,source_type,document_kind,metadata_priority,
             metadata_json,first_seen_at,last_seen_at,published_date)
            VALUES (?,?,'active','file','annual_report',10,?,'2026-01-01','2026-01-01','2026-03-01')""",
            (
                (
                    f"unrelated-{i:06}",
                    f"Unrelated {i:06}",
                    json.dumps(
                        {
                            "acquisition": {
                                "display_name": "Unrelated Industries",
                                "security_id": "OTHER",
                                "market": "US",
                                "fiscal_year": 2025,
                            }
                        }
                    ),
                )
                for i in range(count)
            ),
        )


@pytest.mark.parametrize("count", (19_999, 20_000, 20_001))
def test_exact_query_does_not_project_unrelated_same_kind_documents(
    tmp_path, monkeypatch, count
):
    catalog, _, _, ids = _fixture(tmp_path)
    try:
        add_noise(catalog, count)
        old = catalog.query_filing_candidates
        projected = []

        def traced(**kwargs):
            rows = old(**kwargs)
            projected.extend(d["document_id"] for d in rows)
            return rows

        monkeypatch.setattr(catalog, "query_filing_candidates", traced)
        result = SourceVersionReader(catalog).query_local(request())
        assert result.status == "found"
        assert result.matches[0].document_id == ids["document_id"]
        assert len(projected) <= 2
    finally:
        catalog.close()


def test_candidate_budget_exact_eof_is_not_overflow():
    from types import SimpleNamespace
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    class Catalog:
        def query_filing_candidates(self, **kwargs):
            start = (
                int(kwargs.get("after_document_id") or "-1") + 1
                if "after_document_id" in kwargs
                else kwargs["offset"]
            )
            return [
                {"document_id": str(i)}
                for i in range(start, min(20_000, start + kwargs["limit"]))
            ]

    reader = object.__new__(SourceVersionReader)
    reader.catalog = Catalog()
    assert (
        len(
            list(
                reader._candidate_pages(
                    SimpleNamespace(
                        entity="Acme",
                        document_kind="annual_report",
                        as_of_date="2026-10-21",
                    )
                )
            )
        )
        == 20_000
    )


def test_true_related_candidate_overflow_is_still_bounded():
    from types import SimpleNamespace

    class Catalog:
        def query_filing_candidates(self, **kwargs):
            start = (
                int(kwargs.get("after_document_id") or "-1") + 1
                if "after_document_id" in kwargs
                else kwargs["offset"]
            )
            return [
                {"document_id": str(i)}
                for i in range(start, min(20_001, start + kwargs["limit"]))
            ]

    reader = object.__new__(SourceVersionReader)
    reader.catalog = Catalog()
    with pytest.raises(SourceReadError, match="candidate_budget_exceeded"):
        list(
            reader._candidate_pages(
                SimpleNamespace(
                    entity="Acme",
                    document_kind="annual_report",
                    as_of_date="2026-10-21",
                )
            )
        )


def corrected_assertion(catalog, ids):
    with catalog.store.transaction() as conn:
        conn.execute(
            """INSERT INTO source_metadata_assertions
            (assertion_id,source_id,document_id,content_sha256,evidence_basis,evidence_json,
             decision,created_at,created_by,schema_version,visibility_state,entity,
             market,security_id,fiscal_year,period_end)
            VALUES ('corrected',?,?,?,'verified_bytes','{}','verified',
                    '2099-01-01','test','2.0','active','Corrected Name','US','ACME',2025,'2025-12-31')""",
            (ids["source_id"], ids["document_id"], ids["content_sha256"]),
        )


def test_authoritative_correction_not_directory_name_controls_candidates(tmp_path):
    catalog, _, _, ids = _fixture(tmp_path)
    try:
        corrected_assertion(catalog, ids)
        with catalog.store.transaction() as conn:
            conn.execute(
                "UPDATE source_metadata_assertions SET security_id='BETA' WHERE assertion_id='corrected'"
            )
        reader = SourceVersionReader(catalog)
        assert (
            reader.query_local(request("Corrected Name", security="BETA")).status
            == "found"
        )
        assert (
            reader.query_local(request("Acme", security="BETA")).status == "not_found"
        )
        assert (
            reader.query_local(request("ＢＥＴＡ", security="BETA")).status == "found"
        )
    finally:
        catalog.close()


def test_external_sqlite_correction_is_dirty_and_readable_without_projection_write(
    tmp_path,
):
    catalog, _, _, ids = _fixture(tmp_path)
    try:
        corrected_assertion(catalog, ids)
        with sqlite3.connect(catalog.config.database_path) as conn:
            conn.execute(
                "UPDATE source_metadata_assertions SET entity='A Different Name' WHERE assertion_id='corrected'"
            )
        before = catalog.reader.fetchall("SELECT * FROM source_identity_dirty")
        assert before
        assert (
            SourceVersionReader(catalog).query_local(request("A Different Name")).status
            == "found"
        )
        assert [
            tuple(row)
            for row in catalog.reader.fetchall("SELECT * FROM source_identity_dirty")
        ] == [tuple(row) for row in before]
        with catalog.store.transaction():
            pass
        assert not catalog.reader.fetchall("SELECT * FROM source_identity_dirty")
        assert (
            SourceVersionReader(catalog).query_local(request("A Different Name")).status
            == "found"
        )
    finally:
        catalog.close()


def test_alias_expansion_uses_existing_resolver_authority(tmp_path):
    from company_wiki.source_catalog.security_identity import SecurityMasterStore, SecurityRecord

    catalog, _, _, ids = _fixture(tmp_path)
    try:
        reader = SourceVersionReader(catalog)
        alias_request = request("Alias")
        assert reader.query_local(alias_request).status == "not_found"

        master = SecurityMasterStore(catalog.config.catalog_dir / "security_master")
        record = SecurityRecord(
            canonical_name="Acme",
            market="US",
            exchange="NASDAQ",
            ticker="ACME",
            security_id="ACME",
            aliases=("Alias",),
            active=True,
            source_name="sec",
            source_url="https://www.sec.gov/files/company_tickers.json",
            source_record_id="fixture-issuer",
            identifiers={},
        )
        master.write_market(
            "US", (record,), retrieved_at="2026-10-20T00:00:00Z", sources=("sec",),
        )

        result = reader.query_local(alias_request)
        assert result.status == "found"
        assert [match.document_id for match in result.matches] == [ids["document_id"]]
    finally:
        catalog.close()


def test_candidate_projection_uses_index_not_unrelated_metadata(tmp_path):
    catalog, _, _, _ = _fixture(tmp_path)
    try:
        plan = catalog.reader.fetchall(
            "EXPLAIN QUERY PLAN SELECT document_id FROM source_identity_tokens WHERE token=?",
            ("acme",),
        )
        assert any("idx_source_identity_token" in row["detail"] for row in plan)
    finally:
        catalog.close()


def test_legacy_read_only_catalog_without_index_keeps_same_query_semantics(tmp_path):
    catalog, _, _, _ = _fixture(tmp_path)
    try:
        with sqlite3.connect(catalog.config.database_path) as conn:
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'source_identity_%'"
            ).fetchall():
                conn.execute('DROP TRIGGER "' + row[0] + '"')
            conn.execute("DROP TABLE source_identity_dirty")
            conn.execute("DROP TABLE source_identity_tokens")
        assert (
            SourceVersionReader(catalog).query_local(request("ＡＣＭＥ")).status
            == "found"
        )
        assert not catalog.reader.fetchone(
            "SELECT 1 FROM sqlite_master WHERE name='source_identity_tokens'"
        )
    finally:
        catalog.close()


def test_one_source_assertion_reaches_all_document_references(tmp_path):
    catalog, _, _, ids = _fixture(tmp_path)
    try:
        with catalog.store.transaction() as conn:
            conn.execute(
                """INSERT INTO documents
                (document_id,title,source_status,source_type,document_kind,metadata_priority,
                 metadata_json,first_seen_at,last_seen_at,published_date,primary_source_id)
                VALUES ('second-reference','Second reference','active','file','annual_report',10,
                        '{}','2026-01-01','2026-01-01','2026-03-01',?)""",
                (ids["source_id"],),
            )
        corrected_assertion(catalog, ids)
        result = SourceVersionReader(catalog).query_local(request("Corrected Name"))
        assert result.status == "ambiguous"
        assert {ref.document_id for ref in result.matches} == {
            ids["document_id"],
            "second-reference",
        }
    finally:
        catalog.close()


def test_external_entity_repair_marks_its_existing_references_dirty(tmp_path):
    catalog, _, _, ids = _fixture(tmp_path)
    try:
        # A bare SQLite repair may temporarily have foreign_keys disabled.
        with sqlite3.connect(catalog.config.database_path) as conn:
            conn.execute(
                "INSERT INTO document_entities VALUES (?, 'repaired-entity', 1, 'repair')",
                (ids["document_id"],),
            )
        with catalog.store.transaction():
            pass
        assert not catalog.reader.fetchall("SELECT * FROM source_identity_dirty")
        with sqlite3.connect(catalog.config.database_path) as conn:
            conn.execute(
                "INSERT INTO entities VALUES ('repaired-entity', 'Recovered Name', 'company')"
            )
        rows = catalog.query_filing_candidates(
            document_kind="annual_report",
            source_statuses=("active",),
            identity_tokens=("recoveredname",),
        )
        assert [row["document_id"] for row in rows] == [ids["document_id"]]
    finally:
        catalog.close()


@pytest.mark.parametrize("value", (123, ["Odd Name"], {"label": "Odd Name"}))
def test_candidate_superset_preserves_existing_resolver_string_projection(value):
    from company_wiki.source_catalog.identity_candidates import metadata_identity_tokens
    from company_wiki.source_catalog.security_identity import _normalize_text

    # A candidate index is not the place to silently change how the resolver
    # treats malformed declaration shapes. Final qualification still owns it.
    assert _normalize_text(str(value)) in metadata_identity_tokens(
        {"acquisition": {"display_name": value}}
    )
