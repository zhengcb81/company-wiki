import os,sys,subprocess,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
RF=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast')
ORIG=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/US-MSFT')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
files=[ORIG/'forecast.json',ORIG/'publications.jsonl',ORIG/'snapshot.json']
before={str(p):sha(p) for p in files}
cmd=[sys.executable,'-B',str(RF/'scripts/publication_registry.py'),'audit','--result',str(ORIG/'forecast.json')]
proc=subprocess.run(cmd,cwd=RF,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',REVENUE_PUBLICATION_REGISTRY=str(ORIG/'publications.jsonl')),capture_output=True,timeout=45)
after={str(p):sha(p) for p in files}
result={'command':cmd,'registry':str(ORIG/'publications.jsonl'),'returncode':proc.returncode,'stdout':proc.stdout.decode('utf-8'),'stderr':proc.stderr.decode('utf-8'),'installed_audit_sha256':sha(RF/'scripts/publication_registry.py'),'repository_audit_sha256':sha(Path('C:/Users/郑曾波/Projects/revenue-forecast/scripts/publication_registry.py')),'before':before,'after':after,'unchanged':before==after}
(HERE/'independent_registry_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
assert proc.returncode==0 and before==after and result['installed_audit_sha256']==result['repository_audit_sha256']
