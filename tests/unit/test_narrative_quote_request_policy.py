"""New-template composition chooses quote-primary; frozen parser intent is unchanged."""
from copy import deepcopy
import json

import pytest

from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.source_catalog.official_source_flow import prepare_official_narrative_request
from unit.test_narrative_batch_request import _request
from unit.test_narrative_versioned_resume import frozen_run as _existing_frozen_run

frozen_run = _existing_frozen_run


def template(**overrides):
    value = _request()
    imports = [{'source_ref': ref} for ref in value.pop('sources')]
    value.update(selector_version='0.9.0', **overrides)
    return imports, value


@pytest.mark.parametrize('profile', ['P1', 'P2', 'P4'])
def test_new_explicit_shared_template_selects_quote_primary_without_mutating_input(profile):
    imports, value = template(profile=profile)
    frozen = deepcopy((imports, value))
    request = prepare_official_narrative_request(imports, batch_template=value)
    assert request.reading_model_projection == 'reading-model-input/5'
    assert request.selector_version == '0.9.0' and request.profile == profile
    assert request.model_options['model_id'] == value['model']['model_id']
    assert request.model_options['api_key_env'] == value['model']['api_key_env']
    assert (imports, value) == frozen
    parsed = NarrativeBatchRequest.from_dict(json.loads(json.dumps(request.to_dict())))
    assert parsed.request_sha256 == request.request_sha256


@pytest.mark.parametrize('version', ['4', '5', '6', '7'])
def test_explicit_recipe_is_respected_exactly(version):
    imports, value = template(reading_model_projection='reading-model-input/' + version)
    request = prepare_official_narrative_request(imports, batch_template=value)
    assert request.reading_model_projection == value['reading_model_projection']


@pytest.mark.parametrize('selector', [None, '0.7.0', '0.8.0'])
def test_omitted_or_nonshared_selector_is_not_upgraded(selector):
    imports, value = template()
    if selector is None:
        value.pop('selector_version')
    else:
        value['selector_version'] = selector
    request = prepare_official_narrative_request(imports, batch_template=value)
    assert request.reading_model_projection is None
    assert request.selector_version == selector


@pytest.mark.parametrize('projection', [None, True, 'reading-model-input/99'])
def test_explicit_invalid_projection_is_not_replaced_by_default(projection):
    imports, value = template(reading_model_projection=projection)
    frozen = deepcopy(value)
    with pytest.raises(ValueError):
        prepare_official_narrative_request(imports, batch_template=value)
    assert value == frozen


def test_complete_old_raw_request_is_not_treated_as_new_template():
    value = {**_request(), 'selector_version': '0.9.0'}
    old = NarrativeBatchRequest.from_dict(value)
    request = prepare_official_narrative_request(
        [{'source_ref': ref} for ref in value['sources']], batch_template=value)
    assert request.reading_model_projection is None
    assert request.to_dict() == old.to_dict()
    assert request.request_sha256 == old.request_sha256
    assert request.input_hash == old.input_hash


@pytest.mark.parametrize('membership_field', ['sources', 'items'])
def test_membership_presence_even_empty_is_not_a_new_template(membership_field):
    imports, value = template()
    value[membership_field] = []
    request = prepare_official_narrative_request(imports, batch_template=value)
    assert request.reading_model_projection is None


@pytest.mark.parametrize('schema', ['1', '2'])
def test_old_omitted_projection_parsing_retains_scoped_four_and_hash(schema):
    from company_wiki.automation import narrative_batch as batch
    from unit.test_narrative_batch import Reader

    value = {**_request(), 'selector_version': '0.9.0'}
    # The existing Reader fixture publishes a 123-byte source. Match its real
    # Ref rather than accidentally exercising SOURCE_REF_CHANGED here.
    value['sources'][0]['byte_size'] = 123
    if schema == '2':
        value['schema_version'] = 'narrative-batch-request/2'
        value['items'] = [{'kind': 'raw', 'source_ref': ref} for ref in value.pop('sources')]
    request = NarrativeBatchRequest.from_dict(value)
    repeated = NarrativeBatchRequest.from_dict(json.loads(json.dumps(request.to_dict())))
    assert request.reading_model_projection is None
    assert repeated.to_dict() == request.to_dict()
    assert repeated.request_sha256 == request.request_sha256
    assert repeated.input_hash == request.input_hash
    payloads, _ = batch._current_sources(request, Reader())
    generation = batch._item_generation(request, payloads[0])
    assert generation['reading_model_projection'] == 'reading-model-input/4'


def test_builder_does_not_expand_projected_schema_support():
    imports, value = template()
    value['schema_version'] = 'narrative-batch-request/2'
    value['items'] = [{'kind': 'raw', **row} for row in imports]
    with pytest.raises(ValueError):
        prepare_official_narrative_request(imports, batch_template=value)


def test_new_quote_primary_still_builds_the_actual_model_ranking_request():
    from company_wiki.automation.narrative_model_runtime import build_model_request
    from unit.test_narrative_extractive_runtime import selected

    imports, value = template()
    request = prepare_official_narrative_request(imports, batch_template=value)
    model_request = build_model_request(selected(3), reading_projection_version=request.reading_model_projection)
    view = json.loads(model_request.data_json)
    assert model_request.prompt_version == 'reading-source-extractive/5.0.0'
    assert view['schema_version'] == 'narrative-model-request/6'
    assert 'decisions' in view['response_schema']['properties']
    assert view['output_plan']['available_task_count'] == 3


def test_actual_frozen_resume_keeps_request_and_persisted_jobs_budget(frozen_run):
    from company_wiki.automation import narrative_batch as batch

    state, request, store, runs, run = frozen_run
    restored = NarrativeBatchRequest.from_dict(json.loads(json.dumps(request.to_dict())))
    original = (request.request_sha256, run, store.list_jobs(), runs.budget_snapshot(run.run_id))
    binding, _versions, jobs = batch._resume_binding(restored, state.reader, store, runs, run, deadline=None)
    assert restored.reading_model_projection is None
    assert restored.request_sha256 == original[0]
    assert binding.input_hash == run.input_hash
    assert jobs == store.list_jobs(job_ids=run.job_ids)
    assert (runs.get_run(run.run_id), store.list_jobs(), runs.budget_snapshot(run.run_id)) == original[1:]
    assert all(store.list_attempts(job_id) == () for job_id in run.job_ids)
