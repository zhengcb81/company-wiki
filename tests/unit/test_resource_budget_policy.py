"""Independent public contracts for configured budgets and one work account.

Policy data is entirely task-local.  No production configuration, API key,
external provider, historical billing ledger or original document is touched.
"""

from copy import deepcopy
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest
import yaml

from company_wiki import resource_budget as budget


SCHEMA = "company-wiki-budget-policy/1"
BASE = {
    "schema_version": SCHEMA,
    "external_model": {
        "cumulative_tokens": 10_000_000,
        "cumulative_micro_usd": 20_000_000,
    },
    "company_allocation": {
        "enforcement": "soft",
        "target_tokens": 150_000,
        "target_micro_usd": 1_000_000,
    },
    "document_processing": {"max_work_units": 16_000_000},
}
NUMERIC_PATHS = (
    ("external_model", "cumulative_tokens"),
    ("external_model", "cumulative_micro_usd"),
    ("company_allocation", "target_tokens"),
    ("company_allocation", "target_micro_usd"),
    ("document_processing", "max_work_units"),
)


@pytest.fixture(autouse=True)
def isolate_budget_config(monkeypatch):
    monkeypatch.delenv("COMPANY_WIKI_BUDGET_CONFIG", raising=False)
    assert Path(budget.__file__).resolve().is_relative_to(
        Path(__file__).resolve().parents[2] / "src"
    )


