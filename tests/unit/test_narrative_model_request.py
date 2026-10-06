"""Model input stays lean while the full replayable evidence remains canonical."""

from dataclasses import replace
import json

import pytest

from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.automation.narrative_model import NarrativeModelRequest


from support.narrative_model_request_fixture import selection as _selection


def test_long_selection_fits_budget_without_losing_any_evidence_or_replay_metadata():
    selected = _selection(160)
    before = selected.to_dict()
    request = NarrativeModelRequest.from_selection(selected)
    envelope = json.loads(request.data_json)
    model = NarrativeHTTPModel(model_id="offline-model", endpoint="https://example.invalid/v1/chat/completions",
                               api_key_env="UNUSED_TEST_KEY")

    # The production ledger uses this conservative byte bound, not a guessed tokenizer ratio.
    assert len(model.request_bytes(request)) + 128 + model.max_output_tokens < 60_000
    assert len(envelope["evidence"]) == 160
    canonical_by_id = {item["span_id"]: item for item in before["evidence_spans"]}
    for index, (projected, span) in enumerate(zip(envelope["evidence"], selected.evidence_spans, strict=True), start=1):
        assert projected[0] == f"e{index}"
        assert projected[1] == span.raw_text
        assert (projected[3] if len(projected) > 3 else envelope["default_quality_flags"]) == list(span.quality_flags)
        assert (projected[2] if len(projected) > 2 else envelope["default_source_role"]) == "company_filing"
        assert len(projected) == 2
        # Citation IDs still resolve to the unchanged canonical source locator.
        assert canonical_by_id[span.span_id]["locator"] == span.locator
    assert envelope["selection"] == {key: selected.selection.to_dict()[key] for key in
                                     ("status", "coverage_complete", "omitted_candidate_count")}
    assert selected.to_dict() == before  # canonical replay fields are still intact
    assert all(span.parser_version == "1.0.0" for span in selected.evidence_spans)


@pytest.mark.parametrize("role,flags", [("management", ()), ("analyst", ()),
                                        ("unknown", ("locator_unstable",))])
def test_prompt_preserves_role_quality_source_identity_and_original_language(role, flags):
    selected = _selection(role=role, flags=flags)
    request = NarrativeModelRequest.from_selection(selected)
    envelope = json.loads(request.data_json)
    assert envelope["source"]["source_id"] == selected.source_ref.source_id
    assert envelope["source"]["source_sha256"] == selected.source_ref.content_sha256
    assert envelope["source"]["language"] == "zh"
    span = envelope["evidence"][0]
    assert (span[2] if len(span) > 2 else envelope["default_source_role"]) == role
    assert (span[3] if len(span) > 3 else envelope["default_quality_flags"]) == list(flags)
    assert "No translation" in request.instruction
    assert envelope["selection"]["omitted_candidate_count"] == 20
    assert request.prompt_version != "1.1.0"


def test_request_hash_binds_text_role_quality_and_coverage_and_is_deterministic():
    selected = _selection()
    request = NarrativeModelRequest.from_selection(selected)
    assert NarrativeModelRequest.from_selection(selected) == request
    changed = [_selection(text_suffix="新进展"), _selection(role="management"),
               _selection(flags=("locator_unstable",)),
               replace(selected, selection=replace(selected.selection, source_units=30))]
    assert all(NarrativeModelRequest.from_selection(item).input_sha256 != request.input_sha256
               for item in changed)


def test_model_receives_one_strict_schema_and_excerpt_scope_without_duplicate_example():
    selected = _selection(160)
    before = selected.to_dict()
    request = NarrativeModelRequest.from_selection(selected)
    value = json.loads(request.data_json)
    assert "response_example" not in value and "constraints" not in value
    assert value["response_schema"]["additionalProperties"] is False
    assert value["selection"] == {key: selected.selection.to_dict()[key] for key in
                                  ("status", "coverage_complete", "omitted_candidate_count")}
    assert len(value["evidence"]) == 160
    assert [row[1] for row in value["evidence"]] == [span.raw_text for span in selected.evidence_spans]
    assert selected.to_dict() == before
    changed = replace(selected, selection=replace(selected.selection, source_units=10000))
    other = NarrativeModelRequest.from_selection(changed)
    assert other.data_json == request.data_json  # Full counts stay canonical, outside model prose.
    assert other.input_sha256 != request.input_sha256
