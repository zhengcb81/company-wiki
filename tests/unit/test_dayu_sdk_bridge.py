"""SDK routing and discovery stay metadata-only with fiscal provenance."""

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog.resolver import SourceRequest


@pytest.fixture(scope="session")
def sdk_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class FakeSEC:
    def __init__(self):
        self.original_calls = 0
        self.history_calls = []

    async def resolve_company(self, ticker):
        assert ticker == "FIXTURE"
        return "123", "Provider Company", "0000000123"

    async def fetch_submissions(self, cik):
        return {"cik": 123, "fiscalYearEnd": "0630", "filings": {
            "recent": {"name": "recent"},
            "files": [{"name": "history.json", "filingFrom": "2025-01-01", "filingTo": "2025-12-31"}],
        }}

    async def fetch_json(self, url):
        self.history_calls.append(url)
        return {"name": "history"}

    async def list_filing_files(self, cik, accession, primary, form, **flags):
        assert flags == {"include_xbrl": False, "include_exhibits": False, "include_http_metadata": False}
        return [SimpleNamespace(name=primary, source_url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary}",
                                remote_size=None, http_etag=None, http_last_modified=None)]

    async def fetch_file_bytes(self, url):
        self.original_calls += 1
        raise AssertionError("Discovery must not download originals")


def _collect(records, table, form_windows, end_date):
    assert form_windows["10-Q"].year <= 2025
    assert end_date.isoformat() == "2026-10-08"
    accession = "0000000123-25-000001" if table["name"] == "recent" else "0000000123-25-000002"
    records[accession] = SimpleNamespace(
        form_type="10-Q", filing_date="2025-10-25", report_date="2025-09-30",
        accession_number=accession, primary_document="original.htm",
    )


def test_sec_discovery_uses_sdk_and_correct_fiscal_year_without_original_download(sdk_loop):
    from company_wiki.source_catalog.dayu_sdk_bridge import discover_sec

    sdk = FakeSEC()
    request = SourceRequest(entity="Consumer Name", market="US", security_id="FIXTURE",
                            document_kind="quarterly_report", fiscal_year=2026, fiscal_period="Q1",
                            as_of_date="2026-10-08", allow_download=True)
    candidates = sdk_loop.run_until_complete(discover_sec(request, sdk, collect=_collect))
    assert len(candidates) == 1
    candidate = candidates[0]
    assert (candidate["fiscal_year"], candidate["fiscal_period"]) == (2026, "Q1")
    assert candidate["sdk_company_profile"]["company_name"] == "Provider Company"
    assert candidate["fiscal_year_basis"]["report_date"] == "2025-09-30"
    assert sdk.original_calls == 0
    assert len(sdk.history_calls) == 1


@pytest.mark.parametrize("form", ["8-K", "8-K/A", "6-K"])
def test_unsupported_exhibit_or_ambiguous_period_request_is_explicit_before_sdk(sdk_loop, form):
    from company_wiki.source_catalog.dayu_sdk_bridge import discover_sec, DayuBridgeError

    sdk = FakeSEC()
    request = SourceRequest(entity="Consumer", market="US", security_id="FIXTURE",
                            document_kind="quarterly_report", form_type=form,
                            as_of_date="2026-10-08", allow_download=True)
    with pytest.raises(DayuBridgeError) as error:
        sdk_loop.run_until_complete(discover_sec(request, sdk, collect=_collect))
    assert error.value.error_code == "unsupported_sec_form"
    assert sdk.original_calls == 0


@dataclass
class HKCandidate:
    provider: str = "hkexnews"
    source_id: str = "HK-DOC-2025"
    source_url: str = "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/doc.pdf"
    title: str = "2025年年度報告"
    language: str = "zh"
    filing_date: str = "2026-04-20"
    fiscal_year: int = 2025
    fiscal_period: str = "FY"
    amended: bool = False
    content_length: int | None = None
    etag: str | None = None
    last_modified: str | None = None


class FakeHK:
    def __init__(self, title="2025年年度報告"):
        self.title = title

    def resolve_company(self, query):
        assert query.normalized_ticker == "0700.HK"
        return SimpleNamespace(provider="hkexnews", company_id="HKEX:123", company_name="官方公司",
                               ticker=query.normalized_ticker)

    def list_report_candidates(self, query, profile):
        return (HKCandidate(title=self.title),)


def test_hk_provider_profile_and_title_year_remain_in_candidate():
    from company_wiki.source_catalog.dayu_sdk_bridge import discover_hk
    request = SourceRequest(entity="消费者别名", market="HK", security_id="0700.HK",
                            document_kind="annual_report", fiscal_year=2025,
                            as_of_date="2026-10-08", allow_download=True)
    values = discover_hk(request, FakeHK(), query_type=SimpleNamespace)
    assert values[0]["sdk_company_profile"]["company_name"] == "官方公司"
    assert values[0]["sdk_report_candidate"]["source_id"] == "HK-DOC-2025"
    assert values[0]["fiscal_year_basis"]["kind"] == "explicit_title_year"


def test_hk_missing_title_year_is_not_silently_assigned_the_requested_year():
    from company_wiki.source_catalog.dayu_sdk_bridge import discover_hk
    from company_wiki.source_catalog.dayu_fiscal_metadata import FiscalMetadataError
    request = SourceRequest(entity="消费者", market="HK", security_id="0700.HK",
                            document_kind="annual_report", fiscal_year=2025,
                            as_of_date="2026-10-08", allow_download=True)
    with pytest.raises(FiscalMetadataError):
        discover_hk(request, FakeHK(title="年度報告"), query_type=SimpleNamespace)


def test_hk_irrelevant_unresolved_candidate_does_not_block_requested_report():
    from company_wiki.source_catalog.dayu_sdk_bridge import discover_hk
    class MixedHK(FakeHK):
        def list_report_candidates(self, query, profile):
            return (HKCandidate(title="年度報告", fiscal_year=2024), HKCandidate())
    request = SourceRequest(entity="消费者", market="HK", security_id="0700.HK",
        document_kind="annual_report", fiscal_year=2025, as_of_date="2026-10-08", allow_download=True)
    values = discover_hk(request, MixedHK(), query_type=SimpleNamespace)
    assert len(values) == 1
    assert values[0]["fiscal_year"] == 2025


def test_hk_english_is_not_claimed_when_sdk_filters_english_announcements():
    from company_wiki.source_catalog.dayu_sdk_bridge import discover_hk, DayuBridgeError
    request = SourceRequest(entity="Consumer", market="HK", security_id="0700.HK", language="en",
                            document_kind="annual_report", as_of_date="2026-10-08", allow_download=True)
    with pytest.raises(DayuBridgeError) as error:
        discover_hk(request, FakeHK(), query_type=SimpleNamespace)
    assert error.value.error_code == "unsupported_language"
