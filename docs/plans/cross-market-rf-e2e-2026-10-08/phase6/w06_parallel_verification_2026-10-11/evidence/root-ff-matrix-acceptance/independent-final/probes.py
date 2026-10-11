"""Independent bounded FF matrix-tool review; products are read-only."""
from __future__ import annotations
import copy, hashlib, json, os, shutil, stat, sys, time, zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
BASE=OUT.parent
ROOT=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
TOOLS=ROOT/'tools/offline_contract_matrix'
SCRATCH=OUT/'_owned_scratch'
if SCRATCH.exists() or (OUT/'results.json').exists():
    raise RuntimeError('Never overwrite evidence; scratch must initially be absent')
freeze_path=BASE/'fix/freeze-manifest.json'
assert hashlib.sha256(freeze_path.read_bytes()).hexdigest()=='e098e5bca867a33802d8fcf6945af7370bb092aec13a4397be475244c43e1246'
freeze=json.loads(freeze_path.read_text(encoding='utf-8'))
def inventory():
    return [{'path':r['path'],'sha256':hashlib.sha256(b:=(ROOT/r['path']).read_bytes()).hexdigest(),'bytes':len(b),
             'matches':hashlib.sha256(b).hexdigest()==r['sha256'] and len(b)==r['bytes']} for r in freeze['files']]
before=inventory()
assert all(x['matches'] for x in before)
original_fail=BASE/'intake/independent-counterexamples.json'
original_sha=hashlib.sha256(original_fail.read_bytes()).hexdigest()
bundle=BASE/'fix/offline-evidence.zip'
bundle_before=hashlib.sha256(bundle.read_bytes()).hexdigest()
assert bundle_before==freeze['evidence']['offline_bundle_sha256']
with zipfile.ZipFile(bundle) as z:
    raw_report=z.read('matrix/attempt-1bb98380f75347e7b792e5966c11867e/report.json')
assert hashlib.sha256(raw_report).hexdigest()==freeze['evidence']['report_sha256']
actual_report=json.loads(raw_report)
sys.path.insert(0,str(TOOLS))
import run as runner, cli_main, matrix_cases as cases, matrix_outcome, oracle, runtime
from fixture_builder import CN, HK
from report import CaseResult
SCRATCH.mkdir()
rows=[];actual_control={};start=time.monotonic()
def add(name,expected,actual,ok):
    rows.append({'name':name,'expected':expected,'actual':actual,'pass':bool(ok)})
def fake_context(response):
    return SimpleNamespace(artifacts=SCRATCH,env=SimpleNamespace(calls_file=lambda _:SCRATCH/'unused-calls'),
                           write_state=lambda **kw:None,
                           run_ff=lambda *a,**kw:{'response':response,'exit_code':0,'request_ref':'req','response_ref':'resp'},
                           worker_ran=lambda _:False,fixture_requests=lambda _:0)
