from __future__ import annotations

import hashlib

import pytest


_BABA_CIK = "0001577552"
_BILI_CIK = "0001723690"


def _verified_html(value: str):
    from company_wiki.source_contract.source_version import (
        SourceByteVerifier,
        SourceRef,
        VerifiedContent,
    )

    raw = value.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    ref = SourceRef(
        document_id=f"urn:company-wiki:document:sha256:{digest}",
        source_id=f"urn:company-wiki:source:sha256:{digest}",
        content_sha256=digest,
        byte_size=len(raw),
        mime_type="text/html",
    )
    verifier = SourceByteVerifier(retain_bytes=True)
    verifier.update(raw)
    return VerifiedContent.from_observation(
        ref,
        verifier.observe(),
        read_at="2026-11-09T12:00:00Z",
        policy_sha256="0" * 64,
        source_read_policy_sha256="1" * 64,
    )


def _master(tmp_path, *, omit_hk_listing_ticker_aliases: bool = False):
    from company_wiki.source_catalog.security_identity import (
        SecurityMasterStore,
        SecurityRecord,
    )

    store = SecurityMasterStore(tmp_path / "security_master")
    store.write_market(
        "US",
        (
            SecurityRecord(
                canonical_name="Alibaba Group Holding Limited",
                market="US", exchange="NYSE", ticker="BABA", security_id="BABA",
                aliases=("Alibaba",), active=True, source_name="sec_nasdaq",
                source_url="https://www.sec.gov/files/company_tickers.json",
                source_record_id=_BABA_CIK, identifiers={"cik": _BABA_CIK},
            ),
            SecurityRecord(
                canonical_name="Bilibili Inc.", market="US", exchange="NASDAQ",
                ticker="BILI", security_id="BILI", aliases=("Bilibili",), active=True,
                source_name="sec_nasdaq",
                source_url="https://www.sec.gov/files/company_tickers.json",
                source_record_id=_BILI_CIK, identifiers={"cik": _BILI_CIK},
            ),
        ),
        retrieved_at="2026-11-09T00:00:00Z",
        sources=("https://www.sec.gov/files/company_tickers.json",),
    )
    store.write_market(
        "HK",
        (
            SecurityRecord(
                canonical_name="Alibaba Group Holding Limited",
                market="HK", exchange="HKEX", ticker="09988", security_id="09988",
                aliases=("Alibaba Group",) if omit_hk_listing_ticker_aliases else ("BABA", "Alibaba"),
                active=True, source_name="hkex",
                source_url="https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json",
                source_record_id="7353", identifiers={},
            ),
            SecurityRecord(
                canonical_name="Alibaba Group Holding Limited",
                market="HK", exchange="HKEX", ticker="89988", security_id="89988",
                aliases=("Alibaba Group",) if omit_hk_listing_ticker_aliases else ("BABA-WR", "Alibaba"),
                active=True, source_name="hkex",
                source_url="https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json",
                source_record_id="7353-rmb", identifiers={},
            ),
            SecurityRecord(
                canonical_name="Bilibili Inc.", market="HK", exchange="HKEX",
                ticker="09626", security_id="09626", aliases=("Bilibili",), active=True,
                source_name="hkex",
                source_url="https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json",
                source_record_id="15753", identifiers={},
            ),
        ),
        retrieved_at="2026-11-09T00:00:00Z",
        sources=("https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json",),
    )
    return store


def _metadata(cik: str, accession: str, filename: str) -> dict[str, str]:
    accession_path = accession.replace("-", "")
    return {
        "form_type": "20-F",
        "published_date": "2026-05-20",
        "market": "US",
        "document_kind": "annual_report",
        "provider": "official",
        "provider_document_id": accession,
        "source_url": (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{accession_path}/{filename}"
        ),
    }


