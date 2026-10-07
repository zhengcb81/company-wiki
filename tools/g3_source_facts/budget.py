"""Bounded read budget shared by metadata hashing and the RAW-DUP rounds.

Card rules: 512 MiB total for original-byte reads (re-reads are charged again),
each RAW-DUP round at most 20 groups / 256 MiB / 120 s, two rounds may not sum
past the total, and crossing the budget stops the run (partial) instead of
reporting completeness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TOTAL_READ_BUDGET_BYTES = 512 * 1024 * 1024
RAW_DUP_MAX_READ_BYTES = 256 * 1024 * 1024
RAW_DUP_MAX_GROUPS = 20
RAW_DUP_DEADLINE_SECONDS = 120.0
RAW_DUP_MAX_ROUNDS = 2
RAW_DUP_MAX_DETAIL_ROWS = 100


class BudgetExceeded(RuntimeError):
    """Raised when a read would cross the lane budget; the run must stop."""


@dataclass
class ReadCharge:
    label: str
    nbytes: int


@dataclass
class ReadBudget:
    total_limit: int = TOTAL_READ_BUDGET_BYTES
    raw_dup_round_cap: int = RAW_DUP_MAX_READ_BYTES
    consumed: int = 0
    charges: list[ReadCharge] = field(default_factory=list)
    hit: bool = False

    @property
    def remaining(self) -> int:
        return max(0, self.total_limit - self.consumed)

    @property
    def exhausted(self) -> bool:
        return self.hit or self.remaining == 0

    @property
    def complete(self) -> bool:
        return not self.hit

    @property
    def status(self) -> str:
        return "partial" if self.hit else "complete"

    def charge(self, nbytes: int, *, label: str) -> int:
        if nbytes < 0:
            raise ValueError("nbytes must be non-negative")
        if self.hit:
            self.charges.append(ReadCharge(label=label, nbytes=0))
            raise BudgetExceeded(f"budget already stopped ({label})")
        if nbytes > self.remaining:
            self.hit = True
            self.charges.append(ReadCharge(label=label, nbytes=0))
            raise BudgetExceeded(
                f"{label} needs {nbytes} bytes but only {self.remaining} remain"
            )
        self.consumed += nbytes
        self.charges.append(ReadCharge(label=label, nbytes=nbytes))
        return nbytes

    def try_charge(self, nbytes: int, *, label: str) -> bool:
        try:
            self.charge(nbytes, label=label)
        except BudgetExceeded:
            return False
        return True

    def raw_dup_round_limit(self) -> int:
        return min(self.remaining, self.raw_dup_round_cap)

    def summary(self) -> dict:
        return {
            "total_limit_bytes": self.total_limit,
            "consumed_bytes": self.consumed,
            "remaining_bytes": self.remaining,
            "status": self.status,
            "raw_dup_round_limit_bytes": self.raw_dup_round_limit(),
            "charges": [{"label": c.label, "bytes": c.nbytes} for c in self.charges],
        }
