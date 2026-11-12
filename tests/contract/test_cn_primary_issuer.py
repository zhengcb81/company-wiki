"""Controlled parser/real catalog tests for a native source-identity proof.

Ported from the dashboard-B33/CANONICAL candidate (`385cee72b`).  The seam
below substitutes only an existing source-facts lookup for parser tests;
actual SourceVersionReader and assertions have separate contract tests.
The full-stack test (real catalog + legacy link + canonical browser) stays
with the T-CANON/T-B33 port of those modules and is not duplicated here.
"""

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
