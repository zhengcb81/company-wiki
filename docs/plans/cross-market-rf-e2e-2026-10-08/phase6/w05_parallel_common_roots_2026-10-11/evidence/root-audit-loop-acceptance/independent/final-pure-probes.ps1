$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
@'
import sys,json,hashlib,importlib.util,itertools
from pathlib import Path
root=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root')
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
  kw=dict(run_id=r,attempt='initial',role=role,status='completed',conclusion='PASS');kw.update(extra)
  if refs: kw['report_ref']=r+'/'+role+'.json'
  s=fold(s,'review_status',**kw)
 return s
def finish(s,r):
 s=seal(start(s,r),r);s=reviews(s,r);s=fold(s,'expert_status',run_id=r,attempt='initial',findings=[],refs=[r+'/expert.json']);return fold(s,'advance_round')
print(json.dumps({'phase':'input_sha','files':sha},ensure_ascii=False))
s=reviews(seal(start(new())),refs=False);s=fold(s,'expert_status',run_id='run-new',attempt='initial',findings=[],refs=['run-new/expert.json']);before_clean=PP._company_clean(s,[]);s=fold(s,'advance_round')
print(json.dumps({'probe':'MISSING_REPORT_REFS','expected':'not_clean','actual_clean':before_clean,'streak':s['clean']['streak'],'evidence_refs':s['clean']['evidence_refs'],'status':'FAIL' if s['clean']['streak']==1 else 'PASS'}))
s=start(new());old_digest=s['current_run']['versions_digest'];s=fold(s,'version_change',version_kind='code',refs=['repo-head-v2'],reason='behavior changed');s=seal(s);s=reviews(s,r='run-old',versions_digest=old_digest);ignored=all(s['review_conclusions'][r] is None for r in PP.REVIEW_ROLES)
s=reviews(s,attempt='reviewer-2',execution_attempt='initial');stored=list(s['review_conclusions'].values());accepted=all(x and x['attempt']=='reviewer-2' and x['execution_attempt']=='initial' and x['versions_digest']==old_digest for x in stored);s=fold(s,'expert_status',run_id='run-new',attempt='initial',findings=[],refs=['run-new/expert.json']);action=s['next_action'];before_clean=PP._company_clean(s,[]);s=fold(s,'advance_round')
print(json.dumps({'probe':'STALE_RUN_AND_VERSION_REVIEWS','old_run_ignored':ignored,'reviewer_retry_correctly_bound':accepted,'old_digest':old_digest,'new_digest':s['effective_versions']['digest'],'actual_clean':before_clean,'before_action':action,'streak':s['clean']['streak'],'stored':stored,'status':'PASS' if ignored and accepted and not before_clean[0] and action['action']=='rerun_same_company_after_fix' and s['clean']['streak']==0 else 'FAIL'}))
s=fold(new(),'charge_unknown',call_id='maybe-posted',ref='logs/possible-post');first=s['next_action'];s=fold(s,'charge_reconciled',call_id='maybe-posted',outcome='unknown',evidence_ref='no-provider-reconciliation-available');unknown_action=s['next_action'];s=fold(s,'charge_reconciled',call_id='maybe-posted',outcome='known',cost_usd=None,evidence_ref='no-cost-value');known_action=s['next_action']
for i in range(3):s=finish(s,f'unknown-cost-{i}')
print(json.dumps({'probe':'UNRESOLVED_UNKNOWN_CHARGE','before_action':first,'unknown_action':unknown_action,'known_null_action':known_action,'after_three_rounds':s['next_action'],'streak':s['clean']['streak'],'entry':s['possibly_paid_invocation_refs'][0],'pending_reconciles':PP._stop_criteria_facts(s)['pending_reconciles'],'status':'PASS' if unknown_action['action']==known_action['action']==s['next_action']['action']=='reconcile_possible_charge' and s['clean']['streak']==0 else 'FAIL'}))
s=fold(new(),'finding',run_id='legacy-run',issue_id='OLD1',severity='P1',substantive=True,entity_key='CN:OLD-OUTSIDE-POOL')
for i in range(3):s=finish(s,f'clean-{i}')
major_action=s['next_action'];s=fold(s,'fix_applied',refs=['legacy-run::OLD1'],changes=[],retest_required=True);action_before=s['next_action'];s=fold(s,'retest_done',refs=['legacy-run::OLD1'])
print(json.dumps({'probe':'RETEST_WITHOUT_EVIDENCE','streak':s['clean']['streak'],'unfixed_major_after_three_clean':major_action,'before_action':action_before,'after_action':s['next_action'],'obligation':s['required_retests'][0],'status':'PASS' if major_action['action']==action_before['action']==s['next_action']['action']=='resume_remediation' and not s['required_retests'][0]['done'] else 'FAIL'}))
s=new(3)
for i in range(2):s=finish(s,f'tail-{i}')
s=reviews(seal(start(s,'tail-last'),'tail-last'),'tail-last');s=fold(s,'expert_status',run_id='tail-last',attempt='initial',findings=[],refs=['tail-last/expert.json']);before={'action':s['next_action'],'closed':s['history']['companies_closed'],'streak':s['clean']['streak'],'clean_check':PP._company_clean(s,[])};s=fold(s,'advance_round')
print(json.dumps({'probe':'LAST_COMPANY_CLOSE_SUGGESTION','before_manual_advance':before,'after_manual_advance':{'stage':s['stage'],'action':s['next_action'],'closed':s['history']['companies_closed'],'streak':s['clean']['streak']},'status':'LIMITATION' if before['action']['action']=='no_action' else 'PASS'}))
s=new(2)
for i in range(2):s=finish(s,f'short-pool-{i}')
print(json.dumps({'probe':'POOL_EXHAUSTED_BEFORE_CRITERIA','stage':s['stage'],'action':s['next_action'],'streak':s['clean']['streak'],'status':'PASS' if s['next_action']['action']=='no_action' and s['clean']['streak']==2 else 'FAIL'}))
print(json.dumps({'phase':'input_integrity_after','unchanged':all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in sha.items()),'network_calls':0,'provider_calls':0,'product_writes':0,'pure_probe_count':6}))
'@ | python -X utf8 -B -
