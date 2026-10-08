"""Provider-neutral HTTP accounting; no external network or company fixture."""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from company_wiki.source_catalog.download_budget import AcquisitionBudget


def _budget(limit=100, seconds=30):
    return AcquisitionBudget.from_limits(
        max_response_bytes=limit, max_seconds=seconds, max_cost_usd="0"
    )


@pytest.fixture(scope="session")
def http_test_loop():
    # Windows creates a local wakeup socket pair when constructing an asyncio
    # loop. Construct before the FUNCTION-scoped network guard; all provider
    # calls below still run with socket.connect blocked and MockTransport only.
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class Chunks(httpx.SyncByteStream):
    def __init__(self, chunks, after_chunk=None):
        self.chunks = chunks
        self.after_chunk = after_chunk
        self.closed = False

    def __iter__(self):
        for chunk in self.chunks:
            if self.after_chunk:
                self.after_chunk()
            yield chunk

    def close(self):
        self.closed = True


class AsyncChunks(httpx.AsyncByteStream):
    def __init__(self, chunks, delay=0):
        self.chunks = chunks
        self.delay = delay
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            if self.delay:
                await asyncio.sleep(self.delay)
            yield chunk

    async def aclose(self):
        self.closed = True


def test_redirect_and_retry_error_bodies_share_actual_usage():
    from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport

    budget = _budget(limit=13)
    calls = []
    checkpoints = []

    def provider(request):
        calls.append(request.url.path)
        assert request.headers["accept-encoding"] == "identity"
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "/retry"}, stream=Chunks([b"123"]))
        if len(calls) == 2:
            return httpx.Response(429, stream=Chunks([b"1234"]))
        return httpx.Response(200, stream=Chunks([b"123456"]))

    with httpx.Client(transport=BudgetedHTTPTransport(
        httpx.MockTransport(provider), budget, checkpoint=checkpoints.append,
    ), follow_redirects=True) as client:
        assert client.get("https://example.invalid/redirect").status_code == 429
        assert client.get("https://example.invalid/retry").content == b"123456"
    assert budget.response_bytes_used == 13
    assert calls == ["/redirect", "/retry", "/retry"]
    assert [item["response_bytes"] for item in checkpoints] == [3, 7, 13]


def test_read_overage_is_accounted_and_cannot_be_swallowed_as_head_soft_error():
    from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport, ProviderBudgetStop

    budget = _budget(limit=5)
    chunks = Chunks([b"123", b"4567"])
    checkpoints = []
    with httpx.Client(transport=BudgetedHTTPTransport(
        httpx.MockTransport(lambda r: httpx.Response(200, stream=chunks)),
        budget, checkpoint=checkpoints.append,
    )) as client:
        with pytest.raises(ProviderBudgetStop) as error:
            client.get("https://example.invalid/no-length")
    assert budget.response_bytes_used == 7
    assert error.value.error_code == "byte_budget_exceeded"
    assert not isinstance(error.value, (RuntimeError, ValueError, httpx.HTTPError))
    assert checkpoints[-1]["response_bytes"] == 7
    assert chunks.closed


def test_new_request_after_byte_exhaustion_never_reaches_provider():
    from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport, ProviderBudgetStop

    budget = _budget(limit=3)
    calls = []

    def provider(request):
        calls.append(request)
        return httpx.Response(200, stream=Chunks([b"123"]))

    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(provider), budget)) as client:
        assert client.get("https://example.invalid/one").content == b"123"
        with pytest.raises(ProviderBudgetStop):
            client.get("https://example.invalid/two")
    assert len(calls) == 1


def test_oversize_declared_body_is_refused_before_reading():
    from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport, ProviderBudgetStop

    budget = _budget(limit=3)
    chunks = Chunks([b"1234"])
    with httpx.Client(transport=BudgetedHTTPTransport(
        httpx.MockTransport(lambda r: httpx.Response(
            200, headers={"content-length": "4"}, stream=chunks,
        )), budget,
    )) as client:
        with pytest.raises(ProviderBudgetStop):
            client.get("https://example.invalid/too-large")
    assert budget.response_bytes_used == 0
    assert chunks.closed


