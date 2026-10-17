"""Presentation metadata cannot override source-owned summary semantics."""
import json
import logging

import pytest

from company_wiki.automation import narrative_model as model
from company_wiki.automation import narrative_model_runtime as runtime
from company_wiki.automation.narrative_contracts import NarrativeContractError
from unit.test_narrative_scoped_runtime import clause, request
from unit.test_narrative_reading_transport import with_reading


def decode(payload):
    selected = with_reading()
    response = model.NarrativeModelResponse("offline", "configured", request(selected).prompt_version,
        json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    return runtime.decode_model_draft(response, selected=selected, reading_projection_version="reading-model-input/4")


def test_json_object_presentation_metadata_preserves_identical_canonical_summary(caplog):
    payload = {"drafts_by_task": {"t1": [clause()]}}
    expected = decode(payload)
    with caplog.at_level(logging.INFO):
        actual = decode({**payload, "type": "json_object"})
    assert actual == expected
    assert "presentation metadata" in caplog.text
    assert "type" not in actual


@pytest.mark.parametrize("value", ["object", "text", None, {}, ["json_object"]])
def test_other_response_presentation_types_are_not_reinterpreted(value):
    with pytest.raises((model.ModelResponseError, NarrativeContractError)):
        decode({"drafts_by_task": {"t1": [clause()]}, "type": value})


@pytest.mark.parametrize("extra", [
    {"source_id": "forged"}, {"language": "en"}, {"status": "accepted"},
    {"translate": True}, {"claims": []}, {"metadata": {"unbounded": "data"}},
])
def test_presentation_marker_does_not_admit_unknown_semantic_fields(extra):
    with pytest.raises((model.ModelResponseError, NarrativeContractError)):
        decode({"drafts_by_task": {"t1": [clause()]}, "type": "json_object", **extra})


def test_presentation_marker_does_not_repair_unknown_task_or_basis():
    for tasks in ({"t999": [clause()]}, {"t1": [clause(parts=["p999"])]}):
        with pytest.raises((model.ModelResponseError, NarrativeContractError)):
            decode({"drafts_by_task": tasks, "type": "json_object"})
