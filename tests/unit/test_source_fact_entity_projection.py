"""Source facts qualify issuer identity independently of filesystem placement."""

from dataclasses import replace
import hashlib
import json

import pytest

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceVersionReader


def _fingerprint(path):
    info = path.stat()
    return hashlib.sha256(path.read_bytes()).hexdigest(), info.st_size, info.st_mtime_ns


@pytest.fixture
def lake(tmp_path):
    original = tmp_path / "companies" / "WRONG_FOLDER" / "arbitrary_name.txt"
    original.parent.mkdir(parents=True)
    original.write_bytes(
        b"CorrectIssuer business report. HK security 9896. FY2025 H1. Published 2025-08-26."
    )
    original.with_name(original.name + ".source.json").write_text(
        json.dumps({"ticker": "WRONG_FOLDER"}), encoding="utf-8"
    )
    before = _fingerprint(original)
    catalog = SourceCatalog(
        CatalogConfig(
            tmp_path,
            tmp_path / "catalog",
            (RootSpec("raw", tmp_path / "companies", "company_raw"),),
        )
    )
    try:
        registered = catalog.register_sources(
            root_id="raw", relative_paths={"WRONG_FOLDER/arbitrary_name.txt"}
        )
        assert not registered.errors and registered.files_seen == 2
        version = next(
            item
            for row in catalog.reader.query(limit=2)
            if (item := catalog.reader.exact_source_version(row["document_id"]))[
                "content_sha256"
            ]
            == before[0]
        )
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(version["document_id"], version["source_id"], before[0])
        facts = {
            "entity": "CorrectIssuer",
            "market": "HK",
            "security_id": "9896",
            "document_kind": "semi_annual_report",
            "fiscal_year": 2025,
            "fiscal_period": "H1",
            "published_date": "2025-08-26",
        }
        _record(catalog, ref, facts)
        assert reader.describe_version(ref)["display_name"] == "CorrectIssuer"
        assert (
            reader.open_version(ref, purpose="source_export").data
            == original.read_bytes()
        )
        request = SourceRequest(
            entity="CorrectIssuer",
            document_kind="semi_annual_report",
            market="HK",
            security_id="9896",
            fiscal_year=2025,
            fiscal_period="H1",
            as_of_date="2025-08-27",
            mode="exact",
            allow_download=False,
        )
        yield catalog, reader, ref, original, request
        assert _fingerprint(original) == before
    finally:
        catalog.close()


def _record(catalog, ref, facts):
    return catalog.record_source_facts(
        ref=ref,
        facts=facts,
        evidence={
            key: {
                "value": value,
                "locator": "synthetic:literal-header/" + key,
                "content_sha256": ref.content_sha256,
            }
            for key, value in facts.items()
        },
    )


def _matches(lake, port, **changes):
    catalog, reader, _ref, _original, request = lake
    request = replace(request, **changes)
    return (
        reader.query_local(request)
        if port == "query"
        else SourceResolver(catalog).resolve(request)
    ).matches


@pytest.mark.parametrize("port", ["query", "resolve"])
def test_verified_entity_matches_actual_same_original(lake, port):
    matches = _matches(lake, port)
    assert len(matches) == 1
    assert matches[0].content_sha256 == lake[2].content_sha256


@pytest.mark.parametrize("port", ["query", "resolve"])
@pytest.mark.parametrize(
    "changes",
    [
        {"entity": "WRONG_FOLDER"},
        {"entity": "UnrelatedIssuer"},
        {"market": "US"},
        {"security_id": "OTHER"},
        {"fiscal_year": 2024},
        {"fiscal_period": "H2"},
        {"as_of_date": "2025-08-25"},
    ],
)
def test_wrong_directory_identity_scope_or_date_does_not_match(lake, port, changes):
    assert not _matches(lake, port, **changes)


@pytest.mark.parametrize("port", ["query", "resolve"])
def test_verified_issuer_retains_proven_security_aliases(lake, port):
    from company_wiki.source_catalog.security_identity import (
        SecurityMasterStore,
        SecurityRecord,
    )

    catalog = lake[0]
    record = SecurityRecord(
        canonical_name="CorrectIssuer",
        market="HK",
        exchange="HKEX",
        ticker="9896",
        security_id="9896",
        aliases=("GenuineAlias",),
        active=True,
        source_name="synthetic-official-list",
        source_url="https://fixture.example/hk-list",
        source_record_id="9896",
        identifiers={},
    )
    SecurityMasterStore(catalog.config.catalog_dir / "security_master").write_market(
        "HK",
        [record],
        retrieved_at="2025-08-26T00:00:00Z",
        sources=(record.source_url,),
    )
    assert len(_matches(lake, port, entity="GenuineAlias")) == 1
    assert not _matches(lake, port, entity="WRONG_FOLDER")


