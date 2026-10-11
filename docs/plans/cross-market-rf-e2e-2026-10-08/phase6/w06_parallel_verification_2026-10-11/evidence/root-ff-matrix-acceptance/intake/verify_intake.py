from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
FF = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix')
CANONICAL = Path('C:/Users/郑曾波/Projects/filing-fetch')
TOOLS = FF / 'tools/offline_contract_matrix'

def sha(path):
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

def git(root, *args):
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, encoding='utf-8', timeout=20)
    return {'command': ['git', '-C', str(root), *args], 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}

def inventory():
    handoff = json.loads((FF/'docs/handoffs/w06-ff-matrix/handoff.json').read_text(encoding='utf-8-sig'))
    manifest = json.loads((FF/'docs/handoffs/w06-ff-matrix/manifest.json').read_text(encoding='utf-8-sig'))
    rows = []
    def check(group, item):
        rel = item['path']
        path = FF / rel
        actual = sha(path) if path.is_file() else None
        rows.append({'group': group, 'path': rel, 'expected': item, 'actual': actual,
                     'sha_match': actual is not None and actual['sha256'] == item.get('sha256'),
                     'bytes_match': actual is not None and (item.get('bytes') is None or actual['bytes'] == item['bytes'])})
    for group in ('changed_files', 'input_evidence'):
        for row in handoff[group]:
            check(group,row)
    entries = manifest if isinstance(manifest,list) else manifest.get('files',manifest.get('entries',[]))
    if isinstance(entries,dict):
        entries = [{'path':p,**v} for p,v in entries.items()]
    for row in entries:
        if (FF/row['path']).is_file():
            check('manifest',row)
        elif (FF/'docs/handoffs/w06-ff-matrix'/row['path']).is_file():
            check('manifest',{**row,'path':'docs/handoffs/w06-ff-matrix/'+row['path']})
        else:
            check('manifest',row)
    heads = {
        'worker_head':git(FF,'rev-parse','HEAD'),
        'worker_status':git(FF,'status','--short'),
        'worker_branch':git(FF,'branch','--show-current'),
        'worker_log':git(FF,'log','-3','--format=%H %s'),
        'worker_diff':git(FF,'diff','--name-status',handoff['base_commit'],'HEAD'),
        'canonical_head':git(CANONICAL,'rev-parse','HEAD'),
        'canonical_status':git(CANONICAL,'status','--short'),
        'canonical_worker_distance':git(CANONICAL,'rev-list','--left-right','--count','main...codex/w06-ff-contract-matrix'),
    }
    (HERE/'git-intake.json').write_text(json.dumps(heads,ensure_ascii=False,indent=2),encoding='utf-8')
    (HERE/'sha-verification.json').write_text(json.dumps({'rows':rows,'all_match':all(r['sha_match'] and r['bytes_match'] for r in rows)},ensure_ascii=False,indent=2),encoding='utf-8')
    files = {}
    for p in TOOLS.glob('*'):
        if p.is_file(): files[str(p.relative_to(FF))] = sha(p)
    files['tests/test_w06_contract_matrix.py'] = sha(FF/'tests/test_w06_contract_matrix.py')
    (HERE/'source-shas.json').write_text(json.dumps(files,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'verified_rows':len(rows),'all_sha_match':all(r['sha_match'] for r in rows),'git':heads},ensure_ascii=False))

