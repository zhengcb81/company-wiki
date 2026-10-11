"""Publish completed receipts only; do not stage either active repair lane."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'docs/plans/cross-market-rf-e2e-2026-10-08'
W06 = BASE/'phase6/w06_parallel_verification_2026-10-11'
E = W06/'evidence'

def out(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()

assert out('git', 'branch', '--show-current') == 'master'
assert out('git', 'rev-parse', 'HEAD') == 'e2e19ea200bf87b13dd41d6389897ea5f2711d93'
assert not out('git', 'diff', '--cached', '--name-only')
paths = []
for directory in [ROOT/'.planning/w06-cwp-portability-reception',
                  ROOT/'.planning/w06-ff-matrix-reception',
                  ROOT/'.planning/w06-cross-period-acquisition',
                  E/'root-cwp-portability-acceptance',
                  E/'root-ff-matrix-acceptance/intake',
                  E/'root-ff-matrix-acceptance/independent-final',
                  E/'root-ff-matrix-acceptance/root-cause-review']:
    paths.extend(p for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for path in (E/'root-ff-matrix-acceptance/fix').iterdir():
    if path.is_file() and not path.name.startswith('case-authority-'):
        paths.append(path)
paths.append(W06/'ROOT-reception-status.md')
for group in [BASE, ROOT/'docs/plans/narrative-evidence-pilot-2026-09-26',
              BASE/'phase6/w05_parallel_common_roots_2026-10-11', W06]:
    paths.extend(group/name for name in ('task_plan.md', 'findings.md', 'progress.md'))
names = sorted({p.relative_to(ROOT).as_posix() for p in paths})
assert all('producer-scope-fix/' not in p and 'case-authority' not in p for p in names)
subprocess.run(['git', 'add', '--', *names], cwd=ROOT, check=True)
staged = out('git', 'diff', '--cached', '--name-only').splitlines()
assert staged and set(staged) <= set(names)
subprocess.run(['git', 'commit', '-m',
    'docs: receive W06 portability and record matrix root failures with isolated repair plan'], cwd=ROOT, check=True)
print('published receipt commit:', out('git', 'rev-parse', 'HEAD'))
subprocess.run(['git', 'push', 'origin', 'master'], cwd=ROOT, check=True)
