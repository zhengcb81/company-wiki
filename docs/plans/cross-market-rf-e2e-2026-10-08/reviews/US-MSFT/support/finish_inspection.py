import json,sys,re,hashlib
from pathlib import Path
from bs4 import BeautifulSoup
HERE=Path(__file__).resolve().parent
EX=HERE.parents[2]/'executions'/'US-MSFT'
ORIG=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/US-MSFT')
ROOT=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-review-20261008-US-MSFT-independent')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def out(k,v):print(k,json.dumps(v,ensure_ascii=False))
inp=read(ORIG/'input.json')
mode=sys.argv[1]
if mode=='targets':
    out('numeric_targets',inp['management_targets'])
    comm=read(EX/'communication_coverage.json')
    out('qualitative_table',comm['qualitative_targets'])
    out('communication',comm['formal_categories'])
elif mode=='trees':
    out('tree',inp['growth_driver_tree'])
    out('coverage',inp['research_coverage'])
    out('confidence',read(ORIG/'forecast.json').get('confidence'))
    out('gaps',inp['data_gaps'])
elif mode=='claim_summary':
    from collections import Counter
    out('sources',inp['sources'])
    out('count',Counter(c['target_type'] for c in inp['evidence_claims']))
    for c in inp['evidence_claims']:
        if c['support_type']!='rationale_support':out('claim',c)
elif mode=='raw_context':
    texts={x:(ROOT/(x+'.txt')).read_text(encoding='utf-8') for x in ['call','results','metrics','aws','producer_fy2025']}
    queries={
        'call':['Now to our outlook','double-digit','Commercial bookings','remaining performance obligation','capacity constrained','supply','advanced','higher ARPU','lower ARPU','inventories','Let’s move to Q&A','Let us move to Q&A'],
        'producer_fy2025':['NOTE 1 — ACCOUNTING POLICIES','Revenue Recognition','Principal','gross versus net','gross basis','net basis','June 30, 2025'],
        'aws':['AWS segment sales','37%','AWS sales'],
        'results':['Fiscal Year 2026 Results','331,839','281,724'],
        'metrics':['Capital expenditures','Azure and other cloud services revenue growth','Microsoft 365 Commercial cloud revenue growth']}
    contexts=[]
    for source,qs in queries.items():
        t=texts[source]
        for q in qs:
            matches=[m.start() for m in re.finditer(re.escape(q),t,re.I)]
            size=15000 if q=='Now to our outlook' else (8000 if q=='NOTE 1 — ACCOUNTING POLICIES' else 2300)
            data={'source':source,'query':q,'occurrences':len(matches),'contexts':[{'offset':i,'text':t[max(0,i-400):i+size]} for i in matches[:2]]}
            contexts.append(data);out('rawcontext',data)
    (HERE/'full_raw_contexts.json').write_text(json.dumps(contexts,ensure_ascii=False,indent=2),encoding='utf-8')
elif mode=='capture_diff':
    diff=[]
    for key in ['call','results','metrics']:
        raw=(ORIG/(key+'.html')).read_bytes();soup=BeautifulSoup(raw,'html.parser')
        for x in soup(['script','style']):x.decompose()
        old=soup.get_text(' ',strip=True);new=(ROOT/(key+'.txt')).read_text(encoding='utf-8')
        import difflib
        deltas=list(difflib.ndiff(old.split(),new.split()))
        edits=[x for x in deltas if x.startswith(('+ ','- '))]
        diff.append({'source':key,'normalized_equal':old==new,'normalized_sha256':hashlib.sha256(new.encode()).hexdigest(),'word_edits':edits})
    (HERE/'independent_capture_content_diff.json').write_text(json.dumps(diff,ensure_ascii=False,indent=2),encoding='utf-8');out('diff',diff)
elif mode=='targeted':
    for p in inp['parameters']:
        if any(k in p['parameter_id'] for k in ['windows','xbox','azure_growth_base','microsoft_365_cloud_growth_base']):out('param',p)
    for c in inp['evidence_claims']:
        if c['target_type']=='growth_driver' or c['claim_id'].startswith('claim_122'):out('growthclaim',c)
    sources={s['source_id']:s for s in inp['sources']}
    bad=[]
    for c in inp['evidence_claims']:
        s=sources[c['source_id']]
        for field,key in [('content_sha256','snapshot_sha256'),('capture_receipt_sha256','receipt_sha256')]:
            if c.get(field)!=s['capture'].get(key):bad.append({'claim_id':c['claim_id'],'field':field,'actual':c.get(field),'expected':s['capture'].get(key)})
    out('claim_bindings_mismatch',bad)
