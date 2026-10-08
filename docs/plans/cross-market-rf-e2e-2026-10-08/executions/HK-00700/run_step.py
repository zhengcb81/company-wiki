"""Task-local runner: env isolation, actual skill commands and supplemental IR captures."""
from pathlib import Path
import datetime as dt, hashlib, json, os, subprocess, sys, time
HERE=Path(__file__).resolve().parent
PLAN=HERE.parents[1]
WIKI=HERE.parents[4]
SKILL=Path.home()/'.agents/skills/revenue-forecast'
OUT=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root'])
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',REVENUE_PUBLICATION_REGISTRY=str(OUT/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(HERE/'processes'))
env['PYTHONPATH']=str(PLAN/'process_trace')+os.pathsep+env.get('PYTHONPATH','')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def event(step, action, tool, inp, artifacts=[], outcome='success', source_url=None):
    q=dict(timestamp_utc=dt.datetime.now(dt.timezone.utc).isoformat(),agent_id='/root/rf_hk_execution',step=step,action=action,tool=tool,input_summary=inp,source_url=source_url,artifacts=artifacts,outcome=outcome,error=None)
    with (HERE/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(q,ensure_ascii=False)+'\n')
action=sys.argv[1]
if action=='ir-capture':
    import requests, fitz
    url='https://www.tencent.com/wp-content/uploads/2026/09/Corporate-Overview-2Q26-20260916.pdf'
    started=time.monotonic();r=requests.get(url,timeout=(15,60),stream=True);r.raise_for_status();body=bytearray()
    for chunk in r.iter_content(65536):
        if time.monotonic()-started>180:raise TimeoutError('IR capture deadline')
        body.extend(chunk)
        if len(body)>41943040:raise ValueError('IR capture byte ceiling')
    if not body.startswith(b'%PDF'):raise ValueError('expected PDF original')
    p=OUT/'corporate_overview_20260916.pdf';p.write_bytes(body)
    pages=[dict(page=i+1,text=q.get_text()) for i,q in enumerate(fitz.open(p))]
    (OUT/'corporate_overview_pages.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf-8')
    receipt=dict(url=url,final_url=r.url,status_code=r.status_code,download_bytes=len(body),sha256=sha(p),raw_path=str(p),pages=len(pages),published_date='2026-09-16',publication_date_basis='official investor-kit link+dated filename Sep2026 title; exact day is website filename asserted, not inferred mtime',tool='requests.get streamed',supplemental_route='official IR presentation, not financial-filing route',max_bytes=41943040,timeout_seconds=180,cost_usd='0.00',elapsed_seconds=time.monotonic()-started)
    (HERE/'ir_capture_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    event('1A','supplemental_ir_original_capture','requests.get',receipt,[str(p),str(OUT/'corporate_overview_pages.json')],source_url=url)
    print(json.dumps(receipt,ensure_ascii=False))
    for q in pages:print('\nPDF PAGE',q['page'],'\n',q['text'])
else:
    cli={
        'annual-2025':['source_preparation.py','--request-file',str(HERE/'request_annual_2025_no_language.json'),'--company-wiki-catalog-config',str(WIKI/'config/source_catalog.yaml'),'--timeout-seconds','180'],
        'annual-2024':['source_preparation.py','--request-file',str(HERE/'request_annual_2024_no_language.json'),'--company-wiki-catalog-config',str(WIKI/'config/source_catalog.yaml'),'--timeout-seconds','180'],
        'interim-2026':['source_preparation.py','--request-file',str(HERE/'request_interim_2026_no_language.json'),'--company-wiki-catalog-config',str(WIKI/'config/source_catalog.yaml'),'--timeout-seconds','180','--allow-download'],
        'lint':['lint_input.py',str(OUT/'input.json'),'--check-conclusion-facts','--check-sensitivity-propagation'],
        'hash':['fix_hashes.py',str(OUT/'input.json')],
        'validate':['revenue_forecast.py',str(OUT/'input.json'),'--validate-only','--verbose'],
        'forecast':['revenue_forecast.py',str(OUT/'input.json'),'--output',str(OUT/'forecast.json'),'--markdown',str(OUT/'forecast.md')],
        'snapshot':['revenue_backtest.py','create',str(OUT/'input.json'),'--version','2026-10-08-hk-v1','--output',str(OUT/'snapshot.json')],
        'snapshot-v2':['revenue_backtest.py','create',str(OUT/'input.json'),'--version','2026-10-08-hk-v2','--output',str(OUT/'snapshot-v2.json')],
    }
    args=cli[action];cmd=[sys.executable,str(SKILL/'scripts'/args[0]),*args[1:]]
    print(json.dumps({'actual_command':cmd,'environment_overrides':{k:env[k] for k in ['REVENUE_PUBLICATION_REGISTRY','CWP_AUDIT_PROCESS_DIR','PYTHONPATH']}},ensure_ascii=False),flush=True)
    proc=subprocess.run(cmd,env=env,cwd=str(OUT),text=True,encoding='utf-8',capture_output=True,timeout=220)
    stamp=time.time_ns();out=HERE/f'{action}-{stamp}.response.json';out.write_text(proc.stdout,encoding='utf-8');err=HERE/f'{action}-{stamp}.stderr.txt';err.write_text(proc.stderr,encoding='utf-8')
    if proc.returncode==0 and action.startswith(('annual','interim')):
        target=HERE/f'{action}.source.json';target.write_text(proc.stdout,encoding='utf-8')
    event('3' if action.startswith(('annual','interim')) else '10','actual_skill_'+action,'subprocess',{'command':cmd,'returncode':proc.returncode},[str(out),str(err)],outcome='success' if proc.returncode==0 else 'failed')
    print(proc.stdout);print(proc.stderr,file=sys.stderr);sys.exit(proc.returncode)
