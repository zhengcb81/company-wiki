"""Call-local work accounting shared by extraction and reading.

Scopes tighten a phase's ceiling while charging the same parent account before
work. They never clone the parent's remaining balance or reset exhaustion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

import yaml

# One composed PDF attempt includes source planning and several semantic
# stages. A real 283-page offering uses about 9.2M operations across them;
# 2M was the old standalone layout default, not a whole-document envelope.
# This is local algorithm work, never the separate LLM token/cost allowance.
DEFAULT_DOCUMENT_WORK_LIMIT = 16_000_000
BUDGET_POLICY_SCHEMA = "company-wiki-budget-policy/1"


@dataclass(frozen=True)
class BudgetPolicy:
    """Current ceilings and soft allocations; never a charge ledger."""

    cumulative_tokens: int
    cumulative_micro_usd: int
    company_token_target: int
    company_micro_usd_target: int
    document_work_limit: int


def budget_policy_path(policy_path: str | Path | None = None) -> Path:
    """Explicit selection wins; an invalid selected file never falls back."""
    if policy_path is not None:
        return Path(policy_path)
    selected = os.environ.get("COMPANY_WIKI_BUDGET_CONFIG")
    return Path(selected) if selected is not None else (
        Path(__file__).resolve().parents[2] / "config" / "resource_budget.yaml")


def _nonnegative_int(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def load_budget_policy(policy_path: str | Path | None = None) -> BudgetPolicy:
    """Read one resource configuration, independently of historical usage."""
    path = budget_policy_path(policy_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != BUDGET_POLICY_SCHEMA:
        raise ValueError(f"budget config must declare {BUDGET_POLICY_SCHEMA}: {path}")
    sections = {}
    for name in ("external_model", "company_allocation", "document_processing"):
        value = raw.get(name)
        if not isinstance(value, dict):
            raise ValueError(f"budget config needs {name}: {path}")
        sections[name] = value
    company = sections["company_allocation"]
    if company.get("enforcement") != "soft":
        raise ValueError("company_allocation.enforcement must be soft")
    external, document = sections["external_model"], sections["document_processing"]
    return BudgetPolicy(
        _nonnegative_int(external.get("cumulative_tokens"), "external_model.cumulative_tokens"),
        _nonnegative_int(external.get("cumulative_micro_usd"), "external_model.cumulative_micro_usd"),
        _nonnegative_int(company.get("target_tokens"), "company_allocation.target_tokens"),
        _nonnegative_int(company.get("target_micro_usd"), "company_allocation.target_micro_usd"),
        _nonnegative_int(document.get("max_work_units"), "document_processing.max_work_units"),
    )


def new_document_work_budget(*, max_work_units: int | None = None,
                             policy_path: str | Path | None = None,
                             phase: str = "document") -> WorkBudget:
    limit = (load_budget_policy(policy_path).document_work_limit
             if max_work_units is None else max_work_units)
    return WorkBudget(limit, phase=phase)


class WorkBudgetExceeded(RuntimeError):
    """The caller must retain an honest partial result and stop this work."""

    def __init__(self, message: str, *, phase: str | None = None,
                 used: int | None = None, requested: int | None = None,
                 limit: int | None = None):
        super().__init__(message)
        self.dimension = "document_work"
        self.phase = phase
        self.used, self.requested, self.limit = used, requested, limit


@dataclass
class WorkBudget:
    max_work_units: int
    used: int = 0
    exhausted: bool = False
    _parent: WorkBudget | None = field(default=None, repr=False, compare=False)
    phase: str = "document"

    def __post_init__(self) -> None:
        _nonnegative_int(self.max_work_units, "max_work_units")
        _nonnegative_int(self.used, "used")
        if self.used > self.max_work_units:
            raise ValueError("used must not exceed max_work_units")
        if not isinstance(self.phase, str) or not self.phase.strip():
            raise ValueError("phase must be a non-empty string")

    def charge(self, n: int = 1) -> bool:
        _nonnegative_int(n, "work charge")
        if self.exhausted or self.used + n > self.max_work_units:
            self.exhausted = True
            raise WorkBudgetExceeded(
                f"document_work limit reached: phase={self.phase}, used={self.used}, "
                f"requested={n}, limit={self.max_work_units}",
                phase=self.phase, used=self.used, requested=n, limit=self.max_work_units)
        if self._parent is not None:
            try:
                self._parent.charge(n)
            except WorkBudgetExceeded:
                self.exhausted = True
                raise
        self.used += n
        return True

    def scoped(self, max_work_units: int, *, phase: str | None = None) -> WorkBudget:
        if type(max_work_units) is not int or max_work_units < 0:
            raise ValueError("scope ceiling must be a non-negative integer")
        return WorkBudget(min(max_work_units, self.max_work_units), _parent=self,
                          phase=self.phase if phase is None else phase)
