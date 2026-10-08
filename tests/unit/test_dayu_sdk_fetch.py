"""Fetch executes injected SDK/client, validates original, stages once, cleans scratch."""

import asyncio
from dataclasses import asdict
import hashlib
from pathlib import Path
import sys
from types import ModuleType

import httpx
import pytest

from company_wiki.source_catalog.acquisition import DownloadCandidate, DownloadReceipt
from company_wiki.source_catalog.download_budget import AcquisitionBudget
from company_wiki.source_catalog.store import canonical_json
from unit.test_dayu_fiscal_metadata import _html
from unit.test_dayu_sdk_bridge import HKCandidate


@pytest.fixture(scope="session")
def fetch_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _module(monkeypatch, name, **attrs):
    pieces = name.split(".")
    for index in range(1, len(pieces) + 1):
        key = ".".join(pieces[:index])
        if key not in sys.modules:
            value = ModuleType(key)
            value.__path__ = []
            monkeypatch.setitem(sys.modules, key, value)
    for key, value in attrs.items():
        monkeypatch.setattr(sys.modules[name], key, value, raising=False)


def _budget():
    return AcquisitionBudget.from_limits(max_response_bytes=10000, max_seconds=30, max_cost_usd="0")


def _payload(market):
    raw = dict(candidate_id="sec:fixture", provider="sec", provider_document_id="fixture",
        market=market, entity="Fixture", title="Fixture fiscal report", source_url="https://www.sec.gov/Archives/fixture.htm",
        document_kind="quarterly_report", form_type="10-Q", filing_date="2025-10-25",
        fiscal_year=2026, fiscal_period="Q1", language="en", amended=False,
        cik="123", report_date="2025-09-30")
    if market == "HK":
        sdk = HKCandidate()
        raw.update(candidate_id="hkexnews:"+sdk.source_id, provider="hkexnews",
            provider_document_id=sdk.source_id, source_url=sdk.source_url,
            document_kind="annual_report", form_type="FY", fiscal_year=2025,
            fiscal_period="FY", language="zh", title=sdk.title, filing_date=sdk.filing_date,
            sdk_report_candidate=asdict(sdk))
    candidate = DownloadCandidate(**{k: raw[k] for k in (
        "candidate_id", "provider", "provider_document_id", "market", "entity", "title", "source_url",
        "document_kind", "form_type", "filing_date", "fiscal_year", "fiscal_period", "language", "amended")},
        adapter_payload_json=canonical_json(raw))
    return candidate.to_dict()


@pytest.mark.parametrize("status,headers", [
    (200, {"etag": "get-current", "last-modified": "GET-date"}),
    (206, {"content-range": "bytes 0-399/2000"}),
    (200, {"content-range": "bytes 0-399/2000"}),
])
def test_sec_fetch_uses_client_budget_and_checks_primary_before_staging(tmp_path, monkeypatch, fetch_loop, status, headers):
    from company_wiki.source_catalog.dayu_sdk_cli import _sec_operation

    data = _html()
    calls = []
    monkeypatch.setenv("SEC_USER_AGENT", "test-fixture (not a real request)")
    def respond(request):
        calls.append(request)
        return httpx.Response(status, headers=headers, stream=httpx.ByteStream(data))
    monkeypatch.setattr(httpx, "AsyncHTTPTransport", lambda: httpx.MockTransport(respond))
    class Downloader:
        def __init__(self, workspace_root, client):
            self.client = client
        async def fetch_file_bytes(self, url):
            return (await self.client.get(url)).content
    _module(monkeypatch, "dayu.fins.downloaders.sec_downloader", SecDownloader=Downloader)
    _module(monkeypatch, "dayu.fins.pipelines.sec_filing_collection", collect_filings_from_table=None)
    budget = _budget()
    if status != 200 or "content-range" in headers:
        from company_wiki.source_catalog.bounded_http import ProviderBudgetStop
        with pytest.raises(ProviderBudgetStop) as error:
            fetch_loop.run_until_complete(_sec_operation("fetch", _payload("US"), budget,
                tmp_path, tmp_path, tmp_path, {"name": "test", "version": "1.0.0"}, None))
        assert error.value.error_code == "incomplete_response"
        assert not tuple(tmp_path.iterdir())
        assert len(calls) == 1
        return
    result = fetch_loop.run_until_complete(_sec_operation("fetch", _payload("US"), budget,
        tmp_path, tmp_path, tmp_path, {"name": "test", "version": "1.0.0"}, None))
    receipt = DownloadReceipt(**result["receipt"])
    assert Path(receipt.staged_path).read_bytes() == data
    assert receipt.content_sha256 == hashlib.sha256(data).hexdigest()
    assert receipt.etag == "get-current"
    assert receipt.last_modified == "GET-date"
    assert budget.response_bytes_used == len(data)
    assert len(calls) == 1
    assert not tuple(tmp_path.glob("*.part"))


