"""Only two selected FF files; freeze all other installed file metadata."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PLAN = Path(__file__).resolve().parent
FF = Path('C:/Users/郑曾波/Projects/filing-fetch')
FILES = ['scripts/et_v2_contract.py','scripts/transcript_tool_transport.py']
tool = FF/'tools/sync_installs_b3.py'
base = [sys.executable,str(tool),'--json']
for file in FILES:
    base += ['--file',file]
preview = json.loads(subprocess.check_output([*base,'--plan'],encoding='utf-8'))
assert preview['scope'] == FILES
assert len(preview['targets']) == 2
assert all(not t['errors'] for t in preview['targets'])
roots = [Path(t['physical_target']) for t in preview['targets']]
def metadata(root):
    return {p.relative_to(root).as_posix():[p.stat().st_size,p.stat().st_mtime_ns]
            for p in root.rglob('*') if p.is_file() and p.relative_to(root).as_posix() not in FILES}
before = {str(root):metadata(root) for root in roots}
applied = json.loads(subprocess.check_output([*base,'--install'],encoding='utf-8'))
assert applied['status']=='completed'
assert all(set(t['written']) <= set(FILES) for t in applied['targets'])
assert before == {str(root):metadata(root) for root in roots}
checks = []
env = {key:value for key,value in os.environ.items() if key.upper() in
       {'SYSTEMROOT','PATH','TEMP','TMP','WINDIR','COMSPEC'}}
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
for root in roots:
    for file in FILES:
        assert hashlib.sha256((root/file).read_bytes()).hexdigest() == preview['source_sha256'][file]
    checked = json.loads(subprocess.check_output([sys.executable,'-B',str(PLAN/'install_smoke.py'),str(root)],env=env,encoding='utf-8',timeout=30))
    checks.append(checked)
assert before == {str(root):metadata(root) for root in roots}
(PLAN/'installation.json').write_text(json.dumps({'plan':preview,'result':applied,
    'checks':checks,'unselected_metadata_preserved':True,'credential_read':False},
    ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'physical_copies':len(roots),'selected_files_per_copy':2,'checks':checks,
                  'unselected_metadata_preserved':True}))
