"""Artifact completeness and metadata provenance are separate from visibility."""

from dataclasses import replace
import json
import pytest
from company_wiki.automation.models import canonical_json, canonical_json_hash
from company_wiki.automation.narrative_batch import (
    build_batch_events,
    _execution_versions,
)
from company_wiki.automation.narrative_contracts import (
    SourceRevisionEventPayload,
    NarrativeBundle,
)
from company_wiki.automation.narrative_generation import (
    generation_manifest,
    find_reuse_pin,
)
from company_wiki.source_catalog.narrative_artifact_store import (
    NarrativeArtifactDraft,
    NarrativeArtifactReader,
    LocalNarrativeObjectStore,
)
from support.narrative_transport_fixture import published_fixture
from unit.test_narrative_batch import _request


@pytest.mark.parametrize(
    "state", ["legacy", "prepared", "partial", "complete", "forged_metadata"]
)
def test_only_complete_matching_visible_and_replayed_candidate_is_eligible(
    tmp_path, state
):
    with published_fixture(tmp_path, scoped_policy=True) as fixture:
        request = replace(_request(), sources=(fixture.source_ref,))
        binding = build_batch_events(
            request, fixture.reader, now="2026-10-09T00:00:00Z"
        )
        payload = SourceRevisionEventPayload.from_dict(
            json.loads(binding.events[0].payload_json)
        )
        manifest = generation_manifest(
            request, payload, execution_versions=_execution_versions(request)
        )
        # Fixture uses a replay model; match the actual model provenance for this
        # candidate responsibility test without bypassing source/locator checks.
        original = json.loads(fixture.payload)
        manifest["model"]["model_id"] = original["versions"]["model"]
        manifest["execution_versions"]["prompt"] = original["versions"]["prompt"]
        manifest["execution_versions"]["adapter"] = original["summary"]["model"][
            "adapter_id"
        ]
        metadata = {
            "generation_manifest": manifest,
            "generation_sha256": canonical_json_hash(manifest),
        }
        if state == "legacy":
            metadata = {}
        if state == "partial":
            original["selection"].update(status="partial", coverage_complete=False)
            original["quality_status"] = "needs_review"
        if state == "forged_metadata":
            metadata["generation_manifest"]["source_metadata"]["title"] = (
                "forged title attribution"
            )
            metadata["generation_sha256"] = canonical_json_hash(manifest)
        data = canonical_json(NarrativeBundle.from_dict(original).to_dict()).encode()
        version = fixture.version
        draft = NarrativeArtifactDraft(
            "candidate-effect",
            canonical_json_hash({"candidate": state}),
            version.document_id,
            version.source_id,
            version.source_sha256,
            version.producer_name,
            version.producer_version,
            version.policy_sha256,
            original["selection"]["status"],
            original["quality_status"],
            canonical_json(metadata),
            "2026-10-09T00:00:00Z",
        )
        prepared = fixture.artifacts.prepare(draft, data)
        if state != "prepared":
            fixture.artifacts.activate(
                draft.effect_id,
                verified_after_hash=prepared.content_sha256,
                activated_at="2026-10-09T00:00:01Z",
            )
        reader = NarrativeArtifactReader(
            fixture.catalog.config.database_path,
            LocalNarrativeObjectStore(fixture.catalog.config.catalog_dir),
        )
        try:
            if state == "forged_metadata":
                with pytest.raises(ValueError, match="BATCH_REUSE"):
                    find_reuse_pin(
                        reader,
                        fixture.reader,
                        payload,
                        manifest,
                        binding.source_facts[0],
                    )
            else:
                pin = find_reuse_pin(
                    reader, fixture.reader, payload, manifest, binding.source_facts[0]
                )
                assert (pin is not None) is (state == "complete")
                if pin:
                    assert pin["artifact_version_id"] == prepared.artifact_version_id
        finally:
            reader.close()
