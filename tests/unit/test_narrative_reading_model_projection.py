"""Model semantics are projected separately from the public source audit view."""
import json

import pytest

from company_wiki.automation import narrative_model as model
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from unit.test_narrative_reading_transport import with_reading
from support.narrative_model_request_fixture import selection


VERSION = "reading-model-input/1"


def projected(selected):
    return model.NarrativeModelRequest.from_selection(selected, reading_projection_version=VERSION)


def test_projection_retains_semantics_and_alias_closure_without_audit_directories():
    selected = with_reading()
    before = selected.to_dict()
    request = projected(selected)
    data = json.loads(request.data_json)
    context = data["reading_strategy"]
    assert context["schema_version"] == VERSION
    policy = context["reading_policies"][0]
    for key in ("summary_focus", "reading_questions", "context_requirements", "negative_hints"):
        assert policy[key] == before["reading_context"]["reading_policies"][0][key]
    facet = context["business_facets"][0]
    for key in ("summary_focus", "business_questions", "required_context", "absence_rules", "confusion_checks"):
        assert facet[key] == before["reading_context"]["business_facets"][0][key]
    assert context["constraints"] == before["reading_context"]["constraints"]
    text = json.dumps(context)
    assert all('"' + key + '":' not in text for key in ("selection_basis", "content_digest", "family_policy", "unit_id", "package_id"))
    assert data["evidence_groups"] == [["g1", ["e1", "e2"]], ["g2", ["e2", "e3"]]]
    assert [row[1] for row in data["evidence"]] == [span.raw_text for span in selected.evidence_spans]
    assert selected.to_dict() == before


def test_duplicate_guidance_collapses_but_distinct_risks_and_coverage_remain():
    selected = with_reading()
    wire = selected.to_dict()
    ctx = wire["reading_context"]
    ctx["reading_policies"] *= 3
    ctx["business_facets"] *= 3
    ctx["unread"]["unassigned_unit_ids"] = ["urn:audit-only:abcdef"] * 50
    ctx["unread"]["counts"] = {"unassigned_unit_ids": 50, "opaque_pages": 0,
                                 "deferred_pages": 0, "deferred_unit_ids": 0}
    ctx["unread"]["limited"] = False
    ctx["deferred"] = [{"package_id": "not-model-" + str(n), "reason": "CHAR_BUDGET"} for n in range(20)]
    selected = NarrativeSelectResult.from_dict(wire)
    context = json.loads(projected(selected).data_json)["reading_strategy"]
    assert len(context["reading_policies"]) == len(context["business_facets"]) == 1
    assert "urn:audit-only" not in json.dumps(context)
    assert context["coverage"]["unread_counts"]["unassigned_unit_ids"] == 50
    assert context["coverage"]["layout"]["complete"] is False
    assert context["coverage"]["deferred"]["observed_reasons"] == ["CHAR_BUDGET"]


def test_audit_only_change_does_not_change_sent_projection_but_real_guidance_does():
    selected = with_reading()
    request = projected(selected)
    wire = selected.to_dict()
    wire["reading_context"]["business_facets"][0]["selection_basis"] = [{"unit_id": "audit-only", "matched_signals": ["regex-internal"]}]
    other = projected(NarrativeSelectResult.from_dict(wire))
    assert other.data_json == request.data_json and other.input_sha256 == request.input_sha256
    wire["reading_context"]["business_facets"][0]["business_questions"].append("Keep the next customer validation action.")
    changed = projected(NarrativeSelectResult.from_dict(wire))
    assert changed.data_json != request.data_json and changed.input_sha256 != request.input_sha256


def test_legacy_omission_and_explicit_none_keep_the_original_request_exactly():
    selected = with_reading()
    old = model.NarrativeModelRequest.from_selection(selected)
    assert model.NarrativeModelRequest.from_selection(selected, reading_projection_version=None) == old
    assert json.loads(old.data_json)["reading_strategy"]["schema_version"] == "du-production-reading/1"
    assert old.prompt_version == "1.7.0"
    assert projected(selected).input_sha256 != old.input_sha256
    no_reading = selection(2)
    assert model.NarrativeModelRequest.from_selection(no_reading, reading_projection_version=None) == model.NarrativeModelRequest.from_selection(no_reading)


def test_new_plan_uses_real_groups_and_keeps_current_and_next_separate_under_configured_cap():
    selected = with_reading(selection(24))
    wire = selected.to_dict()
    wire["reading_context"]["groups"] = [{"group_id": "body-" + str(n), "kind": "product_current_and_next", "section_role": "business", "evidence_ids": [span.span_id]} for n, span in enumerate(selected.evidence_spans)]
    selected = NarrativeSelectResult.from_dict(wire)
    request = projected(selected)
    data = json.loads(request.with_output_budget(8192).data_json)
    assert data["output_plan"]["target_claim_count"] == 20
    assert data["output_plan"]["max_claims"] == 20
    assert "single modality" in request.instruction
    assert "next action" in request.instruction
    assert "that claim" in request.instruction
    assert json.loads(request.with_output_budget(400).data_json)["output_plan"]["target_claim_count"] == 1
    port = NarrativeHTTPModel(model_id="fixture", endpoint="https://fixture.invalid/v1", api_key_env="NO_KEY", max_output_tokens=8192)
    actual = json.loads(port.request_bytes(request))
    assert json.loads(actual["messages"][1]["content"])["output_plan"]["target_claim_count"] == 20


@pytest.mark.parametrize("value", ["unavailable/99", False, ""])
def test_unknown_projection_never_silently_uses_a_different_renderer(value):
    with pytest.raises(model.ModelResponseError):
        model.NarrativeModelRequest.from_selection(with_reading(), reading_projection_version=value)


def test_missing_reading_context_rejects_requested_reading_renderer():
    with pytest.raises(model.ModelResponseError):
        projected(selection())


def test_coverage_change_is_sent_without_changing_source_evidence():
    selected = with_reading()
    wire = selected.to_dict()
    wire["reading_context"]["unread"]["opaque_pages"] = [8]
    changed = projected(NarrativeSelectResult.from_dict(wire))
    base = projected(selected)
    assert changed.input_sha256 != base.input_sha256
    assert json.loads(changed.data_json)["evidence"] == json.loads(base.data_json)["evidence"]


def test_reading_instruction_keeps_selected_operating_tables_and_business_causes():
    selected = with_reading()
    legacy = model.NarrativeModelRequest.from_selection(selected)
    current = projected(selected)
    assert "financial tables," in legacy.instruction
    assert "financial tables," not in current.instruction
    assert "pure financial statement totals" in current.instruction
    assert "operating metrics" in current.instruction
    assert "business causes" in current.instruction
    assert "period" in current.instruction and "unit" in current.instruction
