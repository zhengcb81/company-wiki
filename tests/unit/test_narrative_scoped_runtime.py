"""Explicit v4 runtime; canonical bindings are not semantic truth proofs."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import socket

import pytest

from company_wiki.automation import narrative_model as legacy
from company_wiki.automation import narrative_model_runtime as runtime
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import NarrativeContractError
from company_wiki.source_contract import EvidenceSpan
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from support.narrative_model_request_fixture import selection
from unit.test_narrative_reading_transport import with_reading
from unit.test_narrative_source_owned_model_boundary import official_reading, http_port

V4 = 'reading-model-input/4'


@pytest.fixture(autouse=True)
def no_supplier_and_legacy_bytes_unchanged(monkeypatch):
    path = Path(legacy.__file__)
    before = path.read_bytes()
    def forbid(*args, **kwargs):
        raise AssertionError('pure scoped runtime tests must not call a supplier')
    monkeypatch.setattr(socket, 'create_connection', forbid)
    monkeypatch.setattr(socket.socket, 'connect', forbid)
    yield
    assert path.read_bytes() == before


def request(selected=None):
    return runtime.build_model_request(selected or with_reading(), reading_projection_version=V4)


def clause(text='公司新产品已完成海外客户认证。', parts=None, modality='actual', **extra):
    return {'text':text, 'basis_parts':parts or ['p1'], 'modality':modality, **extra}


def decode(tasks, selected=None):
    selected = selected or with_reading()
    reply = legacy.NarrativeModelResponse('offline','configured',request(selected).prompt_version,
        canonical_json({'drafts_by_task':tasks}).encode())
    return runtime.decode_model_draft(reply, selected=selected, reading_projection_version=V4)


def test_v4_boundary_and_request_are_finite_explicit_and_http_compatible():
    selected=with_reading()
    actual=request(selected)
    assert isinstance(actual,legacy.NarrativeModelRequest)
    data=json.loads(actual.data_json)
    assert data['schema_version']=='narrative-model-request/5'
    assert data['material']['schema_version']=='source-scoped-model-view/1'
    assert data['material']['available_task_count']==2
    assert set(data['response_schema']['properties'])=={'drafts_by_task'}
    body=json.loads(http_port().request_bytes(actual))
    user=json.loads(body['messages'][1]['content'])
    assert user['output_plan']['configured_output_tokens']==8192
    assert isinstance(actual.with_output_budget(1024),legacy.NarrativeModelRequest)
    assert actual.with_output_budget(1024).with_output_budget(1024)==actual.with_output_budget(1024)


@pytest.mark.parametrize('selected',[with_reading(),official_reading()],ids=['raw','official'])
def test_v4_reconstructs_program_identity_and_task_order_not_response_key_order(selected):
    view=compile_scoped_model_view(selected,max_claims=20)
    keys=[task.key for task in view.plan.tasks]
    out=decode({key:[clause()] for key in reversed(keys)},selected)
    assert [row['claim_id'] for row in out['claims']]==[key+'-1' for key in keys]
    assert out['language']==selected.source_metadata.language
    if selected.subject.kind=='official_json':
        assert out['subject_id']==selected.subject.item_key
    else:
        assert out['source_id']==selected.source_ref.source_id
    for row, task in zip(out['claims'],view.plan.tasks,strict=True):
        assert row['evidence_ids']==list(task.support_ids)


def test_global_cap_is_checked_before_invalid_clause_recovery():
    with pytest.raises(NarrativeContractError,match='forty'):
        decode({'t1':[clause(parts=['missing']) for _ in range(21)],
                't2':[clause() for _ in range(20)]})


def test_bad_clause_is_discarded_whole_without_citation_repair_or_extra_call():
    out=decode({'t1':[clause(parts=['p1','no-such-part']),clause()]})
    assert [row['claim_id'] for row in out['claims']]==['t1-2']
    assert out['status']=='needs_review'


def test_explicit_translation_is_global_contradiction_not_recovered_bad_clause():
    with pytest.raises(legacy.ModelResponseError,match='untranslated'):
        decode({'t1':[clause(translate=True),clause()]})


@pytest.mark.parametrize('parts',[['p1','p1'],['t2:p1'],['p999'],[], 'p1'])
def test_illegal_basis_is_not_repaired(parts):
    row=clause()
    row['basis_parts']=parts
    with pytest.raises((legacy.ModelResponseError,NarrativeContractError)):
        decode({'t1':[row]})


@pytest.mark.parametrize('extra',[{'claim_id':'model-chosen'}, {'claim_type':'company_statement'},
                                   {'source_id':'model-source'}, {'evidence_ids':['e1']}])
def test_model_cannot_override_program_claim_metadata(extra):
    with pytest.raises((legacy.ModelResponseError,NarrativeContractError)):
        decode({'t1':[clause(**extra)]})


def test_unknown_task_and_duplicate_json_keys_fail_without_global_alias_fallback():
    with pytest.raises(legacy.ModelResponseError):
        decode({'t99':[clause()]})
    actual=request()
    reply=legacy.NarrativeModelResponse('offline','configured',actual.prompt_version,
        b'{"drafts_by_task":{"t1":[],"t1":[]}}')
    with pytest.raises(legacy.ModelResponseError,match='duplicate JSON'):
        runtime.decode_model_draft(reply,selected=with_reading(),reading_projection_version=V4)


def test_correct_task_and_valid_basis_do_not_claim_semantic_quality():
    out=decode({'t1':[clause(text='An unrelated product generated USD 99 billion in 2035.')]})
    assert out['claims'][0]['text'].startswith('An unrelated')
    bound=compile_scoped_model_view(with_reading(),max_claims=20).resolve_basis('t1',['p1'])
    assert bound.semantic_status=='not_evaluated'


@pytest.mark.parametrize('version',[None,'reading-model-input/1','reading-model-input/2','reading-model-input/3'])
def test_old_runtime_calls_delegate_to_actual_legacy_implementation(version):
    selected=with_reading()
    old=legacy.NarrativeModelRequest.from_selection(selected,reading_projection_version=version)
    actual=runtime.build_model_request(selected,reading_projection_version=version)
    assert type(actual) is legacy.NarrativeModelRequest
    assert asdict(actual)==asdict(old)
    assert http_port().request_bytes(actual)==http_port().request_bytes(old)
    assert runtime.reading_model_boundary_identity(version)==legacy.reading_model_boundary_identity(version)


@pytest.mark.parametrize('version',[True,'reading-model-input/99',[],{}])
def test_unknown_projection_does_not_fall_back(version):
    with pytest.raises(legacy.ModelResponseError,match='PROJECTION'):
        runtime.build_model_request(with_reading(),reading_projection_version=version)


def test_role_owner_program_type_and_question_modality_are_shared():
    from company_wiki.source_catalog.narrative_evidence import summary_claim_type_for_roles
    assert summary_claim_type_for_roles(('company_filing','management'))=='company_statement'
    assert summary_claim_type_for_roles(('analyst','investor_question'))=='analyst_question'
    assert summary_claim_type_for_roles(('company_filing','analyst'))=='uncertain'
    assert summary_claim_type_for_roles(('unknown',))=='uncertain'
    selected=with_reading(selection(1,role='analyst'))
    with pytest.raises((legacy.ModelResponseError,NarrativeContractError)):
        decode({'t1':[clause(modality='actual')]},selected)
    assert decode({'t1':[clause(modality='question')]},selected)['claims'][0]['claim_type']=='analyst_question'


@pytest.mark.parametrize('roles,modality,expected',[
    (('company_filing','management'),'actual','company_statement'),
    (('analyst','investor_question'),'question','analyst_question'),
    (('company_filing','analyst'),'actual','uncertain'),
    (('management','unknown'),'actual','uncertain'),
])
def test_actual_decoder_infers_type_from_complete_native_role_set(roles,modality,expected):
    original=selection(2)
    # Role is parser output: recreate native IDs/hash before building groups.
    spans=tuple(EvidenceSpan.create(source_id=span.source_id, coordinates=span.coordinates,
        raw_text=span.raw_text, structured_value={**span.structured_value,'source_role':role},
        parser_name=span.parser_name,parser_version=span.parser_version,
        parse_status=span.parse_status,quality_flags=span.quality_flags)
        for span,role in zip(original.evidence_spans,roles,strict=True))
    selected=with_reading(replace(original,evidence_spans=spans))
    output=decode({'t1':[clause(modality=modality)]},selected)
    assert output['claims'][0]['claim_type']==expected
    assert output['claims'][0]['evidence_ids']==[span.span_id for span in selected.evidence_spans]
