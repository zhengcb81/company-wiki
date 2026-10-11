"""Real cache identity follows emitted generation options; no provider calls."""
from dataclasses import replace

import pytest
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_generation import generation_sha256, _projection_effective_model
from unit.test_narrative_batch import _request
from unit.test_narrative_generation import manifest


@pytest.mark.parametrize("field", ["thinking", "temperature", "reasoning_split", "reasoning_effort"])
def test_optional_null_matches_omitted_wire_and_generation(field):
    request = _request()
    options = request.model_options
    options.pop(field, None)
    omitted = replace(request, model_options_json=canonical_json(options))
    nullable = replace(request, model_options_json=canonical_json({**options, field: None}))
    old_manifest = manifest(omitted)
    assert _projection_effective_model(options) == _projection_effective_model({**options, field: None})
    assert manifest(nullable) == old_manifest
    assert generation_sha256(manifest(nullable)) == generation_sha256(old_manifest)


@pytest.mark.parametrize("field,values", [
    ("thinking", ("disabled", "enabled")),
    ("temperature", (0.2, 0.8)),
    ("reasoning_split", (False, True)),
    ("reasoning_effort", ("low", "high")),
    ("max_output_tokens", (100, 200)),
])
def test_real_effective_option_change_invalidates_both_carriers(field, values):
    request = _request()
    options = request.model_options
    left = {**options, field: values[0]}
    right = {**options, field: values[1]}
    assert _projection_effective_model(left) != _projection_effective_model(right)
    assert generation_sha256(manifest(replace(request, model_options_json=canonical_json(left)))) != generation_sha256(manifest(replace(request, model_options_json=canonical_json(right))))


def test_execution_label_does_not_create_paid_content_identity():
    request = _request()
    options = request.model_options
    with_label = replace(request, model_options_json=canonical_json({**options, "purpose": "narrative"}))
    assert manifest(with_label) == manifest(request)
