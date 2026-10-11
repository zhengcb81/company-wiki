"""Run selected synthetic tests in a minimal environment and restore unique scratch."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root')
EVIDENCE = Path(__file__).resolve().parent
name = sys.argv[1]
args = sys.argv[2:]
scratch = Path('C:/Users/郑曾波/Projects/company-wiki/.tmp') / ('cs-' + uuid.uuid4().hex[:9])
assert not scratch.exists()
scratch.mkdir(parents=True)
env = {key: value for key, value in os.environ.items()
       if key.upper() in {'PATH','SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','PROCESSOR_ARCHITECTURE'}}
for key in ('HOME','USERPROFILE','TEMP','TMP'):
    env[key] = str(scratch)
env.update(PYTHONPATH=str(TREE/'src') + os.pathsep + str(TREE/'tests'),
    PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1',
    COMPANY_WIKI_NETWORK='blocked', COMPANY_WIKI_REAL_LLM='0',
    PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONIOENCODING='utf-8')
command = [sys.executable, '-m', 'pytest', '-q', '-o', 'addopts=',
           '-p', 'no:cacheprovider', '--basetemp=' + str(scratch/'pytest'), *args]
started = time.monotonic()
try:
    result = subprocess.run(command, cwd=TREE, env=env, capture_output=True, text=True,
                            encoding='utf-8', timeout=180)
    (EVIDENCE/(name+'.stdout.txt')).write_text(result.stdout, encoding='utf-8')
    (EVIDENCE/(name+'.stderr.txt')).write_text(result.stderr, encoding='utf-8')
    summary = dict(command=command, cwd=str(TREE), returncode=result.returncode,
        elapsed_seconds=round(time.monotonic()-started,3),
        environment='allowlisted platform vars + synthetic HOME/TMP; dotenv disabled; pytest socket guard',
        actual_network_calls=0, llm_calls=0, fee_usd=0,
        test_sha256={arg:hashlib.sha256((TREE/arg.split('::')[0]).read_bytes()).hexdigest()
                    for arg in args if arg.startswith('tests/') and (TREE/arg.split('::')[0]).is_file()})
    print(result.stdout[-13000:])
    print(result.stderr[-2000:])
finally:
    resolved = scratch.resolve()
    assert resolved.parent == Path('C:/Users/郑曾波/Projects/company-wiki/.tmp').resolve()
    assert resolved.name.startswith('cs-')
    shutil.rmtree(resolved)
    summary['scratch_restored'] = not scratch.exists()
    (EVIDENCE/(name+'.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))
