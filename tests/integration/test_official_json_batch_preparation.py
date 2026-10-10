"""Real projection preparation uses one common finite batch item identity."""

import json
import pytest
from company_wiki.automation.narrative_batch import (
    build_batch_events,
    _thaw_generations,
)
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.source_catalog.source_reader import SourceVersionReader
from integration.test_official_json_transport_subject import owned_state
from unit.test_narrative_batch_request import _request


def request_for(state):
    value = _request()
    value["schema_version"] = "narrative-batch-request/2"
    value.pop("sources")
    value["items"] = [
        {
            "kind": "official_json",
            "projection_id": s.item_key,
            "projection_sha256": s.subject_sha256,
        }
        for s in state.subjects
    ]
    return NarrativeBatchRequest.from_dict(value)


def test_two_issuers_sharing_parents_produce_distinct_bound_events(tmp_path):
    with owned_state(tmp_path) as state:
        request = request_for(state)
        binding = build_batch_events(
            request,
            SourceVersionReader(state.catalog),
            now="2026-10-10T00:00:00Z",
            projection_catalog=state.catalog,
        )
        assert len(binding.events) == 2
        assert [e.subject_id for e in binding.events] == [
            s.item_key for s in state.subjects
        ]
        assert {e.subject_type for e in binding.events} == {"narrative_subject"}
        for event, subject in zip(binding.events, state.subjects):
            value = json.loads(event.payload_json)
            assert value["schema_version"] == "source-revision-event/3.0"
            assert value["subject_binding"] == subject.to_dict()
            assert value["source_metadata"]["language"] == "en"
            assert value["source_metadata"]["source_class"] == "official_json"
            assert (
                "source_ref" not in value and "expected_read_policy_sha256" not in value
            )


def test_projected_preparation_has_explicit_catalog_port_and_never_falls_back_to_anchor(
    tmp_path,
):
    with owned_state(tmp_path) as state:
        with pytest.raises(ValueError, match="PROJECTION_SOURCE_PORT_UNAVAILABLE"):
            build_batch_events(
                request_for(state),
                SourceVersionReader(state.catalog),
                now="2026-10-10T00:00:00Z",
            )


def test_projection_request_execution_identity_pins_active_native_adapter_and_prompt(
    tmp_path,
):
    from company_wiki.automation.narrative_official_json import (
        NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION,
    )
    from company_wiki.automation.narrative_model import (
        PROJECTION_NARRATIVE_PROMPT_VERSION,
        PROJECTION_MODEL_REQUEST_SCHEMA,
    )

    with owned_state(tmp_path) as state:
        versions = request_for(state).execution_versions
        assert (
            versions["official_json_adapter"] == NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION
        )
        assert versions["projection_prompt"] == PROJECTION_NARRATIVE_PROMPT_VERSION
        assert (
            versions["projection_model_request_schema"]
            == PROJECTION_MODEL_REQUEST_SCHEMA
        )


def test_projection_generation_freeze_roundtrip_keeps_subject_in_per_item_inputs(
    tmp_path,
):
    from company_wiki.automation.narrative_batch import (
        _freeze_generations,
        _execution_versions,
    )
    from company_wiki.automation.narrative_generation import (
        projection_generation_manifest,
    )

    with owned_state(tmp_path) as state:
        request = request_for(state)
        versions = {
            **_execution_versions(request),
            "prompt": "official-json/1.0.0",
            "model_request_schema": "narrative-model-request/2",
        }
        manifests = {
            s.item_key: projection_generation_manifest(
                request,
                s,
                language="en",
                execution_versions=versions,
                bundle_producer="1.0.0",
                narrative_adapter_version="1.0.1",
            )
            for s in state.subjects
        }
        frozen = _freeze_generations(manifests)
        assert _thaw_generations(frozen) == manifests
        for subject in state.subjects:
            record = frozen["generation_manifests"][subject.item_key]
            assert record["source_inputs"]["subject_binding"] == subject.to_dict()
            assert "source_ref" not in record["source_inputs"]
