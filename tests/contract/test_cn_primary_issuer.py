"""Controlled parser/real catalog tests for a native source-identity proof."""

from __future__ import annotations

from dataclasses import asdict
from unittest.mock import patch

import pytest

from company_wiki.source_catalog.cn_primary_issuer import (
    PrimaryIssuerUnavailable,
    extract_cn_issuer,
    valid_uscc,
    validate_quote,
)
from company_wiki.source_catalog.security_identity import (
    CNINFO_STOCK_URL,
    SecurityMasterStore,
    SecurityRecord,
)
from company_wiki.source_catalog.source_reader import SourceRef

REF = SourceRef(
    document_id="controlled-document",
    source_id="controlled-source",
    content_sha256="a" * 64,
    byte_size=300,
    mime_type="application/pdf",
    schema_version="2.0",
)
NAME = "受控半导体设备（上海）股份有限公司"
USCC = "913101157626272806"
REGISTRATION = (
    NAME + "(以下简称本公司)的前身为" + NAME.removesuffix("股份有限公司") + "有限公司"
    "(以下简称原公司)由ControlledInc.Asia(以下简称受控亚洲)于2004年5月31日在中华人民共和国上海市成立。"
    "根据原公司全体股东于2018年12月20日签署的《"
    + NAME
    + "创立大会暨2018年第一次临时股东大会决议》，本公司整体改制变更为股份有限公司。"
    "于2018年12月21日取得新营业执照，统一社会信用代码为" + USCC
)
PAGES = [
    "公司基本情况公司的中文名称"
    + NAME
    + "公司的中文简称受控公司公司的外文名称Controlled",
    "公司股票简况股票代码变更前股票简称A股上海证券交易所科创板受控公司688012不适用",
    REGISTRATION,
]

META = {"market": "CN", "document_kind": "annual_report", "security_id": "688012"}


class Catalog:
    def __init__(self, path):
        self.config = type("Config", (), {"catalog_dir": path})()
        self.reader = object()


def make_catalog(tmp_path):
    catalog = Catalog(tmp_path)
    record = SecurityRecord(
        canonical_name="受控公司",
        market="CN",
        exchange="SSE",
        ticker="688012",
        security_id="688012",
        aliases=(),
        active=True,
        source_name="cninfo",
        source_url=CNINFO_STOCK_URL,
        source_record_id="controlled-official-record",
        identifiers={"org_id": "controlled"},
    )
    SecurityMasterStore(tmp_path / "security_master").write_market(
        "CN", [record], retrieved_at="2026-01-01T00:00:00Z", sources=(CNINFO_STOCK_URL,)
    )
    return catalog


def extract(catalog, pages=PAGES, metadata=META):
    # This seam substitutes only an existing source-facts lookup for parser
    # tests. Actual SourceVersionReader and assertions have separate contract
    # tests; this is never presented as real issuer or production evidence.
    with patch(
        "company_wiki.source_catalog.assertion_service.get_verified_assertion",
        return_value={
            "assertion_id": "controlled-assertion",
            "evidence_basis": "source-facts",
        },
    ):
        return extract_cn_issuer(catalog, REF, pages=pages, metadata=metadata)


def test_uscc_checksum_and_quote_ambiguity():
    assert valid_uscc(USCC)
    assert not valid_uscc(USCC[:-1] + "7")
    assert not valid_uscc("Z" * 18)
    assert not valid_uscc("0" * 18)
    assert validate_quote(["2024202420242024"], "202420242024")["state"] == "ambiguous"
    value = validate_quote(
        ["首段这是 实际\n唯一完整引用文字用于定位。"],
        "这是实际唯一完整引用文字用于定位。",
    )
    assert value["state"] == "verified" and value["physical_page"] == 1
    assert value["locator"]["page_kind"] == "physical"
    assert (
        validate_quote(
            ["这是实际唯一完整引用文字用于定位。"] * 2,
            "这是实际唯一完整引用文字用于定位。",
        )["state"]
        == "ambiguous"
    )
    assert (
        validate_quote(["not present"], "这是实际唯一完整引用文字用于定位。")["state"]
        == "not_found"
    )


def test_complete_primary_proof(tmp_path):
    value = extract(make_catalog(tmp_path))
    assert value["state"] == "verified" and value["key"] == {
        "namespace": "cn.uscc",
        "value": USCC,
    }
    assert value["legal_name"] == NAME and value["source_ref"] == asdict(REF)
    assert value["assertion_id"] == "controlled-assertion"
    assert value["evidence"][2]["locator"]["value"] == "3"
    assert "private" not in str(value)


@pytest.mark.parametrize(
    "pages,metadata",
    [
        (PAGES[:2], META),
        (PAGES[:2] + [PAGES[2].replace(USCC, USCC[:-1] + "7")], META),
        (
            PAGES[:2] + [PAGES[2].replace("本公司整体改制", "本公司子公司整体改制")],
            META,
        ),
        (PAGES[:2] + [PAGES[2].replace(NAME, "同业股份有限公司")], META),
        (
            PAGES[:2]
            + [
                PAGES[2].replace(
                    "本公司整体改制",
                    "控股股东同业控股有限公司(以下简称本公司)的登记资料如下。本公司整体改制",
                )
            ],
            META,
        ),
        (PAGES, {**META, "security_id": "688013"}),
        (PAGES, {**META, "market": "US"}),
        ([PAGES[0].replace("受控公司", "不同公司"), *PAGES[1:]], META),
        (
            [PAGES[0] + "公司的中文名称同业股份有限公司公司的中文简称同业", *PAGES[1:]],
            META,
        ),
    ],
)
def test_forged_ambiguous_or_peer_scope_refuses(tmp_path, pages, metadata):
    with pytest.raises(PrimaryIssuerUnavailable):
        extract(make_catalog(tmp_path), pages, metadata)


