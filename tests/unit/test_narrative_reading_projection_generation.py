"""Projection is a software generation, frozen independently of request intent."""
import json
from dataclasses import replace
import pytest

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation import narrative_generation as generation
from company_wiki.automation import narrative_worker_factory as worker
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.narrative_model import ModelResponseError
from unit.test_narrative_batch import _request, Reader


def payload(request):
    event = batch.build_batch_events(request, Reader(), now="2026-10-14T00:00:00Z").events[0]
    return SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))


def test_new_reading_generation_changes_but_legacy_omission_and_old_eight_stay_frozen():
    request = replace(_request(), selector_version="0.9.0")
    original = payload(request)
    versions = batch._execution_versions(request)
    current = generation.generation_manifest(request, original, execution_versions=versions)
    legacy = generation.generation_manifest(request, original, execution_versions=versions, reading_model_projection=None)
    assert current["reading_model_projection"] == "reading-model-input/1"
    assert "reading_model_projection" not in legacy
    assert generation.generation_sha256(current) != generation.generation_sha256(legacy)
    old = generation.generation_manifest(request, original, execution_versions={**versions, "selector": "0.8.0"})
    assert "reading_model_projection" not in old


def test_worker_recovers_each_frozen_choice_instead_of_current_default():
    request = replace(_request(), selector_version="0.9.0")
    original = payload(request)
    versions = batch._execution_versions(request)
    current = generation.generation_manifest(request, original, execution_versions=versions)
    legacy = generation.generation_manifest(request, original, execution_versions=versions, reading_model_projection=None)
    frozen = batch._freeze_generations({"new": current, "old": legacy})
    assert worker._reading_projection_versions(json.dumps(frozen)) == {"new": "reading-model-input/1", "old": None}
    assert worker._reading_projection_versions(None) == {}


def test_unknown_frozen_renderer_is_not_downgraded_to_legacy():
    request = replace(_request(), selector_version="0.9.0")
    manifest = generation.generation_manifest(request, payload(request),
        execution_versions=batch._execution_versions(request), reading_model_projection="future-unavailable/99")
    frozen = batch._freeze_generations({"future": manifest})
    with pytest.raises(ModelResponseError, match="READING_MODEL_PROJECTION_UNAVAILABLE"):
        worker._reading_projection_versions(json.dumps(frozen))


@pytest.mark.parametrize("bad", [None, False, {}, []])
def test_present_wrong_type_is_not_the_missing_legacy_field(bad):
    request = replace(_request(), selector_version="0.9.0")
    manifest = generation.generation_manifest(request, payload(request),
        execution_versions=batch._execution_versions(request))
    manifest["reading_model_projection"] = bad
    with pytest.raises(ModelResponseError, match="READING_MODEL_PROJECTION_UNAVAILABLE"):
        worker._reading_projection_versions(json.dumps(batch._freeze_generations({"bad": manifest})))
