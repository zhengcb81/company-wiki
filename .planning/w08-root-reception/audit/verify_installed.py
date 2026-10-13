"""Fresh installed CLI checks with owned inputs and absent->absent cleanup."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent
REPO=Path('C:/Users/郑曾波/Projects/revenue-forecast-audit')
spec=importlib.util.spec_from_file_location('w08_installed_fixtures',REPO/'tests/test_w08_review_evidence.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
destinations=[Path('C:/Users/郑曾波')/p for p in ['.claude/skills/revenue-forecast-audit','.agents/skills/revenue-forecast-audit']]
before={str(p):digest(p) for root in destinations for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
rows=[];start=time.monotonic()
with tempfile.TemporaryDirectory(prefix='installed-smoke-',dir=HERE) as tmp:
    root=Path(tmp)
    for i,destination in enumerate(destinations):
        for case in ['legal','broken_pointer','unpaired_call']:
            owner=root/f'{i}-{case}';builder=module.PackageBuilder(owner);run=builder.build()
            if case=='broken_pointer':builder.payload['numeric_coverage']['verified'][0]['recompute']['locator']='/rows/99/value'
            if case=='unpaired_call':
                p=run/'roles/storage/events.jsonl';events=[json.loads(line) for line in p.read_text(encoding='utf8').splitlines()];events[1]['data']['capture_id']='other';p.write_text('\n'.join(json.dumps(r) for r in events)+'\n',encoding='utf8')
            input_path=owner/'coverage.json';module.write_json(input_path,builder.payload)
            command=[sys.executable,'-B','-X','utf8',str(destination/'scripts/review_protocol.py'),'coverage','--input',str(input_path),'--execution-root',str(run),'--out-root',str(owner/'result')]
            cp=subprocess.run(command,capture_output=True,text=True,encoding='utf8',timeout=30)
            assert cp.returncode==0,cp.stderr
            result=json.loads(cp.stdout);node=json.loads(Path(result['output_file']).read_text(encoding='utf8'))['evidence_reconciliation']
            assert node['quality_status']=='not_evaluated'
            if case=='legal':assert node['numeric_reconciliation']['recompute_rows_observed']==3 and node['events']['storage']['matched_calls']==1
            if case=='broken_pointer':assert 'V1' in node['numeric_reconciliation']['unresolved_recompute_value_ids']
            if case=='unpaired_call':assert node['events']['storage']['matched_calls']==0 and node['unchecked']
            rows.append({'installation':str(destination),'case':case,'exit_code':cp.returncode,'numeric_observed':node['numeric_reconciliation']['recompute_rows_observed'],'matched_calls':node['events']['storage']['matched_calls'],'unchecked':len(node['unchecked'])})
    scratch=str(root)
after={str(p):digest(p) for d in destinations for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert before==after
result={'schema_version':'w08-installed-cli/1','checks':rows,'files_unchanged':before==after,'scratch_restored':not Path(scratch).exists(),'seconds':round(time.monotonic()-start,6),'model_calls':0}
(HERE/'installed-cli.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