def test_sec_20f_table_links_exact_market_listings_for_two_issuers(tmp_path):
    from company_wiki.source_catalog.security_identity import SecurityIdentityResolver
    from company_wiki.source_catalog.security_listing_evidence import (
        build_sec_20f_listing_evidence,
    )

    store = _master(tmp_path)
    master = store.load(markets=("HK", "US"))
    cases = (
        (
            _BABA_CIK,
            "0000950170-25-090161",
            "baba-20250331.htm",
            """<html><body><table>
            <tr><th>Title of each class</th><th>Trading Symbol(s)</th>
            <th>Name of each exchange on which registered</th></tr>
            <tr><td>Ordinary Shares, par value US$0.000003125 per share</td>
            <td>9988 (HKD Counter) 89988 (RMB Counter)</td>
            <td>The Stock Exchange of Hong Kong Limited</td></tr>
            <tr><td>American Depositary Shares, each representing eight Ordinary Shares</td>
            <td>BABA</td><td>New York Stock Exchange</td></tr>
            <tr><td>4.50% Senior Notes due 2034</td><td>BABA</td>
            <td>New York Stock Exchange</td></tr>
            </table></body></html>""",
            {"BABA", "09988", "89988"},
        ),
        (
            _BILI_CIK,
            "0001193125-26-157842",
            "d91984d20f.htm",
            """<html><body><table>
            <tr><th>Title of Each Class</th><th></th><th>Trading Symbol(s)</th>
            <th></th><th>Name of Each Exchange on Which Registered</th></tr>
            <tr><td>American depositary shares, each representing one Class Z ordinary share</td>
            <td></td><td>BILI</td><td></td><td>Nasdaq Global Select Market</td></tr>
            <tr><td>Class Z ordinary shares, par value US$0.0001 per share</td>
            <td></td><td>9626</td><td></td><td>The Stock Exchange of Hong Kong Limited</td></tr>
            </table></body></html>""",
            {"BILI", "09626"},
        ),
    )

    for cik, accession, filename, html, expected in cases:
        evidence = build_sec_20f_listing_evidence(
            _verified_html(html),
            metadata=_metadata(cik, accession, filename),
            master=master,
        )
        store._write_issuer_link(evidence)
        assert {item.security_id for item in evidence.listings} == expected
        assert len({item.market for item in evidence.listings}) == 2
        assert evidence.source_sha256 == hashlib.sha256(html.encode("utf-8")).hexdigest()

    linked_master = store.load(markets=("HK", "US"))
    resolver = SecurityIdentityResolver(linked_master)
    for query, market in (("BABA", "US"), ("09988", "HK"), ("BILI", "US"), ("09626", "HK")):
        result = resolver.identify(query, market=market).resolved
        assert result is not None and result.issuer_link_id

    baba_us = resolver.identify("BABA", market="US").resolved
    baba_hk = resolver.identify("09988", market="HK").resolved
    bili_us = resolver.identify("BILI", market="US").resolved
    bili_hk = resolver.identify("09626", market="HK").resolved
    assert baba_us and baba_hk and baba_us.issuer_link_id == baba_hk.issuer_link_id
    assert bili_us and bili_hk and bili_us.issuer_link_id == bili_hk.issuer_link_id
    assert baba_us.issuer_link_id != bili_us.issuer_link_id

    # A source-market code cannot override a contradictory foreign issuer
    # alias.  This used to select Bilibili by 09626 even when the query said
    # BABA because the same-market security id was considered independently.
    assert store.issuer_identity_tokens(
        "BABA", market="HK", security_id="09626",
    ) == ()


def test_sec_provider_20f_can_establish_links_from_verified_sec_filing(tmp_path):
    from company_wiki.source_catalog.security_listing_evidence import (
        ListingEvidenceError,
        build_sec_20f_listing_evidence,
    )

    store = _master(tmp_path)
    master = store.load(markets=("HK", "US"))
    html = """<html><body>
    <ix:nonNumeric name="dei:EntityCentralIndexKey">1577552</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentType">20-F</ix:nonNumeric>
    <table>
    <tr><th>Title of each class</th><th>Trading Symbol(s)</th>
    <th>Name of each exchange on which registered</th></tr>
    <tr><td>Ordinary Shares</td><td>9988 89988</td>
    <td>The Stock Exchange of Hong Kong Limited</td></tr>
    <tr><td>American Depositary Shares</td><td>BABA</td>
    <td>New York Stock Exchange</td></tr>
    </table></body></html>"""
    content = _verified_html(html)
    metadata = {
        **_metadata(_BABA_CIK, "0000950170-25-090161", "baba-20250331.htm"),
        "provider": "sec",
    }

    evidence = build_sec_20f_listing_evidence(
        content, metadata=metadata, master=master,
    )

    assert evidence is not None
    assert {listing.security_id for listing in evidence.listings} == {"BABA", "09988", "89988"}
    unsupported_provider = {**metadata, "provider": "third_party"}
    with pytest.raises(ListingEvidenceError, match="official US filing source"):
        build_sec_20f_listing_evidence(
            content, metadata=unsupported_provider, master=master,
        )