def test_wrong_sec_primary_with_real_hash_leaves_no_staged_file(tmp_path, monkeypatch, fetch_loop):
    from company_wiki.source_catalog.dayu_sdk_cli import _sec_operation
    from company_wiki.source_catalog.dayu_fiscal_metadata import FiscalMetadataError

    data = _html(year="2025")
    monkeypatch.setenv("SEC_USER_AGENT", "test-fixture (not a real request)")
    monkeypatch.setattr(httpx, "AsyncHTTPTransport", lambda: httpx.MockTransport(
        lambda r: httpx.Response(200, stream=httpx.ByteStream(data))))
    class Downloader:
        def __init__(self, workspace_root, client):
            self.client = client
        async def fetch_file_bytes(self, url):
            return (await self.client.get(url)).content
    _module(monkeypatch, "dayu.fins.downloaders.sec_downloader", SecDownloader=Downloader)
    _module(monkeypatch, "dayu.fins.pipelines.sec_filing_collection", collect_filings_from_table=None)
    budget = _budget()
    with pytest.raises(FiscalMetadataError):
        fetch_loop.run_until_complete(_sec_operation("fetch", _payload("US"), budget,
            tmp_path, tmp_path, tmp_path, {"name": "test", "version": "1.0.0"}, None))
    assert not tuple(tmp_path.iterdir())
    assert budget.response_bytes_used == len(data)


def test_hk_downloaded_asset_is_moved_to_owned_staging_and_sdk_tmp_removed(tmp_path, monkeypatch):
    from company_wiki.source_catalog.dayu_sdk_cli import _hk_operation
    from types import SimpleNamespace

    scratch, staging = tmp_path / "scratch", tmp_path / "staging"
    scratch.mkdir()
    staging.mkdir()
    data = b"%PDF-1.7\n" + b"fixture" * 200
    monkeypatch.setattr(httpx, "HTTPTransport", lambda: httpx.MockTransport(
        lambda r: httpx.Response(200, stream=httpx.ByteStream(data))))
    class Downloader:
        def __init__(self, client, sleep_func):
            self.client = client
        def download_report_pdf(self, candidate):
            body = self.client.get(candidate.source_url).content
            path = scratch / "sdk-asset.pdf"
            path.write_bytes(body)
            return SimpleNamespace(pdf_path=path, content_length=len(body),
                                   sha256=hashlib.sha256(body).hexdigest())
    _module(monkeypatch, "dayu.fins.downloaders.hkexnews_downloader", HkexnewsDiscoveryClient=Downloader)
    _module(monkeypatch, "dayu.fins.pipelines.cn_download_models", CnReportCandidate=HKCandidate, CnReportQuery=None)
    budget = _budget()
    result = _hk_operation("fetch", _payload("HK"), budget, scratch, staging,
                           {"name": "test", "version": "1.0.0"}, None)
    receipt = DownloadReceipt(**result["receipt"])
    assert Path(receipt.staged_path).read_bytes() == data
    assert not tuple(scratch.iterdir())
    assert budget.response_bytes_used == len(data)


def test_fetch_rejects_changed_discovery_binding_before_provider():
    from company_wiki.source_catalog.dayu_sdk_cli import _candidate
    from company_wiki.source_catalog.dayu_sdk_bridge import DayuBridgeError
    payload = _payload("US")
    payload["fiscal_year"] = 2025
    with pytest.raises(DayuBridgeError, match="discovery metadata"):
        _candidate(payload, "US")
