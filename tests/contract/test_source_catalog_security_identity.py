"""Contracts for fail-closed listed-company security identification."""

from __future__ import annotations

import io
import json
from pathlib import Path


def _record(
    *,
    name: str,
    market: str,
    exchange: str,
    ticker: str,
    aliases: tuple[str, ...] = (),
    source_record_id: str | None = None,
):
    from company_wiki.source_catalog import SecurityRecord

    return SecurityRecord(
        canonical_name=name,
        market=market,
        exchange=exchange,
        ticker=ticker,
        security_id=ticker,
        aliases=aliases,
        active=True,
        source_name={"CN": "cninfo", "HK": "hkex", "US": "sec_nasdaq"}[market],
        source_url=f"https://official.example/{market.lower()}",
        source_record_id=source_record_id or ticker,
        identifiers={},
    )


def _master(tmp_path: Path):
    from company_wiki.source_catalog import SecurityMasterStore

    store = SecurityMasterStore(tmp_path / "security-master")
    store.write_market(
        "CN",
        (
            _record(
                name="中微公司",
                market="CN",
                exchange="SSE",
                ticker="688012",
                aliases=("中微半导体设备（上海）股份有限公司",),
            ),
            _record(
                name="万科A",
                market="CN",
                exchange="SZSE",
                ticker="000002",
                aliases=("万科", "万科企业股份有限公司"),
            ),
        ),
        retrieved_at="2026-07-19T08:00:00Z",
        sources=("https://www.cninfo.com.cn/new/data/szse_stock.json",),
    )
    store.write_market(
        "HK",
        (
            _record(
                name="小米集团-W",
                market="HK",
                exchange="HKEX",
                ticker="01810",
                aliases=("小米", "小米集团"),
            ),
            _record(
                name="万科企业",
                market="HK",
                exchange="HKEX",
                ticker="02202",
                aliases=("万科",),
            ),
        ),
        retrieved_at="2026-07-19T08:00:00Z",
        sources=("https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json",),
    )
    store.write_market(
        "US",
        (
            _record(
                name="Advanced Micro Devices, Inc.",
                market="US",
                exchange="NASDAQ",
                ticker="AMD",
                aliases=("Advanced Micro Devices", "超威半导体"),
                source_record_id="0000002488",
            ),
        ),
        retrieved_at="2026-07-19T08:00:00Z",
        sources=(
            "https://www.sec.gov/files/company_tickers.json",
            "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
        ),
    )
    return store


def test_identity_resolver_handles_three_markets_and_ticker_variants(tmp_path):
    from company_wiki.source_catalog import IdentityStatus, SecurityIdentityResolver

    resolver = SecurityIdentityResolver(_master(tmp_path).load())

    cn = resolver.identify("中微半导体设备上海股份有限公司")
    hk = resolver.identify("1810.HK")
    us = resolver.identify("amd")

    assert cn.status is IdentityStatus.RESOLVED
    assert cn.resolved.canonical_name == "中微公司"
    assert cn.resolved.market == "CN"
    assert cn.resolved.exchange == "SSE"
    assert cn.resolved.security_id == "688012"
    assert cn.resolved.match_basis == "alias_exact"
    assert hk.status is IdentityStatus.RESOLVED
    assert hk.resolved.security_id == "01810"
    assert hk.resolved.match_basis == "ticker_exact"
    assert us.status is IdentityStatus.RESOLVED
    assert us.resolved.security_id == "AMD"
    assert us.resolved.match_basis == "ticker_exact"


def test_identity_resolver_is_fail_closed_for_ambiguity_conflict_and_low_confidence(
    tmp_path,
):
    from company_wiki.source_catalog import IdentityStatus, SecurityIdentityResolver

    resolver = SecurityIdentityResolver(_master(tmp_path).load())

    ambiguous = resolver.identify("万科")
    cn = resolver.identify("万科", market="CN")
    conflict = resolver.identify("AMD", market="CN")
    weak = resolver.identify("微米公司")
    missing = resolver.identify("不存在的上市公司")

    assert ambiguous.status is IdentityStatus.AMBIGUOUS
    assert [(item.market, item.security_id) for item in ambiguous.candidates] == [
        ("CN", "000002"),
        ("HK", "02202"),
    ]
    assert cn.status is IdentityStatus.RESOLVED
    assert cn.resolved.security_id == "000002"
    assert conflict.status is IdentityStatus.CONFLICT
    assert conflict.resolved is None
    assert conflict.candidates[0].market == "US"
    assert weak.status is not IdentityStatus.RESOLVED
    assert missing.status is IdentityStatus.MISSING


