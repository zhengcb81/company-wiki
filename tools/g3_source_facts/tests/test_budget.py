"""Counter-example: the read budget stops the run instead of reporting completeness."""

from __future__ import annotations

import pytest

from g3_source_facts.budget import (
    RAW_DUP_MAX_GROUPS,
    RAW_DUP_MAX_READ_BYTES,
    TOTAL_READ_BUDGET_BYTES,
    BudgetExceeded,
    ReadBudget,
)


def test_total_budget_is_512_mib():
    assert TOTAL_READ_BUDGET_BYTES == 512 * 1024 * 1024


def test_charging_past_the_budget_raises_instead_of_completion():
    budget = ReadBudget(TOTAL_READ_BUDGET_BYTES)
    budget.charge(TOTAL_READ_BUDGET_BYTES - 1, label="hash:S01")
    with pytest.raises(BudgetExceeded):
        budget.charge(2, label="hash:S02")
    assert budget.exhausted is True
    assert budget.status == "partial"


def test_budget_status_stays_partial_after_exhaustion():
    budget = ReadBudget(10)
    budget.charge(10, label="read")
    with pytest.raises(BudgetExceeded):
        budget.charge(1, label="read")
    assert budget.status == "partial"
    assert budget.complete is False


def test_raw_dup_round_cap_is_the_smaller_of_remaining_and_256_mib():
    budget = ReadBudget(268435456 + 10)
    assert budget.raw_dup_round_limit() == 268435456
    small = ReadBudget(1024)
    assert small.raw_dup_round_limit() == 1024
    assert RAW_DUP_MAX_READ_BYTES == 268435456
    assert RAW_DUP_MAX_GROUPS == 20


def test_raw_dup_rounds_cannot_exceed_the_total_budget():
    budget = ReadBudget(TOTAL_READ_BUDGET_BYTES)
    first = budget.raw_dup_round_limit()
    budget.charge(first, label="raw_dup:round1")
    second = budget.raw_dup_round_limit()
    assert first + second <= TOTAL_READ_BUDGET_BYTES


def test_repeated_reads_are_charged_again():
    budget = ReadBudget(100)
    budget.charge(60, label="hash")
    assert budget.remaining == 40
    with pytest.raises(BudgetExceeded):
        budget.charge(60, label="reread")
    assert budget.consumed == 60
    assert budget.exhausted is True
    assert budget.status == "partial"