try:
    fake_ff,fake_cwp,fake_et=[SCRATCH/n for n in ('fake_ff','fake_cwp','fake_et')]
    for root in (fake_ff,fake_cwp,fake_et):(root/'config').mkdir(parents=True)
    key=fake_ff/'config/FMP_API_KEY.txt';key.write_text('synthetic-not-a-key',encoding='utf-8')
    with patch.object(runner,'sha256_file',side_effect=AssertionError('production-byte hash forbidden')):
        g=runner.ProductionGuard(fake_ff,fake_cwp,fake_et)
        assert g.unchanged(g.snapshot())
    add('FFI-SECRET-HASH','metadata only',g.before[str(key)],'sha256' not in g.before[str(key)])
    ctx=object.__new__(runner.Context);ctx.cwp_root=fake_cwp;ctx.et_root=fake_et;ctx.scratch=SCRATCH/'env'
    ctx.env=SimpleNamespace(proxy_state=SCRATCH/'proxy')
    with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'synthetic-marker','OPENAI_API_KEY':'synthetic-marker',
                    'API_BASE_URL':'https://synthetic.invalid','FMP_API_KEY_FILE':'synthetic-file','UNRELATED_SETTING':'marker'},clear=True):
        env=ctx.child_env()
    leaked=[x for x in ('DEEPSEEK_API_KEY','OPENAI_API_KEY','API_BASE_URL','FMP_API_KEY_FILE','UNRELATED_SETTING') if x in env]
    add('FFI-ENV-LEAK','no unrelated host values',{'leaked_names':leaked,'synthetic_fmp':env.get('FMP_API_KEY')==runner.FAKE_FMP_KEY,
             'home_owned':Path(env['HOME']).is_relative_to(ctx.scratch)},not leaked and env.get('FMP_API_KEY')==runner.FAKE_FMP_KEY)
    for name,fn,response,wanted in [
        ('FFI-WRONG-QUARTER',cases.case_call_wrong_quarter,{'transcript':{'status':'downloaded','fiscal_quarter':2,'source_ref':{'source_id':'fake'}}},False),
        ('FFI-CUTOFF-UNRELATED-ERROR',cases.case_call_past_cutoff,{'transcript':{'status':'upstream_error','reason':'arbitrary_import_failure'}},False),
        ('FFI-UNKNOWN-ZERO',cases.case_err_unknown_usage,{'transcript':{'status':'upstream_error','reason':'provider_loss','provider_requests':0,'provider_usage_complete':False}},False),
        ('CONTROL-QUARTER-REJECTED',cases.case_call_wrong_quarter,{'transcript':{'status':'provider_unavailable','reason':'quarter_mismatch'}},True),
        ('CONTROL-CUTOFF-EXPLICIT',cases.case_call_past_cutoff,{'transcript':{'status':'provider_unavailable','reason':'after_as_of'}},True),
        ('CONTROL-UNKNOWN-NULL',cases.case_err_unknown_usage,{'transcript':{'status':'upstream_error','reason':'worker_loss','provider_requests':None,'provider_usage_complete':False}},True)]:
        r=fn(fake_context(response)).to_dict()
        add(name,'PASS' if wanted else 'not PASS',r,(r['result']=='PASS')==wanted)
    response={'status':'source_candidate','filing':{'resolution_outcome':'downloaded_new','download_events':0}}
    r=cases.case_fin_fetch(fake_context(response),HK,'annual_report',2026,'negative').to_dict()
    add('FFI-MISSING-REUSE','not PASS',r,r['result']!='PASS')
    for name,payload,vector in [
        ('FFI-EMPTY-UNBOUND-ORACLE',{'cases':[],'restore':{'restored':True},'code_binding':{'verified':False}},'unbound_code'),
        ('FFI-ORACLE-NULL-AS-ZERO',{'cases':[{'id':'reuse','expected':{'run_twice':True},'provider_counters':{'run2_fixture_requests':None}}],'restore':{'restored':True}},'second_run_still_downloads'),
        ('FFI-ORACLE-MISSING-REGISTRY',{'runner':'offline','cases':[{'id':'any','result':'FAIL'}],'required_cases':[],
             'restore':{'restored':True},'code_binding':{'verified':True},'scope':{'batch_elapsed_seconds':1}},'coverage_gap'),
        ('FFI-ORACLE-BATCH-DEADLINE',{'runner':'offline','cases':[{'id':'any','result':'FAIL'}],'required_cases':['any'],
             'restore':{'restored':True},'code_binding':{'verified':True},'scope':{'batch_elapsed_seconds':220}},'deadline_exceeded')]:
        findings=[f.to_dict() for f in oracle.audit(payload)]
        add(name,vector,findings,any(f['vector']==vector for f in findings))
    with patch.object(runtime.time,'monotonic',side_effect=[0,1,1,2,2,30.1]):
        d=runtime.Deadline(30);first=d.case(30);second=first.case(30)
        try:second.remaining();expired=False
        except runtime.DeadlineExceeded:expired=True
    add('CONTROL-ABSOLUTE-DEADLINE','deadline not reset',{'end':second.end,'expired':expired},second.end==30 and expired)
    owned=SCRATCH/'old_owned';out=SCRATCH/'old_out';(owned/'scratch').mkdir(parents=True);out.mkdir()
    oldfile=owned/'scratch/old.txt';oldfile.write_bytes(b'pre-existing baseline')
    sentinel=owned/runner.SENTINEL_NAME;sentinel.write_bytes(b'pre-existing sentinel')
    report=out/'report.json';report.write_bytes(b'pre-existing report')
    attempt=runtime.OwnedAttempt.create(owned,out)
    (attempt.scratch/'new.txt').write_bytes(b'new only')
    restore=attempt.cleanup()
    preserved=oldfile.read_bytes()==b'pre-existing baseline' and sentinel.read_bytes()==b'pre-existing sentinel' and report.read_bytes()==b'pre-existing report'
    add('FFI-CLI-BASELINE-DELETION','preexisting bytes preserved',restore,preserved and restore['restored'])
    class NoopContext:
        def __init__(self,**kw):self.__dict__.update(kw)
        def child_env(self):return {}
    noop=CaseResult(id='control',title='binding scaffold',declared_layer='ff-only',result='PASS')
    with patch.object(cli_main,'Context',NoopContext),patch.object(cli_main,'seed_all',lambda _:None),\
         patch.object(cli_main,'_verify_binding',lambda *a,**kw:{'verified':False}),\
         patch.object(cli_main,'_case_registry',lambda:[('control',lambda _:noop)]):
        rc=cli_main.main(['--cwp-project',str(fake_cwp),'--et-project',str(fake_et),'--owned-root',str(owned),'--out-root',str(out)])
    add('FFI-CLI-UNBOUND-BUDGET','invalid binding nonzero and no baseline loss',{'exit_code':rc,'oldfile_present':oldfile.exists()},rc!=0 and oldfile.read_bytes()==b'pre-existing baseline' and sentinel.read_bytes()==b'pre-existing sentinel' and report.read_bytes()==b'pre-existing report')
    registry_ids=[cid for cid,_ in cli_main._case_registry()]
    full_findings=[f.to_dict() for f in oracle.audit(actual_report)]
    add('CONTROL-ACTUAL-REQUIRED-REGISTRY','41 actual cases match authoritative runtime registry',
        {'actual':len(actual_report['cases']),'registry':len(registry_ids),'findings':full_findings},
        len(registry_ids)==41 and set(registry_ids)==set(actual_report['required_cases'])=={c['id'] for c in actual_report['cases']} and not any(f['vector']=='coverage_gap' for f in full_findings))
    reduced=copy.deepcopy(actual_report)
    reduced['cases']=[c for c in reduced['cases'] if c['result']=='PASS']
    reduced['required_cases']=[c['id'] for c in reduced['cases']]
    reduced_findings=[f.to_dict() for f in oracle.audit(reduced)]
    add('NEW-FFI-SELF-DECLARED-SUBSET-COVERAGE','omitting 22 required cases must be rejected',
        {'retained_cases':len(reduced['cases']),'omitted':sorted(set(registry_ids)-set(reduced['required_cases'])),
         'oracle_findings':reduced_findings,'oracle_pass':not reduced_findings},bool(reduced_findings))
    (OUT/'original-41-report-copy.json').write_bytes(raw_report)
    (OUT/'omitted-required-22-cases-counterexample.json').write_text(json.dumps(reduced,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    bad=copy.deepcopy(actual_report);bad['source_proofs']={'proofs':{}}
    f=[x.to_dict() for x in oracle.audit(bad)]
    add('CONTROL-MISSING-FRESH-READER-PROOF','cannot PASS accepted refs without byte proof',f,any(x['vector']=='source_bytes_not_verified' for x in f))
    bad=copy.deepcopy(actual_report)
    accepted=next(c for c in bad['cases'] if c['result']=='PASS' and c.get('actual',{}).get('runs'))
    accepted['actual']['runs'][0]['response']['review_spurious_field']=True
    f=[x.to_dict() for x in oracle.audit(bad)]
    add('CONTROL-BOUND-RESPONSE-MUTATION','self-claim must match original response bytes',f,any(x['vector']=='invalid_bound_evidence' for x in f))
    # One necessary positive public path: the already passing warm CN2024 case.
    # It does not change or replace missing US2025 primary / intended ET cases.
    public_scratch=SCRATCH/'public_control';public_out=SCRATCH/'public_evidence'
    public_scratch.mkdir();public_out.mkdir()
    cwp=Path('C:/Users/郑曾波/Projects/company-wiki')
    et=Path('C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts')
    context=runner.Context(ff_root=ROOT,cwp_root=cwp,et_root=et,scratch=public_scratch,out_root=public_out,deadline=runtime.Deadline(25))
    warm=context.warm_seed(CN,'annual_report',2024,'FY')
    actual_control['warm']=warm
    assert warm['response']['outcome']=='downloaded_new'
    context.begin_case()
    r=cases.case_fin_local_hit(context,CN,'annual_report',2024,'FY','independent_cn2024').to_dict()
    actual_control['case']=r
    assert r['result']=='PASS'
    actual_control['proofs']=cli_main._fresh_proofs(context)
    proofs=actual_control['proofs']['proofs']
    actual_control['guard_events']=runtime.guard_events(public_scratch)
    assert len(proofs)==1 and all(p['verified'] and p['source_versions']==1 and p['physical_originals']==1 for p in proofs.values())
    assert not any(e['op'] in {'network_denied','translation_attempt'} for e in actual_control['guard_events'])
    add('CONTROL-ACTUAL-FF-CWP-READER','warm2024 exact original reuse + real fresh byte reader',
        {'case':r,'proofs':actual_control['proofs'],'guard_boots':len(actual_control['guard_events']),
         'scope':'real FF public CLI + real CWP ensure/import/fresh reader; supplier fixture only; no ET retrieval'},True)
finally:
    after=inventory()
    assert SCRATCH.resolve().parent==OUT.resolve() and SCRATCH.name=='_owned_scratch'
    for p in SCRATCH.rglob('*'):
        if p.is_file():p.chmod(stat.S_IREAD|stat.S_IWRITE)
    shutil.rmtree(SCRATCH)
    result={'schema':'w06-independent-final-tool-review/1','before':before,'after':after,'freeze_unchanged':before==after,
            'original_fail_unchanged':hashlib.sha256(original_fail.read_bytes()).hexdigest()==original_sha,
            'original_bundle_unchanged':hashlib.sha256(bundle.read_bytes()).hexdigest()==bundle_before,
            'probes':rows,'public_control':actual_control,'scratch_initial_exists':False,'scratch_final_exists':SCRATCH.exists(),
            'seconds':round(time.monotonic()-start,3),'provider_network_calls':0,'llm_calls':0,'fees_usd':0,
            'scope':'Pure tooling plus one warm2024 FF+CWP fixture control; no full matrix, real supplier, translation, or ET completeness claim'}
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'probes':len(rows),'failed':[r['name'] for r in rows if not r['pass']],
                      'freeze_unchanged':before==after,'scratch_absent':not SCRATCH.exists()},ensure_ascii=False))
