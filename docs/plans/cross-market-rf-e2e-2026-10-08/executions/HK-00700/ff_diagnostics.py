"""Preserve complete FF envelope, including independent transcript status."""
from pathlib import Path
import datetime as dt, json, os, subprocess, sys
HERE=Path(__file__).resolve().parent; PLAN=HERE.parents[1]
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',CWP_AUDIT_PROCESS_DIR=str(HERE/'processes'))
env['PYTHONPATH']=str(PLAN/'process_trace')+os.pathsep+env.get('PYTHONPATH','')
request=json.loads((HERE/'request_annual_2025_no_language.json').read_text(encoding='utf-8'))
request['companion_transcript']={'intent':'fetch_if_missing','fiscal_year':2026,'fiscal_quarter':2,'acquisition_limits':{'max_bytes':41943040,'timeout_seconds':180,'max_cost_usd':'0.00'}}
rp=HERE/'request_ff_annual2025_companion2026q2.json';rp.write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
cmd=[sys.executable,str(Path.home()/'Projects/filing-fetch/scripts/fetch_filing.py'),'--request-file',str(rp),'--source-ref-v2','--timeout-seconds','180']
p=subprocess.run(cmd,env=env,text=True,encoding='utf-8',capture_output=True,timeout=200)
(HERE/'ff_latest_companion.response.json').write_text(p.stdout,encoding='utf-8');(HERE/'ff_latest_companion.stderr.txt').write_text(p.stderr,encoding='utf-8')
print(json.dumps({'command':cmd,'returncode':p.returncode},ensure_ascii=False));print(p.stdout);print(p.stderr,file=sys.stderr)
with (HERE/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'agent_id':'/root/rf_hk_execution','step':'1A','action':'independent_ff_companion_diagnostic','tool':'FF CLI','input_summary':request,'source_url':None,'artifacts':[str(rp),str(HERE/'ff_latest_companion.response.json')],'outcome':'success' if p.returncode==0 else 'failed','error':p.stderr or None},ensure_ascii=False)+'\n')
sys.exit(p.returncode)
