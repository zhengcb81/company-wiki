"""Repair the single static annotation and resume the normal interrupted publish."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT.parent / '_harness_worktrees/w06/cwp-acquisition-scope-root'
E = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance'
OUT = E / 'source-publication'
assert OUT.exists() and not (OUT / 'publication.json').exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
freeze = json.loads((E / 'producer-scope-fix/product-freeze.json').read_text(encoding='utf-8'))
for name, row in freeze['product_files'].items():
    assert sha(TREE / name) == row['sha256'], name
path = TREE / 'src/company_wiki/source_catalog/operation_contract.py'
before = path.read_bytes()
needle = b'    acquisition = {}'
assert before.count(needle) == 1
after = before.replace(needle, b'    acquisition: dict[str, Any] = {}')
path.write_bytes(after)
root_freeze = json.loads(json.dumps(freeze))
root_freeze.update(schema_version='root-w06-source-static-publication-freeze/1',
                   author_freeze_sha256=sha(E / 'producer-scope-fix/product-freeze.json'),
                   root_change='One explicit dict[str, Any] annotation; no runtime or test assertion change')
root_freeze['product_files']['src/company_wiki/source_catalog/operation_contract.py'] = {
    'sha256': sha(path), 'bytes': len(after)}
(OUT / 'root-product-freeze.json').write_text(json.dumps(root_freeze, indent=2)+'\n', encoding='utf-8')
(OUT / 'annotation-fix.json').write_text(json.dumps({'file': str(path.relative_to(TREE)),
    'before_sha256': hashlib.sha256(before).hexdigest(), 'after_sha256': sha(path),
    'change': 'acquisition = {} -> acquisition: dict[str, Any] = {}',
    'cause': 'Normal mypy contract hook found empty container annotation missing',
    'runtime_behavior_changed': False}, indent=2)+'\n', encoding='utf-8')

def run(cwd, name, *args):
    assert not (OUT / (name+'.stdout.log')).exists(), name
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    (OUT / (name+'.stdout.log')).write_bytes(result.stdout)
    (OUT / (name+'.stderr.log')).write_bytes(result.stderr)
    print(name, result.returncode, flush=True)
    if result.returncode:
        print(result.stdout.decode('utf-8', errors='replace')[-4500:])
        print(result.stderr.decode('utf-8', errors='replace')[-2500:])
        raise SystemExit(result.returncode)
    return result.stdout.decode('utf-8', errors='replace').strip()

run(TREE, 'stage-type-annotation', 'git', 'add', '--', 'src/company_wiki/source_catalog/operation_contract.py')
run(TREE, 'commit-after-type', 'git', 'commit', '-m', 'fix(source): unify verified acquisition scope and raw reuse ownership')
commit = run(TREE, 'accepted-head-after-type', 'git', 'rev-parse', 'HEAD')
main_before = run(ROOT, 'main-before-resume', 'git', 'rev-parse', 'HEAD')
run(ROOT, 'fetch-after-type', 'git', 'fetch', 'origin', 'master')
run(ROOT, 'remote-ff-after-type', 'git', 'merge', '--ff-only', 'origin/master')
run(ROOT, 'merge-after-type', 'git', 'merge', '--no-ff', commit, '-m', 'merge: accept verified cross-period source acquisition repair')
main = run(ROOT, 'merged-head-after-type', 'git', 'rev-parse', 'HEAD')
for name, row in root_freeze['product_files'].items():
    assert sha(TREE / name) == row['sha256'], name
    assert (ROOT / name).read_bytes().replace(b'\r\n', b'\n') == (TREE / name).read_bytes().replace(b'\r\n', b'\n'), name
run(ROOT, 'normal-push-after-type', 'git', 'push', 'origin', 'master')
remote = run(ROOT, 'remote-exact-after-type', 'git', 'ls-remote', 'origin', 'refs/heads/master').split()[0]
assert remote == main
record = {'schema':'root-w06-source-publication/1','main_before':main_before,
          'source_commit':commit,'main_commit':main,'remote_exact':remote,
          'product_files':12,'product_lf_equal':True,'normal_hooks':True,
          'engineering':'191 PASS','independent':'13+1 PASS',
          'root_static_fix':'dict[str, Any] annotation; normal mypy hook passed',
          'matrix':'40/1; separate ET cutoff diagnostic fix pending',
          'ci':'pending exact-SHA check','installation':'configured canonical CWP code root'}
(OUT/'publication.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record),flush=True)
