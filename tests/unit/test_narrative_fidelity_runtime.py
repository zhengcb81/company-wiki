"""Explicit fidelity protocol; legacy scoped and extractive wires retain identity."""
import json

import pytest

from company_wiki.automation import narrative_model_runtime as runtime
from company_wiki.automation.narrative_model import NarrativeModelResponse, ModelResponseError
from unit.test_narrative_extractive_runtime import selected

VERSION='reading-model-input/6'


def reply(source,rows):
    request=runtime.build_model_request(source,reading_projection_version=VERSION)
    response=NarrativeModelResponse('offline','configured',request.prompt_version,
        json.dumps({'drafts_by_task':rows},ensure_ascii=False).encode())
    return runtime.decode_model_draft(response,selected=source,reading_projection_version=VERSION)


def test_new_identity_and_actual_request_plan_are_explicit():
    source=selected(8)
    boundary=runtime.resolve_model_boundary(VERSION)
    assert boundary.prompt_version=='reading-source-scoped/4.2.0'
    assert boundary.request_schema=='narrative-model-request/7'
    request=runtime.build_model_request(source,reading_projection_version=VERSION)
    wire=json.loads(request.with_output_budget(8192).data_json)
    assert wire['schema_version']=='narrative-model-request/7'
    assert wire['material']['max_claims']==40
    assert wire['output_plan']['max_claims']==40
    assert wire['output_plan']['max_claims_per_task']>=3
    assert wire['output_plan']['configured_output_tokens']==8192
    assert 'single modality' in request.instruction
    assert runtime.supports_durable_paid_response(VERSION)


def test_legacy_prompts_and_plan_markers_are_preserved():
    source=selected(8)
    old=runtime.build_model_request(source,reading_projection_version='reading-model-input/4')
    wire=json.loads(old.data_json)
    assert old.prompt_version=='reading-source-scoped/4.1.0'
    assert wire['schema_version']=='narrative-model-request/5'
    assert wire['material']['max_claims']==20
    assert wire['output_plan']['max_claims_per_task']==2
    assert runtime.resolve_model_boundary('reading-model-input/5').request_schema=='narrative-model-request/6'


def test_explicit_protocol_does_not_silently_allow_unrecorded_subset_requests():
    with pytest.raises(ModelResponseError):
        runtime.build_model_request(selected(2),reading_projection_version=VERSION,only_tasks={'t1'})


def test_final_quality_keeps_known_fidelity_warning_after_legacy_projection():
    source=selected(1,text_suffix='根据新闻报道，该事项涉及家电产品。')
    draft=reply(source,{'t1':[{'text':'该事项涉及家电产品。','basis_parts':['p1'],'modality':'actual'}]})
    assert draft['claims'][0]['needs_review']
    assert draft['status']=='needs_review'


def test_missing_tasks_are_observed_without_paid_repair_or_fabricated_claims():
    source=selected(3)
    draft=reply(source,{'t1':[{'text':'公司新产品已完成海外客户认证。','basis_parts':['p1'],'modality':'actual'}]})
    assert len(draft['claims'])==1
    assert draft['status']=='needs_review'
