import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

ROOT=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception')
MAIN=Path('C:/Users/郑曾波/Projects/revenue-forecast-audit')
PLAN=Path(__file__).resolve().parent
VER=PLAN/'verification-release'
assert not (PLAN/'publication.json').exists()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
def run(args, cwd=ROOT):
    p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
    if p.returncode:
        raise RuntimeError(f'{args}: {p.stdout}\n{p.stderr}')
    return p.stdout.strip()
for label in ('focused','e2e','skill-structure'):
    assert json.loads((VER/(label+'.json')).read_text(encoding='utf-8'))['exit_code']==0
assert run(['git','branch','--show-current'],MAIN)=='main'
assert run(['git','status','--porcelain'],MAIN)==''
assert run(['git','rev-parse','HEAD'],MAIN)=='9cd5ff8a2c8f9c1726c4047785164e3263673614'

handoff=ROOT/'docs/handoffs/root-w07-audit-analyst-reception'
assert not handoff.exists()
handoff.mkdir(parents=True)
for source,name in ((PLAN/'independent-review.md','independent-review.md'),
                    (PLAN/'red-summary.json','root-red.json'),
                    (VER/'focused.json','focused.json'),
                    (VER/'e2e/analyst-risk-e2e-report.json','e2e-report.json')):
    shutil.copyfile(source,handoff/name)
(handoff/'handoff.md').write_text('''# ROOT W07-AUDIT-ANALYST reception

Accepted after root-cause repairs, preserving author commits 34b5c8ee/e3206880.
Independent review found scoped-reference, date and actual-evidence defects; ROOT added common native reference indexes and actual value/period/scope bindings. Review's remaining four categories are covered by FinalScopeRegressionTests and repaired; no claim of a third independent review.
Final concentrated suite: 90 passed + 4 subtests (2.30s). Original real-CLI E2E: 13/13 COMPLETE (1.4392s), scratch restored absent. Skill structure valid. Existing assertions unchanged; synthetic helper only fills its formerly dangling default claim/output definitions.
Connected fourth reviewer documentation. Report-only diagnostics: no added download/LLM/identity/hash/approval/forecast gate. Source truth false; economic reasonableness not_evaluated. No paid calls. This does not complete real-company G4/G5 research.
Audit has no remote/CI. ROOT normally commits/fast-forwards main, synchronizes the three changed package files to .claude/.agents and records installed CLI and 28-file-per-copy verification in publication.json.
''',encoding='utf-8',newline='\n')
changed=[
'skills/revenue-forecast-audit/scripts/analyst_risk_audit.py',
'skills/revenue-forecast-audit/references/analyst-risk-audit.md',
'skills/revenue-forecast-audit/references/review-analyst.md',
'tests/test_w07_analyst_risk_audit.py','tests/test_root_w07_analyst_scope.py',
]
changed += [p.relative_to(ROOT).as_posix() for p in handoff.rglob('*') if p.is_file()]
p=subprocess.run(['git','add','--pathspec-from-file=-','--pathspec-file-nul'],cwd=ROOT,input=b''.join(s.encode()+b'\0' for s in changed),capture_output=True)
assert p.returncode==0, p.stderr.decode('utf-8',errors='replace')
print(run(['git','commit','-m','fix(audit): bind analyst diagnostics to native scopes and actual evidence']))
implementation=run(['git','rev-parse','HEAD'])
print(run(['git','merge','--ff-only','codex/root-w07-audit-analyst-reception'],MAIN))
installed=json.loads(run(['python','-B','tools/sync_skill.py'],MAIN))
expected={'scripts/analyst_risk_audit.py','references/analyst-risk-audit.md','references/review-analyst.md'}
assert all(set(row['changed'])==expected for row in installed['installations'])
check=json.loads(run(['python','-B','tools/sync_skill.py','--check'],MAIN))
assert all(row['status']=='MATCH' and row['files']==28 for row in check['installations'])
scratch=ROOT/'.tmp'/('install-w07-'+uuid.uuid4().hex[:8])
assert scratch.resolve().is_relative_to(ROOT.resolve()) and not scratch.exists()
probes=[]
try:
    for row in installed['installations']:
        start=time.monotonic()
        script=Path(row['destination'])/'scripts/analyst_risk_audit.py'
        data=ROOT/'.planning/w07-audit-analyst-quality/input'
        receipt=json.loads(run(['python','-B',str(script),'--input',str(data/'native-input.json'),
                               '--forecast',str(data/'native-draft.json'),'--support',str(data/'native-support.json'),
                               '--out-root',str(scratch)]))
        report=json.loads(Path(receipt['output_file']).read_text(encoding='utf-8'))
        assert len(report['checkpoints'])==8
        assert report['source_truth_verified'] is False and report['economic_reasonableness']=='not_evaluated'
        assert report['actual_input_refs']['wape'] is None
        assert all('native_evidence_refs' in f for f in report['findings'])
        probes.append({'destination':row['destination'],'seconds':time.monotonic()-start,'checkpoint_count':8,'success':True})
finally:
    if scratch.exists():
        assert scratch.resolve().is_relative_to(ROOT.resolve())
        shutil.rmtree(scratch)
assert not scratch.exists()
record={'status':'ACCEPTED_MERGED_INSTALLED','implementation_commit':implementation,'main_head':run(['git','rev-parse','HEAD'],MAIN),
        'author_commits':['34b5c8ee605059be7639080a03502026ebce3410','e3206880224f7fa97d3923cb70044a6956f7d2f4'],
        'focused':{'passed':90,'subtests_passed':4,'seconds':2.30},'e2e_checks':13,
        'installation':installed,'installation_check':check,'installed_cli':probes,'scratch_restored':True,
        'real_provider_calls':0,'real_llm_calls':0,'source_truth_verified':False,'economic_reasonableness':'not_evaluated',
        'remote':run(['git','remote'],MAIN),'ci':'not_configured_no_remote'}
(PLAN/'publication.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
(MAIN/'docs/handoffs/root-w07-audit-analyst-reception/publication.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
run(['git','add','docs/handoffs/root-w07-audit-analyst-reception/publication.json'],MAIN)
print(run(['git','commit','-m','docs(audit): record W07 main reception and installed CLI verification'],MAIN))
record['final_main_head']=run(['git','rev-parse','HEAD'],MAIN)
record['final_main_clean']=run(['git','status','--porcelain'],MAIN)==''
(PLAN/'publication.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
