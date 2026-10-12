import json
import os
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception')
out = Path(__file__).resolve().parent / 'verification-release'
assert not out.exists()
out.mkdir()
env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
def run(label, args, expected=0):
    start = time.monotonic()
    p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, encoding='utf-8', errors='replace', timeout=30)
    row = {'command':args, 'exit_code':p.returncode, 'seconds':time.monotonic()-start, 'stdout':p.stdout, 'stderr':p.stderr}
    (out / (label+'.json')).write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'label':label,'exit':p.returncode,'seconds':row['seconds'],'stdout':p.stdout[-1200:]}, ensure_ascii=False))
    assert p.returncode == expected, row
    return p
run('focused',['python','-B','-m','pytest','-q','tests/test_root_w07_analyst_scope.py','tests/test_w07_analyst_risk_audit.py','--tb=short','-p','no:cacheprovider'])
scratch=ROOT/'.tmp'/('root-w07-'+uuid.uuid4().hex[:8])
assert scratch.resolve().is_relative_to(ROOT.resolve()) and not scratch.exists()
run('e2e',['python','-B','tools/run_analyst_risk_e2e.py','--owned-root',str(scratch),'--out-root',str(out/'e2e')])
assert not scratch.exists()
run('skill-structure',['python','-B','C:/Users/郑曾波/.codex/skills/.system/skill-creator/scripts/quick_validate.py',str(ROOT/'skills/revenue-forecast-audit')])
check=run('install-preflight',['python','-B','tools/sync_skill.py','--check'],expected=1)
installed=json.loads(check.stdout)['installations']
expected={'scripts/analyst_risk_audit.py','references/analyst-risk-audit.md','references/review-analyst.md'}
assert len(installed)==2 and all(set(row['mismatches'])==expected for row in installed), installed
print('Release verification green; exactly 3 skill file changes per copy; scratch restored')
