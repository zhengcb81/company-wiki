from decimal import Decimal
import time

import pytest

from company_wiki.source_catalog import AcquisitionBudget, AcquisitionBudgetExceeded


def test_acquisition_budget_charges_response_bytes_and_cost_across_steps():
    budget = AcquisitionBudget(
        max_response_bytes=10,
        deadline_monotonic=time.monotonic() + 30,
        max_cost_usd=Decimal("0.01"),
    )

    budget.consume_response_bytes(6)
    budget.consume_cost_usd("0.01")

    assert budget.remaining_response_bytes == 4
    assert budget.remaining_cost_usd == Decimal("0.00")
    with pytest.raises(AcquisitionBudgetExceeded, match="byte budget"):
        budget.consume_response_bytes(5)
    with pytest.raises(AcquisitionBudgetExceeded, match="cost budget"):
        budget.consume_cost_usd("0.01")
    # These calls report actual consumption, not speculative reservations.
    # Rejecting further work cannot undo bytes already read or cost incurred.
    assert budget.response_bytes_used == 11
    assert budget.cost_usd_used == Decimal("0.02")


def test_acquisition_budget_blocks_new_work_but_accounts_late_usage():
    budget = AcquisitionBudget(
        max_response_bytes=10,
        deadline_monotonic=time.monotonic() - 1,
        max_cost_usd=Decimal("0.01"),
    )

    with pytest.raises(AcquisitionBudgetExceeded, match="deadline"):
        budget.ensure_open()

    # These methods account usage already reported by a provider. They must
    # retain it even when the provider reports completion after the deadline.
    budget.consume_response_bytes(1)
    budget.consume_cost_usd("0.01")

    assert budget.response_bytes_used == 1
    assert budget.cost_usd_used == Decimal("0.01")
