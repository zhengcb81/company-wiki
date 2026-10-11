"""Publish the independently accepted source fix without closing the ET gap."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT.parent / '_harness_worktrees/w06/cwp-acquisition-scope-root'
E = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance'
OUT = E / 'source-publication'
assert not OUT.exists(), 'One-shot publication; inspect existing receipts'
OUT.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
freeze = json.loads((E / 'producer-scope-fix/product-freeze.json').read_text(encoding='utf-8'))
review = json.loads((E / 'independent-source-scope-final/report.json').read_text(encoding='utf-8'))
assert review['verdict'] == 'PASS_SOURCE_SCOPE_FIX_PENDING_ROOT_MATRIX'
for name, row in freeze['product_files'].items():
    assert sha(TREE / name) == row['sha256'], name
config = [ROOT / 'config.yaml', ROOT / 'config/source_catalog.yaml', ROOT / 'config/local_ocr.json']
before_config = {str(p): sha(p) for p in config}

def run(cwd, name, *args):
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    (OUT / (name + '.stdout.log')).write_bytes(result.stdout)
    (OUT / (name + '.stderr.log')).write_bytes(result.stderr)
    print(name, result.returncode, flush=True)
    if result.returncode:
        print(result.stdout.decode('utf-8', errors='replace')[-4500:])
        print(result.stderr.decode('utf-8', errors='replace')[-2500:])
        raise SystemExit(result.returncode)
    return result.stdout.decode('utf-8', errors='replace').strip()

assert run(TREE, 'head-before', 'git', 'rev-parse', 'HEAD') == freeze['base_head']
assert not run(TREE, 'index-before', 'git', 'diff', '--cached', '--name-only')
assert run(ROOT, 'branch-before', 'git', 'branch', '--show-current') == 'master'
main_before = run(ROOT, 'main-before', 'git', 'rev-parse', 'HEAD')
handoff = TREE / 'docs/handoffs/w06-cross-period-acquisition'
author_copy = handoff / 'author-plan'
assert not author_copy.exists()
author_copy.mkdir(parents=True)
for name in ('task_plan.md', 'findings.md', 'progress.md'):
    (author_copy / name).write_bytes((TREE / '.planning/w06-cross-period-acquisition' / name).read_bytes())
receipt = handoff / 'ROOT-source-acceptance.md'
assert not receipt.exists()
receipt.write_text('''# ROOT source-layer acceptance — 2026-10-11

191 focused implementation tests and 13+1 independent public-API probes pass.
The actual unchanged 41-case offline chain now passes 40, with the last failure
in ET-to-FF cutoff diagnostics before CWP import. The source fix is accepted
within its scope: verified source facts belong to the writer/source layer,
irrelevant old periods do not obstruct acquisition, same-period reuse verifies
raw SHA, and registration/facts/reactivation recover through one transaction.

12 frozen product files are included, including canonical_scope.py and both
new tests. Original files/configuration are preserved. No new permission,
canary, review receipt, identity database or consumer filesystem interface.
The independent report and original 40/1 evidence remain in the mother W06
root-ff-matrix-acceptance directory. ROOT owns the ET/FF diagnostic repair,
final 41-case replay, shared PWF and publication. The whole PWF remains open.

Source runtime is read by consumers from the configured canonical CWP code
root; there is no separate company-wiki skill copy to overwrite.
''', encoding='utf-8')
paths = list(freeze['product_files']) + [p.relative_to(TREE).as_posix() for p in handoff.rglob('*') if p.is_file()]
run(TREE, 'stage', 'git', 'add', '--', *paths)
staged = run(TREE, 'staged', 'git', 'diff', '--cached', '--name-only').splitlines()
assert set(staged) == set(paths)
run(TREE, 'commit', 'git', 'commit', '-m', 'fix(source): unify verified acquisition scope and raw reuse ownership')
commit = run(TREE, 'accepted-head', 'git', 'rev-parse', 'HEAD')
run(ROOT, 'fetch', 'git', 'fetch', 'origin', 'master')
run(ROOT, 'remote-fast-forward', 'git', 'merge', '--ff-only', 'origin/master')
run(ROOT, 'merge', 'git', 'merge', '--no-ff', commit, '-m', 'merge: accept verified cross-period source acquisition repair')
main = run(ROOT, 'merged-head', 'git', 'rev-parse', 'HEAD')
for name, row in freeze['product_files'].items():
    assert sha(TREE / name) == row['sha256'], name
    assert (ROOT / name).read_bytes().replace(b'\r\n', b'\n') == (TREE / name).read_bytes().replace(b'\r\n', b'\n'), name
assert before_config == {str(p): sha(p) for p in config}
run(ROOT, 'normal-push', 'git', 'push', 'origin', 'master')
remote = run(ROOT, 'remote-exact', 'git', 'ls-remote', 'origin', 'refs/heads/master').split()[0]
assert remote == main
record = {'schema': 'root-w06-source-publication/1', 'main_before': main_before,
          'source_commit': commit, 'main_commit': main, 'remote_exact': remote,
          'product_files': 12, 'product_lf_equal': True, 'config_unchanged': True,
          'normal_hooks': True, 'engineering': '191 PASS', 'independent': '13+1 PASS',
          'matrix': '40/1; separate ET cutoff diagnostic fix pending',
          'ci': 'pending exact-SHA check', 'installation': 'configured canonical code root; no CWP skill copy'}
(OUT / 'publication.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
print(json.dumps(record), flush=True)
