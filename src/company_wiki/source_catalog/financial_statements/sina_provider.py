"""Sina CompanyFinanceService provider: fixed endpoint, bounded pagination.

One :class:`~company_wiki.source_catalog.download_budget.AcquisitionBudget` is
shared by every page request of one acquisition operation. The provider only
builds URLs from one verified exchange+code identity — callers never pass
arbitrary URLs. Every termination is named; no hidden retries exist.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Sequence

import httpx

from company_wiki.source_catalog.bounded_http import (
    BudgetedHTTPTransport,
    ProviderBudgetStop,
)
from company_wiki.source_catalog.download_budget import AcquisitionBudget

from . import normalize
from .contracts import STATEMENT_PROVIDER_SOURCES

SINA_ENDPOINT = (
    "https://quotes.sina.cn/cn/api/openapi.php/"
    "CompanyFinanceService.getFinanceReport2022"
)
SINA_PROVIDER_ID = "sina_finance"
SINA_PUBLISHER = "新浪财经"
PROBE_USER_AGENT = "Mozilla/5.0 (research probe W19)"

_EXCHANGE_PREFIX = {"SSE": "sh", "SZSE": "sz", "BSE": "bj"}

_REPORT_TYPE_PARAM = {
    ("annual",): "4",
    ("semi_annual",): "2",
    ("q3",): "3",
    ("q1",): "1",
}

_ALL_REPORT_TYPES = ("annual", "semi_annual", "q1", "q3")


class SinaProviderError(RuntimeError):
    """Named provider refusal (never a payload echo)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class FetchedPage:
    page_number: int
    url: str
    raw_bytes: bytes
    sha256: str
    statement_source: str
    report_count: int | None
    periods: tuple[str, ...]

    def normalized(self, statement_type: str) -> normalize.NormalizedPage:
        return normalize.normalize_page(
            self.raw_bytes, statement_type=statement_type, page_number=self.page_number
        )


@dataclass(frozen=True)
class StatementFetchResult:
    statement_type: str
    provider: str = SINA_PROVIDER_ID
    publisher: str = SINA_PUBLISHER
    exchange: str = ""
    code: str = ""
    paper_code: str = ""
    pages: tuple[FetchedPage, ...] = ()
    observed_period_count: int | None = None
    terminal_reason: str = "complete"
    error_code: str | None = None
    http_exchanges: int = 0
    response_bytes: int = 0
    cost_usd: str = "0.00"
    detail: str | None = None

    @property
    def unique_periods_list(self) -> list[str]:
        seen: dict[str, None] = {}
        for page in self.pages:
            for period in page.periods:
                seen.setdefault(period, None)
        return sorted(seen, reverse=True)

    @property
    def unique_periods(self) -> int:
        return len(self.unique_periods_list)


def _type_param(report_types: Sequence[str] | None) -> str:
    if report_types is None or tuple(report_types) == _ALL_REPORT_TYPES:
        return "0"
    return _REPORT_TYPE_PARAM.get(tuple(report_types), "0")


