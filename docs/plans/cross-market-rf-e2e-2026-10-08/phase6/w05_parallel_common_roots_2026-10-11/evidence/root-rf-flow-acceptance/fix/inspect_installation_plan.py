"""ROOT-requested read-only selective installation inventory; never --apply."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
EVIDENCE = Path(__file__).resolve().parent
BASE = '1b616622763ece6549676f2a74f596e6c65244af'
environment = os.environ.copy()
environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
changed = subprocess.run(['git', 'diff', '--name-only', BASE], cwd=ROOT, env=environment,
                         text=True, encoding='utf-8', capture_output=True, timeout=30, check=True).stdout.splitlines()
scope = sorted({name for name in changed if name in {'.gitignore', 'CHANGELOG.md', 'SKILL.md'}
                or name.split('/')[0] in {'agents', 'config', 'references', 'scripts'}}
               | {'scripts/contracts/recognition.py'})
arguments = [sys.executable, '-B', 'tools/sync_installations.py', '--canonical', str(ROOT), '--plan']
for name in scope:
    arguments += ['--file', name]
result = subprocess.run(arguments, cwd=ROOT, env=environment, text=True, encoding='utf-8',
                        capture_output=True, timeout=30, check=True)
plan = json.loads(result.stdout)
(EVIDENCE / 'install-readonly-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
summary = {'tool': 'tools/sync_installations.py', 'configuration': 'DEFAULT_DESTINATIONS in tool; no external install config',
           'declared_destinations': ['C:/Users/郑曾波/.agents/skills', 'C:/Users/郑曾波/.claude/skills', 'C:/Users/郑曾波/.codex/skills'],
           'claude_target_junction': 'C:/Users/郑曾波/.agents/skills/revenue-forecast',
           'actual_independent_targets': ['C:/Users/郑曾波/.agents/skills/revenue-forecast', 'C:/Users/郑曾波/.codex/skills/revenue-forecast'],
           'scope': scope, 'selected_count': len(scope), 'command': arguments,
           'read_only_exit_code': result.returncode, 'stderr': result.stderr, 'applied_files': 0,
           'note': 'existing tool unique_destinations resolves the installed skill target and deduplicates the .claude junction; ROOT will use current canonical after merge and new read-only plan before apply'}
(EVIDENCE / 'install-readonly-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'selected_count': len(scope), 'selected_scope': scope, 'plan_keys': list(plan), 'writes': 0}, ensure_ascii=False))
