"""Real local batches obey measured storage limits even with small requests."""

from dataclasses import asdict
import json

import pytest

from company_wiki.automation.narrative_batch import run_batch
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactNotVisibleError
from support.narrative_batch_fixtures import isolated_batch_directory, prepare_source_catalog


@pytest.mark.parametrize("dimension,cap,error", [
    (None, None, None),
    ("persistent", 1024, "PERSISTENT_BYTES_EXCEEDED"),
    ("scratch", 1024, "SCRATCH_BYTES_EXCEEDED"),
    ("final", 1024, "FINAL_BYTES_EXCEEDED"),
])
def test_local_skip_batch_uses_actual_storage(tmp_path_factory, dimension, cap, error):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root)
        try:
            ref, _, _ = next(item for item in state.indexed.values() if item[2] == "ir_policy")
            originals = {path: path.read_bytes() for path in state.raw_paths.values()}
            initial_objects = state.catalog.narrative_object_bytes()
            wire = {
                "schema_version": "narrative-batch-request/1", "run_id": "small-local-skip",
                "profile": "P1", "selector_version": "0.8.0", "sources": [asdict(ref)],
                "max_seconds": 30, "max_tokens": 1, "max_cost_usd": "0",
                "max_final_bytes": 16384, "max_persistent_bytes": 65536, "max_scratch_bytes": 4096,
                "model": {"model_id": "fixture-only", "endpoint": "https://fixtures.invalid/v1/chat/completions",
                          "api_key_env": "UNREAD_AUTOMATION_TEST_KEY", "max_response_bytes": 1024},
                "pricing": {"version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1000000,
                            "output_micro_usd_per_million_tokens": 1000000},
            }
            if dimension is not None:
                wire[f"max_{dimension}_bytes"] = cap
            request = NarrativeBatchRequest.from_dict(wire)
            db = root / "AUTO.sqlite"
            options = dict(project_root=root, catalog_config_path=state.config_path,
                           db_path=db, work_dir=root / "work")
            result = run_batch(request, **options)
            assert result["budget"]["tokens"] == 0
            assert result["storage"]["persistent_added_bytes"] <= request.max_persistent_bytes
            assert result["storage"]["scratch_peak_bytes"] <= request.max_scratch_bytes
            runs = NarrativeRunStore(db)
            artifacts = state.catalog.open_narrative_artifact_reader()
            try:
                identity = dict(document_id=ref.document_id, source_id=ref.source_id,
                                source_sha256=ref.content_sha256)
                if error is None:
                    assert result["status"] == "completed", result
                    version = artifacts.latest_visible_version(**identity)
                    _, data = artifacts.read_exact(artifact_version_id=version.artifact_version_id, **identity)
                    assert json.loads(data)["selection"]["status"] == "skipped_no_narrative"
                else:
                    assert result["status"] == "storage_exhausted", result
                    assert runs.get_run(request.run_id).block_reason == error
                    assert state.catalog.narrative_object_bytes() == initial_objects
                    with pytest.raises(NarrativeArtifactNotVisibleError):
                        artifacts.latest_visible_version(**identity)
            finally:
                artifacts.close()
            before = runs.get_run(request.run_id)
            resumed = run_batch(request, **options)
            assert resumed["status"] == result["status"]
            assert resumed["documents"] == result["documents"] and resumed["budget"] == result["budget"]
            after = runs.get_run(request.run_id)
            if error is None:
                assert after == before
            else:
                # A blocked, unpublished outbox effect still has a recovery
                # path. A retry may renew the runtime fence, preserving the
                # same binding, refusal, and paid usage.
                assert (after.binding_json, after.block_reason) == (before.binding_json, error)
                assert state.catalog.narrative_object_bytes() == initial_objects
            assert {path: path.read_bytes() for path in originals} == originals
        finally:
            state.catalog.close()
