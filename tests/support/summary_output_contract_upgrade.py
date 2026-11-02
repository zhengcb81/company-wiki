"""Narrow expectation migration for immutable, pre-quota-retirement archives.

Never rewrites archives or relaxes material, identity, citation, or HTTP fields.
Only completed-output compression permissions intentionally changed in R7.
"""
import json

from company_wiki.automation.models import canonical_json


def upgraded_instruction(text):
    return text.replace("Respect the twenty-claim and configured output bounds",
                        "Respect configured output tokens").replace(
        "Respect twenty claims, 280 characters per claim and the configured output token budget.",
        "Use the output plan as compression guidance, not a clause or character quota. "
        "Preserve complete source qualifications within the configured output token budget.")


def upgraded_envelope(encoded):
    data = json.loads(encoded)
    schema = data["response_schema"]
    if "draft" in schema["properties"]:
        schema = schema["properties"]["draft"]
    claims = schema["properties"]["claims"]
    assert claims.pop("maxItems") == 20
    assert claims["items"]["properties"]["text"].pop("maxLength") == 280
    assert data["output_plan"]["planning"] == "compact_target_not_token_estimate"
    data["output_plan"]["planning"] = "advisory_targets_not_result_limits"
    return data


def assert_archived_request_upgrade(actual, archived):
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