def test_sec_provider_canonical_writer_registers_verified_listing_link(
    tmp_path_factory, monkeypatch,
):
    import hashlib
    from pathlib import Path

    from company_wiki.source_catalog import (
        CanonicalSourceWriter,
        DownloadCandidate,
        DownloadReceipt,
        SourceRequest,
    )
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec
    from company_wiki.source_catalog.security_identity import SecurityIdentityResolver
    from company_wiki.source_catalog.service import SourceCatalog

    tmp_path = tmp_path_factory.mktemp("sec")
    html = b"""<html><body>
    <ix:nonNumeric name="dei:EntityCentralIndexKey">1577552</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentType">20-F</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentFiscalYearFocus">2025</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentFiscalPeriodFocus">FY</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentPeriodEndDate">2025-03-31</ix:nonNumeric>
    <table>
    <tr><th>Title of each class</th><th>Trading Symbol(s)</th>
    <th>Name of each exchange on which registered</th></tr>
    <tr><td>Ordinary Shares</td><td>9988 (HKD Counter) 89988 (RMB Counter)</td>
    <td>The Stock Exchange of Hong Kong Limited</td></tr>
    <tr><td>American Depositary Shares</td><td>BABA</td>
    <td>New York Stock Exchange</td></tr>
    </table></body></html>"""
    metadata = _metadata(_BABA_CIK, "0000950170-25-090161", "baba-20250331.htm")
    project_root = tmp_path / "project"
    company_root = project_root / "companies"
    company_root.mkdir(parents=True)
    catalog_dir = project_root / ".source_catalog"
    security_master = _master(catalog_dir)
    catalog = SourceCatalog(CatalogConfig(
        project_root=project_root,
        catalog_dir=catalog_dir,
        roots=(RootSpec("company_raw", company_root, "company_raw"),),
    ))
    staging_root = catalog_dir / "staging"
    staged = staging_root / "sec-20f.html"
    staged.parent.mkdir(parents=True)
    staged.write_bytes(html)
    request = SourceRequest(
        entity="Alibaba Group Holding Limited",
        market="US",
        security_id="BABA",
        document_kind="annual_report",
        fiscal_year=2025,
        fiscal_period="FY",
        as_of_date="2026-11-09",
        allow_download=True,
    )
    candidate = DownloadCandidate(
        candidate_id="sec:" + metadata["provider_document_id"],
        provider="sec",
        provider_document_id=metadata["provider_document_id"],
        market="US",
        entity="Alibaba Group Holding Limited",
        title="Alibaba FY2025 Form 20-F",
        source_url=metadata["source_url"],
        document_kind="annual_report",
        filing_date=metadata["published_date"],
        fiscal_year=2025,
        form_type="20-F",
        fiscal_period="FY",
        language="en",
        security_id="BABA",
    )
    receipt = DownloadReceipt(
        candidate_id=candidate.candidate_id,
        provider=candidate.provider,
        provider_document_id=candidate.provider_document_id,
        source_url=candidate.source_url,
        staged_path=str(staged),
        content_sha256=hashlib.sha256(html).hexdigest(),
        byte_size=len(html),
        mime_type="text/html",
        retrieved_at="2026-11-09T12:00:00Z",
        http_status=200,
        adapter_name="dayu-sec",
        adapter_version="1.0.0",
    )

    imported = CanonicalSourceWriter(catalog, staging_root=staging_root).import_staged(
        request, candidate, receipt,
    )
    resolver = SecurityIdentityResolver(security_master.load(markets=("HK", "US")))
    baba_us = resolver.identify("BABA", market="US").resolved
    baba_hk = resolver.identify("09988", market="HK").resolved
    assert baba_us is not None and baba_hk is not None
    assert baba_us.issuer_link_id is not None
    assert baba_us.issuer_link_id == baba_hk.issuer_link_id

    registered = catalog.register_sec_20f_listing_link(
        document_id=imported.source_ref.document_id,
        source_id=imported.source_ref.source_id,
        content_sha256=imported.source_ref.content_sha256,
    )

    assert registered["status"] == "already_registered"
    assert registered["listing_count"] == 3
    assert registered["markets"] == ["HK", "US"]
    assert registered["content_sha256"] == hashlib.sha256(html).hexdigest()
    assert Path(imported.canonical_path).read_bytes() == html

    # A derived-link outage must not turn a successfully committed original
    # into a failed acquisition or remove the immutable bytes.
    from dataclasses import replace

    def fail_projection(**_kwargs):
        raise OSError("temporary derived-cache failure")

    monkeypatch.setattr(catalog, "register_sec_20f_listing_link", fail_projection)
    staged.write_bytes(html)
    replay = CanonicalSourceWriter(catalog, staging_root=staging_root).import_staged(
        request, candidate, replace(receipt, staged_path=str(staged)),
    )
    assert replay.status.value == "deduplicated_after_download"
    assert Path(imported.canonical_path).read_bytes() == html


def test_sec_20f_link_requires_verified_bytes_accession_and_exact_market_rows(tmp_path):
    from dataclasses import replace

    from company_wiki.source_catalog.security_listing_evidence import (
        ListingEvidenceError,
        build_sec_20f_listing_evidence,
    )

    store = _master(tmp_path)
    master = store.load(markets=("HK", "US"))
    html = """<html><head><title>Alibaba Group Holding Limited 2025 Form 20-F</title></head><body>
    <ix:nonNumeric name="dei:EntityCentralIndexKey">1577552</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentType">20-F</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentFiscalYearFocus">2025</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentFiscalPeriodFocus">FY</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentPeriodEndDate">2025-03-31</ix:nonNumeric>
    <table>
    <tr><th>Title of each class</th><th>Trading Symbol(s)</th>
    <th>Name of each exchange on which registered</th></tr>
    <tr><td>Ordinary Shares, par value US$0.000003125 per share</td>
    <td>9988 (HKD Counter) 89988 (RMB Counter)</td>
    <td>The Stock Exchange of Hong Kong Limited</td></tr>
    <tr><td>American Depositary Shares, each representing eight Ordinary Shares</td>
    <td>BABA</td><td>New York Stock Exchange</td></tr>
    </table></body></html>"""
    content = _verified_html(html)
    metadata = _metadata(_BABA_CIK, "0000950170-25-090161", "baba-20250331.htm")

    tampered = replace(content, data=content.data + b" ")
    with pytest.raises(Exception, match="source bytes do not match"):
        build_sec_20f_listing_evidence(tampered, metadata=metadata, master=master)

    wrong_accession = {**metadata, "provider_document_id": "0000000000-00-000000"}
    with pytest.raises(ListingEvidenceError, match="accession"):
        build_sec_20f_listing_evidence(content, metadata=wrong_accession, master=master)

    wrong_cik = {**metadata, "source_url": metadata["source_url"].replace("1577552", "1723690")}
    assert build_sec_20f_listing_evidence(content, metadata=wrong_cik, master=master) is None

    debt_only = _verified_html(html.replace("Ordinary Shares", "Senior Notes"))
    assert build_sec_20f_listing_evidence(debt_only, metadata=metadata, master=master) is None

    one_market = _verified_html(html.replace("New York Stock Exchange", "Unknown Exchange"))
    assert build_sec_20f_listing_evidence(one_market, metadata=metadata, master=master) is None


