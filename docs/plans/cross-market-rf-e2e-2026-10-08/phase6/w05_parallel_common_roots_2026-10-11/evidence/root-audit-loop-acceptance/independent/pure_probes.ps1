$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
@'
import sys,json,hashlib,importlib.util,itertools
from pathlib import Path
root=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop')
files=['AGENTS.md','skills/revenue-forecast-audit/SKILL.md','docs/handoffs/w05-audit-loop/handoff.md','docs/handoffs/w05-audit-loop/input/construction_card.md','skills/revenue-forecast-audit/references/pool-progress-contract.md','skills/revenue-forecast-audit/scripts/pool_progress.py','tests/test_pool_progress.py','tests/test_pool_progress_cli.py','skills/revenue-forecast-audit/scripts/audit_run.py']
sha={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}
spec=importlib.util.spec_from_file_location('w05_independent_review',root/files[5]);PP=importlib.util.module_from_spec(spec);sys.modules[spec.name]=PP;spec.loader.exec_module(PP)
seq=itertools.count(1)
def obs(kind,**kw): return dict(schema_version=PP.OBSERVATION_SCHEMA,event_id=f'independent-{next(seq)}',recorded_at='2026-10-11T15:00:00Z',kind=kind,**kw)
def fold(s,kind,**kw): return PP.reduce_progress(s,obs(kind,**kw))['new_state']
def new(n=6):
 pool=json.dumps({'schema_version':'audit-pool/1','entities':[{'entity_key':f'CN:CASE{i}','markets':['CN']} for i in range(n)]}).encode()
 return PP.initial_state(pool,'independent-seed',b'{"refs":[{"kind":"repo_head","id":"baseline-v1"}]}',b'{"ref":"existing-ledger"}')
def start(s,r='run-new'):
 return fold(s,'run_started',entity_key=PP._current_entity(s),run_id=r,attempt='initial')
def seal(s,r='run-new'):
 return fold(s,'executor_status',run_id=r,attempt='initial',status='sealed',executor_completion='verified',refs=[r+'/manifest.json'])
def reviews(s,r='run-new',refs=True,**extra):
 for role in PP.REVIEW_ROLES:
  kw=dict(run_id=r,attempt='initial',role=role,status='completed',conclusion='PASS',**extra)
  if refs: kw['report_ref']=r+'/'+role+'.json'
  s=fold(s,'review_status',**kw)
 return s
def finish(s,r):
 s=seal(start(s,r),r);s=reviews(s,r);s=fold(s,'expert_status',run_id=r,attempt='initial',findings=[],refs=[r+'/expert.json']);return fold(s,'advance_round')
print(json.dumps({'phase':'input_sha','files':sha},ensure_ascii=False))
s=reviews(seal(start(new())),refs=False);s=fold(s,'expert_status',run_id='run-new',findings=[]);before_clean=PP._company_clean(s,[]);s=fold(s,'advance_round')
print(json.dumps({'probe':'MISSING_REPORT_REFS','expected':'not_clean','actual_clean':before_clean,'streak':s['clean']['streak'],'evidence_refs':s['clean']['evidence_refs'],'status':'FAIL' if s['clean']['streak']==1 else 'PASS'}))
s=start(new());old_digest=s['effective_versions']['digest'];s=fold(s,'version_change',version_kind='code',refs=['repo-head-v2'],reason='behavior changed');s=seal(s);s=reviews(s,r='run-old',versions_digest=old_digest);stored=[{'role':r,**s['review_conclusions'][r],'observed_run':s['role_observations'][r]['run_id']} for r in PP.REVIEW_ROLES];before_clean=PP._company_clean(s,[]);s=fold(s,'expert_status',run_id='run-new',findings=[]);s=fold(s,'advance_round')
print(json.dumps({'probe':'STALE_RUN_AND_VERSION_REVIEWS','expected':'old run and old version reviews cannot count for new run','old_digest':old_digest,'new_digest':s['effective_versions']['digest'],'actual_clean':before_clean,'streak':s['clean']['streak'],'stored':stored,'status':'FAIL' if s['clean']['streak']==1 else 'PASS'}))
s=fold(new(),'charge_unknown',call_id='maybe-posted',ref='logs/possible-post');first=s['next_action'];s=fold(s,'charge_reconciled',call_id='maybe-posted',outcome='unknown',evidence_ref='no-provider-reconciliation-available')
print(json.dumps({'probe':'UNRESOLVED_UNKNOWN_CHARGE','before_action':first,'after_action':s['next_action'],'entry':s['possibly_paid_invocation_refs'][0],'pending_reconciles':PP._stop_criteria_facts(s)['pending_reconciles'],'expected':'remain unresolved; never infer a safe executor redispatch from unknown reconciliation','status':'FAIL' if s['next_action']['action']=='dispatch_executor' else 'PASS'}))
s=fold(new(),'finding',run_id='legacy-run',issue_id='OLD1',severity='P1',substantive=True,entity_key='CN:OLD-OUTSIDE-POOL');s=fold(s,'fix_applied',refs=['legacy-run::OLD1'],changes=[],retest_required=True)
for i in range(3):s=finish(s,f'clean-{i}')
action_before=s['next_action'];s=fold(s,'retest_done',refs=['legacy-run::OLD1'])
print(json.dumps({'probe':'RETEST_WITHOUT_EVIDENCE','before_action':action_before,'after_action':s['next_action'],'obligation':s['required_retests'][0],'expected':'missing evidence must not discharge historical retest','status':'FAIL' if s['next_action']['action']=='campaign_sample_criteria_met' else 'PASS'}))
s=new(3)
for i in range(2):s=finish(s,f'tail-{i}')
s=reviews(seal(start(s,'tail-last'),'tail-last'),'tail-last');s=fold(s,'expert_status',run_id='tail-last',findings=[],refs=['tail-last/expert.json']);before={'action':s['next_action'],'closed':s['history']['companies_closed'],'streak':s['clean']['streak'],'clean_check':PP._company_clean(s,[])};s=fold(s,'advance_round')
print(json.dumps({'probe':'LAST_COMPANY_CLOSE_SUGGESTION','before_manual_advance':before,'after_manual_advance':{'stage':s['stage'],'action':s['next_action'],'closed':s['history']['companies_closed'],'streak':s['clean']['streak']},'status':'LIMITATION' if before['action']['action']=='no_action' else 'PASS'}))
s=new(2)
for i in range(2):s=finish(s,f'short-pool-{i}')
print(json.dumps({'probe':'POOL_EXHAUSTED_BEFORE_CRITERIA','stage':s['stage'],'action':s['next_action'],'streak':s['clean']['streak'],'status':'PASS' if s['next_action']['action']=='no_action' and s['clean']['streak']==2 else 'FAIL'}))
print(json.dumps({'phase':'input_integrity_after','unchanged':all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in sha.items()),'network_calls':0,'provider_calls':0,'product_writes':0,'pure_probe_count':6}))
'@ | python -X utf8 -B -
