"""Neutral RED: Sina provider pagination, budget and failure boundaries."""

from __future__ import annotations

import json

import httpx
import pytest

from company_wiki.source_catalog.download_budget import AcquisitionBudget
from company_wiki.source_catalog.financial_statements import sina_provider

from . import fixtures


def _budget(limit: int = 8 * 1024 * 1024, seconds: float = 30.0) -> AcquisitionBudget:
    return AcquisitionBudget.from_limits(
        max_response_bytes=limit, max_seconds=seconds, max_cost_usd="0.00"
    )


NULL_PAGE = b'{"result":{"status":{"code":0},"data":null}}'


class _ByteStream(httpx.SyncByteStream):
    """Lazy stream so BudgetedHTTPTransport accounts the wire bytes."""

    def __init__(self, payload: bytes):
        self.payload = payload

    def __iter__(self):
        yield self.payload


class _Recorder:
    def __init__(self, pages: dict[int, bytes | httpx.Response]):
        self.pages = pages
        self.requests: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(str(request.url))
        page = int(request.url.params.get("page", "1"))
        target = self.pages.get(page)
        if isinstance(target, httpx.Response):
            return target
        if target is None:
            return httpx.Response(200, stream=_ByteStream(NULL_PAGE))
        return httpx.Response(
            200,
            stream=_ByteStream(target),
            headers={"content-type": "application/json; charset=utf-8"},
        )


def _zhongwei_lrb_pages() -> dict[int, bytes]:
    return {
        page: fixtures.fixture_bytes(f"sh688012-lrb-type0-page{page}-num10.json.gz")
        for page in range(1, 5)
    }


def _fetch(handler, **kwargs):
    from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport

    def factory(budget: AcquisitionBudget) -> httpx.Client:
        return httpx.Client(
            transport=BudgetedHTTPTransport(httpx.MockTransport(handler), budget)
        )

    provider = sina_provider.SinaStatementsProvider(http_client_factory=factory)
    return provider.fetch_statement(
        exchange=kwargs.pop("exchange", "SSE"),
        code=kwargs.pop("code", "688012"),
        statement_type=kwargs.pop("statement_type", "income_statement"),
        report_types=kwargs.pop("report_types", None),
        max_pages=kwargs.pop("max_pages", 64),
        budget=kwargs.pop("budget") if "budget" in kwargs else _budget(),
        **kwargs,
    )


class TestUrlConstruction:
    def test_fixed_endpoint_and_params_no_user_urls(self):
        recorder = _Recorder(_zhongwei_lrb_pages())
        _fetch(recorder)
        assert all(
            url.startswith(sina_provider.SINA_ENDPOINT + "?") for url in recorder.requests
        )
        first = recorder.requests[0]
        assert "paperCode=sh688012" in first
        assert "source=lrb" in first
        assert "type=0" in first
        assert "num=10" in first
        assert "page=1" in first

    def test_exchange_mapping_and_rejection(self):
        recorder = _Recorder(_zhongwei_lrb_pages())
        _fetch(recorder, exchange="SZSE", code="000333")
        assert "paperCode=sz000333" in recorder.requests[0]
        recorder_bj = _Recorder(_zhongwei_lrb_pages())
        _fetch(recorder_bj, exchange="BSE", code="920001")
        assert "paperCode=bj920001" in recorder_bj.requests[0]
        with pytest.raises(sina_provider.SinaProviderError) as excinfo:
            _fetch(_Recorder(_zhongwei_lrb_pages()), exchange="NYSE", code="AAPL")
        assert excinfo.value.code == "unsupported_exchange"

    def test_annual_filter_uses_type_4(self):
        recorder = _Recorder(
            {
                1: fixtures.fixture_bytes("sh688012-lrb-type4-page1-num2.json.gz"),
                2: b'{"result": {"status": {"code": 0}, "data": null}}',
            }
        )
        result = _fetch(recorder, report_types=("annual",))
        assert "type=4" in recorder.requests[0]
        assert result.terminal_reason == "end_of_data"