def test_linked_identity_projects_source_aliases_into_an_unaliased_target_market(tmp_path):
    from company_wiki.source_catalog.security_identity import SecurityIdentityResolver
    from company_wiki.source_catalog.security_listing_evidence import (
        build_sec_20f_listing_evidence,
    )

    store = _master(tmp_path, omit_hk_listing_ticker_aliases=True)
    master = store.load(markets=("HK", "US"))
    cases = (
        (_BABA_CIK, "0000950170-25-090161", "baba-20250331.htm", "BABA", "9988 89988"),
        (_BILI_CIK, "0001193125-26-157842", "d91984d20f.htm", "BILI", "9626"),
    )
    for cik, accession, filename, ticker, hk_code in cases:
        html = f"""<table>
        <tr><th>Title of each class</th><th>Trading Symbol(s)</th>
        <th>Name of each exchange on which registered</th></tr>
        <tr><td>Ordinary Shares</td><td>{hk_code}</td>
        <td>The Stock Exchange of Hong Kong Limited</td></tr>
        <tr><td>American Depositary Shares</td><td>{ticker}</td>
        <td>{'Nasdaq Global Select Market' if ticker == 'BILI' else 'New York Stock Exchange'}</td></tr>
        </table>"""
        evidence = build_sec_20f_listing_evidence(
            _verified_html(html), metadata=_metadata(cik, accession, filename), master=master,
        )
        store._write_issuer_link(evidence)

    tokens = store.issuer_identity_tokens("BABA", market="HK")
    assert "09988" in tokens
    assert "89988" in tokens
    assert "BABA" not in tokens

    # BILI is absent from the HK aliases too; the exact SEC-backed link lets
    # identity resolution find the sole HK listing without fuzzy name matching.
    result = SecurityIdentityResolver(store.load(markets=("HK", "US"))).identify(
        "BILI", market="HK",
    )
    assert result.status.value == "resolved"
    assert result.resolved is not None
    assert (result.resolved.market, result.resolved.security_id) == ("HK", "09626")
    assert result.resolved.match_basis == "issuer_link_exact"


@pytest.mark.parametrize("changed_field", ["source_record_id", "source_name"])
def test_listing_link_is_not_reused_when_official_market_record_identity_changes(
    tmp_path, changed_field,
):
    from company_wiki.source_catalog.security_identity import (
        SecurityIdentityResolver,
        SecurityRecord,
    )
    from company_wiki.source_catalog.security_listing_evidence import (
        build_sec_20f_listing_evidence,
    )

    store = _master(tmp_path, omit_hk_listing_ticker_aliases=True)
    html = """<table>
    <tr><th>Title of each class</th><th>Trading Symbol(s)</th>
    <th>Name of each exchange on which registered</th></tr>
    <tr><td>Ordinary Shares, par value US$0.000003125 per share</td>
    <td>9988 (HKD Counter) 89988 (RMB Counter)</td>
    <td>The Stock Exchange of Hong Kong Limited</td></tr>
    <tr><td>American Depositary Shares</td><td>BABA</td>
    <td>New York Stock Exchange</td></tr></table>"""
    evidence = build_sec_20f_listing_evidence(
        _verified_html(html),
        metadata=_metadata(_BABA_CIK, "0000950170-25-090161", "baba-20250331.htm"),
        master=store.load(markets=("HK", "US")),
    )
    store._write_issuer_link(evidence)
    changed = {
        "source_record_id": "7353",
        "source_name": "hkex",
    }
    changed[changed_field] = (
        "reused-stock-record-09988"
        if changed_field == "source_record_id"
        else "different-official-feed"
    )
    store.write_market(
        "HK",
        (SecurityRecord(
            canonical_name="Different current issuer", market="HK", exchange="HKEX",
            ticker="09988", security_id="09988", aliases=(), active=True,
            source_name=changed["source_name"],
            source_url="https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json",
            source_record_id=changed["source_record_id"], identifiers={},
        ),),
        retrieved_at="2026-11-10T00:00:00Z",
        sources=("https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json",),
    )

    linked = SecurityIdentityResolver(store.load(markets=("HK", "US"))).identify(
        "BABA", market="HK",
    )
    assert linked.status.value == "conflict"
    assert not any(candidate.issuer_link_id for candidate in linked.candidates)


