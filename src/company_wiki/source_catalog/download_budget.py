"""Per-operation acquisition budget shared by discovery and download."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import math
import time


class AcquisitionBudgetExceeded(RuntimeError):
    """Raised when a provider attempts to exceed its operation budget."""


def _decimal_amount(value: Decimal | str, name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, str)):
        raise TypeError(f"{name} must be Decimal or decimal text")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a finite non-negative decimal") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{name} must be a finite non-negative decimal")
    return amount


@dataclass(slots=True)
class AcquisitionBudget:
    """One shared byte, deadline, and cost ceiling for provider egress.

    ``deadline_monotonic`` uses ``time.monotonic()`` and must be created once
    for the whole ensure/close-gap operation. Budgeted adapters must check the
    deadline and charge response bytes/cost while reading, before accepting
    each chunk. CWP validates the final receipt as a second line of defense.
    """

    max_response_bytes: int
    deadline_monotonic: float
    max_cost_usd: Decimal | str
    response_bytes_used: int = 0
    cost_usd_used: Decimal = field(default=Decimal("0"))

    @classmethod
    def from_limits(
        cls,
        *,
        max_response_bytes: int,
        max_seconds: float,
        max_cost_usd: Decimal | str,
    ) -> AcquisitionBudget:
        if (
            isinstance(max_seconds, bool)
            or not isinstance(max_seconds, (int, float))
            or not math.isfinite(max_seconds)
            or max_seconds <= 0
        ):
            raise ValueError("max_seconds must be a finite positive number")
        return cls(
            max_response_bytes=max_response_bytes,
            deadline_monotonic=time.monotonic() + float(max_seconds),
            max_cost_usd=max_cost_usd,
        )

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_response_bytes, bool)
            or not isinstance(self.max_response_bytes, int)
            or self.max_response_bytes <= 0
        ):
            raise ValueError("max_response_bytes must be a positive integer")
        if (
            isinstance(self.deadline_monotonic, bool)
            or not isinstance(self.deadline_monotonic, (int, float))
            or not math.isfinite(self.deadline_monotonic)
            or self.deadline_monotonic <= 0
        ):
            raise ValueError("deadline_monotonic must be a finite positive number")
        if (
            isinstance(self.response_bytes_used, bool)
            or not isinstance(self.response_bytes_used, int)
            or not 0 <= self.response_bytes_used <= self.max_response_bytes
        ):
            raise ValueError("response_bytes_used must be within the byte ceiling")
        self.max_cost_usd = _decimal_amount(self.max_cost_usd, "max_cost_usd")
        self.cost_usd_used = _decimal_amount(self.cost_usd_used, "cost_usd_used")
        if self.cost_usd_used > self.max_cost_usd:
            raise ValueError("cost_usd_used must be within the cost ceiling")

    @property
    def remaining_response_bytes(self) -> int:
        return self.max_response_bytes - self.response_bytes_used

    @property
    def remaining_cost_usd(self) -> Decimal:
        return self.max_cost_usd - self.cost_usd_used

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.deadline_monotonic - time.monotonic())

    def ensure_open(self) -> None:
        if time.monotonic() >= self.deadline_monotonic:
            raise AcquisitionBudgetExceeded("acquisition deadline exceeded")

    def consume_response_bytes(self, count: int) -> None:
        """Record response bytes already consumed by the provider.

        Deadline checks gate new provider work via ``ensure_open``. Accounting
        must still accept a usage receipt returned just after that deadline.
        """
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("response byte count must be a non-negative integer")
        if count > self.remaining_response_bytes:
            raise AcquisitionBudgetExceeded("response byte budget exceeded")
        self.response_bytes_used += count

    def consume_cost_usd(self, amount: Decimal | str) -> None:
        """Record reported provider cost, even if the call crossed deadline."""
        cost = _decimal_amount(amount, "cost")
        if cost > self.remaining_cost_usd:
            raise AcquisitionBudgetExceeded("acquisition cost budget exceeded")
        self.cost_usd_used += cost