class SinaStatementsProvider:
    """Bounded multi-page reader for one company statement on the fixed endpoint."""

    def __init__(
        self,
        http_client_factory: Callable[[AcquisitionBudget], httpx.Client] | None = None,
    ):
        self._http_client_factory = http_client_factory

    def _client(self, budget: AcquisitionBudget) -> httpx.Client:
        if self._http_client_factory is not None:
            return self._http_client_factory(budget)
        return httpx.Client(
            transport=BudgetedHTTPTransport(httpx.HTTPTransport(), budget)
        )

    def fetch_statement(
        self,
        *,
        exchange: str,
        code: str,
        statement_type: str,
        report_types: Sequence[str] | None = None,
        max_pages: int = 64,
        page_size: int = 10,
        budget: AcquisitionBudget,
        stop_before_period: str | None = None,
    ) -> StatementFetchResult:
        if not isinstance(exchange, str) or exchange.upper() not in _EXCHANGE_PREFIX:
            raise SinaProviderError(
                "unsupported_exchange", f"exchange {exchange!r} has no Sina paper code"
            )
        if not isinstance(code, str) or not code.isdigit() or not 1 <= len(code) <= 8:
            raise SinaProviderError("invalid_security_code", "code must be digits")
        if statement_type not in STATEMENT_PROVIDER_SOURCES:
            raise SinaProviderError(
                "unsupported_statement", f"statement {statement_type!r} unknown"
            )
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
            raise ValueError("max_pages must be a positive integer")
        if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
            raise ValueError("page_size must be a positive integer")
        if stop_before_period is not None and (
            not isinstance(stop_before_period, str) or len(stop_before_period) != 8
        ):
            raise ValueError("stop_before_period must be YYYYMMDD")

        prefix = _EXCHANGE_PREFIX[exchange.upper()]
        paper_code = f"{prefix}{code}"
        source_key = STATEMENT_PROVIDER_SOURCES[statement_type]
        type_param = _type_param(report_types)

        pages: list[FetchedPage] = []
        seen_periods: set[str] = set()
        previous_periods: frozenset[str] | None = None
        previous_count: int | None = None
        terminal = "complete"
        error_code: str | None = None
        detail: str | None = None

        def usage(**overrides: Any) -> StatementFetchResult:
            return StatementFetchResult(
                statement_type=statement_type,
                exchange=exchange.upper(),
                code=code,
                paper_code=paper_code,
                pages=tuple(pages),
                observed_period_count=next(
                    (page.report_count for page in pages if page.report_count is not None),
                    None,
                ),
                terminal_reason=terminal,
                error_code=error_code,
                http_exchanges=budget.http_exchanges_used,
                response_bytes=budget.response_bytes_used,
                cost_usd=str(budget.cost_usd_used.quantize(Decimal("0.01")))
                if budget.cost_usd_used
                else "0.00",
                detail=detail,
                **overrides,
            )

        client = self._client(budget)
        try:
            page_number = 1
            while page_number <= max_pages:
                if pages and stop_before_period is not None:
                    if min(pages[-1].periods) < stop_before_period:
                        terminal = "period_boundary"
                        return usage()
                params = {
                    "paperCode": paper_code,
                    "source": source_key,
                    "type": type_param,
                    "page": str(page_number),
                    "num": str(page_size),
                }
                try:
                    response = client.get(
                        SINA_ENDPOINT,
                        params=params,
                        headers={"user-agent": PROBE_USER_AGENT},
                    )
                except ProviderBudgetStop as exc:
                    terminal = "budget_stopped"
                    error_code = exc.error_code
                    detail = str(exc)
                    return usage()
                except httpx.HTTPError as exc:
                    terminal = "provider_error"
                    error_code = "http_error"
                    detail = f"{type(exc).__name__}"
                    return usage()
                if response.status_code == 403:
                    terminal = "provider_error"
                    error_code = "forbidden"
                    return usage()
                if response.status_code == 429:
                    terminal = "provider_error"
                    error_code = "too_many_requests"
                    return usage()
                if response.status_code != 200:
                    terminal = "provider_error"
                    error_code = "http_error"
                    detail = f"status={response.status_code}"
                    return usage()
                raw = response.content
                try:
                    page = normalize.normalize_page(
                        raw, statement_type=statement_type, page_number=page_number
                    )
                except normalize.NormalizeProtocolError as exc:
                    terminal = "provider_error"
                    error_code = "protocol_error"
                    detail = str(exc)
                    return usage()
                if not page.page_had_data:
                    terminal = "no_data" if page_number == 1 else "end_of_data"
                    return usage()
                if previous_count is not None and page.report_count != previous_count:
                    # The provider's advertised history changed mid-pagination;
                    # committing this page against the old count would be a lie.
                    terminal = "count_changed"
                    detail = (
                        f"report_count {previous_count}->{page.report_count}"
                    )
                    return usage()
                page_periods = frozenset(
                    report.period_end_compact for report in page.reports
                )
                new_periods = page_periods - seen_periods
                if page_number > 1 and not new_periods:
                    # The page was fetched (bytes are real) and stays in the
                    # result; pagination stops because it adds nothing.
                    url = str(response.request.url)
                    pages.append(
                        FetchedPage(
                            page_number=page_number,
                            url=url,
                            raw_bytes=raw,
                            sha256=hashlib.sha256(raw).hexdigest(),
                            statement_source=source_key,
                            report_count=page.report_count,
                            periods=tuple(sorted(page_periods, reverse=True)),
                        )
                    )
                    terminal = (
                        "duplicate_page"
                        if page_periods == previous_periods
                        else "no_progress"
                    )
                    return usage()
                url = str(response.request.url)
                pages.append(
                    FetchedPage(
                        page_number=page_number,
                        url=url,
                        raw_bytes=raw,
                        sha256=hashlib.sha256(raw).hexdigest(),
                        statement_source=source_key,
                        report_count=page.report_count,
                        periods=tuple(
                            sorted(page_periods, reverse=True)
                        ),
                    )
                )
                seen_periods |= page_periods
                previous_periods = page_periods
                previous_count = page.report_count
                page_number += 1
            terminal = "max_pages"
            return usage()
        finally:
            client.close()


__all__ = [
    "FetchedPage",
    "PROBE_USER_AGENT",
    "SINA_ENDPOINT",
    "SINA_PUBLISHER",
    "SINA_PROVIDER_ID",
    "SinaProviderError",
    "SinaStatementsProvider",
    "StatementFetchResult",
]
