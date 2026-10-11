$OutputEncoding=[System.Text.UTF8Encoding]::new($false)
@'
from pathlib import Path
import sys,json,hashlib,importlib.util,tempfile,os,time
root=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root')
source=root/'skills/revenue-forecast-audit/scripts/pool_progress.py';before=hashlib.sha256(source.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('w05_final_tmp_review',source);PP=importlib.util.module_from_spec(spec);sys.modules[spec.name]=PP;spec.loader.exec_module(PP)
base=Path(r'C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-audit-loop-acceptance/independent').resolve()
owned=Path(tempfile.mkdtemp(prefix='w05-audit-final-',dir=base)).resolve()
assert owned.parent==base and owned.name.startswith('w05-audit-final-')
sentinel=owned/'sentinel.txt';sentinel.write_bytes(b'independent initial sentinel');sentinel_sha=hashlib.sha256(sentinel.read_bytes()).hexdigest()
state_path=owned/'state.json';lock_a=lock_b=lock_c=None
try:
 lock_a=PP.StateLock(state_path,timeout=0.2);lock_a.acquire();lock_path=lock_a.path
 age=time.time()-31;os.utime(lock_path,(age,age));lock_b=PP.StateLock(state_path,timeout=0.2)
 first_timeout=None
 try:lock_b.acquire()
 except PP.LockTimeout as exc:first_timeout=str(exc)
 lock_a.release();persistent=lock_path.exists()
 lock_b.acquire();lock_a.release();lock_c=PP.StateLock(state_path,timeout=0.2)
 aba_timeout=None
 try:lock_c.acquire()
 except PP.LockTimeout as exc:aba_timeout=str(exc)
 lock_b.release();t=time.monotonic();lock_c.acquire();recover_ms=round((time.monotonic()-t)*1000,3)
 print(json.dumps({'probe':'LIVE_HOLDER_STALE_STEAL','actual_live_pid':os.getpid(),'setup':'mtime aged 31s while holder A retains kernel lock; no process kill','stale_seconds':PP.DEFAULT_LOCK_STALE,'first_contender_timeout':first_timeout,'release_retains_lock_file':persistent,'repeated_old_release_does_not_unlock_B':aba_timeout,'after_actual_release_acquire_ms':recover_ms,'status':'PASS' if first_timeout and persistent and aba_timeout and recover_ms<200 else 'FAIL'}))
 lock_c.release()
 pool=b'{"schema_version":"audit-pool/1","entities":[{"entity_key":"CN:ONLY","markets":["CN"]}]}'
 state=PP.initial_state(pool,'tmp-seed',b'{"refs":[{"kind":"repo_head","id":"baseline"}]}',b'{"ref":"existing-ledger"}')
 PP.write_state_atomic(state_path,state);sha_before=hashlib.sha256(state_path.read_bytes()).hexdigest()
 observation={'schema_version':PP.OBSERVATION_SCHEMA,'event_id':'tmp-plan','kind':'request_next','recorded_at':'2026-10-11T15:00:00Z'}
 refusal=None
 try:PP.plan_observation(state_path,observation,state_path)
 except ValueError as exc:refusal=str(exc)
 sha_after=hashlib.sha256(state_path.read_bytes()).hexdigest();schema=PP._load_state_file(state_path)['schema_version']
 print(json.dumps({'probe':'PLAN_OVERWRITES_STATE_ALIAS','refusal':refusal,'before_sha256':sha_before,'after_sha256':sha_after,'after_schema':schema,'status':'PASS' if refusal and sha_before==sha_after and schema==PP.STATE_SCHEMA else 'FAIL'}))
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
