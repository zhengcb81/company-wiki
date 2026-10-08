"""Only CN v3 child-process environment; shared settings are unchanged."""
from pathlib import Path
import datetime, json, os, subprocess, sys
ROOT=Path(__file__).resolve().parent
OUT=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/CN-688012/v3')
TRACE=ROOT.parents[1]/'process_trace'
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',REVENUE_PUBLICATION_REGISTRY=str(OUT/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(ROOT/'processes'))
env['PYTHONPATH']=str(TRACE)+os.pathsep+env.get('PYTHONPATH','')
event=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),agent_id='rf_cn_execution',step='v3_repair',action='run actual command with isolated v3 publication registry',tool='subprocess',input_summary=sys.argv[1:],artifacts=[str(OUT/'publications.jsonl')],outcome='started',error=None,environment={k:env[k] for k in ['REVENUE_PUBLICATION_REGISTRY','CWP_AUDIT_PROCESS_DIR','PYTHONPATH']})
with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
sys.exit(subprocess.run(sys.argv[1:],env=env,check=False).returncode)
