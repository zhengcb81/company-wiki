"""Commit tested W04 exact scope; leave main update to next operation."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
record = json.loads((HERE/'integration-attempt1/execution.json').read_text(encoding='utf-8'))
work = Path(record['workdir'])
assert record['exit_code'] == 0 and not record['timed_out']
assert all(record[k] for k in ('protected_config_ci_unchanged','production_configs_unchanged','source_bytes_still_frozen','scratch_restored_absent'))
stdout = (HERE/'integration-attempt1/stdout.log').read_text(encoding='utf-8')
line = next(line for line in stdout.splitlines() if line.startswith('CW-BASETEMP-DECISION '))
decision = json.loads(line.removeprefix('CW-BASETEMP-DECISION '))
assert not Path(decision['effective_basetemp']).exists(), 'Relocated pytest directory was not restored'
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=work).strip()
assert subprocess.check_output(['git','branch','--show-current'],cwd=work,text=True).strip() == record['branch']
for row in record['files']:
    assert hashlib.sha256((work/row['path']).read_bytes()).hexdigest() == row['frozen_worktree_sha256']
attrs = work/'.gitattributes'
with attrs.open('ab') as f:
    f.write(b'\n# Exact ROOT W04 integration receipts.\n/.planning/w04-selector-reception/** -text -diff\n')
dest = work/'.planning/w04-selector-reception'
assert not dest.exists()
shutil.copytree(HERE,dest)
paths = [r['path'] for r in record['files']] + ['.gitattributes','.planning/w04-selector-reception']
subprocess.run(['git','add','--pathspec-from-file=-','--pathspec-file-nul'],cwd=work,
               input=b''.join(p.encode('utf-8')+b'\0' for p in paths),check=True)
for row in record['files']:
    staged = subprocess.check_output(['git','cat-file','blob',':'+row['path']],cwd=work)
    assert hashlib.sha256(staged.replace(b'\r\n',b'\n')).hexdigest() == row['normalized_lf_sha256']
subprocess.run(['git','diff','--cached','--check'],cwd=work,check=True)
subprocess.run(['git','commit','-m','fix: integrate subject-bound narrative selection and quality ordering'],cwd=work,check=True)
head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=work,text=True).strip()
(HERE/'implementation-commit.json').write_bytes((json.dumps({'commit':head,'branch':record['branch'],'workdir':str(work),'relocated_pytest_restored_absent':True},ensure_ascii=False,indent=2)+'\n').encode())
print('W04 tested implementation commit: '+head,flush=True)
