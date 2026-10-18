"""Market representation is a source projection, never a new issuer alias."""

from dataclasses import replace
import hashlib
import json
import shutil

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver
from company_wiki.source_catalog.source_reader import SourceVersionReader


def request(market="HK", code="09896"):
    return SourceRequest(entity="Acme", document_kind="annual_report", fiscal_year=2024,
                         as_of_date="2026-10-18", market=market, security_id=code)


@pytest.mark.parametrize("market,left,right,expected", [
    ("HK", "9896", "09896", "match"), ("HK", "09896", "9896", "match"),
    ("HK", "700", "00700", "match"), ("HK", "9896", "09897", "conflict"),
    ("HK", "009896", "09896", "conflict"),
    ("CN", "1", "000001", "match"), ("CN", "000001", "1", "match"),
    ("CN", "0000001", "000001", "conflict"),
    ("CN", "600001", "600002", "conflict"),
    ("US", "brk.b", "BRK.B", "match"), ("US", "BRK.B", "BRK-B", "conflict"),
    ("US", "BRK.B", "BRKB", "conflict"), ("US", "0ABC", "ABC", "conflict"),
    (None, "001", "1", "conflict"), (None, "Foo", "foo", "conflict"),
    (None, "SAME-ID", "SAME-ID", "match"),
    ("HK", "98 96", "9896", "conflict"),
    ("HK", "９８９６", "09896", "conflict"),
])
def test_strict_match_is_market_qualified(market, left, right, expected):
    assert SourceResolver._identity_matches(request(market, left),
        {"market": market, "security_id": right}) == expected


@pytest.mark.parametrize("metadata", [
    {"market": "CN", "security_id": "09896"},
    {"market": None, "security_id": "9896"},
    {"market": "HK", "security_id": "9896", "_conflicted_fields": ["security_id"]},
])
def test_known_market_is_not_borrowed_from_request_or_over_conflict(metadata):
    assert SourceResolver._identity_matches(request(), metadata) == "conflict"


@pytest.fixture
def indexed(tmp_path, request):
    owned = tmp_path / "identity-owned"
    raw = owned / "lake" / "Acme" / "annual.pdf"
    raw.parent.mkdir(parents=True)
    sentinel = tmp_path / "sentinel.bin"
    sentinel.write_bytes(b"existing independent baseline")
    body = b"%PDF-1.7\nSynthetic Acme annual original, never parsed.\n"
    raw.write_bytes(body)
    facts = {"schema_version": "1.0", "canonical_entity_id": "Acme",
        "display_name": "Acme", "market": "HK", "security_id": getattr(request, "param", "9896"),
        "document_kind": "annual_report", "source_title": "Acme annual report",
        "fiscal_year": 2024, "period_end": "2024-12-31", "filing_date": "2025-03-20",
        "form_type": "annual", "provider": "hkex", "provider_document_id": "acme-2024",
        "source_url": "https://example.invalid/acme-annual.pdf",
        "content_sha256": hashlib.sha256(body).hexdigest()}
    raw.with_name(raw.name + ".source.json").write_text(json.dumps(facts), encoding="utf8")
    catalog = SourceCatalog(CatalogConfig(owned, owned / "catalog", (
        RootSpec("raw", owned / "lake", "directory", adapter_id="sidecar_filing_v1",
                 reusable_for_filing=True),), ("directory",)))
    try:
        catalog.scan()
        row = catalog.reader.fetchone("SELECT document_id,primary_source_id AS source_id FROM documents")
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(row["document_id"], row["source_id"], facts["content_sha256"])
        yield catalog, reader, ref, raw, facts
    finally:
        catalog.close()
        shutil.rmtree(owned)
        assert not owned.exists()
        assert sentinel.read_bytes() == b"existing independent baseline"
        sentinel.unlink()


def test_candidate_projects_canonical_identity_without_mutating_observed_facts(indexed):
    catalog, reader, ref, raw, facts = indexed
    original_sidecar = raw.with_name(raw.name + ".source.json").read_bytes()
    manifest = reader.describe_version(ref)
    candidate = reader.describe_candidate(ref)
    assert candidate["security_id"] == "09896"
    assert candidate["market"] == "HK"
    assert candidate["source_ref"]["content_sha256"] == facts["content_sha256"]
    assert manifest["security_id"] == reader.describe_version(ref)["security_id"] == "9896"
    assert raw.with_name(raw.name + ".source.json").read_bytes() == original_sidecar
    for code in ("9896", "09896"):
        assert SourceResolver(catalog).resolve(request(code=code)).matches
        found = reader.query_local(request(code=code))
        assert found.matches == (ref,)
        assert reader.describe_candidate(found.matches[0])["security_id"] == "09896"


@pytest.mark.parametrize("changes", [
    {"security_id": "09897"}, {"market": "CN"}, {"fiscal_year": 2023},
    {"as_of_date": "2025-03-19"},
])
def test_projection_keeps_existing_company_period_and_asof_filters(indexed, changes):
    catalog, _, _, _, _ = indexed
    assert not SourceResolver(catalog).resolve(replace(request(), **changes)).matches


@pytest.mark.parametrize("published", [None, "2027-01-01"])
def test_canonical_code_does_not_make_unknown_or_future_publication_historical(indexed, published):
    catalog, reader, ref, _, _ = indexed
    catalog.record_source_facts(ref=ref, facts={"published_date": published}, evidence={
        "published_date": {"value": published, "locator": "fixture:publication"},
    })
    assert not reader.query_local(request()).matches
    assert not SourceResolver(catalog).resolve(request()).matches


def test_current_verified_identity_projects_without_rewriting_its_observed_value(indexed):
    catalog, reader, ref, _, _ = indexed
    catalog.record_source_facts(ref=ref, facts={"security_id": "388"}, evidence={
        "security_id": {"value": "388", "locator": "fixture:current-issuer-code"},
    })
    assert reader.describe_version(ref)["security_id"] == "388"
    assert reader.describe_candidate(ref)["security_id"] == "00388"
    assert reader.query_local(request(code="00388")).matches == (ref,)
    assert not reader.query_local(request(code="09896")).matches


@pytest.mark.parametrize("market,observed,canonical", [
    ("HK", "388", "00388"), ("CN", "1", "000001"),
    ("US", "brk.b", "BRK.B"), ("US", "BRK-B", "BRK-B"),
    (None, "001", "001"), (None, "ABC.X", "ABC.X"),
])
def test_candidate_projection_uses_own_market_without_discovery_aliases(indexed, market, observed, canonical):
    catalog, reader, ref, _, _ = indexed
    facts = {"market": market, "security_id": observed}
    catalog.record_source_facts(ref=ref, facts=facts, evidence={
        key: {"value": value, "locator": "fixture:current-market-code"}
        for key, value in facts.items()
    })
    assert reader.describe_version(ref)["security_id"] == observed
    assert reader.describe_candidate(ref)["security_id"] == canonical