def write_policy(tmp_path, payload=None, name="budget.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(BASE if payload is None else payload), encoding="utf-8")
    return path


def values(policy):
    return (
        policy.cumulative_tokens,
        policy.cumulative_micro_usd,
        policy.company_token_target,
        policy.company_micro_usd_target,
        policy.document_work_limit,
    )


@pytest.mark.parametrize("path_kind", [Path, str])
def test_public_loader_reads_frozen_policy_without_changing_source(tmp_path, path_kind):
    path = write_policy(tmp_path)
    before = path.read_bytes()
    policy = budget.load_budget_policy(path_kind(path))
    assert values(policy) == (10_000_000, 20_000_000, 150_000, 1_000_000, 16_000_000)
    assert is_dataclass(policy)
    with pytest.raises(FrozenInstanceError):
        policy.company_token_target = 1
    assert path.read_bytes() == before


def test_explicit_policy_path_wins_over_environment(tmp_path, monkeypatch):
    explicit = write_policy(tmp_path, name="explicit.yaml")
    environment = deepcopy(BASE)
    environment["document_processing"]["max_work_units"] = 47
    monkeypatch.setenv("COMPANY_WIKI_BUDGET_CONFIG", str(write_policy(tmp_path, environment, "env.yaml")))
    assert budget.load_budget_policy(explicit).document_work_limit == 16_000_000


def test_environment_path_is_used_independent_of_current_directory(tmp_path, monkeypatch):
    configured = deepcopy(BASE)
    configured["document_processing"]["max_work_units"] = 29
    path = write_policy(tmp_path, configured)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.setenv("COMPANY_WIKI_BUDGET_CONFIG", str(path))
    monkeypatch.chdir(unrelated)
    assert budget.load_budget_policy().document_work_limit == 29


@pytest.mark.parametrize("malformed", [False, True])
def test_bad_environment_path_cannot_silently_fall_back(tmp_path, monkeypatch, malformed):
    path = tmp_path / "invalid-selected-policy.yaml"
    if malformed:
        path.write_text("external_model: [unterminated", encoding="utf-8")
    monkeypatch.setenv("COMPANY_WIKI_BUDGET_CONFIG", str(path))
    with pytest.raises((ValueError, TypeError, OSError, yaml.YAMLError)):
        budget.load_budget_policy()


@pytest.mark.parametrize("section,field", NUMERIC_PATHS)
def test_every_numeric_policy_dimension_can_be_zero(tmp_path, section, field):
    configured = deepcopy(BASE)
    configured[section][field] = 0
    policy = budget.load_budget_policy(write_policy(tmp_path, configured))
    expected = list(values(budget.load_budget_policy(write_policy(tmp_path, name="base.yaml"))))
    expected[NUMERIC_PATHS.index((section, field))] = 0
    assert values(policy) == tuple(expected)


@pytest.mark.parametrize("section,field", NUMERIC_PATHS)
@pytest.mark.parametrize("invalid", [-1, True, 1.5, "100", None])
def test_policy_numbers_require_actual_nonnegative_integers(tmp_path, section, field, invalid):
    configured = deepcopy(BASE)
    configured[section][field] = invalid
    with pytest.raises((ValueError, TypeError)):
        budget.load_budget_policy(write_policy(tmp_path, configured))


@pytest.mark.parametrize("change", ["schema", "missing", "hard_company_limit"])
def test_invalid_policy_cannot_turn_into_implicit_default_values(tmp_path, change):
    configured = deepcopy(BASE)
    if change == "schema":
        configured["schema_version"] = "unrelated-budget/9"
    elif change == "missing":
        del configured["external_model"]["cumulative_tokens"]
    else:
        configured["company_allocation"]["enforcement"] = "hard"
    with pytest.raises((ValueError, TypeError)):
        budget.load_budget_policy(write_policy(tmp_path, configured))


def test_company_allocation_is_soft_and_can_exceed_mother_allowance(tmp_path):
    configured = deepcopy(BASE)
    configured["external_model"] = {"cumulative_tokens": 0, "cumulative_micro_usd": 0}
    configured["company_allocation"].update(target_tokens=999, target_micro_usd=777)
    configured["document_processing"]["max_work_units"] = 9
    path = write_policy(tmp_path, configured)
    policy = budget.load_budget_policy(path)
    assert policy.company_token_target == 999 and policy.company_micro_usd_target == 777
    work = budget.new_document_work_budget(policy_path=path)
    assert work.charge(9) and work.used == 9


def test_external_token_money_and_company_targets_do_not_reset_or_charge_work(tmp_path):
    configured = deepcopy(BASE)
    configured["external_model"] = {"cumulative_tokens": 0, "cumulative_micro_usd": 0}
    configured["company_allocation"].update(target_tokens=0, target_micro_usd=0)
    configured["document_processing"]["max_work_units"] = 17
    work = budget.new_document_work_budget(policy_path=write_policy(tmp_path, configured))
    assert work.max_work_units == 17 and work.charge(11) and work.used == 11
    assert work.charge(6) and work.used == 17


def test_factory_uses_selected_policy_work_limit_and_phase(tmp_path):
    configured = deepcopy(BASE)
    configured["document_processing"]["max_work_units"] = 32_000_000
    work = budget.new_document_work_budget(policy_path=write_policy(tmp_path, configured), phase="parse")
    assert work.max_work_units == 32_000_000
    assert work.phase == "parse"
    assert work.charge(16_000_001) and work.used == 16_000_001


@pytest.mark.parametrize("explicit", [0, 23, 48_000_000])
def test_explicit_request_work_override_is_not_clamped_to_the_old_constant(tmp_path, explicit):
    path = write_policy(tmp_path)
    work = budget.new_document_work_budget(max_work_units=explicit, policy_path=path, phase="select")
    assert work.max_work_units == explicit and work.phase == "select"
    assert work.charge(explicit) and work.used == explicit


@pytest.mark.parametrize("invalid", [-1, True, 3.5, "30"])
def test_explicit_work_limit_rejects_invalid_number_types(tmp_path, invalid):
    with pytest.raises((ValueError, TypeError)):
        budget.new_document_work_budget(max_work_units=invalid, policy_path=write_policy(tmp_path))


@pytest.mark.parametrize("invalid", [-1, True, 2.5, "10", None])
def test_work_account_constructor_rejects_invalid_limits(invalid):
    with pytest.raises((ValueError, TypeError)):
        budget.WorkBudget(invalid)


@pytest.mark.parametrize("invalid", [-1, True, 2.5, "10", None])
def test_invalid_charge_cannot_mutate_the_account(invalid):
    work = budget.WorkBudget(12)
    with pytest.raises((ValueError, TypeError)):
        work.charge(invalid)
    assert work.used == 0 and not work.exhausted


def assert_exhaustion(exc, *, phase, used, requested, limit):
    assert exc.dimension == "document_work"
    assert exc.phase == phase
    assert (exc.used, exc.requested, exc.limit) == (used, requested, limit)
    message = str(exc).lower()
    assert "document_work" in message and phase.lower() in message
    assert "layout analysis work limit reached" not in message


def test_zero_limit_allows_noop_but_reports_real_dimension_and_phase_on_first_work():
    work = budget.WorkBudget(0, phase="parse")
    assert work.charge(0) and work.used == 0 and not work.exhausted
    with pytest.raises(budget.WorkBudgetExceeded) as caught:
        work.charge(1)
    assert_exhaustion(caught.value, phase="parse", used=0, requested=1, limit=0)
    assert work.exhausted and work.used == 0


def test_scoped_limit_rejects_atomically_without_exhausting_parent_allowance():
    parent = budget.WorkBudget(10, phase="document")
    child = parent.scoped(3, phase="select")
    assert child.charge(2) and child.used == parent.used == 2
    with pytest.raises(budget.WorkBudgetExceeded) as caught:
        child.charge(2)
    assert_exhaustion(caught.value, phase="select", used=2, requested=2, limit=3)
    assert child.exhausted and not parent.exhausted
    assert child.used == parent.used == 2
    assert parent.charge(8) and parent.used == 10


def test_scoped_default_phase_and_sibling_scopes_share_one_parent_account():
    parent = budget.WorkBudget(10, phase="document")
    first = parent.scoped(9)
    second = parent.scoped(9)
    assert first.phase == second.phase == "document"
    assert first.charge(4) and second.charge(3)
    assert first.used == 4 and second.used == 3 and parent.used == 7
    with pytest.raises(budget.WorkBudgetExceeded) as caught:
        second.charge(4)
    assert_exhaustion(caught.value, phase="document", used=7, requested=4, limit=10)
    assert parent.used == 7 and second.used == 3
    assert parent.exhausted and second.exhausted


def test_parsing_and_selection_reuse_the_same_spent_account(tmp_path):
    work = budget.new_document_work_budget(max_work_units=10, policy_path=write_policy(tmp_path))
    identities = []

    def parse(account):
        identities.append(id(account))
        account.phase = "parse"
        account.charge(7)

    def select(account):
        identities.append(id(account))
        account.phase = "select"
        account.charge(4)

    parse(work)
    with pytest.raises(budget.WorkBudgetExceeded) as caught:
        select(work)
    assert identities == [id(work), id(work)]
    assert_exhaustion(caught.value, phase="select", used=7, requested=4, limit=10)
    assert work.used == 7 and work.exhausted
