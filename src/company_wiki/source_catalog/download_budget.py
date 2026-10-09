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
    usage_complete: bool = True
    # Evidence metadata over the EXISTING counters, not another ledger.
    provider_started: bool | None = False
    failure_usage_complete: bool | None = True
    usage_reported: bool = False
    wire_response_bytes_used: int = 0
    wire_usage_complete: bool = True

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
            or self.response_bytes_used < 0
        ):
            raise ValueError("response_bytes_used must be a non-negative integer")
        if (isinstance(self.wire_response_bytes_used, bool)
                or not isinstance(self.wire_response_bytes_used, int)
                or self.wire_response_bytes_used < 0):
            raise ValueError("wire byte count must be a non-negative integer")
        if not isinstance(self.wire_usage_complete, bool):
            raise TypeError("wire_usage_complete must be bool")
        if self.response_bytes_used and not self.wire_response_bytes_used:
            self.wire_usage_complete = False
        self.max_cost_usd = _decimal_amount(self.max_cost_usd, "max_cost_usd")
        self.cost_usd_used = _decimal_amount(self.cost_usd_used, "cost_usd_used")
        if not isinstance(self.usage_complete, bool):
            raise TypeError("usage_complete must be bool")
        if not self.usage_complete:
            self.failure_usage_complete = False
            if self.provider_started is False:
                self.provider_started = None
        if self.response_bytes_used > 0 or self.cost_usd_used > 0:
            self.usage_reported = True
            self.provider_started = True

    def observe_provider(self, *, started: bool | None, complete: bool | None) -> None:
        """Merge invocation proof monotonically over the whole operation."""
        if started is True:
            self.provider_started = True
        elif started is None and self.provider_started is not True:
            self.provider_started = None
        if complete is False:
            self.failure_usage_complete = False
        elif complete is None and self.failure_usage_complete is not False:
            self.failure_usage_complete = None
        if complete is not True:
            self.usage_complete = False  # Existing policy: no unknown-charge retry.

    def _reported(self) -> None:
        self.usage_reported = True

    @property
    def remaining_response_bytes(self) -> int:
        return max(0, self.max_response_bytes - self.response_bytes_used)

    @property
    def remaining_wire_bytes(self) -> int:
        return max(0, self.max_response_bytes - self.wire_response_bytes_used)

    @property
    def remaining_transport_bytes(self) -> int:
        return min(self.remaining_response_bytes, self.remaining_wire_bytes)

    @property
    def remaining_cost_usd(self) -> Decimal:
        return max(Decimal("0"), self.max_cost_usd - self.cost_usd_used)

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.deadline_monotonic - time.monotonic())

    def ensure_open(self) -> None:
        """Check operation limits; finishing exactly at the cap is valid."""
        self.ensure_deadline()
        if not self.usage_complete:
            raise AcquisitionBudgetExceeded("acquisition usage incomplete after provider failure")
        if self.response_bytes_used > self.max_response_bytes:
            raise AcquisitionBudgetExceeded("response byte budget exceeded")
        if self.wire_response_bytes_used > self.max_response_bytes:
            raise AcquisitionBudgetExceeded("wire response byte budget exceeded")
        if self.cost_usd_used > self.max_cost_usd:
            raise AcquisitionBudgetExceeded("acquisition cost budget exceeded")

    def ensure_new_request(self) -> None:
        """Gate provider work; a zero cost ceiling still allows free requests."""
        self.ensure_open()
        if self.remaining_transport_bytes == 0:
            raise AcquisitionBudgetExceeded("response byte budget exhausted")

    def ensure_deadline(self) -> None:
        """Check time while reading an already-open response."""
        if time.monotonic() >= self.deadline_monotonic:
            raise AcquisitionBudgetExceeded("acquisition deadline exceeded")

    def record_reported_usage(
        self, *, response_bytes: int, cost_usd: Decimal | str, wire_bytes: int | None = None
    ) -> None:
        """Record actual usage atomically, then reject an exceeded ceiling.

        This is accounting, not a reservation: already read bytes and billed
        cost cannot be undone. A failed budget may therefore retain an overage.
        Both values are validated before either counter changes, and both are
        recorded even when one exceeds its cap. Never clamp actual usage.
        """
        if (
            isinstance(response_bytes, bool)
            or not isinstance(response_bytes, int)
            or response_bytes < 0
        ):
            raise ValueError("response byte count must be a non-negative integer")
        cost = _decimal_amount(cost_usd, "cost")
        if wire_bytes is not None and (isinstance(wire_bytes, bool)
                or not isinstance(wire_bytes, int) or wire_bytes < 0):
            raise ValueError("wire byte count must be a non-negative integer")
        self._reported()
        if response_bytes > 0 or cost > 0:
            self.observe_provider(started=True, complete=True)
        self.response_bytes_used += response_bytes
        self.cost_usd_used += cost
        if wire_bytes is None:
            self.wire_usage_complete = False
        else:
            self.wire_response_bytes_used += wire_bytes
        if self.response_bytes_used > self.max_response_bytes:
            raise AcquisitionBudgetExceeded("response byte budget exceeded")
        if self.wire_response_bytes_used > self.max_response_bytes:
            raise AcquisitionBudgetExceeded("wire response byte budget exceeded")
        if self.cost_usd_used > self.max_cost_usd:
            raise AcquisitionBudgetExceeded("acquisition cost budget exceeded")

    def consume_response_bytes(self, count: int) -> None:
        """Record response bytes already consumed by the provider.

        Deadline checks gate new provider work via ``ensure_open``. Accounting
        must still accept a usage receipt returned just after that deadline.
        """
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("response byte count must be a non-negative integer")
        self._reported()
        if count > 0:
            self.observe_provider(started=True, complete=True)
        self.response_bytes_used += count
        if self.response_bytes_used > self.max_response_bytes:
            raise AcquisitionBudgetExceeded("response byte budget exceeded")

    def consume_cost_usd(self, amount: Decimal | str) -> None:
        """Record reported provider cost, even if the call crossed deadline."""
        cost = _decimal_amount(amount, "cost")
        self._reported()
        if cost > 0:
            self.observe_provider(started=True, complete=True)
        self.cost_usd_used += cost
        if self.cost_usd_used > self.max_cost_usd:
            raise AcquisitionBudgetExceeded("acquisition cost budget exceeded")

    def consume_http_bytes(self, *, wire_bytes: int, response_bytes: int = 0) -> None:
        """Account consumed wire and materialized entity atomically, even late.

        Identity bodies use both counters in one call so an overage never
        erases their actual entity usage. Compressed wire is accounted before
        bounded inflation; entity bytes are counted only when materialized.
        """
        for count in (wire_bytes, response_bytes):
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("HTTP byte count must be a non-negative integer")
        self._reported()
        if wire_bytes or response_bytes:
            self.observe_provider(started=True, complete=True)
        self.wire_response_bytes_used += wire_bytes
        self.response_bytes_used += response_bytes
        if self.response_bytes_used > self.max_response_bytes:
            raise AcquisitionBudgetExceeded("response byte budget exceeded")
        if self.wire_response_bytes_used > self.max_response_bytes:
            raise AcquisitionBudgetExceeded("wire response byte budget exceeded")
