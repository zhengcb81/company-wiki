"""Formal manifest/factory/summary/verify integration of explicit v4."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.automation import narrative_model_runtime as runtime
from company_wiki.automation import narrative_model as legacy
from company_wiki.automation.models import HandlerMetrics, HandlerOutcome
from company_wiki.automation.narrative_contracts import (
    NarrativeSelectResult, NarrativeSummaryResult, SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from unit.test_narrative_source_owned_model_boundary import official_reading
from unit.test_narrative_output_language_binding import EN, ES, selected_english, manifests
from unit.test_narrative_summarize_handler import _context

V4='reading-model-input/4'


def _run(*, text=EN, projection=V4):
    selected=selected_english()
    sent=[]
    class Caller:
        def generate(self, context, request):
            sent.append(request)
            data=json.loads(request.data_json)
            assert data['schema_version']=='narrative-model-request/5'
            assert data['material']['tasks'][0]['key']=='t1'
            body=json.dumps({'drafts_by_task':{'t1':[{
                'text':text,'basis_parts':['p1'],'modality':'actual'}]}}).encode()
            return legacy.NarrativeModelResponse('offline','configured',request.prompt_version,body), HandlerMetrics(tokens=92,cost_usd=.001,duration_ms=7)
    result=NarrativeSummarizeHandler(model=None,model_caller=Caller(),
        reading_model_projection=lambda subject:projection)(_context(selected))
    return result,selected,sent


def test_actual_handler_uses_v4_and_one_existing_caller_then_canonical_result():
    result,selected,sent=_run()
    assert len(sent)==1 and result.outcome is HandlerOutcome.SUCCEEDED
    parsed=NarrativeSummaryResult.from_dict(result.result)
    parsed.validate_against(selected)
    assert parsed.draft.claims[0].claim_id=='t1-1'
    assert parsed.draft.claims[0].text==EN
    assert result.metrics.tokens==92 and result.metrics.cost_usd==.001


def test_actual_handler_preserves_paid_failure_and_no_retry_for_wrong_language():
    result,selected,sent=_run(text=ES)
    assert len(sent)==1 and result.outcome is HandlerOutcome.TERMINAL_FAILURE
    assert result.error.code=='SUMMARY_INVALID' and 'OUTPUT_LANGUAGE' in result.error.detail
    assert result.metrics.tokens==92
    assert 'failed_final' in result.result


def test_explicit_manifest_reaches_factory_validation_and_new_default_does_not_override_it():
    from company_wiki.automation import narrative_worker_factory as factory
    manifest=manifests(V4)
    assert manifest['reading_model_boundary']==runtime.reading_model_boundary_identity(V4)
    assert factory._validate_model_software(manifest)==V4
    assert manifests('reading-model-input/3')['execution_versions']['model_request_schema']=='narrative-model-request/4'
    from unit.test_narrative_generation import manifest as normal_manifest
    from unit.test_narrative_batch import _request
    assert normal_manifest(replace(_request(),selector_version='0.9.0'))['reading_model_projection']=='reading-model-input/5'
    assert 'reading_model_projection' not in normal_manifest(replace(_request(),selector_version='0.8.0'))


def test_explicit_manifest_decoder_dependencies_are_actual_and_causal(tmp_path,monkeypatch):
    from company_wiki.document_understanding import summary_tasks
    first=manifests(V4)
    dependencies=first['reading_model_boundary']['implementation_dependencies']
    assert {'runtime','scoped_protocol','source_task_plan','role_quality_owner','legacy_utilities','canonical_contracts'}<=set(dependencies)
    original=Path(summary_tasks.__file__)
    expected=hashlib.sha256(original.read_bytes().replace(b'\r\n',b'\n').replace(b'\r',b'\n')).hexdigest()
    assert dependencies['source_task_plan']==expected
    changed=tmp_path/'summary_task_implementation.py'
    changed.write_bytes(original.read_bytes()+b'\n# actual changed dependency bytes\n')
    monkeypatch.setattr(summary_tasks,'__file__',str(changed))
    second=manifests(V4)
    assert second['reading_model_boundary']!=first['reading_model_boundary']
    assert manifests('reading-model-input/3')['reading_model_boundary']==legacy.reading_model_boundary_identity('reading-model-input/3')


def test_stale_v4_implementation_rejected_by_actual_factory_before_call():
    from company_wiki.automation import narrative_worker_factory as factory
    frozen=manifests(V4)
    frozen['reading_model_boundary']['decoder_sha256']='0'*64
    with pytest.raises(legacy.ModelResponseError,match='BOUNDARY'):
        factory._validate_model_software(frozen)


def test_qa_own_support_and_context_survive_canonical_decode():
    wire=official_reading().to_dict()
    wire['reading_context']['schema_version']='du-production-reading/2'
    for group in wire['reading_context']['groups']:
        group['citation_views']=[{'support_evidence_ids':group['evidence_ids'],'context_evidence_ids':[]}]
    ids=wire['reading_context']['groups'][0]['evidence_ids']
    wire['reading_context']['groups'][0]['citation_views']=[
        {'support_evidence_ids':ids[1:],'context_evidence_ids':ids[:1]},
        {'support_evidence_ids':ids[:1],'context_evidence_ids':ids[1:]},
    ]
    selected=NarrativeSelectResult.from_dict(wire)
    view=compile_scoped_model_view(selected,max_claims=20)
    parts=view.to_binding()['task_parts']['t1']
    support=[key for key,sid in parts.items() if sid in view.plan.tasks[0].support_ids]
    context=[key for key,sid in parts.items() if sid in view.plan.tasks[0].context_ids]
    prompt=runtime.build_model_request(selected,reading_projection_version=V4)
    def decode(keys):
        reply=legacy.NarrativeModelResponse('offline','configured',prompt.prompt_version,
            json.dumps({'drafts_by_task':{'t1':[{'text':'The company reported progress.',
                'basis_parts':keys,'modality':'actual'}]}}).encode())
        return runtime.decode_model_draft(reply,selected=selected,reading_projection_version=V4)
    draft=decode(support)
    assert draft['claims'][0]['evidence_ids']==ids[1:]
    assert draft['claims'][0]['context_evidence_ids']==ids[:1]
    assert draft['claims'][0]['claim_type']=='company_statement'
    with pytest.raises(legacy.ModelCitationError):
        decode(context)


def test_verify_dependency_uses_same_registered_v4_prompt(monkeypatch):
    from company_wiki.automation import narrative_verify as verify
    result,selected,sent=_run()
    summary=NarrativeSummaryResult.from_dict(result.result)
    payload=SourceRevisionEventPayload.from_dict({
        'schema_version':'source-revision-event/2.0','source_ref':selected.source_ref.to_dict(),
        'expected_read_policy_sha256':selected.expected_read_policy_sha256,
        'source_metadata':selected.source_metadata.to_dict()})
    monkeypatch.setattr(verify,'parser_component',lambda *a,**k:(selected.parser.name,selected.parser.version))
    verify._validate_dependency_identity(payload,selected,summary,selector_version='0.9.0',
        reading_projection_version=V4)


def test_historical_typed_summary_and_frozen_identity_recovery_does_not_execute_model(monkeypatch):
    from company_wiki.automation import narrative_generation as generation
    from company_wiki.automation import narrative_batch as batch
    from company_wiki.automation import narrative_worker_factory as factory
    old=manifests('reading-model-input/3')
    old['summary_validation']['summary_handler_sha256']='0'*64
    binding_doc=batch._freeze_generations({'one':old})
    binding_doc['execution_versions']=old['execution_versions']
    binding=json.dumps(binding_doc)
    snapshot=factory._worker_binding_snapshot(binding)
    assert snapshot.reading_projections['one']=='reading-model-input/3'
    current=manifests('reading-model-input/3')
    preserved=generation.with_frozen_model_identity(current,old)
    assert preserved['summary_validation']==old['summary_validation']
    assert preserved['reading_model_boundary']==old['reading_model_boundary']
    with pytest.raises(legacy.ModelResponseError,match='SUMMARY_VALIDATION'):
        factory._validate_model_software(old)
    # This is stage-scoped identity restoration, not a new model invocation.
    # The real completed-job no-POST DAG test remains separate from this seam.
