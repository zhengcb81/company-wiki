"""Valid compressed originals stay bounded before SDK delivery; no network."""
from __future__ import annotations

import asyncio
import gzip
import zlib

import httpx
import pytest

from company_wiki.source_catalog.bounded_http import (
    BudgetedAsyncHTTPTransport, BudgetedHTTPTransport, ProviderBudgetStop,
    usage_receipt,
)
from company_wiki.source_catalog.download_budget import AcquisitionBudget

BODY = b"<html><body><p>New products await customer qualification.</p></body></html>"


def budget(limit=4096):
    return AcquisitionBudget.from_limits(max_response_bytes=limit, max_seconds=10,
                                         max_cost_usd="0")


def encoded(kind, value=BODY):
    if kind == "gzip":
        return gzip.compress(value, mtime=0)
    if kind == "deflate":
        return zlib.compress(value)
    if kind == "raw-deflate":
        obj = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        return obj.compress(value) + obj.flush()
    return value


class Chunks(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks, self.closed = chunks, False

    def __iter__(self):
        yield from self.chunks

    def close(self):
        self.closed = True


class AsyncChunks(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks, self.closed = chunks, False

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk

    async def aclose(self):
        self.closed = True


@pytest.fixture(scope="session")
def loop():
    value = asyncio.new_event_loop()
    yield value
    value.close()


def headers(kind, wire):
    return {"content-encoding": "deflate" if kind == "raw-deflate" else kind,
            "content-length": str(len(wire)), "content-type": "text/html; charset=utf-8"}


@pytest.mark.parametrize("kind", ["identity", "gzip", "deflate", "raw-deflate"])
@pytest.mark.parametrize("mode", ["sync", "async"])
def test_valid_original_single_byte_chunks_before_sdk_delivery(kind, mode, loop):
    wire = encoded(kind)
    b = budget()
    chunks = [bytes([value]) for value in wire]
    stream = Chunks(chunks) if mode == "sync" else AsyncChunks(chunks)
    provider = httpx.MockTransport(lambda request: httpx.Response(
        200, headers=headers(kind, wire), stream=stream))
    if mode == "sync":
        with httpx.Client(transport=BudgetedHTTPTransport(provider, b), trust_env=False) as client:
            response = client.get("https://fixture.invalid/official")
    else:
        async def exercise():
            async with httpx.AsyncClient(transport=BudgetedAsyncHTTPTransport(provider, b),
                                         trust_env=False) as client:
                return await client.get("https://fixture.invalid/official")
        response = loop.run_until_complete(exercise())
    assert response.content == BODY and stream.closed
    assert b.response_bytes_used == len(BODY)
    assert b.wire_response_bytes_used == len(wire)
    assert usage_receipt(b) == {"schema_version": "1.0", "response_bytes": len(BODY),
                                "cost_usd": "0"}
    if kind != "identity":
        assert "content-encoding" not in response.headers
        assert "content-length" not in response.headers
    observed = response.extensions["cwp_http_observation"]
    assert observed["status_code"] == 200 and observed["mime_type"] == "text/html"
    assert observed["content_encoding"] == headers(kind, wire)["content-encoding"]
    assert observed["wire_content_length"] == len(wire)


def test_gzip_concatenated_members_are_one_original():
    wire = gzip.compress(BODY[:30], mtime=0) + gzip.compress(BODY[30:], mtime=0)
    b = budget()
    stream = Chunks([wire[:1], wire[1:35], wire[35:]])
    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(lambda request:
        httpx.Response(200, headers=headers("gzip", wire), stream=stream)), b),
        trust_env=False) as client:
        assert client.get("https://fixture.invalid/members").content == BODY
    assert b.response_bytes_used == len(BODY) and b.wire_response_bytes_used == len(wire)
    assert stream.closed


@pytest.mark.parametrize("mutation", ["truncated", "crc", "garbage", "empty"])
def test_invalid_compressed_body_keeps_wire_meter_and_never_succeeds(mutation):
    wire = gzip.compress(BODY, mtime=0)
    if mutation == "truncated":
        wire = wire[:-5]
    elif mutation == "crc":
        wire = wire[:-8] + bytes([wire[-8] ^ 1]) + wire[-7:]
    elif mutation == "garbage":
        wire += b"trailing garbage"
    else:
        wire = b""
    b = budget()
    stream = Chunks([wire])
    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(lambda request:
        httpx.Response(200, headers=headers("gzip", wire), stream=stream)), b),
        trust_env=False) as client:
        with pytest.raises(ProviderBudgetStop) as caught:
            client.get("https://fixture.invalid/broken")
    assert caught.value.error_code == "incomplete_response"
    assert b.wire_response_bytes_used == len(wire)
    assert stream.closed


def test_compressed_bomb_materializes_at_most_entity_cap_plus_one():
    wire = gzip.compress(b"x" * 100_000, mtime=0)
    b = budget(256)
    stream = Chunks([wire])
    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(lambda request:
        httpx.Response(200, headers=headers("gzip", wire), stream=stream)), b),
        trust_env=False) as client:
        with pytest.raises(ProviderBudgetStop) as caught:
            client.get("https://fixture.invalid/bomb")
    assert caught.value.error_code == "byte_budget_exceeded"
    assert b.response_bytes_used == 257
    assert b.wire_response_bytes_used == len(wire) < 256
    assert stream.closed


