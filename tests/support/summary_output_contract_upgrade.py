"""Narrow expectation migration for immutable, pre-quota-retirement archives.

Never rewrites archives or relaxes material, identity, citation, or HTTP fields.
Only completed-output compression permissions intentionally changed in R7.
"""
from contextlib import contextmanager
import json
from unittest.mock import patch

from company_wiki.automation.models import canonical_json


def upgraded_instruction(text):
    return text.replace("Respect the twenty-claim and configured output bounds",
                        "Respect configured output tokens").replace(
        "Respect twenty claims, 280 characters per claim and the configured output token budget.",
        "Use the output plan as compression guidance, not a clause or character quota. "
        "Preserve complete source qualifications within the configured output token budget.").replace(
        "Respect output_plan.max_claims_per_task per task and output_plan.max_claims in total; "
        "the response schema arrays are bounded but the program enforces the smaller per-task cap, "
        "so exceeding it rejects the whole response. Each clause is at most 280 characters. ",
        "Use output_plan as advisory compression targets, not result validity quotas. "
        "Preserve each complete qualified fact within the configured output token budget. ").replace(
        "Emit up to output_plan.target_claim_count clauses (never more than output_plan.max_claims in total), "
        "at most output_plan.max_claims_per_task per task. ", "").replace(
        "Respect output_plan.max_claims and max_claims_per_task and the configured output token limit. "
        "Each clause is at most 280 characters. ",
        "Use output_plan as advisory compression targets and respect the configured output token limit. "
        "Do not shorten away qualifications to meet a clause or character quota. ")


def upgraded_envelope(encoded):
    data = json.loads(encoded)
    schema = data["response_schema"]
    if "drafts_by_task" in schema["properties"]:
        claims = schema["properties"]["drafts_by_task"]["additionalProperties"]
        assert claims.pop("maxItems") in {2, 6}
        old_planning = "soft_target_within_existing_caps"
    else:
        if "draft" in schema["properties"]:
            schema = schema["properties"]["draft"]
        claims = schema["properties"]["claims"]
        assert claims.pop("maxItems") == 20
        old_planning = "compact_target_not_token_estimate"
    assert claims["items"]["properties"]["text"].pop("maxLength") == 280
    assert data["output_plan"]["planning"] == old_planning
    data["output_plan"]["planning"] = "advisory_targets_not_result_limits"
    return data


def assert_archived_request_upgrade(actual, archived, *, selected, reading_projection_version=None):
    from company_wiki.automation.narrative_model_runtime import build_model_request

    # A request's identity also binds source/selection/citation/task context;
    # hashing only its displayed four fields would weaken the real contract.
    # Ask the existing owner to reconstruct the known capture form (initial
    # request, or one HTTP output-budget retarget) without copying its hash DAG.
    rebuilt = build_model_request(selected, reading_projection_version=reading_projection_version)
    output_tokens = json.loads(actual.data_json)["output_plan"]["configured_output_tokens"]
    if output_tokens is not None:
        rebuilt = rebuilt.with_output_budget(output_tokens)
    assert (actual.prompt_version, actual.instruction, actual.data_json, actual.input_sha256) == (
        rebuilt.prompt_version, rebuilt.instruction, rebuilt.data_json, rebuilt.input_sha256)
    assert actual.prompt_version == archived["prompt_version"]
    assert actual.instruction == upgraded_instruction(archived["instruction"])
    assert json.loads(actual.data_json) == upgraded_envelope(archived["data_json"])
    if "input_sha256" in archived:
        assert actual.input_sha256 != archived["input_sha256"]


def upgraded_http_body(encoded):
    body = json.loads(encoded)
    body["messages"][0]["content"] = upgraded_instruction(body["messages"][0]["content"])
    body["messages"][1]["content"] = canonical_json(upgraded_envelope(body["messages"][1]["content"]))
    return body


@contextmanager
def archived_compression_projection():
    """Reconstruct digest-only legacy captures through the unchanged builder.

    The three temporary presentation ports restore only retired20/280 fields,
    advisory naming and their exact instruction fragments. Material, citation,
    selection and input-hash construction stay in the real owner. Old full SHA
    assertions therefore still catch unrelated changes without copying the
    hashing algorithm or regenerating historical fixtures. No decoder is patched.
    Use only for pure request/HTTP serialization, never source/model execution.
    """
    from company_wiki.automation import narrative_model as model
    schema_owner = model._response_schema
    plan_owner = model._output_plan
    instruction_owner = model._boundary_instruction

    def schema(*args, **kwargs):
        result = schema_owner(*args, **kwargs)
        draft = result["properties"].get("draft", result)
        claims = draft["properties"]["claims"]
        assert "maxItems" not in claims
        assert "maxLength" not in claims["items"]["properties"]["text"]
        claims["maxItems"] = 20
        claims["items"]["properties"]["text"]["maxLength"] = 280
        return result

    def plan(*args, **kwargs):
        result = plan_owner(*args, **kwargs)
        assert result["planning"] == "advisory_targets_not_result_limits"
        result["planning"] = "compact_target_not_token_estimate"
        return result

    def instruction(*args, **kwargs):
        result = instruction_owner(*args, **kwargs)
        return result.replace("Respect configured output tokens",
            "Respect the twenty-claim and configured output bounds").replace(
            "Use the output plan as compression guidance, not a clause or character quota. "
            "Preserve complete source qualifications within the configured output token budget.",
            "Respect twenty claims, 280 characters per claim and the configured output token budget.")

    with patch.object(model, "_response_schema", schema), patch.object(model, "_output_plan", plan), \
            patch.object(model, "_boundary_instruction", instruction):
        yield
