"""The scoped request states and enforces the per-task share of the claim cap."""
from company_wiki.automation.narrative_model_scoped import (
    MAX_SUMMARY_CLAIMS, SCOPED_INSTRUCTION, _scoped_output_plan, scoped_response_schema,
)


def test_scoped_plan_states_the_target_and_per_task_cap():
    plan = _scoped_output_plan(64)
    assert plan["max_claims"] == MAX_SUMMARY_CLAIMS == 40
    assert plan["target_claim_count"] == 36
    assert plan["max_claims_per_task"] == 2
    assert "target_claim_count" in SCOPED_INSTRUCTION
    assert "max_claims_per_task" in SCOPED_INSTRUCTION


def test_small_task_sets_target_one_clause_per_task():
    assert _scoped_output_plan(3)["target_claim_count"] == 3
    assert _scoped_output_plan(1)["target_claim_count"] == 1


def test_schema_bounds_each_task_array_by_the_per_task_cap():
    schema = scoped_response_schema(2)
    assert schema["properties"]["drafts_by_task"]["additionalProperties"]["maxItems"] == 2
    full = scoped_response_schema(20)
    assert full["properties"]["drafts_by_task"]["additionalProperties"]["maxItems"] == 20
