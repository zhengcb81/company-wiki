import json
from pathlib import Path
import subprocess

ROOT=Path('C:/Users/郑曾波/Projects/company-wiki')
PLAN=Path(__file__).resolve().parent
W07=ROOT/'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w07_parallel_quality_2026-10-11'
dispatch=json.loads((W07/'dispatch.json').read_text(encoding='utf-8'))
dispatch['state']='PARTIALLY_ACCEPTED'
publication=json.loads((PLAN/'publication.json').read_text(encoding='utf-8'))
for lane in dispatch['lanes']:
    if lane['lane']=='W07-AUDIT-ANALYST':
        lane['status']='ACCEPTED_MERGED_INSTALLED'
        lane['accepted_main_head']=publication['final_main_head']
        lane['root_evidence']='.planning/w07-audit-analyst-reception/publication.json'
(W07/'dispatch.json').write_text(json.dumps(dispatch,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
selected=[p.relative_to(ROOT).as_posix() for p in PLAN.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [p.relative_to(ROOT).as_posix() for p in (W07/'README.md',W07/'task_plan.md',W07/'findings.md',W07/'progress.md',W07/'dispatch.json',W07.parent/'w06_parallel_verification_2026-10-11/ROOT-reception-status.md')]
p=subprocess.run(['git','add','--pathspec-from-file=-','--pathspec-file-nul'],cwd=ROOT,input=b''.join(s.encode()+b'\0' for s in selected),capture_output=True)
assert p.returncode==0,p.stderr.decode(errors='replace')
p=subprocess.run(['git','commit','-m','docs(pwf): record W07 analyst reception, common fixes and skill installation'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
print(p.stdout)
print(p.stderr)
assert p.returncode==0
print(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
