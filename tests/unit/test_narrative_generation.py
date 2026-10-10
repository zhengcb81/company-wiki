"""Per-source content identity excludes execution-only run/accounting fields."""

from dataclasses import replace
import json
import pytest
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from unit.test_narrative_batch import _request, Reader, _module


def manifest(request=None, reader=None, versions=None):
    from company_wiki.automation.narrative_generation import generation_manifest

    request = request or _request()
    module = _module()
    event = module.build_batch_events(
        request, reader or Reader(), now="2026-10-09T00:00:00Z"
    ).events[0]
    payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
    return generation_manifest(
        request,
        payload,
        execution_versions=versions or module._execution_versions(request),
    )


def test_generation_is_stable_for_run_budget_pricing_key_env_and_batch_members():
    original = _request()
    expected = manifest(original)
    model = original.model_options
    model.update(
        api_key_env="OTHER_KEY_NAME",
        timeout_seconds=9,
        max_response_bytes=20000,
        max_request_bytes=18000,
    )
    request = replace(
        original,
        run_id="another-run",
        max_seconds=100,
        max_tokens=1,
        max_micro_usd=0,
        pricing_version="another-price",
        input_micro_usd_per_million_tokens=1,
        output_micro_usd_per_million_tokens=2,
        max_final_bytes=100000,
        max_scratch_bytes=1000000,
        max_persistent_bytes=1000000,
        model_options_json=canonical_json(model),
    )
    assert manifest(request) == expected
    ref = replace(original.sources[0], document_id="other-document")
    assert manifest(replace(original, sources=(*original.sources, ref))) == expected


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_id", "another-model"),
        ("endpoint", "https://other.invalid/v1/chat/completions"),
        ("temperature", 0.8),
        ("thinking", True),
        ("max_output_tokens", 500),
    ],
)
def test_generation_changes_for_real_model_generation_inputs(field, value):
    request = _request()
    model = request.model_options
    model[field] = value
    assert manifest(
        replace(request, model_options_json=canonical_json(model))
    ) != manifest(request)


def test_generation_binds_source_processing_metadata_profile_and_all_versions():
    request = _request()
    expected = manifest(request)
    for field, value in [
        ("title", "A changed title"),
        ("document_kind", "investor_relations"),
        ("language", "zh"),
    ]:
        reader = Reader()
        reader.metadata[field] = value
        assert manifest(request, reader) != expected
    assert manifest(replace(request, profile="P4")) != expected
    versions = _module()._execution_versions(request)
    for key in ("adapter", "model_request_schema", "prompt", "parser", "selector"):
        assert manifest(request, versions={**versions, key: "new-version"}) != expected
    assert (
        manifest(
            request,
            versions={
                **versions,
                "handlers": {
                    **versions["handlers"],
                    "source.narrative_verify": "new-handler",
                },
            },
        )
        != expected
    )


