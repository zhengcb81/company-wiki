"""Single-company repair runner: owned output paths, actual installed commands and trace env."""
from pathlib import Path
import datetime as dt, hashlib, json, os, subprocess, sys, time
HERE=Path(__file__).resolve().parent; PLAN=HERE.parents[1]; WIKI=HERE.parents[4]
SKILL=Path.home()/'.agents/skills/revenue-forecast'
OLD=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root']); OUT=OLD/'v3'
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',REVENUE_PUBLICATION_REGISTRY=str(OUT/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(HERE/'processes'))
env['PYTHONPATH']=os.pathsep.join([str(PLAN/'process_trace'),str(WIKI/'src'),env.get('PYTHONPATH','')])
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def event(action,artifacts,outcome='success',details=None):
 v={'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'agent_id':'/root/rf_hk_execution','step':'v3_repair','action':action,'tool':'actual OS subprocess / bounded HTTP','input_summary':details,'source_url':None,'artifacts':[str(x) for x in artifacts],'outcome':outcome,'error':None}
 with (HERE/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(v,ensure_ascii=False)+'\n')
action=sys.argv[1]
if action=='source-facts':
 old=json.loads((HERE/'source_facts_2025.request.json').read_text(encoding='utf-8'))
 old['evidence']['fiscal_year']['observation']='FY2025 original PDF pages 1 and 4 rendered to owned TEMP/v3 and visually inspected on 2026-10-08. Cover reads 2025 年報; financial-summary current column reads 二零二五年 and income 751,766 人民幣百萬元. This new observation corrects the old copied 2024 visual-check sentence; old assertion/receipt retained.'
 old['evidence']['language']['observation']='FY2025 original cover reads 騰訊控股有限公司 / 2025 年報; financial-summary current-year labels and financial-statement notes are Traditional Chinese. Rendered FY2025 pages 1 and 4 inspected; no translation.'
 rp=HERE/'v3_source_facts_2025.request.json';assert not rp.exists();write(rp,old)
 raw=WIKI/'companies/腾讯/raw/financial_reports/annual/腾讯：2025年年度报告.pdf';before=sha(raw)
 cmd=[sys.executable,'-X','utf8','-m','company_wiki.source_catalog.cli','--config',str(WIKI/'config/source_catalog.yaml'),'source-facts','--request',str(rp)]
elif action=='official-auth':
 import requests
 urls=['https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0409/2026040900888_c.pdf','https://www.tencent.com/zh-hk/investors/financial-reports/','https://static.www.tencent.com/uploads/2026/04/09/5c38a9ec3c5695da42c1534d63e4be0b.pdf']
 rec=[];start=time.monotonic();total=0
 for n,url in enumerate(urls):
  z={'url':url,'captured_at':dt.datetime.now(dt.timezone.utc).isoformat(),'route':'independent official original authentication; NOT FF/Dayu acquisition','max_aggregate_bytes':41943040,'max_aggregate_seconds':180,'cost_usd':0}
  try:
   with requests.get(url,timeout=(8,20),stream=True) as r:
    body=bytearray()
    for chunk in r.iter_content(65536):
     total+=len(chunk);body.extend(chunk)
     if total>41943040 or time.monotonic()-start>180:raise RuntimeError('bounded authentication budget exhausted')
    p=OUT/f'official_auth_{n}.bin';p.write_bytes(body)
    z.update(status_code=r.status_code,final_url=r.url,content_type=r.headers.get('Content-Type'),bytes=len(body),sha256=sha(p),pdf_magic=body.startswith(b'%PDF'),raw_path=str(p),same_sha_as_original=body.startswith(b'%PDF') and sha(p)=='d19f183452e9b8d0c47bcb7543dcbf435b585b2610759b42c0cba7c13f7361c7')
    if n==1:z['archive_contains_observed_url']=urls[2] in body.decode('utf-8',errors='replace')
  except Exception as e:z.update(error=type(e).__name__+': '+str(e),same_sha_as_original=False)
  rec.append(z)
 result={'attempts':rec,'aggregate_bytes':total,'elapsed_seconds':time.monotonic()-start,'status':'SAME_SHA_AUTHENTICATED' if any(x.get('same_sha_as_original') for x in rec) else 'BLOCKED_UNAUTHENTICATED','exact_publication_date':'UNVERIFIED; dated filename is not proof','producer_url_update':'NOT_PERFORMED unless separately same-SHA verified'}
 write(HERE/'v3_official_auth.json',result);event('bounded_official_same_sha_authentication',[HERE/'v3_official_auth.json'],outcome='partial' if result['status'].startswith('BLOCKED') else 'success',details=result)
 print(json.dumps(result,ensure_ascii=False));sys.exit(0)
else:
 cmds={
  'lint':['lint_input.py',str(OUT/'input.json'),'--check-conclusion-facts','--check-sensitivity-propagation'],
  'hash-check':['fix_hashes.py',str(OUT/'input.json'),'--check'],
  'validate':['revenue_forecast.py',str(OUT/'input.json'),'--validate-only','--verbose'],
  'forecast':['revenue_forecast.py',str(OUT/'input.json'),'--output',str(OUT/'forecast.json'),'--markdown',str(OUT/'forecast.md')],
  'snapshot':['revenue_backtest.py','create',str(OUT/'input.json'),'--version','2026-10-08-hk-v3','--output',str(OUT/'snapshot.json')],
  'audit':['publication_registry.py','audit','--result',str(OUT/'forecast.json')],
  'strong-calc':['__local__',str(HERE/'v3_verify.py')],
  'build':['__local__',str(HERE/'v3_build.py')],
 }
 c=cmds[action];cmd=[sys.executable,'-X','utf8',c[1]] if c[0]=='__local__' else [sys.executable,'-X','utf8',str(SKILL/'scripts'/c[0]),*c[1:]]
print(json.dumps({'actual_command':cmd,'environment_overrides':{k:env[k] for k in ['REVENUE_PUBLICATION_REGISTRY','CWP_AUDIT_PROCESS_DIR','PYTHONPATH']}},ensure_ascii=False),flush=True)
r=subprocess.run(cmd,env=env,cwd=str(WIKI if action=='source-facts' else OUT),capture_output=True,text=True,encoding='utf-8',timeout=180)
stdout=HERE/f'v3_{action}.stdout.txt';stderr=HERE/f'v3_{action}.stderr.txt';stdout.write_text(r.stdout,encoding='utf-8');stderr.write_text(r.stderr,encoding='utf-8')
if action=='source-facts':
 assert before==sha(raw),'Original bytes changed'
 write(HERE/'v3_source_facts_2025.receipt.json',{'old_request_sha256':sha(HERE/'source_facts_2025.request.json'),'old_response_sha256':sha(HERE/'source_facts_2025.response.json'),'new_request_path':str(rp),'new_response_path':str(stdout),'new_response':json.loads(r.stdout) if r.returncode==0 else None,'returncode':r.returncode,'raw_before_sha256':before,'raw_after_sha256':sha(raw),'visual_pages':[str(OUT/'FY2025_page_1_visual.png'),str(OUT/'FY2025_page_4_visual.png')],'supersession_requested_via':'standard source-facts producer, no direct DB or sidecar edit'})
event('actual_'+action,[stdout,stderr],outcome='success' if r.returncode==0 else 'failed',details={'command':cmd,'returncode':r.returncode})
print(r.stdout);print(r.stderr,file=sys.stderr);sys.exit(r.returncode)
