"""Publish completed ROOT evidence only; exclude active production/reviews."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
W06 = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11'
OUT = W06 / 'evidence/root-ff-matrix-acceptance/recall-checkpoint-publication.json'
assert not OUT.exists(), 'one-shot publication'

def git(*args):
    proc = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True)
    return proc.stdout.decode('utf-8', errors='replace').strip()

assert git('branch', '--show-current') == 'master'
assert git('rev-parse', 'HEAD') == '8e3d895f832d8bf289fcaf96f3d96159df9e47db'
assert not git('diff', '--cached', '--name-only'), 'preserve any existing index'
selected = []
for sub in ('w04-root-novelty-recall', 'w06-cross-period-acquisition', 'w06-ff-matrix-reception'):
    selected += [ROOT / '.planning' / sub / name for name in ('task_plan.md', 'findings.md', 'progress.md')]
selected += [ROOT / '.planning/w04-root-novelty-recall' / name for name in (
    'run_phase2_native.py', 'native-novelty-six-quality-v2.json.gz',
    'native-novelty-six-quality-v2-storage.json', 'native-novelty-six-quality-v2-execution.json',
    'native-novelty-six-quality-v2-stdout.log', 'native-novelty-six-quality-v2-stderr.log')]
selected += [ROOT / '.planning/w06-cross-period-acquisition/matrix-deadline-diagnosis.md', Path(__file__).resolve()]
selected += [W06 / 'ROOT-reception-status.md', W06 / 'evidence/root-ff-matrix-acceptance/completed-checkpoints-publication.json']
for base in (
    ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08',
    ROOT / 'docs/plans/narrative-evidence-pilot-2026-09-26',
    ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11', W06):
    selected += [base / name for name in ('task_plan.md', 'findings.md', 'progress.md')]
for base in (
    ROOT / '.planning/w06-cross-period-acquisition/cutoff-independent',
    ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w04_post_pw03_common_roots_2026-10-11/evidence/integration/root-novelty-quality',
    W06 / 'evidence/root-ff-matrix-acceptance/root-matrix-final-cutoff-v1'):
    selected += [p for p in base.rglob('*') if p.is_file() and 'retest' not in p.parts]
paths = sorted({str(p.relative_to(ROOT)).replace('\\', '/') for p in selected})
assert all((ROOT / p).is_file() for p in paths)
subprocess.run(['git', 'add', '--pathspec-from-file=-', '--pathspec-file-nul'],
               cwd=ROOT, input=b''.join(p.encode('utf-8') + b'\0' for p in paths), check=True)
staged = git('-c', 'core.quotePath=false', 'diff', '--cached', '--name-only').splitlines()
assert set(staged).issubset(paths), 'publication must keep its explicit file set'
subprocess.run(['git', 'commit', '-m', 'docs: record fixed native recall and remaining contract acceptance'], cwd=ROOT, check=True)
head = git('rev-parse', 'HEAD')
subprocess.run(['git', 'push', 'origin', 'master'], cwd=ROOT, check=True)
remote = git('ls-remote', '--heads', 'origin', 'master').split()[0]
assert head == remote
OUT.write_text(json.dumps({'schema': 'root-recall-checkpoint-publication/1', 'head': head,
    'remote_head': remote, 'paths': paths, 'scope': 'completed evidence and current plans only; no product code',
    'active_cutoff_author_and_phase2_review_excluded': True}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PUBLISHED', head, len(paths), flush=True)
