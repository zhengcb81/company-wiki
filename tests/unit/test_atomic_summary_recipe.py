"""New atomic scope recipe; captured older requests are not silently changed."""
import json
from pathlib import Path

import pytest

from company_wiki.automation import narrative_model_runtime as runtime
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_model import NarrativeModelResponse, ModelResponseError
from company_wiki.automation.narrative_summary_protocols import summary_bundle_format
from unit.test_narrative_extractive_runtime import selected

VERSION = 'reading-model-input/7'


@pytest.mark.parametrize('version', ['reading-model-input/4', 'reading-model-input/5', 'reading-model-input/6'])
def test_old_selected_input_and_http_instruction_remain_exact(version):
    path = Path(__file__).resolve().parents[1] / 'fixtures/atomic_recipe_legacy_requests.json'
    frozen = json.loads(path.read_text('utf-8'))
    request = runtime.build_model_request(NarrativeSelectResult.from_dict(frozen['selection']),
                                          reading_projection_version=version)
    assert {key: getattr(request, key) for key in frozen['requests'][version]} == frozen['requests'][version]


def test_explicit_atomic_recipe_identity_and_artifact_family():
    boundary = runtime.resolve_model_boundary(VERSION)
    assert boundary.prompt_version == 'reading-source-scoped/4.3.0'
    assert boundary.request_schema == 'narrative-model-request/8'
    assert boundary.decoder_version == 'reading-scoped-task-decoder/7'
    assert runtime.supports_durable_paid_response(VERSION)
    assert summary_bundle_format(boundary.prompt_version).raw_schema == 'narrative-bundle/2.1'


def test_unknown_new_scoped_prompt_is_not_silently_given_legacy_bundle_format():
    with pytest.raises(ValueError):
        summary_bundle_format('reading-source-scoped/unsupported')


def test_source_hints_are_compact_source_references_and_do_not_repeat_prose():
    source = selected(2, text_suffix='甲方正在完善海外服务网络。')
    request = runtime.build_model_request(source, reading_projection_version=VERSION)
    material = json.loads(request.data_json)['material']
    hints = material['source_frame_hints']
    assert hints['schema_version'] == 'source-frame-hints/1'
    assert hints['interpretation'] == 'finite_source_observations_not_business_facts'
    assert any(row.get('ongoing') for rows in hints['sources'].values() for row in rows)
    assert not hints['limited']
    for rows in hints['sources'].values():
        for row in rows:
            assert 'ordinal' in row
            assert not {'matching_text', 'text', 'reporting_prefix', 'locator'} & row.keys()


def test_atomic_recipe_has_no_hidden_subset_or_paid_repair():
    with pytest.raises(ModelResponseError):
        runtime.build_model_request(selected(2), reading_projection_version=VERSION, only_tasks={'t1'})


@pytest.mark.parametrize('version,review', [('reading-model-input/6', False), (VERSION, True)])
def test_new_assessor_detects_current_action_downgraded_to_future_without_rewriting_old(version, review):
    source = selected(1, text_suffix='甲方正在完善海外服务网络。')
    request = runtime.build_model_request(source, reading_projection_version=version)
    response = NarrativeModelResponse('offline', 'configured', request.prompt_version,
        json.dumps({'drafts_by_task': {'t1': [{'text': '甲方正在完善海外服务网络。',
                  'basis_parts': ['p1'], 'modality': 'planned'}]}}, ensure_ascii=False).encode())
    draft = runtime.decode_model_draft(response, selected=source, reading_projection_version=version)
    assert draft['claims'][0]['needs_review'] is review
    assert draft['claims'][0]['modality'] == 'planned', 'diagnostics never silently rewrite model claims'
