import json,sys,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent
E=H.parents[2]/'executions'/'US-MSFT'
O=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/US-MSFT/v2')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def emit(v):print(json.dumps(v,ensure_ascii=False,indent=2))
I=read(O/'input.json'); F=read(O/'forecast.json')
m=sys.argv[1]
if m=='shape':
    for n in ['repair_v2.json','qualitative_targets_v2.json','assumption_support_v2.json','claim_contexts_v2.json','validation_v2.json']:
        x=read(E/n);emit({'file':n,'keys':list(x) if isinstance(x,dict) else None,'type':type(x).__name__,'length':len(x),'example': x[0] if isinstance(x,list) else {k:(len(v) if isinstance(v,(list,dict)) else v) for k,v in x.items()}})
    emit({'input_keys':list(I),'claim_count':len(I['evidence_claims']),'sample_parameter':I['parameters'][10],'sample_claim':I['evidence_claims'][-1],'confidence':F['confidence']})
elif m=='input':
    for k in sys.argv[2:]:emit({k:I.get(k)})
elif m=='file':
    for n in sys.argv[2:]:
        p=Path(n);p=p if p.is_absolute() else E/n;emit({'file':str(p),'data':read(p)})
elif m=='ranges':
    for p in I['parameters']:
        if p['kind']=='analyst_assumption':emit(p)
elif m=='delta':
    A=read(E/'assumption_support_v2.json');P={p['parameter_id']:p for p in I['parameters']};C={c['claim_id']:c for c in I['evidence_claims']}
    seen=set()
    for a in A:
        p=P[a['parameter_id']];group=p['parameter_id'].split('_growth_')[0]
        if group not in seen:
            seen.add(group);emit({'stream':group,'support':a,'definition':p['definition'],'claims':[C[c] for c in a['new_claim_ids']]})
        print('ROW',p['parameter_id'],p['value'],p['scenario'],p['period'],'claims='+str(len(p['claim_ids'])))
    old=read(O.parent/'input.json');oc={c['claim_id']:c for c in old['evidence_claims']};unique={}
    for c in I['evidence_claims']:
        if c.get('excerpt')!=oc.get(c['claim_id'],{}).get('excerpt'):
            key=(c['source_id'],c['excerpt']);unique.setdefault(key,{'source_id':c['source_id'],'excerpt':c['excerpt'],'locator':c['locator'],'claim_ids':[]})['claim_ids'].append(c['claim_id'])
    emit({'unique_changed_excerpt_count':len(unique)})
    for u in unique.values():emit({'source_id':u['source_id'],'locator':u['locator'],'excerpt':u['excerpt'],'claim_count':len(u['claim_ids']),'first_claim':u['claim_ids'][0]})
elif m=='semantic':
    A=read(E/'assumption_support_v2.json');P={p['parameter_id']:p for p in I['parameters']};seen=set()
    for a in A:
        p=P[a['parameter_id']];group=p['parameter_id'].split('_growth_')[0]
        if group not in seen:
            seen.add(group);emit({'stream':group,'support':a,'definition':p['definition']})
        print('ROW',p['parameter_id'],p['value'],p['scenario'],p['period'],'claims='+str(len(p['claim_ids'])))
elif m=='targetcompact':
    for n,t in enumerate(read(E/'qualitative_targets_v2.json')['targets']):
        if len(sys.argv)<3 or int(sys.argv[2])<=n<int(sys.argv[3]):emit({k:t.get(k) for k in ['qualitative_target_id','source_id','locator','exact_wording','metric_perimeter','source_period','commitment_strength','comparison_or_gap','source_publication_date','numeric_normalization_performed']})
elif m=='ownfiles':
    r=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-review-20261008-US-MSFT-independent');emit([str(p) for p in r.iterdir()])
elif m=='narrative':
    emit(read(E.parents[1]/'existing_narrative_current_vs_asof.json'))
elif m=='brief':
    X=read(H/'recheck_v2_evidence_bindings.json');emit({k:X[k] for k in ['binding_failures','changed_claim_text_failures','target_text_failures','segment_differences','all72_growth_values_unchanged']})
    L=read(H/'recheck_v2_integrity.json');emit({'artifact_count':len(L['artifacts']),'artifact_failures':[a for a in L['artifacts'] if not a['pass']],'log_count':len(L['logs']),'log_failures':[x for x in L['logs'] if not x['pass']],'unpaired':L['unpaired'],'post_initial_commands':L['logs'][42:]})
elif m=='postlogs':
    records=[json.loads(x) for x in (E/'commands/index.jsonl').read_text(encoding='utf-8').splitlines()]
    for r in [x for x in records if x['event']=='finish'][42:]:
        emit({'label':r['label'],'returncode':r['returncode'],'stdout':Path(r['outputs']['stdout']['path']).read_text(encoding='utf-8'),'stderr':Path(r['outputs']['stderr']['path']).read_text(encoding='utf-8')})
elif m=='unique':
    old=read(O.parent/'input.json');oc={c['claim_id']:c for c in old['evidence_claims']};unique={}
    for c in I['evidence_claims']:
        if c.get('excerpt')!=oc.get(c['claim_id'],{}).get('excerpt'):
            key=(c['source_id'],c['excerpt']);unique.setdefault(key,{'source_id':c['source_id'],'excerpt':c['excerpt'],'locator':c['locator'],'claim_ids':[]})['claim_ids'].append(c['claim_id'])
    for n,u in enumerate(unique.values()):
        if len(sys.argv)<3 or int(sys.argv[2])<=n<int(sys.argv[3]):emit(dict(number=n,source_id=u['source_id'],locator=u['locator'],excerpt=u['excerpt'],claim_count=len(u['claim_ids']),first_claim=u['claim_ids'][0]))
elif m=='integrity':
    M=read(E/'manifest_v2.json');rows=[]
    for a in M['artifacts']:
        p=Path(a['absolute_path']);b=p.read_bytes();rows.append({'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'pass':len(b)==a['bytes'] and hashlib.sha256(b).hexdigest()==a['sha256']})
    starts={};logs=[]
    for line in (E/'commands/index.jsonl').read_text(encoding='utf-8').splitlines():
        r=json.loads(line)
        if r['event']=='start':starts[r['id']]=r
        else:
            ok=r['id'] in starts
            for x in r['outputs'].values():
                b=Path(x['path']).read_bytes();ok=ok and len(b)==x['byte_size'] and hashlib.sha256(b).hexdigest()==x['sha256']
            logs.append({'id':r['id'],'label':r['label'],'returncode':r['returncode'],'pass':ok,'command':r['command']})
    v1=read(E/'validation_v2.json')['original_v1_hashes_after'] if 'original_v1_hashes_after' in read(E/'validation_v2.json') else None
    result={'artifacts':rows,'logs':logs,'starts':len(starts),'finishes':len(logs),'unpaired':list(set(starts)-{x['id'] for x in logs}),'validation_original_hashes':v1}
    (H/'recheck_v2_integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');emit(result)
