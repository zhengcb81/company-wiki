"""Company-local process environment; no shared configuration changes."""
from pathlib import Path
import datetime, json, os, subprocess, sys
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
TRACE=ROOT.parents[1]/'process_trace'
env=dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1', REVENUE_PUBLICATION_REGISTRY=str(OUT/'publications.jsonl'), CWP_AUDIT_PROCESS_DIR=str(ROOT/'processes'))
env['PYTHONPATH']=str(TRACE)+os.pathsep+env.get('PYTHONPATH','')
event=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), agent_id='rf_cn_execution', step='process', action='run configured installed tool with isolated registry and nested process trace', tool='subprocess', input_summary=sys.argv[1:], source_url=None, artifacts=[str(OUT/'publications.jsonl'),str(ROOT/'processes')], outcome='started', error=None, environment={k:env[k] for k in ['REVENUE_PUBLICATION_REGISTRY','CWP_AUDIT_PROCESS_DIR','PYTHONPATH']})
with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
proc=subprocess.run(sys.argv[1:],env=env,check=False)
sys.exit(proc.returncode)
