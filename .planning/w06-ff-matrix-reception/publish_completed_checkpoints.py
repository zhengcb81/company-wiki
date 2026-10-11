"""Commit completed receipts/plans only, leaving active producer evidence untouched."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08'
W06 = BASE / 'phase6/w06_parallel_verification_2026-10-11'
E = W06 / 'evidence/root-ff-matrix-acceptance'
assert not (E / 'completed-checkpoints-publication.json').exists()
pub = E / 'source-publication/publication.json'
r = json.loads(pub.read_text(encoding='utf-8'))
r['ci'] = {'id':38148948361, 'status':'completed', 'conclusion':'success',
           'head_sha':r['main_commit'], 'url':'https://github.com/zhengcb81/company-wiki/actions/runs/38148948361'}
pub.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
path = W06 / 'ROOT-reception-status.md'
raw = path.read_bytes().replace('精确CI38148948361尚在运行'.encode(), '精确CI38148948361已成功'.encode())
path.write_bytes(raw)
paths = []
for folder in [ROOT / '.planning/w06-ff-matrix-reception', ROOT / '.planning/w04-root-novelty-recall', E]:
    paths += [p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
plan = ROOT / '.planning/w06-cross-period-acquisition'
paths += [p for p in plan.iterdir() if p.is_file()]
paths += [p for p in (plan / 'cutoff-diagnosis').rglob('*') if p.is_file()]
paths += [W06 / 'ROOT-reception-status.md']
for group in [BASE, ROOT / 'docs/plans/narrative-evidence-pilot-2026-09-26',
              BASE / 'phase6/w05_parallel_common_roots_2026-10-11', W06]:
    paths += [group / name for name in ('task_plan.md','findings.md','progress.md')]
names = sorted({p.relative_to(ROOT).as_posix() for p in paths})
assert all('cutoff-implementation/' not in name and 'phase2-real-recall/' not in name for name in names)

def run(*args):
    return subprocess.check_output(args,cwd=ROOT,text=True,encoding='utf-8',errors='replace').strip()

assert run('git','branch','--show-current') == 'master'
assert run('git','rev-parse','HEAD') == '8bd233443c7ef6d75aeb9f09cc62edcc10316b5e'
assert not run('git','diff','--cached','--name-only')
# The complete evidence inventory exceeds Windows CreateProcess argv limits.
# Feed exact NUL-delimited paths through Git's native pathspec interface.
subprocess.run(['git','add','--pathspec-from-file=-','--pathspec-file-nul'],
               input=b''.join(name.encode('utf-8')+b'\0' for name in names),cwd=ROOT,check=True)
staged = set(run('git','diff','--cached','--name-only').splitlines())
assert staged <= set(names) and staged
subprocess.run(['git','commit','-m','docs: publish accepted W06 source and tooling with honest real-data gaps'],cwd=ROOT,check=True)
commit = run('git','rev-parse','HEAD')
subprocess.run(['git','push','origin','master'],cwd=ROOT,check=True)
record = {'schema':'root-completed-checkpoints-publication/1','commit':commit,
          'normal_hooks':True,'staged_files':len(staged),
          'source_and_tool_exact_ci':'success','active_cutoff_evidence_excluded':True,
          'w04_real_native_result':'FAIL_CRITICAL_RECALL preserved; phase2 active',
          'whole_pwf_complete':False}
(E / 'completed-checkpoints-publication.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record),flush=True)
