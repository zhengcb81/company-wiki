"""CWP-owned HTTPX transport decorators for read-only provider SDKs.

Each SDK operation shares one budget across redirects, retries and response
bodies, including failures. Prefer identity encoding, but decode valid gzip
and deflate before SDK delivery with bounded output. Wire and entity bytes
share the same configured ceiling. A wire read may overshoot by one chunk; its actual usage is retained and never accepted as a
successful download. Sync SDKs also require the parent process hard deadline:
a blocking socket cannot be interrupted by Python's per-chunk checks alone.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, AsyncIterator, Iterator
import math
import time
from typing import Any

import httpx

from .download_budget import AcquisitionBudget, AcquisitionBudgetExceeded
from .bounded_content_encoding import ContentDecoder, InvalidContentCoding


class ProviderBudgetStop(Exception):
    """Terminal abort that provider RuntimeError/HTTPError retry paths cannot eat."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.http_observation: dict[str, Any] | None = None


def usage_receipt(budget: AcquisitionBudget) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "response_bytes": budget.response_bytes_used,
        "cost_usd": str(budget.cost_usd_used),
    }


def _stop(cause: AcquisitionBudgetExceeded) -> ProviderBudgetStop:
    if "deadline" in str(cause):
        code = "deadline_exceeded"
    elif "byte budget" in str(cause):
        code = "byte_budget_exceeded"
    else:
        code = "cost_budget_exceeded"
    return ProviderBudgetStop(code, str(cause))


def _deadline(budget: AcquisitionBudget) -> None:
    try:
        budget.ensure_deadline()
    except AcquisitionBudgetExceeded as exc:
        raise _stop(exc) from exc


def _prepare(request: httpx.Request, budget: AcquisitionBudget) -> None:
    try:
        budget.ensure_new_request()
    except AcquisitionBudgetExceeded as exc:
        raise _stop(exc) from exc
    request.headers["accept-encoding"] = "identity"
    previous = request.extensions.get("timeout", {})
    remaining = budget.remaining_seconds
    request.extensions["timeout"] = {
        name: min(remaining, value) if isinstance(value, (int, float))
        and not isinstance(value, bool) and math.isfinite(value) and value > 0
        else remaining
        for name in ("connect", "read", "write", "pool")
        for value in [previous.get(name) if isinstance(previous, dict) else None]
    }


def response_observation(response: httpx.Response) -> dict[str, Any]:
    """Only finite public protocol metadata, never arbitrary provider headers."""
    length = response.headers.get("content-length", "").strip()
    size = int(length) if length.isascii() and length.isdigit() and len(length) <= 20 else None
    return {
        "status_code": response.status_code,
        "mime_type": response.headers.get("content-type", "").split(";", 1)[0].strip().lower()[:128],
        "content_encoding": response.headers.get("content-encoding", "identity").strip().lower()[:128],
        "wire_content_length": size,
    }


def _headers(request: httpx.Request, response: httpx.Response, budget: AcquisitionBudget) -> str:
    observed = response_observation(response)
    response.extensions["cwp_http_observation"] = observed
    try:
        _deadline(budget)
        bodyless = request.method == "HEAD" or response.status_code in (204, 304)
        coding = "identity" if bodyless else observed["content_encoding"] or "identity"
        if coding not in ("identity", "gzip", "deflate"):
            raise ProviderBudgetStop("unsupported_content_encoding", "unsupported HTTP content encoding")
        size = observed["wire_content_length"]
        if not bodyless and size is not None and size > budget.remaining_transport_bytes:
            raise ProviderBudgetStop("byte_budget_exceeded", "declared response exceeds remaining byte budget")
    except ProviderBudgetStop as exc:
        exc.http_observation = observed
        raise
    if coding != "identity" or bodyless:
        # The SDK receives the decoded entity; HTTPX must not inflate it again.
        response.headers.pop("content-encoding", None)
        response.headers.pop("content-length", None)
    return coding


def _record_http(
    budget: AcquisitionBudget, checkpoint: Callable[[dict[str, Any]], None] | None,
    *, wire_bytes: int = 0, response_bytes: int = 0,
) -> None:
    try:
        budget.consume_http_bytes(wire_bytes=wire_bytes, response_bytes=response_bytes)
    except AcquisitionBudgetExceeded as exc:
        raise _stop(exc) from exc
    finally:
        if checkpoint is not None:
            checkpoint(usage_receipt(budget))
    _deadline(budget)


