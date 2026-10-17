"""One parent account; local phase ceilings only tighten it."""
import pytest

from company_wiki.document_normalization.layout_snapshots import identity
from company_wiki.document_understanding.layout_hints import contract


def test_extraction_and_understanding_share_the_same_budget_implementation():
    assert identity.WorkBudget is contract.WorkBudget
    assert identity.WorkBudgetExceeded is contract.WorkBudgetExceeded


def test_phase_balance_cannot_reset_parent_or_overspend_local_cap():
    parent = contract.WorkBudget(10)
    source = parent.scoped(6)
    source.charge(6)
    with pytest.raises(contract.WorkBudgetExceeded):
        source.charge()
    assert parent.used == source.used == 6
    assert not parent.exhausted  # source ceiling is not the whole attempt ceiling
    selection = parent.scoped(10)
    selection.charge(4)
    with pytest.raises(contract.WorkBudgetExceeded):
        parent.scoped(10).charge()
    assert parent.used == 10 and parent.exhausted


