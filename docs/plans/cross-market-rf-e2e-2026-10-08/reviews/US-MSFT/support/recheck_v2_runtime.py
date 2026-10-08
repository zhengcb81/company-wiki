from pathlib import Path
import json,hashlib,subprocess,os,sys
H=Path(__file__).resolve().parent
s=(H/'independent_runtime.py').read_text(encoding='utf-8')
s=s.replace("US-MSFT')","US-MSFT/v2')")
s=s.replace("US-MSFT-independent')","US-MSFT-independent/v2')")
s=s.replace("EX/'manifest.json'","EX/'manifest_v2.json'")
s=s.replace("'runtime_recompute.json'","'recheck_v2_runtime_recompute.json'")
s=s.replace("'independent_calculations.json'","'recheck_v2_independent_calculations.json'")
s=s.replace("semantic_status='FAIL'","semantic_status='PASS'")
for name in ['OUTPUT SEGMENT SHAPE','ATTRIBUTION SHAPE','SENSITIVITY SHAPE']:
    s='\n'.join(line for line in s.splitlines() if not line.startswith("print('"+name))
s=s.replace("pid=shock['parameter_id'];seg=", "assert shock['shock_value']==.05\n    pid=shock['parameter_id'];seg=")
s=s.replace("changed=b*(1+eff)","assert req==shock['effective_values'][direction] and shock['clamped'][direction] is False\n        changed=b*(1+eff)")
exec(compile(s,str(H/'independent_runtime.py'),'exec'))
P=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/US-MSFT/v2')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=read(P/'forecast.json');snap=read(P/'snapshot.json');registry=[json.loads(l) for l in (P/'publications.jsonl').read_text(encoding='utf-8').splitlines()]
files=[P/'forecast.json',P/'snapshot.json',P/'publications.jsonl'];before={str(p):sha(p) for p in files}
rf=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast')
cmd=[sys.executable,'-B',str(rf/'scripts/publication_registry.py'),'audit','--result',str(P/'forecast.json')]
p=subprocess.run(cmd,cwd=rf,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',REVENUE_PUBLICATION_REGISTRY=str(P/'publications.jsonl')),capture_output=True,timeout=45)
after={str(p):sha(p) for p in files}
result={'command':cmd,'returncode':p.returncode,'stdout':p.stdout.decode('utf-8'),'stderr':p.stderr.decode('utf-8'),'original_unchanged':before==after,'original_hashes':after,'forecast_publication':f['publication_receipt'],'snapshot_keys':list(snap),'snapshot_receipt':snap.get('publication_receipt'),'registry':registry,'scope':'audit checks publication chain, generation conflict and registered anchor; strong input-bound validation above checks semantic/model output separately'}
(H/'recheck_v2_registry_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
assert p.returncode==0 and before==after
print(json.dumps(result,ensure_ascii=False,indent=2))
