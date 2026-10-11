"""Apply the exact frozen W04 union to fresh current main and test once."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
WORK = Path('C:/Users/郑曾波/.codex/worktrees/w04-selector-integration/company-wiki')
BASE = '5c07f47cc6f9255b9ce2824e9c9c63139f48f533'
BRANCH = 'codex/root-w04-selector-integration-20261011'
manifest_path = ROOT / '.planning/w04-selector-integration/integration-manifest.json'
m = json.loads(manifest_path.read_text(encoding='utf-8'))
old = Path(m['base']['tree'])
out = HERE / 'integration-attempt1'
assert not out.exists(), 'Preserve previous attempt'

def git(*args, check=True):
    return subprocess.run(['git','-C',str(WORK),*args],check=check,capture_output=True)

digest = lambda raw: hashlib.sha256(raw).hexdigest()
normalize = lambda raw: raw.replace(b'\r\n',b'\n') if raw is not None else None

def blob(commit, rel):
    p = git('cat-file','blob',commit+':'+rel,check=False)
    return p.stdout if p.returncode == 0 else None

assert git('rev-parse','HEAD').stdout.decode().strip() == BASE
assert not git('status','--porcelain').stdout.strip(), 'New reception tree must be clean'
rows = []
frozen = {}
for row in m['rows']:
    if row['package'] != 'selector_accept':
        continue
    rel = row['path']
    ours = blob(BASE,rel)
    assert (digest(ours) if ours is not None else None) == row['current_main']['sha256'], 'Main changed: '+rel
    assert normalize(ours) == normalize(blob(m['base']['commit'],rel)), 'Real three-way conflict: '+rel
    raw = (old / rel).read_bytes()
    assert digest(raw) == row['pending_worktree']['sha256'], 'Frozen target changed: '+rel
    frozen[rel] = raw
    rows.append({'path':rel,'main_sha256':digest(ours) if ours is not None else None,
                 'frozen_worktree_sha256':digest(raw),'normalized_lf_sha256':digest(normalize(raw)),
                 'three_way':'no_main_content_conflict'})
assert len(rows) == 18
protected = {row['path']: digest((WORK/row['path']).read_bytes()) if (WORK/row['path']).exists() else None
             for row in m['rows'] if row['package'] != 'selector_accept'}
production_paths = [ROOT/'config.yaml',ROOT/'config/source_catalog.yaml',ROOT/'config/local_ocr.json']
production = {str(p):digest(p.read_bytes()) for p in production_paths}
git('switch','-c',BRANCH)
out.mkdir()
for rel, raw in frozen.items():
    p = WORK / rel
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(raw)
assert all(digest((WORK/r['path']).read_bytes()) == r['frozen_worktree_sha256'] for r in rows)

scratch = WORK / '.tmp' / ('w04s-'+uuid.uuid4().hex[:8])
assert not scratch.exists()
scratch.mkdir(parents=True)
modules = ['tests/unit/test_w04_selector_version_dispatch.py',
           'tests/integration/test_w04_semantic_budget_finalize.py',
           'tests/integration/test_w04_novelty_finalize.py',
           'tests/integration/test_w04_quality_band_budget.py']
command = [sys.executable,'-X','utf8','-B','-m','pytest','-q',*modules,
           '-p','no:cacheprovider','--basetemp',str(scratch/'pytest')]
env = {k:os.environ[k] for k in ('PATH','PATHEXT','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','NUMBER_OF_PROCESSORS') if k in os.environ}
env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',
           PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHON_DOTENV_DISABLED='1')
print('W04 exact 18-file integration; one four-module batch; 90 second cap; 0 model/provider calls',flush=True)
start = time.monotonic()
exit_code = None
timed_out = False
try:
    proc = subprocess.run(command,cwd=WORK,env=env,capture_output=True,timeout=90)
    exit_code = proc.returncode
    (out/'stdout.log').write_bytes(proc.stdout)
    (out/'stderr.log').write_bytes(proc.stderr)
    print(proc.stdout.decode('utf-8',errors='replace')[-4000:],flush=True)
except subprocess.TimeoutExpired as exc:
    timed_out = True
    (out/'stdout.log').write_bytes(exc.stdout or b'')
    (out/'stderr.log').write_bytes(exc.stderr or b'')
finally:
    assert scratch.resolve().parent == (WORK/'.tmp').resolve()
    assert scratch.name.startswith('w04s-')
    shutil.rmtree(scratch)
elapsed = time.monotonic()-start
post_protected = {rel:digest((WORK/rel).read_bytes()) if (WORK/rel).exists() else None for rel in protected}
record = {'schema':'root-w04-selector-integration/1','workdir':str(WORK),'branch':BRANCH,
          'base_commit':BASE,'frozen_manifest_sha256':digest(manifest_path.read_bytes()),'files':rows,
          'test_command':command,'exit_code':exit_code,'timed_out':timed_out,'seconds':round(elapsed,4),
          'protected_config_ci_unchanged':protected==post_protected,
          'production_configs_unchanged':production=={str(p):digest(p.read_bytes()) for p in production_paths},
          'source_bytes_still_frozen':all(digest((WORK/r['path']).read_bytes())==r['frozen_worktree_sha256'] for r in rows),
          'scratch_restored_absent':not scratch.exists(),'real_provider_llm_calls':0,
          'summary_economic_quality':'not_evaluated'}
(out/'execution.json').write_bytes((json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({k:record[k] for k in ('exit_code','timed_out','seconds','protected_config_ci_unchanged','production_configs_unchanged','source_bytes_still_frozen','scratch_restored_absent')},ensure_ascii=False),flush=True)
assert all(record[k] for k in ('protected_config_ci_unchanged','production_configs_unchanged','source_bytes_still_frozen','scratch_restored_absent'))
raise SystemExit(exit_code if exit_code is not None else 124)
