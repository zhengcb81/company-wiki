"""Normal commit/push of the completed W06 receipt and shared status only."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
paths = ['.planning/w06-audit-measures-reception',
         'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11']
for directory in ('docs/plans/cross-market-rf-e2e-2026-10-08',
                  'docs/plans/narrative-evidence-pilot-2026-09-26',
                  'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11'):
    paths += [str(Path(directory) / name) for name in ('task_plan.md', 'findings.md', 'progress.md')]
def run(*args):
    return subprocess.run(args, cwd=ROOT, check=True)
assert not subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT).strip()
run('git', 'add', '--', *paths)
run('git', 'diff', '--cached', '--stat')
run('git', 'commit', '-m', 'docs(w06): close measures acceptance and record installed skill')
run('git', 'push', 'origin', 'master')
run('git', 'rev-parse', 'HEAD')
run('git', 'ls-remote', 'origin', 'refs/heads/master')
