$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
@'
from pathlib import Path
import sys,json,hashlib,importlib.util,tempfile,os,time
root=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop')
source=root/'skills/revenue-forecast-audit/scripts/pool_progress.py';before=hashlib.sha256(source.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('w05_tmp_review',source);PP=importlib.util.module_from_spec(spec);sys.modules[spec.name]=PP;spec.loader.exec_module(PP)
base=Path(r'C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-audit-loop-acceptance/independent').resolve();base.mkdir(parents=True,exist_ok=True);owned=Path(tempfile.mkdtemp(prefix='w05-audit-loop-review-',dir=base)).resolve()
assert owned.parent==base and owned.name.startswith('w05-audit-loop-review-')
sentinel=owned/'sentinel.txt';sentinel.write_bytes(b'independent initial sentinel');sentinel_sha=hashlib.sha256(sentinel.read_bytes()).hexdigest()
state_path=owned/'state.json';lock_a=lock_b=lock_c=None
try:
 lock_a=PP.StateLock(state_path,timeout=0.2);lock_a.acquire();lock_path=lock_a.path
 recorded=json.loads(lock_path.read_text(encoding='utf-8'));age=time.time()-31;os.utime(lock_path,(age,age))
 lock_b=PP.StateLock(state_path,timeout=0.2);lock_b.acquire();both_owned=lock_a._owned and lock_b._owned
 lock_a.release();second_lock_removed=not lock_path.exists();lock_c=PP.StateLock(state_path,timeout=0.2);lock_c.acquire()
 print(json.dumps({'probe':'LIVE_HOLDER_STALE_STEAL','recorded_pid':recorded['pid'],'actual_live_pid':os.getpid(),'default_stale_seconds':PP.DEFAULT_LOCK_STALE,'setup':'mtime aged 31s while holder A stays alive and owns lock; no real wait or crashed process','two_holders_owned':both_owned,'old_release_removed_new_lock':second_lock_removed,'third_holder_acquired_while_second_owned':lock_c._owned and lock_b._owned,'status':'FAIL' if both_owned and second_lock_removed else 'PASS'}))
 lock_c.release();lock_b.release()
 pool=b'{"schema_version":"audit-pool/1","entities":[{"entity_key":"CN:ONLY","markets":["CN"]}]}'
 state=PP.initial_state(pool,'tmp-seed',b'{"refs":[{"kind":"repo_head","id":"baseline"}]}',b'{"ref":"existing-ledger"}')
 PP.write_state_atomic(state_path,state);sha_before=hashlib.sha256(state_path.read_bytes()).hexdigest()
 observation={'schema_version':PP.OBSERVATION_SCHEMA,'event_id':'tmp-plan','kind':'request_next','recorded_at':'2026-10-11T15:00:00Z'}
 result=PP.plan_observation(state_path,observation,state_path)
 after_schema=json.loads(state_path.read_bytes())['schema_version'];reload_error=None
 try:PP._load_state_file(state_path)
 except ValueError as exc:reload_error=str(exc)
 print(json.dumps({'probe':'PLAN_OVERWRITES_STATE_ALIAS','expected':'reject --out equal to state; state bytes must stay unchanged','returned':result,'before_sha256':sha_before,'after_sha256':hashlib.sha256(state_path.read_bytes()).hexdigest(),'after_schema':after_schema,'reload_error':reload_error,'status':'FAIL' if after_schema==PP.PLAN_SCHEMA else 'PASS'}))
 assert hashlib.sha256(sentinel.read_bytes()).hexdigest()==sentinel_sha
 print(json.dumps({'phase':'sentinel_integrity','unchanged':True,'sha256':sentinel_sha}))
finally:
 for lock in [lock_c,lock_b,lock_a]:
  if lock is not None:lock.release()
 for path in [state_path,Path(str(state_path)+PP.LOCK_SUFFIX),sentinel]:
  assert path.resolve().parent==owned
  if path.exists():path.unlink()
 remain=list(owned.iterdir());assert not remain,[p.name for p in remain]
 owned.rmdir()
print(json.dumps({'phase':'tmp_cleanup','owned_path':str(owned),'removed':not owned.exists(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==before,'network_calls':0,'provider_calls':0,'producer_writes':0,'tmp_probe_count':2}))
'@ | python -X utf8 -B -