class TestPaginationTermination:
    def test_full_history_stops_on_null_page_five(self):
        recorder = _Recorder(_zhongwei_lrb_pages())
        result = _fetch(recorder)
        assert result.terminal_reason == "end_of_data"
        assert len(recorder.requests) == 5  # pages 1..4 data + page 5 null
        assert len(result.pages) == 4
        assert result.observed_period_count == 36
        assert result.unique_periods == 36
        assert min(result.unique_periods_list) == "20161231"
        assert max(result.unique_periods_list) == "20260630"
        # usage is real: 5 HTTP exchanges, bytes = wire bodies of all five
        # responses including the terminating null page.
        assert result.http_exchanges == 5
        assert result.response_bytes == sum(
            len(body) for body in _zhongwei_lrb_pages().values()
        ) + len(NULL_PAGE)
        assert result.cost_usd == "0.00"

    def test_first_page_null_data_is_no_data_not_end(self):
        recorder = _Recorder({})
        result = _fetch(recorder)
        assert result.terminal_reason == "no_data"
        assert result.pages == ()

    def test_duplicate_page_stops(self):
        page1 = fixtures.fixture_bytes("sh688012-lrb-type0-page1-num10.json.gz")
        recorder = _Recorder({1: page1, 2: page1})
        result = _fetch(recorder)
        assert result.terminal_reason == "duplicate_page"
        assert len(result.pages) == 2

    def test_count_change_stops_honestly(self):
        page1 = fixtures.fixture_bytes("sh688012-lrb-type0-page1-num10.json.gz")
        shifted = json.loads(page1.decode("utf-8"))
        shifted["result"]["data"]["report_count"] = "35"
        recorder = _Recorder(
            {1: page1, 2: json.dumps(shifted, ensure_ascii=False).encode("utf-8")}
        )
        result = _fetch(recorder)
        assert result.terminal_reason == "count_changed"

    def test_no_new_periods_stops_as_no_progress(self):
        page1 = fixtures.fixture_bytes("sh688012-lrb-type0-page1-num10.json.gz")
        fewer = json.loads(page1.decode("utf-8"))
        # same report_count, but page 2 returns a strict subset of periods.
        keep = sorted(fewer["result"]["data"]["report_list"], reverse=True)[:5]
        fewer["result"]["data"]["report_list"] = {
            key: fewer["result"]["data"]["report_list"][key] for key in keep
        }
        fewer["result"]["data"]["report_date"] = [
            item
            for item in fewer["result"]["data"]["report_date"]
            if item["date_value"] in keep
        ]
        recorder = _Recorder(
            {1: page1, 2: json.dumps(fewer, ensure_ascii=False).encode("utf-8")}
        )
        result = _fetch(recorder)
        assert result.terminal_reason == "no_progress"

    def test_max_pages_bound_is_honest_partial(self):
        recorder = _Recorder(_zhongwei_lrb_pages())
        result = _fetch(recorder, max_pages=2)
        assert result.terminal_reason == "max_pages"
        assert len(result.pages) == 2

    def test_period_stop_boundary(self):
        recorder = _Recorder(_zhongwei_lrb_pages())
        result = _fetch(recorder, stop_before_period="20230101")
        # Pagination stops once an accepted page already contains periods
        # before the boundary; page granularity keeps that whole page.
        assert result.terminal_reason == "period_boundary"
        assert len(recorder.requests) == 2  # page1 (2026-2024) + page2 (2024-2023)
        assert any(p < "20230101" for p in result.unique_periods_list)


class TestFailuresAndBudget:
    def test_403_is_named_provider_error(self):
        recorder = _Recorder({1: httpx.Response(403, text="forbidden")})
        result = _fetch(recorder)
        assert result.terminal_reason == "provider_error"
        assert result.error_code == "forbidden"

    def test_429_is_named_provider_error(self):
        recorder = _Recorder({1: httpx.Response(429, text="slow down")})
        result = _fetch(recorder)
        assert result.terminal_reason == "provider_error"
        assert result.error_code == "too_many_requests"

    def test_http_500(self):
        recorder = _Recorder({1: httpx.Response(500, text="boom")})
        result = _fetch(recorder)
        assert result.terminal_reason == "provider_error"
        assert result.error_code == "http_error"

    def test_budget_stop_mid_pagination_keeps_partial_pages(self):
        pages = _zhongwei_lrb_pages()
        limit = len(pages[1]) + len(pages[2]) + 100
        recorder = _Recorder(pages)
        result = _fetch(recorder, budget=_budget(limit=limit))
        assert result.terminal_reason == "budget_stopped"
        assert result.error_code in {"byte_budget_exceeded", "deadline_exceeded"}
        assert 1 <= len(result.pages) < 4

    def test_one_budget_shared_across_all_pages(self):
        pages = _zhongwei_lrb_pages()
        total = sum(len(body) for body in pages.values())
        recorder = _Recorder(pages)
        result = _fetch(recorder, budget=_budget(limit=total - 10))
        assert result.terminal_reason == "budget_stopped"
        # never exceeds the ceiling even accounting the final failed page
        assert result.response_bytes <= total

    def test_provider_metadata(self):
        recorder = _Recorder(_zhongwei_lrb_pages())
        result = _fetch(recorder)
        assert result.provider == "sina_finance"
        assert result.publisher == "新浪财经"

    def test_bse_capability_gap_is_honest_no_data(self):
        # Real bounded probe 2026-10-25: bj430017 returns HTTP 200 / code=0 /
        # data=null — identical to an invalid security. BJ is a named gap.
        recorder = _Recorder({})
        result = _fetch(recorder, exchange="BSE", code="430017")
        assert result.terminal_reason == "no_data"
        assert result.error_code is None