def test_sec_table_grid_applies_colspan_to_headers_and_data_rows(tmp_path):
    from company_wiki.source_catalog.security_listing_evidence import (
        build_sec_20f_listing_evidence,
    )

    store = _master(tmp_path)
    html = """<table>
    <tr><th>Title of each class</th><th colspan="2">Trading Symbol(s)</th>
    <th>Name of each exchange on which registered</th></tr>
    <tr><td>Ordinary Shares</td><td colspan="2">9988</td>
    <td>The Stock Exchange of Hong Kong Limited</td></tr>
    <tr><td>American Depositary Shares</td><td colspan="2">BABA</td>
    <td>New York Stock Exchange</td></tr></table>"""
    evidence = build_sec_20f_listing_evidence(
        _verified_html(html),
        metadata=_metadata(_BABA_CIK, "0000950170-25-090161", "baba-20250331.htm"),
        master=store.load(markets=("HK", "US")),
    )
    assert {item.security_id for item in evidence.listings} == {"BABA", "09988"}


def test_sec_table_grid_does_not_overwrite_pending_rowspan_cells():
    from bs4 import BeautifulSoup

    from company_wiki.source_catalog.security_listing_evidence import _table_grid

    table = BeautifulSoup(
        """<table>
        <tr><td>left</td><td rowspan="2">locked</td><td>right</td></tr>
        <tr><td colspan="2">new</td><td>end</td></tr>
        </table>""",
        "html.parser",
    ).table
    assert table is not None
    grid = _table_grid(table)
    assert grid[1] == ("", "locked", "new", "new", "end")


def test_listing_evidence_digest_rejects_changed_rows_and_bad_cache_is_nonblocking(tmp_path):
    import json

    from company_wiki.source_catalog.security_identity import (
        SecurityIdentityResolver,
        SecurityMasterStore,
    )
    from company_wiki.source_catalog.security_listing_evidence import (
        IssuerListingEvidence,
        ListingEvidenceError,
        build_sec_20f_listing_evidence,
    )

    store = _master(tmp_path)
    html = """<table><tr><th>Title of each class</th><th>Trading Symbol(s)</th>
    <th>Name of each exchange on which registered</th></tr>
    <tr><td>Ordinary Shares</td><td>9988</td>
    <td>The Stock Exchange of Hong Kong Limited</td></tr>
    <tr><td>American Depositary Shares</td><td>BABA</td>
    <td>New York Stock Exchange</td></tr></table>"""
    evidence = build_sec_20f_listing_evidence(
        _verified_html(html),
        metadata=_metadata(_BABA_CIK, "0000950170-25-090161", "baba-20250331.htm"),
        master=store.load(markets=("HK", "US")),
    )
    assert evidence is not None
    tampered = evidence.to_dict()
    tampered["listings"][0]["security_id"] = "00001"
    with pytest.raises(ListingEvidenceError, match="content hash"):
        IssuerListingEvidence.from_dict(tampered)

    store._write_issuer_link(evidence)
    cache = next(store.issuer_link_directory.glob("s20f-*.json"))
    cache_payload = json.loads(cache.read_text(encoding="utf-8"))
    cache_payload["listings"][0]["security_id"] = "00001"
    cache.write_text(json.dumps(cache_payload), encoding="utf-8")
    # A corrupt derived issuer-link cache is ignored. Official snapshots and
    # same-market identity lookup continue to work without the relationship.
    master = SecurityMasterStore(store.cache_dir).load(markets=("HK", "US"))
    resolved = SecurityIdentityResolver(master).identify("BABA", market="US").resolved
    assert resolved is not None and resolved.security_id == "BABA"


