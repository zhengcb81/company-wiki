"""Independent adversarial W02 probes, no production state/network/credentials."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from copy import deepcopy

import pytest

FF = Path(os.environ['W02_FF_CODE_ROOT'])
RF = Path(os.environ['W02_RF_CODE_ROOT'])
CWP = Path(os.environ['CWP_V2_CODE_ROOT'])
sys.path[:0] = [str(FF/'scripts'), str(RF/'scripts'), str(CWP/'src')]
import fetch_filing as ff
from ff_source_failure import source_request_id
from ff_v2_envelope import error_envelope, success_envelope
from filing_contracts import FilingFetchError, _validate_companion_request
from filing_upstream_cause import failure_observation
from contracts.source_clock import qualify_source_information, source_information_eligibility, SourceClockError
from company_wiki.source_catalog.resolver import SourceRequest


def request(provider='fmp'):
    return {'schema_version':'2.0', 'company_query':'Review Harbor Ltd', 'market':'HK',
        'document_kind':'annual_report', 'fiscal_year':2025, 'fiscal_period':'FY',
        'as_of_date':'2026-10-21', 'filing_intent':'reuse_only',
        'companion_transcript':{'intent':'reuse_only', 'fiscal_year':2025,
            'fiscal_quarter':4, 'provider':provider}}


def source_request():
    return {'entity':'Review Harbor Ltd', 'market':'HK', 'security_id':'09888',
        'document_kind':'annual_report', 'fiscal_year':2025, 'fiscal_period':'FY',
        'as_of_date':'2026-10-21'}


def operation():
    return {'operation_schema_version':'1.0', 'operation':'ensure', 'status':'unavailable',
        'request_id':SourceRequest(**source_request()).request_id,
        'outcome':None, 'download_events':0, 'policy_hash':None, 'source_ref':None,
        'candidate':None, 'gap_plan':None,
        'local_preparation':{'status':'unavailable', 'reason':'local_candidate_limit',
            'blocks_download':True, 'causes':['local_discovery_entry_limit']}}


def child_bytes(body, code=2):
    return [sys.executable, '-S', '-c', 'import sys;sys.stdout.buffer.write('+repr(body)+');sys.exit('+str(code)+')']


@pytest.mark.parametrize('code',[1,2])
def test_real_child_exit_preserves_business_failure_and_native_request_id(tmp_path, code):
    source = source_request()
    assert source_request_id(source) == SourceRequest(**source).request_id
    with pytest.raises(FilingFetchError) as caught:
        ff._run_company_wiki_json(command=child_bytes(json.dumps(operation()).encode(),code),
            root=tmp_path, timeout_seconds=5, action='ensure', source_request=source)
    assert caught.value.producer_exit_code == code
    assert caught.value.upstream_cause['code'] == 'local_candidate_limit'
    assert caught.value.upstream_cause['provider_started'] is False


@pytest.mark.parametrize('mutation',['schema','request','action','field','path','truncated','html','array','unexpected_exit'])
def test_actual_child_malformed_failure_does_not_pass_as_named_local_success(tmp_path,mutation):
    body=operation(); code=2
    if mutation=='schema': body['operation_schema_version']='999'
    if mutation=='request': body['request_id']='urn:company-wiki:source-request:sha256:'+'0'*64
    if mutation=='action': body['operation']='resolve'
    if mutation=='field': body['unknown']={'business':'x'}
    if mutation=='path': body['local_preparation']['path']='hidden/original.pdf'
    if mutation=='unexpected_exit': code=7
    wire=json.dumps(body).encode()
    if mutation=='truncated': wire=wire[:-3]
    if mutation=='html': wire=b'<html>not an envelope</html>'
    if mutation=='array': wire=b'[]'
    with pytest.raises(FilingFetchError) as caught:
        ff._run_company_wiki_json(command=child_bytes(wire,code),root=tmp_path,
            timeout_seconds=5,action='ensure',source_request=source_request())
    assert caught.value.producer_exit_code == code
    assert caught.value.upstream_cause['code']=='invalid_producer_schema'


def test_companion_unresolved_absent_and_requested_are_distinct():
    current=request()
    absent=deepcopy(current); absent.pop('companion_transcript')
    unresolved=deepcopy(current); unresolved['companion_transcript'].pop('fiscal_quarter')
    for req, expected in [(current,'not_run'),(absent,'not_requested'),(unresolved,'period_unresolved')]:
        native=error_envelope('upstream_error','company-wiki ensure unavailable',retryable=False,
            request=req,stats={'calls':2,'downloads':0},producer_exit_code=2)
        observed=failure_observation(native)
        assert observed['companion_observation']['status']==expected
        assert observed['filing_fetch_result']==native
        assert observed['producer_exit_code']==2
    assert native['downloads']==0


def test_non_fmp_reuse_provider_intent_is_not_discarded_by_rf():
    current=request(provider='company_ir')
    _validate_companion_request(current['companion_transcript'])  # public FF owner accepts this intent
    native=error_envelope('upstream_error','company-wiki ensure unavailable',retryable=False,
        request=current,stats={'calls':2,'downloads':0},producer_exit_code=2)
    observed=failure_observation(native)
    assert observed.get('companion_observation')==native['transcript']
    assert observed.get('filing_fetch_result')==native


def native_gap():
    return success_envelope(request(),{'status':'gap','gap_plan':{'schema_version':'1.0','gap_hash':'e'*64},
        'resolution':{'reason':'metadata_only_gap_plan'}},{'status':'not_requested'},
        {'calls':3,'downloads':0})


def test_complete_native_gap_sidecar_remains_available():
    native=native_gap()
    assert native['transcript']['status']=='not_applicable'
    observed=failure_observation(native)
    assert observed.get('filing_fetch_result')==native
    assert observed['companion_observation']==native['transcript']


def run_rf_with_payload(root,payload,code):
    fake=root/'ff'; (fake/'scripts').mkdir(parents=True)
    (fake/'scripts/fetch_filing.py').write_text('import json,sys; print(json.dumps('+repr(payload)+')); sys.exit('+str(code)+')',encoding='utf-8')
    config=root/'catalog.yaml'; config.write_text('{}',encoding='utf-8')
    result=subprocess.run([sys.executable,str(RF/'scripts/source_preparation.py'),'--result-envelope',
        '--company-wiki-catalog-config',str(config),'--filing-fetch-root',str(fake),
        '--timeout-seconds','10'],input=json.dumps(request()),encoding='utf-8',text=True,
        capture_output=True,timeout=30,env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
    assert result.returncode==3,(result.stdout,result.stderr)
    return json.loads(result.stderr)


def test_actual_rf_cli_preserves_nonexception_native_gap(tmp_path):
    native=native_gap()
    error=run_rf_with_payload(tmp_path,native,0)
    assert error.get('filing_fetch_result')==native
    assert error['companion_observation']['status']=='not_applicable'


@pytest.mark.parametrize('change',['known_future','wrong_sha','past_asof','bare_first_seen'])
def test_current_verified_open_cannot_override_source_clock(change):
    proof={'schema_version':'source-availability-evidence/1','source_sha256':'a'*64,
        'available_by':'2026-10-21','basis':'current_verified_open',
        'evidence_ref':'source-verified-open:sha256:fixture','locator':'/read_at + /content_sha256'}
    from datetime import date
    kwargs={'source_sha256':'a'*64,'published_date':None,'as_of':date(2026,10,21),'availability_evidence':proof}
    if change=='known_future': kwargs['published_date']='2026-10-22'
    if change=='wrong_sha': kwargs['source_sha256']='b'*64
    if change=='past_asof': kwargs['as_of']=date(2026,10,20)
    if change=='bare_first_seen': kwargs['availability_evidence']={'first_seen_at':'2026-10-21'}
    with pytest.raises(SourceClockError): qualify_source_information(**kwargs)


def test_current_open_dto_without_public_receipt_does_not_prove_eligibility():
    from datetime import date
    proof={'schema_version':'source-availability-evidence/1','source_sha256':'a'*64,
        'available_by':'2026-10-21','basis':'current_verified_open',
        'evidence_ref':'source-verified-open:sha256:fixture','locator':'/read_at + /content_sha256'}
    with pytest.raises(SourceClockError,match='lineage'):
        source_information_eligibility({'published_date':None,'capture':{'snapshot_sha256':'a'*64},
            'availability_evidence':proof},date(2026,10,21))


def test_actual_cwp_ff_rf_cli_cold_catalog_is_named_and_zero_provider(tmp_path):
    wiki=tmp_path/'wiki'; (wiki/'companies').mkdir(parents=True); (wiki/'config').mkdir()
    (wiki/'config/source_catalog.yaml').write_text('schema_version: "1.0"\ncatalog_dir: "${PROJECT_ROOT}/.source_catalog"\nroots:\n  - root_id: company_raw\n    kind: company_raw\n    path: "${PROJECT_ROOT}/companies"\n    priority: 10\n',encoding='utf-8')
    master=wiki/'.source_catalog/security_master'; master.mkdir(parents=True)
    record={'schema_version':'1.0','canonical_name':'Review Harbor Ltd','market':'HK','exchange':'HKEX',
        'ticker':'09888','security_id':'09888','aliases':['REVIEW HARBOR'],'identifiers':{'org_id':'review-hk'},
        'active':True,'source_name':'hkexnews','source_record_id':'review-hk','source_url':'https://www.hkex.com.hk/'}
    (master/'hk.json').write_text(json.dumps({'schema_version':'1.0','market':'HK','retrieved_at':'2026-10-21T00:00:00Z',
        'sources':[record['source_url']],'record_count':1,'records':[record]}),encoding='utf-8')
    connection=wiki/'connection.json'; connection.write_text(json.dumps({'schema_version':'1.0','company_wiki_root':str(wiki)}),encoding='utf-8')
    current=request(); current['company_query']='09888'
    result=subprocess.run([sys.executable,str(RF/'scripts/source_preparation.py'),'--result-envelope',
        '--company-wiki-catalog-config',str(wiki/'config/source_catalog.yaml'),'--company-wiki-config',str(connection),
        '--filing-fetch-root',str(FF),'--timeout-seconds','30'],input=json.dumps(current),text=True,
        encoding='utf-8',capture_output=True,timeout=50,
        env={**os.environ,'PYTHONPATH':str(CWP/'src'),'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'})
    assert result.returncode==3,(result.stdout,result.stderr)
    payload=json.loads(result.stderr)
    assert payload['upstream_cause']['code'] in {'catalog_unavailable','reader_unavailable'}
    assert payload['upstream_cause']['provider_started'] is False
    assert payload['producer_exit_code']==2
    assert payload['companion_observation']['fiscal_year']==2025
    assert payload['companion_observation']['fiscal_quarter']==4
    assert payload['filing_fetch_result']['transcript']==payload['companion_observation']
    assert not list((wiki/'companies').rglob('*'))
    assert not (wiki/'.source_catalog/acquisition_attempts.jsonl').exists()


@pytest.mark.parametrize('failure_code',['adapter_timeout','budget_exceeded'])
def test_unknown_acquisition_usage_stays_unknown_separately_from_zero_companion_dispatch(tmp_path,failure_code):
    payload=operation()
    payload.pop('local_preparation')
    payload['acquisition_failure']={'schema_version':'acquisition-failure/1','code':failure_code,
        'retryable':True,'provider_started':None,'usage_complete':None,'acquisition_usage':None,'usage_scope':'operation'}
    with pytest.raises(FilingFetchError) as caught:
        ff._run_company_wiki_json(command=child_bytes(json.dumps(payload).encode()),root=tmp_path,
            timeout_seconds=5,action='ensure',source_request=source_request())
    exc=caught.value
    assert exc.upstream_cause['provider_started'] is None
    assert exc.upstream_cause['usage_complete'] is None
    native=error_envelope(exc.code,str(exc),retryable=exc.retryable,stats={'calls':2,'downloads':0},
        request=request(),upstream_cause=exc.upstream_cause,acquisition_failure=exc.acquisition_failure,
        producer_exit_code=exc.producer_exit_code)
    observed=failure_observation(native)
    assert observed['acquisition_failure']['acquisition_usage'] is None
    assert observed['acquisition_failure']['code']==failure_code
    assert observed['upstream_cause']['provider_started'] is None
    assert observed['upstream_cause']['usage_complete'] is None
    assert observed['filing_fetch_result']==native
    assert observed['companion_observation']['provider_started'] is False
    assert observed['companion_observation']['provider_requests']==0


@pytest.mark.parametrize('failure',['stdout_limit','timeout'])
def test_bounded_transport_failure_is_not_reclassified_as_valid_business_json(tmp_path,monkeypatch,failure):
    import ff_process_transport as transport
    actual=transport.run_bounded_json
    if failure=='stdout_limit':
        def narrow(command,**kwargs):
            return actual(command,**kwargs,stdout_cap_bytes=128)
        monkeypatch.setattr(ff,'_run_bounded_json',narrow)
        command=child_bytes(json.dumps(operation()).encode())
        timeout=5
    else:
        command=[sys.executable,'-S','-c','import time;time.sleep(5)']
        timeout=0.1
    before=time.monotonic()
    with pytest.raises(FilingFetchError) as caught:
        ff._run_company_wiki_json(command=command,root=tmp_path,timeout_seconds=timeout,
            action='ensure',source_request=source_request())
    assert caught.value.upstream_cause['code']==('producer_output_exceeded' if failure=='stdout_limit' else 'producer_deadline_exceeded')
    assert caught.value.upstream_cause['provider_started'] is None
    assert caught.value.upstream_cause['usage_complete'] is None
    assert time.monotonic()-before<6


def test_transcript_failure_does_not_replace_valid_filing_source_candidate():
    digest='a'*64
    ref={'schema_version':'2.0','document_id':'doc-review','source_id':'urn:company-wiki:source:sha256:'+digest,
         'content_sha256':digest,'byte_size':37,'mime_type':'application/pdf'}
    handle={'source_ref':ref,'document_kind':'annual_report','fiscal_year':2025,'fiscal_period':'FY',
            'resolution_outcome':'reused_existing','download_events':0}
    et_failure={'status':'upstream_error','reason':'transcript_acquisition_failed:TimeoutError','retryable':True,
                'provider_started':True,'provider_requests':1,'provider_response_bytes':None,'provider_usage_complete':False}
    native=success_envelope(request(),handle,et_failure,{'calls':3,'downloads':0})
    assert native['status']=='source_candidate'
    assert native['filing']['source_ref']==ref
    assert native['transcript']['status']=='upstream_error'
    assert native['transcript']['provider_started'] is True
    assert native['transcript']['provider_usage_complete'] is False
    assert native['transcript']['provider_response_bytes'] is None


@pytest.mark.parametrize('variant',[
    {'entity':'Independent A','market':'cn','security_id':'688955','provider':'CNINFO','document_kind':'annual_report','fiscal_year':2025},
    {'entity':'Independent B','market':'US','security_id':'B','document_kind':'annual_report','mode':'LATEST_AS_OF'},
    {'entity':'Independent C','market':'hk','security_id':'09955','document_kind':'semi_annual_report','fiscal_year':2026,'fiscal_period':'H1'},
])
def test_request_fingerprint_matches_actual_owner_across_markets(variant):
    value={**variant,'as_of_date':'2026-10-21'}
    assert source_request_id(value)==SourceRequest(**value).request_id


@pytest.mark.parametrize('mutation',['bool_event_count','download_outcome_with_local_block'])
def test_nonzero_failure_must_not_invent_zero_provider_from_inconsistent_accounting(tmp_path,mutation):
    payload=operation()
    if mutation=='bool_event_count': payload['download_events']=False
    else: payload['outcome']='downloaded_new'
    with pytest.raises(FilingFetchError) as caught:
        ff._run_company_wiki_json(command=child_bytes(json.dumps(payload).encode()),root=tmp_path,
            timeout_seconds=5,action='ensure',source_request=source_request())
    assert caught.value.upstream_cause['code']=='invalid_producer_schema'
    assert caught.value.upstream_cause['provider_started'] is not False


@pytest.mark.parametrize('reason',['local_document_kind_unresolved','local_original_unreadable',
    'primary_issuer_conflict','budget_exceeded'])
def test_w01_final_local_reasons_cross_existing_contract_without_another_identity_check(tmp_path,reason):
    payload=operation()
    payload['local_preparation']['reason']=reason
    with pytest.raises(FilingFetchError) as caught:
        ff._run_company_wiki_json(command=child_bytes(json.dumps(payload).encode()),root=tmp_path,
            timeout_seconds=5,action='ensure',source_request=source_request())
    error=caught.value
    native=error_envelope(error.code,str(error),retryable=error.retryable,request=request(),
        stats={'calls':2,'downloads':0},upstream_cause=error.upstream_cause,
        producer_exit_code=error.producer_exit_code)
    observed=failure_observation(native)
    assert observed['upstream_cause']['code']==reason
    assert observed['upstream_cause']['provider_started'] is False
    assert observed['filing_fetch_result']==native