def test_head_resource_length_is_not_mistaken_for_response_body():
    from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport

    budget = _budget(limit=3)
    with httpx.Client(transport=BudgetedHTTPTransport(
        httpx.MockTransport(lambda r: httpx.Response(
            200, headers={"content-length": "100000000"}, stream=Chunks([]),
        )), budget,
    )) as client:
        assert client.head("https://example.invalid/metadata").status_code == 200
    assert budget.response_bytes_used == 0


@pytest.mark.parametrize("encoding", ["gzip", "br", "deflate"])
def test_compressed_response_cannot_bypass_budget_by_inflating_after_accounting(encoding):
    from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport, ProviderBudgetStop

    budget = _budget()
    chunks = Chunks([b"compressed"])
    with httpx.Client(transport=BudgetedHTTPTransport(
        httpx.MockTransport(lambda r: httpx.Response(
            200, headers={"content-encoding": encoding}, stream=chunks,
        )), budget,
    )) as client:
        with pytest.raises(ProviderBudgetStop) as error:
            client.get("https://example.invalid/compressed")
    assert error.value.error_code == "unsupported_content_encoding"
    assert budget.response_bytes_used == 0
    assert chunks.closed


def test_chunk_arriving_after_deadline_is_still_recorded_and_not_delivered():
    from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport, ProviderBudgetStop

    budget = _budget()
    chunks = Chunks([b"late"], after_chunk=lambda: setattr(
        budget, "deadline_monotonic", time.monotonic() - 1,
    ))
    with httpx.Client(transport=BudgetedHTTPTransport(
        httpx.MockTransport(lambda r: httpx.Response(200, stream=chunks)), budget,
    )) as client:
        with pytest.raises(ProviderBudgetStop) as error:
            client.get("https://example.invalid/late")
    assert error.value.error_code == "deadline_exceeded"
    assert budget.response_bytes_used == 4
    assert chunks.closed


def test_all_request_timeout_phases_are_bounded_by_remaining_operation_time():
    from company_wiki.source_catalog.bounded_http import BudgetedHTTPTransport

    budget = _budget(seconds=5)
    captured = []

    def provider(request):
        captured.append(request.extensions["timeout"])
        return httpx.Response(200, stream=Chunks([]))

    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(provider), budget),
                      timeout=httpx.Timeout(30, connect=1)) as client:
        client.get("https://example.invalid/timeouts")
    assert 0 < captured[0]["connect"] <= 1
    assert all(0 < value <= 5 for value in captured[0].values())


def test_async_transport_counts_status_body_and_closes(http_test_loop):
    from company_wiki.source_catalog.bounded_http import BudgetedAsyncHTTPTransport

    budget = _budget(limit=7)
    chunks = AsyncChunks([b"err", b"body"])
    async def exercise():
        async with httpx.AsyncClient(transport=BudgetedAsyncHTTPTransport(
            httpx.MockTransport(lambda r: httpx.Response(503, stream=chunks)), budget,
        )) as client:
            assert (await client.get("https://example.invalid/503")).status_code == 503

    http_test_loop.run_until_complete(exercise())
    assert budget.response_bytes_used == 7
    assert chunks.closed


def test_async_slow_drip_total_deadline_stops_before_waiting_for_full_body(http_test_loop):
    from company_wiki.source_catalog.bounded_http import BudgetedAsyncHTTPTransport, ProviderBudgetStop

    budget = _budget(seconds=0.05)
    chunks = AsyncChunks([b"never-arrives"], delay=10)
    started = time.monotonic()
    async def exercise():
        async with httpx.AsyncClient(transport=BudgetedAsyncHTTPTransport(
            httpx.MockTransport(lambda r: httpx.Response(200, stream=chunks)), budget,
        )) as client:
            with pytest.raises(ProviderBudgetStop) as error:
                await client.get("https://example.invalid/drip")
        return error.value

    error = http_test_loop.run_until_complete(exercise())
    assert time.monotonic() - started < 1
    assert error.error_code == "deadline_exceeded"
    assert budget.response_bytes_used == 0
    assert chunks.closed


def test_retry_sleep_cannot_extend_whole_operation_deadline():
    from company_wiki.source_catalog.bounded_http import bounded_sleep, ProviderBudgetStop

    budget = _budget(seconds=1)
    waits = []
    with pytest.raises(ProviderBudgetStop, match="deadline"):
        bounded_sleep(budget, 600, sleep=waits.append)
    assert waits == []