def test_identity_resolver_allows_only_unique_strong_fuzzy_matches(tmp_path):
    from company_wiki.source_catalog import IdentityStatus, SecurityIdentityResolver

    resolver = SecurityIdentityResolver(_master(tmp_path).load())
    result = resolver.identify("Advanced Micro Device")

    assert result.status is IdentityStatus.RESOLVED
    assert result.resolved.security_id == "AMD"
    assert result.resolved.match_basis == "strong_fuzzy"
    assert result.resolved.score >= 0.92


def test_standalone_identify_cli_emits_machine_readable_result(tmp_path, capsys):
    from company_wiki.source_catalog.identity_cli import main

    store = _master(tmp_path)
    assert main(["--cache-dir", str(store.cache_dir), "小米"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "resolved"
    assert payload["resolved"]["canonical_name"] == "小米集团-W"
    assert payload["resolved"]["market"] == "HK"
    assert payload["resolved"]["exchange"] == "HKEX"
    assert payload["resolved"]["ticker"] == "01810"


def test_cross_market_identify_refuses_an_incomplete_master(tmp_path, capsys):
    from company_wiki.source_catalog import SecurityMasterStore
    from company_wiki.source_catalog.identity_cli import main

    store = SecurityMasterStore(tmp_path / "partial-master")
    store.write_market(
        "US",
        (
            _record(
                name="Advanced Micro Devices, Inc.",
                market="US",
                exchange="NASDAQ",
                ticker="AMD",
            ),
        ),
        retrieved_at="2026-07-19T08:00:00Z",
        sources=("https://www.sec.gov/files/company_tickers.json",),
    )

    assert main(["--cache-dir", str(store.cache_dir), "AMD"]) == 1

    error = json.loads(capsys.readouterr().err)
    assert error["error_type"] == "fatal"
    assert "CN" in error["error"] and "HK" in error["error"]


def test_source_resolve_identifies_company_before_opening_catalog(tmp_path, capsys):
    from company_wiki.source_catalog import cli

    project = tmp_path / "project"
    root = project / "companies"
    root.mkdir(parents=True)
    config = project / "config" / "source_catalog.yaml"
    config.parent.mkdir()
    config.write_text(
        """schema_version: '1.0'
catalog_dir: '${PROJECT_ROOT}/.source_catalog'
roots:
  - root_id: company_raw
    path: '${PROJECT_ROOT}/companies'
    kind: company_raw
    priority: 10
""",
        encoding="utf-8",
    )
    store = _master(tmp_path)

    exit_code = cli.main(
        [
            "--config",
            str(config),
            "resolve",
            "--company-query",
            "万科",
            "--identity-cache-dir",
            str(store.cache_dir),
            "--document-kind",
            "annual_report",
            "--as-of-date",
            "2026-07-19",
        ]
    )

    error = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert error["error_type"] == "fatal"
    assert "ambiguous" in error["error"]
    assert not (project / ".source_catalog" / "catalog.sqlite3").exists()


def _workbook_bytes() -> bytes:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["List of Securities"])
    sheet.append(["Stock Code", "Name of Securities", "Category", "Sub-Category"])
    sheet.append([1810, "XIAOMI-W", "Equity", "Equity Securities (Main Board)"])
    sheet.append(
        [2800, "TRACKER FUND", "Exchange Traded Products", "Exchange Traded Funds"]
    )
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_refresh_is_market_isolated_filters_hk_non_equity_and_preserves_stale_cache(
    tmp_path,
):
    from company_wiki.source_catalog import (
        CNINFO_STOCK_URL,
        HKEX_ACTIVE_STOCK_URL,
        HKEX_INACTIVE_STOCK_URL,
        HKEX_SECURITIES_URL,
        NASDAQ_LISTED_URL,
        NASDAQ_OTHER_LISTED_URL,
        SEC_TICKER_URL,
        OfficialSecurityMasterRefresher,
    )

    store = _master(tmp_path)
    payloads = {
        HKEX_ACTIVE_STOCK_URL: json.dumps(
            [{"c": "01810", "n": "小米集團－Ｗ", "s": "1810"}], ensure_ascii=False
        ).encode(),
        HKEX_INACTIVE_STOCK_URL: b"[]",
        HKEX_SECURITIES_URL: _workbook_bytes(),
        SEC_TICKER_URL: json.dumps(
            {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        ).encode(),
        NASDAQ_LISTED_URL: (
            "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n"
            "AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N\n"
            "File Creation Time: 20260719000000\n"
        ).encode(),
        NASDAQ_OTHER_LISTED_URL: (
            "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n"
            "File Creation Time: 20260719000000\n"
        ).encode(),
    }

    def fetch(url: str) -> bytes:
        if url == CNINFO_STOCK_URL:
            raise OSError("simulated CNINFO DNS failure")
        return payloads[url]

    report = OfficialSecurityMasterRefresher(
        store,
        fetch_bytes=fetch,
        minimum_records={"CN": 1, "HK": 1, "US": 1},
    ).refresh(markets=("CN", "HK", "US"))

    assert report["CN"]["status"] == "stale_cache"
    assert report["HK"]["status"] == "refreshed"
    assert report["HK"]["records"] == 1
    assert report["US"]["status"] == "refreshed"
    assert store.load(markets=("CN",)).records[0].ticker == "688012"
    hk_records = store.load(markets=("HK",)).records
    assert [item.ticker for item in hk_records] == ["01810"]
    assert "小米" in hk_records[0].aliases
    us_records = store.load(markets=("US",)).records
    assert [item.ticker for item in us_records] == ["AAPL"]


def test_refresh_below_market_floor_preserves_existing_snapshot(tmp_path):
    from company_wiki.source_catalog import (
        CNINFO_STOCK_URL,
        OfficialSecurityMasterRefresher,
    )

    store = _master(tmp_path)
    existing_path = store.path_for("CN")
    existing_payload = existing_path.read_bytes()

    def fetch(url: str) -> bytes:
        assert url == CNINFO_STOCK_URL
        return json.dumps(
            {
                "stockList": [
                    {"code": "600000", "zwjc": "PFBANK", "orgId": "gssz0000001"}
                ]
            }
        ).encode()

    report = OfficialSecurityMasterRefresher(
        store,
        fetch_bytes=fetch,
        minimum_records={"CN": 2, "HK": 1, "US": 1},
    ).refresh(markets=("CN",))

    assert report["CN"]["status"] == "stale_cache"
    assert "minimum is 2" in report["CN"]["error"]
    assert existing_path.read_bytes() == existing_payload


def test_hk_refresh_uses_standard_transfer_fallback_and_english_aliases(
    tmp_path, monkeypatch
):
    from company_wiki.source_catalog import (
        HKEX_ACTIVE_STOCK_URL,
        HKEX_INACTIVE_STOCK_URL,
        HKEX_SECURITIES_URL,
        HKEX_STANDARD_TRANSFER_URL,
        OfficialSecurityMasterRefresher,
    )
    from company_wiki.source_catalog import security_identity

    store = _master(tmp_path)
    active = [
        {"c": "01810", "n": "Xiaomi Chinese", "s": "1810"},
        {"c": "00700", "n": "Tencent Chinese", "s": "700"},
    ]
    payloads = {
        HKEX_ACTIVE_STOCK_URL: json.dumps(active).encode(),
        HKEX_INACTIVE_STOCK_URL: b"[]",
        HKEX_SECURITIES_URL: _workbook_bytes(),
        HKEX_STANDARD_TRANSFER_URL: b"fake-xls-payload",
    }
    monkeypatch.setattr(
        security_identity,
        "_hk_standard_transfer_codes",
        lambda payload: {"01810": "XIAOMI-W", "00700": "TENCENT"},
        raising=False,
    )

    report = OfficialSecurityMasterRefresher(
        store,
        fetch_bytes=payloads.__getitem__,
        minimum_records={"CN": 1, "HK": 2, "US": 1},
    ).refresh(markets=("HK",))

    assert report["HK"]["status"] == "refreshed"
    assert report["HK"]["records"] == 2
    assert HKEX_STANDARD_TRANSFER_URL in report["HK"]["sources"]
    records = {record.ticker: record for record in store.load(markets=("HK",)).records}
    assert "XIAOMI-W" in records["01810"].aliases
    assert "TENCENT" in records["00700"].aliases
