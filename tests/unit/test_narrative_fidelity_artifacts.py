"""New assessment cannot be dropped or confused with historical bundle wires."""
import json

import pytest

from company_wiki.automation.narrative_contracts import NarrativeBundle, NarrativeContractError
from company_wiki.automation.narrative_model import NarrativeModelResponse
from company_wiki.automation.narrative_model_runtime import build_model_request
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.narrative_summary_execution import parse_summary_job_result
from company_wiki.automation.narrative_summary_execution import wrap_summary, extract_summary_execution
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from unit.test_narrative_extractive_runtime import selected


def materials(source=None):
    source=source or selected(2)
    view=compile_scoped_model_view(source,max_claims=40)
    task=view.model_tasks[0]
    sid=task.support_ids[0]
    text=next(span.raw_text for span in source.evidence_spans if span.span_id==sid)
    part='p'+str(task.member_ids.index(sid)+1)
    request=build_model_request(source,reading_projection_version='reading-model-input/6')
    response=NarrativeModelResponse('offline','configured',request.prompt_version,json.dumps({
        'drafts_by_task':{task.key:[{'text':text[:280],'basis_parts':[part],'modality':'actual'}]}
    },ensure_ascii=False).encode())
    summary=NarrativeSummarizeHandler._completed_result(source,source.prompt_review,response,
        reading_projection_version='reading-model-input/6')
    return source,summary


def test_projected_bundle_has_its_own_assessed_schema_without_raw_source_fields():
    from unit.test_narrative_source_owned_model_boundary import official_reading
    source,summary=materials(official_reading())
    wire=NarrativeVerifyHandler._bundle(source,summary,source.prompt_review).to_dict()
    assert wire['schema_version']=='narrative-bundle/3.1'
    assert 'subject_binding' in wire and 'source_ref' not in wire
    assert wire['summary_assessment']['semantic_status']=='not_evaluated'
    assert NarrativeBundle.from_dict(wire).to_dict()==wire


def test_new_bundle_carries_recomputed_assessment_and_actual_producer():
    source,summary=materials()
    bundle=NarrativeVerifyHandler._bundle(source,summary,source.prompt_review)
    assert bundle.schema_version=='narrative-bundle/2.1'
    wire=bundle.to_dict()
    assert wire['versions']['bundle_producer']=='1.1.0'
    assert wire['summary_assessment']['missing_requested_task_keys']==['t2']
    assert wire['summary_assessment']['semantic_status']=='not_evaluated'
    assert NarrativeBundle.from_dict(wire).to_dict()==wire


@pytest.mark.parametrize('mutation',['missing','claims','source_plan','coverage','legacy_schema'])
def test_assessment_cannot_be_removed_or_forged(mutation):
    source,summary=materials()
    wire=NarrativeVerifyHandler._bundle(source,summary,source.prompt_review).to_dict()
    if mutation=='missing':
        wire.pop('summary_assessment',None)
    elif mutation=='legacy_schema':
        wire['schema_version']='narrative-bundle/2.0'
    elif mutation=='coverage':
        wire['summary_assessment']['requested_emission_complete']=True
    else:
        wire['summary_assessment'][mutation+'_sha256']='f'*64
    with pytest.raises(NarrativeContractError):
        NarrativeBundle.from_dict(wire)


def test_assessed_prompt_requires_internal_report_not_bare_summary():
    source,summary=materials()
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(summary.to_dict(),selected=source)


def test_actual_completed_result_report_survives_internal_wrapper_and_rechecks_source():
    source=selected(2)
    request=build_model_request(source,reading_projection_version='reading-model-input/6')
    response=NarrativeModelResponse('offline','configured',request.prompt_version,json.dumps({
        'drafts_by_task':{'t1':[{'text':source.evidence_spans[0].raw_text,'basis_parts':['p1'],'modality':'actual'}]}
    },ensure_ascii=False).encode())
    report={}
    summary=NarrativeSummarizeHandler._completed_result(source,source.prompt_review,response,
        reading_projection_version='reading-model-input/6',execution_report=report)
    wire=wrap_summary(summary,report)
    assert wire['schema_version']=='narrative-summary-execution/2'
    assert parse_summary_job_result(wire,selected=source)==summary
    assert extract_summary_execution(wire)==report
    wire['assessment']['source_plan_sha256']='f'*64
    with pytest.raises(NarrativeContractError):
        parse_summary_job_result(wire,selected=source)


