"""Every model job owns its actual prompt, independent of request container."""
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.narrative_generation import generation_manifest
from company_wiki.automation.narrative_run_store import model_prompt_version
from unit.test_narrative_batch import Reader, _request


@pytest.mark.parametrize("request_schema", ["narrative-batch-request/1", "narrative-batch-request/2"])
@pytest.mark.parametrize("projection", [None, "reading-model-input/1", "reading-model-input/2", "reading-model-input/3"])
def test_actual_job_prompt_is_frozen_for_raw_new_generation_and_old_bindings_stay_exact(request_schema, projection):
    request = replace(_request(), schema_version=request_schema, selector_version="0.9.0")
    binding = batch.build_batch_events(request, Reader(), now="2026-10-14T00:00:00Z")
    payload = SourceRevisionEventPayload.from_dict(json.loads(binding.events[0].payload_json))
    manifest = generation_manifest(request, payload, execution_versions=batch._execution_versions(request),
        reading_model_projection=projection)
    binding = replace(binding, generation_manifests={payload.item_key: manifest})
    jobs = (SimpleNamespace(job_id="select", job_type="source.narrative_select", subject_id=payload.item_key),
        SimpleNamespace(job_id="summary", job_type="source.narrative_summarize", subject_id=payload.item_key))
    frozen_wire = batch._frozen_binding(request, binding, jobs=jobs)
    frozen = json.loads(frozen_wire)
    expected = manifest["execution_versions"]["prompt"]
    if projection == "reading-model-input/2":
        assert expected == "reading-source-owned/2.0.0"
    elif projection in (None, "reading-model-input/1"):
        assert expected == "1.7.0"
    assert frozen["execution_versions"]["prompt"] == "1.7.0"
    assert model_prompt_version(frozen_wire, job_id="summary", default_prompt="1.7.0") == expected
    if projection in ("reading-model-input/2", "reading-model-input/3") or request_schema == "narrative-batch-request/2":
        assert frozen["job_prompt_versions"] == {"summary": expected}
    else:
        assert "job_prompt_versions" not in frozen


@pytest.mark.parametrize("only_select", [False, True])
def test_cached_source_without_model_work_does_not_acquire_a_model_prompt_responsibility(only_select):
    request = replace(_request(), selector_version="0.9.0")
    binding = batch.build_batch_events(request, Reader(), now="2026-10-14T00:00:00Z")
    payload = SourceRevisionEventPayload.from_dict(json.loads(binding.events[0].payload_json))
    manifest = generation_manifest(request, payload, execution_versions=batch._execution_versions(request),
        reading_model_projection=None)
    # This independent cached-source receipt has no model job. Its source
    # contract does not need the new model's prompt, even with an explicit scope.
    del manifest["execution_versions"]["prompt"]
    binding = replace(binding, generation_manifests={payload.item_key:manifest})
    jobs = ((SimpleNamespace(job_id="select", job_type="source.narrative_select", subject_id=payload.item_key),)
        if only_select else ())
    frozen = json.loads(batch._frozen_binding(request,binding,jobs=jobs))
    assert "job_prompt_versions" not in frozen


def test_a_real_model_job_cannot_fall_back_when_its_prompt_is_missing():
    manifest = {"execution_versions": {"selector": "0.9.0"}}
    job = SimpleNamespace(job_id="summary", job_type="source.narrative_summarize", subject_id="one")
    with pytest.raises(KeyError, match="prompt"):
        batch._job_prompt_versions((job,), {"one":manifest})


def test_mixed_reuse_freezes_only_the_source_with_actual_model_work():
    job = SimpleNamespace(job_id="summary-new", job_type="source.narrative_summarize", subject_id="new")
    manifests = {"cached":{"execution_versions":{"selector":"0.9.0"}},
        "new":{"execution_versions":{"prompt":"reading-source-owned/2.0.0"}}}
    assert batch._uses_distinct_job_prompts(manifests,"1.7.0",jobs=(job,))
    assert batch._job_prompt_versions((job,),manifests) == {"summary-new":"reading-source-owned/2.0.0"}