def probes():
    sys.path.insert(0,str(TOOLS))
    import run as runner
    import matrix_cases as cases
    import cli_main
    import oracle
    from report import CaseResult
    rows=[]
    def add(case_id, expected, actual, fail_if):
        rows.append({'id':case_id,'scope':'independent synthetic pure-function/helper control; no provider, actual product CLI, or network',
                     'expected':expected,'actual':actual,'verdict':'FAIL' if fail_if else 'PASS'})
    with tempfile.TemporaryDirectory(prefix='independent-pure-',dir=HERE) as tmp_name:
        tmp=Path(tmp_name)
        fake_ff,fake_cwp,fake_et=[tmp/n for n in ('ff','cwp','et')]
        for root in (fake_ff,fake_cwp,fake_et): (root/'config').mkdir(parents=True)
        synthetic_key=fake_ff/'config/FMP_API_KEY.txt'
        synthetic_key.write_text('synthetic-not-a-secret',encoding='utf-8')
        reads=[]
        original=runner.sha256_file
        def spy(p): reads.append(str(p)); return original(p)
        with patch.object(runner,'sha256_file',side_effect=spy):
            guard=runner.ProductionGuard(fake_ff,fake_cwp,fake_et)
        add('FFI-SECRET-HASH','no byte read or digest of even synthetic key',{'secret_path_hashed':str(synthetic_key) in reads,'secret_sha_in_guard': 'sha256' in guard.before[str(synthetic_key)]},str(synthetic_key) in reads)
        ctx=object.__new__(runner.Context)
        ctx.cwp_root=fake_cwp;ctx.et_root=fake_et;ctx.scratch=tmp/'scratch'
        ctx.env=SimpleNamespace(proxy_state=tmp/'proxy')
        with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'synthetic-host-marker','OPENAI_API_KEY':'synthetic-host-marker','API_BASE_URL':'https://synthetic-host.invalid','FMP_API_KEY_FILE':'synthetic-file'},clear=True):
            env=ctx.child_env()
        add('FFI-ENV-LEAK','synthetic environment excludes unrelated host credentials/endpoint',{'unrelated_credential_names_propagated':[k for k in ('DEEPSEEK_API_KEY','OPENAI_API_KEY','API_BASE_URL') if k in env], 'fmp_key_synthetic':env.get('FMP_API_KEY')==runner.FAKE_FMP_KEY,'fmp_key_file_removed':'FMP_API_KEY_FILE' not in env},any(k in env for k in ('DEEPSEEK_API_KEY','OPENAI_API_KEY','API_BASE_URL')))
        def fake_ctx(response):
            return SimpleNamespace(env=SimpleNamespace(calls_file=lambda _:tmp/'calls'),write_state=lambda **kw:None,
                                   run_ff=lambda *a,**kw:{'response':response,'exit_code':0,'request_ref':'req','response_ref':'resp'},
                                   worker_ran=lambda _:False,fixture_requests=lambda _:0)
        bad_quarter=cases.case_call_wrong_quarter(fake_ctx({'transcript':{'status':'downloaded','fiscal_quarter':2,'source_ref':{'source_id':'fake'}}})).to_dict()
        add('FFI-WRONG-QUARTER','requested Q3, returned downloaded Q2 must FAIL',bad_quarter,bad_quarter['result']=='PASS')
        wrong_cutoff=cases.case_call_past_cutoff(fake_ctx({'transcript':{'status':'upstream_error','reason':'arbitrary_import_failure'}})).to_dict()
        add('FFI-CUTOFF-UNRELATED-ERROR','unrelated upstream error is not cutoff proof',wrong_cutoff,wrong_cutoff['result']=='PASS')
        false_reuse=cases.case_fin_fetch(fake_ctx({'status':'source_candidate','filing':{'resolution_outcome':'downloaded_new','download_events':0}}),cases.HK,'annual_report',2026,'negative').to_dict()
        add('FFI-MISSING-REUSE','run2 downloaded_new with missing source_ref must FAIL',false_reuse,false_reuse['result']=='PASS')
        unknown=cases.case_err_unknown_usage(fake_ctx({'transcript':{'status':'upstream_error','reason':'provider_loss','provider_requests':0,'provider_usage_complete':False}})).to_dict()
        add('FFI-UNKNOWN-ZERO','unknown provider request count must remain null, even completeness false',unknown,unknown['result']=='PASS')
        valid_quarter=cases.case_call_wrong_quarter(fake_ctx({'transcript':{'status':'provider_unavailable','reason':'quarter_mismatch'}})).to_dict()
        add('CONTROL-QUARTER-REJECTED','explicit quarter mismatch is allowed negative diagnostic',valid_quarter,valid_quarter['result']!='PASS')
        good_error=cases.case_err_request(fake_ctx({'status':'request_error'})) if False else None
        oracle_report={'schema_version':'ff-et-cwp-offline-matrix/1','cases':[], 'restore':{'restored':True},'code_binding':{'verified':False}}
        of=[f.to_dict() for f in oracle.audit(oracle_report)]
        add('FFI-EMPTY-UNBOUND-ORACLE','empty matrix/unverified code binding cannot be PASS',{'findings':of,'passes':oracle.passes(oracle.audit(oracle_report))},not of)
        unknown_oracle={'schema_version':'ff-et-cwp-offline-matrix/1','cases':[{'id':'unknown','expected':{'run_twice':True},'provider_counters':{'run2_fixture_requests':None}}], 'restore':{'restored':True}}
        of=[f.to_dict() for f in oracle.audit(unknown_oracle)]
        add('FFI-ORACLE-NULL-AS-ZERO','unknown reuse request count is not measured zero',{'findings':of},not of)
        # In-process CLI scaffolding only: replaces every producer/case. It proves runner policy,
        # not producer behavior. Existing synthetic baseline must survive even invalid binding.
        owned=tmp/'cli-owned';out=tmp/'cli-output';(owned/'scratch').mkdir(parents=True)
        baseline=owned/'scratch/pre-existing.txt';baseline.write_text('baseline',encoding='utf-8')
        sentinel=owned/runner.SENTINEL_NAME;sentinel.write_text('original-sentinel',encoding='utf-8')
        class NoopContext:
            def __init__(self,**kw):self.__dict__.update(kw)
            def child_env(self):return {}
        class NoopGuard:
            def __init__(self,*a):pass
            def snapshot(self):return {}
            def unchanged(self,*a):return True
        no_op=CaseResult(id='control',title='noop scaffold',declared_layer='ff-only',result='PASS')
        with patch.object(cli_main,'Context',NoopContext), patch.object(cli_main,'ProductionGuard',NoopGuard), patch.object(cli_main,'seed_all',lambda _:None), patch.object(cli_main,'_verify_binding',lambda *a:{'verified':False}), patch.object(cli_main,'_case_registry',lambda:[('control',lambda _:no_op)]), patch.object(cli_main,'_dependency',lambda *a:SimpleNamespace(to_dict=lambda:{})), patch.object(cli_main,'_module_record',lambda *a:{}), patch.object(cli_main.time,'monotonic',side_effect=[0.0,1.0,42.0,220.0]):
            rc=cli_main.main(['--cwp-project',str(fake_cwp),'--et-project',str(fake_et),'--owned-root',str(owned),'--out-root',str(out)])
        rep=json.loads((out/'report.json').read_text(encoding='utf-8'))
        add('FFI-CLI-UNBOUND-BUDGET','unverified import + 41s case/220s batch must not exit0',{'exit_code':rc,'binding':rep['code_binding'],'batch_seconds':rep['scope']['batch_elapsed_seconds'],'diagnostics':rep['cases'][0]['diagnostics']},rc==0)
        add('FFI-CLI-BASELINE-DELETION','existing scratch bytes/sentinel must be rejected or preserved',{'preexisting_file_survived':baseline.exists(),'original_sentinel_survived':sentinel.read_text(encoding='utf-8')=='original-sentinel','restore_claim':rep['restore']},not baseline.exists() or sentinel.read_text(encoding='utf-8')!='original-sentinel')
    out={'schema_version':'w06-ff-independent-probes/1','real_provider_calls':0,'model_calls':0,'paid_usd':0,'scratch_restored':not Path(tmp_name).exists(),'probes':rows}
    (HERE/'independent-counterexamples.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'probe_counts':{k:sum(r['verdict']==k for r in rows) for k in ('PASS','FAIL')},'scratch_restored':out['scratch_restored']},ensure_ascii=False))

def unit_replay():
    with tempfile.TemporaryDirectory(prefix='unit-owned-',dir=HERE) as name:
        owned=Path(name)
        start=time.monotonic()
        cmd=[sys.executable,'-X','utf8','-B','-m','pytest','-q','-p','no:cacheprovider',str(FF/'tests/test_w06_contract_matrix.py'),'--basetemp',str(owned/'pytest')]
        env=dict(os.environ)
        env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONUTF8']='1'
        p=subprocess.run(cmd,cwd=HERE,env=env,capture_output=True,text=True,encoding='utf-8',timeout=45)
        elapsed=time.monotonic()-start
        (HERE/'unit-replay.log').write_text(p.stdout+p.stderr,encoding='utf-8')
        receipt={'command':cmd,'exit_code':p.returncode,'elapsed_seconds':elapsed,'scope':'only 12 delivered pure unit tests; no runner/provider/network','owned_root':str(owned)}
    receipt['scratch_restored']=not Path(name).exists()
    receipt['log']=sha(HERE/'unit-replay.log')
    (HERE/'unit-replay.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))

def evidence_review():
    root=FF/'docs/handoffs/w06-ff-matrix'
    report=json.loads((root/'attempts/attempt-5/report.json').read_text(encoding='utf-8'))
    evidence={'dependencies':report['dependencies'],'code_binding':report.get('code_binding'),'scope':report['scope'],'cost':report['cost'],'restore':report['restore'],'producer_sha_verification':[],'critical_artifacts':{},'retained_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file())}
    for dep in report['dependencies']:
        for m in dep['modules']:
            p=Path(m['file']);a=sha(p)
            evidence['producer_sha_verification'].append({'repository':dep['repository'],'path':str(p),'reported_sha256':m['sha256'],'actual':a,'match':a['sha256']==m['sha256']})
    for name in ('chainA_download_reuse.run1.response.json','chainA_download_reuse.run2.response.json','chainA_download_reuse_run1.usage.json','call_past_cutoff.result.json','call_wrong_quarter.result.json','err_unknown_usage.usage.json'):
        p=root/'attempts/attempt-5/artifacts'/name
        if p.is_file():evidence['critical_artifacts'][name]={'content':json.loads(p.read_text(encoding='utf-8')),'file':sha(p)}
    evidence['ff_report_head_exists']=git(FF,'cat-file','-t',report['dependencies'][0]['head'])
    evidence['ff_report_head_vs_current_product']=git(FF,'diff','--stat',report['dependencies'][0]['head'],'HEAD','--','scripts/')
    evidence['worker_dirty_diff']=git(FF,'diff','--','.planning/w06-ff-matrix/task_plan.md','.planning/w06-ff-matrix/progress.md')
    evidence['changed_files_count']=len(git(FF,'diff','--name-only','08ec85b27133cdf8a8d3b38fdba15255fc1ebac2','HEAD')['stdout'].splitlines())
    (HERE/'delivery-evidence-review.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:evidence[k] for k in ('retained_bytes','changed_files_count','ff_report_head_exists','ff_report_head_vs_current_product','worker_dirty_diff')},ensure_ascii=False))

if __name__=='__main__':
    if '--inventory' in sys.argv:inventory()
    if '--probes' in sys.argv:probes()
    if '--unit' in sys.argv:unit_replay()
    if '--evidence' in sys.argv:evidence_review()
