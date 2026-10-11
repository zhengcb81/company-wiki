"""Normal Git publication of accepted manual tooling; the product gap stays open."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FF = ROOT.parent / '_harness_worktrees/w06/ff-contract-matrix-root'
MAIN = ROOT.parent / 'filing-fetch'
E = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance'
OUT = E / 'tool-publication'
assert not OUT.exists(), 'One-shot publication; inspect the prior receipt instead'
OUT.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
freeze = json.loads((E / 'fix/case-authority/manifest.json').read_text(encoding='utf-8'))
review = json.loads((E / 'independent-case-authority-final/report.json').read_text(encoding='utf-8'))
assert review['verdict'] == 'PASS_WITH_SCOPE' and len(review['probes']) == 28
assert all(p['pass'] for p in review['probes'])
for row in freeze['files']:
    assert sha(FF / row['path']) == row['sha256'], row['path']
key = MAIN / 'config/FMP_API_KEY.txt'
key_before = (key.stat().st_size, key.stat().st_mtime_ns)

def run(cwd, name, *args):
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    (OUT / (name + '.stdout.log')).write_bytes(result.stdout)
    (OUT / (name + '.stderr.log')).write_bytes(result.stderr)
    print(name, result.returncode, flush=True)
    if result.returncode:
        print(result.stdout.decode('utf-8', errors='replace')[-3000:])
        print(result.stderr.decode('utf-8', errors='replace')[-3000:])
        raise SystemExit(result.returncode)
    return result.stdout.decode('utf-8', errors='replace').strip()

assert run(FF, 'branch-before', 'git', 'branch', '--show-current') == 'codex/root-w06-ff-matrix-20261011'
assert run(FF, 'head-before', 'git', 'rev-parse', 'HEAD') == '08ec85b27133cdf8a8d3b38fdba15255fc1ebac2'
assert run(FF, 'merge-before', 'git', 'rev-parse', 'MERGE_HEAD') == 'c5527f1a9b2123e3f1796b5eb4dd35e0a81e13f5'
assert not run(FF, 'unstaged-before', 'git', 'diff', '--name-only')
assert run(MAIN, 'main-before', 'git', 'branch', '--show-current') == 'main'
assert not run(MAIN, 'tracked-before', 'git', 'status', '--porcelain', '--untracked-files=no')
receipt = FF / 'docs/handoffs/w06-ff-matrix/ROOT-tool-reception.md'
assert not receipt.exists()
receipt.write_text('''# ROOT tool acceptance — 2026-10-11

The manual offline-contract tool is accepted: 195 focused tests and 28 independent
fixed-input probes pass. CaseSpec/RunSpec drive coverage, complete requests,
fixtures, expectations and response validation. Old failures and SHA bindings
remain. This tooling is not installed as a user skill or run on every commit.

The actual unchanged 41-case product replay is **40 PASS / 1 FAIL**, 164.62 seconds.
The remaining case is `call_past_cutoff`: ET safely excludes the future call but
collapses its reason into `not_found`, then FF maps it to provider unavailability.
ROOT owns a separate common result-boundary repair. This commit does not certify
all 41 cases, real supplier reachability, fees, or the full mother PWF.

Full evidence: company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/
w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/
independent-case-authority-final and root-matrix-replay.
''', encoding='utf-8')
run(FF, 'add-receipt', 'git', 'add', '--', str(receipt.relative_to(FF)))
run(FF, 'commit', 'git', 'commit', '-m', 'feat: add isolated contract matrix with fixed case authority')
commit = run(FF, 'accepted-head', 'git', 'rev-parse', 'HEAD')
run(MAIN, 'fetch', 'git', 'fetch', 'origin', 'main')
run(MAIN, 'fast-forward-remote', 'git', 'merge', '--ff-only', 'origin/main')
run(MAIN, 'merge', 'git', 'merge', '--no-ff', commit, '-m', 'merge: accept W06 fixed offline contract tooling')
main_head = run(MAIN, 'merged-head', 'git', 'rev-parse', 'HEAD')
run(MAIN, 'normal-push', 'git', 'push', 'origin', 'main')
remote = run(MAIN, 'remote-head', 'git', 'ls-remote', 'origin', 'refs/heads/main').split()[0]
assert remote == main_head
assert key_before == (key.stat().st_size, key.stat().st_mtime_ns)
for row in freeze['files']:
    assert sha(FF / row['path']) == row['sha256'], row['path']
report = {'schema': 'root-w06-ff-tool-publication/1', 'tool_commit': commit,
          'main_commit': main_head, 'remote_exact': remote,
          'normal_hooks': True, 'freeze_unchanged': True, 'real_key_stat_unchanged': True,
          'tool_acceptance': '195 focused + 28 independent PASS',
          'product_matrix': '40 PASS / 1 FAIL; cutoff diagnostic repair remains open',
          'install': 'not needed; manual tools only', 'ci': 'pending exact-SHA check'}
(OUT / 'publication.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report), flush=True)
