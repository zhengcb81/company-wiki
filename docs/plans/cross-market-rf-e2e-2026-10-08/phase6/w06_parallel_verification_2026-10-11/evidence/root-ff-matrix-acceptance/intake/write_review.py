from pathlib import Path
import json
import hashlib

HERE = Path(__file__).resolve().parent
load=lambda name:json.loads((HERE/name).read_text(encoding='utf-8'))
git=load('git-intake.json')
sha=load('sha-verification.json')
probes=load('independent-counterexamples.json')
unit=load('unit-replay.json')
delivery=load('delivery-evidence-review.json')

findings=[
 {'id':'FFI-P1-ISOLATION','priority':'P1','component':'test-harness','root_cause':'No shared hermetic child environment; secret file is hashed despite stat-only declaration. Binding ignores synthetic supplied env.',
  'source_locations':['run.py:56-89','run.py:120-137','report.py:27-28','cli_main.py:53-88'],
  'probes':['FFI-SECRET-HASH','FFI-ENV-LEAK'],'scope_limit':'Synthetic fake key/environment only; no evidence actual delivered run read or leaked real secret, and no production network send was observed.',
  'root_action':'One platform-startup allowlist plus synthetic mandatory env for every child; secret path stat-only; scratch profile/temp; test-only network refusal/translation spy.'},
 {'id':'FFI-P1-RESULT-EVIDENCE','priority':'P1','component':'test-harness','root_cause':'Case predicates and oracle accept self-declared booleans, generic errors, unknown counters as zero and incorrect quarter/reuse status.',
  'source_locations':['matrix_cases.py:91-109','matrix_cases.py:162-183','matrix_cases.py:257-261','matrix_cases.py:283-295','matrix_cases.py:399-405','oracle.py:49-103','cli_main.py:142-145','cli_main.py:234-237'],
  'probes':['FFI-WRONG-QUARTER','FFI-CUTOFF-UNRELATED-ERROR','FFI-MISSING-REUSE','FFI-UNKNOWN-ZERO','FFI-EMPTY-UNBOUND-ORACLE','FFI-ORACLE-NULL-AS-ZERO','CONTROL-QUARTER-REJECTED'],
  'scope_limit':'Pure helper synthetic responses prove harness false PASS, not actual FF/CWP/ET product accepts those responses.',
  'root_action':'Shared typed outcome predicates and mandatory coverage; bind exact request/counters/real fresh reader proof. Missing data UNRESOLVED, no second identity/authorization layer.'},
 {'id':'FFI-P1-OWNERSHIP','priority':'P1','component':'test-harness','root_cause':'CLI unconditionally overwrites sentinel and deletes existing scratch but reports restored based only on its own rewritten sentinel.',
  'source_locations':['cli_main.py:128-140','cli_main.py:166-185'],
  'probes':['FFI-CLI-BASELINE-DELETION'],
  'scope_limit':'Only an intake-owned synthetic preexisting baseline was deleted; no production directory/raw was touched.',
  'root_action':'Reject unsafe/nonempty or overlapping roots before mutation, or use fresh owned child; immutable before baseline and finally cleanup only generated paths.'},
 {'id':'FFI-P1-DEADLINE','priority':'P1','component':'test-harness','root_cause':'No active batch absolute deadline; per-case budget produces WARN only. Binding/init/seed and repeated FF calls bypass batch accounting.',
  'source_locations':['run.py:45-46','run.py:177-182','cli_main.py:147-164','cli_main.py:244-249'],
  'probes':['FFI-CLI-UNBOUND-BUDGET'],
  'scope_limit':'Clock simulated; did not run an expensive 220-second process or real provider.',
  'root_action':'One batch/case deadline covers all spawn and phases, partial output on timeout, terminate/reap active processes, no larger budget to hide issue.'},
 {'id':'FFI-P1-COVERAGE','priority':'P1','component':'acceptance-test-coverage','root_cause':'Required matrix missing; generic fixture provider mistaken for actual provider tool-routing proof; cross-period original failure moved away instead of remaining named failing regression.',
  'source_locations':['cli_main.py:95-115','fixture_builder.py:202-228','fixture_provider_adapter.py:39-51','docs/handoffs/w06-ff-matrix/handoff.json:findings.W06FF-01'],
  'probes':[],'scope_limit':'Existing product cross-period bug is already reported by worker, not newly independently reproduced by live product CLI here. Dayu unchanged; generic ensure/import useful but narrower than route proof.',
  'root_action':'Keep original cross-period FAIL as PARTIAL pending ROOT product repair; add missing required error/market/doc controls, actual configured provider-boundary route proof, no Dayu writes/provider addition.'},
 {'id':'FFI-P2-HANDOFF','priority':'P2','component':'handoff','root_cause':'Post-commit final PWF states not included in manifest; stale next step/unchecked items; missing quantitative scratch peak and RED chronology scope.',
  'source_locations':['.planning/w06-ff-matrix/task_plan.md','.planning/w06-ff-matrix/progress.md','docs/handoffs/w06-ff-matrix/handoff.json'],
  'probes':[],'root_action':'ROOT preserve original SHA snapshot, integrate understood final status changes, report actual 136567 retained bytes and unknown peak honestly; no full suite repeat.'},
]
result={
 'schema_version':'w06-root-independent-review/1','lane':'W06-FF-MATRIX','date':'2026-10-11',
 'verdict':'PARTIAL_REPAIR_REQUIRED','complete_accepted':False,'delivery_received':True,
 'workdir':'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix',
 'branch':git['worker_branch']['stdout'].strip(),'base_commit':git['canonical_head']['stdout'].strip(),
 'feature_commit':'8dd00e207e1465095f37ff720bc165b541bdd093','delivery_head':git['worker_head']['stdout'].strip(),
 'distance':{'canonical_main_only':0,'delivery_only':2},'changed_paths':delivery['changed_files_count'],
 'worker_dirty':git['worker_status']['stdout'].splitlines(),'canonical_dirty':git['canonical_status']['stdout'].splitlines(),
 'sha_rows':{'checked':len(sha['rows']),'match':sum(r['sha_match'] and r['bytes_match'] for r in sha['rows']),
             'mismatch':[r['path'] for r in sha['rows'] if not r['sha_match']]},
 'producer_sha_rows':{'checked':len(delivery['producer_sha_verification']),'matched':sum(r['match'] for r in delivery['producer_sha_verification'])},
 'unit_replay':unit,'independent_probes':{'count':len(probes['probes']),'fail':sum(r['verdict']=='FAIL' for r in probes['probes']),'positive_controls_pass':sum(r['verdict']=='PASS' for r in probes['probes']),'file':'independent-counterexamples.json'},
 'findings':findings,'delivery_retained_bytes':delivery['retained_bytes'],
 'test_restore':{'pure_probe_scratch_restored':probes['scratch_restored'],'unit_scratch_restored':unit['scratch_restored']},
 'cost':{'real_provider_calls':0,'model_calls':0,'paid_usd':0,'unknown_charge':None},
 'did_not_run':['original complete runner (isolation/ownership flaws)', 'actual provider/network/LLM', 'whole legacy suite', 'production lake scan/hash/copy'],
 'unchanged':['FF/ET/CWP products and shared PWF','worker Git/main/install','Dayu and IQS','real secret bytes','production raw and configuration'],
 'root_next_action':'Create isolated FF ROOT integration, preserve frozen negatives + positive controls, TDD shared hermetic env/ownership/deadline/evidence predicates; keep cross-period original product FAIL as PARTIAL; final real three-layer offline chain and matrix using explicit final CWP/ET roots, then independent final accept/normal commit/merge/push.',
}
(HERE/'independent-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
plan=HERE/'task_plan.md'
text=plan.read_text(encoding='utf-8').replace('- [ ] C: report MD/JSON, source manifest and explicit ROOT next action.','- [x] C: report MD/JSON, source manifest and explicit ROOT next action.').replace('Write final independent review and manifest; ROOT must repair shared harness causes before COMPLETE/merge acceptance.','Intake complete. ROOT must repair shared harness causes before COMPLETE/merge acceptance; see independent-review.md/json.')
plan.write_text(text,encoding='utf-8')
manifest=[]
for p in sorted(HERE.iterdir()):
    if p.is_file() and p.name!='manifest.json':
        b=p.read_bytes();manifest.append({'path':p.name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
(HERE/'manifest.json').write_text(json.dumps({'schema_version':'w06-root-intake-manifest/1','lane':'W06-FF-MATRIX','files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'verdict':result['verdict'],'unit_pass':unit['exit_code']==0,'probe_fail':result['independent_probes']['fail'],'files':len(manifest),'retained_intake_bytes':sum(x['bytes'] for x in manifest)},ensure_ascii=False))
