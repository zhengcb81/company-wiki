import json,hashlib,re,unicodedata
from pathlib import Path
H=Path(__file__).resolve().parent;E=H.parents[2]/'executions'/'US-MSFT'
O=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/US-MSFT')
R=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-review-20261008-US-MSFT-independent')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(t):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',t)).strip().lower()
I=read(O/'v2/input.json');V=read(O/'input.json');P={p['parameter_id']:p for p in I['parameters']};oldP={p['parameter_id']:p for p in V['parameters']};oldC={c['claim_id']:c for c in V['evidence_claims']}
maps={'src_call':'call','src_results':'results','src_aws':'aws'}
maps.update({s['source_id']:'producer_fy2025' for s in I['sources'] if s['source_id'].startswith('urn:company-wiki')})
texts={k:(R/(v+'.txt')).read_text(encoding='utf-8') for k,v in maps.items()}
nt={k:norm(t) for k,t in texts.items()};rows=[];contexts={};sources={s['source_id']:s for s in I['sources']}
for c in I['evidence_claims']:
    sid=c['source_id'];changed=c.get('excerpt')!=oldC.get(c['claim_id'],{}).get('excerpt');bits=c['excerpt'].splitlines();found=[]
    for bit in bits:
        j=nt[sid].find(norm(bit)) if sid in nt else -1
        found.append(j)
        if j>=0 and changed:contexts[(sid,bit)]={'source_id':sid,'source_path':str(R/(maps[sid]+'.txt')),'source_sha256':sha(R/(maps[sid]+'.html')),'offset_in_normalized_text':j,'excerpt_piece':bit,'full_context':nt[sid][max(0,j-550):j+len(norm(bit))+1700]}
    bindings=c.get('content_sha256')==sources[sid]['capture']['snapshot_sha256'] and c.get('capture_receipt_sha256')==sources[sid]['capture']['receipt_sha256'] and c.get('excerpt_sha256')==hashlib.sha256(c['excerpt'].strip().encode()).hexdigest()
    rows.append({'claim_id':c['claim_id'],'source_id':sid,'changed':changed,'locator':c['locator'],'bindings_pass':bindings,'independent_piece_offsets':found if sid in nt else None,'independent_original_text_pass':all(j>=0 for j in found) if sid in nt else None,'verification_route':'independent downloaded full original reopened' if sid in nt else ('unchanged original 22-slide visual review / v2 slides17,21' if sid=='src_presentation' else 'unchanged original full-source independent review')})
targets=[]
for t in read(E/'qualitative_targets_v2.json')['targets']:
    sid=t['source_id'];i=nt[sid].find(norm(t['exact_wording'])) if sid in nt else None
    targets.append({'target_id':t['qualitative_target_id'],'source_id':sid,'offset':i,'text_pass':i>=0 if i is not None else None,'route':'independent full official raw reopened' if i is not None else ('independent PPT original visual' if sid=='src_presentation' else 'official Sep25 blog reopened live full article L8/L19/L20/L35/L36')})
unchanged={k:I[k]==V[k] for k in ['historical_revenue','segments','base_year','currency','unit','fiscal_year_end','base_adjustment_parameter_ids','reported_total_revenue_parameter_id','research_coverage','management_communication_coverage','sources']}
changed_nonfuture=[]
for pid,p in P.items():
    if '_growth_' not in pid and p!=oldP[pid]:changed_nonfuture.append(pid)
result={'all_claims':rows,'claim_count':len(rows),'changed_claims':sum(x['changed'] for x in rows),'binding_failures':[x['claim_id'] for x in rows if not x['bindings_pass']],'text_failures':[x for x in rows if x['independent_original_text_pass'] is False],'unique_changed_full_contexts':len(contexts),'targets':targets,'target_text_failures':[x for x in targets if x['text_pass'] is False],'unchanged_input_sections':unchanged,'changed_nonfuture_parameters':changed_nonfuture,'all72_growth_values_unchanged':all(p['value']==oldP[pid]['value'] for pid,p in P.items() if '_growth_' in pid),'source_capture_metadata':[{'source_id':s['source_id'],'capture':s['capture']} for s in I['sources']]}
result['excerpt_hash_contract']='SHA256 of stripped UTF8 text per actual RF text_sha256 contract; first diagnostic compared unstripped text, corrected here; no producer error inferred.'
result['normalized_table_exceptions']=['claim_1_reported_total','claim_99_historical_revenue_2024','claim_100_historical_revenue_2025','claim_101_historical_revenue_2026']
result['changed_claim_text_failures']=[x for x in rows if x['changed'] and x['independent_original_text_pass'] is False]
def diff(a,b,path=''):
    if type(a)!=type(b):return [path]
    if isinstance(a,dict):return sum((diff(a.get(k),b.get(k),path+'/'+str(k)) for k in set(a)|set(b)),[])
    if isinstance(a,list):return sum((diff(x,y,path+'/'+str(n)) for n,(x,y) in enumerate(zip(a,b))),[]) if len(a)==len(b) else [path]
    return [path] if a!=b else []
result['segment_differences']=diff(V['segments'],I['segments'])
(H/'recheck_v2_evidence_bindings.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(H/'recheck_v2_independent_original_contexts.json').write_text(json.dumps(list(contexts.values()),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['all_claims','targets']},ensure_ascii=False,indent=2))
print('All33 target checks',json.dumps(targets,ensure_ascii=False))
