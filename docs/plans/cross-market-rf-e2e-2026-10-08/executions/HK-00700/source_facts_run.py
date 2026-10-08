"""Use CWP public producer API for observed metadata; never mutate raw/sidecars."""
from pathlib import Path
import datetime as dt, hashlib, json, os, subprocess, sys
HERE=Path(__file__).resolve().parent
WIKI=HERE.parents[4]
PLAN=HERE.parents[1]
before=json.loads((HERE/'before.json').read_text(encoding='utf-8'))
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
env['PYTHONPATH']=os.pathsep.join([str(PLAN/'process_trace'),str(WIKI/'src'),env.get('PYTHONPATH','')])
env['CWP_AUDIT_PROCESS_DIR']=str(HERE/'processes')
receipts=[]
for year in (2024,2025):
    original=next(x for x in before['protected'] if x['path'].endswith(f'腾讯：{year}年年度报告.pdf'))
    p=Path(original['path']); sha=hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha==original['sha256'] and p.stat().st_size==original['bytes']
    source_ref={'schema_version':'2.0','document_id':'urn:company-wiki:document:sha256:'+sha,'source_id':'urn:company-wiki:source:sha256:'+sha,'content_sha256':sha,'byte_size':p.stat().st_size,'mime_type':'application/pdf'}
    request={'source_ref':source_ref,'facts':{'fiscal_year':year,'language':'zh'},'evidence':{'fiscal_year':{'locator':'PDF page 1 cover and financial summary PDF page 4','value':year,'observation':f'Cover explicitly {year} 年報; financial summary year column {year}. 2024 cover visually rendered and inspected.'},'language':{'locator':'PDF page 1 cover; PDF page 4 financial summary; audited revenue note','value':'zh','observation':'Traditional Chinese cover 年報 and Chinese financial-summary and revenue-note body; original-language flag only, no translation.'}}}
    rp=HERE/f'source_facts_{year}.request.json';rp.write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
    command=[sys.executable,'-m','company_wiki.source_catalog.cli','--config',str(WIKI/'config/source_catalog.yaml'),'source-facts','--request',str(rp)]
    result=subprocess.run(command,env=env,cwd=str(WIKI),capture_output=True,text=True,encoding='utf-8',timeout=180)
    (HERE/f'source_facts_{year}.response.json').write_text(result.stdout,encoding='utf-8')
    (HERE/f'source_facts_{year}.stderr.txt').write_text(result.stderr,encoding='utf-8')
    unchanged=hashlib.sha256(p.read_bytes()).hexdigest()==sha and p.stat().st_size==source_ref['byte_size']
    receipt={'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'command':command,'returncode':result.returncode,'request_path':str(rp),'raw_path':str(p),'raw_before_sha256':sha,'raw_after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'raw_unchanged':unchanged,'response':result.stdout,'stderr':result.stderr}
    receipts.append(receipt);print(json.dumps(receipt,ensure_ascii=False),flush=True)
    with (HERE/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'timestamp_utc':receipt['timestamp_utc'],'agent_id':'/root/rf_hk_execution','step':'1A','action':'record_source_facts','tool':'CWP source-facts CLI','input_summary':request,'source_url':None,'artifacts':[str(rp),str(HERE/f'source_facts_{year}.response.json')],'outcome':'success' if result.returncode==0 else 'failed','error':result.stderr or None},ensure_ascii=False)+'\n')
    if result.returncode or not unchanged:sys.exit(result.returncode or 1)
for name in ('annual_2024','interim_2026'):
    r=json.loads((HERE/f'request_{name}.json').read_text(encoding='utf-8'));r.pop('language',None)
    (HERE/f'request_{name}_no_language.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'source_facts_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2),encoding='utf-8')