def test_source_catalog_imports_only_exact_verified_ref_and_is_idempotent(tmp_path_factory):
    import hashlib

    from company_wiki.source_catalog.official_source_flow import import_official_source
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec
    from company_wiki.source_catalog.security_identity import SecurityIdentityResolver
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceRef

    tmp_path = tmp_path_factory.mktemp("import")
    html = """<html><head><title>Alibaba Group Holding Limited 2025 Form 20-F</title></head><body>
    <ix:nonNumeric name="dei:EntityCentralIndexKey">1577552</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentType">20-F</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentFiscalYearFocus">2025</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentFiscalPeriodFocus">FY</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentPeriodEndDate">2025-03-31</ix:nonNumeric>
    <table>
    <tr><th>Title of each class</th><th>Trading Symbol(s)</th>
    <th>Name of each exchange on which registered</th></tr>
    <tr><td>Ordinary Shares, par value US$0.000003125 per share</td>
    <td>9988 (HKD Counter) 89988 (RMB Counter)</td>
    <td>The Stock Exchange of Hong Kong Limited</td></tr>
    <tr><td>American Depositary Shares, each representing eight Ordinary Shares</td>
    <td>BABA</td><td>New York Stock Exchange</td></tr>
    </table></body></html>"""
    metadata = _metadata(_BABA_CIK, "0000950170-25-090161", "baba-20250331.htm")
    catalog_dir = tmp_path / "catalog"
    store = _master(catalog_dir)
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    config = CatalogConfig(
        project_root=tmp_path,
        catalog_dir=catalog_dir,
        roots=(RootSpec(root_id="fixture", path=raw_root, kind="company_raw"),),
    )
    catalog = SourceCatalog(config)
    raw = html.encode("utf-8")
    sha256 = hashlib.sha256(raw).hexdigest()
    capture = {
        "capture_method": "local_document",
        "tool_name": "isolated-p2-fixture",
        "tool_call_id": "sec-20f-baba-fixture",
        "captured_at": "2026-11-09T12:00:00Z",
        "content_sha256": sha256,
        "response_bytes": len(raw),
    }
    import_result = import_official_source(
        catalog,
        original=raw,
        request={
            "schema_version": "official-source-import-request/1",
            "request_id": "p2-sec-20f-source-link-fixture",
            "source": {
                "entity": "Alibaba Group Holding Limited",
                "market": "US",
                "security_id": "BABA",
                "document_kind": "annual_report",
                "title": "Alibaba FY2025 Form 20-F fixture",
                "publisher": "U.S. Securities and Exchange Commission",
                "source_url": metadata["source_url"],
                "published_date": metadata["published_date"],
                "filing_date": metadata["published_date"],
                "period_end": "2025-03-31",
                "fiscal_year": 2025,
                "fiscal_period": "FY",
                "language": "en",
                "provider": "official",
                "provider_document_id": metadata["provider_document_id"],
                "form_type": "20-F",
            },
            "content_sha256": sha256,
            "mime_type": "text/html",
            "max_bytes": len(raw) + 10,
            "capture_receipt": capture,
        },
    )
    ref = SourceRef.from_dict(import_result["source_ref"])

    first = catalog.register_sec_20f_listing_link(
        document_id=ref.document_id,
        source_id=ref.source_id,
        content_sha256=ref.content_sha256,
    )
    link_file = next(store.issuer_link_directory.glob("s20f-*.json"))
    link_file.write_text('{"schema_version":"corrupt"}', encoding="utf-8")
    repaired = catalog.register_sec_20f_listing_link(
        document_id=ref.document_id,
        source_id=ref.source_id,
        content_sha256=ref.content_sha256,
    )
    second = catalog.register_sec_20f_listing_link(
        document_id=ref.document_id,
        source_id=ref.source_id,
        content_sha256=ref.content_sha256,
    )

    from company_wiki.source_catalog.security_listing_evidence import (
        build_sec_20f_listing_evidence,
    )

    bili_html = """<html><body><table>
    <tr><th>Title of Each Class</th><th></th><th>Trading Symbol(s)</th>
    <th></th><th>Name of Each Exchange on Which Registered</th></tr>
    <tr><td>American depositary shares, each representing one Class Z ordinary share</td>
    <td></td><td>BILI</td><td></td><td>Nasdaq Global Select Market</td></tr>
    <tr><td>Class Z ordinary shares, par value US$0.0001 per share</td>
    <td></td><td>9626</td><td></td><td>The Stock Exchange of Hong Kong Limited</td></tr>
    </table></body></html>"""
    bili_evidence = build_sec_20f_listing_evidence(
        _verified_html(bili_html),
        metadata=_metadata(_BILI_CIK, "0001193125-26-157842", "d91984d20f.htm"),
        master=store.load(markets=("HK", "US")),
    )
    assert bili_evidence is not None
    store._write_issuer_link(bili_evidence)

    assert first["status"] == "registered"
    assert repaired["status"] == "registered"
    assert second["status"] == "already_registered"
    cached = store._load_issuer_link_evidence()
    assert len(cached) == 2
    assert any(item.source_sha256 == ref.content_sha256 for item in cached)
    assert "path" not in first and "path" not in second
    from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    link_id = first["issuer_link_id"]
    request = SourceRequest(
        entity="BABA", market="HK", identity_scope="issuer",
        issuer_link_id=link_id, document_kind="annual_report",
        fiscal_year=2025, fiscal_period="FY", as_of_date="2026-11-09",
        schema_version="1.1",
    )
    resolver = SourceResolver(catalog)
    assert resolver.match_source_identity(
        market=request.market,
        security_id=request.security_id,
        issuer_link_id=request.issuer_link_id,
        metadata={"market": "HK", "security_id": "09988"},
    ) == "match"
    assert resolver.match_source_identity(
        market=request.market,
        security_id=request.security_id,
        issuer_link_id=request.issuer_link_id,
        metadata={"market": "HK", "security_id": "09626"},
    ) == "conflict"
    assert resolver.match_source_identity(
        market=request.market,
        security_id=request.security_id,
        issuer_link_id=request.issuer_link_id,
        metadata={"market": "HK"},
    ) == "incomplete"
    assert {"09988", "89988"}.issubset(
        store.issuer_identity_tokens(
            "BABA", market="HK", issuer_link_id=link_id,
        )
    )
    assert store.issuer_identity_tokens(
        "BABA", market="HK", issuer_link_id="issuer-link-v1:" + "0" * 64,
    ) == ()
    candidate = SourceVersionReader(catalog).describe_candidate(ref)
    assert candidate["issuer_link_id"] == link_id

    def import_hk_filing(security_id: str, fiscal_year: int, suffix: str) -> str:
        content = f"<html><body>annual filing {security_id} {fiscal_year}</body></html>".encode()
        digest = hashlib.sha256(content).hexdigest()
        source_url = f"https://www1.hkexnews.hk/listedco/listconews/sehk/{suffix}.htm"
        result = import_official_source(
            catalog,
            original=content,
            request={
                "schema_version": "official-source-import-request/1",
                "request_id": f"p2-hk-{security_id}-{fiscal_year}",
                "source": {
                    "entity": "Alibaba Group Holding Limited",
                    "market": "HK",
                    "security_id": security_id,
                    "document_kind": "annual_report",
                    "title": f"Alibaba HK annual report {fiscal_year} {suffix}",
                    "publisher": "Hong Kong Exchanges and Clearing Limited",
                    "source_url": source_url,
                    "published_date": f"{fiscal_year + 1}-05-01",
                    "filing_date": f"{fiscal_year + 1}-05-01",
                    "period_end": f"{fiscal_year}-03-31",
                    "fiscal_year": fiscal_year,
                    "fiscal_period": "FY",
                    "language": "en",
                    "provider": "official",
                    "provider_document_id": suffix,
                },
                "content_sha256": digest,
                "mime_type": "text/html",
                "max_bytes": len(content) + 10,
                "capture_receipt": {
                    "capture_method": "local_document",
                    "tool_name": "isolated-p2-fixture",
                    "tool_call_id": suffix,
                    "captured_at": "2026-11-09T12:00:00Z",
                    "content_sha256": digest,
                    "response_bytes": len(content),
                },
            },
        )
        return SourceRef.from_dict(result["source_ref"]).document_id

    baba_2025 = import_hk_filing("09988", 2025, "baba-2025")
    import_hk_filing("09626", 2025, "same-name-wrong-issuer")
    import_hk_filing("09988", 2024, "baba-2024")
    result, _observation = SourceResolver(catalog).resolve_for_acquisition(request)
    assert result.status.value in {"reused_exact", "reused_equivalent"}
    assert len(result.matches) == 1
    assert result.matches[0].document_id == baba_2025
    public_query = SourceVersionReader(catalog).query_local(request)
    assert public_query.status == "found"
    assert len(public_query.matches) == 1
    assert public_query.matches[0].document_id == baba_2025
    wrong_period = SourceRequest(
        entity="BABA", market="HK", identity_scope="issuer",
        issuer_link_id=link_id, document_kind="annual_report",
        fiscal_year=2024, fiscal_period="FY", as_of_date="2026-11-09",
        schema_version="1.1",
    )
    old_period, _old_observation = SourceResolver(catalog).resolve_for_acquisition(wrong_period)
    assert old_period.status.value in {"reused_exact", "reused_equivalent"}
    assert len(old_period.matches) == 1
    assert old_period.matches[0].document_id != baba_2025
    old_public_query = SourceVersionReader(catalog).query_local(wrong_period)
    assert old_public_query.status == "found"
    assert len(old_public_query.matches) == 1
    assert old_public_query.matches[0].document_id == old_period.matches[0].document_id
    from company_wiki.source_catalog.resolver import SourceResolutionError

    with pytest.raises(SourceResolutionError):
        SourceRequest(
            entity="BABA", market="HK", identity_scope="issuer",
            issuer_link_id=link_id, security_id="09988",
            document_kind="annual_report", as_of_date="2026-11-09",
            schema_version="1.1",
        )
    resolver = SecurityIdentityResolver(store.load(markets=("HK", "US")))
    us = resolver.identify("BABA", market="US").resolved
    hk = resolver.identify("09988", market="HK").resolved
    assert us is not None and hk is not None
    assert us.issuer_link_id == hk.issuer_link_id == first["issuer_link_id"]


