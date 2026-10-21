from __future__ import annotations
import hashlib, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

PLAN = Path(__file__).resolve().parent
TREE = PLAN.parents[2]
MOTHER = Path('C:/Users/郑曾波/Projects/company-wiki')
PYTHON = MOTHER / '.venv/Scripts/python.exe'
LABEL = sys.argv[1]
SELECTIONS = {
 'red-original': ['tests/contract/test_automation_store_boundary.py', 'tests/contract/test_narrative_transport_cli.py'],
 'red-target': ['tests/unit/test_terminal_pin_target.py'],
 'red-projections': ['tests/unit/test_automation_projection_columns.py'],
 'green': ['tests/unit/test_narrative_golden_evolution.py', 'tests/unit/test_terminal_pin_target.py', 'tests/contract/test_automation_store_boundary.py', 'tests/contract/test_narrative_transport_cli.py', 'tests/unit/test_automation_projection_columns.py', 'tests/unit/test_automation_migrations.py::test_wal_connection_retry_yields_until_concurrent_initializer_can_finish', 'tests/unit/test_automation_migrations.py::test_wal_connection_permanent_lock_stops_at_deadline_and_nonbusy_fails_immediately', 'tests/unit/test_terminal_narrative_receipts.py', 'tests/integration/test_terminal_narrative_receipts.py', 'tests/unit/du11_paid_response/test_paid_response.py', 'tests/unit/test_narrative_transport_contracts.py', 'tests/unit/test_narrative_current_read.py', 'tests/unit/test_narrative_transport_cli_output.py', 'tests/unit/test_transcript_boundary_versions.py'],
}
SELECTIONS['green-final'] = SELECTIONS['green']
SELECTIONS['red-run-readers'] = ['tests/unit/test_automation_projection_columns.py::test_reservation_readers_ignore_added_internal_column']
SELECTIONS['green-reviewed'] = SELECTIONS['green'] + ['tests/unit/test_narrative_run_store.py', 'tests/unit/test_narrative_run_ownership.py', 'tests/integration/test_narrative_run_budget.py']
if LABEL not in SELECTIONS: raise ValueError(LABEL)
OUT = MOTHER / '.planning/r1ctfix/logs' / LABEL
OUT.mkdir(parents=True, exist_ok=False)
TEMP = MOTHER / '.planning/r1ctfix' / {'red-original':'r0','red-projections':'r1','red-target':'t0','green':'g0','green-final':'g1','red-run-readers':'r2','green-reviewed':'g2'}[LABEL]
if TEMP.exists(): raise RuntimeError('Preserve existing owned scratch: '+str(TEMP))
TEMP.mkdir(parents=True)
assert len(str(TEMP)) <= 60

def utc(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=TREE,text=True).strip()
tracked_sources = subprocess.check_output(['git','ls-files','-z','companies','sectors','themes'],cwd=TREE).decode().split('\0')
tracked_sources = [p for p in tracked_sources if p and (TREE/p).is_file()]
protected = [TREE/'config/source_catalog.yaml', MOTHER/'config/source_catalog.yaml'] + [TREE/p for p in tracked_sources]
before = {str(p):sha(p) for p in protected}
revision_names = set(git('diff','--name-only','--','src','tests').splitlines())
revision_names.update(git('ls-files','--others','--exclude-standard','--','tests').splitlines())
revision_names.update(str(p.relative_to(TREE)).replace('\\','/') for p in (TREE/'tests/fixtures/narrative_transport_v1').glob('*.json'))
tested_files = sorted((TREE/p for p in revision_names if p and (TREE/p).is_file()), key=str)
tested_before = {str(p.relative_to(TREE)):sha(p) for p in tested_files}
env = os.environ.copy()
for name in ('OPENAI_API_KEY','DEEPSEEK_API_KEY','MINIMAX_API_KEY','MIMO_API_KEY','TAVILY_API_KEY','ANTHROPIC_API_KEY'): env.pop(name,None)
overrides = {'PYTHONPATH':os.pathsep.join(str(TREE/p) for p in ('src','scripts','tests')), 'PYTHONDONTWRITEBYTECODE':'1','PYTHON_DOTENV_DISABLED':'1','COMPANY_WIKI_NETWORK':'blocked','COMPANY_WIKI_REAL_LLM':'0','CW_WR3_GOVERNANCE_AUTOUSE':'0','PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8','TEMP':str(TEMP),'TMP':str(TEMP),'TMPDIR':str(TEMP)}
env.update(overrides)
identity_script = 'import json, company_wiki.automation.store as s, company_wiki.source_catalog.narrative_transport_cli as c; print(json.dumps({"store":s.__file__,"cli":c.__file__}))'
identity = json.loads(subprocess.check_output([str(PYTHON),'-B','-c',identity_script],cwd=TREE,env=env,text=True))
for path in identity.values(): assert Path(path).resolve().is_relative_to(TREE.resolve()), identity
argv = [str(PYTHON),'-B','-m','pytest',*SELECTIONS[LABEL],'-q','-p','no:cacheprovider','--basetemp',str(TEMP),'--junitxml',str(OUT/'junit.xml')]
record={'started_at_utc':utc(),'cwd':str(TREE),'head':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'argv':argv,'environment_overrides':overrides,'imports':identity,'protected_file_count':len(protected),'tracked_entity_file_count':len(tracked_sources),'protected_sha256_before':before,'execution_surface':'approved','live_network_or_model_calls':0,'tested_files_sha256_before':tested_before,'tested_source_sha256':{str(TREE/p):sha(TREE/p) for p in ('src/company_wiki/automation/store.py','src/company_wiki/automation/terminal_receipt_contracts.py','src/company_wiki/automation/narrative_run_store.py')}}
(OUT/'execution.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
clock=time.monotonic()
with (OUT/'stdout.log').open('wb') as out,(OUT/'stderr.log').open('wb') as err:
 try:
  result=subprocess.run(argv,cwd=TREE,env=env,stdout=out,stderr=err,timeout=600,check=False)
  record.update(exit_code=result.returncode,timed_out=False)
 except subprocess.TimeoutExpired: record.update(exit_code=None,timed_out=True)
after={str(p):sha(p) for p in protected}
record.update(finished_at_utc=utc(),elapsed_seconds=time.monotonic()-clock,protected_sha256_after=after,protected_files_unchanged=before==after)
record['tested_files_sha256_after'] = {str(p.relative_to(TREE)):sha(p) for p in tested_files}
record['tested_files_unchanged'] = tested_before == record['tested_files_sha256_after']
assert record['tested_files_unchanged'], 'Tested revision changed during run'
(OUT/'execution.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
assert before==after,'Protected source/config bytes changed'
print(json.dumps({k:record[k] for k in ('started_at_utc','finished_at_utc','exit_code','timed_out','elapsed_seconds','protected_file_count','protected_files_unchanged')}))