def _decode_chunk(chunk: bytes, decoder: ContentDecoder, budget, checkpoint) -> Iterator[bytes]:
    identity = decoder.coding == "identity"
    _record_http(budget, checkpoint, wire_bytes=len(chunk),
                 response_bytes=len(chunk) if identity else 0)
    if identity:
        if chunk:
            yield chunk
        return
    try:
        for entity in decoder.feed(chunk, lambda: budget.remaining_response_bytes + 1):
            _record_http(budget, checkpoint, response_bytes=len(entity))
            yield entity
    except InvalidContentCoding as exc:
        raise ProviderBudgetStop("incomplete_response", "invalid compressed HTTP body") from exc


def _finish(decoder: ContentDecoder, budget: AcquisitionBudget) -> None:
    _deadline(budget)
    try:
        decoder.finish()
    except InvalidContentCoding as exc:
        raise ProviderBudgetStop("incomplete_response", "incomplete compressed HTTP body") from exc


class _SyncStream(httpx.SyncByteStream):
    def __init__(self, stream, budget, checkpoint, coding):
        self.stream, self.budget, self.checkpoint = stream, budget, checkpoint
        self.decoder = ContentDecoder(coding)
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        iterator = iter(self.stream)
        try:
            while True:
                _deadline(self.budget)
                try:
                    chunk = next(iterator)
                except StopIteration:
                    _finish(self.decoder, self.budget)
                    return
                yield from _decode_chunk(chunk, self.decoder, self.budget, self.checkpoint)
        finally:
            try:
                close_iterator = getattr(iterator, "close", None)
                if close_iterator is not None:
                    close_iterator()
            finally:
                self.close()

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.stream.close()


class _AsyncStream(httpx.AsyncByteStream):
    def __init__(self, stream, budget, checkpoint, coding):
        self.stream, self.budget, self.checkpoint = stream, budget, checkpoint
        self.decoder = ContentDecoder(coding)
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        iterator = self.stream.__aiter__()
        try:
            while True:
                _deadline(self.budget)
                try:
                    chunk = await asyncio.wait_for(iterator.__anext__(), self.budget.remaining_seconds)
                except StopAsyncIteration:
                    _finish(self.decoder, self.budget)
                    return
                except asyncio.TimeoutError as exc:
                    raise ProviderBudgetStop("deadline_exceeded", "acquisition deadline exceeded") from exc
                for entity in _decode_chunk(chunk, self.decoder, self.budget, self.checkpoint):
                    yield entity
        finally:
            try:
                close_iterator = getattr(iterator, "aclose", None)
                if close_iterator is not None:
                    await close_iterator()
            finally:
                await self.aclose()

    async def aclose(self) -> None:
        if not self.closed:
            self.closed = True
            await self.stream.aclose()


class BudgetedHTTPTransport(httpx.BaseTransport):
    def __init__(
        self, transport: httpx.BaseTransport, budget: AcquisitionBudget, *,
        checkpoint: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.transport, self.budget, self.checkpoint = transport, budget, checkpoint

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        _prepare(request, self.budget)
        response = self.transport.handle_request(request)
        try:
            coding = _headers(request, response, self.budget)
        except BaseException:
            response.close()
            raise
        response.stream = _SyncStream(response.stream, self.budget, self.checkpoint, coding)
        return response

    def close(self) -> None:
        self.transport.close()


class BudgetedAsyncHTTPTransport(httpx.AsyncBaseTransport):
    def __init__(
        self, transport: httpx.AsyncBaseTransport, budget: AcquisitionBudget, *,
        checkpoint: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.transport, self.budget, self.checkpoint = transport, budget, checkpoint

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        _prepare(request, self.budget)
        try:
            response = await asyncio.wait_for(
                self.transport.handle_async_request(request), self.budget.remaining_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise ProviderBudgetStop("deadline_exceeded", "acquisition deadline exceeded") from exc
        try:
            coding = _headers(request, response, self.budget)
        except BaseException:
            await response.aclose()
            raise
        response.stream = _AsyncStream(response.stream, self.budget, self.checkpoint, coding)
        return response

    async def aclose(self) -> None:
        await self.transport.aclose()


def bounded_sleep(
    budget: AcquisitionBudget, seconds: float, *, sleep: Callable[[float], None] = time.sleep,
) -> None:
    """HK SDK retry callback; a retry beyond the operation deadline is terminal."""
    _deadline(budget)
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("retry sleep must be finite and non-negative")
    if seconds >= budget.remaining_seconds:
        raise ProviderBudgetStop("deadline_exceeded", "retry sleep exceeds acquisition deadline")
    sleep(seconds)
    _deadline(budget)
