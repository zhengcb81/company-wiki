import json
import os
from pathlib import Path
import subprocess
import time
import uuid

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception')
target = ROOT / 'skills/revenue-forecast-audit/scripts/analyst_risk_audit.py'
code = target.read_text(encoding='utf-8')
old = '''        status = "OBSERVED" if reasons == ["independence_metadata_present"] else "UNRESOLVED"'''
new = '''        if independent and claim_ids and all(cid in claim_index for cid in claim_ids) \\
                and len(actual_sources) == 1 and "same_source_not_independent" not in reasons:
            reasons.append("same_source_not_independent")
        status = "OBSERVED" if reasons == ["independence_metadata_present"] else "UNRESOLVED"'''
assert code.count(old) == 1
target.write_text(code.replace(old, new), encoding='utf-8', newline='\n')
out = Path(__file__).resolve().parent / 'verification-final'
assert not out.exists()
out.mkdir()
env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
def run(label, args, limit=30):
    start = time.monotonic()
    p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, encoding='utf-8', errors='replace', timeout=limit)
    row = {'command': args, 'exit_code': p.returncode, 'wall_seconds': time.monotonic()-start, 'stdout':p.stdout, 'stderr':p.stderr}
    (out / (label + '.json')).write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'label':label,'exit_code':p.returncode,'seconds':row['wall_seconds'],'stdout':p.stdout[-1500:]}, ensure_ascii=False))
    assert p.returncode == 0, p.stderr[-1000:]
run('focused', ['python','-B','-m','pytest','-q','tests/test_root_w07_analyst_scope.py','tests/test_w07_analyst_risk_audit.py','--tb=short','-p','no:cacheprovider'])
scratch = ROOT / '.tmp' / ('root-w07-' + uuid.uuid4().hex[:8])
assert scratch.resolve().is_relative_to(ROOT.resolve()) and not scratch.exists()
run('e2e', ['python','-B','tools/run_analyst_risk_e2e.py','--owned-root',str(scratch),'--out-root',str(out / 'e2e')])
assert not scratch.exists()
run('skill-structure', ['python','-B','C:/Users/郑曾波/.codex/skills/.system/skill-creator/scripts/quick_validate.py',str(ROOT / 'skills/revenue-forecast-audit')])
print('Final focused/E2E/skill validation passed; scratch restored to absent')