def test_each_carrier_uses_actual_parser_and_pathless_component_fingerprint():
    from company_wiki.automation.narrative_generation import generation_manifest
    from company_wiki.automation.narrative_formats import parser_component

    request = _request()
    payload = SourceRevisionEventPayload.from_dict(
        json.loads(
            _module()
            .build_batch_events(request, Reader(), now="2026-10-09T00:00:00Z")
            .events[0]
            .payload_json
        )
    )
    wire = payload.to_dict()
    wire["source_ref"]["mime_type"] = "text/html"
    wire["source_metadata"]["source_class"] = "filing"
    payload = SourceRevisionEventPayload.from_dict(wire)
    request = replace(request, sources=(payload.source_ref,))
    versions = _module()._execution_versions(request)
    original = generation_manifest(request, payload, execution_versions=versions)
    other_batch_version = generation_manifest(
        request,
        payload,
        execution_versions={**versions, "document_normalization": "pptx-9"},
    )
    assert original == other_batch_version
    name, version = parser_component("text/html", "filing")
    assert original["parser_component"] == {"name": name, "version": version}
    # This interface takes the normalization owner's real fingerprint, with no
    # model location in identity. HTML never absorbs a PPTX/OCR fingerprint.
    wire["source_ref"]["mime_type"] = (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    pptx = SourceRevisionEventPayload.from_dict(wire)
    request = replace(request, sources=(pptx.source_ref,))
    component = {
        "format": "pptx",
        "parser_name": "document_normalization",
        "parser_version": "2.0.0",
        "ocr_fingerprint": "a" * 64,
    }
    one = generation_manifest(
        request, pptx, execution_versions=versions, parser_components=component
    )
    two = generation_manifest(
        request,
        pptx,
        execution_versions=versions,
        parser_components={**component, "ocr_fingerprint": "b" * 64},
    )
    assert one != two


def test_refresh_is_explicit_boolean_and_default_wire_remains_legacy_exact():
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest

    request = _request()
    assert "refresh" not in request.to_dict()
    assert (
        NarrativeBatchRequest.from_dict(
            {**request.to_dict(), "refresh": False}
        ).request_sha256
        == request.request_sha256
    )
    refresh = NarrativeBatchRequest.from_dict({**request.to_dict(), "refresh": True})
    assert refresh.refresh and refresh.request_sha256 != request.request_sha256
    assert manifest(refresh) == manifest(request)
    for invalid in (1, "true", None):
        with pytest.raises(ValueError, match="refresh"):
            NarrativeBatchRequest.from_dict({**request.to_dict(), "refresh": invalid})


def test_one_hundred_source_reuse_binding_remains_inside_existing_persistence_cap():
    from company_wiki.automation.narrative_generation import generation_manifest

    module = _module()
    request = _request()
    refs = tuple(
        replace(
            request.sources[0],
            document_id="urn:company-wiki:document:sha256:" + format(index, "064x"),
        )
        for index in range(100)
    )
    request = replace(request, sources=refs)
    binding = module.build_batch_events(request, Reader(), now="2026-10-09T00:00:00Z")
    manifests, pins = {}, {}
    for event in binding.events:
        payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
        ref = payload.source_ref
        manifests[event.subject_id] = generation_manifest(
            request, payload, execution_versions=module._execution_versions(request)
        )
        pins[event.subject_id] = {
            "artifact_version_id": "narrative-" + format(len(pins), "032x"),
            "content_sha256": "c" * 64,
            "byte_size": 3000,
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "source_sha256": ref.content_sha256,
        }
    binding = replace(
        binding, generation_manifests=manifests, reused_artifact_pins=pins
    )
    frozen = module._frozen_binding(request, binding)
    assert len(frozen.encode("utf-8")) <= 262144


def test_new_control_locators_are_measured_and_legacy_storage_baseline_is_not_resigned(
    tmp_path,
):
    from types import SimpleNamespace

    module = _module()
    catalog_dir = tmp_path / "catalog"
    work = tmp_path / "work"
    catalog_dir.mkdir()
    work.mkdir()
    catalog = SimpleNamespace(
        config=SimpleNamespace(
            catalog_dir=catalog_dir, database_path=catalog_dir / "catalog.sqlite"
        )
    )
    digest = "a" * 64
    guard = module._storage_guard(
        _request(), catalog, tmp_path / "auto.sqlite", work, digest
    )
    before = guard.snapshot().persistent_added_bytes
    control = catalog_dir / "narrative-generations"
    control.mkdir()
    (control / "pointer.json").write_bytes(b"actual owned locator")
    assert guard.snapshot().persistent_added_bytes == before + len(
        b"actual owned locator"
    )
    assert len(guard.paths) == 9
    legacy = work / "storage-baseline.json"
    legacy.write_text(
        canonical_json({"input_hash": digest, "sizes": [0] * 8}), encoding="utf-8"
    )
    original = legacy.read_bytes()
    old_guard = module._storage_guard(
        _request(), catalog, tmp_path / "auto.sqlite", work, digest, read_only=True
    )
    assert len(old_guard.paths) == 8 and legacy.read_bytes() == original


def test_raw_reasoning_effort_is_causal_without_resigning_legacy_omissions():
    request = _request()
    model = request.model_options
    model.pop("reasoning_effort", None)
    omitted = replace(request, model_options_json=canonical_json(model))
    old = manifest(omitted)
    null = replace(omitted, model_options_json=canonical_json({**model, "reasoning_effort": None}))
    assert manifest(null) == old
    low = manifest(replace(omitted, model_options_json=canonical_json({**model, "reasoning_effort": "low"})))
    high = manifest(replace(omitted, model_options_json=canonical_json({**model, "reasoning_effort": "high"})))
    assert low["model"]["reasoning_effort"] == "low"
    assert low != high and low != old
