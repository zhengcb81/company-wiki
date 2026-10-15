"""Local provider fixtures consume the real finite wire protocols."""
import json

import pytest

from company_wiki.automation.narrative_model import NarrativeModelRequest, NarrativeModelResponse, decode_model_draft
from support.narrative_model_request_fixture import response_draft, selection
from support.official_json_batch_fixture import model_draft
from unit.test_narrative_reading_transport import with_reading
from unit.test_narrative_source_owned_model_boundary import official_reading
from unit.test_narrative_citation_attribution_contract import selected_qa


@pytest.mark.parametrize("official", [False, True])
@pytest.mark.parametrize("projection", [None, "reading-model-input/1", "reading-model-input/2", "reading-model-input/3"])
def test_mock_provider_understands_actual_wire_without_recreating_source_identity(official, projection):
    selected = official_reading() if official else with_reading(selection(1))
    if official and projection == "reading-model-input/3":
        selected = selected_qa()
    request = NarrativeModelRequest.from_selection(selected, reading_projection_version=projection)
    payload = json.loads(request.data_json)
    final = model_draft(payload) if official else response_draft(payload)
    if projection == "reading-model-input/3":
        assert set(final) == {"claims"}
        assert "citation_unit_ids" in final["claims"][0]
        assert not any(key.endswith("_id") or key.endswith("_sha256")
            for key in payload.get("source", payload.get("subject", {})))
    elif projection == "reading-model-input/2":
        assert set(final) == {"draft"}
        assert set(final["draft"]) == {"claims"}
        assert not any(key.endswith("_id") or key.endswith("_sha256")
            for key in payload.get("source", payload.get("subject", {})))
    else:
        identity = "subject_id" if official else "source_id"
        assert identity in final["draft"]
        assert final["draft"]["language"] == selected.source_metadata.language
    response = NarrativeModelResponse("offline", "fixture", request.prompt_version,
        json.dumps(final, ensure_ascii=False).encode("utf-8"))
    canonical = decode_model_draft(response, selected=selected, reading_projection_version=projection)
    assert canonical["language"] == selected.source_metadata.language
    assert canonical["subject_id" if official else "source_id"] == (
        selected.subject.item_key if official else selected.source_ref.source_id)