@pytest.mark.parametrize("port", ["query", "resolve"])
def test_explicit_unknown_issuer_does_not_restore_directory_identity(lake, port):
    _record(lake[0], lake[2], {"entity": None, "security_id": None})
    assert not _matches(lake, port, entity="WRONG_FOLDER", security_id=None)
    assert not _matches(lake, port, entity="CorrectIssuer", security_id=None)


@pytest.mark.parametrize("port", ["query", "resolve"])
@pytest.mark.parametrize("visibility", ["shadow", "candidate"])
def test_invisible_facts_do_not_gain_entity_authority_and_legacy_fallback_survives(
    lake, port, visibility
):
    catalog = lake[0]
    with catalog.store.transaction() as connection:
        connection.execute(
            "UPDATE source_metadata_assertions SET visibility_state=?", (visibility,)
        )
    scope = {
        "market": None,
        "security_id": None,
        "fiscal_year": None,
        "fiscal_period": None,
    }
    assert not _matches(lake, port, entity="CorrectIssuer", **scope)
    assert len(_matches(lake, port, entity="WRONG_FOLDER", **scope)) == 1
    if port == "resolve":
        assert _matches(lake, port, entity="WRONG_FOLDER", **scope)[0].entity_ids == (
            "ticker:WRONG_FOLDER",
        )


@pytest.mark.parametrize("port", ["query", "resolve"])
def test_candidate_assertion_projection_is_loaded_once_for_entity_and_scope(
    lake, monkeypatch, port
):
    from company_wiki.source_catalog import resolver

    calls = []
    original = resolver._v2_assertion_metadata

    def observed(*args, **kwargs):
        calls.append(args[1])
        return original(*args, **kwargs)

    monkeypatch.setattr(resolver, "_v2_assertion_metadata", observed)
    assert len(_matches(lake, port)) == 1
    assert calls == [lake[2].source_id]


@pytest.mark.parametrize(
    "identity_field,value",
    [("display_name", "CorrectIssuer"), ("canonical_entity_id", "ent-correct")],
)
def test_entity_owner_prefers_explicit_identity_to_directory_hint(
    lake, identity_field, value
):
    resolver = SourceResolver(lake[0])
    document = {
        "entities": [{"name": "WRONG_FOLDER", "entity_id": "ticker:WRONG_FOLDER"}]
    }
    metadata = {
        identity_field: value,
        "company_name": "WRONG_FOLDER",
        "ticker": "WRONG_FOLDER",
    }
    assert resolver._entity_matches(value, document, metadata=metadata)
    assert not resolver._entity_matches("WRONG_FOLDER", document, metadata=metadata)
    metadata["_conflicted_fields"] = (identity_field,)
    assert not resolver._entity_matches(value, document, metadata=metadata)


def test_verified_handle_does_not_export_directory_as_canonical_identity(lake):
    handle = _matches(lake, "resolve")[0]
    assert handle.entity_ids == ()
    assert handle.to_dict()["entity_ids"] == []


def test_verified_handle_exports_only_existing_canonical_identity(tmp_path):
    original = tmp_path / "lake" / "original.txt"
    original.parent.mkdir()
    original.write_bytes(
        b"CorrectIssuer semi-annual report. Existing canonical entity ent-existing."
    )
    digest = _fingerprint(original)[0]
    sidecar = original.with_name(original.name + ".source.json")
    sidecar.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "canonical_entity_id": "ent-existing",
                "display_name": "CorrectIssuer",
                "market": "HK",
                "security_id": "9896",
                "document_kind": "semi_annual_report",
                "source_title": "CorrectIssuer H1 report",
                "fiscal_year": 2025,
                "fiscal_period": "H1",
                "period_end": "2025-06-30",
                "filing_date": "2025-08-26",
                "form_type": "interim_report",
                "provider": "hkex",
                "provider_document_id": "synthetic-report-1",
                "content_sha256": digest,
            }
        ),
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            tmp_path,
            tmp_path / "catalog",
            (
                RootSpec(
                    "raw",
                    original.parent,
                    "directory",
                    adapter_id="sidecar_filing_v1",
                    reusable_for_filing=True,
                ),
            ),
            ("directory",),
        )
    )
    try:
        registered = catalog.register_sources(
            root_id="raw", relative_paths={"original.txt"}
        )
        assert not registered.errors
        document = catalog.reader.query(limit=2)[0]
        version = catalog.reader.exact_source_version(document["document_id"])
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(version["document_id"], version["source_id"], digest)
        assert reader.describe_version(ref)["canonical_entity_id"] == "ent-existing"
        _record(catalog, ref, {"entity": "CorrectIssuer"})
        request = SourceRequest(
            entity="CorrectIssuer",
            document_kind="semi_annual_report",
            market="HK",
            security_id="9896",
            fiscal_year=2025,
            fiscal_period="H1",
            as_of_date="2025-08-27",
            mode="exact",
            allow_download=False,
        )
        result = SourceResolver(catalog).resolve(request)
        assert len(result.matches) == 1
        assert result.matches[0].entity_ids == ("ent-existing",)
    finally:
        catalog.close()
