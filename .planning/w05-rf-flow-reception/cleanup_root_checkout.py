"""Remove only the clean accepted ROOT checkout; retain branch and worker."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PARENT = (ROOT.parent/'_harness_worktrees/w05').resolve(strict=True)
TREE = (PARENT/'rf-flow-root').resolve(strict=True)
MAIN = ROOT.parent/'revenue-forecast'
E = ROOT/'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-rf-flow-acceptance'
assert TREE.parent == PARENT and TREE.name == 'rf-flow-root'
assert TREE != MAIN.resolve() and TREE != (PARENT/'rf-flow').resolve()
receipt = E/'root-checkout-cleanup.json'
assert not receipt.exists()
def output(cwd, *args):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()
head = output(TREE, 'git', 'rev-parse', 'HEAD')
assert head == '30ddae8ed2a457c418e63b182e7d8c9230fbf3ff'
assert output(TREE, 'git', 'branch', '--show-current') == 'codex/root-w05-rf-flow-20261011'
assert not output(TREE, 'git', 'status', '--porcelain')
subprocess.run(['git', 'merge-base', '--is-ancestor', head, 'main'], cwd=MAIN, check=True)
ignored = output(TREE, 'git', 'status', '--short', '--ignored').splitlines()
assert set(ignored) <= {'!! .mypy_cache/', '!! .ruff_cache/'}, ignored
inventory = json.loads((E/'fix/price-correlation/root-product-inventory.json').read_text(encoding='utf-8'))
for row in inventory['files']:
    assert (TREE/row['path']).read_bytes().replace(b'\r\n', b'\n') == (MAIN/row['path']).read_bytes().replace(b'\r\n', b'\n')
smoke = json.loads((E/'independent-price-final/installed-smoke/results.json').read_text(encoding='utf-8'))
assert smoke['status'] == 'PASS_WITH_SCOPE'
subprocess.run(['git', 'worktree', 'remove', str(TREE)], cwd=MAIN, check=True)
assert not TREE.exists()
receipt.write_text(json.dumps({'schema': 'root-checkout-cleanup/1',
    'removed_checkout': str(TREE), 'retained_branch': 'codex/root-w05-rf-flow-20261011',
    'accepted_commit': head, 'ancestor_of_main': True, 'tracked_clean': True,
    'canonical_LF_equal_files': len(inventory['files']),
    'ignored_only_disposable_caches': ignored, 'normal_worktree_remove': True,
    'worker_and_canonical_preserved': True, 'raw_originals_untouched': True},
    ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Accepted RF ROOT checkout removed normally; branch, worker, main and evidence retained')
