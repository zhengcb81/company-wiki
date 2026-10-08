"""CWP-owned HTTPX transport decorators for read-only provider SDKs.

Each SDK operation shares one budget across redirects, retries and response
bodies, including failures. Force identity encoding so bytes charged here are
the same bytes used for the eventual immutable file. A read may overshoot by
one underlying chunk; its actual usage is retained and never accepted as a
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


class ProviderBudgetStop(Exception):
    """Terminal abort that provider RuntimeError/HTTPError retry paths cannot eat."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


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


def _headers(request: httpx.Request, response: httpx.Response, budget: AcquisitionBudget) -> None:
    _deadline(budget)
    if request.method == "HEAD" or response.status_code in (204, 304):
        return
    if response.headers.get("content-encoding", "identity").strip().lower() not in ("", "identity"):
        raise ProviderBudgetStop(
            "unsupported_content_encoding", "provider ignored identity content encoding"
        )
    length = response.headers.get("content-length")
    if length is not None:
        try:
            size = int(length)
        except ValueError:
            size = -1  # Missing/invalid length is still checked while reading.
        if size > budget.remaining_response_bytes:
            raise ProviderBudgetStop(
                "byte_budget_exceeded", "declared response exceeds remaining byte budget"
            )


def _record(
    chunk: bytes, budget: AcquisitionBudget,
    checkpoint: Callable[[dict[str, Any]], None] | None,
) -> None:
    try:
        budget.consume_response_bytes(len(chunk))
    except AcquisitionBudgetExceeded as exc:
        raise _stop(exc) from exc
    finally:
        if checkpoint is not None:
            checkpoint(usage_receipt(budget))
    _deadline(budget)


class _SyncStream(httpx.SyncByteStream):
    def __init__(self, stream, budget, checkpoint):
        self.stream, self.budget, self.checkpoint = stream, budget, checkpoint

    def __iter__(self) -> Iterator[bytes]:
        iterator = iter(self.stream)
        while True:
            _deadline(self.budget)
            try:
                chunk = next(iterator)
            except StopIteration:
                return
            _record(chunk, self.budget, self.checkpoint)
            yield chunk

    def close(self) -> None:
        self.stream.close()


class _AsyncStream(httpx.AsyncByteStream):
    def __init__(self, stream, budget, checkpoint):
        self.stream, self.budget, self.checkpoint = stream, budget, checkpoint

    async def __aiter__(self) -> AsyncIterator[bytes]:
        iterator = self.stream.__aiter__()
        while True:
            _deadline(self.budget)
            try:
                chunk = await asyncio.wait_for(iterator.__anext__(), self.budget.remaining_seconds)
            except StopAsyncIteration:
                return
            except asyncio.TimeoutError as exc:
                raise ProviderBudgetStop("deadline_exceeded", "acquisition deadline exceeded") from exc
            _record(chunk, self.budget, self.checkpoint)
            yield chunk

    async def aclose(self) -> None:
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
            _headers(request, response, self.budget)
        except BaseException:
            response.close()
            raise
        response.stream = _SyncStream(response.stream, self.budget, self.checkpoint)
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
            _headers(request, response, self.budget)
        except BaseException:
            await response.aclose()
            raise
        response.stream = _AsyncStream(response.stream, self.budget, self.checkpoint)
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
