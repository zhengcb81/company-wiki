"""Logical stage reservations for structure, not Python-operation proxies.

The same caller budget pays input visits/text blocks, linear stage passes and
n*bit_length(n) sorting work before the stage. Pair expansion reserves its actual candidate
cardinality and graph traversal charges visits in relations. These are logical enhancement
work units, not an instruction counter or a wall-clock cancellation mechanism;
regex implementation time remains outside that guarantee.
"""

from __future__ import annotations
from dataclasses import dataclass
from ..layout_hints.contract import WorkBudget


def reserve(budget: WorkBudget | None, count: int = 1) -> None:
    if budget is not None:
        budget.charge(count)


@dataclass
class WorkPlan:
    budget: WorkBudget
    units: int = 0
    text_blocks: int = 0

    def observe(self, text: str) -> None:
        blocks = (len(text) + 63) // 64
        self.budget.charge(1 + blocks)
        self.units += 1
        self.text_blocks += blocks

    def stage(self, *, passes: int, sorts: int = 0) -> None:
        self.budget.charge(
            passes * (self.units + self.text_blocks)
            + sorts * self.units * self.units.bit_length()
        )