elif mode=='source_claim_presence':
    textmap={'src_call':'call','src_results':'results','src_aws':'aws'}
    textmap.update({s['source_id']:'producer_fy2025' for s in inp['sources'] if s['source_id'].startswith('urn:company-wiki')})
    rows=[]
    for c in inp['evidence_claims']:
        if c['source_id'] not in textmap:continue
        t=(ROOT/(textmap[c['source_id']]+'.txt')).read_text(encoding='utf-8')
        excerpt=c['excerpt'];i=t.lower().find(excerpt.lower())
        key=excerpt if i>=0 else ('AWS segment sales' if c['source_id']=='src_aws' else excerpt[:25])
        j=t.lower().find(key.lower())
        row={'claim_id':c['claim_id'],'source':textmap[c['source_id']],'exact_excerpt_present':i>=0,'context_offset':j,'fresh_context':t[max(0,j-200):j+2100] if j>=0 else None}
        rows.append(row);out('presence',row)
    (HERE/'independent_claim_contexts.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
elif mode=='full_call_chunk':
    t=(ROOT/'call.txt').read_text(encoding='utf-8');start=int(sys.argv[2]);end=min(int(sys.argv[3]),len(t));out('call_characters_'+str(start)+'_'+str(end),t[start:end])
elif mode=='note1_full':
    t=(ROOT/'producer_fy2025.txt').read_text(encoding='utf-8');i=t.index('Revenue is recognized upon transfer of control')
    out('Note1_RevenueRecognition',{'offset':i,'text':t[i-350:i+10500]})
elif mode=='boundary':
    baseline=read(HERE.parents[2]/'baseline.json');rows=[]
    for row in baseline['config_files']:
        p=Path(row['path']);current=hashlib.sha256(p.read_bytes()).hexdigest();rows.append({'path':str(p),'baseline_sha256':row['sha256'],'current_sha256':current,'unchanged':current==row['sha256']})
    result={'baseline_timestamp':baseline['timestamp_utc'],'configuration':rows,'executor_artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ORIG/'input.json',ORIG/'forecast.json',ORIG/'forecast.md',ORIG/'snapshot.json']},'limitations':'File SHA comparison confirms these files only; other agents own WIP and global-store audits. This reviewer does not assert a global store before/after snapshot.'}
    (HERE/'boundary_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');out('boundary',result)
elif mode=='events_summary':
    rows=[json.loads(x) for x in (EX/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    for i,row in enumerate(rows):out('event',{'number':i+1,**{k:row.get(k) for k in ['timestamp_utc','step','action','tool','outcome','returncode','source_url','byte_size','cwp_canonical_narrative_processed']}})
    out('events_count',len(rows))
elif mode=='source_receipts':
    for f in ['request_fy2025_reuse_response.json','request_fy2024_reuse_response.json','request_fy2026_fetch_legacy.json','request_fy2026_fetch.json','request_fy2026_fetch_legacy_response.json','html_temporary_parse_receipt.json','et_discover_response.json','et_standalone_probe_response.json']:
        p=EX/f
        if p.exists() and p.stat().st_size:out(f,read(p))
        else:out(f,{'missing':not p.exists(),'bytes':p.stat().st_size if p.exists() else None,'interpretation':'Failed subprocess output is not a success receipt; inspect matching stderr and ledger.'})
elif mode=='all_logs':
    rows=[json.loads(x) for x in (EX/'commands/index.jsonl').read_text(encoding='utf-8').splitlines() if json.loads(x)['event']=='finish'];replay=[]
    for row in rows:
        logs={k:Path(v['path']).read_text(encoding='utf-8') for k,v in row['outputs'].items()}
        stderr=logs['stderr'];stdout=logs['stdout']
        summary={'label':row['label'],'returncode':row['returncode'],'command':row['command'],'stdout_bytes':row['outputs']['stdout']['byte_size'],'stderr_bytes':row['outputs']['stderr']['byte_size'],'stderr':stderr,'stdout':stdout if len(stdout)<=6000 else {'full_content_retained_in_replay':True,'first1000':stdout[:1000],'last1000':stdout[-1000:]}}
        out('command_log',summary);replay.append({'ledger':row,'stdout':stdout,'stderr':stderr})
    (HERE/'execution_log_replay.json').write_text(json.dumps(replay,ensure_ascii=False,indent=2),encoding='utf-8');out('full_byte_read_count',len(rows))