def test_provider_candidate_listing_is_bound_before_fetch_and_survives_import(tmp_path_factory):
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.acquisition import (
        AcquisitionCoordinator,
        AcquisitionError,
        AdapterRegistry,
        DownloadCandidate,
        DownloadReceipt,
    )
    from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
    from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
    from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter
    from company_wiki.source_catalog.resolver import SourceRequest, SourceResolver
    from company_wiki.source_catalog.security_listing_evidence import (
        build_sec_20f_listing_evidence,
    )
    tmp_path = tmp_path_factory.mktemp("link")
    catalog_dir = tmp_path / ".source_catalog"
    store = _master(catalog_dir)
    listing_html = """<html><body><table>
    <tr><th>Title of each class</th><th>Trading Symbol(s)</th>
    <th>Name of each exchange on which registered</th></tr>
    <tr><td>Ordinary Shares</td><td>9988 (HKD Counter) 89988 (RMB Counter)</td>
    <td>The Stock Exchange of Hong Kong Limited</td></tr>
    <tr><td>American Depositary Shares</td><td>BABA</td>
    <td>New York Stock Exchange</td></tr>
    </table></body></html>"""
    evidence = build_sec_20f_listing_evidence(
        _verified_html(listing_html),
        metadata=_metadata(_BABA_CIK, "0000950170-25-090161", "baba-20250331.htm"),
        master=store.load(markets=("HK", "US")),
    )
    assert evidence is not None
    store._write_issuer_link(evidence)

    raw_root = tmp_path / "companies"
    raw_root.mkdir()
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=catalog_dir,
        roots=(RootSpec("company_raw", raw_root, "company_raw"),),
    ))
    catalog.scan()
    request = SourceRequest(
        entity="BABA",
        market="US",
        identity_scope="issuer",
        issuer_link_id=evidence.issuer_link_id,
        document_kind="annual_report",
        form_type="20-F",
        fiscal_year=2025,
        fiscal_period="FY",
        as_of_date="2026-11-09",
        allow_download=True,
        schema_version="1.1",
    )

    class CandidateAdapter:
        name = "p2-fixture"
        version = "1.0.0"

        def __init__(self, candidate):
            self.candidate = candidate
            self.discovery_request = None
            self.discovery_count = 0
            self.fetch_count = 0

        def discover(self, provider_request):
            self.discovery_request = provider_request
            self.discovery_count += 1
            return (self.candidate,)

        def fetch(self, candidate, staging_dir):
            self.fetch_count += 1
            staging_dir.mkdir(parents=True, exist_ok=True)
            staged_path = staging_dir / "baba-2025.html"
            staged_path.write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            return DownloadReceipt(
                candidate_id=candidate.candidate_id,
                provider=candidate.provider,
                provider_document_id=candidate.provider_document_id,
                source_url=candidate.source_url,
                staged_path=str(staged_path), content_sha256=digest,
                byte_size=len(content), mime_type="text/html",
                retrieved_at="2026-11-09T12:00:00Z", http_status=200,
                adapter_name=self.name, adapter_version=self.version,
            )

    def candidate(security_id: str, *, fiscal_period: str | None = "FY"):
        return DownloadCandidate(
            candidate_id=f"sec:{security_id}", provider="sec",
            provider_document_id="0000950170-25-090161", market="US",
            entity=request.entity, title="FY2025 20-F",
            source_url="https://www.sec.gov/Archives/edgar/data/1577552/filing.htm",
            document_kind="annual_report", form_type="20-F",
            filing_date="2026-05-20", fiscal_year=2025,
            fiscal_period=fiscal_period, language="en", security_id=security_id,
        )

    content = ("<html><body>"
        "<ix:nonNumeric name='dei:EntityCentralIndexKey'>0001577552</ix:nonNumeric>"
        "<ix:nonNumeric name='dei:DocumentType'>20-F</ix:nonNumeric>"
        "<ix:nonNumeric name='dei:DocumentFiscalYearFocus'>2025</ix:nonNumeric>"
        "<ix:nonNumeric name='dei:DocumentFiscalPeriodFocus'>FY</ix:nonNumeric>"
        "<ix:nonNumeric name='dei:DocumentPeriodEndDate'>2025-03-31</ix:nonNumeric>"
        "<p>Alibaba annual filing evidence.</p></body></html>").encode()

    wrong_adapter = CandidateAdapter(candidate("BILI"))
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(wrong_adapter, wrong_adapter, wrong_adapter),
        staging_root=tmp_path / "staging-wrong",
    )
    with pytest.raises(AcquisitionError, match="security_id"):
        coordinator.select(request)
    assert wrong_adapter.fetch_count == 0
    assert wrong_adapter.discovery_request is not None
    assert wrong_adapter.discovery_request.identity_scope == "listing"
    assert wrong_adapter.discovery_request.security_id == "BABA"

    missing_period_adapter = CandidateAdapter(candidate("BABA", fiscal_period=None))
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(missing_period_adapter, missing_period_adapter,
                                 missing_period_adapter),
        staging_root=tmp_path / "staging-period",
    )
    with pytest.raises(AcquisitionError, match="fiscal_period"):
        coordinator.select(request)

    correct_adapter = CandidateAdapter(candidate("BABA"))
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(correct_adapter, correct_adapter, correct_adapter),
        staging_root=tmp_path / "staging-correct",
    )
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    correct_service = SourceAcquisitionService(
        coordinator=coordinator,
        writer=CanonicalSourceWriter(catalog, staging_root=tmp_path / "staging-correct"),
        journal=AcquisitionJournal(journal_dir),
    )
    first = correct_service.ensure(request)
    assert first.canonical_import is not None
    assert first.canonical_import.source_ref.content_sha256 == hashlib.sha256(content).hexdigest()
    assert correct_adapter.fetch_count == 1
    second = correct_service.ensure(request)
    assert second.status.value in {"reused", "deduplicated", "imported"}
    assert correct_adapter.fetch_count == 1
    resolved, observation = SourceResolver(catalog).resolve_for_acquisition(request)
    assert observation is not None
    assert resolved.status.value in {"reused_exact", "reused_equivalent"}
    assert resolved.matches[0].source_id == first.canonical_import.source_ref.source_id

    hk_adapter = CandidateAdapter(candidate("BABA"))
    hk_request = SourceRequest(
        entity="BABA", market="HK", identity_scope="issuer",
        issuer_link_id=evidence.issuer_link_id, document_kind="annual_report",
        fiscal_year=2025, fiscal_period="FY", as_of_date="2026-11-09",
        allow_download=True, schema_version="1.1",
    )
    hk_coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(hk_adapter, hk_adapter, hk_adapter),
        staging_root=tmp_path / "staging-hk",
    )
    hk_result = hk_coordinator.select(hk_request)
    assert hk_result.status.value == "ambiguous"
    assert hk_result.reason == "issuer_scope_has_multiple_target_listings"
    assert hk_adapter.discovery_count == 0
    catalog.close()
