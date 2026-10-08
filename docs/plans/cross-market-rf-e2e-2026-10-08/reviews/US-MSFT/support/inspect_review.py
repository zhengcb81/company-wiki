import sys, json, hashlib
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]
EX = BASE / 'executions' / 'US-MSFT'
OUT = Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/US-MSFT')

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def emit(name, data):
    print('\n### ' + str(name))
    print(json.dumps(data, ensure_ascii=False, indent=2) if not isinstance(data,str) else data)

mode = sys.argv[1]
if mode == 'refs':
    root=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast/references')
    for f in sys.argv[2:]: emit(f, (root/f).read_text(encoding='utf-8'))
elif mode == 'inventory':
    for root in [EX, OUT]:
        emit(root, [dict(path=str(p),bytes=p.stat().st_size) for p in root.rglob('*') if p.is_file()])
    for f in ['input.json','forecast.json','snapshot.json']:
        data=load(OUT/f);emit(f+' topkeys',list(data))
    for f in ['fact_checks.json','communication_coverage.json']:
        data=load(EX/f);emit(f+' topkeys',list(data) if isinstance(data,dict) else type(data).__name__)
elif mode == 'files':
    for f in sys.argv[2:]:
        p = Path(f)
        if not p.is_absolute(): p=EX/p
        emit(p, p.read_text(encoding='utf-8-sig'))
elif mode == 'input':
    inp=load(OUT/'input.json')
    for k in sys.argv[2:]:emit(k,inp.get(k))
elif mode == 'facts':
    fc=load(EX/'fact_checks.json');emit('facts',fc)
elif mode == 'compact':
    inp=load(OUT/'input.json')
    for k in ['company_name','as_of_date','currency','unit','fiscal_year_end','base_year','forecast_years','forecast_version','historical_revenue','segments','research_coverage','management_communication_coverage','management_targets','growth_driver_tree','data_gaps','sensitivity_tests']:
        emit(k,inp[k])
    emit('sources',[{k:s.get(k) for k in ['source_id','source_type','title','publisher','url','published_date','locator','capture']} for s in inp['sources']])
    emit('parameters',inp['parameters'])
elif mode == 'claims_compact':
    inp=load(OUT/'input.json');claims=inp['evidence_claims']
    emit('claim_shape',claims[0]);emit('fact_shape',load(EX/'fact_checks.json')[0])
    for c in claims:
        print(json.dumps(c,ensure_ascii=False))
elif mode == 'summary':
    inp=load(OUT/'input.json')
    emit('sources', [{k:s.get(k) for k in ['source_id','title','url','published_date','locator']} for s in inp['sources']])
    emit('claim example',inp['evidence_claims'][0])
    emit('fact example',load(EX/'fact_checks.json')[0])
    print('ALL PARAMETERS')
    for p in inp['parameters']: print(json.dumps({k:v for k,v in p.items() if k not in ['evidence_claim_ids','source_ids','rationale']},ensure_ascii=False))
    print('ALL CLAIMS')
    for c in inp['evidence_claims']: print(json.dumps({k:c.get(k) for k in ['claim_id','target_type','target_id','source_id','locator','excerpt','extracted_value','extracted_unit','extracted_period','support_type']},ensure_ascii=False))
elif mode == 'audit_summary':
    m=load(EX/'manifest.json');i=load(Path(__file__).parent/'integrity.json')
    emit('integrity summary',{k:v for k,v in i.items() if k!='commands'})
    for c in i['commands']:print(c['label'],c['rc'],c['elapsed'],' '.join(c['command']))
    for k in ['defects','gaps','calls_and_cost','owned_cleanup','unchanged_originals']:emit(k,m.get(k))
    for p in sorted((EX/'processes').glob('*')):emit(p.name,p.read_text(encoding='utf-8'))
elif mode == 'review_rows':
    inp=load(OUT/'input.json');group={}
    for p in inp['parameters']:
        print('PARAM',json.dumps({k:p.get(k) for k in ['parameter_id','value','kind','unit','period','scenario','source_ids']},ensure_ascii=False))
    for c in inp['evidence_claims']:
        key=(c['source_id'],c.get('locator'),c.get('excerpt'))
        group.setdefault(key,[]).append({k:c.get(k) for k in ['claim_id','target_type','target_id','extracted_value','extracted_unit','extracted_period','support_type']})
    for (sid,loc,ex),cs in group.items():emit('source-context',{ 'source_id':sid,'locator':loc,'excerpt':ex,'claims':cs})
elif mode == 'logs':
    for f in ['commands/index.jsonl','events.jsonl']:
        emit(f,(EX/f).read_text(encoding='utf-8'))
elif mode == 'integrity':
    m=load(EX/'manifest.json');bad=[];checked=[]
    for a in m['artifacts']:
        p=Path(a['absolute_path']);h=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        ok=h==a['sha256'] and p.stat().st_size==a['bytes'] if p.exists() else False
        checked.append(dict(path=str(p),sha256=h,ok=ok))
        if not ok:bad.append(checked[-1])
    starts={};finishes=[];logbad=[]
    for l in (EX/'commands/index.jsonl').read_text(encoding='utf-8').splitlines():
        r=json.loads(l)
        if r['event']=='start':starts[r['id']]=r
        else:
            finishes.append(r)
            if r['id'] not in starts:logbad.append({'missingstart':r['id']})
            for o in r['outputs'].values():
                p=Path(o['path']);h=hashlib.sha256(p.read_bytes()).hexdigest()
                if h!=o['sha256'] or p.stat().st_size!=o['byte_size']:logbad.append({'mismatch':str(p)})
    result=dict(artifacts_checked=len(checked),artifact_failures=bad,starts=len(starts),finishes=len(finishes),failure_count=sum(x['returncode']!=0 for x in finishes),unpaired=list(set(starts)-{x['id'] for x in finishes}),log_failures=logbad,commands=[dict(label=x['label'],command=x['command'],rc=x['returncode'],elapsed=x['elapsed_seconds'],outputs=x['outputs']) for x in finishes])
    dest=Path(__file__).parent/'integrity.json';dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');emit('integrity',result)
