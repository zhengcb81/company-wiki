"""Read-only Git/task inventory; never inspect credentials or session stores."""
import json
from pathlib import Path
import subprocess

PLAN = Path(__file__).resolve().parent
projects = Path('C:/Users/郑曾波/Projects')
result = {}
for name in ['company-wiki','revenue-forecast','revenue-forecast-audit']:
    root = projects/name
    def git(*args):
        return subprocess.check_output(['git','-C',str(root),*args],encoding='utf-8').strip()
    status = git('status','--porcelain')
    trees = git('worktree','list','--porcelain')
    tracked = git('ls-files').splitlines()
    result[name] = {'root':str(root),'head':git('rev-parse','HEAD'),
        'branch':git('branch','--show-current'),'dirty_count':len(status.splitlines()),
        'worktrees':trees,'tracked_file_count':len(tracked),
        'tracked_paths':[p for p in tracked if p.startswith(('scripts/','tools/','skills/',
            'tests/support/','tests/fixtures/forward_bundle/'))]}
(PLAN/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name,entry in result.items():
    print(json.dumps({'name':name,'head':entry['head'],'branch':entry['branch'],
                     'dirty_count':entry['dirty_count'],'worktrees':entry['worktrees']}))
print('AUDIT_KNOWN_FILES')
for p in result['revenue-forecast-audit']['tracked_paths']:
    if p.startswith(('skills/revenue-forecast-audit/scripts/','tools/','tests/')) and any(s in p for s in ['audit','document','execution','pool','workflow']):
        print(p)