def test_error_body_and_retry_share_decoded_entity_budget():
    body = b"x" * 100
    wire = gzip.compress(body, mtime=0)
    b = budget(150)
    calls = []
    def provider(request):
        calls.append(request.url.path)
        return httpx.Response(429 if len(calls) == 1 else 200,
            headers=headers("gzip", wire), stream=Chunks([wire]))
    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(provider), b),
                      trust_env=False) as client:
        assert client.get("https://fixture.invalid/first").content == body
        with pytest.raises(ProviderBudgetStop) as caught:
            client.get("https://fixture.invalid/retry")
    assert caught.value.error_code == "byte_budget_exceeded"
    assert b.response_bytes_used == 151 and b.wire_response_bytes_used == 2 * len(wire)
    assert calls == ["/first", "/retry"]


@pytest.mark.parametrize("kind", ["br", "zstd", "gzip, br"])
def test_unsupported_encoding_diagnostic_keeps_observed_headers_without_body_read(kind):
    stream = Chunks([b"not read"])
    b = budget()
    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(lambda request:
        httpx.Response(200, headers={"content-encoding": kind, "content-type": "application/pdf"},
                       stream=stream)), b), trust_env=False) as client:
        with pytest.raises(ProviderBudgetStop) as caught:
            client.get("https://fixture.invalid/unsupported")
    assert caught.value.error_code == "unsupported_content_encoding"
    assert caught.value.http_observation["content_encoding"] == kind
    assert caught.value.http_observation["status_code"] == 200
    assert b.response_bytes_used == b.wire_response_bytes_used == 0 and stream.closed


@pytest.mark.parametrize("status,method", [(200, "HEAD"), (204, "GET"), (304, "GET")])
def test_bodyless_response_does_not_decode_or_charge_resource_length(status, method):
    b = budget(3)
    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(lambda request:
        httpx.Response(status, headers={"content-encoding": "gzip", "content-length": "999999"},
                       stream=Chunks([]))), b), trust_env=False) as client:
        response = client.request(method, "https://fixture.invalid/header")
    assert response.content == b""
    assert b.response_bytes_used == b.wire_response_bytes_used == 0


def test_wire_cap_stops_before_inflation_and_records_actual_overage():
    wire = gzip.compress(bytes(range(200)), mtime=0)
    b = budget(200)
    stream = Chunks([wire])
    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(lambda request:
        httpx.Response(200, headers={"content-encoding": "gzip"}, stream=stream)), b),
        trust_env=False) as client:
        with pytest.raises(ProviderBudgetStop) as caught:
            client.get("https://fixture.invalid/wire-too-large")
    assert caught.value.error_code == "byte_budget_exceeded"
    assert b.wire_response_bytes_used == len(wire) > 200
    assert b.response_bytes_used == 0 and stream.closed


def test_async_bomb_closes_before_delivery(loop):
    wire = gzip.compress(b"x" * 100_000, mtime=0)
    b = budget(256)
    stream = AsyncChunks([wire])
    async def exercise():
        async with httpx.AsyncClient(transport=BudgetedAsyncHTTPTransport(httpx.MockTransport(lambda request:
            httpx.Response(200, headers=headers("gzip", wire), stream=stream)), b),
            trust_env=False) as client:
            with pytest.raises(ProviderBudgetStop) as caught:
                await client.get("https://fixture.invalid/async-bomb")
            return caught.value
    assert loop.run_until_complete(exercise()).error_code == "byte_budget_exceeded"
    assert b.response_bytes_used == 257 and b.wire_response_bytes_used == len(wire)
    assert stream.closed


def test_large_compressed_entity_uses_bounded_output_chunks():
    body = b"x" * 180_000
    wire = gzip.compress(body, mtime=0)
    b = budget(200_000)
    stream = Chunks([wire])
    with httpx.Client(transport=BudgetedHTTPTransport(httpx.MockTransport(lambda request:
        httpx.Response(200, headers=headers("gzip", wire), stream=stream)), b),
        trust_env=False) as client:
        with client.stream("GET", "https://fixture.invalid/large") as response:
            parts = list(response.iter_bytes())
    assert b"".join(parts) == body and max(map(len, parts)) <= 65536
    assert b.response_bytes_used == len(body) and b.wire_response_bytes_used == len(wire)


def test_async_budget_stop_closes_the_active_iterator_not_only_transport(loop):
    wire = gzip.compress(b"x" * 100_000, mtime=0)
    b = budget(256)
    class TrackedChunks(AsyncChunks):
        iterator_closed = False
        async def __aiter__(self):
            try:
                yield wire
                yield b"must not be read"
            finally:
                self.iterator_closed = True
    stream = TrackedChunks([])
    async def exercise():
        async with httpx.AsyncClient(transport=BudgetedAsyncHTTPTransport(httpx.MockTransport(lambda request:
            httpx.Response(200, headers=headers("gzip", wire), stream=stream)), b),
            trust_env=False) as client:
            with pytest.raises(ProviderBudgetStop):
                await client.get("https://fixture.invalid/close-iterator")
    loop.run_until_complete(exercise())
    assert stream.closed and stream.iterator_closed
