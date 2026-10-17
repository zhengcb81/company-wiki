"""Call-local work accounting shared by extraction and reading.

Scopes tighten a phase's ceiling while charging the same parent account before
work. They never clone the parent's remaining balance or reset exhaustion.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# One composed PDF attempt includes source planning and several semantic
# stages. A real 283-page offering uses about 9.2M operations across them;
# 2M was the old standalone layout default, not a whole-document envelope.
# This is local algorithm work, never the separate LLM token/cost allowance.
DEFAULT_DOCUMENT_WORK_LIMIT = 16_000_000


def new_document_work_budget() -> WorkBudget:
    return WorkBudget(DEFAULT_DOCUMENT_WORK_LIMIT)


class WorkBudgetExceeded(RuntimeError):
    """The caller must retain an honest partial result and stop this work."""


@dataclass
class WorkBudget:
    max_work_units: int
    used: int = 0
    exhausted: bool = False
    _parent: WorkBudget | None = field(default=None, repr=False, compare=False)

    def charge(self, n: int = 1) -> bool:
        if n < 0:
            raise ValueError("work charge must be non-negative")
        if self.exhausted or self.used + n > self.max_work_units:
            self.exhausted = True
            raise WorkBudgetExceeded("layout analysis work limit reached")
        if self._parent is not None:
            try:
                self._parent.charge(n)
            except WorkBudgetExceeded:
                self.exhausted = True
                raise
        self.used += n
        return True

    def scoped(self, max_work_units: int) -> WorkBudget:
        if type(max_work_units) is not int or max_work_units < 0:
            raise ValueError("scope ceiling must be a non-negative integer")
        return WorkBudget(min(max_work_units, self.max_work_units), _parent=self)
