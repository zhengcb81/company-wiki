"""The scoped request states and enforces the per-task share of the claim cap."""
from company_wiki.automation.narrative_model_scoped import (
    SCOPED_INSTRUCTION, _scoped_output_plan, scoped_response_schema,
)


def test_scoped_plan_states_the_per_task_share_of_the_global_claim_cap():
    plan = _scoped_output_plan(12)
    assert plan["max_claims"] == 20
    assert plan["max_claims_per_task"] == 1
    assert "max_claims_per_task" in SCOPED_INSTRUCTION
    assert "output_plan.max_claims" in SCOPED_INSTRUCTION


def test_fewer_tasks_allow_a_larger_per_task_share():
    assert _scoped_output_plan(2)["max_claims_per_task"] == 10
    assert _scoped_output_plan(1)["max_claims_per_task"] == 20


def test_schema_bounds_each_task_array_by_the_per_task_share():
    schema = scoped_response_schema(1)
    assert schema["properties"]["drafts_by_task"]["additionalProperties"]["maxItems"] == 1
    full = scoped_response_schema(20)
    assert full["properties"]["drafts_by_task"]["additionalProperties"]["maxItems"] == 20
