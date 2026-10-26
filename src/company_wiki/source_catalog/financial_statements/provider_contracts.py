"""Provider-independent acquisition port and source-page observations; no I/O."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Sequence, TYPE_CHECKING
from ..download_budget import AcquisitionBudget
from .contracts import SINA_PROVIDER_ID, SINA_PUBLISHER
if TYPE_CHECKING:
    from .normalize import NormalizedPage

class StatementProviderError(RuntimeError):
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

    def normalized(self, statement_type: str) -> NormalizedPage:
        from .normalize import normalize_page
        return normalize_page(
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



class StatementsProvider(Protocol):
    def fetch_statement(self, *, exchange: str, code: str, statement_type: str,
        report_types: Sequence[str] | None = None, max_pages: int = 64,
        page_size: int = 10, budget: AcquisitionBudget,
        stop_before_period: str | None = None) -> StatementFetchResult: ...