def test_publication_effect_uses_actual_bundle_producer():
    from types import SimpleNamespace
    from company_wiki.automation.models import make_effect_key, canonical_json_hash
    source,summary=materials()
    bundle=NarrativeVerifyHandler._bundle(source,summary,source.prompt_review)
    context=SimpleNamespace(job=SimpleNamespace(job_id='verification-job'),
                            event=SimpleNamespace(observed_at='2026-10-30T12:00:00Z'))
    effect=NarrativeVerifyHandler._effect(context,bundle)
    payload=canonical_json_hash({'verification_job_id':'verification-job',
                                'bundle_sha256':canonical_json_hash(bundle.to_dict())})
    assert effect.effect_key==make_effect_key(effect.effect_type,effect.target,payload,'1.1.0')
    assert effect.effect_key!=make_effect_key(effect.effect_type,effect.target,payload,'1.0.0')


def test_generation_uses_same_bundle_format_as_verified_output():
    from dataclasses import replace
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation.narrative_generation import generation_manifest
    from unit.test_narrative_batch import _request
    from unit.test_narrative_reading_projection_generation import payload
    request=replace(_request(),selector_version='0.9.0',reading_model_projection='reading-model-input/6')
    manifest=generation_manifest(request,payload(request),execution_versions=batch._execution_versions(request),
                                 reading_model_projection='reading-model-input/6')
    assert manifest['bundle_schema']=='narrative-bundle/2.1'
    assert manifest['bundle_producer']=='1.1.0'
    assert manifest['execution_versions']['prompt']=='reading-source-scoped/4.2.0'


def test_explicit_protocol_skip_keeps_generation_format_without_fake_model_or_assessment():
    source=selected(1)
    wire=source.to_dict()
    wire['evidence_spans']=[]
    wire['selection'].update(status='skipped_no_narrative',selected_count=0)
    wire['reading_context']['groups']=[]
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult
    source=NarrativeSelectResult.from_dict(wire)
    summary=NarrativeSummarizeHandler._skip_result(source)
    bundle=NarrativeVerifyHandler._bundle(source,summary,source.prompt_review,
                                          reading_projection_version='reading-model-input/6')
    wire=bundle.to_dict()
    assert wire['schema_version']=='narrative-bundle/2.1'
    assert wire['versions']['bundle_producer']=='1.1.0'
    assert wire['versions']['prompt']=='reading-source-scoped/4.2.0'
    assert wire['versions']['model'] is None and wire['summary']['model'] is None
    assert wire['summary_assessment'] is None
    assert wire['quality_status']=='skipped_no_narrative'
    assert NarrativeBundle.from_dict(wire).to_dict()==wire


def test_batch_receipt_keeps_assessment_without_optional_provider_meter_fields():
    from types import SimpleNamespace
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation.narrative_summarize import _success
    from company_wiki.automation.models import canonical_json
    from company_wiki.automation.narrative_summary_assessment import assess_summary
    source,summary=materials()
    view=compile_scoped_model_view(source,max_claims=40)
    report=assess_summary(source,summary.to_dict()['draft']['claims'],plan_max_claims=40,
                          requested_task_keys=[task.key for task in view.model_tasks])
    result=_success(summary,execution=report)
    raw=canonical_json(result.to_dict())
    assert '"reasoning_tokens"' not in raw and '"usage_diagnostic"' not in raw
    attempt=SimpleNamespace(attempt_id='summary-attempt',result_json=raw)
    store=SimpleNamespace(list_attempts=lambda _:[attempt])
    rows=batch._attempt_model_diagnostics(store,{},SimpleNamespace(job_id='summary-job'))
    assert len(rows)==1 and rows[0]['execution']==report


def test_terminal_compaction_keeps_assessment_without_retain_full_summary_body():
    from company_wiki.automation.narrative_summary_assessment import assess_summary
    source,summary=materials()
    view=compile_scoped_model_view(source,max_claims=40)
    report=assess_summary(source,summary.to_dict()['draft']['claims'],plan_max_claims=40,
                          requested_task_keys=[task.key for task in view.model_tasks])
    terminal={'schema_version':'narrative-terminal-receipt/1.0','execution':report}
    assert extract_summary_execution(terminal)==report
