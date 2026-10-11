"""Two pure report-copy probes: fixed coverage and request/expectation authority."""
import copy,hashlib,json,shutil,sys,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
BASE=OUT.parent
SCRATCH=OUT/'_expectation_scratch'
if SCRATCH.exists() or (OUT/'expectation-results.json').exists():
    raise RuntimeError('Never overwrite independent evidence')
root=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
sys.path.insert(0,str(root/'tools/offline_contract_matrix'))
import oracle
with zipfile.ZipFile(BASE/'fix/offline-evidence.zip') as z:
    original=json.loads(z.read('matrix/attempt-1bb98380f75347e7b792e5966c11867e/report.json'))
rows=[]
before=[f.to_dict() for f in oracle.audit(original)]
copy1=copy.deepcopy(original)
case=next(c for c in copy1['cases'] if c['id']=='call_past_cutoff')
old_expected=copy.deepcopy(case['expected'])
case['expected']={}
after=[f.to_dict() for f in oracle.audit(copy1)]
rows.append({'name':'CASE-EXPECTED-CUTOFF-REMOVAL','expected':'fixed case ID must retain cutoff requirement',
             'old_expected':old_expected,'new_expected':case['expected'],'original_findings':before,
             'mutated_findings':after,'pass':any(f['vector']=='wrong_cutoff' for f in after)})
(OUT/'removed-cutoff-expectation-report-copy.json').write_text(json.dumps(copy1,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
SCRATCH.mkdir()
try:
    copy2=copy.deepcopy(original)
    copy2['cases']=[c for c in copy2['cases'] if c['result']=='PASS']
    copy2['required_cases']=[c['id'] for c in copy2['cases']]
    oldroot=Path(copy2['evidence_root'])
    for c in copy2['cases']:
        for run in c['actual']['runs']:
            for kind in ('request','response'):
                rel=run[kind+'_ref']
                source=(oldroot/rel).resolve()
                target=(SCRATCH/rel).resolve()
                assert source.is_relative_to(oldroot.resolve()) and target.is_relative_to(SCRATCH.resolve())
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(source.read_bytes())
    target=next(c for c in copy2['cases'] if c['id']=='fin_cn_annual_hit')
    run=target['actual']['runs'][0]
    request_path=SCRATCH/run['request_ref']
    request=json.loads(request_path.read_text(encoding='utf-8'))
    original_request=copy.deepcopy(request)
    request['market']='HK'
    request['company_query']='Tencent Holdings Limited'
    # This is a review-only response transcript: real source proof remains CN2024.
    # No producer or request is actually executed, and old receipts are untouched.
    request_path.write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    run['request_sha256']=hashlib.sha256(request_path.read_bytes()).hexdigest()
    copy2['evidence_root']=str(SCRATCH)
    findings=[f.to_dict() for f in oracle.audit(copy2)]
    rows.append({'name':'CASE-REQUEST-MARKET-NOT-BOUND-TO-FIXED-VECTOR',
                 'expected':'fin_cn_annual_hit requires its fixed CN request, not caller-declared HK',
                 'original_request':original_request,'mutated_request':request,
                 'retained_case_id':target['id'],'case_expected':target['expected'],
                 'oracle_findings':findings,'oracle_pass':not findings,'pass':bool(findings)})
    # Freeze the countermodel in a replayable form without leaving scratch artifacts.
    # Restore root field to original sealed location only in a separate explanatory copy;
    # the executed in-memory root and modified request bytes are retained below.
    (OUT/'modified-request-vector.json').write_text(json.dumps({'executed_request':request,'request_sha256':run['request_sha256'],
         'retained_source_proof':copy2['source_proofs']['proofs'][(run['response']['filing']['source_ref'])['document_id']],
         'target_case':target,'executed_evidence_root':str(SCRATCH),'original_evidence_root':str(oldroot)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
finally:
    assert SCRATCH.resolve().parent==OUT.resolve() and SCRATCH.name=='_expectation_scratch'
    shutil.rmtree(SCRATCH)
    (OUT/'expectation-results.json').write_text(json.dumps({'schema':'w06-independent-expectation-authority/1','probes':rows,
         'scratch_initial_exists':False,'scratch_final_exists':SCRATCH.exists(),'provider_calls':0,'llm_calls':0,'fees_usd':0,
         'scope':'Only report copies and synthetic copied request/response evidence; no actual producer calls'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'probes':len(rows),'failed':[r['name'] for r in rows if not r['pass']],
                      'mutated_request_oracle_pass':rows[-1].get('oracle_pass'),'scratch_absent':not SCRATCH.exists()},ensure_ascii=False))