def test_missing_official_cache_and_source_facts_refuse(tmp_path):
    catalog = Catalog(tmp_path)
    with pytest.raises(PrimaryIssuerUnavailable, match="cache_unavailable"):
        extract(catalog)
    catalog = make_catalog(tmp_path)
    with patch(
        "company_wiki.source_catalog.assertion_service.get_verified_assertion",
        return_value=None,
    ):
        with pytest.raises(PrimaryIssuerUnavailable, match="source_facts_missing"):
            extract_cn_issuer(catalog, REF, pages=PAGES, metadata=META)


def test_real_pdf_catalog_source_facts_and_canonical_namespace(tmp_path):
    import hashlib
    import json
    import pymupdf
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
    from company_wiki.source_catalog.assertion_service import record_source_facts
    # Keep this integration test on the E13 owner API in the candidate.
    # Legacy source-link resolution is a separate B33 implementation surface.
    from company_wiki.source_catalog.public_canonical_browser import (
        Binding,
        PublicCanonicalBrowser,
    )

    raw = tmp_path / "originals"
    raw.mkdir()
    quote = "受控证据定位必须保持原始引用文字与原件版本完全一致。"
    document = pymupdf.open()
    for text in [*PAGES, quote]:
        page = document.new_page()
        page.insert_textbox((30, 30, 570, 780), text, fontsize=11, fontname="china-s")
    body = document.tobytes()
    document.close()
    original = raw / "controlled.pdf"
    original.write_bytes(body)
    sidecar = {
        "schema_version": "1.0",
        "canonical_entity_id": "company-name:受控公司",
        "display_name": "受控公司",
        "market": "CN",
        "security_id": "688012",
        "document_kind": "annual_report",
        "filing_date": "2026-03-01",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "language": "zh",
        "provider": "controlled",
        "provider_document_id": "controlled-pdf",
    }
    (raw / "controlled.pdf.source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / "catalog",
            roots=(RootSpec("originals", raw, "directory", reusable_for_filing=True),),
            reusable_root_kinds=("directory",),
        )
    )
    catalog.scan()
    digest = hashlib.sha256(body).hexdigest()
    ref = SourceRef(
        document_id="urn:company-wiki:document:sha256:" + digest,
        source_id="urn:company-wiki:source:sha256:" + digest,
        content_sha256=digest,
        byte_size=len(body),
        mime_type="application/pdf",
        schema_version="2.0",
    )
    facts = {
        "entity": "受控公司",
        "market": "CN",
        "security_id": "688012",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
    }
    evidence = {
        key: {
            "value": value,
            "locator": "pdf:page:1:controlled",
            "content_sha256": digest,
        }
        for key, value in facts.items()
    }
    recorded = record_source_facts(catalog, ref=ref, facts=facts, evidence=evidence)
    assert recorded["status"] == "recorded"
    # Supply the cache-only official CN security record used by the verifier.
    official = make_catalog(catalog.config.catalog_dir)
    del official
    # The exact real SourceRef and native source-facts row are the input to the
    # E13 CN issuer verifier; do not pull the separate B33 legacy-link API.
    browser = PublicCanonicalBrowser(catalog)
    resolution = browser._resolve_source_facts(ref.source_id)
    assert isinstance(resolution, tuple), resolution
    issuer, pin = resolution
    assert issuer.key.namespace == "cn.uscc" and issuer.key.value == USCC
    assert pin["assertion_id"] == recorded["assertion_id"]
    versions = browser._proven_versions(
        Binding(status="verified", reason_codes=[], issuer_pin=issuer.pin())
    )
    assert [version.source_id for version in versions] == [ref.source_id]
    catalog.close()
@pytest.mark.parametrize(
    "byte_size,document_kind,expected_status,expected_reason",
    [
        (16_000_001, "annual_report", "unavailable", "cn_primary_pdf_byte_limit"),
        (1024, "prospectus", "unknown", "cn_primary_filing_scope_missing"),
    ],
)
def test_canonical_cn_refusal_happens_before_exact_original_open(
    tmp_path, monkeypatch, byte_size, document_kind, expected_status, expected_reason
):
    from types import SimpleNamespace
    from unittest.mock import Mock

    import company_wiki.source_catalog.public_canonical_browser as browser_module
    from company_wiki.source_catalog.public_canonical_browser import (
        PublicCanonicalBrowser,
    )
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    source_id = "urn:company-wiki:source:sha256:" + "a" * 64

    class Reader:
        def fetchone(self, _query, _params):
            return {
                "content_sha256": "a" * 64,
                "byte_size": byte_size,
                "mime_type": "application/pdf",
            }

    class FakeCatalog:
        def __init__(self):
            self.reader = Reader()
            self.config = SimpleNamespace(catalog_dir=tmp_path)

    monkeypatch.setattr(
        browser_module,
        "get_verified_assertion",
        lambda *_args, **_kwargs: {
            "document_id": "controlled-document",
            "assertion_id": "controlled-assertion",
        },
    )
    monkeypatch.setattr(SourceVersionReader, "__init__", lambda _reader, _catalog: None)
    monkeypatch.setattr(
        SourceVersionReader,
        "describe_version",
        lambda _reader, _ref: {
            "market": "CN",
            "document_kind": document_kind,
            "security_id": "688012",
        },
    )
    original_open = Mock(side_effect=AssertionError("original must not be opened"))
    monkeypatch.setattr(SourceVersionReader, "open_described_version", original_open)

    browser = object.__new__(PublicCanonicalBrowser)
    browser.catalog = FakeCatalog()
    result = browser._resolve_source_facts(source_id)

    assert result.status == expected_status
    assert expected_reason in result.reason_codes
    original_open.assert_not_called()
